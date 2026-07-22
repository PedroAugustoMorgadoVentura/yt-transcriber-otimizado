import os
import uuid
from collections import Counter
from fastapi import Request, UploadFile, File

import nltk
from wordcloud import WordCloud
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from nltk.corpus import stopwords
from fastapi import APIRouter
from utils.runtime_paths import resolve_runtime_path

try:
    nltk.data.find('corpora/stopwords')
except LookupError:
    try:
        nltk.download('stopwords', quiet=True)
    except Exception:
        pass

router = APIRouter()

# dicionário global: UID da última imagem gerada por cada cliente (IP, por exemplo)
ultima_imagem_por_cliente = {}

@router.post("/upload/")
async def upload_file(
    request: Request,
    file: UploadFile = File(...),
):
    client_ip = request.client.host
    uid = uuid.uuid4().hex
    output_path = str(resolve_runtime_path("youtubeDownload", "nuvem", f"nuvem_{uid}.png"))

    # Remove imagem anterior, se houver
    ultima = ultima_imagem_por_cliente.get(client_ip)
    if ultima and os.path.exists(ultima):
        os.remove(ultima)

    try:
        stopwords_pt = set(stopwords.words('portuguese'))
    except LookupError:
        stopwords_pt = {
            'de','a','o','que','e','do','da','em','um','para','com','não','na','se','por','mais','os','as','ou','mas','foi','como','ao','ele','das','tem','à','ser','suas','me','te','nos','vos','meu','minha','tua','sua','nosso','nossa','seu','sua','está','estão','este','esta','isto','isso','aquilo','um','uma','uns','umas','ludovico','adriana'
        }
    else:
        stopwords_pt.update(['ludovico', 'adriana'])
    contents = await file.read()
    texto = contents.decode("utf-8").lower()
    palavras = ''.join(c if c.isalnum() or c.isspace() else ' ' for c in texto).split()
    palavras_filtradas = [p for p in palavras if p not in stopwords_pt]
    contador = Counter(palavras_filtradas)

    nuvem = WordCloud(width=870, height=400, background_color='white').generate_from_frequencies(contador)
    plt.figure(figsize=(10, 5))
    plt.imshow(nuvem, interpolation='bilinear')
    plt.axis('off')
    plt.tight_layout()
    plt.savefig(output_path)
    plt.close()

    # Atualiza última imagem do cliente
    ultima_imagem_por_cliente[client_ip] = output_path

    return {"message": "Nuvem gerada com sucesso!", "image_path": f"/{output_path}"}