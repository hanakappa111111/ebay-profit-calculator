import streamlit as st
import pandas as pd
import requests
import json
import re
from typing import Dict, Optional, Tuple, List
from datetime import datetime
import io
import base64
from urllib.parse import quote

# Import our custom modules
from config import SHIPPING_RATES, CURRENCY_CONFIG, APP_CONFIG
from ebay_api import ebay_api

# Configure page
st.set_page_config(
    page_title=APP_CONFIG['title'],
    page_icon="💰",
    layout="wide"
)

# Load shipping rates
@st.cache_data
def load_shipping_rates():
    """Load Japan Post shipping rates"""
    return SHIPPING_RATES

def calculate_shipping_cost(weight_g: int, method: str, length_cm: float = 0, width_cm: float = 0, height_cm: float = 0) -> int:
    """Calculate shipping cost based on weight, dimensions and method"""
    rates = load_shipping_rates()
    
    if method not in rates:
        return 0
    
    rate_table = rates[method]
    
    # Calculate base cost by weight
    if weight_g <= 500:
        base_cost = rate_table["up_to_500g"]
    elif weight_g <= 1000:
        base_cost = rate_table["501_to_1000g"]
    elif weight_g <= 1500:
        base_cost = rate_table["1001_to_1500g"]
    elif weight_g <= 2000:
        base_cost = rate_table["1501_to_2000g"]
    else:
        base_cost = rate_table["over_2000g"]
    
    # Calculate dimensional weight (length x width x height / 5000 for international shipping)
    if length_cm > 0 and width_cm > 0 and height_cm > 0:
        dimensional_weight = (length_cm * width_cm * height_cm) / 5000  # grams
        
        # Use the higher of actual weight or dimensional weight
        effective_weight = max(weight_g, dimensional_weight)
        
        # Recalculate if dimensional weight is higher
        if effective_weight > weight_g:
            if effective_weight <= 500:
                base_cost = rate_table["up_to_500g"]
            elif effective_weight <= 1000:
                base_cost = rate_table["501_to_1000g"]
            elif effective_weight <= 1500:
                base_cost = rate_table["1001_to_1500g"]
            elif effective_weight <= 2000:
                base_cost = rate_table["1501_to_2000g"]
            else:
                base_cost = rate_table["over_2000g"]
        
        # Add size surcharge for oversized packages
        max_dimension = max(length_cm, width_cm, height_cm)
        if max_dimension > 60:  # Over 60cm in any dimension
            base_cost = int(base_cost * 1.5)  # 50% surcharge
        elif max_dimension > 40:  # Over 40cm in any dimension
            base_cost = int(base_cost * 1.2)  # 20% surcharge
    
    return int(base_cost)

@st.cache_data
def get_currency_rate() -> float:
    """Get current JPY to USD exchange rate"""
    try:
        # Try to fetch live rate (you can replace with your preferred API)
        response = requests.get("https://api.exchangerate-api.com/v4/latest/USD")
        if response.status_code == 200:
            data = response.json()
            if 'rates' in data and 'JPY' in data['rates']:
                return data['rates']['JPY']
    except:
        pass
    
    # Fallback to configured default rate
    return CURRENCY_CONFIG['default_jpy_usd_rate']

def calculate_profit(selling_price: float, fee_rate: float, shipping_cost: int, supplier_cost: float) -> Tuple[float, float]:
    """Calculate profit amount and margin"""
    total_fees = selling_price * fee_rate
    total_costs = supplier_cost + total_fees + shipping_cost
    profit = selling_price - total_costs
    margin = (profit / selling_price) * 100 if selling_price > 0 else 0
    
    return profit, margin

