"""
Enhanced eBay Profit Calculator with Modular Architecture
"""
import streamlit as st
import pandas as pd
import time
from datetime import datetime
from typing import Dict, List, Optional
import io
import base64

# Import new modular components
from data_sources.ebay import search_completed_items, get_item_detail
from publish.drafts import save_draft, list_drafts, DraftPayload
from shipping.calc import quote as shipping_quote, zone as shipping_zone, estimate_weight
from utils.fx import get_rate, convert_currency, format_currency, display_rate_badge
from utils.openai_rewrite import rewrite_title, rewrite_description
from utils.logging_utils import get_app_logger

# Legacy imports
from config import APP_CONFIG
from ebay_api import ebay_api

# Configure page
st.set_page_config(
    page_title="Enhanced eBay Profit Calculator",
    page_icon="💰",
    layout="wide"
)

# Initialize logger
logger = get_app_logger()

# Configure eBay API
def configure_ebay_api():
    """Configure eBay API with Streamlit secrets or environment variables"""
    try:
        if hasattr(st, 'secrets') and 'EBAY_APP_ID' in st.secrets:
            ebay_api.config['app_id'] = st.secrets['EBAY_APP_ID']
            ebay_api.config['dev_id'] = st.secrets['EBAY_DEV_ID']
            ebay_api.config['cert_id'] = st.secrets['EBAY_CERT_ID']
            ebay_api.config['environment'] = st.secrets.get('EBAY_ENV', 'production')
            return True
    except:
        pass
    return False

def initialize_session_state():
    """Initialize session state variables"""
    if 'research_results' not in st.session_state:
        st.session_state.research_results = []
    if 'selected_items' not in st.session_state:
        st.session_state.selected_items = set()
    if 'fx_rate' not in st.session_state:
        st.session_state.fx_rate = None

