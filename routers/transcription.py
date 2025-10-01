from fastapi import WebSocket
import os
import subprocess
import traceback
from pathlib import Path
import torch
from faster_whisper import WhisperModel as Twhisper
from services.audioprocess import get_audio
from utils.clean_text import Clean_Text
model_cache = {}
from fastapi import APIRouter

router = APIRouter()

@router.websocket("/ws/transcribe")
async def websocket_transcribe(websocket: WebSocket):
    await websocket.accept()

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

        if model not in model_cache:
            await websocket.send_json({
                "message": f"⏳ Carregando modelo Whisper: {model}..."
            })
            print(f"⏳ Carregando modelo Whisper: {model}...")

            device = "cuda" if torch.cuda.is_available() else "cpu"
            transcriber_fast = Twhisper(model, device=device, compute_type="int8" if device == "cuda" else "int4")
            
            model_cache[model] = transcriber_fast
            await websocket.send_json({
                "message": f"✅ Modelo {model} carregado."
            })
            print(f"✅ Modelo {model} carregado.")
        else:
            transcriber_fast = model_cache[model]
            await websocket.send_json({
                "message": f"✅ Modelo {model} já estava carregado."
            })
            print(f"✅ Modelo {model} já estava carregado.")
        
        chunk_length = chunk_length_choice
        overlap = 2
        transcriptions = []        
        output_path, duration, uid, data = await get_audio(websocket, data) 

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
                segments, _ = model_cache[model].transcribe(
                    chunk_filename,
                    vad_filter=True,
                    language=language,
                    beam_size = 5
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

        txt_path = transcript_dir / f"transcription_{uid}.txt"
        
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
        del model_cache[model]
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        print("INFO: cleaning up model from memory")

        await websocket.close()
        
        
        
    print("INFO: connection closed")
