# app.py
# -------------------------------------------------------------
# App site em Python (Streamlit) para registrar Compras, Vendas
# e calcular Lucro por mês com as regras:
#  - 20% de taxa do marketplace (sobre preço de venda)
#  - R$ 4,00 fixo por unidade vendida
#  - 8% de imposto (sobre preço de venda)
# Persistência local via SQLite. Edite no VS Code e rode com:
#   pip install streamlit pandas
#   streamlit run app.py
# -------------------------------------------------------------

import sqlite3
from datetime import date, datetime
import pandas as pd
import streamlit as st
from pathlib import Path

DB_PATH = Path("dados.db")

# -------------- Utilidades -----------------

def get_conn():
    return sqlite3.connect(DB_PATH)


def init_db():
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS purchases (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                sku TEXT NOT NULL,
                name TEXT,
                unit_cost REAL NOT NULL,
                quantity INTEGER NOT NULL
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS sales (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                sku TEXT NOT NULL,
                name TEXT,
                unit_price REAL NOT NULL,
                quantity INTEGER NOT NULL,
                marketplace TEXT
            )
            """
        )
        cur.execute("CREATE INDEX IF NOT EXISTS idx_purchases_sku ON purchases(sku)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_sales_sku ON sales(sku)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_purchases_date ON purchases(date)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_sales_date ON sales(date)")
        conn.commit()


def iso(d: date) -> str:
    return d.isoformat()


def fmt_money(x):
    try:
        return f"R$ {float(x):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except Exception:
        return x

# custo médio ponderado até a data (inclusive)
def get_avg_cost_until(sku: str, until_iso: str) -> float | None:
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT SUM(unit_cost * quantity) * 1.0 / NULLIF(SUM(quantity), 0)
            FROM purchases
            WHERE sku = ? AND date <= ?
            """,
            (sku, until_iso),
        )
        row = cur.fetchone()
        if row and row[0] is not None:
            return float(row[0])
        return None



# -------------- UI -----------------

st.set_page_config(page_title="Controle de Compras, Vendas e Lucro", page_icon="💹", layout="wide")

init_db()

st.title("💼 Controle de Compras, Vendas e Lucro")

aba1, aba2, aba3 = st.tabs(["📥 Compras do mês", "🧾 Vendas do mês", "💰 Lucro (automático)"])

# --------- Aba Compras ---------
with aba1:
    st.subheader("Cadastrar compra")
    with st.form("form_compras", clear_on_submit=True):
        col1, col2, col3 = st.columns([1, 1, 2])
        d = col1.date_input("Data da compra", value=date.today())
        sku = col2.text_input("SKU / Código", placeholder="Ex.: KETTLE-INOX-18L", max_chars=60)
        nome = col3.text_input("Nome do produto", placeholder="Chaleira Elétrica Inox 1,8L", max_chars=120)
        c1, c2 = st.columns(2)
        custo_unit = c1.number_input("Custo unitário (R$)", min_value=0.0, step=0.1, format="%.2f")
        qtd = c2.number_input("Quantidade comprada", min_value=1, step=1)
        enviar = st.form_submit_button("Salvar compra")
        if enviar:
            if not sku:
                st.warning("Informe o SKU/Código.")
            elif custo_unit <= 0:
                st.warning("Informe o custo unitário.")
            else:
                with get_conn() as conn:
                    conn.execute(
                        "INSERT INTO purchases(date, sku, name, unit_cost, quantity) VALUES (?, ?, ?, ?, ?)",
                        (iso(d), sku.strip(), nome.strip(), float(custo_unit), int(qtd)),
                    )
                    conn.commit()
                st.success("Compra registrada!")

    st.divider()

    st.subheader("Compras cadastradas (mês atual)")
    # filtro mês atual
    first_day = date(date.today().year, date.today().month, 1).isoformat()
    last_day = date(date.today().year + (1 if date.today().month == 12 else 0),
                    1 if date.today().month == 12 else date.today().month + 1,
                    1).isoformat()
    with get_conn() as conn:
        dfc = pd.read_sql_query(
            "SELECT id, date AS data, sku, COALESCE(name,'') AS nome, unit_cost AS custo_unit, quantity AS qtd FROM purchases WHERE date >= ? AND date < ? ORDER BY date DESC, id DESC",
            conn,
            params=(first_day, last_day),
        )
    if not dfc.empty:
        dfc["total_compra"] = dfc["custo_unit"] * dfc["qtd"]
        st.dataframe(
            dfc.assign(
                custo_unit=dfc["custo_unit"].map(fmt_money),
                total_compra=dfc["total_compra"].map(fmt_money),
            ),
            use_container_width=True,
            hide_index=True,
        )
        # opção de excluir
        with st.expander("Excluir compra"):
            del_id = st.number_input("ID para excluir", min_value=0, step=1)
            if st.button("Excluir compra selecionada"):
                with get_conn() as conn:
                    conn.execute("DELETE FROM purchases WHERE id=?", (int(del_id),))
                    conn.commit()
                st.success("Compra excluída.")
                st.experimental_rerun()
    else:
        st.info("Sem compras no mês atual.")