def enhanced_search_tab():
    """Enhanced research tab with new features"""
    st.header("🔍 商品リサーチ（拡張版）")
    
    # Search interface
    col1, col2, col3 = st.columns([3, 1, 1])
    
    with col1:
        keyword = st.text_input("🔍 キーワードを入力", placeholder="例: Nintendo Switch, iPhone, Camera")
    
    with col2:
        target_market = st.selectbox("📍 市場", ["US", "GB", "AU", "DE", "CA"])
    
    with col3:
        limit = st.number_input("📊 表示件数", min_value=5, max_value=50, value=20)
    
    # Advanced options
    with st.expander("🎛️ 詳細設定"):
        col1, col2, col3 = st.columns(3)
        
        with col1:
            enable_ai_rewrite = st.checkbox("🤖 AIタイトルリライト", value=False)
        
        with col2:
            show_shipping_calc = st.checkbox("📦 配送料計算", value=True)
        
        with col3:
            auto_estimate_weight = st.checkbox("⚖️ 重量自動推定", value=True)
    
    # Search button and processing
    if st.button("🔍 検索実行", type="primary"):
        if not keyword.strip():
            st.warning("⚠️ キーワードを入力してください")
            return
        
        # Log search
        start_time = time.time()
        logger.log_search(keyword, 0, 0)  # Will update with results
        
        with st.spinner("🔍 商品を検索しています..."):
            # Try real eBay API first, fallback to mock data
            try:
                # Attempt real eBay API search
                real_results = ebay_api.search_items(keyword, limit)
                if real_results and len(real_results) > 0:
                    # Use real API results
                    results = []
                    for item in real_results:
                        # Convert eBay API format to our format
                        converted_item = {
                            "item_id": item.get("item_id", ""),
                            "title": item.get("title", ""),
                            "price_usd": item.get("price_usd", 0),
                            "shipping_usd": item.get("shipping_usd", 0),
                            "sold_date": item.get("sold_date", datetime.now().strftime("%Y-%m-%d")),
                            "condition": item.get("condition", "Unknown"),
                            "seller": item.get("seller", "Unknown Seller"),
                            "image_url": item.get("image_url", ""),
                            "ebay_url": item.get("ebay_url", ""),
                            "category": item.get("category", "General"),
                            "location": item.get("location", ""),
                            "watchers": item.get("watchers", 0),
                            "bids": item.get("bids", 0)
                        }
                        results.append(converted_item)
                    
                    st.info(f"✅ eBay APIから{len(results)}件取得")
                    logger.log_api_call("eBay", "/search", True, time.time() - start_time)
                else:
                    raise Exception("No results from eBay API")
                    
            except Exception as e:
                # Fallback to mock data
                st.warning(f"⚠️ eBay API接続失敗: {str(e)[:100]}... モックデータを使用")
                results = search_completed_items(keyword, limit)
                logger.log_api_call("eBay", "/search", False, time.time() - start_time)
                
            processing_time = time.time() - start_time
            
            if results:
                # Process results with enhancements
                enhanced_results = []
                
                for item in results:
                    enhanced_item = item.copy()
                    
                    # Add shipping calculation
                    if show_shipping_calc:
                        weight_g = estimate_weight(
                            item.get("category", ""), 
                            item.get("title", "")
                        ) if auto_estimate_weight else 500
                        
                        shipping_info = shipping_quote(weight_g, target_market)
                        enhanced_item["shipping_calc"] = shipping_info
                        enhanced_item["estimated_weight_g"] = weight_g
                        
                        # Get all shipping options for comparison
                        from shipping.calc import get_all_options
                        all_options = get_all_options(weight_g, target_market)
                        enhanced_item["shipping_options"] = all_options
                        
                        # Log shipping calculation
                        logger.log_user_action("shipping_calculation", {
                            "weight_g": weight_g,
                            "country": target_market,
                            "method": shipping_info.get("method", "Unknown"),
                            "cost_jpy": shipping_info.get("cost_jpy", 0)
                        })
                    
                    # Add AI rewrite
                    if enable_ai_rewrite:
                        rewrite_result = rewrite_title(
                            item.get("title", ""), 
                            target_market, 
                            80
                        )
                        enhanced_item["ai_rewrite"] = rewrite_result
                    
                    enhanced_results.append(enhanced_item)
                
                st.session_state.research_results = enhanced_results
                
                # Update search log
                logger.log_search(keyword, len(results), processing_time)
                
                st.success(f"✅ {len(results)}件の商品を見つけました（{processing_time:.2f}秒）")
            else:
                st.warning("⚠️ 該当する商品が見つかりませんでした")
    
    # Display results if available
    if st.session_state.research_results:
        display_enhanced_results()

