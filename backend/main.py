import os
import uuid
import threading
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional
from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .config import (
    DOWNLOADS_DIR, BASE_DIR, get_gemini_api_key, save_gemini_api_key,
    has_youtube_cookies, save_youtube_cookies, delete_youtube_cookies, COOKIES_PATH
)
from .youtube_service import get_video_info, fetch_transcript, download_video_or_audio
from .ai_service import summarize_with_gemini, local_fallback_summary

app = FastAPI(title="YouTube AI Extractor API", version="1.0.0")

# In-memory download task state
download_jobs: Dict[str, Dict[str, Any]] = {}

class VideoInfoRequest(BaseModel):
    url: str

class DownloadRequest(BaseModel):
    url: str
    media_type: str  # "mp3" or "mp4"
    quality: Optional[str] = "best"

class SummarizeRequest(BaseModel):
    url: str
    video_title: Optional[str] = ""

class CookiesRequest(BaseModel):
    cookies: str

class ApiKeyRequest(BaseModel):
    api_key: str

class DeleteFileRequest(BaseModel):
    filename: str

@app.post("/api/video-info")
def api_video_info(req: VideoInfoRequest):
    try:
        info = get_video_info(req.url)
        return {"success": True, "data": info}
    except Exception as e:
        return {"success": False, "error": f"영상 정보를 불러오는 데 실패했습니다: {str(e)}"}

@app.post("/api/download-start")
def api_download_start(req: DownloadRequest, background_tasks: BackgroundTasks):
    job_id = str(uuid.uuid4())[:8]
    download_jobs[job_id] = {
        "job_id": job_id,
        "status": "starting",
        "percent": 0,
        "speed": "0 KB/s",
        "eta": "계산 중...",
        "message": "다운로드 준비 중..."
    }

    def progress_callback(data: Dict[str, Any]):
        download_jobs[job_id].update(data)

    def run_download():
        try:
            download_video_or_audio(
                url=req.url,
                media_type=req.media_type,
                quality=req.quality or "best",
                job_id=job_id,
                progress_callback=progress_callback
            )
        except Exception as e:
            download_jobs[job_id].update({
                "status": "error",
                "message": f"다운로드 실패: {str(e)}"
            })

    # Start thread
    t = threading.Thread(target=run_download, daemon=True)
    t.start()

    return {"success": True, "job_id": job_id}

@app.get("/api/download-progress/{job_id}")
def api_download_progress(job_id: str):
    job = download_jobs.get(job_id)
    if not job:
        return {"success": False, "error": "Job not found"}
    return {"success": True, "data": job}

@app.post("/api/summarize")
def api_summarize(req: SummarizeRequest):
    # 1. Fetch transcript
    transcript_res = fetch_transcript(req.url)
    if not transcript_res["success"]:
        return transcript_res

    title = req.video_title or "유튜브 영상"
    transcript_text = transcript_res["full_script"]
    segments = transcript_res["segments"]

    # 2. Try Gemini API
    gemini_key = get_gemini_api_key()
    if gemini_key:
        ai_res = summarize_with_gemini(transcript_text, title)
        if ai_res.get("success"):
            return {
                "success": True,
                "type": "gemini",
                "markdown": ai_res["markdown"],
                "language": transcript_res["language"],
                "is_generated": transcript_res["is_generated"],
                "segment_count": len(segments),
                "full_script": transcript_text
            }

    # 3. Fallback heuristic summary
    fallback = local_fallback_summary(segments, title)
    return {
        "success": True,
        "type": "fallback",
        "data": fallback,
        "language": transcript_res["language"],
        "is_generated": transcript_res["is_generated"],
        "segment_count": len(segments),
        "full_script": transcript_text,
        "has_api_key": bool(gemini_key)
    }

@app.get("/api/history")
def api_history():
    files = []
    if DOWNLOADS_DIR.exists():
        for p in DOWNLOADS_DIR.iterdir():
            if p.is_file() and p.suffix.lower() in [".mp3", ".mp4", ".m4a", ".webm"]:
                stat = p.stat()
                size_mb = round(stat.st_size / (1024 * 1024), 2)
                files.append({
                    "name": p.name,
                    "ext": p.suffix.lower().replace(".", ""),
                    "size_mb": size_mb,
                    "mtime": stat.st_mtime
                })
    files.sort(key=lambda x: x["mtime"], reverse=True)
    return {"success": True, "files": files}

@app.get("/api/stream/{filename}")
def api_stream_file(filename: str):
    file_path = DOWNLOADS_DIR / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    media_type = "audio/mpeg" if filename.endswith(".mp3") else "video/mp4"
    return FileResponse(path=file_path, media_type=media_type, filename=filename)

@app.get("/api/download-file/{filename}")
def api_download_file(filename: str):
    from urllib.parse import quote
    file_path = DOWNLOADS_DIR / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    encoded_filename = quote(filename)
    return FileResponse(
        path=file_path,
        media_type="application/octet-stream",
        filename=filename,
        headers={
            "Content-Disposition": f'attachment; filename="{encoded_filename}"; filename*=UTF-8\'\'{encoded_filename}'
        }
    )

@app.post("/api/open-downloads")
def api_open_downloads():
    try:
        downloads_path = str(DOWNLOADS_DIR.resolve())
        subprocess.Popen(f'explorer "{downloads_path}"', shell=True)
        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.post("/api/delete-file")
def api_delete_file(req: DeleteFileRequest):
    file_path = DOWNLOADS_DIR / req.filename
    if file_path.exists():
        try:
            file_path.unlink()
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}
    return {"success": False, "error": "File does not exist"}

@app.get("/api/settings")
def api_get_settings():
    key = get_gemini_api_key()
    masked = ""
    if key:
        masked = key[:6] + "..." + key[-4:] if len(key) > 10 else "***"
    return {"success": True, "has_key": bool(key), "masked_key": masked}

@app.post("/api/settings")
def api_save_settings(req: ApiKeyRequest):
    save_gemini_api_key(req.api_key.strip())
    return {"success": True, "message": "API 키가 안전하게 저장되었습니다."}

@app.get("/api/cookies-status")
def api_cookies_status():
    configured = has_youtube_cookies()
    size = COOKIES_PATH.stat().st_size if configured else 0
    return {
        "success": True,
        "configured": configured,
        "size_bytes": size
    }

@app.post("/api/save-cookies")
def api_save_cookies(req: CookiesRequest):
    content = req.cookies.strip()
    if not content or len(content) < 10:
        return {"success": False, "error": "유효한 cookies.txt 내용이 아닙니다. 최소 10자 이상이어야 합니다."}
    save_youtube_cookies(content)
    return {"success": True, "message": "유튜브 인증 쿠키가 성공적으로 저장되었습니다! 이제 클라우드에서도 차단 없이 다운로드됩니다."}

@app.post("/api/delete-cookies")
def api_delete_cookies():
    delete_youtube_cookies()
    return {"success": True, "message": "유튜브 인증 쿠키가 삭제되었습니다."}

# Mount Frontend static files
FRONTEND_DIR = BASE_DIR / "frontend"
FRONTEND_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")

