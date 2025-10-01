import subprocess
def eh_mp3(outputpath):
    return outputpath.endswith('.mp3')

def mp3_to_wav(input_path, output_path):
    command = [
        "ffmpeg", "-i", input_path,
        "-ar", "16000",  # taxa de amostragem
        "-ac", "1",      # mono
        output_path
    ]
    subprocess.run(command, check=True)