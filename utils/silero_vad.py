import torch
import silero_vad

def silero_vad_setup():
    global get_speech_timestamps, read_audio, VADIterator, collect_chunks
    get_speech_timestamps, read_audio, VADIterator, collect_chunks = silero_vad.setup_model(
        "silero_vad.jit",
        device=torch.device("cuda" if torch.cuda.is_available() else "cpu"),
        num_workers=0,
        threshold=0.5,
        sampling_rate=16000
    )