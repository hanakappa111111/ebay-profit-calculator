"""
eBay 出品下書き管理モジュール
"""
import json
import os
from datetime import datetime
from typing import Dict, List, Optional
from pathlib import Path
import logging
from pydantic import BaseModel, ValidationError

# ロガー設定
logger = logging.getLogger(__name__)

# 下書き保存用ディレクトリ
DRAFTS_DIR = Path("logs/drafts")
DRAFTS_DIR.mkdir(parents=True, exist_ok=True)

class DraftPayload(BaseModel):
    """下書きペイロードのバリデーションモデル"""
    item_id: str
    title: str
    price_usd: float
    shipping_usd: float
    condition: str
    purchase_price_jpy: int
    profit_jpy: float
    profit_margin: float
    seller: str
    sold_date: str
    category: Optional[str] = None
    image_url: Optional[str] = None
    ebay_url: Optional[str] = None
    notes: Optional[str] = None
    created_at: Optional[str] = None


def save_draft(payload: Dict) -> Dict:
    """
    下書きをローカルJSONファイルに保存
    
    Args:
        payload: 下書きデータ（辞書形式）
        
    Returns:
        Dict: 保存結果
    """
    try:
        # 作成時刻を追加
        payload["created_at"] = datetime.now().isoformat()
        
        # Pydanticバリデーション
        try:
            validated_payload = DraftPayload(**payload)
        except ValidationError as e:
            logger.error(f"Validation error: {e}")
            return {
                "success": False,
                "error": f"バリデーションエラー: {e}",
                "details": str(e)
            }
        
        # ファイル名生成（日時 + アイテムID）
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"draft_{timestamp}_{validated_payload.item_id}.json"
        filepath = DRAFTS_DIR / filename
        
        # JSONファイルに保存
        with open(filepath, 'w', encoding='utf-8') as f:
            # Pydantic v2 compatibility
            if hasattr(validated_payload, 'model_dump'):
                json.dump(validated_payload.model_dump(), f, ensure_ascii=False, indent=2)
            else:
                json.dump(validated_payload.dict(), f, ensure_ascii=False, indent=2)
        
        logger.info(f"Draft saved successfully: {filename}")
        
        return {
            "success": True,
            "message": "下書きが正常に保存されました",
            "filename": filename,
            "filepath": str(filepath),
            "draft_id": f"{timestamp}_{validated_payload.item_id}"
        }
        
    except Exception as e:
        logger.error(f"Error saving draft: {e}")
        return {
            "success": False,
            "error": f"下書き保存エラー: {str(e)}"
        }


def load_draft(draft_id: str) -> Optional[Dict]:
    """
    指定された下書きIDの下書きを読み込み
    
    Args:
        draft_id: 下書きID
        
    Returns:
        Optional[Dict]: 下書きデータ
    """
    try:
        # ファイル検索
        for filepath in DRAFTS_DIR.glob(f"draft_*{draft_id}*.json"):
            with open(filepath, 'r', encoding='utf-8') as f:
                draft_data = json.load(f)
            
            logger.info(f"Draft loaded successfully: {filepath.name}")
            return draft_data
        
        logger.warning(f"Draft not found: {draft_id}")
        return None
        
    except Exception as e:
        logger.error(f"Error loading draft: {e}")
        return None


def list_drafts(limit: int = 50) -> List[Dict]:
    """
    保存された下書き一覧を取得
    
    Args:
        limit: 取得件数上限
        
    Returns:
        List[Dict]: 下書き一覧
    """
    try:
        drafts = []
        
        # 下書きファイル一覧を取得（新しい順）
        draft_files = sorted(
            DRAFTS_DIR.glob("draft_*.json"),
            key=lambda x: x.stat().st_mtime,
            reverse=True
        )[:limit]
        
        for filepath in draft_files:
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    draft_data = json.load(f)
                
                # サマリー情報を追加
                draft_summary = {
                    "draft_id": filepath.stem.replace("draft_", ""),
                    "title": draft_data.get("title", ""),
                    "price_usd": draft_data.get("price_usd", 0),
                    "profit_jpy": draft_data.get("profit_jpy", 0),
                    "profit_margin": draft_data.get("profit_margin", 0),
                    "created_at": draft_data.get("created_at", ""),
                    "filename": filepath.name
                }
                
                drafts.append(draft_summary)
                
            except Exception as e:
                logger.warning(f"Error reading draft file {filepath}: {e}")
                continue
        
        logger.info(f"Listed {len(drafts)} drafts")
        return drafts
        
    except Exception as e:
        logger.error(f"Error listing drafts: {e}")
        return []


