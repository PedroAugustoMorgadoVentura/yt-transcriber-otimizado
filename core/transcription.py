"""
Módulo de Transcrição usando Faster Whisper
Funções para transcrever áudio em texto com suporte a GPU
Segue o padrão assíncrono do projeto
"""

import os
import asyncio
from typing import Optional, Dict, Any
from services.charge_model import Charge_Model
from utils.clean_text import Clean_Text
from utils.get_audio_duration import get_audio_duration


async def transcribe_chunk(
    audio_path: str,
    model,
    language: Optional[str] = None,
    beam_size: int = 1,
    vad_filter: bool = True
) -> Dict[str, Any]:
    """
    Transcreve um chunk de áudio
    
    Args:
        audio_path: Caminho do arquivo de áudio
        model: Modelo Whisper já carregado
        language: Código do idioma ou None para auto-detectar
        beam_size: Tamanho do beam search
        vad_filter: Usar Voice Activity Detection
    
    Returns:
        Dict com texto limpo e metadados
    """
    segments, info = await asyncio.to_thread(
        model.transcribe,
        audio_path,
        language=language,
        beam_size=beam_size,
        vad_filter=vad_filter
    )
    
    text = "".join(seg.text for seg in segments)
    clean_text = Clean_Text(text)
    
    return {
        'text': clean_text,
        'raw_text': text,
        'language': info.language if hasattr(info, 'language') else language,
    }


async def transcribe_audio_with_chunks(
    audio_path: str,
    model_name: str = "small",
    chunk_length: int = 30,
    overlap: int = 2,
    language: Optional[str] = None,
    beam_size: int = 1,
    websocket=None
) -> Dict[str, Any]:
    """
    Transcreve áudio em chunks para melhor gerenciamento de memória
    Integrável com WebSocket para enviar progresso em tempo real
    
    Args:
        audio_path: Caminho do arquivo de áudio
        model_name: Modelo Whisper (tiny, base, small, medium, large)
        chunk_length: Duração de cada chunk em segundos
        overlap: Sobreposição entre chunks em segundos
        language: Código do idioma ou None para auto-detectar
        beam_size: Tamanho do beam search (1-5)
        websocket: WebSocket opcional para enviar progresso
    
    Returns:
        Dict com:
        - transcription: texto completo transcrito
        - segments: lista de segmentos com timing
        - language: idioma detectado
        - duration: duração total do áudio
    """
    if not os.path.exists(audio_path):
        raise FileNotFoundError(f"Arquivo não encontrado: {audio_path}")
    
    # Carregar modelo uma vez
    model = await asyncio.to_thread(Charge_Model, model_name)
    
    # Obter duração
    duration = await get_audio_duration(audio_path)
    
    transcriptions = []
    segments_data = []
    detected_language = language
    
    print(f"⏳ Iniciando transcrição: {audio_path} ({duration:.0f}s)")
    
    for start in range(0, int(duration), chunk_length - overlap):
        end = min(start + chunk_length, int(duration))
        chunk_filename = f"chunk_{start}_{end}.wav"
        
        try:
            # Criar chunk com ffmpeg
            print(f"📦 Criando chunk: {start}s → {end}s")
            process = await asyncio.create_subprocess_exec(
                "ffmpeg",
                "-i", audio_path,
                "-ss", str(start),
                "-to", str(end),
                "-ac", "1",
                "-ar", "16000",
                "-vn",
                "-f", "wav",
                chunk_filename,
                "-y",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await process.communicate()
            
            if not os.path.exists(chunk_filename):
                raise Exception(f"Falha ao criar chunk: {chunk_filename}")
            
            # Transcrever chunk
            result = await transcribe_chunk(
                chunk_filename,
                model,
                language=language,
                beam_size=beam_size,
                vad_filter=True
            )
            
            if detected_language is None:
                detected_language = result['language']
            
            transcriptions.append(f"\n{start} --> {end} segundos: {result['text']}")
            segments_data.append({
                'start': start,
                'end': end,
                'text': result['text']
            })
            
            # Calcular progresso
            progress = int((end / duration) * 100)
            message = f"✅ Transcrito até {end} segundos de {duration:.0f} segundos totais."
            
            print(message)
            
            # Enviar progresso via WebSocket se disponível
            if websocket:
                await websocket.send_json({
                    "progress": progress,
                    "message": message,
                    "transcription": "\n".join(transcriptions)
                })
        
        finally:
            # Limpar chunk
            if os.path.exists(chunk_filename):
                await asyncio.to_thread(os.remove, chunk_filename)
    
    return {
        'transcription': "\n".join(transcriptions),
        'segments': segments_data,
        'language': detected_language,
        'duration': duration,
        'model': model_name
    }