# Mock eBay search data
MOCK_SEARCH_DATA = [
    {
        "タイトル": "Nintendo Switch 本体 グレー",
        "価格_USD": 220,
        "送料_USD": 20,
        "売れた日": "2025-01-15",
        "商品状態": "中古 - 良い",
        "出品者": "seller123 (評価 1520)"
    },
    {
        "タイトル": "Apple iPhone 13 Pro 256GB ゴールド",
        "価格_USD": 550,
        "送料_USD": 25,
        "売れた日": "2025-01-18",
        "商品状態": "中古 - 非常に良い",
        "出品者": "best_seller (評価 3210)"
    },
    {
        "タイトル": "SONY WH-1000XM5 ヘッドホン",
        "価格_USD": 300,
        "送料_USD": 15,
        "売れた日": "2025-01-20",
        "商品状態": "新品同様",
        "出品者": "sound_japan (評価 985)"
    },
    {
        "タイトル": "LEGO スターウォーズ ミレニアムファルコン",
        "価格_USD": 150,
        "送料_USD": 30,
        "売れた日": "2025-01-22",
        "商品状態": "中古 - 可",
        "出品者": "lego_master (評価 422)"
    },
    {
        "タイトル": "Canon EOS R6 Mark II ボディ",
        "価格_USD": 1250,
        "送料_USD": 40,
        "売れた日": "2025-01-25",
        "商品状態": "新品",
        "出品者": "camera_pro (評価 5210)"
    }
]

@st.cache_data
def get_usd_to_jpy_rate() -> float:
    """Get USD to JPY exchange rate"""
    try:
        response = requests.get("https://api.exchangerate.host/latest?base=USD&symbols=JPY")
        if response.status_code == 200:
            data = response.json()
            if 'rates' in data and 'JPY' in data['rates']:
                return data['rates']['JPY']
    except:
        pass
    
    # Fallback to default rate
    return 150.0

def ebay_search_real(keyword: str) -> List[Dict]:
    """Real eBay search function using existing API"""
    if not keyword.strip():
        return MOCK_SEARCH_DATA
    
    try:
        # Try real eBay API search first
        real_results = ebay_api.search_items(keyword, limit=15)
        
        if real_results:
            st.success(f"✅ 実際のeBayデータを{len(real_results)}件取得しました！")
            return real_results
        
        # Fallback to enhanced mock data if API fails
        st.warning("⚠️ eBay APIからデータを取得できませんでした。拡張モックデータを表示します。")
        enhanced_results = []
        
        # Add more realistic mock data based on common keywords
        keyword_lower = keyword.lower()
        
        if 'nintendo' in keyword_lower or 'switch' in keyword_lower:
            enhanced_results.extend([
                {"タイトル": "Nintendo Switch OLED モデル ホワイト", "価格_USD": 280, "送料_USD": 25, "売れた日": "2025-01-26", "商品状態": "新品", "出品者": "game_seller (評価 2100)"},
                {"タイトル": "Nintendo Switch Lite ターコイズ", "価格_USD": 180, "送料_USD": 20, "売れた日": "2025-01-25", "商品状態": "中古 - 良い", "出品者": "retro_games (評価 890)"},
                {"タイトル": "Nintendo Switch Pro コントローラー", "価格_USD": 65, "送料_USD": 15, "売れた日": "2025-01-24", "商品状態": "新品同様", "出品者": "controller_shop (評価 1450)"}
            ])
        
        if 'iphone' in keyword_lower or 'apple' in keyword_lower:
            enhanced_results.extend([
                {"タイトル": "iPhone 14 Pro Max 128GB ディープパープル", "価格_USD": 850, "送料_USD": 30, "売れた日": "2025-01-26", "商品状態": "新品", "出品者": "apple_store_jp (評価 5500)"},
                {"タイトル": "iPhone 13 mini 256GB ピンク", "価格_USD": 480, "送料_USD": 25, "売れた日": "2025-01-25", "商品状態": "中古 - 非常に良い", "出品者": "phone_expert (評価 3200)"},
                {"タイトル": "iPhone 12 64GB ブラック", "価格_USD": 320, "送料_USD": 20, "売れた日": "2025-01-24", "商品状態": "中古 - 良い", "出品者": "mobile_reseller (評価 1800)"}
            ])
        
        if 'sony' in keyword_lower or 'headphone' in keyword_lower:
            enhanced_results.extend([
                {"タイトル": "Sony WH-1000XM4 ワイヤレスヘッドホン ブラック", "価格_USD": 250, "送料_USD": 20, "売れた日": "2025-01-26", "商品状態": "中古 - 良い", "出品者": "audio_pro (評価 2800)"},
                {"タイトル": "Sony WF-1000XM4 完全ワイヤレスイヤホン", "価格_USD": 180, "送料_USD": 15, "売れた日": "2025-01-25", "商品状態": "新品同様", "出品者": "earphone_master (評価 1200)"},
                {"タイトル": "Sony α7 III ミラーレス一眼カメラ ボディ", "価格_USD": 1500, "送料_USD": 45, "売れた日": "2025-01-24", "商品状態": "中古 - 非常に良い", "出品者": "camera_world (評価 4200)"}
            ])
        
        if 'canon' in keyword_lower or 'camera' in keyword_lower:
            enhanced_results.extend([
                {"タイトル": "Canon EOS R5 ミラーレス一眼 ボディ", "価格_USD": 2800, "送料_USD": 50, "売れた日": "2025-01-26", "商品状態": "新品", "出品者": "photo_gear (評価 6100)"},
                {"タイトル": "Canon EF 24-70mm f/2.8L II USM レンズ", "価格_USD": 1200, "送料_USD": 35, "売れた日": "2025-01-25", "商品状態": "中古 - 良い", "出品者": "lens_specialist (評価 3400)"},
                {"タイトル": "Canon PowerShot G7X Mark III コンパクトデジカメ", "価格_USD": 450, "送料_USD": 25, "売れた日": "2025-01-24", "商品状態": "新品同様", "出品者": "compact_cam (評価 1900)"}
            ])
        
        if 'lego' in keyword_lower:
            enhanced_results.extend([
                {"タイトル": "LEGO Creator Expert 10264 コーナーガレージ", "価格_USD": 180, "送料_USD": 35, "売れた日": "2025-01-26", "商品状態": "新品", "出品者": "brick_builder (評価 2500)"},
                {"タイトル": "LEGO テクニック 42115 ランボルギーニ", "価格_USD": 320, "送料_USD": 40, "売れた日": "2025-01-25", "商品状態": "新品同様", "出品者": "technic_fan (評価 1600)"},
                {"タイトル": "LEGO ハリーポッター 76391 ホグワーツ城", "価格_USD": 380, "送料_USD": 45, "売れた日": "2025-01-24", "商品状態": "中古 - 良い", "出品者": "wizard_bricks (評価 980)"}
            ])
        
        # If no specific keyword matches, return original mock data
        if not enhanced_results:
            # Filter original mock data
            for item in MOCK_SEARCH_DATA:
                if keyword_lower in item["タイトル"].lower():
                    enhanced_results.append(item)
            
            if not enhanced_results:
                enhanced_results = MOCK_SEARCH_DATA
        
        return enhanced_results
        
    except Exception as e:
        # Fallback to original mock data on any error
        return MOCK_SEARCH_DATA

