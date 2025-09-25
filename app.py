from fastapi import FastAPI, Request, WebSocket, UploadFile, File, BackgroundTasks
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from wordcloud import WordCloud
from collections import Counter
import os
import uuid
import subprocess
import traceback
import matplotlib.pyplot as plt
from nltk.corpus import stopwords
from pathlib import Path
import nltk
import torch
from faster_whisper import WhisperModel as Twhisper
import re
import json
import gc
import silero_vad
# Desativa o uso de symlinks no cache do Hugging Face
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
try:
    nltk.data.find('corpora/stopwords')
except LookupError:
    nltk.download('stopwords') 


def Clean_Text(texto: str) -> str:
    # Remove linhas com 1 ou 2 palavras, geralmente ruído ou marcações
    texto = re.sub(r'^(?:\s*\w+\s*){1,2}$', '', texto, flags=re.MULTILINE)

    # Remove sequências numéricas e pontuadas sem sentido (tipo "1. 2. 3.")
    texto = re.sub(r'(?:\d+\.\s*){3,}', '', texto)

    # Substitui sequências longas de pontuação por "..."
    texto = re.sub(r'\.{2,}', '..', texto)

    # Remove repetições consecutivas de palavras (ex: "o o o debate")
    texto = re.sub(r'\b(\w+)([\s\.,;:!?]+\1\b)+', r'\1', texto, flags=re.IGNORECASE)

    # Normaliza espaços múltiplos
    texto = re.sub(r' {2,}', ' ', texto)

    # Remove quebras de linha múltiplas
    texto = re.sub(r'\n{3,}', '\n\n', texto)

    # Remove espaços no início e fim de cada linha
    texto = re.sub(r'^\s+|\s+$', '', texto, flags=re.MULTILINE)

    # Remove linhas completamente vazias ou com só pontuação
    texto = re.sub(r'^\W*$', '', texto, flags=re.MULTILINE)

    # --- Novas adições para eliminar repetições exageradas ---

    # 1. Reduz repetições de frases simples (como "aperte o botão", "vamos lá") seguidas
    texto = re.sub(r'(?i)\b(.{3,100}?)([\s\.,;:!?]+\1\b)+', r'\1', texto)

    # 2. Reduz repetições exageradas de vírgulas
    texto = re.sub(r'(,\s*){2,}', ', ', texto)

    # 3. Reduz repetições exageradas de pontos de exclamação ou interrogação
    texto = re.sub(r'(!{2,})', '!', texto)
    texto = re.sub(r'(\?{2,})', '?', texto)

    # 4. Reduz risadas repetidas do tipo "haha haha", "kkk kkk"
    texto = re.sub(r'\b((ha){2,}|(kk+)){2,}', r'\1', texto, flags=re.IGNORECASE)

    # 5. Reduz sons como "ah ah ah", "uh uh"
    texto = re.sub(r'\b(ah|uh|oh)([\s\-]+\1)+\b', r'\1', texto, flags=re.IGNORECASE)

    # 6. Reduz interjeições como "e aí", "tá bom", "beleza" repetidas
    texto = re.sub(r'(?i)\b((e[ \-]?a[ií])|(tá bom)|(beleza))(\s+\1)+', r'\1', texto)

    # 7. Reduz repetições de linhas completas duplicadas consecutivamente
    texto = re.sub(r'^(.*)(\n\1)+$', r'\1', texto, flags=re.MULTILINE)

    # 8. Remove onomatopeias repetitivas ("tum tum tum", "plim plim")
    texto = re.sub(r'\b(\w{2,5})(\s+\1){2,}\b', r'\1', texto)

    # 9. Remove eco de palavras com variações mínimas ("vamos, vamos!", "sim... sim...")
    texto = re.sub(r'\b(\w+)[\W_]+(\1)\b', r'\1', texto, flags=re.IGNORECASE)

    # 10. Limpa repetições espaçadas com emojis ou símbolos: "ok ✅ ok ✅"
    texto = re.sub(r'\b(\w+)\s*[^\w\s]{1,3}\s*\1\b', r'\1', texto)

    return texto.strip()

