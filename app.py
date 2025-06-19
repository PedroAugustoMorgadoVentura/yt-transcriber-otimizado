from fastapi import FastAPI, Request, WebSocket, UploadFile, File, BackgroundTasks
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from wordcloud import WordCloud
from collections import Counter
import whisper
import os
import uuid
import subprocess
import traceback
import matplotlib.pyplot as plt
from nltk.corpus import stopwords
from pathlib import Path

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

print("⏳ Carregando modelo Whisper...")
model = whisper.load_model("small", device="cuda")
print("✅ Modelo carregado com sucesso.")

def get_audio_duration(audio_path: str) -> float:
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", audio_path],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=True
    )
    return float(result.stdout.strip())

@app.get("/", response_class=HTMLResponse)
async def form_get(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})
@app.websocket("/ws/video")
async def websocket_video(websocket: WebSocket):
    await websocket.accept()
    print("Conexão de baixar video iniciou")
    try:
        data = await websocket.receive_json()
        url = data["url"]
        
        uid = uuid.uuid4().hex
        downloads_dir = Path("youtubeDownload/video")
        downloads_dir.mkdir(parents=True, exist_ok=True)

        # Nome do arquivo de saída (garantindo extensão .mp4)
        output_path = str(downloads_dir / f"perm_{uid}.mp4")
        
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
        })#oi

    except Exception as e:
        traceback.print_exc()
        await websocket.send_json({
            "error": f"{str(e)}\n\n{traceback.format_exc()}"
        })
    await websocket.accept()
    print("Conexão de baixar video iniciou")
    try:
        data = await websocket.receive_json()
        url = data["url"]
        
        uid = uuid.uuid4().hex
        downloads_dir = Path("youtubeDownload/video")
        downloads_dir.mkdir(parents=True, exist_ok=True)

        # Padrão de nomeação que funciona com yt-dlp
        output_pattern = str(downloads_dir / f"perm_{uid}.mp4")
        
        command = [
            "yt-dlp",
            "-f", "bestvideo[ext=mp4][height<=1080]+bestaudio/bestvideo[ext=mp4][height<=720]+bestaudio/best",
            "--no-playlist",
            "-o", output_pattern,
            url
        ]
        
        result = subprocess.run(command, capture_output=True, text=True)
        if result.returncode != 0:
            raise Exception(f"Erro no yt-dlp:\n{result.stderr}")

        # Encontra o arquivo real que foi criado
        output_files = list(downloads_dir.glob(f"perm_{uid}.*"))
        if not output_files:
            raise Exception(f"Nenhum arquivo foi criado em {downloads_dir}")
        
        output_path_video = str(output_files[0])
        video_file_name = output_files[0].name

        await websocket.send_json({
            "progress": 100,
            "message": "✅ video gerado!",
            "download_url": f"/download/{video_file_name}"
        })

    except Exception as e:
        traceback.print_exc()
        await websocket.send_json({
            "error": f"{str(e)}\n\n{traceback.format_exc()}"
        })
