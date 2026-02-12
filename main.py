import customtkinter as ctk
from tkinter import filedialog, messagebox, ttk
import sqlite3
from PIL import Image, ImageTk
import os
import shutil
import sys
from datetime import datetime
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4

# --- LÓGICA DE DIRETÓRIOS PARA DISTRIBUIÇÃO ---
if getattr(sys, 'frozen', False):
    # Se rodando como executável (.exe)
    BASE_DIR = os.path.dirname(sys.executable)
else:
    # Se rodando como script (.py)
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DB_PATH = os.path.join(BASE_DIR, "estoque_motos.db")
IMG_DIR = os.path.join(BASE_DIR, "imagens_estoque")
BACKUP_DIR = os.path.join(BASE_DIR, "backups")

def inicializar_sistema():
    """Cria pastas necessárias e o banco de dados fora do executável."""
    for pasta in [IMG_DIR, BACKUP_DIR]:
        if not os.path.exists(pasta):
            os.makedirs(pasta)
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS pecas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            codigo_sku TEXT, descricao TEXT, marca TEXT,
            compatibilidade TEXT, quantidade INTEGER, caminho_imagem TEXT
        )
    """)
    conn.commit()
    conn.close()

def realizar_backup():
    """Cria uma cópia de segurança do banco ao fechar o sistema."""
    try:
        if os.path.exists(DB_PATH):
            data_str = datetime.now().strftime("%Y%m%d_%H%M%S")
            nome_bkp = f"backup_estoque_{data_str}.db"
            shutil.copy2(DB_PATH, os.path.join(BACKUP_DIR, nome_bkp))
            
            # Limpeza: Mantém apenas os últimos 5 backups
            lista_bkp = sorted([os.path.join(BACKUP_DIR, f) for f in os.listdir(BACKUP_DIR)])
            while len(lista_bkp) > 5:
                os.remove(lista_bkp.pop(0))
    except Exception as e:
        print(f"Erro ao gerar backup: {e}")

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("MotoEstoque Pro v3.0")
        self.geometry("1200x750")
        
        inicializar_sistema()
        self.caminho_foto_temp = ""
        
        # Define o que fazer ao fechar a janela (X)
        self.protocol("WM_DELETE_WINDOW", self.ao_fechar)
        self.tela_login()

    def ao_fechar(self):
        realizar_backup()
        self.destroy()

    def tela_login(self):
        self.frame_login = ctk.CTkFrame(self)
        self.frame_login.pack(pady=100, padx=60, fill="both", expand=True)
        ctk.CTkLabel(self.frame_login, text="Acesso Administrativo", font=("Roboto", 28, "bold")).pack(pady=20)
        self.user = ctk.CTkEntry(self.frame_login, placeholder_text="Usuário", width=300)
        self.user.pack(pady=10)
        self.password = ctk.CTkEntry(self.frame_login, placeholder_text="Senha", show="*", width=300)
        self.password.pack(pady=10)
        ctk.CTkButton(self.frame_login, text="Entrar", width=300, command=self.autenticar).pack(pady=20)

    def autenticar(self):
        if self.user.get() == "admin" and self.password.get() == "123":
            self.frame_login.destroy()
            self.tela_principal()
        else:
            messagebox.showerror("Erro", "Login Inválido!")

    def tela_principal(self):
        # Menu Lateral
        self.menu_lateral = ctk.CTkFrame(self, width=220, corner_radius=0)
        self.menu_lateral.pack(side="left", fill="y")
        
        ctk.CTkButton(self.menu_lateral, text="+ Nova Peça", command=self.abrir_cadastro).pack(pady=10, padx=20)
        ctk.CTkButton(self.menu_lateral, text="📝 Editar", fg_color="#2980b9", command=self.abrir_edicao).pack(pady=10, padx=20)
        ctk.CTkButton(self.menu_lateral, text="🗑️ Excluir", fg_color="#c0392b", command=self.deletar_peca).pack(pady=10, padx=20)
        ctk.CTkButton(self.menu_lateral, text="📄 Relatório PDF", fg_color="#D35400", command=self.gerar_pdf).pack(pady=10, padx=20)

        # Área de Dados
        self.container = ctk.CTkFrame(self)
        self.container.pack(side="right", fill="both", expand=True, padx=10, pady=10)

        # Busca em Tempo Real
        self.entry_busca = ctk.CTkEntry(self.container, placeholder_text="🔍 Buscar por descrição, marca ou compatibilidade...", height=40)
        self.entry_busca.pack(fill="x", padx=15, pady=15)
        self.entry_busca.bind("<KeyRelease>", lambda e: self.atualizar_tabela())

        self.frame_tabela = ctk.CTkFrame(self.container)
        self.frame_tabela.pack(side="left", fill="both", expand=True, padx=5, pady=5)
        
        # Painel de Visualização de Foto
        self.frame_vizi = ctk.CTkFrame(self.container, width=300)
        self.frame_vizi.pack(side="right", fill="y", padx=5, pady=5)
        self.canvas_foto = ctk.CTkLabel(self.frame_vizi, text="Selecione um item", fg_color="black", width=250, height=250, corner_radius=10)
        self.canvas_foto.pack(pady=30, padx=15)

        self.configurar_tabela()
        self.atualizar_tabela()

    def configurar_tabela(self):
        colunas = ("ID", "SKU", "Descrição", "Marca", "Compatibilidade", "Qtd")
        self.tree = ttk.Treeview(self.frame_tabela, columns=colunas, show="headings")
        for col in colunas:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=100, anchor="center")
        self.tree.pack(fill="both", expand=True)
        self.tree.bind("<<TreeviewSelect>>", self.carregar_foto_vizi)

    def atualizar_tabela(self):
        for i in self.tree.get_children(): self.tree.delete(i)
        termo = f"%{self.entry_busca.get()}%"
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT id, codigo_sku, descricao, marca, compatibilidade, quantidade FROM pecas WHERE descricao LIKE ? OR marca LIKE ? OR compatibilidade LIKE ?", (termo, termo, termo))
        for r in cursor.fetchall():
            self.tree.insert("", "end", values=r)
        conn.close()

    def carregar_foto_vizi(self, event):
        item = self.tree.selection()
        if not item: return
        conn = sqlite3.connect(DB_PATH)
        res = conn.execute("SELECT caminho_imagem FROM pecas WHERE id=?", (self.tree.item(item)['values'][0],)).fetchone()
        conn.close()
        if res and res[0]:
            full_p = os.path.join(BASE_DIR, res[0])
            if os.path.exists(full_p):
                img = Image.open(full_p).resize((240, 240), Image.LANCZOS)
                tk_img = ImageTk.PhotoImage(img)
                self.canvas_foto.configure(image=tk_img, text="")
                self.canvas_foto.image = tk_img
                return
        self.canvas_foto.configure(image="", text="Sem Foto")

    def abrir_cadastro(self):
        self.janela_form("Cadastrar Novo Item", "create")

    def abrir_edicao(self):
        item = self.tree.selection()
        if not item: return
        self.janela_form("Editar Item", "edit", self.tree.item(item)['values'])

    def janela_form(self, titulo, modo, valores=None):
        janela = ctk.CTkToplevel(self)
        janela.title(titulo)
        janela.geometry("450x650")
        janela.attributes('-topmost', True)
        self.caminho_foto_temp = ""

        campos = ["SKU", "Descrição", "Marca", "Compatibilidade", "Quantidade"]
        entries = {}
        for i, c in enumerate(campos):
            ctk.CTkLabel(janela, text=c, font=("Arial", 12, "bold")).pack(pady=(10,0))
            en = ctk.CTkEntry(janela, width=320)
            if modo == "edit": en.insert(0, valores[i+1])
            en.pack(pady=5)
            entries[c] = en

        lbl_foto = ctk.CTkLabel(janela, text="Foto atual mantida" if modo == "edit" else "Nenhuma foto selecionada", font=("Arial", 10))

        def selecionar():
            p = filedialog.askopenfilename()
            if p:
                self.caminho_foto_temp = p
                lbl_foto.configure(text=f"Nova foto: {os.path.basename(p)}", text_color="green")

        def salvar():
            sku = entries["SKU"].get().upper()
            caminho_final = ""
            if modo == "edit":
                conn_tmp = sqlite3.connect(DB_PATH)
                caminho_final = conn_tmp.execute("SELECT caminho_imagem FROM pecas WHERE id=?", (valores[0],)).fetchone()[0]
                conn_tmp.close()

            if self.caminho_foto_temp:
                ext = os.path.splitext(self.caminho_foto_temp)[1]
                caminho_final = os.path.join("imagens_estoque", f"{sku}{ext}")
                shutil.copy(self.caminho_foto_temp, os.path.join(BASE_DIR, caminho_final))

            conn = sqlite3.connect(DB_PATH)
            if modo == "create":
                conn.execute("INSERT INTO pecas (codigo_sku, descricao, marca, compatibilidade, quantidade, caminho_imagem) VALUES (?,?,?,?,?,?)",
                             (sku, entries["Descrição"].get(), entries["Marca"].get(), entries["Compatibilidade"].get(), entries["Quantidade"].get(), caminho_final))
            else:
                conn.execute("UPDATE pecas SET codigo_sku=?, descricao=?, marca=?, compatibilidade=?, quantidade=?, caminho_imagem=? WHERE id=?",
                             (sku, entries["Descrição"].get(), entries["Marca"].get(), entries["Compatibilidade"].get(), entries["Quantidade"].get(), caminho_final, valores[0]))
            conn.commit()
            conn.close()
            messagebox.showinfo("Sucesso", "Dados salvos!", parent=janela)
            janela.destroy()
            self.atualizar_tabela()

        ctk.CTkButton(janela, text="Escolher Foto", fg_color="#16a085", command=selecionar).pack(pady=15)
        lbl_foto.pack()
        ctk.CTkButton(janela, text="SALVAR DADOS", height=45, command=salvar).pack(pady=30)

    def deletar_peca(self):
        item = self.tree.selection()
        if not item: return
        if messagebox.askyesno("Confirmar", "Deseja excluir este item permanentemente?"):
            conn = sqlite3.connect(DB_PATH)
            conn.execute("DELETE FROM pecas WHERE id=?", (self.tree.item(item)['values'][0],))
            conn.commit()
            conn.close()
            self.atualizar_tabela()

    def gerar_pdf(self):
        f = filedialog.asksaveasfilename(defaultextension=".pdf", filetypes=[("PDF", "*.pdf")])
        if not f: return
        pdf = canvas.Canvas(f, pagesize=A4)
        pdf.drawString(50, 800, "RELATÓRIO DE ESTOQUE - MOTO PEÇAS")
        pdf.line(50, 795, 550, 795)
        y = 770
        conn = sqlite3.connect(DB_PATH)
        for r in conn.execute("SELECT codigo_sku, descricao, quantidade FROM pecas").fetchall():
            pdf.drawString(50, y, f"SKU: {r[0]} | Desc: {r[1]} | Qtd: {r[2]}")
            y -= 20
        pdf.save()
        conn.close()
        messagebox.showinfo("Sucesso", "Relatório PDF gerado!")

if __name__ == "__main__":
    app = App()
    app.mainloop()