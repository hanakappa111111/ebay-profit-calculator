import streamlit as st
import pandas as pd
import requests
import json
import re
from typing import Dict, Optional, Tuple, List
from datetime import datetime
import io
import base64
import csv
import os
from pathlib import Path

# Import our custom modules
from config import SHIPPING_RATES, CURRENCY_CONFIG, APP_CONFIG
from ebay_api import ebay_api

# Configure eBay API with Streamlit secrets if available
def configure_ebay_api():
    """Configure eBay API with Streamlit secrets or environment variables"""
    try:
        # Try to use Streamlit secrets first
        if hasattr(st, 'secrets') and 'EBAY_APP_ID' in st.secrets:
            ebay_api.config['app_id'] = st.secrets['EBAY_APP_ID']
            ebay_api.config['dev_id'] = st.secrets['EBAY_DEV_ID']
            ebay_api.config['cert_id'] = st.secrets['EBAY_CERT_ID']
            ebay_api.config['environment'] = st.secrets.get('EBAY_ENV', 'production')
            return True
    except:
        pass
    
    # Fallback to environment variables (already configured in config.py)
    return False

# Configure page
st.set_page_config(
    page_title="eBay Profit Calculator - Step 2.5",
    page_icon="💰",
    layout="wide"
)

# Load shipping rates
@st.cache_data
def load_shipping_rates():
    """Load Japan Post shipping rates"""
    return SHIPPING_RATES

# Mock sold items data (structured for easy replacement with eBay API)
MOCK_SOLD_ITEMS = [
    {
        "title": "Nintendo Switch Console - Gray (Japanese Version)",
        "price_usd": 220.00,
        "sold_date": "2024-01-15",
        "category": "Video Games & Consoles",
        "condition": "Used - Very Good",
        "shipping_usd": 25.00,
        "item_id": "item_001"
    },
    {
        "title": "Apple iPhone 13 Pro 256GB Gold Unlocked",
        "price_usd": 550.00,
        "sold_date": "2024-01-18",
        "category": "Cell Phones & Smartphones", 
        "condition": "Used - Excellent",
        "shipping_usd": 30.00,
        "item_id": "item_002"
    },
    {
        "title": "Sony WH-1000XM5 Wireless Noise Canceling Headphones",
        "price_usd": 300.00,
        "sold_date": "2024-01-20",
        "category": "Consumer Electronics",
        "condition": "New with Tags",
        "shipping_usd": 20.00,
        "item_id": "item_003"
    },
    {
        "title": "LEGO Star Wars Millennium Falcon 75257",
        "price_usd": 150.00,
        "sold_date": "2024-01-22",
        "category": "Toys & Hobbies",
        "condition": "Used - Good",
        "shipping_usd": 35.00,
        "item_id": "item_004"
    },
    {
        "title": "Canon EOS R6 Mark II Camera Body Only",
        "price_usd": 1250.00,
        "sold_date": "2024-01-25",
        "category": "Cameras & Photo",
        "condition": "New",
        "shipping_usd": 45.00,
        "item_id": "item_005"
    },
    {
        "title": "Pokemon Card Collection - Charizard Base Set Japanese",
        "price_usd": 380.00,
        "sold_date": "2024-01-28",
        "category": "Toys & Hobbies",
        "condition": "Used - Very Good",
        "shipping_usd": 15.00,
        "item_id": "item_006"
    },
    {
        "title": "Vintage Seiko Automatic Watch - Made in Japan",
        "price_usd": 450.00,
        "sold_date": "2024-01-30",
        "category": "Jewelry & Watches",
        "condition": "Used - Good",
        "shipping_usd": 20.00,
        "item_id": "item_007"
    },
    {
        "title": "Yamaha Electric Guitar - Pacifica Series",
        "price_usd": 280.00,
        "sold_date": "2024-02-01",
        "category": "Musical Instruments & Gear",
        "condition": "Used - Very Good",
        "shipping_usd": 50.00,
        "item_id": "item_008"
    }
]

def get_exchange_rate():
    """Get USD to JPY exchange rate from exchangerate.host API"""
    try:
        response = requests.get(
            "https://api.exchangerate.host/latest?base=USD&symbols=JPY",
            timeout=10
        )
        response.raise_for_status()
        data = response.json()
        
        if data.get("success") and "JPY" in data.get("rates", {}):
            return data["rates"]["JPY"]
        else:
            return 150.0  # Fallback rate
            
    except Exception as e:
        st.warning(f"為替レート取得エラー: フォールバック値150円を使用")
        return 150.0

