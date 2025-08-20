"""
OpenAI を使用したタイトル・説明リライト機能
"""
import os
import logging
from typing import Optional, Dict
from dotenv import load_dotenv

try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    OpenAI = None

# 環境変数読み込み
load_dotenv()

# ロガー設定
logger = logging.getLogger(__name__)

# OpenAI クライアント
_client = None

def _get_client() -> Optional[OpenAI]:
    """OpenAI クライアントを取得"""
    global _client
    
    if not OPENAI_AVAILABLE:
        logger.warning("OpenAI library not available")
        return None
    
    if _client is None:
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            logger.warning("OPENAI_API_KEY not found in environment")
            return None
        
        try:
            _client = OpenAI(api_key=api_key)
            logger.info("OpenAI client initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing OpenAI client: {e}")
            return None
    
    return _client


def rewrite_title(original_title: str, target_market: str = "US", max_length: int = 80) -> Dict:
    """
    商品タイトルをリライト
    
    Args:
        original_title: 元のタイトル
        target_market: ターゲット市場（"US", "GB", "AU"など）
        max_length: 最大文字数
        
    Returns:
        Dict: リライト結果
    """
    try:
        client = _get_client()
        if not client:
            return {
                "success": False,
                "error": "OpenAI API key not configured",
                "original": original_title,
                "rewritten": original_title
            }
        
        # プロンプト作成
        prompt = f"""
あなたはeBayの商品タイトル最適化エキスパートです。

以下の日本語商品タイトルを、{target_market}市場向けの魅力的な英語eBayタイトルにリライトしてください。

元のタイトル: {original_title}

リライトの条件:
- 最大{max_length}文字以内
- eBayでの検索性を高めるキーワードを含める
- 商品の特徴や状態を明確に
- 自然で読みやすい英語
- ブランド名は正確に
- 重要な情報（モデル番号、サイズ、色等）を保持

リライトされたタイトルのみを出力してください。
"""
        
        # OpenAI API 呼び出し
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are an expert eBay listing optimizer."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2,  # 決定論的設定
            max_tokens=150
        )
        
        rewritten = response.choices[0].message.content.strip()
        
        # 文字数チェック
        if len(rewritten) > max_length:
            rewritten = rewritten[:max_length-3] + "..."
        
        logger.info(f"Title rewritten successfully: {len(rewritten)} chars")
        
        return {
            "success": True,
            "original": original_title,
            "rewritten": rewritten,
            "length": len(rewritten),
            "target_market": target_market
        }
        
    except Exception as e:
        logger.error(f"Error rewriting title: {e}")
        return {
            "success": False,
            "error": str(e),
            "original": original_title,
            "rewritten": original_title
        }


def rewrite_description(original_title: str, condition: str, category: str = "", additional_info: str = "") -> Dict:
    """
    商品説明をリライト
    
    Args:
        original_title: 商品タイトル
        condition: 商品状態
        category: 商品カテゴリ
        additional_info: 追加情報
        
    Returns:
        Dict: リライト結果
    """
    try:
        client = _get_client()
        if not client:
            return {
                "success": False,
                "error": "OpenAI API key not configured",
                "description": f"Description for {original_title}\n\nCondition: {condition}"
            }
        
        # プロンプト作成
        prompt = f"""
eBayの商品説明を作成してください。

商品情報:
- タイトル: {original_title}
- 状態: {condition}
- カテゴリ: {category}
- 追加情報: {additional_info}

以下の要件で説明文を作成:
- 英語で記述
- 魅力的で詳細な説明
- 商品の特徴や利点を強調
- 状態について正確に記述
- 配送や返品について簡潔に言及
- プロフェッショナルなトーン
- 200-300語程度
- HTMLタグは使用しない

説明文のみを出力してください。
"""
        
        # OpenAI API 呼び出し
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are an expert eBay listing description writer."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2,
            max_tokens=500
        )
        
        description = response.choices[0].message.content.strip()
        
        logger.info(f"Description rewritten successfully: {len(description)} chars")
        
        return {
            "success": True,
            "description": description,
            "length": len(description),
            "word_count": len(description.split())
        }
        
    except Exception as e:
        logger.error(f"Error rewriting description: {e}")
        return {
            "success": False,
            "error": str(e),
            "description": f"High-quality {original_title} in {condition} condition. Fast shipping from Japan. Please contact us for any questions."
        }


