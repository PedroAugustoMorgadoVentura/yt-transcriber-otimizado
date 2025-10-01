import subprocess
from pathlib import Path

def get_title_from_youtube_url(url: str) -> str:
    try:
        result = subprocess.run(
            ["yt-dlp", "--get-title", url],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True
        )
        title = result.stdout.strip()
        return title
    except subprocess.CalledProcessError as e:
        print(f"Erro ao obter título: {e.stderr}")
        return "unknown_title"
    
    
def get_title_from_file_path_modern(file_path: str) -> str:
    """Retorna o nome do arquivo sem a extensão usando pathlib."""
    return Path(file_path).stem
