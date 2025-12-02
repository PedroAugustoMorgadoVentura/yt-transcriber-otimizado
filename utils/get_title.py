import asyncio
from pathlib import Path

async def get_title_from_youtube_url(url: str) -> str:
    try:
        result = await asyncio.create_subprocess_exec(
            "yt-dlp", "--get-title", url,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await result.communicate()
        
        
        
        if result.returncode != 0:
            erro = stderr.decode().strip()
            print(f"Erro ao obter título: {erro}")
            return "unknown_title"
        title = stdout.decode().strip()
        return title
    
    except Exception as e:
        print(f"Erro não esperado: {e}")
        return "unknown_title"
    
    
def get_title_from_file_path_modern(file_path: str) -> str:
    """Retorna o nome do arquivo sem a extensão usando pathlib."""
    return Path(file_path).stem
