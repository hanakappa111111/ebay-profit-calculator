"""
eBay API integration module for fetching item details
"""
import requests
import re
from typing import Dict, Optional
from bs4 import BeautifulSoup
import json
import time
from config import EBAY_CONFIG, API_ENDPOINTS, get_ebay_headers, get_fee_rate

class eBayAPI:
    def __init__(self):
        self.config = EBAY_CONFIG
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
    
    def extract_item_id(self, url_or_id: str) -> Optional[str]:
        """Extract eBay item ID from URL or return the ID if already provided"""
        if not url_or_id:
            return None
        
        # Remove whitespace
        url_or_id = url_or_id.strip()
        
        # If it's already just numbers, return as-is
        if url_or_id.isdigit():
            return url_or_id
        
        # Extract from various eBay URL formats
        patterns = [
            r'/itm/([0-9]+)',
            r'item=([0-9]+)',
            r'/([0-9]+)(?:\?|$)',
            r'ItemID=([0-9]+)',
            r'ebay\.com/([0-9]+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url_or_id)
            if match:
                return match.group(1)
        
        return None
    
    def fetch_item_via_api(self, item_id: str) -> Optional[Dict]:
        """Fetch item details using official eBay API (requires authentication)"""
        try:
            if self.config['app_id'] == 'your_app_id_here':
                return None  # No valid API credentials
            
            url = f"{API_ENDPOINTS['ebay_browse']}/item/{item_id}"
            headers = get_ebay_headers()
            
            response = self.session.get(url, headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                return self._parse_api_response(data)
            else:
                print(f"API Error: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"API fetch error: {e}")
            return None
    
    def fetch_item_via_scraping(self, item_id: str) -> Optional[Dict]:
        """Fetch item details via web scraping (fallback method)"""
        try:
            url = f"https://www.ebay.com/itm/{item_id}"
            
            # Add more headers to avoid blocking
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
            }
            
            response = self.session.get(url, headers=headers, timeout=10)
            
            print(f"Response status: {response.status_code}")
            print(f"Response URL: {response.url}")
            
            if response.status_code != 200:
                print(f"HTTP Error: {response.status_code}")
                return None
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Extract item details
            dimensions = self._extract_dimensions_and_weight(soup)
            title = self._extract_title(soup)
            price = self._extract_price(soup)
            
            print(f"Extracted title: {title}")
            print(f"Extracted price: {price}")
            print(f"Extracted dimensions: {dimensions}")
            
            # Try multiple title selectors for better compatibility
            if not title:
                title_selectors = [
                    'h1',
                    '[data-testid="x-title-label-lbl"]',
                    '.x-title-label-lbl',
                    '.it-ttl',
                    '.ebay-title',
                    '#ia-title'
                ]
                
                for selector in title_selectors:
                    title_element = soup.select_one(selector)
                    if title_element and title_element.get_text().strip():
                        title = title_element.get_text().strip()
                        print(f"Found title with selector {selector}: {title}")
                        break
            
            # Try multiple price selectors
            if not price:
                price_selectors = [
                    '[data-testid="price"] .ux-textspans',
                    '.price .notranslate',
                    '#prcIsum .notranslate',
                    '.ebay-price',
                    '.u-flL.condText + .u-flL .notranslate'
                ]
                
                for selector in price_selectors:
                    price_element = soup.select_one(selector)
                    if price_element:
                        price_text = price_element.get_text()
                        # Extract numeric value
                        price_match = re.search(r'[\d,]+\.?\d*', price_text.replace(',', ''))
                        if price_match:
                            try:
                                price = float(price_match.group())
                                print(f"Found price with selector {selector}: {price}")
                                break
                            except ValueError:
                                continue
            
            item_data = {
                'item_id': item_id,
                'title': title or "商品タイトル取得失敗",
                'price': price or 0.0,
                'category_id': self._extract_category(soup),
                'currency': 'USD',
                'condition': self._extract_condition(soup),
                'shipping_weight': dimensions.get('weight', 500),  # Use extracted weight or default
                'image_url': self._extract_image(soup),
                'seller_info': self._extract_seller_info(soup),
                'dimensions': dimensions
            }
            
            # Return data even if title or price extraction failed (for debugging)
            return item_data
            
        except Exception as e:
            print(f"Scraping error: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _extract_title(self, soup: BeautifulSoup) -> str:
        """Extract item title from HTML"""
        selectors = [
            'h1[id="x-title-label-lbl"]',
            'h1.x-title-label-lbl',
            'h1.it-ttl',
            '.notranslate'
        ]
        
        for selector in selectors:
            element = soup.select_one(selector)
            if element:
                return element.get_text().strip()
        
        return ""
    
    def _extract_dimensions_and_weight(self, soup: BeautifulSoup) -> Dict:
        """Extract product dimensions and weight from HTML"""
        dimensions_data = {
            'length': None,
            'width': None, 
            'height': None,
            'weight': None,
            'weight_unit': 'g',
            'dimension_unit': 'cm'
        }
        
        # Look for shipping and payment section
        shipping_section = soup.find('div', {'id': 'shipping-payment'}) or soup.find('div', class_='u-flL')
        
        # Try to find dimensions in various locations
        selectors_to_try = [
            '.itemAttr',
            '.attrLabels',
            '.u-flL.condText',
            '.specs',
            '.itemSpecifics'
        ]
        
        text_content = ""
        if shipping_section:
            text_content += shipping_section.get_text()
        
        # Get all text content from potential locations
        for selector in selectors_to_try:
            elements = soup.select(selector)
            for element in elements:
                text_content += " " + element.get_text()
        
        # Extract weight information
        import re
        
        # Weight patterns
        weight_patterns = [
            r'(\d+(?:\.\d+)?)\s*(?:kg|キロ|kilogram)',
            r'(\d+(?:\.\d+)?)\s*(?:g|グラム|gram)',
            r'(\d+(?:\.\d+)?)\s*(?:lb|pound|ポンド)',
            r'(\d+(?:\.\d+)?)\s*(?:oz|ounce|オンス)',
            r'Weight:?\s*(\d+(?:\.\d+)?)\s*(?:kg|g|lb|oz)',
            r'重量:?\s*(\d+(?:\.\d+)?)\s*(?:kg|g|キロ|グラム)'
        ]
        
        for pattern in weight_patterns:
            match = re.search(pattern, text_content, re.IGNORECASE)
            if match:
                weight_value = float(match.group(1))
                weight_text = match.group(0).lower()
                
                if 'kg' in weight_text or 'キロ' in weight_text:
                    dimensions_data['weight'] = int(weight_value * 1000)  # Convert to grams
                elif 'lb' in weight_text or 'pound' in weight_text:
                    dimensions_data['weight'] = int(weight_value * 453.592)  # Convert to grams
                elif 'oz' in weight_text or 'ounce' in weight_text:
                    dimensions_data['weight'] = int(weight_value * 28.3495)  # Convert to grams
                else:
                    dimensions_data['weight'] = int(weight_value)  # Assume grams
                break
        
        # Dimension patterns
        dimension_patterns = [
            r'(\d+(?:\.\d+)?)\s*x\s*(\d+(?:\.\d+)?)\s*x\s*(\d+(?:\.\d+)?)\s*(?:cm|センチ|inch|インチ)',
            r'Length:?\s*(\d+(?:\.\d+)?)\s*(?:cm|inch)',
            r'Width:?\s*(\d+(?:\.\d+)?)\s*(?:cm|inch)',
            r'Height:?\s*(\d+(?:\.\d+)?)\s*(?:cm|inch)',
            r'Dimensions:?\s*(\d+(?:\.\d+)?)\s*x\s*(\d+(?:\.\d+)?)\s*x\s*(\d+(?:\.\d+)?)',
            r'サイズ:?\s*(\d+(?:\.\d+)?)\s*x\s*(\d+(?:\.\d+)?)\s*x\s*(\d+(?:\.\d+)?)'
        ]
        
        for pattern in dimension_patterns:
            match = re.search(pattern, text_content, re.IGNORECASE)
            if match:
                if 'x' in pattern and len(match.groups()) >= 3:
                    # L x W x H format
                    dimensions_data['length'] = float(match.group(1))
                    dimensions_data['width'] = float(match.group(2))
                    dimensions_data['height'] = float(match.group(3))
                    
                    # Check for inch and convert to cm
                    if 'inch' in match.group(0).lower() or 'インチ' in match.group(0):
                        dimensions_data['length'] *= 2.54
                        dimensions_data['width'] *= 2.54
                        dimensions_data['height'] *= 2.54
                        dimensions_data['dimension_unit'] = 'cm'
                    break
                else:
                    # Single dimension
                    value = float(match.group(1))
                    if 'inch' in match.group(0).lower():
                        value *= 2.54
                    
                    if 'length' in pattern.lower():
                        dimensions_data['length'] = value
                    elif 'width' in pattern.lower():
                        dimensions_data['width'] = value
                    elif 'height' in pattern.lower():
                        dimensions_data['height'] = value
        
        return dimensions_data
    
    def _extract_price(self, soup: BeautifulSoup) -> float:
        """Extract item price from HTML"""
        selectors = [
            '.notranslate[data-testid="price"] .ux-textspans',
            '.price .notranslate',
            '#prcIsum .notranslate',
            '[data-testid="price"] span'
        ]
        
        for selector in selectors:
            element = soup.select_one(selector)
            if element:
                price_text = element.get_text()
                # Extract numeric value
                price_match = re.search(r'[\d,]+\.?\d*', price_text.replace(',', ''))
                if price_match:
                    try:
                        return float(price_match.group())
                    except ValueError:
                        continue
        
        return 0.0
    
    def _extract_category(self, soup: BeautifulSoup) -> str:
        """Extract category information from HTML"""
        # Try to find breadcrumb navigation
        breadcrumb = soup.select('.seo-breadcrumb-text')
        if breadcrumb and len(breadcrumb) > 1:
            return breadcrumb[-1].get_text().strip()
        
        # Fallback to category ID in scripts
        scripts = soup.find_all('script')
        for script in scripts:
            if script.string and 'categoryId' in script.string:
                # Try to extract category ID
                match = re.search(r'"categoryId":"([^"]+)"', script.string)
                if match:
                    return match.group(1)
        
        return "general"
    
    def _extract_condition(self, soup: BeautifulSoup) -> str:
        """Extract item condition from HTML"""
        condition_element = soup.select_one('.u-flL.condText')
        if condition_element:
            return condition_element.get_text().strip()
        
        return "Used"
    
    def _extract_image(self, soup: BeautifulSoup) -> str:
        """Extract main item image URL"""
        img_element = soup.select_one('#icImg')
        if img_element and img_element.get('src'):
            return img_element['src']
        
        return ""
    
    def _extract_seller_info(self, soup: BeautifulSoup) -> Dict:
        """Extract seller information"""
        seller_info = {
            'username': '',
            'feedback_score': '',
            'feedback_percent': ''
        }
        
        # Extract seller username
        seller_element = soup.select_one('.mbg-nw')
        if seller_element:
            seller_info['username'] = seller_element.get_text().strip()
        
        return seller_info
    
    def _parse_api_response(self, data: Dict) -> Dict:
        """Parse official API response into standardized format"""
        try:
            price = 0.0
            if 'price' in data and 'value' in data['price']:
                price = float(data['price']['value'])
            
            return {
                'item_id': data.get('itemId', ''),
                'title': data.get('title', ''),
                'price': price,
                'category_id': data.get('primaryCategory', {}).get('categoryId', ''),
                'currency': data.get('price', {}).get('currency', 'USD'),
                'condition': data.get('condition', 'Unknown'),
                'shipping_weight': 500,  # Default weight
                'image_url': data.get('image', {}).get('imageUrl', ''),
                'seller_info': {
                    'username': data.get('seller', {}).get('username', ''),
                    'feedback_score': data.get('seller', {}).get('feedbackScore', ''),
                    'feedback_percent': data.get('seller', {}).get('feedbackPercentage', '')
                }
            }
        except Exception as e:
            print(f"Error parsing API response: {e}")
            return None
    
    def get_item_details(self, url_or_id: str) -> Optional[Dict]:
        """Main method to fetch item details - tries API first, then scraping"""
        # Check for test mode
        if url_or_id.lower().strip() == 'test':
            return self._get_test_data()
        
        item_id = self.extract_item_id(url_or_id)
        if not item_id:
            return None
        
        # Try API first (if credentials are configured)
        item_data = self.fetch_item_via_api(item_id)
        
        # Fallback to scraping if API fails
        if not item_data:
            item_data = self.fetch_item_via_scraping(item_id)
        
        # Add calculated fee rate
        if item_data:
            item_data['fee_rate'] = get_fee_rate(item_data.get('category_id'))
        
        return item_data
    
    def _get_test_data(self) -> Dict:
        """Return test data for debugging purposes"""
        return {
            'item_id': 'test',
            'title': 'テスト商品 - iPhone 15 Pro Max 256GB',
            'price': 999.99,
            'category_id': 'electronics',
            'currency': 'USD',
            'condition': 'New',
            'shipping_weight': 750,  # 750g
            'image_url': '',
            'seller_info': {'username': 'test_seller'},
            'dimensions': {
                'length': 16.0,
                'width': 7.8,
                'height': 0.8,
                'weight': 750,
                'weight_unit': 'g',
                'dimension_unit': 'cm'
            },
            'fee_rate': 0.1275
        }

# Create a global instance
ebay_api = eBayAPI() 