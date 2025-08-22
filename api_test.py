#!/usr/bin/env python3
"""
eBay API接続テストスクリプト
"""
import os
import sys
from dotenv import load_dotenv

# プロジェクトのモジュールをインポート
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_api_connection():
    """eBay API接続をテスト"""
    print("🔌 eBay API接続テスト")
    print("=" * 40)
    
    # 環境変数読み込み
    load_dotenv()
    
    try:
        # config.pyのインポートテスト
        from config import EBAY_CONFIG
        print("✅ config.py: 正常にインポート")
        
        # API設定表示
        print(f"📊 設定情報:")
        print(f"  App ID: {EBAY_CONFIG['app_id'][:10]}...{EBAY_CONFIG['app_id'][-4:]}")
        print(f"  Environment: {EBAY_CONFIG['environment']}")
        
    except Exception as e:
        print(f"❌ config.py インポートエラー: {e}")
        return False
    
    try:
        # eBay API クラステスト
        from ebay_api import eBayAPI
        api = eBayAPI()
        print("✅ eBayAPI: クラス初期化成功")
        
        # OAuth トークン取得テスト
        token = api.get_oauth_token()
        if token:
            print("✅ OAuth: トークン取得成功")
        else:
            print("❌ OAuth: トークン取得失敗")
            return False
            
    except Exception as e:
        print(f"❌ eBay API エラー: {e}")
        return False
    
    try:
        # 実際の検索テスト
        print("\n🔍 検索テスト実行中...")
        results = api.search_items("iPhone", limit=3)
        
        if results and len(results) > 0:
            print(f"✅ 検索成功: {len(results)}件取得")
            print(f"  最初の商品: {results[0].get('title', 'タイトル不明')[:50]}...")
            return True
        else:
            print("⚠️ 検索結果なし（APIは動作中）")
            return True
            
    except Exception as e:
        print(f"❌ 検索テストエラー: {e}")
        return False

if __name__ == "__main__":
    success = test_api_connection()
    
    print(f"\n🎯 総合結果: {'✅ 成功' if success else '❌ 失敗'}")
    
    if not success:
        print("\n🔧 トラブルシューティング:")
        print("1. .envファイルのAPI値を再確認")
        print("2. eBay Developer Portalで権限確認")
        print("3. python3 security_check.py でセキュリティ確認")
        print("4. インターネット接続確認")
