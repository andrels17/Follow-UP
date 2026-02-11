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
    """Normaliza tipos e cria coluna de busca (cacheada)."""
    if df is None or df.empty:
        return df

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

    for dc in ["data_solicitacao", "data_oc", "previsao_entrega", "data_entrega"]:
        if dc in out.columns:
            out[dc] = pd.to_datetime(out[dc], errors="coerce")

    for nc in ["qtde_solicitada", "qtde_entregue", "valor_total", "dias_atraso", "qtde_pendente"]:
        if nc in out.columns:
            out[nc] = pd.to_numeric(out[nc], errors="coerce")

    return out

def _is_atrasado(df: pd.DataFrame) -> pd.Series:
    if df is None or df.empty:
        return pd.Series([], dtype=bool)
    if "dias_atraso" in df.columns:
        return pd.to_numeric(df["dias_atraso"], errors="coerce").fillna(0) > 0
    if "previsao_entrega" in df.columns:
        hoje = pd.Timestamp.now().normalize()
        if "status" in df.columns:
            status_ok = df["status"].fillna("").astype(str) != "Entregue"
        else:
            status_ok = True
        return df["previsao_entrega"].notna() & (df["previsao_entrega"] < hoje) & status_ok
    return pd.Series([False] * len(df), index=df.index)

def _apply_filters(df: pd.DataFrame, q: str, depto: str, status: str, somente_atrasados: bool) -> pd.DataFrame:
    out = df

    if depto != "Todos" and "departamento" in out.columns:
        out = out[out["departamento"] == depto]

    if status != "Todos" and "status" in out.columns:
        out = out[out["status"] == status]

    if q:
        out = out[out["__search__"].str.contains(q.lower().strip(), na=False)]

    if somente_atrasados:
        out = out[_is_atrasado(out)]

    return out

def _download_csv(df: pd.DataFrame, filename: str):
    csv = df.to_csv(index=False, sep=";", decimal=",", encoding="utf-8-sig").encode("utf-8-sig")
    st.download_button("⬇️ CSV", csv, file_name=filename, mime="text/csv", use_container_width=True)

def _download_xlsx(df: pd.DataFrame, filename: str):
    """Download XLSX without requiring xlsxwriter (fallback to openpyxl)."""
    output = io.BytesIO()
    engine = "xlsxwriter"
    try:
        __import__("xlsxwriter")
    except Exception:
        engine = "openpyxl"

    with pd.ExcelWriter(output, engine=engine) as writer:
        df.to_excel(writer, index=False, sheet_name="Pedidos")

    st.download_button(
        "⬇️ XLSX",
        output.getvalue(),
        file_name=filename,
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
    )

def _set_preset(preset: str):
    if preset == "atraso":
        st.session_state.update({"c_atraso": True, "c_status": "Todos", "c_pag": 1})
    elif preset == "transporte":
        st.session_state.update({"c_status": "Em Transporte", "c_atraso": False, "c_pag": 1})
    elif preset == "sem_oc":
        st.session_state.update({"c_status": "Sem OC", "c_atraso": False, "c_pag": 1})

def _to_label(row: pd.Series) -> str:
    nr_oc = str(row.get("nr_oc") or "").strip()
    nr_sol = str(row.get("nr_solicitacao") or "").strip()
    dept = str(row.get("departamento") or "").strip()
    stt = str(row.get("status") or "").strip()
    desc = str(row.get("descricao") or "").strip().replace("\n", " ")
    if len(desc) > 70:
        desc = desc[:70] + "…"
    return f"OC: {nr_oc or '-'} | SOL: {nr_sol or '-'} | {stt} | {dept} — {desc}"

