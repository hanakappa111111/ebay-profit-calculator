# 💰 Enhanced eBay Profit Calculator

**日本からeBayへの転売利益計算ツール（拡張版）**

モジュラー構造で拡張された、包括的なeBay転売利益計算プラットフォーム

## 🚀 新機能（Enhanced Version）

### ✨ **新しい抽象化アーキテクチャ**
- **モジュラー設計**: 機能別に分離された再利用可能なモジュール
- **データソース抽象化**: `data_sources/ebay.py` による検索・詳細取得
- **出品管理**: `publish/drafts.py` による下書き保存・管理
- **配送計算**: `shipping/calc.py` による高精度な配送料計算

### 🤖 **AI統合機能**
- **OpenAI タイトルリライト**: 市場に最適化されたタイトル生成
- **商品説明自動生成**: プロフェッショナルな説明文作成
- **SEOキーワード提案**: 検索最適化されたキーワード

### 📦 **高度な配送計算**
- **ゾーン別料金**: 60+ 国家の配送ゾーン判定
- **重量自動推定**: カテゴリ・タイトルベースの重量推定
- **最適配送選択**: ePacket/SmallPacket/EMS から最安選択

### 💱 **スマート為替管理**
- **リアルタイムレート**: exchangerate.host API統合
- **1時間キャッシュ**: Streamlitキャッシュによる高速化
- **フォールバック対応**: API障害時の固定レート

### 📊 **拡張UI/UX**
- **フィルタ・ソート**: 価格帯、状態、利益率での絞り込み
- **状態バッジ**: 為替レート、配送方法の視覚化
- **動的利益計算**: リアルタイムでの利益・利益率更新
- **セッション状態保持**: チェックボックス選択の永続化

### 📄 **CSV入出力機能**
- **選択エクスポート**: チェック済み商品のみCSV出力
- **UTF-8対応**: 日本語完全対応のCSVエクスポート
- **履歴インポート**: 過去の調査データ復元（今後実装）

### 📈 **バリデーション＆ログ**
- **Pydantic検証**: DraftPayloadモデルによる型安全性
- **構造化ログ**: JSON Lines形式による詳細ログ
- **統計情報**: 検索回数、利益分析、エラー追跡

## 🏗️ **新しいプロジェクト構造**

```
ebayseller/
├── app.py                    # レガシーアプリケーション
├── app_enhanced.py           # 🆕 拡張版アプリケーション
├── config.py                 # 設定ファイル
├── ebay_api.py              # eBay API統合
├── requirements.txt          # 🆕 拡張依存関係
├── test_modules.py          # 🆕 統合テストスイート
├── env_template.txt         # 🆕 環境変数テンプレート
│
├── data_sources/            # 🆕 データソース抽象化
│   ├── __init__.py
│   └── ebay.py             # eBay検索・詳細取得
│
├── publish/                 # 🆕 出品管理
│   ├── __init__.py
│   └── drafts.py           # 下書き保存・管理
│
├── shipping/                # 🆕 配送計算
│   ├── __init__.py
│   ├── zones.csv           # 国別配送ゾーン
│   ├── japan_post_rates.csv # 日本郵便料金表
│   └── calc.py             # 配送料計算ロジック
│
├── utils/                   # 🆕 ユーティリティ
│   ├── __init__.py
│   ├── fx.py               # 為替レート管理
│   ├── openai_rewrite.py   # AI文章リライト
│   └── logging_utils.py    # 構造化ログ
│
└── logs/                    # 🆕 ログ・下書き保存
    ├── app-YYYYMMDD.jsonl  # 日次アプリケーションログ
    └── drafts/             # 下書きJSONファイル
        └── draft_*.json
```

## 🚀 **クイックスタート（拡張版）**

### 前提条件
- Python 3.8以上
- pip パッケージマネージャー

### インストール

1. **リポジトリのクローン**
   ```bash
   cd ebayseller
   ```

