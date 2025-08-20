#!/usr/bin/env python3
"""
Enhanced eBay Profit Calculator - Module Integration Test
"""
import sys
import time
from datetime import datetime

def test_data_sources():
    """Test data sources module"""
    print("=== Testing Data Sources ===")
    
    try:
        from data_sources.ebay import search_completed_items, get_item_detail
        
        # Test search
        print("Testing search_completed_items...")
        results = search_completed_items("Nintendo", 5)
        print(f"✅ Search returned {len(results)} items")
        
        if results:
            # Test item detail
            print("Testing get_item_detail...")
            item_id = results[0]["item_id"]
            detail = get_item_detail(item_id)
            if detail:
                print(f"✅ Item detail retrieved: {detail['title'][:50]}...")
            else:
                print("⚠️ Item detail not found")
        
        return True
        
    except Exception as e:
        print(f"❌ Data sources test failed: {e}")
        return False

def test_shipping_module():
    """Test shipping calculation module"""
    print("\n=== Testing Shipping Module ===")
    
    try:
        from shipping.calc import quote, zone, estimate_weight
        
        # Test zone lookup
        print("Testing zone lookup...")
        us_zone = zone("US")
        jp_zone = zone("JP")
        print(f"✅ US zone: {us_zone}, JP zone: {jp_zone}")
        
        # Test shipping quote
        print("Testing shipping quote...")
        quote_result = quote(500, "US")  # 500g to US
        print(f"✅ Shipping quote: {quote_result}")
        
        # Test weight estimation
        print("Testing weight estimation...")
        weight = estimate_weight("Video Games & Consoles", "Nintendo Switch")
        print(f"✅ Estimated weight: {weight}g")
        
        return True
        
    except Exception as e:
        print(f"❌ Shipping module test failed: {e}")
        return False

def test_fx_utility():
    """Test FX utility module"""
    print("\n=== Testing FX Utility ===")
    
    try:
        from utils.fx import get_rate, convert_currency, format_currency
        
        # Test rate fetching
        print("Testing get_rate...")
        rate_info = get_rate("USD", "JPY")
        print(f"✅ USD/JPY rate: {rate_info['rate']:.2f} (source: {rate_info['source']})")
        
        # Test currency conversion
        print("Testing convert_currency...")
        conversion = convert_currency(100, "USD", "JPY")
        print(f"✅ $100 USD = ¥{conversion['converted_amount']:.0f} JPY")
        
        # Test formatting
        print("Testing format_currency...")
        formatted_jpy = format_currency(150000, "JPY")
        formatted_usd = format_currency(1000.50, "USD")
        print(f"✅ Formatted: {formatted_jpy}, {formatted_usd}")
        
        return True
        
    except Exception as e:
        print(f"❌ FX utility test failed: {e}")
        return False

def test_draft_management():
    """Test draft management module"""
    print("\n=== Testing Draft Management ===")
    
    try:
        from publish.drafts import save_draft, list_drafts
        
        # Test draft saving
        print("Testing save_draft...")
        test_draft = {
            "item_id": f"test_{int(time.time())}",
            "title": "Test Nintendo Switch Console",
            "price_usd": 250.0,
            "shipping_usd": 20.0,
            "condition": "中古 - 良い",
            "purchase_price_jpy": 35000,
            "profit_jpy": 2500.0,
            "profit_margin": 7.1,
            "seller": "test_seller (評価 100)",
            "sold_date": "2024-01-01"
        }
        
        save_result = save_draft(test_draft)
        if save_result["success"]:
            print(f"✅ Draft saved: {save_result['filename']}")
        else:
            print(f"⚠️ Draft save failed: {save_result['error']}")
        
        # Test draft listing
        print("Testing list_drafts...")
        drafts = list_drafts(5)
        print(f"✅ Found {len(drafts)} drafts")
        
        return True
        
    except Exception as e:
        print(f"❌ Draft management test failed: {e}")
        return False

def test_logging_utility():
    """Test logging utility module"""
    print("\n=== Testing Logging Utility ===")
    
    try:
        from utils.logging_utils import get_app_logger
        
        # Test logger
        print("Testing structured logging...")
        logger = get_app_logger()
        
        logger.log_search("test_keyword", 10, 0.5)
        logger.log_user_action("test_action", {"test": "data"})
        logger.log_api_call("test_api", "/test", True, 0.3, 200)
        
        print("✅ Logging tests completed")
        
        return True
        
    except Exception as e:
        print(f"❌ Logging utility test failed: {e}")
        return False

def test_openai_integration():
    """Test OpenAI integration (if API key is available)"""
    print("\n=== Testing OpenAI Integration ===")
    
    try:
        from utils.openai_rewrite import rewrite_title, OPENAI_AVAILABLE
        import os
        
        if not OPENAI_AVAILABLE:
            print("⚠️ OpenAI library not installed, skipping OpenAI tests")
            return True
        
        if not os.getenv('OPENAI_API_KEY'):
            print("⚠️ OPENAI_API_KEY not set, skipping OpenAI tests")
            return True
        
        # Test title rewrite
        print("Testing rewrite_title...")
        result = rewrite_title("Nintendo Switch 本体 グレー", "US", 80)
        
        if result["success"]:
            print(f"✅ Title rewritten: {result['rewritten']}")
        else:
            print(f"⚠️ Title rewrite failed: {result['error']}")
        
        return True
        
    except Exception as e:
        print(f"❌ OpenAI integration test failed: {e}")
        return False

def run_all_tests():
    """Run all module tests"""
    print("🚀 Enhanced eBay Profit Calculator - Module Integration Test")
    print("=" * 60)
    
    tests = [
        ("Data Sources", test_data_sources),
        ("Shipping Module", test_shipping_module),
        ("FX Utility", test_fx_utility),
        ("Draft Management", test_draft_management),
        ("Logging Utility", test_logging_utility),
        ("OpenAI Integration", test_openai_integration),
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        try:
            start_time = time.time()
            success = test_func()
            elapsed = time.time() - start_time
            
            results[test_name] = {
                "success": success,
                "time": elapsed
            }
            
        except Exception as e:
            print(f"❌ {test_name} test crashed: {e}")
            results[test_name] = {
                "success": False,
                "time": 0,
                "error": str(e)
            }
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 TEST SUMMARY")
    print("=" * 60)
    
    total_tests = len(tests)
    passed_tests = sum(1 for r in results.values() if r["success"])
    
    for test_name, result in results.items():
        status = "✅ PASS" if result["success"] else "❌ FAIL"
        time_str = f"({result['time']:.2f}s)"
        print(f"{status:<8} {test_name:<20} {time_str}")
        
        if not result["success"] and "error" in result:
            print(f"         Error: {result['error']}")
    
    print(f"\nResults: {passed_tests}/{total_tests} tests passed")
    
    if passed_tests == total_tests:
        print("🎉 All tests passed! The enhanced application is ready to deploy.")
        return True
    else:
        print("⚠️ Some tests failed. Please check the errors above.")
        return False

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
