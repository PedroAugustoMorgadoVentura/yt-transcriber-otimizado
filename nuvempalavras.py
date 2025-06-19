from collections import Counter
from wordcloud import WordCloud
import matplotlib.pyplot as plt
from tkinter import Tk, filedialog
import nltk
from nltk.corpus import stopwords

# Baixa as stopwords do NLTK (só é necessário uma vez)
#nltk.download('stopwords')

# Lista completa de stopwords em português
stopwords_pt = set(stopwords.words('portuguese'))
stopwords_pt.update(['ludovico'])
stopwords_pt.update(['adriana'])

# Abre janela para selecionar o arquivo
root = Tk()
root.withdraw()
caminho_arquivo = filedialog.askopenfilename(
    title="Selecione o arquivo de transcrição",
    filetypes=[("Arquivos de texto", "*.txt")]
)

# Lê o conteúdo
with open(caminho_arquivo, 'r', encoding='utf-8') as file:
    texto = file.read().lower()

# Remove caracteres especiais simples e separa as palavras
palavras = ''.join(c if c.isalnum() or c.isspace() else ' ' for c in texto).split()

# Filtra as palavras, excluindo as stopwords
palavras_filtradas = [p for p in palavras if p not in stopwords_pt]

# Conta a frequência
contador = Counter(palavras_filtradas)

# Gera nuvem de palavras
nuvem = WordCloud(width=800, height=400, background_color='white').generate_from_frequencies(contador)

# Exibe
plt.figure(figsize=(10, 5))
plt.imshow(nuvem, interpolation='bilinear')
plt.axis('off')
plt.tight_layout()
plt.show()