2. **拡張依存関係のインストール**
   ```bash
   pip install -r requirements.txt
   ```

3. **環境変数の設定**
   ```bash
   cp env_template.txt .env
   # .envファイルを編集してAPIキーを設定
   ```

4. **統合テスト実行**
   ```bash
   python test_modules.py
   ```

5. **拡張アプリケーション起動**
   ```bash
   streamlit run app_enhanced.py
   ```

## ⚙️ **設定（拡張版）**

### 必須API設定

#### 1. eBay API
```bash
EBAY_APP_ID=your_app_id_here
EBAY_DEV_ID=your_dev_id_here  
EBAY_CERT_ID=your_cert_id_here
EBAY_ENV=production
```

#### 2. OpenAI API (オプション)
```bash
OPENAI_API_KEY=your_openai_api_key_here
```

### Streamlit Cloud設定

```toml
# secrets.toml
EBAY_APP_ID = "your_app_id"
EBAY_DEV_ID = "your_dev_id"
EBAY_CERT_ID = "your_cert_id"
EBAY_ENV = "production"
OPENAI_API_KEY = "your_openai_key"  # オプション
```

## 📋 **使用方法（拡張版）**

### 🔍 商品リサーチタブ

1. **キーワード検索**
   - キーワード入力（例: "Nintendo Switch", "iPhone"）
   - ターゲット市場選択（US, GB, AU, DE, CA）
   - 表示件数指定（5-50件）

2. **詳細設定**
   - ✅ AIタイトルリライト
   - ✅ 配送料計算  
   - ✅ 重量自動推定

3. **結果表示・分析**
   - フィルタ機能（価格帯、状態）
   - ソート機能（価格、利益率）
   - リアルタイム利益計算

4. **アクション**
   - 📄 CSVエクスポート（選択商品のみ）
   - 💾 下書き保存（Pydanticバリデーション付き）
   - 📈 収益分析（統計情報・グラフ）

### 📋 下書き管理タブ

1. **保存済み下書き一覧**
   - タイトル、価格、利益情報表示
   - 作成日時による管理

2. **統計情報**
   - 総予想利益
   - 平均利益率
   - 下書き数

### ℹ️ システム情報タブ

1. **モジュール状態**
   - 各モジュールの動作確認
   - API接続テスト

2. **ログ要約**
   - 今日のアクティビティ
   - エラー数、検索回数

## 🔧 **高度な機能**

### AIタイトルリライト
```python
from utils.openai_rewrite import rewrite_title

result = rewrite_title("Nintendo Switch 本体 グレー", "US", 80)
# → "Nintendo Switch Console Gray - Used Excellent Condition - Fast Ship"
```

### 配送料計算
```python
from shipping.calc import quote, zone

# 500gをアメリカに配送
shipping = quote(500, "US")
# → {"method": "ePacket", "cost_jpy": 1200, "delivery_days": "7-14", "zone": 1}
```

### 為替レート取得
```python
from utils.fx import get_rate, format_currency

rate = get_rate("USD", "JPY")  # 1時間キャッシュ
formatted = format_currency(150000, "JPY")  # → "¥150,000"
```

### 構造化ログ
```python
from utils.logging_utils import get_app_logger

logger = get_app_logger()
logger.log_search("Nintendo", 15, 0.5)  # JSON Lines形式で保存
```

## 📊 **ログ・統計情報**

### JSON Lines ログ形式
```json
{"timestamp": "2024-01-15T10:30:00", "event_type": "search", "session_id": "abc123", "data": {"keyword": "Nintendo", "results_count": 15}}
{"timestamp": "2024-01-15T10:35:00", "event_type": "draft_save", "session_id": "abc123", "data": {"item_id": "123456", "profit_jpy": 2500}}
```

### 統計ダッシュボード
- **日次アクティビティ**: 総イベント数、エラー数、検索回数
- **収益分析**: 平均利益、利益率分布、投資額
- **時間帯分析**: アクセス時間帯の分析