# --------- Aba Vendas ---------
with aba2:
    st.subheader("Registrar venda")
    with st.form("form_vendas", clear_on_submit=True):
        col1, col2, col3 = st.columns([1, 1, 2])
        d = col1.date_input("Data da venda", value=date.today(), key="dv")
        sku_v = col2.text_input("SKU / Código", placeholder="KETTLE-INOX-18L", max_chars=60, key="skuv")
        nome_v = col3.text_input("Nome do produto", placeholder="Chaleira Elétrica Inox 1,8L", max_chars=120, key="nomev")
        c1, c2, c3 = st.columns([1,1,1])
        preco_unit = c1.number_input("Preço de venda (R$)", min_value=0.0, step=0.1, format="%.2f")
        qtd_v = c2.number_input("Quantidade vendida", min_value=1, step=1)
        market = c3.selectbox("Marketplace", ["Shopee", "Mercado Livre", "Outros"], index=0)
        enviar_v = st.form_submit_button("Salvar venda")
        if enviar_v:
            if not sku_v:
                st.warning("Informe o SKU/Código.")
            elif preco_unit <= 0:
                st.warning("Informe o preço de venda.")
            else:
                with get_conn() as conn:
                    conn.execute(
                        "INSERT INTO sales(date, sku, name, unit_price, quantity, marketplace) VALUES (?, ?, ?, ?, ?, ?)",
                        (iso(d), sku_v.strip(), nome_v.strip(), float(preco_unit), int(qtd_v), market),
                    )
                    conn.commit()
                st.success("Venda registrada!")

    st.divider()

    st.subheader("Vendas cadastradas (mês atual)")
    with get_conn() as conn:
        dfv = pd.read_sql_query(
            "SELECT id, date AS data, sku, COALESCE(name,'') AS nome, unit_price AS preco_unit, quantity AS qtd, marketplace FROM sales WHERE date >= ? AND date < ? ORDER BY date DESC, id DESC",
            conn,
            params=(first_day, last_day),
        )
    if not dfv.empty:
        dfv["faturamento"] = dfv["preco_unit"] * dfv["qtd"]
        st.dataframe(
            dfv.assign(
                preco_unit=dfv["preco_unit"].map(fmt_money),
                faturamento=dfv["faturamento"].map(fmt_money),
            ),
            use_container_width=True,
            hide_index=True,
        )
        with st.expander("Excluir venda"):
            del_id2 = st.number_input("ID para excluir", min_value=0, step=1, key="delv")
            if st.button("Excluir venda selecionada"):
                with get_conn() as conn:
                    conn.execute("DELETE FROM sales WHERE id=?", (int(del_id2),))
                    conn.commit()
                st.success("Venda excluída.")
                st.experimental_rerun()
    else:
        st.info("Sem vendas no mês atual.")

