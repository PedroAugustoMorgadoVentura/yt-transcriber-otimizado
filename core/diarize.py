"""
Módulo de Diarização usando Pyannote.audio
Funções para identificar e separar locutores em áudio
Segue o padrão assíncrono do projeto
"""

import os
import asyncio
import torch
from typing import Optional, Dict, Any
from datetime import timedelta

try:
    from pyannote.audio import Pipeline
except ImportError:
    raise ImportError("pyannote.audio não está instalado. Instale com: pip install pyannote.audio")


_diarization_pipeline = None  # Cache global da pipeline


async def load_diarization_pipeline(use_auth_token: Optional[str] = None) -> Pipeline:
    """
    Carrega a pipeline de diarização com cache
    
    Args:
        use_auth_token: Token do Hugging Face (https://huggingface.co/settings/tokens)
                       Se None, tenta usar HUGGINGFACE_TOKEN do .env
    
    Returns:
        Pipeline de diarização carregado
    """
    global _diarization_pipeline
    
    if _diarization_pipeline is not None:
        return _diarization_pipeline
    
    if use_auth_token is None:
        use_auth_token = os.getenv("HUGGINGFACE_TOKEN")
    
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"🔄 Carregando pipeline de diarização (device: {device})...")
    
    _diarization_pipeline = await asyncio.to_thread(
        Pipeline.from_pretrained,
        "pyannote/speaker-diarization-3.0",
        use_auth_token=use_auth_token
    )
    _diarization_pipeline.to(torch.device(device))
    print("✅ Pipeline de diarização carregado")
    
    return _diarization_pipeline


async def diarize_audio(
    audio_path: str,
    num_speakers: Optional[int] = None,
    use_auth_token: Optional[str] = None,
    websocket=None
) -> Dict[str, Any]:
    """
    Realiza diarização de áudio (identifica locutores)
    Integrável com WebSocket para enviar progresso em tempo real
    
    Args:
        audio_path: Caminho do arquivo de áudio
        num_speakers: Número de locutores (None para auto-detectar)
        use_auth_token: Token do Hugging Face
        websocket: WebSocket opcional para enviar progresso
    
    Returns:
        Dict com:
        - speakers: lista de locutores encontrados
        - segments: segmentos com timing e speaker
        - num_speakers: número total de locutores
    """
    if not os.path.exists(audio_path):
        raise FileNotFoundError(f"Arquivo não encontrado: {audio_path}")
    
    print(f"🎙️ Iniciando diarização: {audio_path}")
    
    if websocket:
        await websocket.send_json({
            "message": "🎙️ Realizando diarização (identificando locutores)..."
        })
    
    try:
        pipeline = await load_diarization_pipeline(use_auth_token)
        
        # Realizar diarização em thread
        diarization = await asyncio.to_thread(
            pipeline,
            audio_path,
            num_speakers=num_speakers,
            min_duration_on=0.5
        )
        
        speakers_info = {}
        segments = []
        
        # Processar resultado
        for turn, _, speaker in diarization.itertracks(yield_label=True):
            start = turn.start
            end = turn.end
            duration = end - start
            
            if speaker not in speakers_info:
                speakers_info[speaker] = {
                    'speaker_id': speaker,
                    'first_appearance': start,
                    'last_appearance': end,
                    'total_duration': duration,
                    'num_segments': 1
                }
            else:
                speakers_info[speaker]['last_appearance'] = end
                speakers_info[speaker]['total_duration'] += duration
                speakers_info[speaker]['num_segments'] += 1
            
            segments.append({
                'speaker': speaker,
                'start': start,
                'end': end,
                'duration': duration
            })
        
        print(f"✅ Diarização completa. Detectados {len(speakers_info)} locutores")
        
        if websocket:
            await websocket.send_json({
                "message": f"✅ Diarização completa. {len(speakers_info)} locutores detectados."
            })
        
        return {
            'speakers': list(speakers_info.values()),
            'segments': segments,
            'num_speakers': len(speakers_info),
            'diarization_object': diarization
        }
        
    except Exception as e:
        print(f"❌ Erro na diarização: {str(e)}")
        if websocket:
            await websocket.send_json({
                "error": f"Erro na diarização: {str(e)}"
            })
        raise


def _format_timestamp(seconds: float) -> str:
    """Formata segundos em HH:MM:SS"""
    td = timedelta(seconds=seconds)
    hours, remainder = divmod(int(td.total_seconds()), 3600)
    minutes, secs = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


async def merge_diarization_with_transcription(
    transcription_result: Dict,
    diarization_result: Dict,
    websocket=None
) -> Dict[str, Any]:
    """
    Combina transcrição com diarização (quem falou o quê)
    
    Args:
        transcription_result: Resultado de transcribe_audio_with_chunks
        diarization_result: Resultado de diarize_audio
        websocket: WebSocket opcional para enviar progresso
    
    Returns:
        Dict com:
        - speaker_turns: [{'speaker', 'start', 'end', 'text'}]
        - speakers_summary: resumo por locutor
    """
    print("🔗 Combinando transcrição com diarização...")
    
    if websocket:
        await websocket.send_json({
            "message": "🔗 Combinando transcrição com diarização..."
        })
    
    try:
        transcription_segments = transcription_result.get('segments', [])
        diarization_segments = diarization_result.get('segments', [])
        
        # Criar speaker turns combinando ambas
        speaker_turns = []
        for dia_seg in diarization_segments:
            matching_text = ""
            
            # Encontrar textos que coincidem com este segmento de diarização
            for trans_seg in transcription_segments:
                if (trans_seg['start'] < dia_seg['end'] and 
                    trans_seg['end'] > dia_seg['start']):
                    matching_text += trans_seg['text'] + " "
            
            speaker_turns.append({
                'speaker': dia_seg['speaker'],
                'start': dia_seg['start'],
                'end': dia_seg['end'],
                'duration': dia_seg['duration'],
                'text': matching_text.strip() if matching_text.strip() else "[sem transcrição]",
                'start_formatted': _format_timestamp(dia_seg['start']),
                'end_formatted': _format_timestamp(dia_seg['end'])
            })
        
        # Resumir por locutor
        speakers_summary = {}
        for turn in speaker_turns:
            speaker_id = turn['speaker']
            if speaker_id not in speakers_summary:
                speakers_summary[speaker_id] = {
                    'speaker_id': speaker_id,
                    'total_duration': 0,
                    'num_turns': 0,
                    'all_text': []
                }
            
            speakers_summary[speaker_id]['total_duration'] += turn['duration']
            speakers_summary[speaker_id]['num_turns'] += 1
            speakers_summary[speaker_id]['all_text'].append(turn['text'])
        
        # Juntar textos por locutor
        for speaker_id in speakers_summary:
            speakers_summary[speaker_id]['text'] = " ".join(speakers_summary[speaker_id]['all_text'])
            del speakers_summary[speaker_id]['all_text']
        
        result = {
            'speaker_turns': speaker_turns,
            'speakers_summary': speakers_summary,
            'num_speakers': len(speakers_summary),
            'total_duration': transcription_result.get('duration', 0)
        }
        
        print(f"✅ Combinação completa: {len(speaker_turns)} turnos de fala")
        
        if websocket:
            await websocket.send_json({
                "message": f"✅ Combinação completa: {len(speaker_turns)} turnos de fala"
            })
        
        return result
        
    except Exception as e:
        print(f"❌ Erro ao combinar: {str(e)}")
        if websocket:
            await websocket.send_json({
                "error": f"Erro ao combinar transcrição e diarização: {str(e)}"
            })
        raise
