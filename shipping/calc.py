"""
日本郵便 配送料金計算モジュール
"""
import pandas as pd
from pathlib import Path
from typing import Dict, Optional, List
import logging

# ロガー設定
logger = logging.getLogger(__name__)

# CSVファイルパス
SHIPPING_DIR = Path(__file__).parent
ZONES_CSV = SHIPPING_DIR / "zones.csv"
RATES_CSV = SHIPPING_DIR / "japan_post_rates.csv"

# データキャッシュ
_zones_cache = None
_rates_cache = None


def _load_zones() -> pd.DataFrame:
    """配送ゾーンデータを読み込み"""
    global _zones_cache
    
    if _zones_cache is None:
        try:
            _zones_cache = pd.read_csv(ZONES_CSV)
            logger.info(f"Loaded shipping zones: {len(_zones_cache)} countries")
        except Exception as e:
            logger.error(f"Error loading zones CSV: {e}")
            # フォールバック用の基本ゾーンデータ
            _zones_cache = pd.DataFrame({
                'country_code': ['US', 'CA', 'GB', 'AU', 'DE'],
                'zone': [1, 1, 3, 2, 3]
            })
    
    return _zones_cache


def _load_rates() -> pd.DataFrame:
    """配送料金データを読み込み"""
    global _rates_cache
    
    if _rates_cache is None:
        try:
            _rates_cache = pd.read_csv(RATES_CSV)
            logger.info(f"Loaded shipping rates: {len(_rates_cache)} rate entries")
        except Exception as e:
            logger.error(f"Error loading rates CSV: {e}")
            # フォールバック用の基本料金データ
            _rates_cache = pd.DataFrame({
                'method': ['ePacket', 'SmallPacket', 'EMS'],
                'zone': [1, 1, 1],
                'weight_min_g': [0, 0, 0],
                'weight_max_g': [2000, 2000, 500],
                'cost_jpy': [1200, 1400, 1800],
                'delivery_days': ['7-14', '7-21', '3-6']
            })
    
    return _rates_cache


def zone(country_code: str) -> int:
    """
    国コードから配送ゾーンを取得
    
    Args:
        country_code: ISO 2文字国コード（例: 'US', 'GB'）
        
    Returns:
        int: 配送ゾーン番号（1-4）
    """
    try:
        zones_df = _load_zones()
        
        # 国コードを大文字に変換
        country_code = country_code.upper()
        
        # ゾーン検索
        zone_row = zones_df[zones_df['country_code'] == country_code]
        
        if not zone_row.empty:
            zone_num = int(zone_row.iloc[0]['zone'])
            logger.debug(f"Zone for {country_code}: {zone_num}")
            return zone_num
        else:
            # デフォルトゾーン（その他の国）
            logger.warning(f"Zone not found for {country_code}, using default zone 4")
            return 4
            
    except Exception as e:
        logger.error(f"Error getting zone for {country_code}: {e}")
        return 4  # デフォルト


def quote(weight_g: int, country_code: str) -> Dict:
    """
    重量と配送先国から最適な配送方法と料金を取得
    
    Args:
        weight_g: 重量（グラム）
        country_code: ISO 2文字国コード
        
    Returns:
        Dict: {"method": str, "cost_jpy": int, "delivery_days": str, "zone": int}
    """
    try:
        # ゾーン取得
        destination_zone = zone(country_code)
        
        # 料金データ読み込み
        rates_df = _load_rates()
        
        # 該当ゾーンと重量範囲で絞り込み
        applicable_rates = rates_df[
            (rates_df['zone'] == destination_zone) &
            (rates_df['weight_min_g'] <= weight_g) &
            (rates_df['weight_max_g'] >= weight_g)
        ]
        
        if applicable_rates.empty:
            # 該当する料金がない場合のフォールバック
            logger.warning(f"No shipping rate found for {weight_g}g to zone {destination_zone}")
            return {
                "method": "Standard",
                "cost_jpy": 2000,  # フォールバック料金
                "delivery_days": "7-21",
                "zone": destination_zone,
                "error": "料金データなし"
            }
        
        # 最安の配送方法を選択
        cheapest = applicable_rates.loc[applicable_rates['cost_jpy'].idxmin()]
        
        result = {
            "method": cheapest['method'],
            "cost_jpy": int(cheapest['cost_jpy']),
            "delivery_days": cheapest['delivery_days'],
            "zone": destination_zone
        }
        
        logger.debug(f"Best shipping for {weight_g}g to {country_code}: {result}")
        return result
        
    except Exception as e:
        logger.error(f"Error calculating shipping quote: {e}")
        return {
            "method": "Error",
            "cost_jpy": 0,
            "delivery_days": "不明",
            "zone": 4,
            "error": str(e)
        }