def display_enhanced_results():
    """Display search results with enhanced features"""
    results = st.session_state.research_results
    
    st.markdown("---")
    st.subheader(f"🛍️ 検索結果 ({len(results)}件)")
    
    # Status badges
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        display_rate_badge("USD", "JPY")
    
    with col2:
        # Enhanced shipping status
        if results[0].get("shipping_calc"):
            shipping_method = results[0]["shipping_calc"].get("method", "Unknown")
            st.markdown(f"🚚 **配送**: {shipping_method} 最安選択")
        else:
            st.markdown("🚚 **配送計算**: 無効")
    
    with col3:
        # Enhanced AI status
        if results[0].get("ai_rewrite"):
            ai_status = "成功" if results[0]["ai_rewrite"].get("success") else "失敗"
            st.markdown(f"🤖 **AIリライト**: {ai_status}")
        else:
            st.markdown("🤖 **AIリライト**: 無効")
    
    with col4:
        # Data source status
        if any("eBay API" in str(results) for results in [results]):
            st.markdown("🔗 **データ**: eBay API")
        else:
            st.markdown("🔗 **データ**: モック")
    
    # Create DataFrame for display
    display_data = []
    
    for idx, item in enumerate(results):
        # Get FX rate
        fx_info = get_rate("USD", "JPY")
        usd_to_jpy = fx_info["rate"]
        
        # Calculate JPY prices
        price_jpy = item["price_usd"] * usd_to_jpy
        shipping_jpy = item["shipping_usd"] * usd_to_jpy
        
        # Shipping calculation
        shipping_text = f"${item['shipping_usd']:.2f} / ¥{shipping_jpy:,.0f}"
        if item.get("shipping_calc"):
            calc_shipping = item["shipping_calc"]["cost_jpy"]
            method = item["shipping_calc"]["method"]
            shipping_text += f" (最安: {method} ¥{calc_shipping:,})"
            
            # Show all options in tooltip
            if item.get("shipping_options"):
                options_text = " | ".join([
                    f"{opt['method']}: ¥{opt['cost_jpy']:,}" 
                    for opt in item["shipping_options"]
                ])
                shipping_text += f" (全選択肢: {options_text})"
        
        # Title display
        title_display = item["title"][:50] + "..." if len(item["title"]) > 50 else item["title"]
        
        # AI rewrite display
        if item.get("ai_rewrite") and item["ai_rewrite"]["success"]:
            title_display += f"\n🤖 {item['ai_rewrite']['rewritten'][:40]}..."
        
        row_data = {
            "選択": False,
            "商品タイトル": title_display,
            "価格": f"${item['price_usd']:.2f} / ¥{price_jpy:,.0f}",
            "送料": shipping_text,
            "売れた日": item["sold_date"],
            "状態": item["condition"],
            "出品者": item["seller"],
            "仕入れ値(円)": 0,
            "利益額": 0,
            "利益率": 0.0,
            "_price_usd": item["price_usd"],
            "_shipping_usd": item["shipping_usd"],
            "_price_jpy": price_jpy,
            "_shipping_jpy": shipping_jpy,
            "_item_idx": idx
        }
        
        display_data.append(row_data)
    
    # Data editor with filters and sorting
    st.markdown("### 💰 利益計算・商品選択")
    
    # Filter options
    with st.expander("🔍 フィルター・ソート"):
        col1, col2, col3 = st.columns(3)
        
        with col1:
            price_range = st.slider(
                "価格範囲 (USD)", 
                min_value=0, 
                max_value=2000, 
                value=(0, 1000),
                step=50
            )
        
        with col2:
            condition_filter = st.multiselect(
                "商品状態",
                options=list(set(item["condition"] for item in results)),
                default=list(set(item["condition"] for item in results))
            )
        
        with col3:
            sort_by = st.selectbox(
                "ソート基準",
                ["価格昇順", "価格降順", "売れた日", "利益率"]
            )
    
    # Apply filters
    filtered_data = [
        row for row in display_data
        if (price_range[0] <= row["_price_usd"] <= price_range[1] and
            any(item["condition"] in condition_filter for item in results if item["title"] in row["商品タイトル"]))
    ]
    
    if not filtered_data:
        st.warning("⚠️ フィルター条件に該当する商品がありません")
        return
    
    # Data editor
    df = pd.DataFrame(filtered_data)
    
    edited_df = st.data_editor(
        df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "選択": st.column_config.CheckboxColumn("選択", help="CSVエクスポートや下書き保存対象"),
            "商品タイトル": st.column_config.TextColumn("商品タイトル", width="large"),
            "価格": st.column_config.TextColumn("価格", help="USD / JPY表示"),
            "送料": st.column_config.TextColumn("送料", help="USD / JPY表示"),
            "仕入れ値(円)": st.column_config.NumberColumn(
                "仕入れ値(円)",
                help="仕入れ予定価格を入力",
                min_value=0,
                step=1000
            ),
            "利益額": st.column_config.NumberColumn("利益額", format="%.0f"),
            "利益率": st.column_config.NumberColumn("利益率(%)", format="%.1f")
        },
        key="research_data_editor"
    )
    
    # Calculate profits dynamically
    for idx, row in edited_df.iterrows():
        if row["仕入れ値(円)"] > 0:
            # Calculate profit
            sale_price_jpy = row["_price_jpy"]
            purchase_price_jpy = row["仕入れ値(円)"]
            shipping_cost_jpy = row["_shipping_jpy"]
            fee_rate = 0.13  # 13% eBay fee
            
            profit_jpy = sale_price_jpy - purchase_price_jpy - shipping_cost_jpy - (sale_price_jpy * fee_rate)
            profit_margin = (profit_jpy / purchase_price_jpy) * 100 if purchase_price_jpy > 0 else 0
            
            edited_df.at[idx, "利益額"] = profit_jpy
            edited_df.at[idx, "利益率"] = profit_margin
    
    # Action buttons
    st.markdown("### 🎯 アクション")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if st.button("📄 CSVエクスポート"):
            export_selected_to_csv(edited_df)
    
    with col2:
        if st.button("📁 CSVインポート"):
            show_csv_import_dialog()
    
    with col3:
        if st.button("💾 下書き保存"):
            save_selected_as_drafts(edited_df)
    
    with col4:
        if st.button("📈 収益分析"):
            show_profit_analysis(edited_df)

