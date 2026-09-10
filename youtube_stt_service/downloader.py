import os
import re
from typing import Callable, Optional, Dict, Any
import yt_dlp

class YouTubeDownloader:
    """YouTube 영상의 메타데이터 조회 및 오디오 스트림 다운로드를 처리하는 클래스."""

    def __init__(self, download_dir: str):
        self.download_dir = download_dir
        os.makedirs(self.download_dir, exist_ok=True)

    @staticmethod
    def is_valid_youtube_url(url: str) -> bool:
        """유효한 YouTube URL 패턴인지 검증합니다."""
        pattern = r"^(https?://)?(www\.|m\.)?(youtube\.com/(watch\?v=|shorts/|embed/)|youtu\.be/)[\w-]{11}"
        return bool(re.search(pattern, url.strip()))

    @staticmethod
    def format_duration(seconds: Optional[int]) -> str:
        """초 단위 재생 시간을 'MM:SS' 또는 'HH:MM:SS' 형식으로 포맷팅합니다."""
        if not seconds:
            return "00:00"
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60
        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{secs:02d}"
        return f"{minutes:02d}:{secs:02d}"

    def get_video_info(self, url: str) -> Dict[str, Any]:
        """비디오를 다운로드하지 않고 메타데이터만 신속하게 추출합니다."""
        url = url.strip()
        if not self.is_valid_youtube_url(url):
            raise ValueError("올바른 YouTube 영상 URL 형식이 아닙니다.")

        ydl_opts = {
            "quiet": True,
            "no_warnings": True,
            "skip_download": True,
            "extract_flat": False,
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                if not info:
                    raise ValueError("영상 정보를 불러올 수 없습니다.")

                video_id = info.get("id")
                title = info.get("title", "제목 없음")
                channel = info.get("uploader") or info.get("channel", "알 수 없는 채널")
                duration = info.get("duration", 0)
                thumbnail = info.get("thumbnail", "")

                # 캐시된 오디오 파일 확인
                cached_file = self.find_cached_audio(video_id)

                return {
                    "id": video_id,
                    "title": title,
                    "channel": channel,
                    "duration": duration,
                    "duration_str": self.format_duration(duration),
                    "thumbnail": thumbnail,
                    "url": url,
                    "is_cached": cached_file is not None,
                }
        except Exception as e:
            raise RuntimeError(f"YouTube 메타데이터 추출 실패: {str(e)}")

    def find_cached_audio(self, video_id: str) -> Optional[str]:
        """이미 다운로드된 오디오 파일이 존재하는지 확인합니다."""
        extensions = [".m4a", ".webm", ".opus", ".mp3", ".mp4", ".wav"]
        for ext in extensions:
            candidate = os.path.join(self.download_dir, f"{video_id}{ext}")
            if os.path.exists(candidate) and os.path.getsize(candidate) > 0:
                return candidate
        return None

    def download_audio(
        self,
        url: str,
        progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
    ) -> Dict[str, Any]:
        """영상에서 오디오 스트림(m4a/webm)을 다운로드합니다."""
        info = self.get_video_info(url)
        video_id = info["id"]

        # 이미 캐시된 오디오가 있으면 다운로드 생략
        cached_file = self.find_cached_audio(video_id)
        if cached_file:
            file_size = os.path.getsize(cached_file)
            mime_type = self._get_mime_type(cached_file)
            return {
                **info,
                "file_path": cached_file,
                "file_name": os.path.basename(cached_file),
                "file_size": file_size,
                "file_size_mb": round(file_size / (1024 * 1024), 2),
                "mime_type": mime_type,
                "is_cached": True,
            }

        outtmpl = os.path.join(self.download_dir, f"{video_id}.%(ext)s")

        def ydl_hook(d):
            if progress_callback and d["status"] == "downloading":
                total_bytes = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
                downloaded_bytes = d.get("downloaded_bytes") or 0
                percent = (downloaded_bytes / total_bytes * 100) if total_bytes > 0 else 0
                speed = d.get("speed") or 0
                speed_str = f"{speed / (1024 * 1024):.1f} MB/s" if speed else "계산 중..."
                progress_callback({
                    "status": "downloading",
                    "percent": round(percent, 1),
                    "downloaded_bytes": downloaded_bytes,
                    "total_bytes": total_bytes,
                    "speed": speed_str,
                    "eta": d.get("eta", 0),
                })
            elif progress_callback and d["status"] == "finished":
                progress_callback({
                    "status": "finished",
                    "percent": 100.0,
                })

        ydl_opts = {
            # ffmpeg 없이도 다운로드 가능한 고음질 m4a/webm 오디오 스트림 우선 추출
            "format": "bestaudio[ext=m4a]/bestaudio/best",
            "outtmpl": outtmpl,
            "quiet": True,
            "no_warnings": True,
            "noplaylist": True,
            "progress_hooks": [ydl_hook],
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])

            actual_file = self.find_cached_audio(video_id)
            if not actual_file or not os.path.exists(actual_file):
                raise FileNotFoundError("오디오 다운로드는 완료되었으나 파일을 찾을 수 없습니다.")

            file_size = os.path.getsize(actual_file)
            mime_type = self._get_mime_type(actual_file)

            return {
                **info,
                "file_path": actual_file,
                "file_name": os.path.basename(actual_file),
                "file_size": file_size,
                "file_size_mb": round(file_size / (1024 * 1024), 2),
                "mime_type": mime_type,
                "is_cached": False,
            }
        except Exception as e:
            raise RuntimeError(f"YouTube 오디오 다운로드 실패: {str(e)}")

    @staticmethod
    def _get_mime_type(file_path: str) -> str:
        """파일 확장자에 따른 MIME 타입을 매핑합니다."""
        ext = os.path.splitext(file_path)[1].lower()
        mime_map = {
            ".m4a": "audio/mp4",
            ".mp4": "audio/mp4",
            ".webm": "audio/webm",
            ".opus": "audio/opus",
            ".mp3": "audio/mp3",
            ".wav": "audio/wav",
            ".aac": "audio/aac",
            ".ogg": "audio/ogg",
        }
        return mime_map.get(ext, "audio/mp4")