def get_all_options(weight_g: int, country_code: str) -> List[Dict]:
    """
    指定重量・配送先に対する全配送オプションを取得
    
    Args:
        weight_g: 重量（グラム）
        country_code: ISO 2文字国コード
        
    Returns:
        List[Dict]: 利用可能な配送オプション一覧
    """
    try:
        destination_zone = zone(country_code)
        rates_df = _load_rates()
        
        # 該当する配送オプション
        applicable_rates = rates_df[
            (rates_df['zone'] == destination_zone) &
            (rates_df['weight_min_g'] <= weight_g) &
            (rates_df['weight_max_g'] >= weight_g)
        ]
        
        options = []
        for _, rate in applicable_rates.iterrows():
            option = {
                "method": rate['method'],
                "cost_jpy": int(rate['cost_jpy']),
                "delivery_days": rate['delivery_days'],
                "zone": destination_zone
            }
            options.append(option)
        
        # 料金順にソート
        options.sort(key=lambda x: x['cost_jpy'])
        
        logger.debug(f"Found {len(options)} shipping options for {weight_g}g to {country_code}")
        return options
        
    except Exception as e:
        logger.error(f"Error getting shipping options: {e}")
        return []


def estimate_weight(category: str, title: str) -> int:
    """
    カテゴリとタイトルから商品重量を推定
    
    Args:
        category: 商品カテゴリ
        title: 商品タイトル
        
    Returns:
        int: 推定重量（グラム）
    """
    try:
        # カテゴリベースの重量推定
        category_weights = {
            "Cell Phones & Smartphones": 200,
            "Video Games & Consoles": 800,
            "Cameras & Photo": 600,
            "Consumer Electronics": 500,
            "Toys & Hobbies": 400,
            "Jewelry & Watches": 100,
            "Clothing": 300,
            "Books": 250,
            "Collectibles": 200
        }
        
        # タイトルベースの重量調整
        title_lower = title.lower()
        weight_modifiers = {
            "nintendo switch": 800,
            "iphone": 200,
            "camera": 600,
            "headphone": 300,
            "watch": 100,
            "laptop": 2000,
            "tablet": 500,
            "book": 250,
            "card": 50,
            "figure": 150
        }
        
        # 基本重量
        base_weight = category_weights.get(category, 500)
        
        # タイトルから調整
        for keyword, weight in weight_modifiers.items():
            if keyword in title_lower:
                base_weight = weight
                break
        
        logger.debug(f"Estimated weight for '{title}' ({category}): {base_weight}g")
        return base_weight
        
    except Exception as e:
        logger.error(f"Error estimating weight: {e}")
        return 500  # デフォルト重量


def get_zone_info(country_code: str) -> Optional[Dict]:
    """
    国の詳細ゾーン情報を取得
    
    Args:
        country_code: ISO 2文字国コード
        
    Returns:
        Optional[Dict]: 国情報
    """
    try:
        zones_df = _load_zones()
        country_code = country_code.upper()
        
        country_row = zones_df[zones_df['country_code'] == country_code]
        
        if not country_row.empty:
            row = country_row.iloc[0]
            return {
                "country_code": row['country_code'],
                "country_name_en": row['country_name_en'],
                "country_name_jp": row['country_name_jp'],
                "zone": int(row['zone'])
            }
        else:
            return None
            
    except Exception as e:
        logger.error(f"Error getting zone info: {e}")
        return None


# テスト用関数
def test_shipping_calc():
    """配送計算のテスト"""
    print("=== Shipping Calculation Test ===")
    
    test_cases = [
        {"weight": 500, "country": "US", "description": "iPhone to USA"},
        {"weight": 800, "country": "GB", "description": "Nintendo Switch to UK"},
        {"weight": 200, "country": "AU", "description": "Small item to Australia"},
        {"weight": 1500, "country": "DE", "description": "Heavy item to Germany"},
        {"weight": 300, "country": "CN", "description": "Medium item to China"},
    ]
    
    for case in test_cases:
        print(f"\n{case['description']}:")
        print(f"  Weight: {case['weight']}g, Destination: {case['country']}")
        
        # ゾーン取得
        dest_zone = zone(case['country'])
        print(f"  Zone: {dest_zone}")
        
        # 最適配送
        best_quote = quote(case['weight'], case['country'])
        print(f"  Best option: {best_quote}")
        
        # 全オプション
        all_options = get_all_options(case['weight'], case['country'])
        print(f"  All options ({len(all_options)}):")
        for option in all_options:
            print(f"    - {option['method']}: ¥{option['cost_jpy']} ({option['delivery_days']}日)")


if __name__ == "__main__":
    test_shipping_calc()
