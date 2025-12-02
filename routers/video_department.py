from fastapi import APIRouter, WebSocket
import os
import subprocess
import traceback
from pathlib import Path
router = APIRouter()
import uuid
from utils.get_title import get_title_from_youtube_url

@router.websocket("/ws/video")
async def websocket_video(websocket: WebSocket):
    await websocket.accept()
    await websocket.send_json({
        "message": "Conexão estabelecida. Envie a URL do vídeo."
    })
    print("Conexão de baixar video iniciou")
    try:
        data = await websocket.receive_json()
        url = data["url"]
        
        uid = uuid.uuid4().hex
        downloads_dir = Path("youtubeDownload/video")
        downloads_dir.mkdir(parents=True, exist_ok=True)
        title = await get_title_from_youtube_url(url)
        # Nome do arquivo de saída (garantindo extensão .mp4)
        output_path = str(downloads_dir / f"perm_{title}_{uid}.mp4")
        
        command = [
            "yt-dlp",
            "-f", "bestvideo[ext=mp4][height<=1080]+bestaudio[ext=m4a]/bestvideo[ext=mp4][height<=720]+bestaudio[ext=m4a]/best[ext=mp4]/best",
            "--merge-output-format", "mp4",  # Força a saída em MP4
            "--no-playlist",
            "-o", output_path,
            "--recode-video", "mp4",  # Recodifica para MP4 se necessário
            url
        ]
        
        print(f"Executando comando: {' '.join(command)}")
        result = subprocess.run(command, capture_output=True, text=True)
        
        if result.returncode != 0:
            await websocket.send_json({
                "error": f"Erro ao baixar o vídeo: {result.stderr}"
            })
            raise Exception(f"Erro no yt-dlp:\n{result.stderr}")

        # Verifica se o arquivo foi criado
        if not os.path.exists(output_path):
            # Tenta encontrar qualquer arquivo com o UID
            output_files = list(downloads_dir.glob(f"perm_{uid}.*"))
            if not output_files:
                raise Exception(f"Nenhum arquivo foi criado em {downloads_dir}")
            
            # Se encontrou um arquivo mas não é MP4, converte
            output_path = str(output_files[0])
            if not output_path.endswith('.mp4'):
                new_path = output_path.rsplit('.', 1)[0] + '.mp4'
                convert_cmd = [
                    "ffmpeg", "-i", output_path,
                    "-c:v", "libx264", "-preset", "fast",
                    "-c:a", "aac", "-b:a", "192k",
                    new_path
                ]
                subprocess.run(convert_cmd, check=True)
                os.remove(output_path)
                output_path = new_path

        video_file_name = Path(output_path).name

        await websocket.send_json({
            "progress": 100,
            "message": "✅ Vídeo em MP4 gerado!",
            "download_url": f"/download/{video_file_name}"
        })

    except Exception as e:
        traceback.print_exc()
        await websocket.send_json({
            "error": f"{str(e)}\n\n{traceback.format_exc()}"
        })
