"""
構造化ログユーティリティ（JSON Lines形式）
"""
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional
import streamlit as st

# ログディレクトリ
LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)

class JSONLinesLogger:
    """JSON Lines形式でログを出力するクラス"""
    
    def __init__(self, log_name: str = "app"):
        self.log_name = log_name
        self.log_file = self._get_log_file()
        
        # 標準ロガー設定
        self.logger = logging.getLogger(f"jsonl_{log_name}")
        self.logger.setLevel(logging.INFO)
        
        # ハンドラーが既に設定されている場合はスキップ
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
    
    def _get_log_file(self) -> Path:
        """日付ベースのログファイルパスを取得"""
        today = datetime.now().strftime("%Y%m%d")
        return LOG_DIR / f"{self.log_name}-{today}.jsonl"
    
    def log_event(self, event_type: str, data: Dict[str, Any], level: str = "info", user_session: Optional[str] = None) -> None:
        """
        イベントをJSON Lines形式でログ出力
        
        Args:
            event_type: イベントタイプ（例: "search", "draft_save", "error"）
            data: ログデータ
            level: ログレベル
            user_session: ユーザーセッションID
        """
        try:
            # セッション情報を取得（Streamlit環境）
            if user_session is None and hasattr(st, 'session_state'):
                try:
                    if 'session_id' not in st.session_state:
                        import uuid
                        st.session_state.session_id = str(uuid.uuid4())[:8]
                    user_session = st.session_state.session_id
                except:
                    user_session = "unknown"
            
            # ログエントリー作成
            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "event_type": event_type,
                "level": level.upper(),
                "session_id": user_session,
                "data": data
            }
            
            # JSON Lines形式でファイル出力
            with open(self.log_file, 'a', encoding='utf-8') as f:
                json.dump(log_entry, f, ensure_ascii=False, separators=(',', ':'))
                f.write('\n')
            
            # 標準ログにも出力
            log_message = f"[{event_type}] {json.dumps(data, ensure_ascii=False, separators=(',', ':'))}"
            
            if level.lower() == "error":
                self.logger.error(log_message)
            elif level.lower() == "warning":
                self.logger.warning(log_message)
            elif level.lower() == "debug":
                self.logger.debug(log_message)
            else:
                self.logger.info(log_message)
                
        except Exception as e:
            # ログ出力エラーは標準ログにのみ記録
            self.logger.error(f"Error writing JSON log: {e}")
    
    def log_search(self, keyword: str, results_count: int, processing_time: float) -> None:
        """検索イベントをログ"""
        self.log_event("search", {
            "keyword": keyword,
            "results_count": results_count,
            "processing_time_seconds": processing_time,
            "timestamp": datetime.now().isoformat()
        })
    
    def log_draft_save(self, item_id: str, title: str, profit_jpy: float, success: bool) -> None:
        """下書き保存イベントをログ"""
        self.log_event("draft_save", {
            "item_id": item_id,
            "title": title,
            "profit_jpy": profit_jpy,
            "success": success,
            "timestamp": datetime.now().isoformat()
        })
    
    def log_error(self, error_type: str, error_message: str, context: Dict[str, Any] = None) -> None:
        """エラーイベントをログ"""
        error_data = {
            "error_type": error_type,
            "error_message": error_message,
            "timestamp": datetime.now().isoformat()
        }
        
        if context:
            error_data["context"] = context
        
        self.log_event("error", error_data, level="error")
    
    def log_user_action(self, action: str, details: Dict[str, Any] = None) -> None:
        """ユーザーアクションをログ"""
        action_data = {
            "action": action,
            "timestamp": datetime.now().isoformat()
        }
        
        if details:
            action_data["details"] = details
        
        self.log_event("user_action", action_data)
    
    def log_api_call(self, api_name: str, endpoint: str, success: bool, response_time: float, status_code: int = None) -> None:
        """API呼び出しをログ"""
        self.log_event("api_call", {
            "api_name": api_name,
            "endpoint": endpoint,
            "success": success,
            "response_time_seconds": response_time,
            "status_code": status_code,
            "timestamp": datetime.now().isoformat()
        })


# グローバルロガーインスタンス
_app_logger = None

def get_app_logger() -> JSONLinesLogger:
    """アプリケーション用ロガーを取得"""
    global _app_logger
    if _app_logger is None:
        _app_logger = JSONLinesLogger("app")
    return _app_logger


