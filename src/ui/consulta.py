
from __future__ import annotations

import math
import io
import pandas as pd
import streamlit as st

from src.repositories.pedidos import carregar_pedidos

STATUS_VALIDOS = ["Sem OC", "Tem OC", "Em Transporte", "Entregue"]
DEPARTAMENTOS_VALIDOS = [
    "Estoque", "Caminhões", "Oficina Geral", "Borracharia",
    "Máquinas pesadas", "Veic. Leves", "Tratores", "Colhedoras",
    "Irrigação", "Reboques", "Carregadeiras"
]

def _make_stamp(df: pd.DataFrame, col: str = "atualizado_em") -> tuple:
    if df is None or df.empty:
        return (0, "empty")
    mx = None
    if col in df.columns:
        mx = pd.to_datetime(df[col], errors="coerce").max()
    return (len(df), str(mx) if mx is not None else "none")

@st.cache_data(ttl=120)
def _prepare_search(stamp: tuple, df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    cols = []
    for c in ["nr_oc", "nr_solicitacao", "descricao", "departamento", "fornecedor", "cod_material", "cod_equipamento"]:
        if c in out.columns:
            cols.append(out[c].fillna("").astype(str).str.lower())
    if cols:
        s = cols[0]
        for x in cols[1:]:
            s = s + " " + x
        out["__search__"] = s.str.replace(r"\s+", " ", regex=True).str.strip()
    else:
        out["__search__"] = ""

    for dc in ["data_solicitacao", "data_oc", "previsao_entrega"]:
        if dc in out.columns:
            out[dc] = pd.to_datetime(out[dc], errors="coerce")

    for nc in ["qtde_solicitada", "qtde_entregue", "valor_total"]:
        if nc in out.columns:
            out[nc] = pd.to_numeric(out[nc], errors="coerce")

    return out

def _apply_filters(df: pd.DataFrame, q: str, depto: str, status: str, somente_atrasados: bool):
    out = df
    if depto != "Todos" and "departamento" in out.columns:
        out = out[out["departamento"] == depto]
    if status != "Todos" and "status" in out.columns:
        out = out[out["status"] == status]
    if q:
        out = out[out["__search__"].str.contains(q.lower().strip(), na=False)]
    if somente_atrasados:
        if "dias_atraso" in out.columns:
            out = out[pd.to_numeric(out["dias_atraso"], errors="coerce").fillna(0) > 0]
        elif "previsao_entrega" in out.columns:
            hoje = pd.Timestamp.now().normalize()
            out = out[out["previsao_entrega"].notna() & (out["previsao_entrega"] < hoje) & (out.get("status","") != "Entregue")]
    return out

def _download_csv(df: pd.DataFrame, filename: str):
    csv = df.to_csv(index=False, sep=";", decimal=",", encoding="utf-8-sig").encode("utf-8-sig")
    st.download_button("⬇️ CSV", csv, file_name=filename, mime="text/csv")

def _download_xlsx(df: pd.DataFrame, filename: str):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        df.to_excel(writer, index=False, sheet_name="Pedidos")
    st.download_button("⬇️ XLSX", output.getvalue(), file_name=filename, mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

def exibir_consulta_pedidos(_supabase):
    st.title("🔎 Consultar Pedidos")

    df_raw = carregar_pedidos(_supabase)
    if df_raw.empty:
        st.info("📭 Nenhum pedido cadastrado.")
        return

    df = _prepare_search(_make_stamp(df_raw), df_raw)

    # Presets rápidos
    cpr1, cpr2, cpr3 = st.columns(3)
    if cpr1.button("📦 Em atraso"):
        st.session_state.update({"c_atraso": True, "c_status": "Todos", "c_pag": 1})
    if cpr2.button("🚚 Em transporte"):
        st.session_state.update({"c_status": "Em Transporte", "c_atraso": False, "c_pag": 1})
    if cpr3.button("🧾 Sem OC"):
        st.session_state.update({"c_q": "sem oc", "c_pag": 1})

    with st.sidebar:
        st.subheader("Filtros")
        with st.form("filtros_consulta"):
            q = st.text_input("Buscar", value=st.session_state.get("c_q", ""))
            depto = st.selectbox("Departamento", ["Todos"] + DEPARTAMENTOS_VALIDOS)
            status = st.selectbox("Status", ["Todos"] + STATUS_VALIDOS)
            somente_atrasados = st.checkbox("Somente atrasados", value=st.session_state.get("c_atraso", False))
            por_pagina = st.selectbox("Itens por página", [50, 100, 200, 500], index=1)
            aplicar = st.form_submit_button("Aplicar")

        if aplicar:
            st.session_state.update({
                "c_q": q,
                "c_depto": depto,
                "c_status": status,
                "c_atraso": somente_atrasados,
                "c_pp": por_pagina,
                "c_pag": 1
            })

    q = st.session_state.get("c_q", "")
    depto = st.session_state.get("c_depto", "Todos")
    status = st.session_state.get("c_status", "Todos")
    somente_atrasados = st.session_state.get("c_atraso", False)
    por_pagina = int(st.session_state.get("c_pp", 100))

    df_f = _apply_filters(df, q, depto, status, somente_atrasados)

    # KPIs
    k1, k2, k3 = st.columns(3)
    k1.metric("Resultados", len(df_f))
    k2.metric("Entregues", int((df_f["status"] == "Entregue").sum()) if "status" in df_f.columns else 0)
    k3.metric("Valor total", float(df_f["valor_total"].fillna(0).sum()) if "valor_total" in df_f.columns else 0)

    cols_default = [c for c in ["nr_solicitacao","nr_oc","departamento","fornecedor","descricao","status","previsao_entrega","qtde_solicitada","qtde_entregue","valor_total"] if c in df_f.columns]
    with st.expander("⚙️ Colunas exibidas"):
        cols_sel = st.multiselect("Colunas", options=[c for c in df_f.columns if not c.startswith("__")], default=cols_default)

    total = len(df_f)
    total_paginas = max(1, math.ceil(total / por_pagina))
    pag = st.number_input("Página", min_value=1, max_value=total_paginas, value=min(st.session_state.get("c_pag", 1), total_paginas))
    st.session_state["c_pag"] = int(pag)

    i0 = (pag - 1) * por_pagina
    i1 = i0 + por_pagina

    df_page = df_f.iloc[i0:i1][cols_sel].copy()

    # Ação abrir pedido
    if "id" in df_page.columns:
        df_page["🔍"] = "Abrir"

    st.dataframe(df_page, use_container_width=True, height=520)

    # Export
    cexp1, cexp2 = st.columns(2)
    with cexp1:
        _download_csv(df_f[cols_sel], "consulta_pedidos.csv")
    with cexp2:
        _download_xlsx(df_f[cols_sel], "consulta_pedidos.xlsx")
