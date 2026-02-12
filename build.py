import PyInstaller.__main__
import os
import customtkinter
from datetime import datetime

# Nome dinâmico com data e hora
timestamp = datetime.now().strftime("%Y%m%d_%H%M")
nome_executavel = f"MotoEstoque_Pro_{timestamp}"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ctk_path = os.path.dirname(customtkinter.__file__)

PyInstaller.__main__.run([
    os.path.join(BASE_DIR, 'main.py'),
    f'--name={nome_executavel}',
    '--onefile',
    '--windowed',
    f'--add-data={ctk_path}{os.pathsep}customtkinter',
    '--clean',
])

print(f"Build finalizado: {nome_executavel}.exe gerado na pasta dist.")