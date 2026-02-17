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
from textwrap import wrap

# --- CONFIGURAÇÃO DE DIRETÓRIOS ---
if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DB_PATH = os.path.join(BASE_DIR, "estoque_motos.db")
IMG_DIR = os.path.join(BASE_DIR, "imagens_estoque")
BACKUP_DIR = os.path.join(BASE_DIR, "backups")

# --- CLASSE DO SCANNER COM MOLDURA ---
class ScannerCamera:
    def __init__(self, titulo="Scanner de Código"):
        self.cap = cv2.VideoCapture(0)
        self.valor_lido = None
        self.titulo = titulo

    def ler(self):
        if not self.cap.isOpened():
            messagebox.showerror("Erro", "Câmera não detectada.")
            return None

        while True:
            ret, frame = self.cap.read()
            if not ret: break

            h, w, _ = frame.shape
            # Define moldura centralizada
            box_w, box_h = 320, 200
            x1, y1 = int((w - box_w) / 2), int((h - box_h) / 2)
            x2, y2 = x1 + box_w, y1 + box_h

            # Desenha guia visual
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
            cv2.putText(frame, "POSICIONE O CODIGO AQUI", (x1, y1 - 15), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

            codigos = pyzbar.decode(frame)
            for obj in codigos:
                cx, cy, cw, ch = obj.rect
                # Validação de proximidade da moldura
                if x1 - 40 < cx < x2 + 40 and y1 - 40 < cy < y2 + 40:
                    self.valor_lido = obj.data.decode('utf-8')
                    cv2.rectangle(frame, (cx, cy), (cx + cw, cy + ch), (255, 0, 0), 3)

            cv2.imshow(self.titulo + " (ESC para Sair)", frame)
            if self.valor_lido or cv2.waitKey(1) == 27: break
        
        self.cap.release()
        cv2.destroyAllWindows()
        return self.valor_lido

# --- LÓGICA DE INICIALIZAÇÃO ---
def inicializar_sistema():
    for pasta in [IMG_DIR, BACKUP_DIR]:
        if not os.path.exists(pasta): os.makedirs(pasta)
    
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""CREATE TABLE IF NOT EXISTS pecas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        codigo_sku TEXT, descricao TEXT, marca TEXT,
        compatibilidade TEXT, quantidade INTEGER, caminho_imagem TEXT)""")
    conn.commit()
    conn.close()

# --- APP PRINCIPAL ---
class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("MotoEstoque Pro v5.0")
        self.geometry("1200x800")
        inicializar_sistema()
        self.caminho_foto_temp = ""
        self.protocol("WM_DELETE_WINDOW", self.ao_fechar)
        self.tela_login()

    def ao_fechar(self):
        if os.path.exists(DB_PATH):
            ts = datetime.now().strftime("%Y%m%d_%H%M")
            shutil.copy2(DB_PATH, os.path.join(BACKUP_DIR, f"backup_{ts}.db"))
        self.destroy()

    def tela_login(self):
        self.frame_login = ctk.CTkFrame(self)
        self.frame_login.pack(pady=100, padx=60, fill="both", expand=True)
        ctk.CTkLabel(self.frame_login, text="SISTEMA DE ESTOQUE", font=("Roboto", 28, "bold")).pack(pady=20)
        self.user = ctk.CTkEntry(self.frame_login, placeholder_text="Usuário", width=300)
        self.user.pack(pady=10)
        self.password = ctk.CTkEntry(self.frame_login, placeholder_text="Senha", show="*", width=300)
        self.password.pack(pady=10)
        ctk.CTkButton(self.frame_login, text="Acessar", width=300, command=self.autenticar).pack(pady=20)

    def autenticar(self):
        if self.user.get() == "admin" and self.password.get() == "123":
            self.frame_login.destroy()
            self.tela_principal()
        else: messagebox.showerror("Erro", "Login Inválido")

    def tela_principal(self):
        # Menu Lateral
        self.menu_lateral = ctk.CTkFrame(self, width=220, corner_radius=0)
        self.menu_lateral.pack(side="left", fill="y")
        
        ctk.CTkButton(self.menu_lateral, text="+ Nova Peça", command=self.abrir_cadastro).pack(pady=10, padx=20)
        ctk.CTkButton(self.menu_lateral, text="📷 Scan Busca", fg_color="#8e44ad", command=self.buscar_scanner).pack(pady=10, padx=20)
        ctk.CTkButton(self.menu_lateral, text="📝 Editar", fg_color="#2980b9", command=self.abrir_edicao).pack(pady=10, padx=20)
        ctk.CTkButton(self.menu_lateral, text="🗑️ Excluir", fg_color="#c0392b", command=self.deletar_peca).pack(pady=10, padx=20)
        ctk.CTkButton(self.menu_lateral, text="📄 Relatório PDF", fg_color="#D35400", command=self.gerar_pdf).pack(pady=10, padx=20)

        # Container Central
        self.container = ctk.CTkFrame(self)
        self.container.pack(side="right", fill="both", expand=True, padx=10, pady=10)

        self.entry_busca = ctk.CTkEntry(self.container, placeholder_text="🔍 Pesquisar SKU, Nome, Marca...", height=40)
        self.entry_busca.pack(fill="x", padx=15, pady=15)
        self.entry_busca.bind("<KeyRelease>", lambda e: self.atualizar_tabela())

        self.frame_tabela = ctk.CTkFrame(self.container)
        self.frame_tabela.pack(side="left", fill="both", expand=True, padx=5, pady=5)
        
        self.canvas_foto = ctk.CTkLabel(self.container, text="Selecione um item", fg_color="black", width=260, height=260, corner_radius=10)
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

    def atualizar_tabela(self):
        for i in self.tree.get_children(): self.tree.delete(i)
        termo = f"%{self.entry_busca.get()}%"
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT id, codigo_sku, descricao, marca, compatibilidade, quantidade FROM pecas WHERE codigo_sku LIKE ? OR descricao LIKE ? OR marca LIKE ?", (termo, termo, termo))
        for r in cursor.fetchall(): self.tree.insert("", "end", values=r)
        conn.close()

    def buscar_scanner(self):
        res = ScannerCamera("Busca Inteligente").ler()
        if res:
            self.entry_busca.delete(0, 'end')
            self.entry_busca.insert(0, res)
            self.atualizar_tabela()

    def carregar_foto(self, event):
        item = self.tree.selection()
        if not item: return
        conn = sqlite3.connect(DB_PATH)
        res = conn.execute("SELECT caminho_imagem FROM pecas WHERE id=?", (self.tree.item(item)['values'][0],)).fetchone()
        conn.close()
        if res and res[0] and os.path.exists(os.path.join(BASE_DIR, res[0])):
            img = Image.open(os.path.join(BASE_DIR, res[0])).resize((250, 250))
            tk_img = ImageTk.PhotoImage(img)
            self.canvas_foto.configure(image=tk_img, text="")
            self.canvas_foto.image = tk_img
        else: self.canvas_foto.configure(image="", text="Sem Foto")

    def abrir_cadastro(self): self.janela_form("Novo Registro", "create")

    def abrir_edicao(self):
        item = self.tree.selection()
        if not item: return
        self.janela_form("Editar Registro", "edit", self.tree.item(item)['values'])

    def janela_form(self, titulo, modo, valores=None):
        janela = ctk.CTkToplevel(self)
        janela.title(titulo)
        janela.geometry("480x750")
        janela.attributes('-topmost', True)
        self.caminho_foto_temp = ""

        campos = ["SKU", "Descrição", "Marca", "Compatibilidade", "Quantidade"]
        entries = {}
        for i, c in enumerate(campos):
            ctk.CTkLabel(janela, text=c, font=("Arial", 12, "bold")).pack(pady=(5,0))
            en = ctk.CTkEntry(janela, width=350)
            if modo == "edit": en.insert(0, valores[i+1])
            en.pack(pady=5)
            entries[c] = en

        def scan_campo():
            res = ScannerCamera("Escaneando SKU").ler()
            if res:
                entries["SKU"].delete(0, 'end')
                entries["SKU"].insert(0, res)

        ctk.CTkButton(janela, text="📷 Escanear SKU", fg_color="#27ae60", command=scan_campo).pack(pady=5)

        def salvar():
            sku = entries["SKU"].get().upper()
            caminho_final = ""
            if modo == "edit":
                conn_t = sqlite3.connect(DB_PATH)
                caminho_final = conn_t.execute("SELECT caminho_imagem FROM pecas WHERE id=?", (valores[0],)).fetchone()[0]
                conn_t.close()

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
            janela.destroy()
            self.atualizar_tabela()

        ctk.CTkButton(janela, text="Selecionar Foto", command=lambda: [setattr(self, 'caminho_foto_temp', filedialog.askopenfilename())]).pack(pady=10)
        ctk.CTkButton(janela, text="SALVAR", height=45, fg_color="#1f538d", command=salvar).pack(pady=20)

    def deletar_peca(self):
        item = self.tree.selection()
        if not item: return
        if messagebox.askyesno("Confirmar", "Deseja excluir permanentemente?"):
            conn = sqlite3.connect(DB_PATH)
            conn.execute("DELETE FROM pecas WHERE id=?", (self.tree.item(item)['values'][0],))
            conn.commit()
            conn.close()
            self.atualizar_tabela()

    def gerar_pdf(self):
        f = filedialog.asksaveasfilename(defaultextension=".pdf", filetypes=[("PDF", "*.pdf")])
        if not f: return
        
        pdf = canvas.Canvas(f, pagesize=A4)
        y = 780
        
        # Cabeçalho do PDF
        pdf.setFont("Helvetica-Bold", 16)
        pdf.drawString(50, 810, "INVENTÁRIO GERAL DE ESTOQUE")
        pdf.setFont("Helvetica", 10)
        pdf.drawString(50, 795, f"Data de Emissão: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
        pdf.line(50, 790, 550, 790)
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT codigo_sku, descricao, marca, compatibilidade, quantidade FROM pecas")
        
        for r in cursor.fetchall():
            if y < 100:
                pdf.showPage()
                y = 800
            
            # Linha Principal (SKU e Qtd)
            pdf.setFont("Helvetica-Bold", 11)
            pdf.drawString(50, y, f"SKU: {r[0]} | Marca: {r[2]} | Qtd: {r[4]}")
            y -= 15
            
            # Descrição e Compatibilidade com Quebra de Linha
            pdf.setFont("Helvetica", 9)
            text_info = f"Descrição: {r[1]} | Compatibilidade: {r[3]}"
            
            # Quebra o texto em linhas de no máximo 95 caracteres
            linhas = wrap(text_info, width=95)
            
            text_obj = pdf.beginText(50, y)
            for linha in linhas:
                text_obj.textLine(linha)
                y -= 12
            
            pdf.drawText(text_obj)
            y -= 10
            pdf.setStrokeColorRGB(0.8, 0.8, 0.8)
            pdf.line(50, y, 550, y)
            y -= 25
            
        pdf.save()
        conn.close()
        messagebox.showinfo("Sucesso", "PDF Gerado!")

if __name__ == "__main__":
    app = App()
    app.mainloop()