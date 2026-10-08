import os
import re
import math
from typing import Dict, Any, Optional, Callable
import shutil
import requests
import subprocess
import yt_dlp
from youtube_transcript_api import YouTubeTranscriptApi
from .config import DOWNLOADS_DIR, FFMPEG_PATH

def get_node_runtime() -> Optional[str]:
    if os.name == 'nt':
        default_nt = r"C:\Program Files\nodejs\node.exe"
        if os.path.exists(default_nt):
            return default_nt
    which_node = shutil.which("node") or shutil.which("nodejs")
    if which_node and os.path.exists(which_node):
        return which_node
    if os.path.exists("/usr/bin/node"):
        return "/usr/bin/node"
    if os.path.exists("/usr/bin/nodejs"):
        return "/usr/bin/nodejs"
    return None

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
    node_path = get_node_runtime()
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36',
        'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7',
    }
    client_candidates = [
        ['android'],
        ['android', 'ios'],
        ['ios'],
    ]

    info = None
    last_err = None

    for client_list in client_candidates:
        ydl_opts: Dict[str, Any] = {
            'quiet': True,
            'skip_download': True,
            'ffmpeg_location': str(FFMPEG_PATH),
            'http_headers': headers,
            'socket_timeout': 10,
            'extractor_args': {
                'youtube': {
                    'player_client': client_list
                }
            }
        }
        if node_path:
            ydl_opts['js_runtimes'] = {'node': {'path': node_path}}

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                if info and info.get('title'):
                    break
        except Exception as e:
            last_err = e
            continue

    if not info:
        # Ultimate Fallback: Official YouTube oEmbed API (Never blocked by YouTube on cloud servers)
        video_id = extract_video_id(url)
        if video_id:
            try:
                oembed_url = f"https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v={video_id}&format=json"
                resp = requests.get(oembed_url, timeout=5)
                if resp.status_code == 200:
                    data = resp.json()
                    return {
                        "id": video_id,
                        "title": data.get('title', '유튜브 영상'),
                        "channel": data.get('author_name', '알 수 없음'),
                        "duration": 0,
                        "duration_str": "재생시간 자동 감지",
                        "thumbnail": f"https://i.ytimg.com/vi/{video_id}/maxresdefault.jpg",
                        "view_count": 0,
                        "available_resolutions": ["최고화질 (Best)", "1080p", "720p", "480p", "360p"],
                        "original_url": url
                    }
            except Exception:
                pass
        raise last_err or RuntimeError("유튜브 영상 정보를 파싱하지 못했습니다. URL을 확인해 주세요.")

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
    node_path = get_node_runtime()
    
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
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36',
        'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7',
    }

    client_candidates = [
        ['android'],
        ['android', 'ios'],
        ['ios'],
    ]

    last_err = None
    info = None
    filename = None

    for client_list in client_candidates:
        ydl_opts: Dict[str, Any] = {
            'ffmpeg_location': str(FFMPEG_PATH),
            'progress_hooks': [ydl_hook],
            'outtmpl': output_template,
            'windowsfilenames': True,
            'restrictfilenames': False,
            'quiet': True,
            'no_warnings': True,
            'http_headers': headers,
            'socket_timeout': 15,
            'extractor_args': {
                'youtube': {
                    'player_client': client_list
                }
            }
        }
        if node_path:
            ydl_opts['js_runtimes'] = {'node': {'path': node_path}}

        if media_type == 'mp3':
            ydl_opts['format'] = '18/bestaudio/best'
            ydl_opts['postprocessors'] = [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '320',
            }]
        else: # mp4
            if quality and "p" in quality:
                height = quality.replace("p", "").strip()
                ydl_opts['format'] = f'bestvideo[height<={height}][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<={height}]+bestaudio/best[height<={height}]/18/best'
            else:
                ydl_opts['format'] = '18/bestvideo[ext=mp4]+bestaudio[ext=m4a]/best'
            ydl_opts['merge_output_format'] = 'mp4'

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                filename = ydl.prepare_filename(info)
                if filename:
                    break
        except Exception as e:
            last_err = e
            # Direct Stream Fallback: If yt-dlp internal downloader fails, stream raw googlevideo bytes directly
            try:
                with yt_dlp.YoutubeDL({
                    'quiet': True,
                    'extractor_args': {'youtube': {'player_client': client_list}},
                    'skip_download': True,
                    'socket_timeout': 10
                }) as ydl_stream:
                    stream_info = ydl_stream.extract_info(url, download=False)
                    stream_url = None
                    for fmt in stream_info.get('formats', []):
                        if fmt.get('format_id') == '18' and fmt.get('url'):
                            stream_url = fmt.get('url')
                            break
                    if not stream_url:
                        for fmt in stream_info.get('formats', []):
                            if fmt.get('url'):
                                stream_url = fmt.get('url')
                                break
                    if stream_url:
                        title = stream_info.get('title', 'youtube_video')
                        vid_id = stream_info.get('id', 'video')
                        clean_title = sanitize_filename(title)[:50]
                        temp_mp4 = str(DOWNLOADS_DIR / f"{clean_title}_{vid_id}.mp4")
                        
                        progress_callback({
                            "job_id": job_id,
                            "status": "downloading",
                            "percent": 10,
                            "message": "고속 다이렉트 스트림 다운로드 중..."
                        })

                        with requests.get(stream_url, stream=True, timeout=15) as r:
                            r.raise_for_status()
                            total_len = int(r.headers.get('content-length', 0))
                            dl_bytes = 0
                            with open(temp_mp4, 'wb') as f:
                                for chunk in r.iter_content(chunk_size=1024*256):
                                    if chunk:
                                        f.write(chunk)
                                        dl_bytes += len(chunk)
                                        if total_len > 0:
                                            p = round(dl_bytes / total_len * 90, 1)
                                            progress_callback({
                                                "job_id": job_id,
                                                "status": "downloading",
                                                "percent": p,
                                                "message": f"스트림 다운로드 중... ({p}%)"
                                            })

                        if media_type == 'mp3':
                            target_file = str(DOWNLOADS_DIR / f"{clean_title}_{vid_id}.mp3")
                            subprocess.run([str(FFMPEG_PATH), '-y', '-i', temp_mp4, '-vn', '-b:a', '320k', target_file], check=True)
                            if os.path.exists(temp_mp4):
                                os.remove(temp_mp4)
                            filename = target_file
                        else:
                            filename = temp_mp4
                        info = stream_info
                        break
            except Exception as stream_e:
                last_err = stream_e
            continue

    if not filename or not info:
        raise last_err or RuntimeError("다운로드에 실패했습니다. 유튜브 정책 또는 네트워크를 확인해 주세요.")

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
