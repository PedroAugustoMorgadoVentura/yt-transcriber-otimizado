# run.py

import uvicorn
import asyncio
import os
import socket

def get_local_ip():
    """
    Obtém o endereço IP local da máquina.
    """
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # Conecta a um endereço IP arbitrário (não precisa ser alcançável)
        s.connect(('10.255.255.255', 1))
        IP = s.getsockname()[0]
    except Exception:
        IP = '127.0.0.1'
    finally:
        s.close()
    return IP

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
            host=get_local_ip(),
            port=8000,
            reload=False      # Ativa o hot-reload para desenvolvimento
        )
    

if __name__ == "__main__":
    main()