"""
eBay API integration module for fetching item details
"""
import requests
import re
from typing import Dict, Optional, List
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
        self.last_debug_info = {}
        self.access_token = None
    
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
            # Try multiple URL formats and approaches
            urls_to_try = [
                f"https://www.ebay.com/itm/{item_id}",
                f"https://www.ebay.com/itm/{item_id}?_from=R40",
                f"https://www.ebay.com/p/{item_id}",
                f"https://www.ebay.com/sch/i.html?_nkw={item_id}"
            ]
            
            # Multiple user agents to rotate
            user_agents = [
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
                'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
                'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0'
            ]
            
            import random
            import time
            
            for attempt, url in enumerate(urls_to_try):
                try:
                    # Random delay to avoid rate limiting
                    time.sleep(random.uniform(1, 3))
                    
                    # Enhanced headers to mimic real browser
                    headers = {
                        'User-Agent': random.choice(user_agents),
                        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
                        'Accept-Language': 'en-US,en;q=0.9,ja;q=0.8',
                        'Accept-Encoding': 'gzip, deflate, br',
                        'Connection': 'keep-alive',
                        'Upgrade-Insecure-Requests': '1',
                        'Sec-Fetch-Dest': 'document',
                        'Sec-Fetch-Mode': 'navigate',
                        'Sec-Fetch-Site': 'none' if attempt == 0 else 'same-origin',
                        'Sec-Fetch-User': '?1',
                        'Cache-Control': 'max-age=0',
                        'DNT': '1',
                        'Sec-Ch-Ua': '"Not A(Brand";v="99", "Google Chrome";v="121", "Chromium";v="121"',
                        'Sec-Ch-Ua-Mobile': '?0',
                        'Sec-Ch-Ua-Platform': '"macOS"',
                        'Referer': 'https://www.ebay.com/' if attempt > 0 else None
                    }
                    
                    # Remove None values
                    headers = {k: v for k, v in headers.items() if v is not None}
                    
                    response = self.session.get(url, headers=headers, timeout=15)
                    
                    # Check if we got blocked
                    if 'checking your browser' in response.text.lower() or response.status_code == 403:
                        continue
                    
                    if response.status_code == 200:
                        break
                        
                except Exception as e:
                    if attempt == len(urls_to_try) - 1:
                        raise e
                    continue
            else:
                return None
            
            # Store debug info for UI display
            self.last_debug_info = {
                'response_status': response.status_code,
                'response_url': str(response.url),
                'attempt_count': attempt + 1,
                'successful_url': url,
                'is_blocked': 'checking your browser' in response.text.lower(),
                'extracted_data': {}
            }
            
            if response.status_code != 200:
                print(f"HTTP Error: {response.status_code}")
                return None
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Extract item details
            dimensions = self._extract_dimensions_and_weight(soup)
            title = self._extract_title(soup)
            price = self._extract_price(soup)
            
            # Store extracted data for debugging
            page_text = soup.get_text().lower()
            price_mentions = [line.strip() for line in soup.get_text().split('\n') if '$' in line and line.strip()][:10]
            
            # Extract all prices found on the page for debugging
            all_found_prices = []
            for line in soup.get_text().split('\n'):
                if '$' in line:
                    dollar_matches = re.findall(r'\$\s*([\d,]+\.?\d*)', line.replace(',', ''))
                    for match in dollar_matches:
                        try:
                            price_val = float(match)
                            if 0.01 <= price_val <= 99999:
                                all_found_prices.append(price_val)
                        except ValueError:
                            continue
            
            self.last_debug_info['extracted_data'] = {
                'title': title,
                'price': price,
                'dimensions': dimensions,
                'page_length': len(response.content),
                'contains_price_data': '$' in page_text or 'usd' in page_text,
                'contains_weight_data': any(word in page_text for word in ['weight', '重量', 'kg', 'gram', 'lb', 'oz']),
                'contains_dimension_data': any(word in page_text for word in ['dimension', 'size', 'length', 'width', 'height']),
                'price_mentions_sample': price_mentions,
                'all_prices_found': sorted(set(all_found_prices), reverse=True)[:10],  # Top 10 unique prices
                'highest_price_found': max(all_found_prices) if all_found_prices else 0,
                'title_selectors_found': len(soup.select('h1')),
                'price_selectors_found': len(soup.select('[data-testid="price"]')),
                'url_used': url
            }
            
            # More aggressive price extraction methods
            if not price or price < 10:  # If price is suspiciously low, try harder
                # Method 1: Look for the largest price on the page
                all_prices = []
                all_text_lines = soup.get_text().split('\n')
                
                for line in all_text_lines:
                    if '$' in line:
                        # Extract all dollar amounts from the line
                        dollar_matches = re.findall(r'\$\s*([\d,]+\.?\d*)', line.replace(',', ''))
                        for match in dollar_matches:
                            try:
                                price_val = float(match)
                                if 1 <= price_val <= 99999:  # Reasonable price range
                                    all_prices.append(price_val)
                            except ValueError:
                                continue
                
                # Take the highest price (likely the main selling price)
                if all_prices:
                    potential_price = max(all_prices)
                    if potential_price > price:  # Use if higher than current
                        price = potential_price
                        self.last_debug_info['extracted_data']['price_method'] = 'max_price_extraction'
                
                # Method 2: Look in specific price containers
                price_containers = [
                    '.ux-price-display',
                    '.price-current',
                    '.current-price',
                    '.selling-price',
                    '.item-price',
                    '[data-testid="price"]'
                ]
                
                for container in price_containers:
                    elements = soup.select(container)
                    for element in elements:
                        text = element.get_text()
                        prices_in_element = re.findall(r'\$\s*([\d,]+\.?\d*)', text.replace(',', ''))
                        for price_str in prices_in_element:
                            try:
                                potential_price = float(price_str)
                                if potential_price > price and 1 <= potential_price <= 99999:
                                    price = potential_price
                                    self.last_debug_info['extracted_data']['price_method'] = f'container_{container}'
                            except ValueError:
                                continue
                
                # Method 3: Look in meta tags
                meta_price = soup.find('meta', property='product:price:amount')
                if meta_price and meta_price.get('content'):
                    try:
                        meta_price_val = float(meta_price['content'])
                        if meta_price_val > price:
                            price = meta_price_val
                            self.last_debug_info['extracted_data']['price_method'] = 'meta_tag'
                    except ValueError:
                        pass
            
            # Improved title extraction if needed
            if not title:
                title_selectors = [
                    'h1[data-testid="x-title-label-lbl"]',
                    'h1',
                    '.x-title-label-lbl',
                    '.it-ttl',
                    '[data-testid="item-title"]',
                    '.ebay-title'
                ]
                
                for selector in title_selectors:
                    title_element = soup.select_one(selector)
                    if title_element and title_element.get_text().strip():
                        title = title_element.get_text().strip()
                        # Clean up title
                        title = re.sub(r'^Details about\s*', '', title, flags=re.IGNORECASE)
                        self.last_debug_info['extracted_data']['title_selector'] = selector
                        break

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
            self.last_debug_info = {
                'error': str(e),
                'error_type': type(e).__name__
            }
            return None
    
    def _extract_title(self, soup: BeautifulSoup) -> str:
        """Extract item title from HTML"""
        # More comprehensive title selectors for modern eBay
        selectors = [
            'h1[data-testid="x-title-label-lbl"]',
            'h1[id="x-title-label-lbl"]', 
            'h1.x-title-label-lbl',
            'h1.it-ttl',
            'h1.notranslate',
            'h1 span.notranslate',
            '[data-testid="item-title"]',
            '.x-title-label-lbl span',
            'h1'
        ]
        
        for selector in selectors:
            element = soup.select_one(selector)
            if element and element.get_text().strip():
                title = element.get_text().strip()
                # Remove unwanted text like "Details about"
                title = re.sub(r'^Details about\s*', '', title, flags=re.IGNORECASE)
                return title
        
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
        
        # Look for dimensions and weight in multiple sections
        sections_to_check = [
            soup.find('div', {'id': 'shipping-payment'}),
            soup.find('div', class_='u-flL'),
            soup.find('div', {'id': 'itemSpecifics'}),
            soup.find('section', {'data-testid': 'item-details'}),
            soup.find('div', class_='itemAttr')
        ]
        
        # More comprehensive selectors for item specifications
        selectors_to_try = [
            '.itemAttr',
            '.attrLabels', 
            '.u-flL.condText',
            '.specs',
            '.itemSpecifics',
            '[data-testid="item-specifics"]',
            '.item-specifics',
            '.ebay-details',
            '.vim',
            'table',
            '.x-item-condition-text',
            '.section-subtitle'
        ]
        
        text_content = ""
        
        # Extract text from specific sections
        for section in sections_to_check:
            if section:
                text_content += " " + section.get_text()
        
        # Get all text content from potential locations
        for selector in selectors_to_try:
            elements = soup.select(selector)
            for element in elements:
                text_content += " " + element.get_text()
        
        # Also check the entire page text for specifications
        page_text = soup.get_text()
        text_content += " " + page_text
        
        # Extract weight information
        import re
        
        # Enhanced weight patterns
        weight_patterns = [
            r'Weight[:\s]*(\d+(?:\.\d+)?)\s*(?:kg|キロ|kilogram)',
            r'Weight[:\s]*(\d+(?:\.\d+)?)\s*(?:g|グラム|gram|grams)',
            r'Weight[:\s]*(\d+(?:\.\d+)?)\s*(?:lb|lbs|pound|pounds|ポンド)',
            r'Weight[:\s]*(\d+(?:\.\d+)?)\s*(?:oz|ounce|ounces|オンス)',
            r'重量[:\s]*(\d+(?:\.\d+)?)\s*(?:kg|g|キロ|グラム)',
            r'Item Weight[:\s]*(\d+(?:\.\d+)?)\s*(?:kg|g|lb|oz)',
            r'Shipping Weight[:\s]*(\d+(?:\.\d+)?)\s*(?:kg|g|lb|oz)',
            r'(\d+(?:\.\d+)?)\s*(?:kg|キロ|kilogram)s?',
            r'(\d+(?:\.\d+)?)\s*(?:g|グラム|gram)s?',
            r'(\d+(?:\.\d+)?)\s*(?:lb|lbs|pound|pounds|ポンド)',
            r'(\d+(?:\.\d+)?)\s*(?:oz|ounce|ounces|オンス)'
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
        
        # Enhanced dimension patterns
        dimension_patterns = [
            r'Dimensions?[:\s]*(\d+(?:\.\d+)?)\s*[x×]\s*(\d+(?:\.\d+)?)\s*[x×]\s*(\d+(?:\.\d+)?)\s*(?:cm|センチ|inch|インチ|in)',
            r'Size[:\s]*(\d+(?:\.\d+)?)\s*[x×]\s*(\d+(?:\.\d+)?)\s*[x×]\s*(\d+(?:\.\d+)?)\s*(?:cm|センチ|inch|インチ|in)',
            r'(\d+(?:\.\d+)?)\s*[x×]\s*(\d+(?:\.\d+)?)\s*[x×]\s*(\d+(?:\.\d+)?)\s*(?:cm|センチ|inch|インチ|in)',
            r'Length[:\s]*(\d+(?:\.\d+)?)\s*(?:cm|センチ|inch|インチ|in)',
            r'Width[:\s]*(\d+(?:\.\d+)?)\s*(?:cm|センチ|inch|インチ|in)', 
            r'Height[:\s]*(\d+(?:\.\d+)?)\s*(?:cm|センチ|inch|インチ|in)',
            r'Depth[:\s]*(\d+(?:\.\d+)?)\s*(?:cm|センチ|inch|インチ|in)',
            r'サイズ[:\s]*(\d+(?:\.\d+)?)\s*[x×]\s*(\d+(?:\.\d+)?)\s*[x×]\s*(\d+(?:\.\d+)?)',
            r'寸法[:\s]*(\d+(?:\.\d+)?)\s*[x×]\s*(\d+(?:\.\d+)?)\s*[x×]\s*(\d+(?:\.\d+)?)',
            r'Package Dimensions[:\s]*(\d+(?:\.\d+)?)\s*[x×]\s*(\d+(?:\.\d+)?)\s*[x×]\s*(\d+(?:\.\d+)?)'
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
        """Extract item price from HTML with improved accuracy"""
        # Priority-ordered selectors for different eBay layouts
        priority_selectors = [
            # Modern eBay layouts
            'span[data-testid="price"] .ux-textspans',
            '[data-testid="price"] .ux-textspans',
            'span[data-testid="price"] span',
            '.ux-textspans--BOLD',
            
            # Legacy selectors
            '.notranslate[data-testid="price"] .ux-textspans',
            '.price .notranslate', 
            '#prcIsum .notranslate',
            '.u-flL.condText + .u-flL .notranslate',
            '.ebay-price .notranslate',
            '.display-price',
            '[data-testid="price"] .notranslate',
            
            # Fallback selectors
            '.ux-price-display__range',
            '.ux-price-display',
            '.notranslate'
        ]
        
        # Enhanced price patterns with priorities
        def extract_price_from_text(text):
            price_patterns = [
                r'US\s*\$\s*([\d,]+\.?\d*)',  # US $44.00
                r'\$\s*([\d,]+\.?\d*)',       # $44.00
                r'([\d,]+\.?\d*)\s*USD',      # 44.00 USD
                r'([\d,]+\.?\d*)\s*dollars?', # 44.00 dollars
                r'([\d,]+\.?\d*)'             # 44.00
            ]
            
            for pattern in price_patterns:
                matches = re.findall(pattern, text.replace(',', ''), re.IGNORECASE)
                for match in matches:
                    try:
                        price = float(match)
                        # Valid price range check
                        if 0.01 <= price <= 999999:
                            return price
                    except (ValueError, TypeError):
                        continue
            return None
        
        # Try priority selectors first
        for selector in priority_selectors:
            elements = soup.select(selector)
            for element in elements:
                if element and element.get_text().strip():
                    text = element.get_text().strip()
                    price = extract_price_from_text(text)
                    if price:
                        return price
        
        # Fallback: search in script tags for JSON data
        scripts = soup.find_all('script', type='application/ld+json')
        for script in scripts:
            try:
                import json
                data = json.loads(script.string)
                if isinstance(data, dict):
                    # Look for offers or price in structured data
                    offers = data.get('offers', {})
                    if offers and 'price' in offers:
                        price = float(offers['price'])
                        if price > 0:
                            return price
            except (json.JSONDecodeError, ValueError, TypeError):
                continue
        
        # Last resort: search all text for price patterns
        all_text = soup.get_text()
        # Focus on lines that contain currency symbols
        lines_with_currency = [line for line in all_text.split('\n') if '$' in line or 'USD' in line]
        for line in lines_with_currency:
            price = extract_price_from_text(line)
            if price:
                return price
        
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
    
    def get_oauth_token(self) -> Optional[str]:
        """Get OAuth access token for eBay API"""
        try:
            # eBay OAuth endpoint
            oauth_url = "https://api.ebay.com/identity/v1/oauth2/token"
            
            # Prepare credentials
            import base64
            credentials = f"{self.config['app_id']}:{self.config['cert_id']}"
            encoded_credentials = base64.b64encode(credentials.encode()).decode()
            
            headers = {
                'Content-Type': 'application/x-www-form-urlencoded',
                'Authorization': f'Basic {encoded_credentials}'
            }
            
            data = {
                'grant_type': 'client_credentials',
                'scope': 'https://api.ebay.com/oauth/api_scope'
            }
            
            response = self.session.post(oauth_url, headers=headers, data=data, timeout=10)
            
            if response.status_code == 200:
                token_data = response.json()
                self.access_token = token_data.get('access_token')
                return self.access_token
            else:
                self.last_debug_info['oauth_error'] = {
                    'status_code': response.status_code,
                    'response': response.text[:300]
                }
                return None
                
        except Exception as e:
            self.last_debug_info['oauth_exception'] = str(e)
            return None
    
    def test_api_connection(self) -> Dict:
        """Test eBay API connection and credentials"""
        test_result = {
            'config_valid': False,
            'oauth_token': False,
            'finding_api': False,
            'errors': []
        }
        
        # Check config
        if (self.config['app_id'] != 'your_actual_app_id_here' and 
            self.config['cert_id'] != 'your_actual_cert_id_here'):
            test_result['config_valid'] = True
        else:
            test_result['errors'].append('API credentials not configured')
        
        # Test OAuth
        if test_result['config_valid']:
            token = self.get_oauth_token()
            if token:
                test_result['oauth_token'] = True
            else:
                test_result['errors'].append('OAuth token acquisition failed')
        
        return test_result
    
    def search_items(self, keyword: str, limit: int = 20) -> List[Dict]:
        """Search for items using eBay Browse API (newer, OAuth-based)"""
        try:
            if self.config['app_id'] == 'your_actual_app_id_here':
                self.last_debug_info = {'error': 'No valid API credentials configured'}
                return []
            
            # Get OAuth token first
            if not self.access_token:
                token = self.get_oauth_token()
                if not token:
                    self.last_debug_info['error'] = 'Failed to obtain OAuth token'
                    return []
            
            # Try eBay Browse API (newer)
            browse_api_url = "https://api.ebay.com/buy/browse/v1/item_summary/search"
            
            headers = {
                'Authorization': f'Bearer {self.access_token}',
                'Content-Type': 'application/json',
                'X-EBAY-C-MARKETPLACE-ID': 'EBAY_US'
            }
            
            params = {
                'q': keyword,
                'limit': str(min(limit, 20)),
                'sort': 'price',
                'filter': 'price:[5..10000],priceCurrency:USD,itemLocationCountry:US'
            }
            
            self.last_debug_info = {
                'api_type': 'Browse API',
                'api_url': browse_api_url,
                'keyword': keyword,
                'has_token': bool(self.access_token),
                'token_preview': self.access_token[:20] + '...' if self.access_token else None
            }
            
            response = self.session.get(browse_api_url, headers=headers, params=params, timeout=15)
            
            self.last_debug_info.update({
                'response_status': response.status_code,
                'response_length': len(response.content)
            })
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    results = self._parse_browse_results(data)
                    self.last_debug_info['results_count'] = len(results)
                    return results
                except json.JSONDecodeError as e:
                    self.last_debug_info['json_error'] = str(e)
                    return []
            else:
                # Fallback to Finding API (legacy)
                return self._search_with_finding_api(keyword, limit)
                
        except Exception as e:
            self.last_debug_info = {'exception': str(e), 'exception_type': type(e).__name__}
            return []
    
    def _search_with_finding_api(self, keyword: str, limit: int = 20) -> List[Dict]:
        """Fallback to Finding API (no OAuth required)"""
        try:
            # eBay Finding API endpoint  
            finding_api_url = "https://svcs.ebay.com/services/search/FindingService/v1"
            
            # API parameters - simplified for better compatibility
            params = {
                'OPERATION-NAME': 'findItemsByKeywords',
                'SERVICE-VERSION': '1.0.0',
                'SECURITY-APPNAME': self.config['app_id'],
                'RESPONSE-DATA-FORMAT': 'JSON',
                'keywords': keyword,
                'paginationInput.entriesPerPage': str(min(limit, 20)),
                'sortOrder': 'BestMatch',
                'itemFilter(0).name': 'ListingType',
                'itemFilter(0).value(0)': 'FixedPrice',
                'itemFilter(1).name': 'MinPrice',
                'itemFilter(1).value': '5',
                'itemFilter(2).name': 'MaxPrice', 
                'itemFilter(2).value': '10000'
            }
            
            # Store debug info
            self.last_debug_info = {
                'api_type': 'Finding API (fallback)',
                'api_url': finding_api_url,
                'app_id_used': self.config['app_id'][:10] + '...' if len(self.config['app_id']) > 10 else self.config['app_id'],
                'keyword': keyword,
                'request_params': params
            }
            
            response = self.session.get(finding_api_url, params=params, timeout=15)
            
            # Store response info
            self.last_debug_info.update({
                'response_status': response.status_code,
                'response_url': str(response.url),
                'response_length': len(response.content)
            })
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    self.last_debug_info['response_json'] = True
                    
                    # Check for API errors in response
                    if 'errorMessage' in str(data):
                        self.last_debug_info['api_error'] = str(data)
                        return []
                    
                    results = self._parse_search_results(data)
                    self.last_debug_info['results_count'] = len(results)
                    return results
                    
                except json.JSONDecodeError as e:
                    self.last_debug_info['json_error'] = str(e)
                    self.last_debug_info['response_text'] = response.text[:500]
                    return []
            else:
                self.last_debug_info['error_response'] = response.text[:500]
                return []
                
        except Exception as e:
            self.last_debug_info = {
                'exception': str(e),
                'exception_type': type(e).__name__
            }
            return []
    
    def _parse_search_results(self, data: Dict) -> List[Dict]:
        """Parse eBay Finding API search results"""
        results = []
        
        try:
            search_result = data.get('findItemsByKeywordsResponse', [{}])[0]
            items = search_result.get('searchResult', [{}])[0].get('item', [])
            
            for item in items:
                try:
                    # Extract item details
                    title = item.get('title', [''])[0] if item.get('title') else ''
                    item_id = item.get('itemId', [''])[0] if item.get('itemId') else ''
                    
                    # Price information
                    selling_status = item.get('sellingStatus', [{}])[0]
                    current_price = selling_status.get('currentPrice', [{}])[0]
                    price = float(current_price.get('__value__', '0')) if current_price else 0.0
                    
                    # Shipping cost
                    shipping_info = item.get('shippingInfo', [{}])[0]
                    shipping_cost = shipping_info.get('shippingServiceCost', [{}])[0]
                    shipping_price = float(shipping_cost.get('__value__', '0')) if shipping_cost else 0.0
                    
                    # End time (sold date)
                    end_time = item.get('listingInfo', [{}])[0].get('endTime', [''])[0]
                    if end_time:
                        # Convert to simple date format
                        from datetime import datetime
                        try:
                            dt = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
                            sold_date = dt.strftime('%Y-%m-%d')
                        except:
                            sold_date = end_time[:10]  # Take first 10 chars as fallback
                    else:
                        sold_date = '2025-01-01'
                    
                    # Condition
                    condition = item.get('condition', [{}])[0].get('conditionDisplayName', ['Used'])[0] if item.get('condition') else 'Used'
                    
                    # Seller info
                    seller_info = item.get('sellerInfo', [{}])[0]
                    seller_name = seller_info.get('sellerUserName', ['Unknown'])[0] if seller_info else 'Unknown'
                    feedback_score = seller_info.get('feedbackScore', ['0'])[0] if seller_info else '0'
                    
                    # Skip items with very low prices (likely invalid)
                    if price < 1.0:
                        continue
                    
                    result_item = {
                        'タイトル': title[:50] + '...' if len(title) > 50 else title,  # Truncate long titles
                        '価格_USD': price,
                        '送料_USD': shipping_price,
                        '売れた日': sold_date,
                        '商品状態': condition,
                        '出品者': f"{seller_name} (評価 {feedback_score})",
                        'item_id': item_id
                    }
                    
                    results.append(result_item)
                    
                except Exception as item_error:
                    print(f"Error parsing item: {item_error}")
                    continue
            
        except Exception as e:
            print(f"Error parsing search results: {e}")
        
        return results
    
    def _parse_browse_results(self, data: Dict) -> List[Dict]:
        """Parse eBay Browse API search results"""
        results = []
        
        try:
            items = data.get('itemSummaries', [])
            
            for item in items:
                try:
                    # Extract item details
                    title = item.get('title', '')
                    item_id = item.get('itemId', '')
                    
                    # Price information
                    price_info = item.get('price', {})
                    price = float(price_info.get('value', '0')) if price_info else 0.0
                    
                    # Shipping cost
                    shipping_info = item.get('shippingOptions', [{}])[0] if item.get('shippingOptions') else {}
                    shipping_cost_info = shipping_info.get('shippingCost', {})
                    shipping_price = float(shipping_cost_info.get('value', '0')) if shipping_cost_info else 0.0
                    
                    # Condition
                    condition = item.get('condition', 'Unknown')
                    
                    # Seller info
                    seller_info = item.get('seller', {})
                    seller_name = seller_info.get('username', 'Unknown')
                    feedback_score = seller_info.get('feedbackScore', '0')
                    
                    # Skip items with very low prices
                    if price < 1.0:
                        continue
                    
                    result_item = {
                        'タイトル': title[:50] + '...' if len(title) > 50 else title,
                        '価格_USD': price,
                        '送料_USD': shipping_price,
                        '売れた日': '2025-01-26',  # Browse API doesn't provide sold dates
                        '商品状態': condition,
                        '出品者': f"{seller_name} (評価 {feedback_score})",
                        'item_id': item_id
                    }
                    
                    results.append(result_item)
                    
                except Exception as item_error:
                    continue
            
        except Exception as e:
            pass
        
        return results
    
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