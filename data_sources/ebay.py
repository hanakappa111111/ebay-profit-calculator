"""
eBay データソース抽象化モジュール
"""
import json
import random
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import logging

# ロガー設定
logger = logging.getLogger(__name__)

# モックデータ
MOCK_COMPLETED_ITEMS = [
    {
        "item_id": "265893442181",
        "title": "Nintendo Switch 本体 グレー 付属品完備",
        "price_usd": 220.00,
        "shipping_usd": 20.00,
        "sold_date": "2024-01-15",
        "condition": "中古 - 良い",
        "seller": "gameshop_japan (評価 1520)",
        "image_url": "https://i.ebayimg.com/images/g/XYZabc123def/s-l225.jpg",
        "ebay_url": "https://www.ebay.com/itm/265893442181",
        "category": "Video Games & Consoles",
        "location": "Japan",
        "watchers": 15,
        "bids": 3
    },
    {
        "item_id": "394852963741",
        "title": "Apple iPhone 13 Pro 256GB ゴールド SIMフリー",
        "price_usd": 550.00,
        "shipping_usd": 25.00,
        "sold_date": "2024-01-18",
        "condition": "中古 - 非常に良い",
        "seller": "tech_reseller (評価 3210)",
        "image_url": "https://i.ebayimg.com/images/g/ABCdef456ghi/s-l225.jpg",
        "ebay_url": "https://www.ebay.com/itm/394852963741",
        "category": "Cell Phones & Smartphones",
        "location": "Tokyo, Japan",
        "watchers": 28,
        "bids": 7
    },
    {
        "item_id": "175629384756",
        "title": "SONY WH-1000XM5 ワイヤレスノイズキャンセリングヘッドホン",
        "price_usd": 300.00,
        "shipping_usd": 15.00,
        "sold_date": "2024-01-20",
        "condition": "新品同様",
        "seller": "audio_specialist (評価 985)",
        "image_url": "https://i.ebayimg.com/images/g/JKLmno789pqr/s-l225.jpg",
        "ebay_url": "https://www.ebay.com/itm/175629384756",
        "category": "Consumer Electronics",
        "location": "Osaka, Japan",
        "watchers": 12,
        "bids": 2
    },
    {
        "item_id": "284751963852",
        "title": "LEGO スターウォーズ ミレニアムファルコン 75257",
        "price_usd": 150.00,
        "shipping_usd": 30.00,
        "sold_date": "2024-01-22",
        "condition": "中古 - 可",
        "seller": "toy_collector (評価 422)",
        "image_url": "https://i.ebayimg.com/images/g/STUvwx012yza/s-l225.jpg",
        "ebay_url": "https://www.ebay.com/itm/284751963852",
        "category": "Toys & Hobbies",
        "location": "Kyoto, Japan",
        "watchers": 8,
        "bids": 1
    },
    {
        "item_id": "155847296384",
        "title": "Canon EOS R6 Mark II ミラーレス一眼カメラ ボディのみ",
        "price_usd": 1250.00,
        "shipping_usd": 40.00,
        "sold_date": "2024-01-25",
        "condition": "新品",
        "seller": "camera_expert (評価 5210)",
        "image_url": "https://i.ebayimg.com/images/g/BCDefg345hij/s-l225.jpg",
        "ebay_url": "https://www.ebay.com/itm/155847296384",
        "category": "Cameras & Photo",
        "location": "Nagoya, Japan",
        "watchers": 35,
        "bids": 12
    },
    {
        "item_id": "265742158963",
        "title": "Rolex Submariner Date 116610LN 自動巻 メンズ",
        "price_usd": 8500.00,
        "shipping_usd": 50.00,
        "sold_date": "2024-01-28",
        "condition": "中古 - 非常に良い",
        "seller": "luxury_watches (評価 892)",
        "image_url": "https://i.ebayimg.com/images/g/KLMnop678qrs/s-l225.jpg",
        "ebay_url": "https://www.ebay.com/itm/265742158963",
        "category": "Jewelry & Watches",
        "location": "Tokyo, Japan",
        "watchers": 67,
        "bids": 25
    },
    {
        "item_id": "374839562741",
        "title": "Pokemon Card ポケモンカード 旧裏面 リザードン",
        "price_usd": 380.00,
        "shipping_usd": 10.00,
        "sold_date": "2024-01-30",
        "condition": "中古 - 良い",
        "seller": "card_trader_jp (評価 1876)",
        "image_url": "https://i.ebayimg.com/images/g/TUVwxy901zab/s-l225.jpg",
        "ebay_url": "https://www.ebay.com/itm/374839562741",
        "category": "Toys & Hobbies",
        "location": "Fukuoka, Japan",
        "watchers": 45,
        "bids": 18
    }
]

# キーワードマッピング（検索機能強化用）
KEYWORD_MAPPING = {
    "nintendo": ["Nintendo", "Switch", "ゲーム", "任天堂"],
    "iphone": ["iPhone", "Apple", "スマートフォン", "携帯"],
    "sony": ["SONY", "ソニー", "ヘッドホン", "カメラ"],
    "lego": ["LEGO", "レゴ", "おもちゃ", "ブロック"],
    "canon": ["Canon", "キヤノン", "カメラ", "一眼"],
    "rolex": ["Rolex", "ロレックス", "腕時計", "時計"],
    "pokemon": ["Pokemon", "ポケモン", "カード", "トレーディング"],
    "camera": ["カメラ", "Camera", "Canon", "Sony", "Nikon"],
    "watch": ["腕時計", "時計", "Watch", "Rolex", "Seiko"],
    "game": ["ゲーム", "Game", "Nintendo", "PlayStation", "Xbox"]
}


