import PyInstaller.__main__
import os
import customtkinter
from datetime import datetime

# Configuração de caminhos
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ctk_path = os.path.dirname(customtkinter.__file__)

# Nome do executável com timestamp
timestamp = datetime.now().strftime("%Y%m%d_%H%M")
nome_executavel = f"stock_python_app_{timestamp}"

PyInstaller.__main__.run([
    os.path.join(BASE_DIR, 'main.py'),        # Arquivo principal
    f'--name={nome_executavel}',              # Nome do arquivo final
    '--onefile',                              # Gerar apenas um arquivo .exe
    '--windowed',                             # Não abrir janela de console (CMD)
    '--clean',                                # Limpar cache antes do build
    
    # Adicionando CustomTkinter
    f'--add-data={ctk_path}{os.pathsep}customtkinter',
    
    # SOLUÇÃO PARA O PYZBAR: Coleta todas as DLLs e dependências ocultas
    '--collect-all', 'pyzbar',
    
    # Opcional: Adicione um ícone se tiver um arquivo .ico na pasta
    # f'--icon={os.path.join(BASE_DIR, "icone.ico")}', 
])

print(f"\n--- Build Finalizado! ---")
print(f"O arquivo {nome_executavel}.exe está na pasta 'dist'.")