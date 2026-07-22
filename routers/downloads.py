from fastapi import APIRouter
import os
from fastapi.responses import FileResponse
from pathlib import Path
from utils.runtime_paths import resolve_runtime_path
router = APIRouter()
@router.get("/download/{file_name}")
async def download_file(file_name: str):
    file_name = Path(file_name).name  # segurança contra path traversal
    audio_file_path = str(resolve_runtime_path("youtubeDownload", "audio", file_name))
    transcribe_file_path = str(resolve_runtime_path("youtubeDownload", "transcript", file_name))
    video_file_path = str(resolve_runtime_path("youtubeDownload", "video", file_name))
    if os.path.exists(transcribe_file_path):
        return FileResponse(transcribe_file_path, filename=file_name, media_type='text/plain')
    
    elif os.path.exists(audio_file_path):
        return FileResponse(audio_file_path, filename=file_name, media_type='audio/mpeg')
    elif os.path.exists(video_file_path):
        return FileResponse(video_file_path, filename=file_name, media_type='video/mp4')        
    return {"error": "Arquivo não encontrado"}