def suggest_keywords(title: str, category: str = "") -> Dict:
    """
    SEO キーワードを提案
    
    Args:
        title: 商品タイトル
        category: 商品カテゴリ
        
    Returns:
        Dict: キーワード提案結果
    """
    try:
        client = _get_client()
        if not client:
            return {
                "success": False,
                "error": "OpenAI API key not configured",
                "keywords": []
            }
        
        prompt = f"""
eBay商品のSEOキーワードを提案してください。

商品情報:
- タイトル: {title}
- カテゴリ: {category}

以下の条件でキーワードを提案:
- eBayで検索されやすいキーワード
- 商品に関連する検索用語
- ブランド、モデル、特徴を含む
- 10個程度のキーワード
- 各キーワードは1-3語程度

キーワードをカンマ区切りで出力してください。
"""
        
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are an eBay SEO specialist."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=200
        )
        
        keywords_text = response.choices[0].message.content.strip()
        keywords = [kw.strip() for kw in keywords_text.split(',')]
        
        logger.info(f"Generated {len(keywords)} SEO keywords")
        
        return {
            "success": True,
            "keywords": keywords,
            "count": len(keywords)
        }
        
    except Exception as e:
        logger.error(f"Error generating keywords: {e}")
        return {
            "success": False,
            "error": str(e),
            "keywords": []
        }


def translate_to_japanese(english_text: str) -> Dict:
    """
    英語テキストを日本語に翻訳
    
    Args:
        english_text: 英語テキスト
        
    Returns:
        Dict: 翻訳結果
    """
    try:
        client = _get_client()
        if not client:
            return {
                "success": False,
                "error": "OpenAI API key not configured",
                "translated": english_text
            }
        
        prompt = f"""
以下の英語テキストを自然な日本語に翻訳してください。

英語: {english_text}

翻訳条件:
- 自然で読みやすい日本語
- 商品説明として適切な表現
- 敬語は使わず、です・ます調
- 専門用語は適切に翻訳

翻訳結果のみを出力してください。
"""
        
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a professional Japanese translator."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2,
            max_tokens=400
        )
        
        translated = response.choices[0].message.content.strip()
        
        logger.info(f"Text translated to Japanese: {len(translated)} chars")
        
        return {
            "success": True,
            "original": english_text,
            "translated": translated
        }
        
    except Exception as e:
        logger.error(f"Error translating text: {e}")
        return {
            "success": False,
            "error": str(e),
            "translated": english_text
        }


# テスト用関数
def test_openai_functions():
    """OpenAI 機能のテスト"""
    print("=== OpenAI Rewrite Test ===")
    
    # タイトルリライトテスト
    test_title = "Nintendo Switch 本体 グレー 付属品完備"
    print(f"\n元のタイトル: {test_title}")
    
    title_result = rewrite_title(test_title, "US", 80)
    if title_result["success"]:
        print(f"リライト後: {title_result['rewritten']}")
        print(f"文字数: {title_result['length']}")
    else:
        print(f"エラー: {title_result['error']}")
    
    # 説明リライトテスト
    desc_result = rewrite_description(test_title, "中古 - 良い", "Video Games & Consoles")
    if desc_result["success"]:
        print(f"\n説明文: {desc_result['description'][:100]}...")
        print(f"文字数: {desc_result['length']}")
    else:
        print(f"エラー: {desc_result['error']}")
    
    # キーワード提案テスト
    keywords_result = suggest_keywords(test_title, "Video Games & Consoles")
    if keywords_result["success"]:
        print(f"\nSEOキーワード: {', '.join(keywords_result['keywords'][:5])}")
    else:
        print(f"エラー: {keywords_result['error']}")


if __name__ == "__main__":
    test_openai_functions()
