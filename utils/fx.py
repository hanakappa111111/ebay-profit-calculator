"""
為替レート取得ユーティリティ
"""
import requests
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional
import streamlit as st

# ロガー設定
logger = logging.getLogger(__name__)

# フォールバック為替レート
DEFAULT_USD_JPY = 150.0

@st.cache_data(ttl=3600)  # 1時間キャッシュ
def get_rate(from_currency: str = "USD", to_currency: str = "JPY") -> Dict:
    """
    為替レートを取得（1時間キャッシュ）
    
    Args:
        from_currency: 変換元通貨（例: "USD"）
        to_currency: 変換先通貨（例: "JPY"）
        
    Returns:
        Dict: {"rate": float, "timestamp": str, "success": bool, "source": str}
    """
    try:
        # exchangerate.host API を使用
        api_url = f"https://api.exchangerate.host/latest"
        params = {
            "base": from_currency,
            "symbols": to_currency
        }
        
        logger.debug(f"Fetching exchange rate: {from_currency} -> {to_currency}")
        
        response = requests.get(api_url, params=params, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        
        if data.get("success", False) and to_currency in data.get("rates", {}):
            rate = float(data["rates"][to_currency])
            timestamp = datetime.now().isoformat()
            
            logger.info(f"Exchange rate fetched: 1 {from_currency} = {rate:.2f} {to_currency}")
            
            return {
                "rate": rate,
                "timestamp": timestamp,
                "success": True,
                "source": "exchangerate.host",
                "date": data.get("date", ""),
                "base": from_currency,
                "target": to_currency
            }
        else:
            raise ValueError("Invalid API response or rate not found")
            
    except Exception as e:
        logger.warning(f"Error fetching exchange rate from API: {e}")
        
        # フォールバック: 固定レート
        fallback_rate = _get_fallback_rate(from_currency, to_currency)
        timestamp = datetime.now().isoformat()
        
        logger.info(f"Using fallback rate: 1 {from_currency} = {fallback_rate:.2f} {to_currency}")
        
        return {
            "rate": fallback_rate,
            "timestamp": timestamp,
            "success": False,
            "source": "fallback",
            "error": str(e),
            "base": from_currency,
            "target": to_currency
        }


def _get_fallback_rate(from_currency: str, to_currency: str) -> float:
    """フォールバック為替レートを取得"""
    
    # 主要通貨ペアの固定レート（2024年基準）
    fallback_rates = {
        ("USD", "JPY"): 150.0,
        ("JPY", "USD"): 1 / 150.0,
        ("EUR", "JPY"): 165.0,
        ("JPY", "EUR"): 1 / 165.0,
        ("GBP", "JPY"): 185.0,
        ("JPY", "GBP"): 1 / 185.0,
        ("AUD", "JPY"): 100.0,
        ("JPY", "AUD"): 1 / 100.0,
        ("CAD", "JPY"): 110.0,
        ("JPY", "CAD"): 1 / 110.0,
        ("USD", "EUR"): 0.91,
        ("EUR", "USD"): 1.10,
        ("USD", "GBP"): 0.81,
        ("GBP", "USD"): 1.23,
    }
    
    rate_key = (from_currency.upper(), to_currency.upper())
    
    if rate_key in fallback_rates:
        return fallback_rates[rate_key]
    else:
        # 同一通貨または不明な組み合わせ
        if from_currency.upper() == to_currency.upper():
            return 1.0
        else:
            # デフォルト
            return DEFAULT_USD_JPY if to_currency.upper() == "JPY" else 1.0


def convert_currency(amount: float, from_currency: str = "USD", to_currency: str = "JPY") -> Dict:
    """
    通貨変換を実行
    
    Args:
        amount: 金額
        from_currency: 変換元通貨
        to_currency: 変換先通貨
        
    Returns:
        Dict: 変換結果
    """
    try:
        rate_info = get_rate(from_currency, to_currency)
        
        converted_amount = amount * rate_info["rate"]
        
        result = {
            "original_amount": amount,
            "converted_amount": converted_amount,
            "from_currency": from_currency,
            "to_currency": to_currency,
            "rate": rate_info["rate"],
            "timestamp": rate_info["timestamp"],
            "source": rate_info["source"],
            "success": True
        }
        
        if not rate_info["success"]:
            result["warning"] = "フォールバックレートを使用"
        
        logger.debug(f"Currency conversion: {amount} {from_currency} = {converted_amount:.2f} {to_currency}")
        
        return result
        
    except Exception as e:
        logger.error(f"Error converting currency: {e}")
        return {
            "original_amount": amount,
            "converted_amount": amount,
            "error": str(e),
            "success": False
        }


def format_currency(amount: float, currency: str = "JPY", show_symbol: bool = True) -> str:
    """
    通貨を適切な形式でフォーマット
    
    Args:
        amount: 金額
        currency: 通貨コード
        show_symbol: 通貨記号を表示するか
        
    Returns:
        str: フォーマットされた金額
    """
    try:
        currency = currency.upper()
        
        # 通貨記号マッピング
        currency_symbols = {
            "JPY": "¥",
            "USD": "$",
            "EUR": "€", 
            "GBP": "£",
            "AUD": "A$",
            "CAD": "C$",
            "CNY": "¥",
            "KRW": "₩"
        }
        
        # 小数点以下の桁数
        decimal_places = {
            "JPY": 0,  # 円は整数
            "KRW": 0,  # ウォンは整数
        }
        
        # 桁数設定
        decimals = decimal_places.get(currency, 2)
        
        # 金額フォーマット
        if decimals == 0:
            formatted_amount = f"{amount:,.0f}"
        else:
            formatted_amount = f"{amount:,.{decimals}f}"
        
        # 通貨記号追加
        if show_symbol:
            symbol = currency_symbols.get(currency, currency + " ")
            if currency in ["USD", "EUR", "GBP", "AUD", "CAD"]:
                return f"{symbol}{formatted_amount}"
            else:
                return f"{formatted_amount}{symbol}"
        else:
            return formatted_amount
            
    except Exception as e:
        logger.error(f"Error formatting currency: {e}")
        return str(amount)


def get_rate_status() -> Dict:
    """
    現在の為替レート取得状況を確認
    
    Returns:
        Dict: ステータス情報
    """
    try:
        # 直近のレート取得を試行
        rate_info = get_rate("USD", "JPY")
        
        status = {
            "api_available": rate_info["success"],
            "current_rate": rate_info["rate"],
            "last_updated": rate_info["timestamp"],
            "source": rate_info["source"],
            "cache_ttl": "1 hour"
        }
        
        if not rate_info["success"]:
            status["warning"] = "API接続不可、フォールバックレート使用中"
        
        return status
        
    except Exception as e:
        logger.error(f"Error getting rate status: {e}")
        return {
            "api_available": False,
            "error": str(e)
        }


def clear_rate_cache():
    """為替レートキャッシュをクリア"""
    try:
        get_rate.clear()
        logger.info("Exchange rate cache cleared")
        return True
    except Exception as e:
        logger.error(f"Error clearing rate cache: {e}")
        return False


# Streamlit 用ヘルパー関数
def display_rate_badge(from_currency: str = "USD", to_currency: str = "JPY") -> None:
    """
    Streamlit で為替レートバッジを表示
    
    Args:
        from_currency: 変換元通貨
        to_currency: 変換先通貨
    """
    try:
        rate_info = get_rate(from_currency, to_currency)
        
        # ステータス色設定
        if rate_info["success"]:
            status_color = "🟢"
            status_text = "リアルタイム"
        else:
            status_color = "🟡"
            status_text = "フォールバック"
        
        # バッジ表示
        badge_text = f"{status_color} **1 {from_currency} = {rate_info['rate']:.2f} {to_currency}** ({status_text})"
        
        # タイムスタンプ
        try:
            timestamp = datetime.fromisoformat(rate_info["timestamp"].replace("Z", "+00:00"))
            time_str = timestamp.strftime("%m/%d %H:%M")
            badge_text += f" *{time_str}*"
        except:
            pass
        
        st.markdown(badge_text)
        
    except Exception as e:
        st.markdown(f"🔴 **為替レート取得エラー**: {e}")


# テスト用関数
def test_fx_functions():
    """為替機能のテスト"""
    print("=== FX Utility Test ===")
    
    # レート取得テスト
    print("\n1. Rate Fetching Test:")
    rate_info = get_rate("USD", "JPY")
    print(f"USD/JPY Rate: {rate_info}")
    
    # 通貨変換テスト
    print("\n2. Currency Conversion Test:")
    conversion = convert_currency(100, "USD", "JPY")
    print(f"$100 USD = {conversion}")
    
    # フォーマットテスト
    print("\n3. Currency Formatting Test:")
    amounts = [1234.56, 150000, 99.99]
    currencies = ["USD", "JPY", "EUR"]
    
    for amount, currency in zip(amounts, currencies):
        formatted = format_currency(amount, currency)
        print(f"{amount} {currency} -> {formatted}")
    
    # ステータステスト
    print("\n4. Rate Status Test:")
    status = get_rate_status()
    print(f"Status: {status}")


if __name__ == "__main__":
    test_fx_functions()
