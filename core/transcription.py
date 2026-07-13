import os
import asyncio
def _safe_next(it):
        try:
            return next(it)
        except StopIteration:
            return None
async def brute_transcription(audio_path, model, language):
    """Transcreve um arquivo de áudio e emite os segmentos conforme vão sendo processados."""
    if not audio_path:
        raise ValueError("audio_path is obrigatório")

    if not os.path.exists(audio_path):
        raise FileNotFoundError(f"Arquivo de áudio não encontrado: {audio_path}")

    if model is None:
        raise ValueError("model é obrigatório")

    if not hasattr(model, "transcribe") or not callable(getattr(model, "transcribe")):
        raise TypeError("model deve expor um método 'transcribe' chamável")
        
    transcriber_fast = model
    
    try:
        segments, _ = await asyncio.to_thread(
            transcriber_fast.transcribe,
            audio_path,
            language=language,
            vad_filter=True,
            # Seus parâmetros mantidos conforme solicitado2
            vad_parameters=dict(min_speech_duration_ms=150, min_silence_duration_ms=150, threshold=0.30),
            beam_size=1,
        )
    except Exception as exc: 
        raise RuntimeError(f"Erro ao transcrever o áudio '{audio_path}': {exc}") from exc

    segment_timestamps = []
    
    # Transforma o gerador síncrono em um iterador iterável manualmente
    iterator = iter(segments or [])

    
    while True:
        try:
            # 🎯 Isola o avanço síncrono do iterador C++ do Faster-Whisper dentro da Thread Pool
            segment = await asyncio.to_thread(_safe_next, iterator)
            if segment is None:
                break  # O iterador chegou ao fim
        except StopIteration:
            # O iterador chegou ao fim, quebra o laço while
            break

        start_time = getattr(segment, "start", None)
        end_time = getattr(segment, "end", None)
        text = getattr(segment, "text", "")

        if start_time is None or end_time is None:
            raise ValueError(f"Segmento inválido recebido da transcrição: {segment}")

        segment_timestamps.append((start_time, end_time, text))
        yield start_time, end_time, text