# 📚 Guia de Integração - Core (Transcrição e Diarização)

## 📌 Resumo das Mudanças

Os módulos `core/transcription.py` e `core/diarize.py` foram refeitos seguindo o padrão assíncrono do seu projeto:

### ✅ `core/transcription.py`
- **`transcribe_chunk()`**: Transcreve um chunk individual
- **`transcribe_audio_with_chunks()`**: Transcreve áudio em chunks com progresso via WebSocket

### ✅ `core/diarize.py`
- **`load_diarization_pipeline()`**: Carrega o modelo de diarização com cache
- **`diarize_audio()`**: Realiza diarização (identificar locutores)
- **`merge_diarization_with_transcription()`**: Combina transcrição + diarização

---

## 🚀 Como Integrar no Seu Projeto

### Opção 1: Adicionar Diarização Opcional no Router Existente

Atualize `routers/transcription.py` para permitir habilitar/desabilitar diarização:

```python
# Em routers/transcription.py
import asyncio
from fastapi import WebSocket, APIRouter
import os
import traceback
from pathlib import Path
import torch
from services.audioprocess import get_audio
from services.charge_model import Charge_Model
from utils.get_title import get_title_from_file_path_modern
# ✅ ADICIONAR IMPORTS DO CORE
from core.transcription import transcribe_audio_with_chunks
from core.diarize import diarize_audio, merge_diarization_with_transcription

router = APIRouter()

@router.websocket("/ws/transcribe")
async def websocket_transcribe(websocket: WebSocket):
    await websocket.accept()
    output_path = None 
    print("INFO: connection open")
    try:
        # ✅ RECEBER DADOS INCLUINDO OPÇÃO DE DIARIZAÇÃO
        data = await websocket.receive_json()
        model = data.get("model", "small")
        chunk_length_choice = int(data.get("chunk_length_choice"))
        language = data.get("language")
        enable_diarization = data.get("enable_diarization", False)  # ✅ NOVO
        language = None if language == "none" else language
        
        if "url" in data:
            url = data["url"]
            await websocket.send_json({
                "message": f"⏳ Baixando áudio do vídeo: {url}..."
            })
            print(f"⏳ Baixando áudio do vídeo: {url}...")
        
        # ✅ USAR FUNÇÃO DO CORE
        output_path, duration, uid, data_info = await get_audio(websocket, data)
        title = get_title_from_file_path_modern(output_path)
        
        # ✅ TRANSCREVER USANDO CORE
        transcription_result = await transcribe_audio_with_chunks(
            audio_path=output_path,
            model_name=model,
            chunk_length=chunk_length_choice,
            language=language,
            websocket=websocket
        )
        
        # ✅ SE DIARIZAÇÃO ATIVADA, FAZER DIARIZAÇÃO
        combined_result = transcription_result
        if enable_diarization:
            await websocket.send_json({
                "message": "🎙️ Iniciando diarização (identificar locutores)..."
            })
            
            diarization_result = await diarize_audio(
                audio_path=output_path,
                websocket=websocket
            )
            
            # ✅ COMBINAR TRANSCRIÇÃO COM DIARIZAÇÃO
            combined_result = await merge_diarization_with_transcription(
                transcription_result=transcription_result,
                diarization_result=diarization_result,
                websocket=websocket
            )
        
        # ✅ LIMPAR ARQUIVO DE ÁUDIO
        await asyncio.to_thread(os.remove, output_path)
        
        # ✅ SALVAR ARQUIVO
        transcript_dir = Path("youtubeDownload/transcript")
        transcript_dir.mkdir(parents=True, exist_ok=True)
        
        if enable_diarization:
            # Salvar com diarização (quem falou o quê)
            output_text = "🎙️ TRANSCRIÇÃO COM DIARIZAÇÃO\n"
            output_text += "=" * 60 + "\n\n"
            for turn in combined_result['speaker_turns']:
                output_text += f"[{turn['start_formatted']} → {turn['end_formatted']}] {turn['speaker']}:\n"
                output_text += f"{turn['text']}\n\n"
            
            txt_path = transcript_dir / f"transcription_diarized_{title}_{uid}.txt"
        else:
            # Salvar sem diarização (apenas transcrição)
            output_text = combined_result['transcription']
            txt_path = transcript_dir / f"transcription_{title}_{uid}.txt"
        
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write(output_text)
        
        # ✅ ENVIAR RESULTADO FINAL
        await websocket.send_json({
            "progress": 100,
            "message": "✅ Processamento concluído!",
            "transcription": output_text,
            "download_url": f"/download/{txt_path.name}",
            "num_speakers": combined_result.get('num_speakers', 0),
            "has_diarization": enable_diarization
        })
        
    except Exception as e:
        traceback.print_exc()
        await websocket.send_json({
            "error": f"{str(e)}\n\n{traceback.format_exc()}"
        })
    finally:
        if output_path and await asyncio.to_thread(os.path.exists, output_path):
            await asyncio.to_thread(os.remove, output_path)
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            print("INFO: cleaning up model from memory")
        await websocket.close()
    
    print("INFO: connection closed")
```

