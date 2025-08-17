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
            
            response = self.session.get(url)
            
            if response.status_code != 200:
                return None
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Extract item details
            item_data = {
                'item_id': item_id,
                'title': self._extract_title(soup),
                'price': self._extract_price(soup),
                'category_id': self._extract_category(soup),
                'currency': 'USD',
                'condition': self._extract_condition(soup),
                'shipping_weight': 500,  # Default weight in grams
                'image_url': self._extract_image(soup),
                'seller_info': self._extract_seller_info(soup)
            }
            
            return item_data if item_data['title'] and item_data['price'] else None
            
        except Exception as e:
            print(f"Scraping error: {e}")
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

# Create a global instance
ebay_api = eBayAPI() 