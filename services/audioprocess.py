import os
import uuid
from fastapi import WebSocket
from utils.get_audio_duration import get_audio_duration
from utils.conversionfiles import eh_mp3, mp3_to_wav
import json
import asyncio

async def get_audio(websocket: WebSocket, data: dict):
        temp_dir = "temp"
        await asyncio.to_thread(os.makedirs, temp_dir, exist_ok=True)

        uid = uuid.uuid4().hex
        if "url" in data:
            output_path = f"temp/temp_{uid}.wav"
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
            output_path = f"temp/temp_{uid}.mp3"

            with open(output_path, "wb") as audio_file:
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

        if not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
            await websocket.send_json({
                "error": f"Arquivo de áudio não foi recebido: {output_path}"
            })
            raise Exception(f"Arquivo de áudio não foi recebido: {output_path}")
        try:
            duration = await get_audio_duration(output_path)
        except Exception as e:
            error_msg = f"Erro ao obter duração do áudio: {str(e)}"
            await websocket.send_json({"error": error_msg})
            raise Exception(error_msg)
        if eh_mp3(output_path):
            wav_path = output_path.rsplit('.', 1)[0] + ".wav"
            await mp3_to_wav(output_path, wav_path)
            os.remove(output_path)
            output_path = wav_path
        return output_path, duration, uid, None
 