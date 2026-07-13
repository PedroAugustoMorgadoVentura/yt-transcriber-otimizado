import asyncio
from fastapi import WebSocket
import os
import traceback
from pathlib import Path
import torch
from services.audioprocess import get_audio
from utils.clean_text import Clean_Text
from fastapi import APIRouter
from services.charge_model import Charge_Model
from utils.get_title import get_title_from_file_path_modern
from core.transcription import brute_transcription
router = APIRouter()

@router.websocket("/ws/transcribe")
async def websocket_transcribe(websocket: WebSocket):
    await websocket.accept()
    output_path = None 
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
        charge_model = await asyncio.to_thread(Charge_Model, model)

        
        chunk_length = chunk_length_choice
        transcriptions = []        
        output_path, duration, uid, data = await get_audio(websocket, data) 
        title = get_title_from_file_path_modern(output_path)


        async for start, end, text in brute_transcription(output_path, charge_model, language):
            clean_text = Clean_Text(text)
            transcriptions.append(f"{text}")
            print(f"✅ Transcrito até {end} segundos de {duration} segundos totais.")

            progress = int((end / duration) * 100)
            await websocket.send_json({
                "progress": progress,
                "message": f"✅ Transcrito até {end} segundos de {duration} segundos totais.",
                "transcription": "\n".join(transcriptions)
            })

        await asyncio.to_thread(os.remove, output_path)
        
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

        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            print("INFO: cleaning up model from memory")

        await websocket.close()
        
        
        
    print("INFO: connection closed")