def export_selected_to_csv(df: pd.DataFrame):
    """Export selected items to CSV"""
    selected_rows = df[df["選択"] == True]
    
    if selected_rows.empty:
        st.warning("⚠️ 商品を選択してください")
        return
    
    # Prepare CSV data
    csv_data = selected_rows[[
        "商品タイトル", "価格", "送料", "売れた日", "状態", "出品者", 
        "仕入れ値(円)", "利益額", "利益率"
    ]].copy()
    
    # Create CSV download
    csv_buffer = io.StringIO()
    csv_data.to_csv(csv_buffer, index=False, encoding='utf-8-sig')
    csv_string = csv_buffer.getvalue()
    
    b64 = base64.b64encode(csv_string.encode('utf-8-sig')).decode()
    href = f'<a href="data:file/csv;base64,{b64}" download="ebay_research_{datetime.now().strftime("%Y%m%d_%H%M")}.csv">📄 CSVダウンロード</a>'
    st.markdown(href, unsafe_allow_html=True)
    
    st.success(f"✅ {len(selected_rows)}件の商品データを準備しました")
    
    # Log export
    logger.log_user_action("csv_export", {"item_count": len(selected_rows)})

def save_selected_as_drafts(df: pd.DataFrame):
    """Save selected items as drafts"""
    selected_rows = df[df["選択"] == True]
    
    if selected_rows.empty:
        st.warning("⚠️ 商品を選択してください")
        return
    
    success_count = 0
    error_count = 0
    
    with st.spinner("💾 下書きを保存中..."):
        for _, row in selected_rows.iterrows():
            try:
                # Get original item data
                item_idx = row["_item_idx"]
                original_item = st.session_state.research_results[item_idx]
                
                # Create draft payload
                draft_data = {
                    "item_id": original_item.get("item_id", f"draft_{int(time.time())}"),
                    "title": original_item["title"],
                    "price_usd": row["_price_usd"],
                    "shipping_usd": row["_shipping_usd"],
                    "condition": original_item["condition"],
                    "purchase_price_jpy": int(row["仕入れ値(円)"]),
                    "profit_jpy": float(row["利益額"]),
                    "profit_margin": float(row["利益率"]),
                    "seller": original_item["seller"],
                    "sold_date": original_item["sold_date"],
                    "category": original_item.get("category"),
                    "image_url": original_item.get("image_url"),
                    "ebay_url": original_item.get("ebay_url"),
                    "notes": f"検索キーワード: {getattr(st.session_state, 'last_keyword', 'N/A')}"
                }
                
                # Save draft
                result = save_draft(draft_data)
                
                if result["success"]:
                    success_count += 1
                    logger.log_draft_save(
                        draft_data["item_id"],
                        draft_data["title"],
                        draft_data["profit_jpy"],
                        True
                    )
                else:
                    error_count += 1
                    logger.log_error("draft_save_error", result.get("error", "Unknown error"))
                    
            except Exception as e:
                error_count += 1
                logger.log_error("draft_save_exception", str(e))
    
    if success_count > 0:
        st.success(f"✅ {success_count}件の下書きを保存しました")
    
    if error_count > 0:
        st.error(f"❌ {error_count}件の保存に失敗しました")

