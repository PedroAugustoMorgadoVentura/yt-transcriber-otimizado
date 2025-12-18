import os
import uuid
from fastapi import WebSocket
from utils.get_audio_duration import get_audio_duration
from utils.conversionfiles import is_wav, convert_to_wav
import json
import asyncio
from utils.get_title import get_title_from_youtube_url, get_title_from_file_path_modern
import re

def sanitize_filename(filename: str) -> str:
    # Remove os caracteres proibidos no Windows
    filename = re.sub(r'[<>:"/\\|?*]+', '', filename)
    # Remove espaços múltiplos e espaços no início/fim
    filename = re.sub(r'\s+', ' ', filename).strip()
    return filename

async def get_audio(websocket: WebSocket, data: dict):
        temp_dir = "temp"
        await asyncio.to_thread(os.makedirs, temp_dir, exist_ok=True)

        uid = uuid.uuid4().hex[:8]
        if "url" in data:
            title = sanitize_filename(await get_title_from_youtube_url(data["url"]))
            output_path = f"temp/{title}_{uid}_.wav"
            url = data["url"]
            command = [
                "yt-dlp", "-x", "--audio-format", "wav", "--no-playlist",
                "-o", output_path,
                url
            ]
            process = await asyncio.create_subprocess_exec(*command)
            await process.wait()
            if not os.path.exists(output_path):
                await websocket.send_json({
                    "error": f"Arquivo de áudio não foi criado: {output_path}"
                })
                raise Exception(f"Arquivo de áudio não foi criado: {output_path}")

            duration = await get_audio_duration(output_path)
            return output_path, duration, uid, data
        else:
            filename = data.get("filename")
            title = sanitize_filename(get_title_from_file_path_modern(filename))
            extension = filename.rsplit('.', 1)[-1].lower()
            raw_path = f"temp/{title}_{uid}_raw.{extension}"
            wav_path = f"temp/{title}_{uid}.wav"
            with open(raw_path, "wb") as audio_file:
                while True:
                    databyte = await websocket.receive()

                    if databyte["type"] == "websocket.receive":
                        if "text" in databyte:
                            text_data = databyte["text"]
                            if text_data == "FILE_END":
                                break
                            try:
                                json_data = json.loads(text_data)
                                continue
                            
                            except json.JSONDecodeError:
                                continue

                        elif "bytes" in databyte:
                            audio_file.write(databyte["bytes"])
                            
        

        if not os.path.exists(raw_path) or os.path.getsize(raw_path) == 0:
            await websocket.send_json({
                "error": f"Arquivo de áudio não foi recebido: {raw_path}"
            })
            raise Exception(f"Arquivo de áudio não foi recebido: {raw_path}")
        if is_wav(raw_path):
            output_path = raw_path
        else:
            await convert_to_wav(raw_path, wav_path)
            os.remove(raw_path)
            output_path = wav_path
        try:
            duration = await get_audio_duration(output_path)
        except Exception as e:
            error_msg = f"Erro ao obter duração do áudio: {str(e)}"
            await websocket.send_json({"error": error_msg})
            raise Exception(error_msg)
        return output_path, duration, uid, None
 