def search_completed_items(keyword: str, limit: int = 20) -> List[Dict]:
    """
    完了した取引アイテムを検索（モックデータ使用）
    
    Args:
        keyword: 検索キーワード
        limit: 取得件数上限
        
    Returns:
        List[Dict]: 検索結果のリスト
    """
    try:
        logger.info(f"Searching completed items for keyword: {keyword}")
        
        if not keyword.strip():
            return []
        
        # キーワード正規化
        keyword_lower = keyword.lower()
        
        # 基本検索
        results = []
        for item in MOCK_COMPLETED_ITEMS:
            # タイトル検索
            if keyword_lower in item["title"].lower():
                results.append(item.copy())
                continue
            
            # カテゴリ検索
            if keyword_lower in item["category"].lower():
                results.append(item.copy())
                continue
            
            # キーワードマッピング検索
            for key, related_terms in KEYWORD_MAPPING.items():
                if keyword_lower in key or any(term.lower() in keyword_lower for term in related_terms):
                    if any(term.lower() in item["title"].lower() for term in related_terms):
                        results.append(item.copy())
                        break
        
        # 結果が少ない場合は類似アイテムを生成
        if len(results) < 3:
            results.extend(_generate_similar_items(keyword, 5 - len(results)))
        
        # 価格ランダム化（リアルさのため）
        for item in results:
            variation = random.uniform(0.9, 1.1)
            item["price_usd"] = round(item["price_usd"] * variation, 2)
            item["shipping_usd"] = round(item["shipping_usd"] * variation, 2)
        
        # 売れた日をランダム化
        for item in results:
            days_ago = random.randint(1, 30)
            sold_date = datetime.now() - timedelta(days=days_ago)
            item["sold_date"] = sold_date.strftime("%Y-%m-%d")
        
        # 結果をlimitに制限
        results = results[:limit]
        
        logger.info(f"Found {len(results)} items for keyword: {keyword}")
        return results
        
    except Exception as e:
        logger.error(f"Error searching completed items: {e}")
        return []


def get_item_detail(item_id: str) -> Optional[Dict]:
    """
    アイテムの詳細情報を取得（モックデータ使用）
    
    Args:
        item_id: eBayアイテムID
        
    Returns:
        Optional[Dict]: アイテム詳細情報
    """
    try:
        logger.info(f"Getting item detail for ID: {item_id}")
        
        # モックデータから検索
        for item in MOCK_COMPLETED_ITEMS:
            if item["item_id"] == item_id:
                # 詳細情報を追加
                detail = item.copy()
                detail.update({
                    "description": f"詳細説明: {item['title']}\n\n商品の状態: {item['condition']}\n配送元: {item['location']}",
                    "shipping_options": [
                        {"method": "Standard", "cost_usd": item["shipping_usd"], "days": "7-14"},
                        {"method": "Express", "cost_usd": item["shipping_usd"] * 1.5, "days": "3-5"},
                        {"method": "Economy", "cost_usd": item["shipping_usd"] * 0.7, "days": "14-21"}
                    ],
                    "return_policy": "30日以内返品可能",
                    "payment_methods": ["PayPal", "Credit Card"],
                    "item_specifics": {
                        "Brand": _extract_brand(item["title"]),
                        "Model": _extract_model(item["title"]),
                        "Color": _extract_color(item["title"]),
                        "Condition": item["condition"]
                    }
                })
                
                logger.info(f"Found item detail for ID: {item_id}")
                return detail
        
        logger.warning(f"Item not found for ID: {item_id}")
        return None
        
    except Exception as e:
        logger.error(f"Error getting item detail: {e}")
        return None


def _generate_similar_items(keyword: str, count: int) -> List[Dict]:
    """類似アイテムを生成"""
    similar_items = []
    
    for i in range(count):
        base_item = random.choice(MOCK_COMPLETED_ITEMS)
        similar_item = base_item.copy()
        
        # タイトルにキーワードを含める
        similar_item["title"] = f"{keyword} {base_item['title']}"
        similar_item["item_id"] = f"gen{random.randint(100000000000, 999999999999)}"
        
        # 価格を調整
        price_factor = random.uniform(0.7, 1.3)
        similar_item["price_usd"] = round(base_item["price_usd"] * price_factor, 2)
        
        similar_items.append(similar_item)
    
    return similar_items


def _extract_brand(title: str) -> str:
    """タイトルからブランドを抽出"""
    brands = ["Apple", "Sony", "Canon", "Nintendo", "LEGO", "Rolex", "Pokemon"]
    for brand in brands:
        if brand.lower() in title.lower():
            return brand
    return "Generic"


def _extract_model(title: str) -> str:
    """タイトルからモデルを抽出"""
    words = title.split()
    for i, word in enumerate(words):
        if any(char.isdigit() for char in word) and len(word) > 2:
            return word
    return "N/A"


def _extract_color(title: str) -> str:
    """タイトルから色を抽出"""
    colors = ["黒", "白", "赤", "青", "緑", "ゴールド", "シルバー", "グレー", "Black", "White", "Red", "Blue", "Gold", "Silver", "Gray"]
    for color in colors:
        if color.lower() in title.lower():
            return color
    return "N/A"


# テスト用関数
def test_search():
    """検索機能のテスト"""
    keywords = ["Nintendo", "iPhone", "camera", "watch"]
    
    for keyword in keywords:
        print(f"\n=== Testing keyword: {keyword} ===")
        results = search_completed_items(keyword, 3)
        for item in results:
            print(f"- {item['title']} (${item['price_usd']})")


if __name__ == "__main__":
    test_search()
