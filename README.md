# 🎙️ YouTube Transcriber & WordCloud Generator

> 🇧🇷 Aplicação web para baixar vídeos do YouTube, transcrever áudios com Whisper e gerar nuvens de palavras.  
> 🇺🇸 Web app to download YouTube videos, transcribe audio with Whisper, and generate word clouds.

## ✅ Requisitos / Requirements

- Python 3.10+
- ffmpeg instalado / installed
- GPU com suporte CUDA (opcional) / CUDA-enabled GPU (optional)
- instalar Git Bash / install Git Bash (recomended)
- Se usar gpu para acelerar processo, instale os drivers do link abaixo e coloque eles no path / if you are going to use GPU to faster process, install the drivers with the link below and put them on path
  [text](https://developer.nvidia.com/cudnn-downloads?)

## 🚀 Instalação / Installation

```bash
git clone https://github.com/PedroAugustoMorgadoVentura/yt-transcriber-otimizado
cd yt-transcriber-otimizado
pip install -r requirements.txt
run.py

```
## 📁 Estrutura / Structure

```
youtubeDownload/
├── audio/        # Áudios baixados / Downloaded audio
├── video/        # Vídeos baixados / Downloaded video
├── transcript/   # Transcrições / Transcriptions
├── nuvem/        # Nuvens de palavras / Word clouds
├── utils/
├──

static/           # Arquivos estáticos / Static files
templates/        # HTML com Jinja2 / Jinja2 templates
app.py            # App principal / Main app
```

## ⚙️ Funcionalidades / Features

- 🎥 Download de vídeos (até 1080p) / Video download (up to 1080p)
- 🎧 Extração de áudio em MP3 / Audio extraction in MP3
- 🧠 Transcrição automática com Whisper / Automatic transcription with Whisper
- ☁️ Geração de nuvem de palavras / Word cloud generation
- 🌍 Suporte a múltiplos idiomas / Multilingual support

## 📌 Melhorias Futuras / Future Improvements
- 💸 Sistema de monetização / Monetization system
- 👤 Sistema de usuários / User accounts
- ⭐ Funcionalidade de assinatura / Subscription feature

## 🤝 Contribuição / Contributing

Contribuições são bem-vindas!
Pull requests e sugestões são encorajados.
Contributions are welcome!
Pull requests and suggestions encouraged.

## 🧡 Autor / Author

Pedro Augusto – 2025
Gabrieli da Silva Adão Monteiro - 2026