def show_csv_import_dialog():
    """Show CSV import dialog"""
    st.markdown("### 📁 CSVインポート")
    
    uploaded_file = st.file_uploader(
        "CSVファイルを選択してください",
        type=['csv'],
        help="過去にエクスポートしたCSVファイルをインポートできます"
    )
    
    if uploaded_file is not None:
        try:
            # Read CSV file
            df = pd.read_csv(uploaded_file, encoding='utf-8-sig')
            
            st.success(f"✅ CSVファイルを読み込みました ({len(df)}行)")
            
            # Display preview
            st.markdown("**プレビュー:**")
            st.dataframe(df.head(10), use_container_width=True)
            
            # Validation
            required_columns = ["商品タイトル", "価格", "送料"]
            missing_columns = [col for col in required_columns if col not in df.columns]
            
            if missing_columns:
                st.error(f"❌ 必須カラムが不足しています: {', '.join(missing_columns)}")
                return
            
            # Import confirmation
            if st.button("🔄 インポート実行", type="primary"):
                import_csv_data(df)
                
        except Exception as e:
            st.error(f"❌ CSVファイルの読み込みに失敗しました: {str(e)}")
            logger.log_error("csv_import_error", str(e))

def import_csv_data(df: pd.DataFrame):
    """Import CSV data into session state"""
    try:
        # Convert CSV data back to our internal format
        imported_results = []
        
        for idx, row in df.iterrows():
            # Extract data from CSV format
            title = str(row.get("商品タイトル", ""))
            
            # Parse price (remove currency symbols and convert)
            price_text = str(row.get("価格", "0"))
            try:
                # Extract USD price from "$ X.XX / ¥ Y,YYY" format
                usd_price = float(price_text.split('$')[1].split('/')[0].strip()) if '$' in price_text else 0
            except:
                usd_price = 0
            
            # Parse shipping
            shipping_text = str(row.get("送料", "0"))
            try:
                usd_shipping = float(shipping_text.split('$')[1].split('/')[0].strip()) if '$' in shipping_text else 0
            except:
                usd_shipping = 0
            
            # Create item in our format
            item = {
                "item_id": f"imported_{int(time.time())}_{idx}",
                "title": title,
                "price_usd": usd_price,
                "shipping_usd": usd_shipping,
                "sold_date": str(row.get("売れた日", datetime.now().strftime("%Y-%m-%d"))),
                "condition": str(row.get("状態", "Unknown")),
                "seller": str(row.get("出品者", "Unknown Seller")),
                "category": "Imported",
                "location": "Unknown",
                "image_url": "",
                "ebay_url": "",
                "watchers": 0,
                "bids": 0
            }
            
            imported_results.append(item)
        
        # Add to session state
        if 'research_results' not in st.session_state:
            st.session_state.research_results = []
        
        # Merge with existing results
        existing_count = len(st.session_state.research_results)
        st.session_state.research_results.extend(imported_results)
        
        st.success(f"✅ {len(imported_results)}件のデータをインポートしました")
        st.info(f"📊 合計: {len(st.session_state.research_results)}件 (既存: {existing_count}件 + 新規: {len(imported_results)}件)")
        
        # Log import
        logger.log_user_action("csv_import", {
            "imported_count": len(imported_results),
            "total_count": len(st.session_state.research_results)
        })
        
        # Rerun to update display
        st.rerun()
        
    except Exception as e:
        st.error(f"❌ データのインポートに失敗しました: {str(e)}")
        logger.log_error("csv_import_data_error", str(e))

def show_profit_analysis(df: pd.DataFrame):
    """Show profit analysis"""
    profitable_items = df[df["利益額"] > 0]
    
    if profitable_items.empty:
        st.warning("⚠️ 利益が出る商品がありません")
        return
    
    st.markdown("### 📊 収益分析")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        avg_profit = profitable_items["利益額"].mean()
        st.metric("平均利益", f"¥{avg_profit:,.0f}")
    
    with col2:
        avg_margin = profitable_items["利益率"].mean()
        st.metric("平均利益率", f"{avg_margin:.1f}%")
    
    with col3:
        total_investment = profitable_items["仕入れ値(円)"].sum()
        st.metric("総仕入れ額", f"¥{total_investment:,.0f}")
    
    with col4:
        total_profit = profitable_items["利益額"].sum()
        st.metric("総利益", f"¥{total_profit:,.0f}")
    
    # Profit distribution chart
    if len(profitable_items) > 1:
        import plotly.express as px
        
        fig = px.scatter(
            profitable_items,
            x="仕入れ値(円)",
            y="利益額",
            size="利益率",
            hover_name="商品タイトル",
            title="仕入れ値 vs 利益額",
            labels={"仕入れ値(円)": "仕入れ値 (円)", "利益額": "利益額 (円)"}
        )
        
        st.plotly_chart(fig, use_container_width=True)

