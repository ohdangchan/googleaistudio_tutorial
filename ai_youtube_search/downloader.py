import os
import re
from typing import Optional, Callable, Dict, Any
import yt_dlp

YOUTUBE_ID_REGEX = re.compile(
    r'(?:https?:\/\/)?(?:www\.|m\.)?(?:youtube\.com\/(?:watch\?.*?v=|embed\/|v\/|shorts\/)|youtu\.be\/)([a-zA-Z0-9_-]{11})'
)
RAW_ID_REGEX = re.compile(r'^[a-zA-Z0-9_-]{11}$')

class YouTubeDownloader:
    """유튜브 영상 URL 검증, 메타데이터 조회 및 오디오 다운로드 전담 클래스."""

    def __init__(self, download_dir: str = "downloads"):
        self.download_dir = download_dir
        os.makedirs(self.download_dir, exist_ok=True)

    @classmethod
    def extract_and_validate_video_id(cls, url: str) -> str:
        """유튜브 URL을 철저히 검증하고 11자리 비디오 ID를 추출합니다. 유효하지 않으면 ValueError 발생."""
        if not url or not isinstance(url, str):
            raise ValueError("URL이 입력되지 않았습니다.")
        
        cleaned = url.strip()
        if RAW_ID_REGEX.match(cleaned):
            return cleaned

        match = YOUTUBE_ID_REGEX.search(cleaned)
        if match:
            return match.group(1)

        raise ValueError("유효한 유튜브 영상 링크(URL) 형식이 아닙니다.")

    def get_video_info(self, url: str) -> Dict[str, Any]:
        """비디오를 다운로드하지 않고 메타데이터(제목, 채널, 재생 시간)를 빠르게 조회합니다."""
        video_id = self.extract_and_validate_video_id(url)
        clean_url = f"https://www.youtube.com/watch?v={video_id}"

        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'skip_download': True,
            'extract_flat': False,
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(clean_url, download=False)
        except Exception as e:
            raise ValueError(f"유튜브 영상 정보를 불러올 수 없습니다: {str(e)}")

        duration = int(info.get('duration') or 0)
        minutes, seconds = divmod(duration, 60)
        hours, minutes = divmod(minutes, 60)

        dur_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}" if hours > 0 else f"{minutes:02d}:{seconds:02d}"

        return {
            'video_id': info.get('id') or video_id,
            'title': info.get('title', 'YouTube Video'),
            'channel': info.get('uploader') or info.get('channel', 'Channel'),
            'duration_sec': duration,
            'duration_str': dur_str,
            'thumbnail': info.get('thumbnail') or f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg",
        }

    def download_audio(
        self,
        url: str,
        progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
    ) -> Dict[str, Any]:
        """오디오 파일을 다운로드하거나 로컬 캐시를 반환합니다."""
        info = self.get_video_info(url)
        video_id = info['video_id']

        # 1. 기존 다운로드 캐시 확인
        for ext in ['m4a', 'webm', 'mp3', 'opus']:
            cached_path = os.path.join(self.download_dir, f"{video_id}.{ext}")
            if os.path.exists(cached_path) and os.path.getsize(cached_path) > 1024:
                size_mb = round(os.path.getsize(cached_path) / (1024 * 1024), 2)
                return {
                    **info,
                    'file_path': cached_path,
                    'file_name': f"{video_id}.{ext}",
                    'file_size_mb': size_mb,
                    'mime_type': 'audio/mp4' if ext == 'm4a' else f'audio/{ext}',
                    'cached': True,
                }

        # 2. 신규 다운로드
        outtmpl = os.path.join(self.download_dir, f"{video_id}.%(ext)s")

        def hook(d):
            if progress_callback and d['status'] == 'downloading':
                total = d.get('total_bytes') or d.get('total_bytes_estimate') or 0
                downloaded = d.get('downloaded_bytes') or 0
                pct = round(downloaded / total * 100, 1) if total > 0 else 0
                progress_callback({
                    'status': 'downloading',
                    'percent': pct,
                    'speed': d.get('_speed_str', ''),
                })

        ydl_opts = {
            'format': 'bestaudio[ext=m4a]/bestaudio/best',
            'outtmpl': outtmpl,
            'quiet': True,
            'no_warnings': True,
            'progress_hooks': [hook],
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([f"https://www.youtube.com/watch?v={video_id}"])

        for ext in ['m4a', 'webm', 'mp3', 'opus']:
            target = os.path.join(self.download_dir, f"{video_id}.{ext}")
            if os.path.exists(target):
                size_mb = round(os.path.getsize(target) / (1024 * 1024), 2)
                return {
                    **info,
                    'file_path': target,
                    'file_name': f"{video_id}.{ext}",
                    'file_size_mb': size_mb,
                    'mime_type': 'audio/mp4' if ext == 'm4a' else f'audio/{ext}',
                    'cached': False,
                }

        raise RuntimeError("오디오 파일 다운로드에 실패했습니다.")
