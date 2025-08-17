"""
Configuration settings for eBay Profit Calculator
"""
import os
from typing import Dict

# eBay API Configuration
EBAY_CONFIG = {
    'app_id': os.getenv('EBAY_APP_ID', 'your_app_id_here'),
    'dev_id': os.getenv('EBAY_DEV_ID', 'your_dev_id_here'),
    'cert_id': os.getenv('EBAY_CERT_ID', 'your_cert_id_here'),
    'environment': os.getenv('EBAY_ENV', 'sandbox'),  # 'sandbox' or 'production'
}

# Currency Configuration
CURRENCY_CONFIG = {
    'api_key': os.getenv('CURRENCY_API_KEY', ''),
    'default_jpy_usd_rate': float(os.getenv('DEFAULT_JPY_USD_RATE', '150')),
    'update_interval': 3600,  # Update currency rates every hour
}

# eBay Fee Structure (simplified)
EBAY_FEES = {
    'default': 0.1275,  # 12.75% standard fee
    'motors_vehicles': 0.04,  # 4% for vehicles
    'collectibles': 0.15,  # 15% for some collectibles
    'electronics': 0.0875,  # 8.75% for electronics
    'business_industrial': 0.1275,  # 12.75%
    'fashion': 0.1275,  # 12.75%
    'home_garden': 0.1275,  # 12.75%
    'sports_mem': 0.1275,  # 12.75%
    'toys_hobbies': 0.1275,  # 12.75%
}

# Japan Post Shipping Rates (JPY)
SHIPPING_RATES = {
    "EMS": {
        "up_to_500g": 1400,
        "501_to_1000g": 2000,
        "1001_to_1500g": 2800,
        "1501_to_2000g": 3600,
        "over_2000g": 4400
    },
    "Air": {
        "up_to_500g": 1200,
        "501_to_1000g": 1800,
        "1001_to_1500g": 2400,
        "1501_to_2000g": 3000,
        "over_2000g": 3600
    },
    "SAL": {
        "up_to_500g": 800,
        "501_to_1000g": 1200,
        "1001_to_1500g": 1600,
        "1501_to_2000g": 2000,
        "over_2000g": 2400
    },
    "Surface": {
        "up_to_500g": 600,
        "501_to_1000g": 900,
        "1001_to_1500g": 1200,
        "1501_to_2000g": 1500,
        "over_2000g": 1800
    }
}

# Application Settings
APP_CONFIG = {
    'title': 'eBay Profit Calculator',
    'version': '1.0.0',
    'author': 'eBay Reseller Tool',
    'debug': os.getenv('DEBUG', 'False').lower() == 'true',
    'max_history_items': 100,
}

# API Endpoints
API_ENDPOINTS = {
    'ebay_browse': 'https://api.ebay.com/buy/browse/v1',
    'ebay_finding': 'https://svcs.ebay.com/services/search/FindingService/v1',
    'currency_api': 'https://api.exchangerate-api.com/v4/latest/USD',
}

def get_ebay_headers() -> Dict[str, str]:
    """Get headers for eBay API requests"""
    return {
        'Authorization': f'Bearer {EBAY_CONFIG["app_id"]}',
        'Content-Type': 'application/json',
        'X-EBAY-C-MARKETPLACE-ID': 'EBAY_US',
        'X-EBAY-C-ENDUSERCTX': 'affiliateCampaignId=<ePNCampaignId>,affiliateReferenceId=<referenceId>'
    }

def get_fee_rate(category_id: str = None) -> float:
    """Get eBay fee rate based on category"""
    if not category_id:
        return EBAY_FEES['default']
    
    # Simple category mapping
    category_lower = category_id.lower()
    
    if 'motor' in category_lower or 'vehicle' in category_lower:
        return EBAY_FEES['motors_vehicles']
    elif 'collect' in category_lower:
        return EBAY_FEES['collectibles']
    elif 'electronic' in category_lower or 'computer' in category_lower:
        return EBAY_FEES['electronics']
    elif 'business' in category_lower or 'industrial' in category_lower:
        return EBAY_FEES['business_industrial']
    else:
        return EBAY_FEES['default'] 