@app.websocket("/ws/audio")
async def websocket_audio(websocket: WebSocket):
    await websocket.accept()
    print("Conexão de baixar audio iniciou")
    try:
        data = await websocket.receive_json()
        url = data["url"]

        uid = uuid.uuid4().hex
        downloads_dir = Path("youtubeDownload/audio")
        downloads_dir.mkdir(parents=True, exist_ok=True)

        output_path_audio = str(downloads_dir / f"perm_{uid}.mp3")
        command = ["yt-dlp", "-x", "--audio-format", "mp3", "--no-playlist","-o" ,output_path_audio, url]
        result = subprocess.run(command, capture_output=True, text=True)
        if result.returncode != 0:
            raise Exception(f"Erro no yt-dlp:\n{result.stderr}")
        
        if not os.path.exists(output_path_audio):
            raise Exception(f"Arquivo de áudio não foi criado: {output_path_audio}")
        audio_file_name = f"perm_{uid}.mp3"
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
@app.websocket("/ws/transcribe")
async def websocket_transcribe(websocket: WebSocket):
    await websocket.accept()
    
    print("INFO: connection open")
    try:
        data = await websocket.receive_json()
        url = data["url"]

        uid = uuid.uuid4().hex
        output_path = f"temp_{uid}.mp3"

        command = [
            "yt-dlp", "-x", "--audio-format", "mp3", "--no-playlist",
            "-o", output_path,
            url
        ]
        subprocess.run(command, check=True)

        if not os.path.exists(output_path):
            raise Exception(f"Arquivo de áudio não foi criado: {output_path}")

        duration = get_audio_duration(output_path)
        chunk_length = 60
        overlap = 2
        transcriptions = []

        for start in range(0, int(duration), chunk_length - overlap):
            end = min(start + chunk_length, int(duration))
            chunk_filename = f"chunk_{start}_{end}.mp3"

            subprocess.run([
                "ffmpeg", "-ss", str(start), "-to", str(end),
                "-i", output_path, "-vn", "-acodec", "mp3", "-y", chunk_filename
            ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

            if not os.path.exists(chunk_filename):
                raise Exception(f"Falha ao criar chunk de áudio: {chunk_filename}")

            try:
                result = model.transcribe(
                    chunk_filename,
                    fp16=True,
                    language="pt",
                    temperature=0,
                    best_of=5,
                    beam_size=5
                )
            except Exception as e:
                raise Exception(f"Erro ao transcrever o chunk {chunk_filename}: {str(e)}")

            transcriptions.append(result["text"])
            os.remove(chunk_filename)

            print(f"✅ Transcrito até {end} segundos de {duration} segundos totais.")

            progress = int((end / duration) * 100)
            await websocket.send_json({
                "progress": progress,
                "message": f"Transcrevendo {start}-{end} segundos...",
                "transcription": "\n".join(transcriptions)
            })

        os.remove(output_path)

        txt_filename = f"transcription_{uid}.txt"
        with open(txt_filename, "w", encoding="utf-8") as f:
            f.write("\n".join(transcriptions))

        await websocket.send_json({
            "progress": 100,
            "message": "✅ Transcrição concluída!",
            "transcription": "\n".join(transcriptions),
            "download_url": f"/download/{txt_filename}"
        })

    except Exception as e:
        traceback.print_exc()
        await websocket.send_json({
            "error": f"{str(e)}\n\n{traceback.format_exc()}"
        })

    await websocket.close()
    print("INFO: connection closed")
@app.get("/download/{file_name}")
async def download_file(file_name: str):
    file_name = Path(file_name).name  # segurança contra path traversal
    audio_file_path = os.path.abspath(f"youtubeDownload/audio/{file_name}")
    file_path = os.path.abspath(f"youtubeDownload/transcript/{file_name}")
    video_file_path = os.path.abspath(f"youtubeDownload/video/{file_name}")
    if os.path.exists(file_path):
        return FileResponse(file_path, filename=file_name, media_type='text/plain')
    
    elif os.path.exists(audio_file_path):
        return FileResponse(audio_file_path, filename=file_name, media_type='audio/mpeg')
    elif os.path.exists(video_file_path):
        return FileResponse(video_file_path, filename=file_name, media_type='video/mp4')        
    return {"error": "Arquivo não encontrado"}

    
        


    
# dicionário global: UID da última imagem gerada por cada cliente (IP, por exemplo)
ultima_imagem_por_cliente = {}

@app.post("/upload/")
async def upload_file(
    request: Request,
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = None
):
    client_ip = request.client.host
    uid = uuid.uuid4().hex
    output_path = f"static/nuvem_{uid}.png"

    # Remove imagem anterior, se houver
    ultima = ultima_imagem_por_cliente.get(client_ip)
    if ultima and os.path.exists(ultima):
        os.remove(ultima)

    stopwords_pt = set(stopwords.words('portuguese'))
    stopwords_pt.update(['ludovico', 'adriana'])
    contents = await file.read()
    texto = contents.decode("utf-8").lower()
    palavras = ''.join(c if c.isalnum() or c.isspace() else ' ' for c in texto).split()
    palavras_filtradas = [p for p in palavras if p not in stopwords_pt]
    contador = Counter(palavras_filtradas)

    nuvem = WordCloud(width=870, height=400, background_color='white').generate_from_frequencies(contador)
    plt.figure(figsize=(10, 5))
    plt.imshow(nuvem, interpolation='bilinear')
    plt.axis('off')
    plt.tight_layout()
    plt.savefig(output_path)
    plt.close()

    # Atualiza última imagem do cliente
    ultima_imagem_por_cliente[client_ip] = output_path

    return {"message": "Nuvem gerada com sucesso!", "image_path": f"/{output_path}"}
