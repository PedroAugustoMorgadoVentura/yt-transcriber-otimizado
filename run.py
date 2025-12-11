import webbrowser
import uvicorn
import asyncio
import os
import socket
import torch
import tkinter as tk
from app.main import app 
import sys

BASE_DIR = os.path.dirname(os.path.abspath(sys.argv[0]))
FFMPEEG_PATH = os.path.join(BASE_DIR, "ffmpeg")


if os.path.isdir(FFMPEEG_PATH):
    os.environ["PATH"] += os.pathsep + FFMPEEG_PATH

else:
    print("AVISO: Pasta /ffmpeg não encontrada (ffmpeg não disponível localmente)")

def test_cuda_availability():
    if not torch.cuda.is_available():
        root = tk.Tk()
        root.title("Aviso de CUDA")

        # Garante que a janela fique na frente das outras (IDE/Terminal)
        root.attributes('-topmost', True)

        # --- Lógica de Centralização ---
        largura_janela = 450
        altura_janela = 180

        largura_tela = root.winfo_screenwidth()
        altura_tela = root.winfo_screenheight()

        # Cálculo do centro
        pos_x = (largura_tela // 2) - (largura_janela // 2)
        pos_y = (altura_tela // 2) - (altura_janela // 2)

        root.geometry(f"{largura_janela}x{altura_janela}+{pos_x}+{pos_y}")
        # -------------------------------

        def abrir_site_nvidia():
            # Abre o site oficial
            webbrowser.open("https://developer.nvidia.com/cuda-downloads")

        def fechar_e_continuar():
            print("Botão continuar clicado. Fechando janela...")
            root.destroy()

        # 1. O TEXTO (LABEL) VEM PRIMEIRO
        label = tk.Label(
            root, 
            text="Para melhor eficiência, é necessário possuir os drivers CUDA instalados.",
            font=("Arial", 10),
            wraplength=400, 
            justify="center"
        )
        label.pack(pady=(25, 15))

        # 2. OS BOTÕES VÊM DEPOIS (dentro de um Frame para ficarem lado a lado)
        frame_botoes = tk.Frame(root)
        frame_botoes.pack()

        # Botão com cor verde (estilo Nvidia)
        btn_download = tk.Button(
            frame_botoes, 
            text="Baixar Drivers CUDA", 
            command=abrir_site_nvidia, 
            bg="#76b900",
            fg="white",
            width=20,
            padx=5,
            pady=5
        )
        btn_download.pack(side="left", padx=10)

        # Botão padrão para continuar
        btn_continuar = tk.Button(
            frame_botoes, 
            text="Continuar sem CUDA", 
            command=fechar_e_continuar,
            width=20,
            padx=5,
            pady=5
        )
        btn_download.pack(side="left", padx=10)
        btn_continuar.pack(side="left", padx=10)
        root.mainloop()
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
    test_cuda_availability()
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
    "O webbrowser direciona o usuario ao site do projeto"
    webbrowser.open(f"http://{get_local_ip()}:8000")
    uvicorn.run(
            app,  # O caminho para o seu objeto FastAPI ('pasta.arquivo:objeto')
            host=get_local_ip(),
            port=8000,
            reload=False      # Ativa o hot-reload para desenvolvimento
        )


if __name__ == "__main__":
    main()
