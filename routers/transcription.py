import asyncio
from fastapi import WebSocket
import os
import subprocess
import traceback
from pathlib import Path
import torch
from services.audioprocess import get_audio
from utils.clean_text import Clean_Text
from fastapi import APIRouter
from services.charge_model import Charge_Model
from utils.get_title import get_title_from_file_path_modern

router = APIRouter()

@router.websocket("/ws/transcribe")
async def websocket_transcribe(websocket: WebSocket):
    await websocket.accept()
    output_path = None 
    chunk_filename = None
    print("INFO: connection open")
    try:
        data = await websocket.receive_json()
        model = data.get("model", "small")
        chunk_length_choice = int(data.get("chunk_length_choice"))
        language = data.get("language")
        language = None if language=="none" else language
        if "url" in data:
            url = data["url"]
            await websocket.send_json({
                "message": f"⏳ Baixando áudio do vídeo: {url}..."
            })
            print(f"⏳ Baixando áudio do vídeo: {url}...")
        transcriber_fast = await asyncio.to_thread(Charge_Model, model)

        
        chunk_length = chunk_length_choice
        overlap = 2
        transcriptions = []        
        output_path, duration, uid, data = await get_audio(websocket, data) 
        title = get_title_from_file_path_modern(output_path)


        for start in range(0, int(duration), chunk_length - overlap):
            end = min(start + chunk_length, int(duration))
            chunk_filename = f"chunk_{start}_{end}.mp3"

            subprocess.run([
                "ffmpeg", "-ss", str(start), "-to", str(end),
                "-i", output_path, "-vn", "-acodec", "mp3", "-y", chunk_filename
            ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            

            if not os.path.exists(chunk_filename):
                await websocket.send_json({
                    "error": f"Falha ao criar chunk de áudio: {chunk_filename}"
                })
                raise Exception(f"Falha ao criar chunk de áudio: {chunk_filename}")
            
            try:
                segments, _ = transcriber_fast.transcribe(
                    chunk_filename,
                    vad_filter=True,
                    language=language,
                    beam_size = 4
                )
            except Exception as e:
                await websocket.send_json({
                    "error": f"Erro ao transcrever o chunk {chunk_filename}: {str(e)}"
                })
                raise Exception(f"Erro ao transcrever o chunk {chunk_filename}: {str(e)}")
            text = "".join(seg.text for seg in segments)
            clean_text = Clean_Text(text)
            transcriptions.append(f"\n{start} --> {end} segundos: {clean_text}")
            os.remove(chunk_filename)
            print(f"✅ Transcrito até {end} segundos de {duration} segundos totais.")
            
            progress = int((end / duration) * 100)
            await websocket.send_json({
                "progress": progress,
                "message": f"✅ Transcrito até {end} segundos de {duration} segundos totais.",
                "transcription": "\n".join(transcriptions)
            })

        os.remove(output_path)
        
        transcript_dir = Path("youtubeDownload/transcript")
        transcript_dir.mkdir(parents=True, exist_ok=True)

        txt_path = transcript_dir / f"transcription: {title}_{uid}.txt"
        
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write("\n".join(transcriptions))

        await websocket.send_json({
            "progress": 100,
            "message": "✅ Transcrição concluída!",
            "transcription": "\n".join(transcriptions),
            "download_url": f"/download/{txt_path.name}"
        })
    except Exception as e:
        traceback.print_exc()
        await websocket.send_json({
            "error": f"{str(e)}\n\n{traceback.format_exc()}"
        })
    finally:
        if output_path and await asyncio.to_thread(os.path.exists, output_path): # Assíncrono para os.path.exists
            await asyncio.to_thread(os.remove, output_path)
        if chunk_filename and await asyncio.to_thread(os.path.exists, chunk_filename):
            await asyncio.to_thread(os.remove, chunk_filename)
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        print("INFO: cleaning up model from memory")

        await websocket.close()
        
        
        
    print("INFO: connection closed")