@st.cache_data(ttl=3600)  # Cache for 1 hour
def get_cached_exchange_rate():
    """Get cached exchange rate"""
    return get_exchange_rate()

def search_mock_items(keyword: str) -> List[Dict]:
    """Search mock items by keyword (simulates eBay API call)"""
    if not keyword.strip():
        return []
    
    keyword_lower = keyword.lower()
    filtered_items = []
    
    for item in MOCK_SOLD_ITEMS:
        # Search in title and category
        if (keyword_lower in item["title"].lower() or 
            keyword_lower in item["category"].lower()):
            filtered_items.append(item)
    
    return filtered_items

def calculate_max_purchase_price(selling_price_jpy: float, target_margin: float = 0.20) -> float:
    """Calculate maximum purchase price for target profit margin"""
    # eBay fee (13% fixed)
    ebay_fee_rate = 0.13
    
    # Maximum purchase price = (Selling Price / (1 + Target Margin)) - eBay Fees
    max_price = (selling_price_jpy / (1 + target_margin)) * (1 - ebay_fee_rate)
    
    return max(0, max_price)

def save_drafts_to_csv(selected_items: List[Dict], exchange_rate: float):
    """Save selected items to CSV file"""
    if not selected_items:
        return None
    
    # Prepare data for CSV
    csv_data = []
    for item in selected_items:
        price_jpy = item["price_usd"] * exchange_rate
        shipping_jpy = item["shipping_usd"] * exchange_rate
        total_price_jpy = price_jpy + shipping_jpy
        max_purchase_price = calculate_max_purchase_price(price_jpy, 0.20)
        
        csv_row = {
            "Item ID": item["item_id"],
            "Title": item["title"],
            "Price USD": item["price_usd"],
            "Price JPY": round(price_jpy),
            "Shipping USD": item["shipping_usd"], 
            "Shipping JPY": round(shipping_jpy),
            "Total JPY": round(total_price_jpy),
            "Sold Date": item["sold_date"],
            "Category": item["category"],
            "Condition": item["condition"],
            "Max Purchase Price (20% margin)": round(max_purchase_price),
            "Saved Date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        csv_data.append(csv_row)
    
    # Save to CSV
    drafts_dir = Path("drafts")
    drafts_dir.mkdir(exist_ok=True)
    
    filename = f"drafts_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    filepath = drafts_dir / filename
    
    df = pd.DataFrame(csv_data)
    df.to_csv(filepath, index=False, encoding='utf-8-sig')
    
    return str(filepath)

def load_all_drafts() -> pd.DataFrame:
    """Load all draft CSV files"""
    drafts_dir = Path("drafts")
    
    if not drafts_dir.exists():
        return pd.DataFrame()
    
    all_drafts = []
    
    for csv_file in drafts_dir.glob("drafts_*.csv"):
        try:
            df = pd.read_csv(csv_file, encoding='utf-8-sig')
            df['Source File'] = csv_file.name
            all_drafts.append(df)
        except Exception as e:
            st.warning(f"ファイル読み込みエラー: {csv_file.name}")
            continue
    
    if all_drafts:
        return pd.concat(all_drafts, ignore_index=True)
    else:
        return pd.DataFrame()

def profit_calculation_tab():
    """Original profit calculation tab (Step 1)"""
    st.header("💰 利益計算")
    st.markdown("eBay商品URLまたはアイテムIDから利益を計算します")
    
    # Input section
    col1, col2 = st.columns([2, 1])
    
    with col1:
        item_input = st.text_input(
            "eBay URL または アイテムID",
            placeholder="例: https://www.ebay.com/itm/123456789 または 123456789",
            help="eBayの商品ページURLまたは数字のアイテムIDを入力してください"
        )
    
    with col2:
        supplier_price = st.number_input(
            "仕入れ価格 (円)",
            min_value=0,
            value=0,
            step=100,
            help="商品の仕入れ価格を円で入力してください"
        )
    
    if item_input and supplier_price > 0:
        if st.button("💰 利益を計算", type="primary"):
            with st.spinner("商品情報を取得中..."):
                try:
                    # Extract item ID and fetch data
                    item_id = ebay_api.extract_item_id(item_input)
                    if item_id:
                        item_data = ebay_api.fetch_item_via_api(item_id)
                        
                        if not item_data:
                            item_data = ebay_api.fetch_item_via_scraping(item_input)
                        
                        if item_data:
                            # Display results
                            st.success("✅ 商品情報を取得しました")
                            
                            col1, col2 = st.columns(2)
                            
                            with col1:
                                st.subheader("📦 商品情報")
                                st.write(f"**タイトル:** {item_data['title']}")
                                st.write(f"**価格:** ${item_data['price']:.2f}")
                                st.write(f"**カテゴリ:** {item_data.get('category', 'Unknown')}")
                                
                                if item_data.get('image_url'):
                                    st.image(item_data['image_url'], width=200)
                            
                            with col2:
                                st.subheader("💹 利益計算")
                                
                                # Get exchange rate
                                exchange_rate = get_cached_exchange_rate()
                                st.write(f"**為替レート:** 1 USD = {exchange_rate:.2f} JPY")
                                
                                # Calculate costs and profit
                                selling_price_jpy = item_data['price'] * exchange_rate
                                ebay_fee = selling_price_jpy * 0.13  # 13% eBay fee
                                total_costs = supplier_price + ebay_fee
                                profit = selling_price_jpy - total_costs
                                profit_margin = (profit / selling_price_jpy) * 100 if selling_price_jpy > 0 else 0
                                
                                st.write(f"**販売価格 (円):** ¥{selling_price_jpy:,.0f}")
                                st.write(f"**仕入れ価格:** ¥{supplier_price:,}")
                                st.write(f"**eBay手数料 (13%):** ¥{ebay_fee:,.0f}")
                                st.write(f"**利益:** ¥{profit:,.0f}")
                                
                                if profit > 0:
                                    st.success(f"**利益率:** {profit_margin:.1f}%")
                                else:
                                    st.error(f"**損失率:** {abs(profit_margin):.1f}%")
                        else:
                            st.error("❌ 商品情報を取得できませんでした")
                    else:
                        st.error("❌ 有効なアイテムIDを抽出できませんでした")
                        
                except Exception as e:
                    st.error(f"❌ エラーが発生しました: {str(e)}")

def research_and_draft_tab():
    """Research & Draft tab (Step 2.5)"""
    st.header("🔍 Research & Draft")
    st.markdown("キーワードで商品を検索し、下書きに保存できます")
    
    # Search section
    col1, col2 = st.columns([3, 1])
    
    with col1:
        keyword = st.text_input(
            "検索キーワード",
            placeholder="例: Nintendo, iPhone, Camera",
            help="商品名、カテゴリなどで検索できます"
        )
    
    with col2:
        if st.button("🔍 検索", type="primary"):
            if keyword.strip():
                st.session_state.search_results = search_mock_items(keyword)
                st.session_state.search_keyword = keyword
            else:
                st.warning("キーワードを入力してください")
    
    # Display search results
    if hasattr(st.session_state, 'search_results') and st.session_state.search_results:
        st.markdown("---")
        st.subheader(f"🛍️ 検索結果: '{st.session_state.search_keyword}' ({len(st.session_state.search_results)}件)")
        
        # Get current exchange rate
        exchange_rate = get_cached_exchange_rate()
        st.info(f"💱 現在の為替レート: 1 USD = {exchange_rate:.2f} JPY")
        
        # Prepare data for display
        display_data = []
        for i, item in enumerate(st.session_state.search_results):
            price_jpy = item["price_usd"] * exchange_rate
            shipping_jpy = item["shipping_usd"] * exchange_rate
            max_purchase = calculate_max_purchase_price(price_jpy, 0.20)
            
            display_data.append({
                "選択": False,
                "商品タイトル": item["title"],
                "価格 (USD)": f"${item['price_usd']:.2f}",
                "価格 (JPY)": f"¥{price_jpy:,.0f}",
                "送料 (USD)": f"${item['shipping_usd']:.2f}",
                "送料 (JPY)": f"¥{shipping_jpy:,.0f}",
                "売れた日": item["sold_date"],
                "カテゴリ": item["category"],
                "状態": item["condition"],
                "最大仕入値 (20%利益)": f"¥{max_purchase:,.0f}",
                "_item_index": i
            })
        
        # Display as data editor for selection
        df = pd.DataFrame(display_data)
        
        edited_df = st.data_editor(
            df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "選択": st.column_config.CheckboxColumn(
                    "選択",
                    help="下書きに保存したい商品をチェックしてください"
                ),
                "商品タイトル": st.column_config.TextColumn(
                    "商品タイトル",
                    width="large"
                ),
                "最大仕入値 (20%利益)": st.column_config.TextColumn(
                    "最大仕入値 (20%利益)",
                    help="20%の利益率を確保するための最大仕入れ価格"
                )
            }
        )
        
        # Save to draft button
        selected_count = len(edited_df[edited_df["選択"] == True])
        
        col1, col2, col3 = st.columns([1, 1, 2])
        
        with col1:
            st.metric("選択中", f"{selected_count}件")
        
        with col2:
            if st.button("📋 下書きに保存", disabled=selected_count == 0):
                # Get selected items
                selected_indices = edited_df[edited_df["選択"] == True]["_item_index"].tolist()
                selected_items = [st.session_state.search_results[i] for i in selected_indices]
                
                # Save to CSV
                filepath = save_drafts_to_csv(selected_items, exchange_rate)
                
                if filepath:
                    st.success(f"✅ {len(selected_items)}件を下書きに保存しました")
                    st.info(f"📁 保存先: {filepath}")
                    
                    # Update drafts in session state
                    if 'drafts_updated' not in st.session_state:
                        st.session_state.drafts_updated = 0
                    st.session_state.drafts_updated += 1
                else:
                    st.error("❌ 保存に失敗しました")
        
        with col3:
            if selected_count > 0:
                selected_items = edited_df[edited_df["選択"] == True]
                total_price = sum([
                    float(price.replace('¥', '').replace(',', '')) 
                    for price in selected_items["価格 (JPY)"]
                ])
                st.metric("選択商品総額", f"¥{total_price:,.0f}")