# --------- Aba Lucro ---------
with aba3:
    st.subheader("Lucro do período")

    # Seletor de mês/ano
    colf1, colf2 = st.columns(2)
    ref_date = colf1.date_input("Escolha um dia do mês para calcular (usamos o mês inteiro)", value=date.today())
    marketplace_filter = colf2.selectbox("Filtrar por marketplace (opcional)", ["Todos", "Shopee", "Mercado Livre", "Outros"], index=0)

    # intervalo do mês inteiro
    month_start = date(ref_date.year, ref_date.month, 1)
    next_month = date(ref_date.year + (1 if ref_date.month == 12 else 0), 1 if ref_date.month == 12 else ref_date.month + 1, 1)
    start_iso, end_iso = month_start.isoformat(), next_month.isoformat()

    # Carrega vendas no período
    with get_conn() as conn:
        if marketplace_filter == "Todos":
            df = pd.read_sql_query(
                "SELECT id, date AS data, sku, COALESCE(name,'') AS nome, unit_price, quantity, marketplace FROM sales WHERE date >= ? AND date < ? ORDER BY date",
                conn,
                params=(start_iso, end_iso),
            )
        else:
            df = pd.read_sql_query(
                "SELECT id, date AS data, sku, COALESCE(name,'') AS nome, unit_price, quantity, marketplace FROM sales WHERE date >= ? AND date < ? AND marketplace = ? ORDER BY date",
                conn,
                params=(start_iso, end_iso, marketplace_filter),
            )

    if df.empty:
        st.info("Sem vendas no período selecionado.")
    else:
        # Calcula custo médio até a data da venda (ponderado)
        avg_costs = []
        for _idx, r in df.iterrows():
            avg = get_avg_cost_until(r["sku"], r["data"])  # até a data da venda
            avg_costs.append(avg if avg is not None else 0.0)
        df["custo_medio_unit"] = avg_costs

        # Regras de dedução
        #  - 20% taxa marketplace sobre preço de venda (unit_price)
        #  - R$ 4,00 fixo por unidade vendida
        #  - 8% imposto sobre preço de venda (unit_price)
        df["taxa_percent_unit"] = df["unit_price"] * 0.20
        df["taxa_fixa_unit"] = 4.0
        df["imposto_unit"] = df["unit_price"] * 0.08

        # lucro unitário e total
        df["lucro_unit"] = df["unit_price"] - df["custo_medio_unit"] - df["taxa_percent_unit"] - df["taxa_fixa_unit"] - df["imposto_unit"]
        df["faturamento"] = df["unit_price"] * df["quantity"]
        df["lucro_total"] = df["lucro_unit"] * df["quantity"]
        df["margem_%"] = (df["lucro_unit"] / df["unit_price"]).replace([pd.NA, pd.NaT], 0) * 100

        # Tabela detalhada
        vis = df.copy()
        vis.rename(
            columns={
                "data": "Data",
                "sku": "SKU",
                "nome": "Produto",
                "unit_price": "Preço unit.",
                "quantity": "Qtd",
                "marketplace": "Marketplace",
                "custo_medio_unit": "Custo médio unit.",
                "taxa_percent_unit": "Taxa 20% (unit)",
                "taxa_fixa_unit": "Taxa fixa R$4 (unit)",
                "imposto_unit": "Imposto 8% (unit)",
                "lucro_unit": "Lucro unit.",
                "faturamento": "Faturamento",
                "lucro_total": "Lucro total",
            },
            inplace=True,
        )

        money_cols = [
            "Preço unit.", "Custo médio unit.", "Taxa 20% (unit)", "Taxa fixa R$4 (unit)", "Imposto 8% (unit)",
            "Lucro unit.", "Faturamento", "Lucro total"
        ]
        for c in money_cols:
            vis[c] = vis[c].map(fmt_money)
        vis["Margem %"] = df["margem_%"].round(2)

        st.dataframe(vis[[
            "Data","SKU","Produto","Marketplace","Qtd","Preço unit.","Custo médio unit.",
            "Taxa 20% (unit)","Taxa fixa R$4 (unit)","Imposto 8% (unit)","Lucro unit.","Faturamento","Lucro total","Margem %"
        ]], use_container_width=True, hide_index=True)

        # Indicadores agregados
        total_faturamento = float(df["faturamento"].sum())
        total_custo = float((df["custo_medio_unit"] * df["quantity"]).sum())
        total_taxa_percent = float((df["taxa_percent_unit"] * df["quantity"]).sum())
        total_taxa_fixa = float((df["taxa_fixa_unit"] * df["quantity"]).sum())
        total_imposto = float((df["imposto_unit"] * df["quantity"]).sum())
        total_lucro = float(df["lucro_total"].sum())

        cA, cB, cC, cD, cE, cF = st.columns(6)
        cA.metric("Faturamento", fmt_money(total_faturamento))
        cB.metric("Custo dos produtos", fmt_money(total_custo))
        cC.metric("Taxa marketplace (20%)", fmt_money(total_taxa_percent))
        cD.metric("Taxa fixa (R$4/un)", fmt_money(total_taxa_fixa))
        cE.metric("Imposto (8%)", fmt_money(total_imposto))
        cF.metric("Lucro total", fmt_money(total_lucro))

        st.download_button(
            label="Baixar relatório (CSV)",
            data=df.to_csv(index=False).encode("utf-8"),
            file_name=f"relatorio_lucro_{ref_date.strftime('%Y_%m')}.csv",
            mime="text/csv",
        )

st.caption("Dica: para começar do zero, registre primeiro as COMPRAS (com SKU), depois registre as VENDAS usando o mesmo SKU. O custo médio é calculado automaticamente.")
