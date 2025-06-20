import time
import torch
import gc
import tkinter as tk
from tkinter import filedialog
from faster_whisper import WhisperModel as FasterModel
import whisper as OriginalWhisper
import os

# Seleciona o arquivo de áudio
def escolher_arquivo():
    root = tk.Tk()
    root.withdraw()
    caminho = filedialog.askopenfilename(
        title="Selecione o arquivo de áudio",
        filetypes=[("Áudio", "*.mp3 *.wav *.m4a *.flac"), ("Todos os arquivos", "*.*")]
    )
    root.destroy()
    return caminho

audio_path = escolher_arquivo()
if not audio_path or not os.path.isfile(audio_path):
    print("Nenhum arquivo válido selecionado. Encerrando.")
    exit(1)

device = "cuda" if torch.cuda.is_available() else "cpu"

def benchmark_model(name, model_loader, transcriber):
    gc.collect()
    if device == "cuda":
        torch.cuda.empty_cache()

    print(f"\nTestando modelo: {name}")
    start = time.time()
    model = model_loader()
    load_time = time.time() - start

    start = time.time()
    result = transcriber(model)
    transcribe_time = time.time() - start

    print(f"Tempo de carregamento: {load_time:.2f}s")
    print(f"Tempo de transcrição: {transcribe_time:.2f}s")
    print(f"Trecho da transcrição: {result[:150]}...\n")

def load_faster_whisper():
    return FasterModel("small", device=device, compute_type="float16" if device == "cuda" else "int8")

def transcribe_faster_whisper(model):
    segments, _ = model.transcribe(audio_path, language="pt")
    return "".join(seg.text for seg in segments)

def load_whisper():
    return OriginalWhisper.load_model("small", device=device)

def transcribe_whisper(model):
    result = model.transcribe(audio_path, language="pt", fp16=(device == "cuda"))
    return result["text"]

benchmark_model("Faster Whisper", load_faster_whisper, transcribe_faster_whisper)
benchmark_model("Whisper Original", load_whisper, transcribe_whisper)