def my_drafts_tab():
    """My Drafts tab to view saved draft items"""
    st.header("📋 My Drafts")
    st.markdown("保存した下書きアイテムを確認できます")
    
    # Load all drafts
    drafts_df = load_all_drafts()
    
    if drafts_df.empty:
        st.info("📝 保存された下書きはありません")
        st.markdown("**使い方:**")
        st.markdown("1. 「Research & Draft」タブで商品を検索")
        st.markdown("2. 商品を選択して「下書きに保存」をクリック")
        st.markdown("3. 保存された商品がここに表示されます")
        return
    
    # Statistics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("総下書き数", len(drafts_df))
    
    with col2:
        total_value = drafts_df["Total JPY"].sum()
        st.metric("総価値", f"¥{total_value:,.0f}")
    
    with col3:
        avg_price = drafts_df["Price JPY"].mean()
        st.metric("平均価格", f"¥{avg_price:,.0f}")
    
    with col4:
        files_count = drafts_df["Source File"].nunique()
        st.metric("ファイル数", files_count)
    
    # Filters
    st.markdown("---")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        categories = ["全て"] + sorted(drafts_df["Category"].unique().tolist())
        selected_category = st.selectbox("カテゴリフィルタ", categories)
    
    with col2:
        conditions = ["全て"] + sorted(drafts_df["Condition"].unique().tolist())
        selected_condition = st.selectbox("状態フィルタ", conditions)
    
    with col3:
        price_range = st.slider(
            "価格範囲 (JPY)",
            min_value=int(drafts_df["Price JPY"].min()),
            max_value=int(drafts_df["Price JPY"].max()),
            value=(int(drafts_df["Price JPY"].min()), int(drafts_df["Price JPY"].max()))
        )
    
    # Apply filters
    filtered_df = drafts_df.copy()
    
    if selected_category != "全て":
        filtered_df = filtered_df[filtered_df["Category"] == selected_category]
    
    if selected_condition != "全て":
        filtered_df = filtered_df[filtered_df["Condition"] == selected_condition]
    
    filtered_df = filtered_df[
        (filtered_df["Price JPY"] >= price_range[0]) & 
        (filtered_df["Price JPY"] <= price_range[1])
    ]
    
    # Display filtered results
    if filtered_df.empty:
        st.warning("フィルタ条件に該当する下書きはありません")
        return
    
    st.subheader(f"📋 下書き一覧 ({len(filtered_df)}件)")
    
    # Prepare display DataFrame
    display_df = filtered_df[[ 
        "Title", "Price USD", "Price JPY", "Shipping JPY", "Total JPY",
        "Sold Date", "Category", "Condition", "Max Purchase Price (20% margin)",
        "Saved Date", "Source File"
    ]].copy()
    
    # Format for better display
    display_df["Price JPY"] = display_df["Price JPY"].apply(lambda x: f"¥{x:,.0f}")
    display_df["Shipping JPY"] = display_df["Shipping JPY"].apply(lambda x: f"¥{x:,.0f}")
    display_df["Total JPY"] = display_df["Total JPY"].apply(lambda x: f"¥{x:,.0f}")
    display_df["Max Purchase Price (20% margin)"] = display_df["Max Purchase Price (20% margin)"].apply(lambda x: f"¥{x:,.0f}")
    
    # Rename columns for display
    display_df.columns = [
        "商品タイトル", "価格 (USD)", "価格 (JPY)", "送料 (JPY)", "総額 (JPY)",
        "売れた日", "カテゴリ", "状態", "最大仕入値 (20%利益)",
        "保存日時", "ファイル名"
    ]
    
    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "商品タイトル": st.column_config.TextColumn("商品タイトル", width="large"),
            "最大仕入値 (20%利益)": st.column_config.TextColumn(
                "最大仕入値 (20%利益)",
                help="20%の利益率を確保するための最大仕入れ価格"
            )
        }
    )
    
    # Export functionality
    st.markdown("---")
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("📄 全データCSVエクスポート"):
            csv_buffer = io.StringIO()
            filtered_df.to_csv(csv_buffer, index=False, encoding='utf-8-sig')
            csv_string = csv_buffer.getvalue()
            
            b64 = base64.b64encode(csv_string.encode('utf-8-sig')).decode()
            href = f'<a href="data:file/csv;base64,{b64}" download="all_drafts_{datetime.now().strftime("%Y%m%d_%H%M")}.csv">CSVダウンロード</a>'
            st.markdown(href, unsafe_allow_html=True)
            st.success("✅ CSVエクスポート準備完了")
    
    with col2:
        if st.button("🗑️ 古いファイルを削除"):
            drafts_dir = Path("drafts")
            if drafts_dir.exists():
                csv_files = list(drafts_dir.glob("drafts_*.csv"))
                if len(csv_files) > 5:  # Keep only latest 5 files
                    csv_files.sort(key=lambda x: x.stat().st_mtime)
                    files_to_delete = csv_files[:-5]
                    
                    for file_path in files_to_delete:
                        file_path.unlink()
                    
                    st.success(f"✅ {len(files_to_delete)}個の古いファイルを削除しました")
                    st.rerun()
                else:
                    st.info("削除する古いファイルはありません")

