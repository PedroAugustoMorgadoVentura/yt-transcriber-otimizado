# utils/conversionfiles.py

import asyncio # Importar asyncio para usar create_subprocess_exec
import os # Para os.path.exists se necessário em alguma validação

# A função eh_mp3 é síncrona e não bloqueante, não precisa ser async def.
# Será chamada com asyncio.to_thread em funções async def.
def eh_mp3(file_path: str) -> bool:
    # return file_path.lower().endswith('.mp3') # Melhor usar lower() para case-insensitivity
    # Uma verificação mais robusta de tipo de arquivo (com ffprobe) seria ideal,
    # mas por enquanto, a extensão é suficiente.
    return file_path.lower().endswith('.mp3')


# mp3_to_wav AGORA É UMA FUNÇÃO ASSÍNCRONA
async def mp3_to_wav(input_path: str, output_path: str):
    command = [
        "ffmpeg", "-i", input_path,
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