def calculate_research_profit(selling_price_usd: float, shipping_usd: float, 
                            purchase_price_jpy: float, exchange_rate: float) -> Tuple[float, float]:
    """Calculate profit for research items"""
    if purchase_price_jpy <= 0:
        return 0.0, 0.0
    
    # Convert to JPY
    selling_price_jpy = selling_price_usd * exchange_rate
    shipping_jpy = shipping_usd * exchange_rate
    
    # Calculate fees (13% fixed)
    fees_jpy = selling_price_jpy * 0.13
    
    # Calculate profit
    profit_jpy = selling_price_jpy - purchase_price_jpy - shipping_jpy - fees_jpy
    profit_margin = (profit_jpy / purchase_price_jpy) * 100 if purchase_price_jpy > 0 else 0
    
    return profit_jpy, profit_margin

def main():
    st.title("💰 eBay転売利益計算ツール")
    st.subheader("日本からeBayへの転売利益を簡単計算！")
    
    # Create tabs
    tab1, tab2 = st.tabs(["利益計算", "リサーチ"])
    
    with tab1:
        profit_calculator_tab()
    
    with tab2:
        research_tab()

def profit_calculator_tab():
    """Original profit calculator functionality"""
    
    # Add explanation for profit calculator
    st.info("""
    **使い方：**
    1. eBayで販売中の商品URLまたは商品IDを入力
    2. あなたがその商品を仕入れた（購入した）価格を入力
    3. 商品重量と配送方法を選択
    4. 「利益を計算する」ボタンをクリック
    
    ⚠️ **仕入価格**は、eBayでの販売価格ではなく、あなたが商品を購入した価格です。
    
    💡 **テスト用**: データ取得に問題がある場合は、商品IDに「test」と入力すると、サンプルデータで動作を確認できます。
    """)
    
    # Initialize session state for results
    if 'results_df' not in st.session_state:
        st.session_state.results_df = pd.DataFrame(columns=[
            '商品ID', '商品タイトル', 'eBay販売価格 (USD)', '仕入価格 (JPY)', 
            '配送方法', '送料 (JPY)', 'eBay手数料 (USD)', 
            '利益 (USD)', '利益率 (%)', '計算日時'
        ])
    
    # Main input section
    col1, col2 = st.columns(2)
    
    with col1:
        st.header("📝 商品情報")
        ebay_input = st.text_input("eBay商品URLまたは商品ID", 
                                  placeholder="eBayのURLまたは数字の商品IDを入力")
        
        # Add button to fetch product info without calculating profit
        if st.button("🔍 商品情報を取得", help="重量・サイズなどの商品情報のみを取得します"):
            if ebay_input:
                with st.spinner("eBayから商品情報を取得中..."):
                    try:
                        item_data = ebay_api.get_item_details(ebay_input)
                        
                        # Show debug info
                        with st.expander("🔧 デバッグ情報"):
                            st.write("**入力値:**", ebay_input)
                            st.write("**取得データ:**", item_data)
                            if hasattr(ebay_api, 'last_debug_info'):
                                st.write("**デバッグ詳細:**", ebay_api.last_debug_info)
                                
                    except Exception as e:
                        st.error(f"エラーが発生しました: {e}")
                        item_data = None
                
                if item_data and isinstance(item_data, dict):
                    # Update session state with auto-detected dimensions
                    if item_data.get('shipping_weight'):
                        st.session_state.auto_weight = item_data['shipping_weight']
                    
                    if item_data.get('dimensions'):
                        dimensions = item_data['dimensions']
                        st.session_state.auto_dimensions = {
                            'length': dimensions.get('length'),
                            'width': dimensions.get('width'),
                            'height': dimensions.get('height')
                        }
                    
                    # Display fetched information
                    st.success(f"✅ 商品情報取得成功!")
                    st.write(f"**商品名**: {item_data.get('title', 'N/A')}")
                    st.write(f"**販売価格**: ${item_data.get('price', 0):.2f}")
                    
                    # Show detected dimensions
                    auto_info = []
                    if item_data.get('shipping_weight'):
                        auto_info.append(f"重量: {item_data['shipping_weight']}g")
                    
                    if item_data.get('dimensions'):
                        dimensions = item_data['dimensions']
                        if dimensions.get('length') and dimensions.get('width') and dimensions.get('height'):
                            auto_info.append(f"サイズ: {dimensions['length']:.1f} x {dimensions['width']:.1f} x {dimensions['height']:.1f} cm")
                        elif any([dimensions.get('length'), dimensions.get('width'), dimensions.get('height')]):
                            size_parts = []
                            if dimensions.get('length'): size_parts.append(f"長さ{dimensions['length']:.1f}cm")
                            if dimensions.get('width'): size_parts.append(f"幅{dimensions['width']:.1f}cm") 
                            if dimensions.get('height'): size_parts.append(f"高さ{dimensions['height']:.1f}cm")
                            auto_info.append("サイズ: " + ", ".join(size_parts))
                    
                    if auto_info:
                        st.info(f"🎯 自動検出: {' / '.join(auto_info)}")
                    else:
                        st.warning("⚠️ 重量・サイズ情報が見つかりませんでした。下記で手動入力してください。")
                    
                    st.rerun()  # Refresh to update the input fields
                else:
                    st.error("🚫 商品情報の取得に失敗しました。URLまたは商品IDを確認してください。")
            else:
                st.warning("⚠️ 商品URLまたは商品IDを入力してください。")
        
        supplier_price = st.number_input("仕入価格（日本円）", 
                                       min_value=0, step=100, value=0, format="%d",
                                       help="あなたが商品を仕入れた（購入した）価格を日本円で入力してください。eBayでの販売価格ではありません。")
    
    with col2:
        st.header("🚚 配送設定")
        
        # Initialize session state for dimensions
        if 'auto_weight' not in st.session_state:
            st.session_state.auto_weight = 500
        if 'auto_dimensions' not in st.session_state:
            st.session_state.auto_dimensions = {'length': None, 'width': None, 'height': None}
        
        # Weight input with auto-detected value
        weight = st.number_input("商品重量（グラム）", 
                               min_value=1, max_value=10000, 
                               value=st.session_state.auto_weight,
                               help="eBayから自動取得された重量です。必要に応じて調整してください")
        
        # Dimension inputs
        col2a, col2b, col2c = st.columns(3)
        with col2a:
            length = st.number_input("長さ（cm）", 
                                   min_value=0.0, 
                                   value=st.session_state.auto_dimensions.get('length', 0.0) or 0.0,
                                   help="商品の長さ（自動取得または手動入力）")
        with col2b:
            width = st.number_input("幅（cm）", 
                                  min_value=0.0,
                                  value=st.session_state.auto_dimensions.get('width', 0.0) or 0.0,
                                  help="商品の幅（自動取得または手動入力）")
        with col2c:
            height = st.number_input("高さ（cm）", 
                                   min_value=0.0,
                                   value=st.session_state.auto_dimensions.get('height', 0.0) or 0.0,
                                   help="商品の高さ（自動取得または手動入力）")
        
        shipping_method = st.selectbox("配送方法", 
                                     [
                                         "EMS（国際スピード郵便）",
                                         "国際eパケット",
                                         "ヤマト運輸",
                                         "佐川急便",
                                         "DHL Express",
                                         "FedEx"
                                     ])
    
    # Calculate button
    if st.button("💰 利益を計算する", type="primary"):
        if not ebay_input or supplier_price <= 0:
            st.error("eBayのURLまたは商品IDと仕入価格の両方を入力してください")
            return
        
        with st.spinner("eBayから商品データを取得中..."):
            # Show debug info in expander
            debug_container = st.empty()
            
            item_data = ebay_api.get_item_details(ebay_input)
        
        if not item_data:
            st.error("eBayの商品データを取得できませんでした。URLまたは商品IDを確認してもう一度お試しください。")
            
            # Show debug information
            with st.expander("🔧 デバッグ情報（開発者向け）"):
                st.write("**抽出されたItem ID:**", ebay_api.extract_item_id(ebay_input))
                st.write("**入力URL/ID:**", ebay_input)
                st.write("**考えられる原因:**")
                st.write("- eBayがアクセスをブロックしている")
                st.write("- 商品が存在しないまたは削除されている") 
                st.write("- URLの形式が対応していない")
                st.write("- 一時的なネットワークエラー")
            return
        
        # Update session state with auto-detected dimensions
        if item_data.get('shipping_weight'):
            st.session_state.auto_weight = item_data['shipping_weight']
        
        if item_data.get('dimensions'):
            dimensions = item_data['dimensions']
            st.session_state.auto_dimensions = {
                'length': dimensions.get('length'),
                'width': dimensions.get('width'),
                'height': dimensions.get('height')
            }
            
            # Show what was auto-detected
            auto_info = []
            if dimensions.get('weight'):
                auto_info.append(f"重量: {dimensions['weight']}g")
            if dimensions.get('length') and dimensions.get('width') and dimensions.get('height'):
                auto_info.append(f"サイズ: {dimensions['length']:.1f} x {dimensions['width']:.1f} x {dimensions['height']:.1f} cm")
            elif any([dimensions.get('length'), dimensions.get('width'), dimensions.get('height')]):
                size_parts = []
                if dimensions.get('length'): size_parts.append(f"長さ{dimensions['length']:.1f}cm")
                if dimensions.get('width'): size_parts.append(f"幅{dimensions['width']:.1f}cm") 
                if dimensions.get('height'): size_parts.append(f"高さ{dimensions['height']:.1f}cm")
                auto_info.append("サイズ: " + ", ".join(size_parts))
            
            if auto_info:
                st.success(f"🎯 自動取得成功: {' / '.join(auto_info)}")
            else:
                st.warning("⚠️ 重量・サイズ情報が見つかりませんでした。手動で入力してください。")
        
        st.info("💡 上記の配送設定で重量・サイズを確認・調整してから再計算してください。")
        
        # Calculate shipping cost - convert method name back to English for calculation
        method_mapping = {
            "EMS（国際スピード郵便）": "EMS",
            "国際eパケット": "SAL",  # eパケットはSAL相当の料金
            "ヤマト運輸": "Air",  # 航空便相当
            "佐川急便": "Air",  # 航空便相当
            "DHL Express": "EMS",  # EMS相当の料金
            "FedEx": "EMS"  # EMS相当の料金
        }
        english_method = method_mapping.get(shipping_method, "Surface")
        shipping_cost_jpy = calculate_shipping_cost(weight, english_method, length, width, height)
        
        # Get current exchange rate
        usd_jpy_rate = get_currency_rate()
        
        # Calculate profit
        selling_price = item_data['price']
        fee_rate = item_data.get('fee_rate', 0.1275)
        ebay_fees = selling_price * fee_rate
        
        # Convert costs to USD
        shipping_cost_usd = shipping_cost_jpy / usd_jpy_rate
        supplier_cost_usd = supplier_price / usd_jpy_rate
        
        profit_usd, margin_percent = calculate_profit(
            selling_price, fee_rate, shipping_cost_usd, supplier_cost_usd
        )
        
        # Display results
        st.header("📊 計算結果")
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("販売価格", f"${selling_price:.2f}")
        with col2:
            st.metric("総コスト", f"${supplier_cost_usd + ebay_fees + shipping_cost_usd:.2f}")
        with col3:
            st.metric("利益", f"${profit_usd:.2f}", 
                     delta=f"{margin_percent:.1f}%" if profit_usd > 0 else None)
        with col4:
            st.metric("利益率", f"{margin_percent:.1f}%")
        
        # Detailed breakdown
        st.subheader("💡 詳細内訳")
        # Calculate dimensional weight for display
        dimensional_weight = 0
        if length > 0 and width > 0 and height > 0:
            dimensional_weight = (length * width * height) / 5000
        
        breakdown_data = {
            "項目": [
                "eBay販売価格（米ドル）",
                "仕入コスト（円→ドル）",
                "eBay手数料（米ドル）",
                "送料（円→ドル）",
                "商品重量",
                "サイズ（長x幅x高）",
                "容積重量",
                "最終利益（米ドル）",
                "利益率（％）"
            ],
            "金額・詳細": [
                f"${selling_price:.2f}",
                f"${supplier_cost_usd:.2f}",
                f"${ebay_fees:.2f}",
                f"${shipping_cost_usd:.2f} (¥{shipping_cost_jpy:,})",
                f"{weight:,}g",
                f"{length:.1f} x {width:.1f} x {height:.1f} cm" if all([length, width, height]) else "未設定",
                f"{dimensional_weight:.0f}g" if dimensional_weight > 0 else "計算不可",
                f"${profit_usd:.2f}",
                f"{margin_percent:.1f}%"
            ]
        }
        
        st.table(pd.DataFrame(breakdown_data))
        
        # Add to results history
        new_row = pd.DataFrame([{
            '商品ID': item_data.get('item_id', 'N/A'),
            '商品タイトル': item_data['title'],
            'eBay販売価格 (USD)': f"${selling_price:.2f}",
            '仕入価格 (JPY)': f"¥{supplier_price:,.0f}",
            '配送方法': shipping_method,
            '送料 (JPY)': f"¥{shipping_cost_jpy:,}",
            'eBay手数料 (USD)': f"${ebay_fees:.2f}",
            '利益 (USD)': f"${profit_usd:.2f}",
            '利益率 (%)': f"{margin_percent:.1f}%",
            '計算日時': datetime.now().strftime("%Y-%m-%d %H:%M")
        }])
        
        st.session_state.results_df = pd.concat([new_row, st.session_state.results_df], 
                                              ignore_index=True)
    
    # Results history
    if not st.session_state.results_df.empty:
        st.header("📋 計算履歴")
        st.dataframe(st.session_state.results_df, use_container_width=True)
        
        # CSV download
        csv_buffer = io.StringIO()
        st.session_state.results_df.to_csv(csv_buffer, index=False)
        csv_data = csv_buffer.getvalue()
        
        st.download_button(
            label="📥 結果をCSVでダウンロード",
            data=csv_data,
            file_name=f"ebay利益分析_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
            mime="text/csv"
        )
        
        # Clear history button
        if st.button("🗑️ 履歴をクリア"):
            st.session_state.results_df = pd.DataFrame(columns=[
                '商品ID', '商品タイトル', 'eBay販売価格 (USD)', '仕入価格 (JPY)', 
                '配送方法', '送料 (JPY)', 'eBay手数料 (USD)', 
                '利益 (USD)', '利益率 (%)', '計算日時'
            ])
            st.rerun()

