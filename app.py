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

def calculate_shipping_cost(weight_g: int, method: str) -> int:
    """Calculate shipping cost based on weight and method"""
    rates = load_shipping_rates()
    
    if method not in rates:
        return 0
    
    rate_table = rates[method]
    
    if weight_g <= 500:
        return rate_table["up_to_500g"]
    elif weight_g <= 1000:
        return rate_table["501_to_1000g"]
    elif weight_g <= 1500:
        return rate_table["1001_to_1500g"]
    elif weight_g <= 2000:
        return rate_table["1501_to_2000g"]
    else:
        return rate_table["over_2000g"]

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
        supplier_price = st.number_input("仕入価格（日本円）", 
                                       min_value=0.0, step=100.0, 
                                       help="あなたが商品を仕入れた（購入した）価格を日本円で入力してください。eBayでの販売価格ではありません。")
    
    with col2:
        st.header("🚚 配送設定")
        weight = st.number_input("商品重量（グラム）", 
                               min_value=1, max_value=10000, value=500,
                               help="商品の重量をグラムで入力してください")
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
            item_data = ebay_api.get_item_details(ebay_input)
        
        if not item_data:
            st.error("eBayの商品データを取得できませんでした。URLまたは商品IDを確認してもう一度お試しください。")
            return
        
        # Calculate shipping cost - convert method name back to English for calculation
        method_mapping = {
            "日本郵便 - 船便（最安・2-3ヶ月）": "Surface",
            "日本郵便 - SAL便（エコノミー航空便・1-2週間）": "SAL", 
            "日本郵便 - 航空便（1週間）": "Air",
            "日本郵便 - 国際eパケット（1-2週間）": "SAL",  # eパケットはSAL相当の料金
            "日本郵便 - EMS（国際スピード郵便・3-6日）": "EMS",
            "ヤマト運輸 - 国際宅急便（5-10日）": "Air",  # 航空便相当
            "佐川急便 - 国際宅配便（1週間）": "Air",  # 航空便相当
            "DHL Express（2-5日・高速）": "EMS",  # EMS相当の料金
            "FedEx（2-5日・高速）": "EMS"  # EMS相当の料金
        }
        english_method = method_mapping.get(shipping_method, "Surface")
        shipping_cost_jpy = calculate_shipping_cost(weight, english_method)
        
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
        breakdown_data = {
            "項目": [
                "eBay販売価格（米ドル）",
                "仕入コスト（円→ドル）",
                "eBay手数料（米ドル）",
                "送料（円→ドル）",
                "最終利益（米ドル）",
                "利益率（％）"
            ],
            "金額": [
                f"${selling_price:.2f}",
                f"${supplier_cost_usd:.2f}",
                f"${ebay_fees:.2f}",
                f"${shipping_cost_usd:.2f}",
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