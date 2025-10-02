import re
import html
import unicodedata
from typing import List, Callable

#==============================================================================
# == MÓDULOS DE LIMPEZA (AS "ESTAÇÕES" DA PIPELINE)
#==============================================================================
# Usamos um "_" no início para indicar que são funções "internas",
# a serem usadas pela função principal Clean_Text.

# --- Categoria 1: Remoção Estrutural e de Metadados ---

def _remove_html_tags(text: str) -> str:
    """Remove tags HTML como <p>, <div>, etc."""
    return re.sub(r'<[^>]+>', '', text)

def _decode_html_entities(text: str) -> str:
    """Converte entidades HTML (ex: &amp;) para caracteres (ex: &)."""
    return html.unescape(text)

def _remove_timestamps_and_metadata(text: str) -> str:
    """Remove timestamps [00:12:34] e metadados entre colchetes/parênteses (risos)."""
    return re.sub(r'\[[^\]]*\]|\([^)]*\)', '', text)


def _remove_urls_and_emails(text: str) -> str:
    """Remove URLs e endereços de email."""
    text = re.sub(r'https?://\S+|www\.\S+', '', text)
    text = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '', text)
    return text

# --- Categoria 2: Normalização e Padronização ---

def _normalize_whitespace(text: str) -> str:
    """Consolida todos os tipos de espaços e quebras de linha."""
    text = re.sub(r'[\t\r\f\v]', ' ', text)
    text = re.sub(r' +', ' ', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = re.sub(r'^\s+|\s+$', '', text, flags=re.MULTILINE)
    return text.strip()

def _normalize_punctuation(text: str) -> str:
    """Padroniza pontuação e remove espaços antes dela."""
    text = re.sub(r'\s+([!?,.:;])', r'\1', text)
    text = re.sub(r'([!?,.:;])\1+', r'\1', text)
    text = re.sub(r'[“”]', '"', text)
    text = re.sub(r'[‘’]', "'", text)
    text = re.sub(r'[–—]', '-', text)
    return text

def _expand_english_contractions(text: str) -> str:
    """Expande contrações comuns do inglês (ex: 'don't' -> 'do not')."""
    # Dicionário de contrações para expansão
    contractions = {
        "ain't": "am not", "aren't": "are not", "can't": "cannot",
        "couldn't": "could not", "didn't": "did not", "doesn't": "does not",
        "don't": "do not", "hadn't": "had not", "hasn't": "has not",
        "haven't": "have not", "he'd": "he would", "he'll": "he will",
        "he's": "he is", "I'd": "I would", "I'll": "I will", "I'm": "I am",
        "I've": "I have", "isn't": "is not", "it's": "it is", "let's": "let us",
        "mightn't": "might not", "mustn't": "must not", "shan't": "shall not",
        "she'd": "she would", "she'll": "she will", "she's": "she is",
        "shouldn't": "should not", "that's": "that is", "there's": "there is",
        "they'd": "they would", "they'll": "they will", "they're": "they are",
        "they've": "they have", "we'd": "we would", "we'll": "we will",
        "we're": "we are", "we've": "we have", "weren't": "were not",
        "what'll": "what will", "what're": "what are", "what's": "what is",
        "what've": "what have", "where's": "where is", "who'd": "who would",
        "who'll": "who will", "who're": "who are", "who's": "who is",
        "who've": "who have", "won't": "will not", "wouldn't": "would not",
        "you'd": "you would", "you'll": "you will", "you're": "you are",
        "you've": "you have"
    }
    def replace(match):
        return contractions[match.group(0).lower()]
    contraction_pattern = re.compile(r'\b(' + '|'.join(contractions.keys()) + r')\b', re.IGNORECASE)
    return contraction_pattern.sub(replace, text)

# --- Categoria 3: Remoção de Ruído Específico de Fala ---

def _remove_repeated_words(text: str) -> str:
    """Remove palavras repetidas consecutivamente (gagueira)."""
    return re.sub(r'\b(\w+)(?:\s+\1\b)+', r'\1', text, flags=re.IGNORECASE)

def _remove_short_lines(text: str) -> str:
    """Remove linhas inteiras que contêm de 1 a 3 palavras (ruído)."""
    return re.sub(r'^\s*(?:\b\w+\b[\s\W]*){1,3}$', '', text, flags=re.MULTILINE)

def _remove_empty_lines(text: str) -> str:
    """Remove linhas que ficaram vazias após as limpezas."""
    return "\n".join([line for line in text.split('\n') if line.strip()])


#==============================================================================
# == ORQUESTRADOR DA PIPELINE (Não precisa mexer aqui)
#==============================================================================

def _process_text_pipeline(text: str, cleaning_modules: List[Callable[[str], str]]) -> str:
    """Aplica uma sequência de funções de limpeza a um texto."""
    for module in cleaning_modules:
        text = module(text)
    return text


#==============================================================================
# == FUNÇÃO PRINCIPAL (A ÚNICA QUE VOCÊ PRECISA IMPORTAR E USAR)
#==============================================================================

def Clean_Text(text: str) -> str:
    """
    Executa uma pipeline de limpeza de texto de nível profissional, otimizada
    para transcrições de áudio (Português/Inglês).
    """
    if not text:
        return ""

    # --- A "Receita" de Limpeza Profissional ---
    # A ordem dos módulos é importante para o resultado final.
    professional_pipeline = [
        # 1. Limpeza Grosseira: remove blocos grandes de "lixo".
        _remove_html_tags,
        _decode_html_entities,
        _remove_timestamps_and_metadata,  # Essencial para transcrições
        _remove_urls_and_emails,

        # 2. Normalização: padroniza o texto para consistência.
        _expand_english_contractions,     # Essencial para áudios em inglês
        _normalize_punctuation,

        # 3. Limpeza Fina: lida com ruídos de fala e repetições.
        _remove_repeated_words,

        # 4. Limpeza de Formatação Final: remove linhas e espaços residuais.
        _remove_short_lines,
        _normalize_whitespace,
        _remove_empty_lines,
    ]

    return _process_text_pipeline(text, professional_pipeline)


#==============================================================================
# == FUNÇÃO ESSENCIAL PARA TRATAR SOBREPOSIÇÃO (OVERLAP)
#==============================================================================
# Lembre-se: esta função deve ser chamada DEPOIS de Clean_Text,
# comparando o chunk atual com o chunk anterior.

def remove_overlap(texto_anterior: str, texto_atual: str, min_overlap: int = 15) -> str:
    """
    Compara o final do `texto_anterior` com o começo do `texto_atual`
    e remove a porção sobreposta do `texto_atual`.
    """
    if not texto_anterior or not texto_atual:
        return texto_atual

    for i in range(len(texto_atual), min_overlap - 1, -1):
        prefixo_atual = texto_atual[:i]
        if texto_anterior.endswith(prefixo_atual):
            # Encontramos a maior sobreposição. Retorna o resto do texto atual.
            return texto_atual[i:]
    
    # Nenhuma sobreposição significativa encontrada.
    return texto_atual