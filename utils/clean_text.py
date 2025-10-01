def Clean_Text(texto: str) -> str:
    # Remove linhas com 1 ou 2 palavras, geralmente ruído ou marcações
    texto = re.sub(r'^(?:\s*\w+\s*){1,2}$', '', texto, flags=re.MULTILINE)

    # Remove sequências numéricas e pontuadas sem sentido (tipo "1. 2. 3.")
    texto = re.sub(r'(?:\d+\.\s*){3,}', '', texto)

    # Substitui sequências longas de pontuação por "..."
    texto = re.sub(r'\.{2,}', '..', texto)

    # Remove repetições consecutivas de palavras (ex: "o o o debate")
    texto = re.sub(r'\b(\w+)([\s\.,;:!?]+\1\b)+', r'\1', texto, flags=re.IGNORECASE)

    # Normaliza espaços múltiplos
    texto = re.sub(r' {2,}', ' ', texto)

    # Remove quebras de linha múltiplas
    texto = re.sub(r'\n{3,}', '\n\n', texto)

    # Remove espaços no início e fim de cada linha
    texto = re.sub(r'^\s+|\s+$', '', texto, flags=re.MULTILINE)

    # Remove linhas completamente vazias ou com só pontuação
    texto = re.sub(r'^\W*$', '', texto, flags=re.MULTILINE)

    # --- Novas adições para eliminar repetições exageradas ---

    # 1. Reduz repetições de frases simples (como "aperte o botão", "vamos lá") seguidas
    texto = re.sub(r'(?i)\b(.{3,100}?)([\s\.,;:!?]+\1\b)+', r'\1', texto)

    # 2. Reduz repetições exageradas de vírgulas
    texto = re.sub(r'(,\s*){2,}', ', ', texto)

    # 3. Reduz repetições exageradas de pontos de exclamação ou interrogação
    texto = re.sub(r'(!{2,})', '!', texto)
    texto = re.sub(r'(\?{2,})', '?', texto)

    # 4. Reduz risadas repetidas do tipo "haha haha", "kkk kkk"
    texto = re.sub(r'\b((ha){2,}|(kk+)){2,}', r'\1', texto, flags=re.IGNORECASE)

    # 5. Reduz sons como "ah ah ah", "uh uh"
    texto = re.sub(r'\b(ah|uh|oh)([\s\-]+\1)+\b', r'\1', texto, flags=re.IGNORECASE)

    # 6. Reduz interjeições como "e aí", "tá bom", "beleza" repetidas
    texto = re.sub(r'(?i)\b((e[ \-]?a[ií])|(tá bom)|(beleza))(\s+\1)+', r'\1', texto)

    # 7. Reduz repetições de linhas completas duplicadas consecutivamente
    texto = re.sub(r'^(.*)(\n\1)+$', r'\1', texto, flags=re.MULTILINE)

    # 8. Remove onomatopeias repetitivas ("tum tum tum", "plim plim")
    texto = re.sub(r'\b(\w{2,5})(\s+\1){2,}\b', r'\1', texto)

    # 9. Remove eco de palavras com variações mínimas ("vamos, vamos!", "sim... sim...")
    texto = re.sub(r'\b(\w+)[\W_]+(\1)\b', r'\1', texto, flags=re.IGNORECASE)

    # 10. Limpa repetições espaçadas com emojis ou símbolos: "ok ✅ ok ✅"
    texto = re.sub(r'\b(\w+)\s*[^\w\s]{1,3}\s*\1\b', r'\1', texto)

    return texto.strip()
import re