import asyncio
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import os
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from routers import transcription, downloads, wordcloud, video_department, audio_department
if os.name == 'nt': # 'nt' é o código para o sistema operacional Windows
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

# Desativa o uso de symlinks no cache do Hugging Face
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1" 
load_dotenv()  # Carrega variáveis de ambiente do .env
app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")
app.mount("/youtubeDownload", StaticFiles(directory="youtubeDownload"), name="youtube_download")
app.mount("/scripts", StaticFiles(directory="scripts"), name="scripts")


app.include_router(transcription.router)
app.include_router(downloads.router)
app.include_router(wordcloud.router)
app.include_router(video_department.router)
app.include_router(audio_department.router)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
@app.get("/", response_class=HTMLResponse)
async def form_get(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

