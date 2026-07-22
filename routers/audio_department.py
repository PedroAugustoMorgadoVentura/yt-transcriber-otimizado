from fastapi import WebSocket, APIRouter
from utils.get_title import get_title_from_youtube_url
import asyncio
import os
import re
import traceback

router = APIRouter()
from pathlib import Path
import uuid
from utils.runtime_paths import ensure_runtime_dir


def sanitize_filename(name: str) -> str:
    """Remove caracteres inválidos para nomes de arquivos em sistemas operacionais."""
    return re.sub(r'[\\/*?:"<>|]', "", name).strip()


def resolve_downloaded_file(downloads_dir: Path, preferred_output_path: str, uid: str) -> Path:
    preferred_path = Path(preferred_output_path)
    if preferred_path.exists() and preferred_path.is_file():
        return preferred_path

    matches = sorted(
        path for path in downloads_dir.glob(f"*{uid}*") if path.is_file()
    )
    if matches:
        return matches[0]

    raise FileNotFoundError(f"Nenhum arquivo foi criado em {downloads_dir}")


@router.websocket("/ws/audio")
async def websocket_audio(websocket: WebSocket):
    await websocket.accept()
    print("Conexão de baixar audio iniciou")
    try:
        data = await websocket.receive_json()
        url = data["url"]
        raw_title = await get_title_from_youtube_url(url)
        title = sanitize_filename(raw_title)
        uid = uuid.uuid4().hex
        downloads_dir = ensure_runtime_dir("youtubeDownload", "audio")

        output_path_audio = str(downloads_dir / f"audio_{title}_{uid}.mp3")
        command = ["yt-dlp", "-x", "--audio-format", "mp3", "--no-playlist", "-o", output_path_audio, url]

        process = await asyncio.create_subprocess_exec(
            *command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            error_msg = stderr.decode("utf-8", errors="ignore")
            await websocket.send_json({
                "error": f"Erro ao baixar o áudio: {error_msg}"
            })
            raise Exception(f"Erro no yt-dlp:\n{error_msg}")

        downloaded_file = resolve_downloaded_file(downloads_dir, output_path_audio, uid)
        audio_file_name = downloaded_file.name

        await websocket.send_json({
            "progress": 100,
            "message": "✅ Áudio gerado!",
            "download_url": f"/download/{audio_file_name}"
        })

    except Exception as e:
        traceback.print_exc()
        await websocket.send_json({
            "error": f"{str(e)}\n\n{traceback.format_exc()}"
        })
