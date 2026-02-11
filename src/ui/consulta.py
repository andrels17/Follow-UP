"""Tela: Consultar pedidos (com foco em performance e UX)."""
from __future__ import annotations

from datetime import datetime, timedelta

import pandas as pd
import plotly.express as px  # Mantido para compatibilidade (pode ser usado em gráficos futuros)
import streamlit as st

import exportacao_relatorios as er
import filtros_avancados as fa

from src.repositories.pedidos import carregar_pedidos
from src.utils.formatting import formatar_moeda_br, formatar_numero_br


# ----------------------------
# Helpers (cache / filtros)
# ----------------------------
def _df_stamp(df: pd.DataFrame) -> tuple:
    """Carimbo simples para invalidar caches quando os dados mudarem."""
    if df is None or df.empty:
        return (0, "empty")
    # Tenta usar uma coluna de atualização se existir
    for col in ("atualizado_em", "updated_at", "data_atualizacao"):
        if col in df.columns:
            try:
                return (int(len(df)), str(pd.to_datetime(df[col], errors="coerce").max()))
            except Exception:
                break
    return (int(len(df)), str(hash(tuple(df.columns))))


@st.cache_data(ttl=120, show_spinner=False)
def _build_search_series(stamp: tuple, df: pd.DataFrame) -> pd.Series:
    """Pré-monta uma série com os campos de busca concatenados em lowercase (barato de filtrar depois)."""
    if df is None or df.empty:
        return pd.Series([], dtype="string")
    nr_oc = df.get("nr_oc", pd.Series([""] * len(df))).astype(str).fillna("")
    desc = df.get("descricao", pd.Series([""] * len(df))).astype(str).fillna("")
    forn = df.get("fornecedor_nome", pd.Series([""] * len(df))).astype(str).fillna("")
    return (nr_oc + " " + desc + " " + forn).str.lower()


def _apply_filters(
    df: pd.DataFrame,
    busca: str,
    dept: str,
    status: str,
    situacao: str,
    filtrar_data: bool,
    data_inicio,
    data_fim,
    search_series: pd.Series | None = None,
) -> pd.DataFrame:
    """Aplica filtros de forma barata (evita recomputar strings de busca)."""
    out = df

    # Busca textual (usa série pré-processada alinhada ao index)
    if busca:
        s = search_series
        if s is None or len(s) != len(df) or not s.index.equals(df.index):
            s = _build_search_series(_df_stamp(df), df)
        mask = s.str.contains(str(busca).lower(), na=False)
        out = out[mask]

    if dept and dept != "Todos" and "departamento" in out.columns:
        out = out[out["departamento"] == dept]

    if status and status != "Todos" and "status" in out.columns:
        out = out[out["status"] == status]

    if situacao == "Pendentes" and "entregue" in out.columns:
        out = out[out["entregue"] == False]  # noqa: E712
    elif situacao == "Entregues" and "entregue" in out.columns:
        out = out[out["entregue"] == True]  # noqa: E712
    elif situacao == "Atrasados" and "atrasado" in out.columns:
        out = out[out["atrasado"] == True]  # noqa: E712

    if filtrar_data:
        col = "data_solicitacao" if "data_solicitacao" in out.columns else None
        if col is not None:
            ds = pd.to_datetime(out[col], errors="coerce")
            ini = pd.to_datetime(data_inicio) if data_inicio else None
            fim = pd.to_datetime(data_fim) if data_fim else None
            if ini is not None:
                out = out[ds >= ini]
            if fim is not None:
                out = out[ds <= fim]

    return out


def _paginate(df: pd.DataFrame, page: int, page_size: int) -> pd.DataFrame:
    if df is None or df.empty:
        return df
    page = max(1, int(page))
    page_size = max(10, int(page_size))
    start = (page - 1) * page_size
    end = start + page_size
    return df.iloc[start:end]


def _download_df(df: pd.DataFrame, nome: str) -> None:
    """Botão de download CSV do dataframe filtrado."""
    if df is None or df.empty:
        return
    csv_bytes = df.to_csv(index=False, sep=";", decimal=",", encoding="utf-8-sig").encode("utf-8-sig")
    st.download_button("⬇️ Baixar resultado (CSV)", data=csv_bytes, file_name=nome, mime="text/csv", use_container_width=True)


