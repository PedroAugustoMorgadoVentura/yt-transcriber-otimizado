import asyncio
import re
async def get_audio_duration(audio_path: str) -> float:
    result = await asyncio.create_subprocess_exec(
        *["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", audio_path],
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    
    stdout, stderr = await result.communicate()
    stdout = stdout.decode().strip()
    stderr = stderr.decode().strip()
    if result.returncode != 0:
        
        raise Exception(f"ffprobe error: {stderr.strip()}")
    duration = stdout.strip()

    return float(duration) if re.match(r'^\d+(\.\d+)?$', duration) else 0.0

