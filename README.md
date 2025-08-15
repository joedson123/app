# Controle de Compras, Vendas e Lucro (Streamlit)

App web em **Python + Streamlit** com **SQLite** para registrar **compras**, **vendas** e calcular **lucro** automaticamente:

- Desconta **20%** de taxa do marketplace (sobre o valor de venda)
- Desconta **R$ 4,00** fixo por unidade
- Desconta **8%** de imposto (sobre o valor de venda)
- Calcula **custo médio ponderado** por SKU até a data da venda
- Exporta **CSV** e mostra **indicadores** (faturamento, custos, taxas, impostos, lucro)

## 🚀 Rodando localmente (VS Code)

```bash
python -m venv .venv
# Windows (PowerShell)
.venv\Scripts\Activate.ps1
# macOS/Linux
# source .venv/bin/activate

pip install -r requirements.txt
python -m streamlit run app.py
```

Se o link não aparecer, copie/cole no navegador: `http://localhost:8501`  
Porta ocupada? Rode em outra porta:  
```bash
python -m streamlit run app.py --server.port 8502
```

## 📁 Estrutura
```
.
├── app.py
├── requirements.txt
├── .gitignore
└── dados.db           # gerado automaticamente depois de rodar
```

## 🧮 Como usar
1. **Compras**: cadastre o SKU, custo unitário e quantidade (pode registrar várias compras ao longo do mês).
2. **Vendas**: registre o SKU, preço de venda e quantidade.
3. **Lucro (automático)**: escolha o mês → o app calcula custo médio, aplica taxas/impostos e exibe o lucro.

> Dica: use **o mesmo SKU** nas compras e vendas para o custo médio funcionar.

## ☁️ Subindo no GitHub

Crie o repositório no GitHub e envie:
```bash
git init
git add .
git commit -m "App Streamlit de compras, vendas e lucro"
git branch -M main
git remote add origin https://github.com/SEU-USUARIO/controle-loja-streamlit.git
git push -u origin main
```

## 🌐 Hospedagem (opcional)
- **Streamlit Community Cloud** (grátis): crie um app a partir do seu repositório GitHub.
- **Render/Fly.io/Railway**: plataformas de deploy que rodam apps Python.

Licença: MIT