def delete_draft(draft_id: str) -> Dict:
    """
    指定された下書きを削除
    
    Args:
        draft_id: 下書きID
        
    Returns:
        Dict: 削除結果
    """
    try:
        # ファイル検索・削除
        deleted_count = 0
        for filepath in DRAFTS_DIR.glob(f"draft_*{draft_id}*.json"):
            filepath.unlink()
            deleted_count += 1
            logger.info(f"Draft deleted: {filepath.name}")
        
        if deleted_count > 0:
            return {
                "success": True,
                "message": f"{deleted_count}件の下書きを削除しました",
                "deleted_count": deleted_count
            }
        else:
            return {
                "success": False,
                "error": "該当する下書きが見つかりませんでした"
            }
            
    except Exception as e:
        logger.error(f"Error deleting draft: {e}")
        return {
            "success": False,
            "error": f"下書き削除エラー: {str(e)}"
        }


def export_drafts_to_csv(draft_ids: List[str] = None) -> Dict:
    """
    下書きをCSV形式でエクスポート
    
    Args:
        draft_ids: エクスポートする下書きIDのリスト（Noneの場合は全件）
        
    Returns:
        Dict: エクスポート結果
    """
    try:
        import pandas as pd
        
        drafts_data = []
        
        if draft_ids:
            # 指定された下書きのみ
            for draft_id in draft_ids:
                draft = load_draft(draft_id)
                if draft:
                    drafts_data.append(draft)
        else:
            # 全下書き
            draft_files = list(DRAFTS_DIR.glob("draft_*.json"))
            for filepath in draft_files:
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        draft_data = json.load(f)
                    drafts_data.append(draft_data)
                except:
                    continue
        
        if not drafts_data:
            return {
                "success": False,
                "error": "エクスポートする下書きがありません"
            }
        
        # DataFrame作成
        df = pd.DataFrame(drafts_data)
        
        # CSV出力
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        csv_filename = f"drafts_export_{timestamp}.csv"
        csv_filepath = DRAFTS_DIR / csv_filename
        
        df.to_csv(csv_filepath, index=False, encoding='utf-8-sig')
        
        logger.info(f"Drafts exported to CSV: {csv_filename}")
        
        return {
            "success": True,
            "message": f"{len(drafts_data)}件の下書きをCSVエクスポートしました",
            "filename": csv_filename,
            "filepath": str(csv_filepath),
            "count": len(drafts_data)
        }
        
    except Exception as e:
        logger.error(f"Error exporting drafts to CSV: {e}")
        return {
            "success": False,
            "error": f"CSVエクスポートエラー: {str(e)}"
        }


# 統計情報取得
def get_draft_stats() -> Dict:
    """下書きの統計情報を取得"""
    try:
        drafts = list_drafts()
        
        if not drafts:
            return {
                "total_drafts": 0,
                "avg_profit_jpy": 0,
                "avg_profit_margin": 0,
                "total_investment_jpy": 0
            }
        
        total_profit = sum(d.get("profit_jpy", 0) for d in drafts)
        total_margin = sum(d.get("profit_margin", 0) for d in drafts)
        
        return {
            "total_drafts": len(drafts),
            "avg_profit_jpy": round(total_profit / len(drafts), 0),
            "avg_profit_margin": round(total_margin / len(drafts), 1),
            "highest_profit": max(d.get("profit_jpy", 0) for d in drafts),
            "lowest_profit": min(d.get("profit_jpy", 0) for d in drafts)
        }
        
    except Exception as e:
        logger.error(f"Error getting draft stats: {e}")
        return {"error": str(e)}


# テスト用関数
def test_draft_operations():
    """下書き操作のテスト"""
    # テスト用ペイロード
    test_payload = {
        "item_id": "test123456789",
        "title": "テスト商品 Nintendo Switch",
        "price_usd": 250.0,
        "shipping_usd": 20.0,
        "condition": "中古 - 良い",
        "purchase_price_jpy": 35000,
        "profit_jpy": 2500.0,
        "profit_margin": 7.1,
        "seller": "test_seller (評価 100)",
        "sold_date": "2024-01-01",
        "notes": "テスト用下書き"
    }
    
    print("=== Draft Operations Test ===")
    
    # 保存テスト
    result = save_draft(test_payload)
    print(f"Save result: {result}")
    
    if result["success"]:
        draft_id = result["draft_id"]
        
        # 読み込みテスト
        loaded = load_draft(draft_id)
        print(f"Loaded draft: {loaded['title'] if loaded else 'None'}")
        
        # 一覧テスト
        drafts = list_drafts(5)
        print(f"Total drafts: {len(drafts)}")
        
        # 統計テスト
        stats = get_draft_stats()
        print(f"Stats: {stats}")


if __name__ == "__main__":
    test_draft_operations()
