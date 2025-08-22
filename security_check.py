#!/usr/bin/env python3
"""
セキュリティチェックスクリプト
"""
import os
import stat
import subprocess

def check_security():
    """プロジェクトのセキュリティ状態をチェック"""
    print("🔒 セキュリティチェック")
    print("=" * 40)
    
    security_score = 0
    max_score = 6
    
    # 1. .envファイルの存在確認
    if os.path.exists('.env'):
        print("✅ .envファイル: 存在")
        security_score += 1
        
        # ファイル権限チェック
        file_stat = os.stat('.env')
        file_mode = stat.filemode(file_stat.st_mode)
        if file_mode == '-rw-------':
            print("✅ .env権限: 安全 (600)")
            security_score += 1
        else:
            print(f"⚠️ .env権限: {file_mode} (推奨: -rw-------)")
    else:
        print("❌ .envファイル: 未作成")
    
    # 2. .gitignoreチェック
    try:
        with open('.gitignore', 'r') as f:
            gitignore_content = f.read()
            if '.env' in gitignore_content:
                print("✅ .gitignore: .envを除外済み")
                security_score += 1
            else:
                print("❌ .gitignore: .envが含まれていない")
    except FileNotFoundError:
        print("❌ .gitignore: ファイルが存在しない")
    
    # 3. Git追跡状態チェック
    try:
        result = subprocess.run(['git', 'ls-files', '.env'], 
                              capture_output=True, text=True)
        if result.returncode == 0 and result.stdout.strip():
            print("❌ Git追跡: .envがGitで追跡されています！")
        else:
            print("✅ Git追跡: .envは追跡されていない")
            security_score += 1
    except:
        print("⚠️ Git追跡: チェックできませんでした")
    
    # 4. 設定値チェック
    from dotenv import load_dotenv
    load_dotenv()
    
    api_keys = [
        ('EBAY_APP_ID', os.getenv('EBAY_APP_ID')),
        ('EBAY_DEV_ID', os.getenv('EBAY_DEV_ID')),
        ('EBAY_CERT_ID', os.getenv('EBAY_CERT_ID'))
    ]
    
    valid_keys = 0
    for key_name, key_value in api_keys:
        if key_value and key_value != f'your_{key_name.lower()}_here':
            valid_keys += 1
    
    if valid_keys == 3:
        print("✅ API設定: 全て設定済み")
        security_score += 1
    else:
        print(f"⚠️ API設定: {valid_keys}/3 設定済み")
    
    # 5. iCloud同期警告
    current_path = os.getcwd()
    if 'iCloud' in current_path:
        print("⚠️ iCloud同期: プロジェクトがiCloud配下にあります")
        print("   推奨: 非同期ディレクトリでの作業")
    else:
        print("✅ iCloud同期: 非同期ディレクトリ")
        security_score += 1
    
    # 総合評価
    print(f"\n🎯 セキュリティスコア: {security_score}/{max_score}")
    
    if security_score >= 5:
        print("✅ セキュリティ良好")
    elif security_score >= 3:
        print("⚠️ 改善の余地あり")
    else:
        print("❌ セキュリティ要改善")
    
    return security_score, max_score

if __name__ == "__main__":
    check_security()