def read_log_entries(log_date: str = None, event_type: str = None, limit: int = 100) -> list:
    """
    ログエントリーを読み込み
    
    Args:
        log_date: 読み込む日付（YYYYMMDD形式）
        event_type: フィルタするイベントタイプ
        limit: 最大読み込み件数
        
    Returns:
        list: ログエントリーのリスト
    """
    try:
        if log_date is None:
            log_date = datetime.now().strftime("%Y%m%d")
        
        log_file = LOG_DIR / f"app-{log_date}.jsonl"
        
        if not log_file.exists():
            return []
        
        entries = []
        with open(log_file, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    try:
                        entry = json.loads(line)
                        
                        # イベントタイプフィルタ
                        if event_type and entry.get("event_type") != event_type:
                            continue
                        
                        entries.append(entry)
                        
                        # 制限チェック
                        if len(entries) >= limit:
                            break
                            
                    except json.JSONDecodeError:
                        continue
        
        # 新しい順にソート
        entries.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        
        return entries
        
    except Exception as e:
        logging.error(f"Error reading log entries: {e}")
        return []


def get_log_stats(log_date: str = None) -> Dict[str, Any]:
    """
    ログ統計を取得
    
    Args:
        log_date: 統計対象日付（YYYYMMDD形式）
        
    Returns:
        Dict: 統計情報
    """
    try:
        entries = read_log_entries(log_date, limit=10000)
        
        if not entries:
            return {"total_events": 0}
        
        # イベントタイプ別集計
        event_counts = {}
        error_count = 0
        
        for entry in entries:
            event_type = entry.get("event_type", "unknown")
            event_counts[event_type] = event_counts.get(event_type, 0) + 1
            
            if entry.get("level") == "ERROR":
                error_count += 1
        
        # 時間帯別集計
        hourly_counts = {}
        for entry in entries:
            try:
                timestamp = datetime.fromisoformat(entry.get("timestamp", ""))
                hour = timestamp.hour
                hourly_counts[hour] = hourly_counts.get(hour, 0) + 1
            except:
                continue
        
        stats = {
            "total_events": len(entries),
            "event_types": event_counts,
            "error_count": error_count,
            "hourly_distribution": hourly_counts,
            "date": log_date or datetime.now().strftime("%Y%m%d")
        }
        
        return stats
        
    except Exception as e:
        logging.error(f"Error getting log stats: {e}")
        return {"error": str(e)}


def cleanup_old_logs(days_to_keep: int = 30) -> int:
    """
    古いログファイルを削除
    
    Args:
        days_to_keep: 保持日数
        
    Returns:
        int: 削除されたファイル数
    """
    try:
        cutoff_date = datetime.now() - timedelta(days=days_to_keep)
        deleted_count = 0
        
        for log_file in LOG_DIR.glob("*.jsonl"):
            if log_file.stat().st_mtime < cutoff_date.timestamp():
                log_file.unlink()
                deleted_count += 1
        
        logging.info(f"Cleaned up {deleted_count} old log files")
        return deleted_count
        
    except Exception as e:
        logging.error(f"Error cleaning up old logs: {e}")
        return 0


# Streamlit用ヘルパー関数
def display_log_summary() -> None:
    """Streamlitでログ要約を表示"""
    try:
        today_stats = get_log_stats()
        
        if today_stats.get("total_events", 0) > 0:
            st.markdown("### 📊 今日のアクティビティ")
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("総イベント数", today_stats["total_events"])
            
            with col2:
                st.metric("エラー数", today_stats.get("error_count", 0))
            
            with col3:
                search_count = today_stats.get("event_types", {}).get("search", 0)
                st.metric("検索回数", search_count)
            
            # イベントタイプ別詳細
            if today_stats.get("event_types"):
                st.markdown("**イベント種別:**")
                for event_type, count in today_stats["event_types"].items():
                    st.write(f"- {event_type}: {count}回")
        else:
            st.info("今日のログデータはありません")
            
    except Exception as e:
        st.error(f"ログ要約表示エラー: {e}")


# テスト用関数
def test_logging_utils():
    """ログユーティリティのテスト"""
    print("=== Logging Utils Test ===")
    
    logger = get_app_logger()
    
    # 各種ログテスト
    logger.log_search("Nintendo Switch", 15, 0.5)
    logger.log_draft_save("test123", "Test Item", 2500.0, True)
    logger.log_user_action("button_click", {"button": "search"})
    logger.log_api_call("eBay", "/search", True, 1.2, 200)
    logger.log_error("validation_error", "Invalid item data")
    
    print("Test logs written")
    
    # ログ読み込みテスト
    entries = read_log_entries(limit=5)
    print(f"Read {len(entries)} log entries")
    
    # 統計テスト
    stats = get_log_stats()
    print(f"Log stats: {stats}")


if __name__ == "__main__":
    from datetime import timedelta
    test_logging_utils()