---

### Opção 2: Criar Router Separado para Diarização

Crie um novo arquivo `routers/diarization.py`:

```python
# routers/diarization.py
import asyncio
from fastapi import WebSocket, APIRouter
import os
import traceback
from pathlib import Path
import torch
from services.audioprocess import get_audio
from utils.get_title import get_title_from_file_path_modern
from core.diarize import diarize_audio, merge_diarization_with_transcription
from core.transcription import transcribe_audio_with_chunks

router = APIRouter()

@router.websocket("/ws/diarize-and-transcribe")
async def websocket_diarize_and_transcribe(websocket: WebSocket):
    """
    WebSocket para transcrição completa com diarização
    Sempre faz ambas as operações
    """
    await websocket.accept()
    output_path = None 
    print("INFO: connection open")
    try:
        data = await websocket.receive_json()
        model = data.get("model", "small")
        chunk_length_choice = int(data.get("chunk_length_choice", 30))
        language = data.get("language")
        language = None if language == "none" else language
        
        if "url" in data:
            url = data["url"]
            await websocket.send_json({
                "message": f"⏳ Baixando áudio do vídeo: {url}..."
            })
            print(f"⏳ Baixando áudio do vídeo: {url}...")
        
        # Obter áudio
        output_path, duration, uid, data_info = await get_audio(websocket, data)
        title = get_title_from_file_path_modern(output_path)
        
        # Transcrever
        await websocket.send_json({
            "message": "🔤 Iniciando transcrição..."
        })
        transcription_result = await transcribe_audio_with_chunks(
            audio_path=output_path,
            model_name=model,
            chunk_length=chunk_length_choice,
            language=language,
            websocket=websocket
        )
        
        # Diarizar
        diarization_result = await diarize_audio(
            audio_path=output_path,
            websocket=websocket
        )
        
        # Combinar
        combined_result = await merge_diarization_with_transcription(
            transcription_result=transcription_result,
            diarization_result=diarization_result,
            websocket=websocket
        )
        
        # Limpar
        await asyncio.to_thread(os.remove, output_path)
        
        # Salvar resultado
        transcript_dir = Path("youtubeDownload/transcript")
        transcript_dir.mkdir(parents=True, exist_ok=True)
        
        output_text = "🎙️ TRANSCRIÇÃO COM DIARIZAÇÃO\n"
        output_text += "=" * 60 + "\n\n"
        output_text += f"Total de locutores: {combined_result['num_speakers']}\n"
        output_text += f"Duração total: {combined_result['total_duration']:.0f}s\n\n"
        
        for turn in combined_result['speaker_turns']:
            output_text += f"[{turn['start_formatted']} → {turn['end_formatted']}] {turn['speaker']}:\n"
            output_text += f"{turn['text']}\n\n"
        
        txt_path = transcript_dir / f"diarized_{title}_{uid}.txt"
        
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write(output_text)
        
        await websocket.send_json({
            "progress": 100,
            "message": "✅ Transcrição e diarização concluídas!",
            "transcription": output_text,
            "download_url": f"/download/{txt_path.name}",
            "num_speakers": combined_result['num_speakers'],
            "speaker_turns_count": len(combined_result['speaker_turns'])
        })
        
    except Exception as e:
        traceback.print_exc()
        await websocket.send_json({
            "error": f"{str(e)}\n\n{traceback.format_exc()}"
        })
    finally:
        if output_path and await asyncio.to_thread(os.path.exists, output_path):
            await asyncio.to_thread(os.remove, output_path)
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            print("INFO: cleaning up model from memory")
        await websocket.close()
    
    print("INFO: connection closed")
```

Se usar essa opção, adicione no `app/main.py`:

```python
from routers import transcription, diarization  # ✅ ADICIONAR

# ...

app.include_router(transcription.router)
app.include_router(diarization.router)  # ✅ ADICIONAR
```

---

## 🎨 Atualizar Frontend (HTML/JavaScript)

