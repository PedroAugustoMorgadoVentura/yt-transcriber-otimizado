import os
import uuid
from collections import Counter
from fastapi import Request, UploadFile, File

import nltk
from wordcloud import WordCloud
import matplotlib.pyplot as plt
from nltk.corpus import stopwords
from fastapi import APIRouter

try:
    nltk.data.find('corpora/stopwords')
except LookupError:
    nltk.download('stopwords')

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
    output_path = f"youtubeDownload/nuvem/nuvem_{uid}.png"

    # Remove imagem anterior, se houver
    ultima = ultima_imagem_por_cliente.get(client_ip)
    if ultima and os.path.exists(ultima):
        os.remove(ultima)

    stopwords_pt = set(stopwords.words('portuguese'))
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