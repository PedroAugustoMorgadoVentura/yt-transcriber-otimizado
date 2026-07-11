from fastapi import APIRouter, WebSocket
import os
import asyncio
import re
import traceback
from pathlib import Path
import uuid
from utils.get_title import get_title_from_youtube_url

router = APIRouter()

def sanitize_filename(name: str) -> str:
    """Remove caracteres inválidos para nomes de arquivos em sistemas operacionais."""
    return re.sub(r'[\\/*?:"<>|]', "", name).strip()

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
        
        # Obtém e sanitiza o título para evitar quebras no sistema de arquivos
        raw_title = await get_title_from_youtube_url(url)
        title = sanitize_filename(raw_title)
        
        # Caminho final esperado em MP4
        output_path = str(downloads_dir / f"perm_{title}_{uid}.mp4")
        
        # Configuração para extrair o maior bitrate absoluto (incluindo streams VP9/AV1 em 4K+)
        # O remux-video altera o container para MP4 sem recodificar a stream original (zero perda de qualidade)
        command = [
            "yt-dlp",
            "-f", "bestvideo+bestaudio/best",
            "--merge-output-format", "mp4",
            "--remux-video", "mp4",
            "--no-playlist",
            "-o", output_path,
            url
        ]
        
        print(f"Executando comando: {' '.join(command)}")
        
        # Execução assíncrona do processo para não bloquear o Event Loop do FastAPI
        process = await asyncio.create_subprocess_exec(
            *command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        
        if process.returncode != 0:
            error_msg = stderr.decode('utf-8', errors='ignore')
            await websocket.send_json({
                "error": f"Erro ao baixar o vídeo: {error_msg}"
            })
            raise Exception(f"Erro no yt-dlp:\n{error_msg}")

        # Tratamento de fallback caso o container não tenha sido nomeado como esperado pelo yt-dlp
        if not os.path.exists(output_path):
            # Busca baseada estritamente no UID gerado
            output_files = list(downloads_dir.glob(f"*{uid}.*"))
            if not output_files:
                raise Exception(f"Nenhum arquivo foi criado em {downloads_dir}")
            
            output_path = str(output_files[0])
            
            # Se o arquivo resultante não for MP4, realiza conversão mantendo altíssimo bitrate
            if not output_path.endswith('.mp4'):
                new_path = output_path.rsplit('.', 1)[0] + '.mp4'
                
                # -crf 18 entrega qualidade visualmente idêntica à original (lossless perceptivo)
                # -b:a 320k garante a máxima fidelidade de áudio disponível
                convert_cmd = [
                    "ffmpeg", "-i", output_path,
                    "-c:v", "libx264", "-crf", "18", "-preset", "slow",
                    "-c:a", "aac", "-b:a", "320k",
                    new_path
                ]
                
                ffmpeg_process = await asyncio.create_subprocess_exec(
                    *convert_cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                await ffmpeg_process.communicate()
                
                if ffmpeg_process.returncode == 0:
                    os.remove(output_path)
                    output_path = new_path
                else:
                    raise Exception("Falha na conversão via ffmpeg.")

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