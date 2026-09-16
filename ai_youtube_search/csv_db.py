import os
import csv
import json
from datetime import datetime
from typing import Optional, Dict, Any, List

CSV_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "transcripts_db.csv")

FIELDNAMES = [
    "video_id", "url", "title", "channel", "duration_str",
    "detected_languages", "created_at", "transcript_text",
    "transcript_json", "chapters_json"
]

class TranscriptCSVDatabase:
    """트랜스크립트 영구 저장 및 캐싱을 위한 안정적 경량 CSV 데이터베이스."""

    def __init__(self, file_path: str = CSV_PATH):
        self.file_path = file_path
        self._init_file()

    def _init_file(self):
        if not os.path.exists(self.file_path):
            with open(self.file_path, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.DictWriter(f, fieldnames=FIELDNAMES, extrasaction='ignore')
                writer.writeheader()

    def get_by_video_id(self, video_id: str) -> Optional[Dict[str, Any]]:
        """비디오 ID 또는 URL로 기존 레코드 검색."""
        if not os.path.exists(self.file_path) or not video_id:
            return None

        with open(self.file_path, "r", newline="", encoding="utf-8-sig") as f:
            for row in csv.DictReader(f):
                row_vid = row.get("video_id", "").strip()
                row_url = row.get("url", "").strip()
                if row_vid == video_id or (row_url and video_id in row_url):
                    try:
                        blocks = json.loads(row.get("transcript_json") or "[]")
                    except Exception:
                        blocks = []
                    try:
                        chapters = json.loads(row.get("chapters_json") or "[]")
                    except Exception:
                        chapters = []

                    langs = row.get("detected_languages") or row.get("language") or "다국어"

                    return {
                        **row,
                        "detected_languages": langs,
                        "transcript_blocks": blocks,
                        "chapters": chapters,
                    }
        return None

    def save_record(
        self,
        video_id: str,
        url: str,
        title: str,
        channel: str,
        duration_str: str,
        detected_languages: List[str] | str,
        transcript_text: str,
        transcript_blocks: List[Dict[str, Any]],
        chapters: Optional[List[Dict[str, Any]]] = None,
    ) -> bool:
        """기존 비디오 ID는 갱신하고 신규 비디오는 추가합니다. 구버전 컬럼과의 호환성 보장."""
        self._init_file()
        if isinstance(detected_languages, list):
            lang_str = ", ".join(detected_languages) if detected_languages else "다국어"
        else:
            lang_str = str(detected_languages or "다국어")

        new_entry = {
            "video_id": str(video_id).strip(),
            "url": str(url).strip(),
            "title": str(title).strip(),
            "channel": str(channel).strip(),
            "duration_str": str(duration_str).strip(),
            "detected_languages": lang_str,
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "transcript_text": transcript_text or "",
            "transcript_json": json.dumps(transcript_blocks or [], ensure_ascii=False),
            "chapters_json": json.dumps(chapters or [], ensure_ascii=False),
        }

        rows = []
        updated = False

        if os.path.exists(self.file_path):
            with open(self.file_path, "r", newline="", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                for r in reader:
                    cleaned_r = {k: r.get(k, "") for k in FIELDNAMES}
                    if not cleaned_r.get("detected_languages") and r.get("language"):
                        cleaned_r["detected_languages"] = r.get("language")

                    if cleaned_r.get("video_id") == video_id:
                        rows.append(new_entry)
                        updated = True
                    else:
                        rows.append(cleaned_r)

        if not updated:
            rows.append(new_entry)

        with open(self.file_path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=FIELDNAMES, extrasaction='ignore')
            writer.writeheader()
            writer.writerows(rows)

        return True

    def list_history(self) -> List[Dict[str, Any]]:
        """저장된 영상 목록 요약 반환 (최신순)."""
        if not os.path.exists(self.file_path):
            return []

        with open(self.file_path, "r", newline="", encoding="utf-8-sig") as f:
            records = []
            for r in csv.DictReader(f):
                langs = r.get("detected_languages") or r.get("language") or "다국어"
                records.append({
                    "video_id": r.get("video_id"),
                    "url": r.get("url"),
                    "title": r.get("title"),
                    "channel": r.get("channel"),
                    "duration_str": r.get("duration_str"),
                    "detected_languages": langs,
                    "created_at": r.get("created_at"),
                })
        return list(reversed(records))
