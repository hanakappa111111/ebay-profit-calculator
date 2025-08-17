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
    st.title("💰 eBay Profit Calculator")
    st.subheader("日本からeBayへの転売利益計算ツール")
    
    # Initialize session state for results
    if 'results_df' not in st.session_state:
        st.session_state.results_df = pd.DataFrame(columns=[
            'Item ID', 'Title', 'Selling Price (USD)', 'Supplier Cost (JPY)', 
            'Shipping Method', 'Shipping Cost (JPY)', 'eBay Fees (USD)', 
            'Profit (USD)', 'Margin (%)', 'Calculated At'
        ])
    
    # Main input section
    col1, col2 = st.columns(2)
    
    with col1:
        st.header("📝 Item Details")
        ebay_input = st.text_input("eBay URL or Item ID", 
                                  placeholder="Enter eBay URL or Item ID")
        supplier_price = st.number_input("Supplier Price (JPY)", 
                                       min_value=0.0, step=100.0, 
                                       help="仕入れ価格を入力してください")
    
    with col2:
        st.header("🚚 Shipping Settings")
        weight = st.number_input("Weight (grams)", 
                               min_value=1, max_value=10000, value=500,
                               help="商品の重量をグラムで入力")
        shipping_method = st.selectbox("Shipping Method", 
                                     ["EMS", "Air", "SAL", "Surface"])
    
    # Calculate button
    if st.button("Calculate Profit", type="primary"):
        if not ebay_input or supplier_price <= 0:
            st.error("Please enter both eBay URL/ID and supplier price")
            return
        
        with st.spinner("Fetching eBay data..."):
            item_data = ebay_api.get_item_details(ebay_input)
        
        if not item_data:
            st.error("Could not fetch eBay item data. Please check the URL/ID and try again.")
            return
        
        # Calculate shipping cost
        shipping_cost_jpy = calculate_shipping_cost(weight, shipping_method)
        
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
        st.header("📊 Calculation Results")
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Selling Price", f"${selling_price:.2f}")
        with col2:
            st.metric("Total Costs", f"${supplier_cost_usd + ebay_fees + shipping_cost_usd:.2f}")
        with col3:
            st.metric("Profit", f"${profit_usd:.2f}", 
                     delta=f"{margin_percent:.1f}%" if profit_usd > 0 else None)
        with col4:
            st.metric("Margin", f"{margin_percent:.1f}%")
        
        # Detailed breakdown
        st.subheader("💡 Breakdown")
        breakdown_data = {
            "Item": [
                "Selling Price (USD)",
                "Supplier Cost (JPY → USD)",
                "eBay Fees (USD)",
                "Shipping Cost (JPY → USD)",
                "Total Profit (USD)",
                "Profit Margin (%)"
            ],
            "Amount": [
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
            'Item ID': item_data.get('item_id', 'N/A'),
            'Title': item_data['title'],
            'Selling Price (USD)': f"${selling_price:.2f}",
            'Supplier Cost (JPY)': f"¥{supplier_price:,.0f}",
            'Shipping Method': shipping_method,
            'Shipping Cost (JPY)': f"¥{shipping_cost_jpy:,}",
            'eBay Fees (USD)': f"${ebay_fees:.2f}",
            'Profit (USD)': f"${profit_usd:.2f}",
            'Margin (%)': f"{margin_percent:.1f}%",
            'Calculated At': datetime.now().strftime("%Y-%m-%d %H:%M")
        }])
        
        st.session_state.results_df = pd.concat([new_row, st.session_state.results_df], 
                                              ignore_index=True)
    
    # Results history
    if not st.session_state.results_df.empty:
        st.header("📋 Calculation History")
        st.dataframe(st.session_state.results_df, use_container_width=True)
        
        # CSV download
        csv_buffer = io.StringIO()
        st.session_state.results_df.to_csv(csv_buffer, index=False)
        csv_data = csv_buffer.getvalue()
        
        st.download_button(
            label="📥 Download Results as CSV",
            data=csv_data,
            file_name=f"ebay_profit_analysis_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
            mime="text/csv"
        )
        
        # Clear history button
        if st.button("🗑️ Clear History"):
            st.session_state.results_df = pd.DataFrame(columns=[
                'Item ID', 'Title', 'Selling Price (USD)', 'Supplier Cost (JPY)', 
                'Shipping Method', 'Shipping Cost (JPY)', 'eBay Fees (USD)', 
                'Profit (USD)', 'Margin (%)', 'Calculated At'
            ])
            st.rerun()
    
    # Sidebar with shipping rates
    with st.sidebar:
        st.header("📦 Japan Post Shipping Rates")
        rates = load_shipping_rates()
        
        for method, rate_table in rates.items():
            with st.expander(f"{method} Rates"):
                for weight_range, cost in rate_table.items():
                    st.write(f"{weight_range.replace('_', ' ').title()}: ¥{cost:,}")
        
        st.header("ℹ️ Notes")
        st.write("""
        - Prices are in Japanese Yen (JPY) for shipping
        - eBay fees typically range from 8.75% to 12.75%
        - Currency conversion uses approximate rates
        - For accurate API data, configure eBay API keys
        """)

if __name__ == "__main__":
    main() 