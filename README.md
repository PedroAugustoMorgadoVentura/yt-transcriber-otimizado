# 🎙️ YouTube Transcriber & WordCloud Generator

Este projeto é uma aplicação web construída com FastAPI e outras bibliotecas para permitir:

- Baixar vídeos e áudios do YouTube
- Transcrever o áudio dos vídeos automaticamente com Whisper
- Gerar nuvens de palavras a partir de textos transcritos ou arquivos `.txt`

## ✅ Requisitos

- Python 3.10 ou superior
- ffmpeg instalado e no PATH
- GPU com suporte CUDA (opcional, para acelerar o Whisper)

## 🧪 Instalação

1. Clone este repositório:

```bash
git clone https://github.com/seu-usuario/seu-repositorio.git
cd nome-do-projeto
```

2. Instale as dependências:

```bash
pip install -r requirements.txt
```

3. Execute o servidor local:

```bash
uvicorn app:app --reload
```

4. Acesse a aplicação via navegador:

Abra o link `http://127.0.0.1:8000` mostrado no terminal após iniciar o servidor.

## 📁 Estrutura de Pastas

```
youtubeDownload/
├── audio/        # Áudios baixados
├── video/        # Vídeos baixados
├── transcript/   # Transcrições em texto
├── nuvem/        # Nuvens de palavras geradas
static/           # Arquivos estáticos (CSS, JS, imagens)
templates/        # HTML renderizado com Jinja2
app.py            # Código principal da aplicação
```

## ⚙️ Funcionalidades

- 🎥 Download de vídeos em até 1080p
- 🎧 Extração de áudio em MP3
- 🧠 Transcrição de áudios com Whisper
- ☁️ Criação de nuvem de palavras com base em frequência

## 🤝 Contribuição

Sinta-se à vontade para sugerir melhorias, abrir issues ou enviar pull requests.

## 🧡 Autor

Pedro Augusto – 2025