def drafts_management_tab():
    """Drafts management tab"""
    st.header("📋 下書き管理")
    
    # Load and display drafts
    drafts = list_drafts(50)
    
    if not drafts:
        st.info("💡 保存された下書きはありません")
        return
    
    st.subheader(f"📄 保存済み下書き ({len(drafts)}件)")
    
    # Draft statistics
    if drafts:
        col1, col2, col3 = st.columns(3)
        
        with col1:
            total_profit = sum(d.get("profit_jpy", 0) for d in drafts)
            st.metric("総予想利益", f"¥{total_profit:,.0f}")
        
        with col2:
            avg_margin = sum(d.get("profit_margin", 0) for d in drafts) / len(drafts)
            st.metric("平均利益率", f"{avg_margin:.1f}%")
        
        with col3:
            st.metric("下書き数", len(drafts))
    
    # Display drafts table
    drafts_df = pd.DataFrame(drafts)
    
    if not drafts_df.empty:
        st.dataframe(
            drafts_df[["title", "price_usd", "profit_jpy", "profit_margin", "created_at"]],
            use_container_width=True,
            column_config={
                "title": "商品タイトル",
                "price_usd": st.column_config.NumberColumn("価格(USD)", format="$%.2f"),
                "profit_jpy": st.column_config.NumberColumn("利益(円)", format="¥%.0f"),
                "profit_margin": st.column_config.NumberColumn("利益率", format="%.1f%%"),
                "created_at": "作成日時"
            }
        )

def main():
    """Main application function"""
    # Initialize
    initialize_session_state()
    configure_ebay_api()
    
    # Header
    st.title("💰 Enhanced eBay Profit Calculator")
    st.markdown("**モジュラー構造で拡張された利益計算ツール**")
    
    # Navigation tabs
    tab1, tab2, tab3 = st.tabs(["🔍 商品リサーチ", "📋 下書き管理", "ℹ️ システム情報"])
    
    with tab1:
        enhanced_search_tab()
    
    with tab2:
        drafts_management_tab()
    
    with tab3:
        show_system_info()

def show_system_info():
    """Show system information and logs"""
    st.header("ℹ️ システム情報")
    
    # Module status
    st.subheader("🔧 モジュール状態")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        **データソース:**
        - ✅ eBay検索 (data_sources.ebay)
        - ✅ アイテム詳細取得
        
        **配送計算:**
        - ✅ ゾーン判定 (shipping.calc)
        - ✅ 料金計算
        - ✅ 重量推定
        """)
    
    with col2:
        st.markdown("""
        **AI機能:**
        - ✅ タイトルリライト (utils.openai_rewrite)
        - ✅ 説明文生成
        
        **ユーティリティ:**
        - ✅ 為替レート (utils.fx)
        - ✅ 構造化ログ (utils.logging_utils)
        """)
    
    # Log summary
    from utils.logging_utils import display_log_summary
    display_log_summary()
    
    # API status
    st.subheader("🌐 API状態")
    
    # Test eBay API
    if st.button("🔧 eBay API テスト"):
        test_result = ebay_api.test_api_connection()
        if test_result.get("success"):
            st.success("✅ eBay API接続成功")
        else:
            st.error(f"❌ eBay API接続失敗: {test_result.get('errors', [])}")
    
    # FX rate status
    from utils.fx import get_rate_status
    fx_status = get_rate_status()
    
    if fx_status.get("api_available"):
        st.success(f"✅ 為替レートAPI正常 (1 USD = {fx_status['current_rate']:.2f} JPY)")
    else:
        st.warning("⚠️ 為替レートAPIエラー、フォールバック値使用中")

if __name__ == "__main__":
    main()