## 🧪 **テスト・品質保証**

### 統合テストスイート
```bash
python test_modules.py
```

**テスト対象**:
- ✅ データソース（検索・詳細取得）
- ✅ 配送計算（ゾーン・料金・重量推定）
- ✅ 為替ユーティリティ（レート取得・変換・フォーマット）
- ✅ 下書き管理（保存・一覧・バリデーション）
- ✅ ログユーティリティ（構造化ログ・統計）
- ✅ OpenAI統合（タイトルリライト）

## 🔒 **セキュリティ**

### APIキー管理
- ✅ Streamlit Secrets使用推奨
- ✅ 環境変数フォールバック
- ⚠️ ソースコードにAPIキー埋め込み禁止
- ✅ .gitignoreによる機密ファイル除外

### データ保護
- ✅ ローカルファイルシステムのみ使用
- ✅ セッションベースの一時データ
- ✅ Pydanticによる入力バリデーション

## 🎯 **拡張計算式**

### 基本利益計算
```
利益額 = 販売価格(JPY) - 仕入れ値(JPY) - 配送料(JPY) - 手数料(JPY)
利益率 = (利益額 ÷ 仕入れ値) × 100

手数料 = 販売価格(JPY) × 13%（固定）
```

### 配送料最適化
```
最適配送 = min(ePacket料金, SmallPacket料金, EMS料金)
※ 重量・配送先ゾーンに応じて自動選択
```

### 為替レート適用
```
JPY価格 = USD価格 × リアルタイムレート（1時間キャッシュ）
フォールバック = 150 JPY/USD（API障害時）
```

## 🐛 **トラブルシューティング**

### よくある問題

1. **"No module named 'data_sources'"**
   ```bash
   # Pythonパスを確認
   export PYTHONPATH="${PYTHONPATH}:$(pwd)"
   streamlit run app_enhanced.py
   ```

2. **"OPENAI_API_KEY not configured"**
   - OpenAI機能は無効化され、他の機能は正常動作
   - APIキー設定は任意（AI機能使用時のみ必要）

3. **"Exchange rate API failed"**
   - フォールバックレート（150 JPY/USD）で継続動作
   - インターネット接続を確認

4. **"Draft validation error"**
   - Pydanticバリデーションエラーログを確認
   - 必須フィールド（item_id, title, price_usd等）を確認

### デバッグモード
```bash
export DEBUG=true
streamlit run app_enhanced.py --logger.level=debug
```

## 📈 **今後の拡張予定**

### Phase 3 機能
- [ ] **在庫管理統合**: 仕入れ・売上の一元管理
- [ ] **自動価格監視**: 競合他社価格の自動チェック
- [ ] **メール通知**: 利益閾値達成時の自動通知
- [ ] **API レート制限**: 安全なAPI使用量管理

### Phase 4 機能  
- [ ] **マルチマーケット対応**: Mercari, Yahoo Auctions統合
- [ ] **機械学習予測**: 売れ筋商品の予測モデル
- [ ] **自動出品**: 設定条件での自動出品機能
- [ ] **ダッシュボード**: 総合的な販売分析

## 📞 **サポート・貢献**

### 問題報告
1. [GitHub Issues](https://github.com/your-repo/issues)で既存の問題を確認
2. 詳細な問題説明とログファイルを添付
3. 再現手順を明確に記載

### 機能提案
1. 新機能のユースケースを説明
2. 技術的実装案を提示
3. 既存機能への影響を評価

### 開発貢献
1. モジュラー構造に従った実装
2. 包括的なテストケース追加
3. ドキュメント更新

## 📄 **ライセンス**

MIT License - 商用利用、改変、再配布が可能です。

---

**🎉 Enhanced eBay Profit Calculator で効率的な転売ビジネスを！**

*Built with ❤️ using Python, Streamlit, OpenAI, and Modern Architecture*