def research_tab():
    """Research tab functionality"""
    st.header("🔍 商品リサーチ")
    
    # Explanation for research tab
    st.info("""
    **リサーチ機能の使い方：**
    1. キーワードを入力して商品を検索
    2. 検索結果から気になる商品をチェック
    3. 仕入れ値を入力して利益を計算
    4. 選択した商品をCSVダウンロードまたは下書き保存
    
    💡 **検索のコツ**: 「Nintendo」「iPhone」「Canon」「Sony」「LEGO」などのキーワードを試してください
    💡 **為替レート**: USD→JPY変換は最新レートを自動取得します
    
    🚀 **リアルデータ対応**: eBay Finding APIを使用して実際の商品データを取得します！
    """)
    
    # Search section
    col1, col2 = st.columns([3, 1])
    with col1:
        keyword = st.text_input("キーワードを入力", placeholder="例: Nintendo Switch, iPhone, Canon")
    with col2:
        st.write("")
        st.write("")
        search_button = st.button("🔍 検索", type="primary")
    
    # Initialize session state for research
    if 'research_results' not in st.session_state:
        st.session_state.research_results = pd.DataFrame()
    if 'exchange_rate' not in st.session_state:
        st.session_state.exchange_rate = get_usd_to_jpy_rate()
    
    # Display current exchange rate
    col1, col2 = st.columns([2, 1])
    with col2:
        st.metric("為替レート", f"1 USD = {st.session_state.exchange_rate:.1f} JPY")
    
    # Perform search
    if search_button or keyword:
        search_results = ebay_search_real(keyword if keyword else "")
        
        if search_results:
            # Prepare data for display
            display_data = []
            for item in search_results:
                # Convert to JPY
                price_jpy = item["価格_USD"] * st.session_state.exchange_rate
                shipping_jpy = item["送料_USD"] * st.session_state.exchange_rate
                
                display_data.append({
                    "チェック": False,
                    "タイトル": item["タイトル"],
                    "価格": f"${item['価格_USD']:.0f} (¥{price_jpy:,.0f})",
                    "送料": f"${item['送料_USD']:.0f} (¥{shipping_jpy:,.0f})",
                    "売れた日": item["売れた日"],
                    "商品状態": item["商品状態"],
                    "出品者": item["出品者"],
                    "仕入れ値入力": 0,
                    "利益額": 0.0,
                    "利益率": 0.0,
                    "_価格_USD": item["価格_USD"],
                    "_送料_USD": item["送料_USD"]
                })
            
            st.session_state.research_results = pd.DataFrame(display_data)
    
    # Display results table
    if not st.session_state.research_results.empty:
        st.subheader(f"検索結果 ({len(st.session_state.research_results)}件)")
        
        # Configure column types for data editor
        column_config = {
            "チェック": st.column_config.CheckboxColumn(
                "チェック",
                help="選択する商品にチェックを入れてください",
                default=False,
            ),
            "タイトル": st.column_config.TextColumn(
                "タイトル",
                help="商品タイトル",
                max_chars=50,
            ),
            "価格": st.column_config.TextColumn(
                "価格",
                help="販売価格（USD / 円換算）",
            ),
            "送料": st.column_config.TextColumn(
                "送料", 
                help="送料（USD / 円換算）",
            ),
            "売れた日": st.column_config.DateColumn(
                "売れた日",
                help="商品が売れた日付",
            ),
            "商品状態": st.column_config.TextColumn(
                "商品状態",
                help="商品の状態",
            ),
            "出品者": st.column_config.TextColumn(
                "出品者",
                help="出品者情報（評価数含む）",
            ),
            "仕入れ値入力": st.column_config.NumberColumn(
                "仕入れ値入力 (円)",
                help="仕入れ値を円で入力してください",
                min_value=0,
                max_value=1000000,
                step=100,
                format="¥%d",
            ),
            "利益額": st.column_config.NumberColumn(
                "利益額 (円)",
                help="計算された利益額",
                format="¥%.0f",
                disabled=True,
            ),
            "利益率": st.column_config.NumberColumn(
                "利益率 (%)",
                help="計算された利益率",
                format="%.1f%%",
                disabled=True,
            ),
            "_価格_USD": None,  # Hidden columns
            "_送料_USD": None,
        }
        
        # Display editable dataframe
        edited_df = st.data_editor(
            st.session_state.research_results,
            column_config=column_config,
            use_container_width=True,
            num_rows="fixed",
            disabled=["タイトル", "価格", "送料", "売れた日", "商品状態", "出品者", "利益額", "利益率"],
            hide_index=True,
            key="research_editor"
        )
        
        # Calculate profits dynamically
        for idx, row in edited_df.iterrows():
            if row["仕入れ値入力"] > 0:
                profit, margin = calculate_research_profit(
                    row["_価格_USD"], 
                    row["_送料_USD"],
                    row["仕入れ値入力"], 
                    st.session_state.exchange_rate
                )
                edited_df.at[idx, "利益額"] = profit
                edited_df.at[idx, "利益率"] = margin
        
        # Update session state
        st.session_state.research_results = edited_df
        
        # Action buttons
        st.subheader("アクション")
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("📥 CSVダウンロード", help="選択した商品のみをCSVでダウンロード"):
                selected_rows = edited_df[edited_df["チェック"] == True]
                if not selected_rows.empty:
                    # Prepare CSV data (exclude hidden columns and checkbox)
                    csv_data = selected_rows.drop(columns=["チェック", "_価格_USD", "_送料_USD"])
                    
                    # Convert to CSV
                    csv_buffer = io.StringIO()
                    csv_data.to_csv(csv_buffer, index=False, encoding='utf-8-sig')
                    csv_string = csv_buffer.getvalue()
                    
                    # Create download button
                    b64 = base64.b64encode(csv_string.encode('utf-8-sig')).decode()
                    href = f'<a href="data:file/csv;base64,{b64}" download="ebay_research_{datetime.now().strftime("%Y%m%d_%H%M")}.csv">CSVをダウンロード</a>'
                    st.markdown(href, unsafe_allow_html=True)
                    
                    st.success(f"✅ {len(selected_rows)}件の商品データを準備しました")
                else:
                    st.warning("⚠️ 商品を選択してください")
        
        with col2:
            if st.button("💾 選択商品を下書き保存", help="選択した商品を下書きとして保存（モック機能）"):
                selected_rows = edited_df[edited_df["チェック"] == True]
                if not selected_rows.empty:
                    st.success(f"✅ {len(selected_rows)}件の商品を下書きに保存しました")
                    
                    # Display selected items for debugging
                    with st.expander("保存された商品一覧"):
                        for idx, row in selected_rows.iterrows():
                            st.write(f"**{row['タイトル']}**")
                            st.write(f"- 価格: {row['価格']}")
                            st.write(f"- 仕入れ値: ¥{row['仕入れ値入力']:,}")
                            st.write(f"- 予想利益: ¥{row['利益額']:,.0f} ({row['利益率']:.1f}%)")
                            st.write("---")
                else:
                    st.warning("⚠️ 商品を選択してください")
    
    else:
        st.info("🔍 キーワードを入力して検索ボタンを押してください")
    
    # Sidebar with shipping rates
    with st.sidebar:
        st.header("📦 国際配送料金表（参考）")
        rates = load_shipping_rates()
        
        method_names = {
            "SAL": "国際eパケット", 
            "Air": "ヤマト運輸 / 佐川急便",
            "EMS": "EMS / DHL Express / FedEx"
        }
        
        for method, rate_table in rates.items():
            japanese_name = method_names.get(method, method)
            with st.expander(f"{japanese_name} 参考料金"):
                for weight_range, cost in rate_table.items():
                    weight_jp = weight_range.replace('up_to_', '～').replace('g', 'g').replace('_to_', '-').replace('over_', '')
                    st.write(f"{weight_jp}: ¥{cost:,}")
        
        st.header("📋 利用可能な配送業者")
        st.write("""
        **EMS（国際スピード郵便）**
        - 3-6日で配送、追跡可能
        
        **国際eパケット**
        - 1-2週間、小型軽量物向け
        
        **ヤマト運輸**
        - 国際宅急便、5-10日
        
        **佐川急便**
        - 国際宅配便、1週間程度
        
        **DHL Express**
        - 2-5日、高速配送
        
        **FedEx**
        - 2-5日、高速配送
        """)
        
        st.header("ℹ️ ご利用について")
        st.write("""
        - 料金は日本郵便ベースの参考価格です
        - 実際の料金は配送業者にご確認ください
        - eBay手数料は通常8.75%〜12.75%です
        - 為替レートは最新レートを自動取得します
        """)

if __name__ == "__main__":
    main() 