No seu `templates/index.html`, adicione um checkbox para habilitar diarização:

```html
<!-- Adicionar no formulário -->
<div class="form-group">
    <label>
        <input type="checkbox" id="enableDiarization" name="enable_diarization" />
        ✅ Habilitar Diarização (identificar locutores)
    </label>
</div>

<!-- Atualizar o envio do WebSocket -->
<script>
function startTranscription() {
    const enableDiarization = document.getElementById('enableDiarization').checked;
    
    const data = {
        url: document.getElementById('urlInput').value,
        model: document.getElementById('modelSelect').value,
        chunk_length_choice: document.getElementById('chunkLength').value,
        language: document.getElementById('languageSelect').value,
        enable_diarization: enableDiarization  // ✅ NOVO
    };
    
    ws.send(JSON.stringify(data));
}
</script>
```

---

## 📋 Estrutura de Resposta

### Sem Diarização
```json
{
    "progress": 100,
    "message": "✅ Transcrição concluída!",
    "transcription": "...",
    "download_url": "/download/...",
    "num_speakers": 0,
    "has_diarization": false
}
```

### Com Diarização
```json
{
    "progress": 100,
    "message": "✅ Processamento concluído!",
    "transcription": "[00:00:10 → 00:00:25] Speaker_1:\nTexto aqui...\n\n[00:00:25 → 00:00:40] Speaker_2:\nOutro texto...",
    "download_url": "/download/...",
    "num_speakers": 2,
    "has_diarization": true
}
```

---

## 🔐 Configuração - Tokens Necessários

### Para Diarização (Pyannote)

Crie um arquivo `.env` na raiz do projeto:

```env
# .env
HUGGINGFACE_TOKEN=hf_xxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

Para obter o token:
1. Acesse https://huggingface.co/settings/tokens
2. Crie um novo token (read permission)
3. Cole no `.env`

---

## ✨ Recursos Principais

### Transcrição
- ✅ Processamento em chunks (gerencia melhor memória)
- ✅ Suporte a GPU com CUDA
- ✅ Múltiplos idiomas
- ✅ Progresso em tempo real via WebSocket
- ✅ Limpeza automática de GPU

### Diarização
- ✅ Identificação automática de locutores
- ✅ Sem necessidade de especificar número de locutores
- ✅ Combina automáticamente com transcrição (quem falou o quê)
- ✅ Timestamps formatados
- ✅ Resumo por locutor

---

## 🎯 Exemplo de Uso Direto no Python

Se quiser usar sem WebSocket:

```python
# Exemplo de uso
import asyncio
from core.transcription import transcribe_audio_with_chunks
from core.diarize import diarize_audio, merge_diarization_with_transcription

async def main():
    audio_file = "temp/meu_audio.wav"
    
    # Transcrever
    trans = await transcribe_audio_with_chunks(
        audio_path=audio_file,
        model_name="small",
        chunk_length=30,
        language="pt"
    )
    print(f"Texto: {trans['transcription']}")
    
    # Diarizar
    dia = await diarize_audio(audio_path=audio_file)
    print(f"Locutores: {dia['num_speakers']}")
    
    # Combinar
    combined = await merge_diarization_with_transcription(trans, dia)
    for turn in combined['speaker_turns']:
        print(f"{turn['speaker']}: {turn['text']}")

asyncio.run(main())
```

---

## 🐛 Troubleshooting

### Erro: "pyannote.audio não está instalado"
```bash
pip install pyannote.audio
```

### Erro: "Token de autenticação inválido"
- Verifique se o token está correto em `.env`
- Token deve ter permission `read`

### Erro: "CUDA out of memory"
- Reduza `chunk_length` para valores menores (ex: 20 em vez de 30)
- Use modelo menor (ex: "tiny" em vez de "small")

### Diarização muito lenta
- É normal! Pode levar 1-2 minutos dependendo da duração do áudio
- GPU acelera bastante se disponível

---

## 📝 Resumo das Mudanças

| Arquivo | Mudanças |
|---------|----------|
| `core/transcription.py` | ✅ Refeito com funções assíncronas simples |
| `core/diarize.py` | ✅ Refeito com funções assíncronas simples |
| `routers/transcription.py` | 📝 Exemplo de integração da Opção 1 |
| `routers/diarization.py` | 📝 Exemplo de router separado (Opção 2) |
| `.env` | 📝 Adicionar HUGGINGFACE_TOKEN |

---

**Escolha a opção que melhor se adequa ao seu projeto!** 🚀