def main():
    """Main application function"""
    # Initialize
    configure_ebay_api()
    
    # Header
    st.title("💰 eBay Profit Calculator - Step 2.5")
    st.markdown("**利益計算 + Research & Draft 機能**")
    
    # Create tabs
    tab1, tab2, tab3 = st.tabs(["💰 利益計算", "🔍 Research & Draft", "📋 My Drafts"])
    
    with tab1:
        profit_calculation_tab()
    
    with tab2:
        research_and_draft_tab()
    
    with tab3:
        my_drafts_tab()
    
    # Sidebar with info
    with st.sidebar:
        st.header("📊 アプリ情報")
        st.markdown("**Step 2.5 新機能:**")
        st.markdown("- 🔍 キーワード検索")
        st.markdown("- 📋 下書き保存 (CSV)")
        st.markdown("- 💱 リアルタイム為替")
        st.markdown("- 📈 利益率計算")
        
        st.markdown("---")
        st.markdown("**使用中の為替レート:**")
        try:
            rate = get_cached_exchange_rate()
            st.success(f"1 USD = {rate:.2f} JPY")
        except:
            st.error("為替レート取得失敗")
        
        st.markdown("---")
        st.markdown("**下書きフォルダ:**")
        drafts_dir = Path("drafts")
        if drafts_dir.exists():
            csv_files = list(drafts_dir.glob("drafts_*.csv"))
            st.info(f"📁 {len(csv_files)} ファイル保存済み")
        else:
            st.info("📁 下書きなし")

if __name__ == "__main__":
    main()