def silero_vad_setup():
    global get_speech_timestamps, read_audio, VADIterator, collect_chunks
    get_speech_timestamps, read_audio, VADIterator, collect_chunks = silero_vad.setup_model(
        "silero_vad.jit",
        device=torch.device("cuda" if torch.cuda.is_available() else "cpu"),
        num_workers=0,
        threshold=0.5,
        sampling_rate=16000
    )
def eh_mp3(outputpath):
    return outputpath.endswith('.mp3')

def mp3_to_wav(input_path, output_path):
    command = [
        "ffmpeg", "-i", input_path,
        "-ar", "16000",  # taxa de amostragem
        "-ac", "1",      # mono
        output_path
    ]
    subprocess.run(command, check=True)


app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")
app.mount("/youtubeDownload", StaticFiles(directory="youtubeDownload"), name="youtube_download")
app.mount("/scripts", StaticFiles(directory="scripts"), name="scripts")
model_cache = {}
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
async def get_audio(websocket: WebSocket, data: dict):
        temp_dir = "tempo"
        os.makedirs(temp_dir, exist_ok=True)

        uid = uuid.uuid4().hex
        if "url" in data:
            output_path = f"tempo/temp_{uid}.wav"
            url = data["url"]
            command = [
                "yt-dlp", "-x", "--audio-format", "wav", "--no-playlist",
                "-o", output_path,
                url
            ]
            subprocess.run(command, check=True)
            if not os.path.exists(output_path):
                await websocket.send_json({
                    "error": f"Arquivo de áudio não foi criado: {output_path}"
                })
                raise Exception(f"Arquivo de áudio não foi criado: {output_path}")
            
            
            duration = get_audio_duration(output_path)
            return output_path, duration, uid, data
        else:
            output_path = f"tempo/temp_{uid}.mp3"

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
            duration = get_audio_duration(output_path)
        except Exception as e:
            error_msg = f"Erro ao obter duração do áudio: {str(e)}"
            await websocket.send_json({"error": error_msg})
            raise Exception(error_msg)
        if eh_mp3(output_path):
            wav_path = output_path.rsplit('.', 1)[0] + ".wav"
            mp3_to_wav(output_path, wav_path)
            os.remove(output_path)
            output_path = wav_path
        return output_path, duration, uid, None
    

@app.get("/", response_class=HTMLResponse)
async def form_get(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})
@app.websocket("/ws/video")
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
            await websocket.send_json({
                "error": f"Erro ao baixar o áudio: {result.stderr}"
            })
            raise Exception(f"Erro no yt-dlp:\n{result.stderr}")
        
        if not os.path.exists(output_path_audio):
            await websocket.send_json({
                "error": f"Arquivo de áudio não foi criado: {output_path_audio}"
            })
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
        model = data.get("model", "small")
        chunk_length_choice = int(data.get("chunk_length_choice", 60))
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
            transcriber_fast = Twhisper(model, device=device, compute_type="int8" if device == "cuda" else "int8")
            
            model_cache[model] = transcriber_fast
            await websocket.send_json({
                "message": f"✅ Modelo {model} carregado."
            })
            print(f"✅ Modelo {model} carregado.")
        model = model_cache[model]
        
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
                segments, _ = model.transcribe(
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
                os.remove(chunk_filename)
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
    del model_cache[model]  # remove a referência
    gc.collect()               # força coleta de lixo
    torch.cuda.empty_cache() 
    await websocket.close()
    print("INFO: connection closed")
@app.get("/download/{file_name}")
async def download_file(file_name: str):
    file_name = Path(file_name).name  # segurança contra path traversal
    audio_file_path = os.path.abspath(f"youtubeDownload/audio/{file_name}")
    transcribe_file_path = os.path.abspath(f"youtubeDownload/transcript/{file_name}")
    video_file_path = os.path.abspath(f"youtubeDownload/video/{file_name}")
    if os.path.exists(transcribe_file_path):
        return FileResponse(transcribe_file_path, filename=file_name, media_type='text/plain')
    
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
):
    client_ip = request.client.host
    uid = uuid.uuid4().hex
    output_path = f"youtubeDownload/nuvem/nuvem_{uid}.png"

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