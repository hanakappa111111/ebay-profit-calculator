# 💰 eBay Profit Calculator

日本からeBayへの転売利益計算ツール (Japanese to eBay Reselling Profit Calculator)

A comprehensive Streamlit-based tool for calculating profit margins when reselling items from Japan to eBay, including accurate shipping costs from Japan Post and eBay fee calculations.

## ✨ Features

- **eBay Integration**: Automatically fetch item details from eBay URLs or Item IDs
- **Japan Post Shipping**: Calculate accurate shipping costs for EMS, Air, SAL, and Surface mail
- **Real-time Currency**: Live JPY to USD exchange rate conversion
- **eBay Fee Calculation**: Category-specific eBay final value fees
- **Profit Analysis**: Calculate profit amount and margin percentage
- **Data Export**: Save calculations to CSV for record keeping
- **Calculation History**: Track multiple item analyses in one session

## 🚀 Quick Start

### Prerequisites

- Python 3.8 or higher
- pip package manager

### Installation

1. **Clone or download this repository**
   ```bash
   cd ebayseller
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the application**
   ```bash
   streamlit run app.py
   ```

4. **Open your browser** to `http://localhost:8501`

## 📋 Usage Guide

### Basic Workflow

1. **Enter Item Details**:
   - eBay URL or Item ID (e.g., `https://www.ebay.com/itm/123456789` or `123456789`)
   - Supplier price in Japanese Yen (仕入れ価格)

2. **Configure Shipping**:
   - Enter item weight in grams
   - Select shipping method (EMS, Air, SAL, Surface)

3. **Calculate Profit**:
   - Click "Calculate Profit" button
   - View detailed breakdown of costs and profit

4. **Export Results**:
   - Download calculation history as CSV
   - Clear history when needed

### Input Examples

**eBay URLs (all formats supported)**:
- `https://www.ebay.com/itm/123456789012`
- `https://www.ebay.com/itm/123456789012?hash=item1234567890`
- `123456789012` (just the item ID)

**Supplier Prices**:
- Enter in Japanese Yen (JPY)
- Example: 3000 (for ¥3,000)

## 🏗️ Project Structure

```
ebayseller/
├── app.py              # Main Streamlit application
├── config.py           # Configuration settings and constants
├── ebay_api.py         # eBay API integration and web scraping
├── requirements.txt    # Python dependencies
└── README.md          # This file
```

## ⚙️ Configuration

### eBay API Setup (Optional)

For more accurate data, you can configure eBay API credentials:

1. **Get API credentials** from [eBay Developer Program](https://developer.ebay.com/)

2. **Set environment variables**:
   ```bash
   export EBAY_APP_ID="your_app_id"
   export EBAY_DEV_ID="your_dev_id" 
   export EBAY_CERT_ID="your_cert_id"
   export EBAY_ENV="production"  # or "sandbox"
   ```

3. **Without API credentials**, the tool uses web scraping as a fallback method.

### Currency Rate Configuration

- **Live rates**: Automatically fetched from exchange rate API
- **Fallback rate**: Configured in `config.py` (default: 150 JPY/USD)
- **Custom API**: Modify `get_currency_rate()` in `app.py` for different providers

## 📦 Shipping Rates

### Japan Post International Shipping Rates (JPY)

| Weight Range | EMS | Air | SAL | Surface |
|-------------|-----|-----|-----|---------|
| Up to 500g | 1,400 | 1,200 | 800 | 600 |
| 501-1000g | 2,000 | 1,800 | 1,200 | 900 |
| 1001-1500g | 2,800 | 2,400 | 1,600 | 1,200 |
| 1501-2000g | 3,600 | 3,000 | 2,000 | 1,500 |
| Over 2000g | 4,400 | 3,600 | 2,400 | 1,800 |

*Note: Rates are simplified and based on general Japan Post pricing. Always verify current rates on [Japan Post website](https://www.post.japanpost.jp/int/).*

## 💡 eBay Fee Structure

### Final Value Fees by Category

- **Default**: 12.75%
- **Electronics**: 8.75%
- **Motors & Vehicles**: 4%
- **Collectibles**: 15%
- **Business & Industrial**: 12.75%

*Note: eBay fees are subject to change. Refer to [eBay seller fees](https://www.ebay.com/help/selling/fees-credits-invoices/selling-fees) for current rates.*

## 🔧 Customization

### Adding New Shipping Methods

Edit `SHIPPING_RATES` in `config.py`:

```python
SHIPPING_RATES["YOUR_METHOD"] = {
    "up_to_500g": your_rate,
    "501_to_1000g": your_rate,
    # ... add more weight ranges
}
```

### Modifying Fee Rates

Update `EBAY_FEES` in `config.py`:

```python
EBAY_FEES["your_category"] = 0.10  # 10% fee
```

### Custom Currency Provider

Modify `get_currency_rate()` function in `app.py` to use your preferred exchange rate API.

## 🎯 Calculation Formula

```
Total Costs = Supplier Cost (USD) + eBay Fees (USD) + Shipping Cost (USD)
Profit = Selling Price (USD) - Total Costs
Margin % = (Profit ÷ Selling Price) × 100
```

**Where**:
- Supplier Cost (USD) = Supplier Price (JPY) ÷ Exchange Rate
- eBay Fees (USD) = Selling Price × Fee Rate
- Shipping Cost (USD) = Shipping Cost (JPY) ÷ Exchange Rate

## 🐛 Troubleshooting

### Common Issues

1. **"Could not extract item ID"**
   - Verify the eBay URL format
   - Try using just the numeric item ID

2. **"Could not fetch eBay item data"**
   - Check internet connection
   - eBay may be blocking requests (configure API credentials)
   - Item may no longer exist

3. **Incorrect shipping costs**
   - Verify item weight is accurate
   - Check if shipping method is available for your region

### Debug Mode

Set environment variable for debugging:
```bash
export DEBUG=true
streamlit run app.py
```

## 📈 Future Enhancements

- [ ] Multi-currency support
- [ ] Automated profit threshold alerts
- [ ] Integration with inventory management
- [ ] Historical profit trend analysis
- [ ] Bulk item analysis
- [ ] Advanced eBay category detection

## ⚖️ Legal Notice

This tool is for educational and personal use. When using eBay data:

- Respect eBay's robots.txt and terms of service
- Use official eBay APIs when possible
- Don't make excessive requests that could overload servers
- Verify all calculations independently

## 📞 Support

For issues, suggestions, or contributions:

1. Check existing GitHub issues
2. Create a new issue with detailed description
3. Include error messages and steps to reproduce

## 📄 License

This project is open source and available under the MIT License.

---

**Happy reselling! 🎉**

*Built with ❤️ using Streamlit and Python* 