# utils/conversionfiles.py

import asyncio # Importar asyncio para usar create_subprocess_exec
import os # Para os.path.exists se necessário em alguma validação

# A função is_not_wav é síncrona e não bloqueante, não precisa ser async def.
# Será chamada com asyncio.to_thread em funções async def.
def is_wav(file_path: str) -> bool:
    return file_path.lower().endswith('.wav')

async def video_to_audio_converter(video_path: str, output_path: str):
    command = ["ffmpeg", "-i", video_path, "-vn", "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1", output_path]
    process = await asyncio.create_subprocess_exec(
        *command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE)
    
    
    stdout, stderr = await process.communicate()
    if process.returncode != 0:
        raise Exception(f"Erro na conversão de vídeo para áudio: {stderr.decode()}")
    return output_path

# convert_to_wav AGORA É UMA FUNÇÃO ASSÍNCRONA
async def convert_to_wav(input_path: str, output_path: str):
    command = [
        "ffmpeg", "-i", input_path,
        "-vn",          # remove a faixa de vídeo
        "-ar", "16000",  # taxa de amostragem
        "-ac", "1",      # mono
        "-c:a", "pcm_s16le", # Especifica codec de áudio PCM de 16-bit little-endian
        output_path
    ]
    
    # Inicia o subprocesso ffmpeg de forma assíncrona
    process = await asyncio.create_subprocess_exec(
        *command, # Usa * para desempacotar a lista de comandos
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    
    # Aguarda o subprocesso terminar e captura a saída
    stdout, stderr = await process.communicate()
    
    # Verifica o código de retorno do ffmpeg
    if process.returncode != 0:
        error_message = stderr.strip() if stderr else f"FFmpeg failed to convert {input_path}"
        raise Exception(f"FFmpeg conversion error (code {process.returncode}): {error_message}")
    
    # Opcional: Você pode querer verificar se o arquivo de saída realmente existe
    # if not await asyncio.to_thread(os.path.exists, output_path):
    #     raise Exception(f"Arquivo WAV não foi criado após conversão: {output_path}")