def exibir_consulta_pedidos(_supabase):
    """Exibe página de consulta e filtros de pedidos."""

    st.title("🔍 Consultar Pedidos")

    with st.spinner("Carregando pedidos..."):
        df_pedidos = carregar_pedidos(_supabase)

    if df_pedidos.empty:
        st.info("📭 Nenhum pedido cadastrado ainda")
        return

    # ----------------------------
    # Sidebar: filtros com form (evita rerun a cada mudança)
    # ----------------------------
    with st.sidebar:
        st.subheader("🔎 Filtros")

        # Defaults persistidos
        if "c_busca" not in st.session_state:
            st.session_state.c_busca = ""
        if "c_dept" not in st.session_state:
            st.session_state.c_dept = "Todos"
        if "c_status" not in st.session_state:
            st.session_state.c_status = "Todos"
        if "c_situacao" not in st.session_state:
            st.session_state.c_situacao = "Todos"
        if "c_filtrar_data" not in st.session_state:
            st.session_state.c_filtrar_data = False
        if "c_data_inicio" not in st.session_state:
            st.session_state.c_data_inicio = (datetime.now() - timedelta(days=30)).date()
        if "c_data_fim" not in st.session_state:
            st.session_state.c_data_fim = datetime.now().date()
        if "c_page_size" not in st.session_state:
            st.session_state.c_page_size = 50

        departamentos = ["Todos"] + sorted(df_pedidos.get("departamento", pd.Series(dtype="object")).dropna().unique().tolist())
        status_opcoes = ["Todos"] + sorted(df_pedidos.get("status", pd.Series(dtype="object")).dropna().unique().tolist())

        with st.form("form_filtros_consulta"):
            busca = st.text_input("🔍 Buscar", placeholder="N° OC, Descrição, Fornecedor...", key="c_busca")
            dept = st.selectbox("🏢 Departamento", departamentos, key="c_dept")
            status = st.selectbox("📊 Status", status_opcoes, key="c_status")
            situacao = st.radio("📦 Situação", ["Todos", "Pendentes", "Entregues", "Atrasados"], key="c_situacao")

            st.markdown("---")
            filtrar_data = st.checkbox("Filtrar por período", key="c_filtrar_data")
            data_inicio = None
            data_fim = None
            if filtrar_data:
                data_inicio = st.date_input("Data início", key="c_data_inicio")
                data_fim = st.date_input("Data fim", key="c_data_fim")

            st.markdown("---")
            page_size = st.selectbox("Linhas por página", [25, 50, 100, 200], key="c_page_size")

            col_a, col_b = st.columns(2)
            with col_a:
                aplicar = st.form_submit_button("Aplicar")
            with col_b:
                limpar = st.form_submit_button("Limpar")

        if aplicar:
            st.session_state.pagina_consulta = 1

        if limpar:
            for k in ("c_busca","c_dept","c_status","c_situacao","c_filtrar_data","c_data_inicio","c_data_fim","c_page_size",
                      "busca_detalhes","pedido_id_selecionado","pagina_consulta"):
                if k in st.session_state:
                    del st.session_state[k]
            st.rerun()

    # Se nunca clicou em aplicar, ainda assim usa o que está no estado (melhor UX)
    busca = st.session_state.get("c_busca", "")
    dept = st.session_state.get("c_dept", "Todos")
    status = st.session_state.get("c_status", "Todos")
    situacao = st.session_state.get("c_situacao", "Todos")
    filtrar_data = st.session_state.get("c_filtrar_data", False)
    data_inicio = st.session_state.get("c_data_inicio", None) if filtrar_data else None
    data_fim = st.session_state.get("c_data_fim", None) if filtrar_data else None
    page_size = st.session_state.get("c_page_size", 50)

    # ----------------------------
    # Aplicar filtros
    # ----------------------------
    search_series = _build_search_series(_df_stamp(df_pedidos), df_pedidos)
    df_filtrado = _apply_filters(df_pedidos, busca, dept, status, situacao, filtrar_data, data_inicio, data_fim, search_series=search_series)

    st.info(f"📊 {len(df_filtrado)} pedidos encontrados")

    if df_filtrado.empty:
        return

    # ----------------------------
    # Detalhes do pedido (com busca leve e selectbox eficiente)
    # ----------------------------
    st.markdown("---")
    st.subheader("📋 Detalhes do Pedido")

    # Busca de detalhes persistida (sem st.rerun)
    busca_detalhes = st.text_input(
        "🔍 Buscar pedido por N° OC, Descrição ou Fornecedor",
        placeholder="Digite para buscar...",
        key="busca_detalhes",
    )

    df_selecao = df_filtrado
    if busca_detalhes:
        s = _build_search_series(_df_stamp(df_selecao), df_selecao)
        df_selecao = df_selecao[s.str.contains(busca_detalhes.lower(), na=False)]
        if df_selecao.empty:
            st.warning(f"⚠️ Nenhum pedido encontrado com '{busca_detalhes}'")
            df_selecao = df_filtrado

    # Mapa id -> label (O(1) no format_func)
    ids = df_selecao["id"].tolist() if "id" in df_selecao.columns else []
    label_map = {}
    if ids:
        # monta labels uma vez
        for _, row in df_selecao[["id","nr_oc","descricao","fornecedor_nome"]].fillna("").iterrows():
            desc = str(row["descricao"])
            label_map[row["id"]] = f"OC: {row['nr_oc']} — {desc[:60]} | {row.get('fornecedor_nome','')}"
    else:
        st.warning("⚠️ Não foi possível listar IDs para seleção.")
        return

    pedido_id = st.selectbox(
        "Selecione um pedido para ver detalhes:",
        options=ids,
        format_func=lambda x: label_map.get(x, str(x)),
        key="pedido_id_selecionado",
    )

    if pedido_id:
        pedido_info = df_filtrado[df_filtrado["id"] == pedido_id].iloc[0]

        col1, col2 = st.columns(2)
        with col1:
            st.markdown(
                f"""
**N° Solicitação:** {pedido_info.get('nr_solicitacao','')}  
**N° OC:** {pedido_info.get('nr_oc','')}  
**Departamento:** {pedido_info.get('departamento','')}  
**Equipamento:** {pedido_info.get('cod_equipamento','')}  
**Código Material:** {pedido_info.get('cod_material','')}  
**Descrição:** {pedido_info.get('descricao','')}
"""
            )
        with col2:
            data_sol = pedido_info.get("data_solicitacao", None)
            if pd.notna(data_sol):
                try:
                    data_sol_fmt = pd.to_datetime(data_sol).strftime("%d/%m/%Y")
                except Exception:
                    data_sol_fmt = str(data_sol)
            else:
                data_sol_fmt = ""

            st.markdown(
                f"""
**Fornecedor:** {pedido_info.get('fornecedor_nome','')}  
**Cidade/UF:** {pedido_info.get('fornecedor_cidade','')}/{pedido_info.get('fornecedor_uf','')}  
**Data Solicitação:** {data_sol_fmt}  
**Previsão Entrega:** {pedido_info.get('previsao_entrega','')}  
**Status:** {pedido_info.get('status','')}  
**Valor Total:** {formatar_moeda_br(pedido_info.get('valor_total', 0)) if 'valor_total' in pedido_info else ''}
"""
            )

    # ----------------------------
    # Tabela com paginação (formatar só o que vai aparecer)
    # ----------------------------
    st.markdown("---")
    st.subheader("📑 Lista de Pedidos")

    total = len(df_filtrado)
    total_pages = max(1, (total + page_size - 1) // page_size)

    if "pagina_consulta" not in st.session_state:
        st.session_state.pagina_consulta = 1
    else:
        # garante que a página atual existe após mudar filtros
        st.session_state.pagina_consulta = max(1, min(int(st.session_state.pagina_consulta), total_pages))

    colp1, colp2, colp3 = st.columns([2, 2, 6])
    with colp1:
        if st.button("⬅️", disabled=st.session_state.pagina_consulta <= 1):
            st.session_state.pagina_consulta -= 1
    with colp2:
        if st.button("➡️", disabled=st.session_state.pagina_consulta >= total_pages):
            st.session_state.pagina_consulta += 1
    with colp3:
        st.caption(f"Página {st.session_state.pagina_consulta} de {total_pages} • {page_size} por página")

    df_page = _paginate(df_filtrado, st.session_state.pagina_consulta, page_size)

    # monta apenas as colunas de exibição e formata apenas a página
    df_display = df_page.copy()
    if "valor_total" in df_display.columns:
        df_display["valor_total_formatado"] = df_display["valor_total"].apply(formatar_moeda_br)
    else:
        df_display["valor_total_formatado"] = ""

    for col, out_col in [
        ("qtde_solicitada", "qtde_solicitada_formatada"),
        ("qtde_entregue", "qtde_entregue_formatada"),
        ("qtde_pendente", "qtde_pendente_formatada"),
    ]:
        if col in df_display.columns:
            df_display[out_col] = df_display[col].apply(formatar_numero_br)
        else:
            df_display[out_col] = ""

    cols = [
        "nr_oc",
        "descricao",
        "departamento",
        "fornecedor_nome",
        "qtde_solicitada_formatada",
        "qtde_entregue_formatada",
        "qtde_pendente_formatada",
        "previsao_entrega",
        "status",
        "valor_total_formatado",
    ]
    cols = [c for c in cols if c in df_display.columns]

    st.dataframe(
        df_display[cols],
        use_container_width=True,
        hide_index=True,
        height=420,
        column_config={
            "nr_oc": "N° OC",
            "descricao": "Descrição",
            "departamento": "Departamento",
            "fornecedor_nome": "Fornecedor",
            "qtde_solicitada_formatada": "Qtd. Solicitada",
            "qtde_entregue_formatada": "Qtd. Entregue",
            "qtde_pendente_formatada": "Qtd. Pendente",
            "previsao_entrega": st.column_config.DateColumn("Previsão", format="DD/MM/YYYY"),
            "status": "Status",
            "valor_total_formatado": "Valor Total",
        },
    )