def exibir_consulta_pedidos(_supabase):
    st.title("🔎 Consultar Pedidos")

    df_raw = carregar_pedidos(_supabase)
    if df_raw is None or df_raw.empty:
        st.info("📭 Nenhum pedido cadastrado.")
        return

    df = _prepare_search(_make_stamp(df_raw), df_raw)

    atrasados = int(_is_atrasado(df).sum())
    sem_oc = int((df["status"] == "Sem OC").sum()) if "status" in df.columns else 0
    transporte = int((df["status"] == "Em Transporte").sum()) if "status" in df.columns else 0
    entregues = int((df["status"] == "Entregue").sum()) if "status" in df.columns else 0
    total = int(len(df))

    st.subheader("Visão rápida")
    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        st.metric("Total", total)
    with c2:
        st.metric("Atrasados", atrasados)
        if st.button("Filtrar", key="preset_atraso", use_container_width=True):
            _set_preset("atraso")
            st.rerun()
    with c3:
        st.metric("Sem OC", sem_oc)
        if st.button("Filtrar", key="preset_semoc", use_container_width=True):
            _set_preset("sem_oc")
            st.rerun()
    with c4:
        st.metric("Em transporte", transporte)
        if st.button("Filtrar", key="preset_transp", use_container_width=True):
            _set_preset("transporte")
            st.rerun()
    with c5:
        st.metric("Entregues", entregues)

    st.markdown("---")

    with st.sidebar:
        st.subheader("Filtros")
        with st.form("filtros_consulta"):
            q = st.text_input("Buscar (OC, solicitação, descrição, fornecedor...)", value=st.session_state.get("c_q", ""))
            depto = st.selectbox("Departamento", ["Todos"] + DEPARTAMENTOS_VALIDOS, index=0)
            status = st.selectbox("Status", ["Todos"] + STATUS_VALIDOS, index=0)
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

    k1, k2, k3 = st.columns(3)
    k1.metric("Resultados (filtro)", int(len(df_f)))
    k2.metric("Atrasados (filtro)", int(_is_atrasado(df_f).sum()))
    if "valor_total" in df_f.columns:
        k3.metric("Valor total (filtro)", float(pd.to_numeric(df_f["valor_total"], errors="coerce").fillna(0).sum()))
    else:
        k3.metric("Valor total (filtro)", 0)

    cols_default = [c for c in [
        "nr_solicitacao", "nr_oc", "departamento", "fornecedor", "descricao", "status",
        "previsao_entrega", "qtde_solicitada", "qtde_entregue", "qtde_pendente", "valor_total"
    ] if c in df_f.columns]

    with st.expander("⚙️ Colunas exibidas", expanded=False):
        cols_sel = st.multiselect(
            "Selecione colunas",
            options=[c for c in df_f.columns if not c.startswith("__")],
            default=cols_default
        )
        if not cols_sel:
            st.warning("Selecione ao menos uma coluna para exibir.")
            return

    total_f = int(len(df_f))
    total_paginas = max(1, math.ceil(total_f / por_pagina))
    pag = st.number_input(
        "Página",
        min_value=1,
        max_value=total_paginas,
        value=min(int(st.session_state.get("c_pag", 1)), total_paginas),
        step=1
    )
    st.session_state["c_pag"] = int(pag)

    i0 = (int(pag) - 1) * por_pagina
    i1 = i0 + por_pagina

    df_page_all = df_f.iloc[i0:i1].copy()

    st.caption(f"Mostrando {i0 + 1}–{min(i1, total_f)} de {total_f} resultados.")
    st.dataframe(df_page_all[cols_sel], use_container_width=True, height=520)

    st.subheader("Ações rápidas")
    st.caption("Selecione um pedido e use os atalhos para abrir na Gestão ou ir para a Ficha do Material.")

    if df_page_all.empty:
        st.info("Sem resultados nesta página.")
    else:
        options = []
        id_to_row = {}

        for _, r in df_page_all.iterrows():
            pid = str(r.get("id") or "")
            if not pid:
                continue
            options.append(pid)
            id_to_row[pid] = (_to_label(r), r)

        if not options:
            st.info("Não foi possível montar ações (coluna 'id' não encontrada).")
        else:
            default_pid = st.session_state.get("consulta_selected_pid")
            if default_pid not in options:
                default_pid = options[0]

            sel_pid = st.selectbox(
                "Pedido selecionado",
                options=options,
                index=options.index(default_pid),
                format_func=lambda pid: id_to_row[pid][0]
            )
            st.session_state["consulta_selected_pid"] = sel_pid
            row = id_to_row[sel_pid][1]

            nr_oc_sel = str(row.get("nr_oc") or "").strip()
            nr_sol_sel = str(row.get("nr_solicitacao") or "").strip()
            desc_sel = str(row.get("descricao") or "").strip()
            cod_mat_sel = str(row.get("cod_material") or "").strip()

            b1, b2, b3, b4 = st.columns(4)

            with b1:
                if st.button("✏️ Abrir na Gestão", use_container_width=True):
                    st.session_state["gp_open_pedido_id"] = sel_pid
                    st.session_state["gp_open_tab"] = "editar"
                    st.success("✅ Vá em **Gestão de Pedidos → Editar** (pedido já selecionado).")
            with b2:
                if st.button("📄 Ficha do Material", use_container_width=True):
                    st.session_state["fm_open_tipo"] = "material"
                    st.session_state["fm_open_codigo"] = cod_mat_sel if cod_mat_sel else None
                    st.session_state["fm_open_descricao"] = desc_sel if desc_sel else None
                    st.success("✅ Abra **Ficha do Material** (filtros preenchidos automaticamente).")
            with b3:
                if st.button("📋 Copiar OC/SOL", use_container_width=True):
                    st.code(f"OC: {nr_oc_sel} | SOL: {nr_sol_sel}")
            with b4:
                if st.button("🔎 Filtro por OC", use_container_width=True, disabled=not bool(nr_oc_sel)):
                    st.session_state.update({"c_q": nr_oc_sel, "c_pag": 1})
                    st.rerun()

    st.markdown("---")

    st.subheader("Exportar")
    ce1, ce2 = st.columns(2)
    with ce1:
        _download_csv(df_f[cols_sel].copy(), "consulta_pedidos.csv")
    with ce2:
        _download_xlsx(df_f[cols_sel].copy(), "consulta_pedidos.xlsx")
