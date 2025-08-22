#!/usr/bin/env python3
"""
環境変数設定テストスクリプト
"""
import os
from dotenv import load_dotenv

def test_env_variables():
    """環境変数の読み込みをテスト"""
    print("🔧 環境変数設定テスト")
    print("=" * 40)
    
    # .envファイルを読み込み
    load_dotenv()
    
    # eBay API設定チェック
    print("📊 eBay API設定:")
    ebay_app_id = os.getenv('EBAY_APP_ID')
    ebay_dev_id = os.getenv('EBAY_DEV_ID')
    ebay_cert_id = os.getenv('EBAY_CERT_ID')
    ebay_env = os.getenv('EBAY_ENV')
    
    print(f"  App ID: {'✅ 設定済み' if ebay_app_id and ebay_app_id != 'your_ebay_app_id_here' else '❌ 未設定'}")
    print(f"  Dev ID: {'✅ 設定済み' if ebay_dev_id and ebay_dev_id != 'your_ebay_dev_id_here' else '❌ 未設定'}")
    print(f"  Cert ID: {'✅ 設定済み' if ebay_cert_id and ebay_cert_id != 'your_ebay_cert_id_here' else '❌ 未設定'}")
    print(f"  Environment: {ebay_env}")
    
    # OpenAI設定チェック（オプション）
    print("\n🤖 OpenAI設定:")
    openai_key = os.getenv('OPENAI_API_KEY')
    print(f"  API Key: {'✅ 設定済み' if openai_key and openai_key != 'your_openai_api_key_here' else '❌ 未設定（オプション）'}")
    
    # 設定値プレビュー（セキュリティのため一部のみ表示）
    print("\n🔍 設定値プレビュー:")
    if ebay_app_id and ebay_app_id != 'your_ebay_app_id_here':
        print(f"  App ID: {ebay_app_id[:10]}...{ebay_app_id[-4:]}")
    if ebay_cert_id and ebay_cert_id != 'your_ebay_cert_id_here':
        print(f"  Cert ID: {ebay_cert_id[:10]}...{ebay_cert_id[-4:]}")
    
    # 全体判定
    print("\n🎯 総合判定:")
    all_set = all([
        ebay_app_id and ebay_app_id != 'your_ebay_app_id_here',
        ebay_dev_id and ebay_dev_id != 'your_ebay_dev_id_here', 
        ebay_cert_id and ebay_cert_id != 'your_ebay_cert_id_here'
    ])
    
    if all_set:
        print("✅ eBay API設定完了！Streamlitアプリで実APIが使用できます")
    else:
        print("⚠️ 設定が不完全です。.envファイルを編集してください")
    
    return all_set

if __name__ == "__main__":
    test_env_variables()
