from fastapi import WebSocket, APIRouter
from utils.get_title import get_title_from_youtube_url
import os
import subprocess
import traceback

router = APIRouter()
from pathlib import Path
import uuid
@router.websocket("/ws/audio")
async def websocket_audio(websocket: WebSocket):
    await websocket.accept()
    print("Conexão de baixar audio iniciou")
    try:
        data = await websocket.receive_json()
        url = data["url"]
        title = await get_title_from_youtube_url(url)
        uid = uuid.uuid4().hex
        downloads_dir = Path("youtubeDownload/audio")
        downloads_dir.mkdir(parents=True, exist_ok=True)

        output_path_audio = str(downloads_dir / f"audio_{title}_{uid}.mp3")
        command = ["yt-dlp", "-x", "--audio-format", "mp3", "--no-playlist","-o" ,output_path_audio, url]
        result = subprocess.run(command, capture_output=True, text=True)
        if result.returncode != 0:
            await websocket.send_json({
                "error": f"Erro ao baixar o áudio: {result.stderr}"
            })
            raise Exception(f"Erro no yt-dlp:\n{result.stderr}")
        
        if not os.path.exists(output_path_audio):
            await websocket.send_json({
                "error": f"Arquivo de áudio não foi criado: {output_path_audio}"
            })
            raise Exception(f"Arquivo de áudio não foi criado: {output_path_audio}")
        audio_file_name = f"audio_{title}_{uid}.mp3"
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
