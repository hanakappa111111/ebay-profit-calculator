import streamlit as st
import pandas as pd
import requests
import json
import re
from typing import Dict, Optional, Tuple
from datetime import datetime
import io

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

def main():
    st.title("💰 eBay転売利益計算ツール")
    st.subheader("日本からeBayへの転売利益を簡単計算！")
    
    # Add explanation
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
                    item_data = ebay_api.get_item_details(ebay_input)
                
                if item_data:
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
                                       min_value=0.0, step=100.0, 
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
                                         "日本郵便 - 船便（最安・2-3ヶ月）", 
                                         "日本郵便 - SAL便（エコノミー航空便・1-2週間）",
                                         "日本郵便 - 航空便（1週間）", 
                                         "日本郵便 - 国際eパケット（1-2週間）",
                                         "日本郵便 - EMS（国際スピード郵便・3-6日）",
                                         "ヤマト運輸 - 国際宅急便（5-10日）",
                                         "佐川急便 - 国際宅配便（1週間）",
                                         "DHL Express（2-5日・高速）",
                                         "FedEx（2-5日・高速）"
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
            "日本郵便 - 国際eパケット（1-2週間）": "SAL",  # eパケットはSAL相当の料金
            "日本郵便 - EMS（国際スピード郵便・3-6日）": "EMS",
            "ヤマト運輸 - 国際宅急便（5-10日）": "Air",  # 航空便相当
            "佐川急便 - 国際宅配便（1週間）": "Air",  # 航空便相当
            "DHL Express（2-5日・高速）": "EMS",  # EMS相当の料金
            "FedEx（2-5日・高速）": "EMS"  # EMS相当の料金
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
    
    # Sidebar with shipping rates
    with st.sidebar:
        st.header("📦 国際配送料金表（参考）")
        rates = load_shipping_rates()
        
        method_names = {
            "Surface": "日本郵便 - 船便",
            "SAL": "日本郵便 - SAL便/eパケット", 
            "Air": "日本郵便 - 航空便 / ヤマト・佐川",
            "EMS": "日本郵便 - EMS / DHL・FedEx"
        }
        
        for method, rate_table in rates.items():
            japanese_name = method_names.get(method, method)
            with st.expander(f"{japanese_name} 参考料金"):
                for weight_range, cost in rate_table.items():
                    weight_jp = weight_range.replace('up_to_', '～').replace('g', 'g').replace('_to_', '-').replace('over_', '')
                    st.write(f"{weight_jp}: ¥{cost:,}")
        
        st.header("📋 利用可能な配送業者")
        st.write("""
        **日本郵便（Japan Post）**
        - EMS、国際eパケット、航空便、船便
        
        **ヤマト運輸**
        - 国際宅急便
        
        **佐川急便**
        - 国際宅配便（DHL提携便など）
        
        **DHL Express**
        - 国際高速配送サービス
        
        **FedEx**
        - 国際高速配送サービス
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