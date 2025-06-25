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

    return {
        "nome": name,
        "tempo_carregamento": load_time,
        "tempo_transcricao": transcribe_time,
        "texto": result
    }

def load_faster_whisper():
    # Use int8 na GPU por exemplo, ou float16 se preferir e device == cuda
    return FasterModel("medium", device=device, compute_type="int8" if device == "cuda" else "int8")

def transcribe_faster_whisper(model):
    segments, _ = model.transcribe(audio_path, language="pt")
    return "".join(seg.text for seg in segments)

def load_whisper():
    return OriginalWhisper.load_model("small", device=device)

def transcribe_whisper(model):
    result = model.transcribe(audio_path, language="pt", fp16=(device == "cuda"))
    return result["text"]

# Executa benchmarks
res_faster = benchmark_model("Faster Whisper", load_faster_whisper, transcribe_faster_whisper)
res_original = benchmark_model("Whisper Original", load_whisper, transcribe_whisper)

# Salva resultados em um arquivo .txt
output_file = "resultado_transcricoes.txt"
with open(output_file, "w", encoding="utf-8") as f:
    for res in [res_faster, res_original]:
        f.write(f"=== Resultado do {res['nome']} ===\n")
        f.write(f"Tempo de carregamento: {res['tempo_carregamento']:.2f} segundos\n")
        f.write(f"Tempo de transcrição: {res['tempo_transcricao']:.2f} segundos\n\n")
        f.write(res["texto"] + "\n\n")
        f.write("="*40 + "\n\n")

print(f"Resultados salvos em {output_file}")
