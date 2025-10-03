# run.py

import uvicorn
import asyncio
import os

def main():
    """
    Script de inicialização customizado para garantir que a política de
    eventos do asyncio seja configurada antes do Uvicorn iniciar.
    """
    # 1. APLICA A CORREÇÃO DO WINDOWS AQUI
    # Este código é executado em um contexto Python normal, ANTES de o Uvicorn
    # ser iniciado, garantindo que a política seja aplicada sem erros.
    if os.name == 'nt':
        print(">>> Aplicando a política ProactorEventLoop para Windows <<<")
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

    # 2. INICIA O SERVIDOR UVICORN PROGRAMATICAMENTE
    # O uvicorn.run() irá agora usar o loop com a política que acabamos de definir.
    uvicorn.run(
        "app.main:app",  # O caminho para o seu objeto FastAPI ('pasta.arquivo:objeto')
        host="0.0.0.0",
        port=8000,
        reload=True      # Ativa o hot-reload para desenvolvimento
    )

if __name__ == "__main__":
    main()