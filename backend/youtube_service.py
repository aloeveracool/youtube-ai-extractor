import os
import re
import math
from typing import Dict, Any, Optional, Callable
import yt_dlp
from youtube_transcript_api import YouTubeTranscriptApi
from .config import DOWNLOADS_DIR, FFMPEG_PATH

def extract_video_id(url: str) -> Optional[str]:
    patterns = [
        r'(?:v=|\/)([0-9A-Za-z_-]{11}).*',
        r'(?:youtu\.be\/)([0-9A-Za-z_-]{11})',
        r'(?:shorts\/)([0-9A-Za-z_-]{11})'
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None

def format_duration(seconds: int) -> str:
    if not seconds:
        return "00:00"
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    if h > 0:
        return f"{h:02d}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"

def format_timestamp(seconds: float) -> str:
    secs = int(seconds)
    m = secs // 60
    s = secs % 60
    h = m // 60
    m = m % 60
    if h > 0:
        return f"{h:02d}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"

def sanitize_filename(name: str) -> str:
    return re.sub(r'[\\/*?:"<>|]', "", name).strip()

def get_video_info(url: str) -> Dict[str, Any]:
    node_path = r"C:\Program Files\nodejs\node.exe" if os.name == 'nt' else "/usr/bin/node"
    ydl_opts = {
        'quiet': True,
        'skip_download': True,
        'ffmpeg_location': str(FFMPEG_PATH),
    }
    if os.path.exists(node_path):
        ydl_opts['js_runtimes'] = {'node': {'path': node_path}}

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
    
    formats = info.get('formats', [])
    resolutions = set()
    for f in formats:
        if f.get('vcodec') != 'none' and f.get('height'):
            h = f.get('height')
            if h in [2160, 1440, 1080, 720, 480, 360]:
                resolutions.add(h)
    
    sorted_res = sorted(list(resolutions), reverse=True)
    res_labels = [f"{h}p" for h in sorted_res]
    if not res_labels:
        res_labels = ["최고화질 (Best)"]
    else:
        res_labels.insert(0, "최고화질 (Best)")

    duration = info.get('duration', 0)
    video_id = info.get('id') or extract_video_id(url)
    
    return {
        "id": video_id,
        "title": info.get('title', '제목 없음'),
        "channel": info.get('uploader') or info.get('channel', '알 수 없음'),
        "duration": duration,
        "duration_str": format_duration(duration),
        "thumbnail": info.get('thumbnail') or f"https://i.ytimg.com/vi/{video_id}/maxresdefault.jpg",
        "view_count": info.get('view_count', 0),
        "available_resolutions": res_labels,
        "original_url": url
    }

def fetch_transcript(video_id_or_url: str) -> Dict[str, Any]:
    video_id = extract_video_id(video_id_or_url) if "http" in video_id_or_url else video_id_or_url
    if not video_id:
        return {"success": False, "error": "유효한 유튜브 영상 ID를 찾을 수 없습니다."}

    ytt = YouTubeTranscriptApi()
    try:
        transcript_list = ytt.list(video_id)
    except Exception as e:
        return {"success": False, "error": f"자막 목록을 조회할 수 없습니다: {str(e)}"}

    # Prioritize: Korean (manual) -> Korean (auto) -> English (manual) -> English (auto) -> First available
    selected_t = None
    target_langs = ['ko', 'en']
    
    try:
        # First check manual ko, then auto ko, etc.
        for lang in target_langs:
            for t in transcript_list:
                if t.language_code.startswith(lang) and not t.is_generated:
                    selected_t = t
                    break
            if selected_t:
                break
        
        if not selected_t:
            for lang in target_langs:
                for t in transcript_list:
                    if t.language_code.startswith(lang):
                        selected_t = t
                        break
                if selected_t:
                    break
                    
        if not selected_t:
            # Pick whatever is first
            all_transcripts = list(transcript_list)
            if all_transcripts:
                selected_t = all_transcripts[0]
                
        if not selected_t:
            return {"success": False, "error": "이 영상에서 사용 가능한 자막/스크립트가 없습니다."}

        snippets = selected_t.fetch()
        formatted_segments = []
        full_text_lines = []
        
        for item in snippets:
            # Snippet has start, text, duration
            text = getattr(item, 'text', '') if not isinstance(item, dict) else item.get('text', '')
            start = getattr(item, 'start', 0.0) if not isinstance(item, dict) else item.get('start', 0.0)
            dur = getattr(item, 'duration', 0.0) if not isinstance(item, dict) else item.get('duration', 0.0)
            
            clean_text = text.replace('\n', ' ').strip()
            if not clean_text:
                continue
            ts = format_timestamp(start)
            formatted_segments.append({
                "timestamp": ts,
                "seconds": start,
                "text": clean_text
            })
            full_text_lines.append(f"[{ts}] {clean_text}")

        return {
            "success": True,
            "language": getattr(selected_t, 'language', '알 수 없음'),
            "is_generated": getattr(selected_t, 'is_generated', False),
            "segments": formatted_segments,
            "full_script": "\n".join(full_text_lines),
            "clean_text": " ".join([s['text'] for s in formatted_segments])
        }

    except Exception as e:
        return {"success": False, "error": f"자막 스크립트 추출 실패: {str(e)}"}

def download_video_or_audio(
    url: str,
    media_type: str, # "mp3" or "mp4"
    quality: str,     # "best", "1080p", "720p", etc.
    job_id: str,
    progress_callback: Callable[[Dict[str, Any]], None]
) -> Dict[str, Any]:
    node_path = r"C:\Program Files\nodejs\node.exe" if os.name == 'nt' else "/usr/bin/node"
    
    def ydl_hook(d):
        if d['status'] == 'downloading':
            total = d.get('total_bytes') or d.get('total_bytes_estimate') or 0
            downloaded = d.get('downloaded_bytes', 0)
            percent = (downloaded / total * 100) if total > 0 else 0
            speed = d.get('speed') or 0
            eta = d.get('eta') or 0
            speed_str = f"{speed / (1024*1024):.2f} MB/s" if speed > 1024*1024 else f"{speed / 1024:.1f} KB/s"
            progress_callback({
                "job_id": job_id,
                "status": "downloading",
                "percent": round(percent, 1),
                "speed": speed_str,
                "eta": f"{eta}초",
                "message": f"다운로드 중... ({round(percent, 1)}%)"
            })
        elif d['status'] == 'finished':
            progress_callback({
                "job_id": job_id,
                "status": "processing",
                "percent": 95,
                "message": "인코딩 및 파일 변환 중..."
            })

    output_template = str(DOWNLOADS_DIR / "%(title).100s_%(id)s.%(ext)s")
    
    ydl_opts: Dict[str, Any] = {
        'ffmpeg_location': str(FFMPEG_PATH),
        'progress_hooks': [ydl_hook],
        'outtmpl': output_template,
        'windowsfilenames': True,
        'restrictfilenames': False,
        'quiet': True,
        'no_warnings': True,
    }
    if os.path.exists(node_path):
        ydl_opts['js_runtimes'] = {'node': {'path': node_path}}

    if media_type == 'mp3':
        ydl_opts['format'] = 'bestaudio/best'
        ydl_opts['postprocessors'] = [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '320',
        }]
    else: # mp4
        # Format selection based on quality
        if quality and "p" in quality:
            height = quality.replace("p", "").strip()
            ydl_opts['format'] = f'bestvideo[height<={height}][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<={height}]+bestaudio/best[height<={height}]/best'
        else:
            ydl_opts['format'] = 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/bestvideo+bestaudio/best[ext=mp4]/best'
        ydl_opts['merge_output_format'] = 'mp4'

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        filename = ydl.prepare_filename(info)
        
        # Adjust extension for mp3
        if media_type == 'mp3':
            base, _ = os.path.splitext(filename)
            filename = base + ".mp3"
        else:
            base, _ = os.path.splitext(filename)
            filename = base + ".mp4"

    target_name = os.path.basename(filename)
    progress_callback({
        "job_id": job_id,
        "status": "completed",
        "percent": 100,
        "filename": target_name,
        "message": "다운로드 및 변환 완료!"
    })

    return {
        "success": True,
        "filename": target_name,
        "filepath": filename,
        "title": info.get('title')
    }
