# 🏍️ MotoEstoque Pro v5.0

Sistema profissional para gestão de estoque de moto peças com suporte a **leitura de código de barras/QR Code via câmera**, visualização de fotos e exportação de relatórios em PDF.



## 🚀 Funcionalidades

* **Scanner Integrado:** Cadastro e busca de produtos via webcam com guia de centralização.
* **Gestão de Fotos:** Armazenamento local de imagens vinculado ao SKU.
* **Relatórios em PDF:** Exportação detalhada com quebra de linha automática para descrições longas.
* **Segurança de Dados:** Backup automático do banco de dados SQLite a cada fechamento.
* **Interface Moderna:** Desenvolvido com CustomTkinter com suporte a temas.

---

## 📋 Pré-requisitos

Antes de iniciar, você precisará ter instalado:

1.  **Python 3.9 ou superior.**
2.  **Visual C++ Redistributable (x64):** Essencial para o funcionamento do leitor de códigos (`pyzbar`).
    * [Download Oficial Microsoft](https://aka.ms/vs/17/release/vc_redist.x64.exe)

---

## 🛠️ Instalação e Configuração

### 1. Clonar o repositório
```bash
git clone https://github.com/eder1985/stock_python_app.git

cd stock_python_app
