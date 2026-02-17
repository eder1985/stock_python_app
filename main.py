import customtkinter as ctk
from tkinter import filedialog, messagebox, ttk
import sqlite3
import cv2
from pyzbar import pyzbar
from PIL import Image, ImageTk
import os
import shutil
import sys
from datetime import datetime
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4

# --- CONFIGURAÇÃO DE DIRETÓRIOS ---
if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DB_PATH = os.path.join(BASE_DIR, "estoque_motos.db")
IMG_DIR = os.path.join(BASE_DIR, "imagens_estoque")
BACKUP_DIR = os.path.join(BASE_DIR, "backups")

# --- LÓGICA DO SCANNER ---
class ScannerCamera:
    """Abre a câmera e retorna o valor do código lido."""
    def __init__(self, titulo="Scanner"):
        self.cap = cv2.VideoCapture(0)
        self.valor_lido = None
        self.titulo = titulo

    def ler(self):
        while True:
            ret, frame = self.cap.read()
            if not ret: break

            # Detectar códigos
            codigos = pyzbar.decode(frame)
            for obj in codigos:
                self.valor_lido = obj.data.decode('utf-8')
                # Desenha um retângulo no código detectado
                (x, y, w, h) = obj.rect
                cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
                cv2.putText(frame, self.valor_lido, (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

            cv2.imshow(self.titulo + " (Pressione ESC para sair)", frame)
            
            # Se leu ou apertou ESC (27), fecha
            if self.valor_lido or cv2.waitKey(1) == 27:
                break
        
        self.cap.release()
        cv2.destroyAllWindows()
        return self.valor_lido

# --- APLICAÇÃO PRINCIPAL ---
def inicializar_sistema():
    for pasta in [IMG_DIR, BACKUP_DIR]:
        if not os.path.exists(pasta): os.makedirs(pasta)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""CREATE TABLE IF NOT EXISTS pecas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        codigo_sku TEXT, descricao TEXT, marca TEXT,
        compatibilidade TEXT, quantidade INTEGER, caminho_imagem TEXT)""")
    conn.close()

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("MotoEstoque Pro v4.0 - Scanner Integrado")
        self.geometry("1250x800")
        inicializar_sistema()
        self.protocol("WM_DELETE_WINDOW", self.ao_fechar)
        self.tela_login()

    def ao_fechar(self):
        # Backup automático simplificado
        if os.path.exists(DB_PATH):
            shutil.copy2(DB_PATH, os.path.join(BACKUP_DIR, f"bkp_{datetime.now().strftime('%Y%m%d')}.db"))
        self.destroy()

    def tela_login(self):
        self.frame_login = ctk.CTkFrame(self)
        self.frame_login.pack(pady=100, padx=60, fill="both", expand=True)
        ctk.CTkLabel(self.frame_login, text="Login MotoEstoque", font=("Roboto", 24)).pack(pady=20)
        self.user = ctk.CTkEntry(self.frame_login, placeholder_text="Usuário", width=300)
        self.user.pack(pady=10)
        self.password = ctk.CTkEntry(self.frame_login, placeholder_text="Senha", show="*", width=300)
        self.password.pack(pady=10)
        ctk.CTkButton(self.frame_login, text="Entrar", width=300, command=lambda: [self.frame_login.destroy(), self.tela_principal()]).pack(pady=20)

    def tela_principal(self):
        # Menu Lateral
        self.menu_lateral = ctk.CTkFrame(self, width=220, corner_radius=0)
        self.menu_lateral.pack(side="left", fill="y")
        
        ctk.CTkButton(self.menu_lateral, text="+ Nova Peça", command=self.abrir_cadastro).pack(pady=10, padx=20)
        # BOTÃO SCANNER PARA BUSCA
        ctk.CTkButton(self.menu_lateral, text="🔍 Ler Código (Busca)", fg_color="#8e44ad", command=self.buscar_via_scanner).pack(pady=10, padx=20)
        ctk.CTkButton(self.menu_lateral, text="📝 Editar", fg_color="#2980b9", command=self.abrir_edicao).pack(pady=10, padx=20)
        ctk.CTkButton(self.menu_lateral, text="🗑️ Excluir", fg_color="#c0392b", command=self.deletar_peca).pack(pady=10, padx=20)

        # Conteúdo Central
        self.container = ctk.CTkFrame(self)
        self.container.pack(side="right", fill="both", expand=True, padx=10, pady=10)

        self.entry_busca = ctk.CTkEntry(self.container, placeholder_text="Buscar por SKU, Descrição ou Marca...", height=40)
        self.entry_busca.pack(fill="x", padx=15, pady=15)
        self.entry_busca.bind("<KeyRelease>", lambda e: self.atualizar_tabela())

        self.frame_tabela = ctk.CTkFrame(self.container)
        self.frame_tabela.pack(side="left", fill="both", expand=True, padx=5, pady=5)
        
        self.canvas_foto = ctk.CTkLabel(self.container, text="Selecione um item", fg_color="black", width=280, height=280)
        self.canvas_foto.pack(side="right", padx=15)

        self.configurar_tabela()
        self.atualizar_tabela()

    def configurar_tabela(self):
        colunas = ("ID", "SKU", "Descrição", "Marca", "Compatibilidade", "Qtd")
        self.tree = ttk.Treeview(self.frame_tabela, columns=colunas, show="headings")
        for col in colunas:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=100, anchor="center")
        self.tree.pack(fill="both", expand=True)
        self.tree.bind("<<TreeviewSelect>>", self.carregar_foto)

    # --- FUNCIONALIDADES DO SCANNER ---
    def buscar_via_scanner(self):
        scanner = ScannerCamera(titulo="Buscando Produto")
        codigo = scanner.ler()
        if codigo:
            self.entry_busca.delete(0, 'end')
            self.entry_busca.insert(0, codigo)
            self.atualizar_tabela()

    def abrir_cadastro(self):
        self.janela_form("Novo Cadastro", "create")

    def abrir_edicao(self):
        item = self.tree.selection()
        if not item: return
        self.janela_form("Editar Peça", "edit", self.tree.item(item)['values'])

    def janela_form(self, titulo, modo, valores=None):
        janela = ctk.CTkToplevel(self)
        janela.title(titulo)
        janela.geometry("450x700")
        janela.attributes('-topmost', True)

        entries = {}
        for c in ["SKU", "Descrição", "Marca", "Compatibilidade", "Quantidade"]:
            ctk.CTkLabel(janela, text=c).pack(pady=(5,0))
            en = ctk.CTkEntry(janela, width=320)
            if modo == "edit": en.insert(0, valores[1 if c=="SKU" else 2]) # Ajuste simplificado de índices
            # Preenchimento manual para os outros campos... (omitido para brevidade, use a lógica do main.py anterior)
            en.pack(pady=5)
            entries[c] = en
        
        # Inserção correta para edição (ajuste dos índices conforme a tabela)
        if modo == "edit":
            entries["SKU"].delete(0, 'end'); entries["SKU"].insert(0, valores[1])
            entries["Descrição"].delete(0, 'end'); entries["Descrição"].insert(0, valores[2])
            entries["Marca"].delete(0, 'end'); entries["Marca"].insert(0, valores[3])
            entries["Compatibilidade"].delete(0, 'end'); entries["Compatibilidade"].insert(0, valores[4])
            entries["Quantidade"].delete(0, 'end'); entries["Quantidade"].insert(0, valores[5])

        # BOTÃO SCANNER PARA SKU
        def scan_sku():
            scanner = ScannerCamera(titulo="Lendo Código para SKU")
            res = scanner.ler()
            if res:
                entries["SKU"].delete(0, 'end')
                entries["SKU"].insert(0, res)

        ctk.CTkButton(janela, text="📷 Escanear SKU", fg_color="#27ae60", command=scan_sku).pack(pady=5)

        def salvar():
            # ... (Mantenha a lógica de salvar/shutil do código anterior) ...
            sku = entries["SKU"].get().upper()
            conn = sqlite3.connect(DB_PATH)
            if modo == "create":
                conn.execute("INSERT INTO pecas (codigo_sku, descricao, marca, compatibilidade, quantidade) VALUES (?,?,?,?,?)",
                             (sku, entries["Descrição"].get(), entries["Marca"].get(), entries["Compatibilidade"].get(), entries["Quantidade"].get()))
            else:
                conn.execute("UPDATE pecas SET codigo_sku=?, descricao=?, marca=?, compatibilidade=?, quantidade=? WHERE id=?",
                             (sku, entries["Descrição"].get(), entries["Marca"].get(), entries["Compatibilidade"].get(), entries["Quantidade"].get(), valores[0]))
            conn.commit()
            conn.close()
            janela.destroy()
            self.atualizar_tabela()

        ctk.CTkButton(janela, text="Salvar", command=salvar).pack(pady=20)

    # --- MÉTODOS AUXILIARES ---
    def atualizar_tabela(self):
        for i in self.tree.get_children(): self.tree.delete(i)
        termo = f"%{self.entry_busca.get()}%"
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT id, codigo_sku, descricao, marca, compatibilidade, quantidade FROM pecas WHERE codigo_sku LIKE ? OR descricao LIKE ? OR marca LIKE ?", (termo, termo, termo))
        for r in cursor.fetchall(): self.tree.insert("", "end", values=r)
        conn.close()

    def carregar_foto(self, event):
        # ... (Mesma lógica de carregar foto do código anterior) ...
        pass

    def deletar_peca(self):
        item = self.tree.selection()
        if not item: return
        if messagebox.askyesno("Excluir", "Deseja apagar este item?"):
            conn = sqlite3.connect(DB_PATH)
            conn.execute("DELETE FROM pecas WHERE id=?", (self.tree.item(item)['values'][0],))
            conn.commit()
            conn.close()
            self.atualizar_tabela()

if __name__ == "__main__":
    app = App()
    app.mainloop()