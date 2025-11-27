# services/charge_model.py (ou onde quer que esteja)
import torch
from faster_whisper import WhisperModel as Twhisper

model_cache = {} # Cache global para modelos Whisper carregados

def Charge_Model(model_name: str) -> Twhisper:
    if model_name not in model_cache:
        print(f"🔄 Carregando modelo Whisper: {model_name}")
        device = "cuda" if torch.cuda.is_available() else "cpu"
        # AQUI: Armazena a instância real do modelo Twhisper
        model_instance = Twhisper(model_name, device=device, compute_type="int8" if device == "cuda" else "int4")
        model_cache[model_name] = model_instance
        print(f"✅ Modelo {model_name} carregado.")
        return model_instance
    else:
        print(f"✅ Modelo {model_name} já estava carregado.")
        return model_cache[model_name]