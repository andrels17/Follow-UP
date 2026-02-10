"""
Módulo de Dashboard Avançado
Gráficos interativos e análises preditivas

Melhorias aplicadas:
- Pré-processamento de datas (data_solicitacao) feito uma única vez
- Agregações pesadas com cache (st.cache_data)
- Filtros em st.form (evita rerun a cada clique no sidebar)
- Redução de cópias desnecessárias de DataFrame
"""

from __future__ import annotations

from datetime import datetime, timedelta

import pandas as pd
import plotly.graph_objects as go
import streamlit as st


# ----------------------------
# Helpers (performance)
# ----------------------------

def _df_key(df: pd.DataFrame) -> tuple:
    """Gera uma chave simples para invalidar cache quando o dataset muda."""
    if df is None or df.empty:
        return (0, "empty")

    # Evita KeyError caso não exista
    updated_col = None
    for col in ("atualizado_em", "updated_at", "data_atualizacao", "created_at"):
        if col in df.columns:
            updated_col = col
            break

    max_updated = None
    if updated_col:
        try:
            max_updated = pd.to_datetime(df[updated_col], errors="coerce").max()
        except Exception:
            max_updated = None

    return (int(len(df)), str(max_updated) if max_updated is not None else "no-updated-col")


@st.cache_data(ttl=300)
def _prepare_datas(_key: tuple, df_small: pd.DataFrame) -> pd.DataFrame:
    """Normaliza a coluna data_solicitacao para datetime e remove nulos/invalidos."""
    if df_small.empty or "data_solicitacao" not in df_small.columns:
        return pd.DataFrame()

    s = df_small["data_solicitacao"]
    if not pd.api.types.is_datetime64_any_dtype(s):
        s = pd.to_datetime(s, errors="coerce")

    out = df_small.copy()
    out["data_solicitacao_dt"] = s
    out = out[out["data_solicitacao_dt"].notna()]
    return out


@st.cache_data(ttl=300)
def _agg_evolucao(_key: tuple, df_small: pd.DataFrame) -> pd.DataFrame:
    """Agrupa por mês para o gráfico de evolução."""
    dfp = _prepare_datas(_key, df_small)
    if dfp.empty:
        return pd.DataFrame()

    dfp["mes_ano"] = dfp["data_solicitacao_dt"].dt.to_period("M").astype(str)

    # Usa apenas o que precisa
    if "valor_total" not in dfp.columns:
        dfp["valor_total"] = 0

    agg = (
        dfp.groupby("mes_ano", dropna=False)
        .agg(qtd=("id", "count"), valor_total=("valor_total", "sum"))
        .reset_index()
        .sort_values("mes_ano")
    )
    return agg


@st.cache_data(ttl=300)
def _agg_heatmap(_key: tuple, df_small: pd.DataFrame) -> pd.DataFrame:
    """Retorna pivot (dias x períodos) para heatmap."""
    dfp = _prepare_datas(_key, df_small)
    if dfp.empty:
        return pd.DataFrame()

    dt = dfp["data_solicitacao_dt"]
    dias_en = dt.dt.day_name()
    hora = dt.dt.hour

    dias_pt = {
        "Monday": "Segunda",
        "Tuesday": "Terça",
        "Wednesday": "Quarta",
        "Thursday": "Quinta",
        "Friday": "Sexta",
        "Saturday": "Sábado",
        "Sunday": "Domingo",
    }

    def categorizar_periodo(h: int) -> str:
        if 6 <= h < 12:
            return "Manhã (6h-12h)"
        if 12 <= h < 18:
            return "Tarde (12h-18h)"
        if 18 <= h < 24:
            return "Noite (18h-24h)"
        return "Madrugada (0h-6h)"

    dfp = dfp.assign(
        dia_semana=dias_en.map(dias_pt),
        periodo=hora.map(categorizar_periodo),
    )

    heat = dfp.groupby(["dia_semana", "periodo"]).size().reset_index(name="quantidade")

    ordem_dias = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo"]
    ordem_periodos = ["Manhã (6h-12h)", "Tarde (12h-18h)", "Noite (18h-24h)", "Madrugada (0h-6h)"]

    pivot = (
        heat.pivot(index="dia_semana", columns="periodo", values="quantidade")
        .fillna(0)
        .reindex(index=ordem_dias, columns=ordem_periodos, fill_value=0)
    )
    return pivot


@st.cache_data(ttl=300)
def _agg_comparativo(_key: tuple, df_small: pd.DataFrame, tipo_periodo: str, metrica: str) -> pd.DataFrame:
    """Agrupa por período (M/Q) para o comparativo."""
    dfp = _prepare_datas(_key, df_small)
    if dfp.empty:
        return pd.DataFrame()

    dt = dfp["data_solicitacao_dt"]
    if tipo_periodo == "Mensal":
        periodo = dt.dt.to_period("M").astype(str)
    else:
        periodo = dt.dt.to_period("Q").astype(str)

    if metrica == "Quantidade de Pedidos":
        agg = dfp.assign(periodo=periodo).groupby("periodo").size().reset_index(name="valor")
    else:
        if "valor_total" not in dfp.columns:
            dfp = dfp.assign(valor_total=0)
        agg = dfp.assign(periodo=periodo).groupby("periodo")["valor_total"].sum().reset_index(name="valor")

    return agg.sort_values("periodo")


# ----------------------------
# UI helpers (UX)
# ----------------------------

def _sidebar_filtros(df: pd.DataFrame) -> pd.DataFrame:
    """Filtros em form para evitar rerun a cada widget."""
    if df.empty:
        return df

    with st.sidebar:
        st.subheader("Filtros (Dashboard Avançado)")
        with st.form("filtros_dashboard_avancado"):
            fornecedores = ["Todos"]
            if "fornecedor" in df.columns:
                fornecedores += sorted([x for x in df["fornecedor"].dropna().unique().tolist() if str(x).strip() != ""])

            fornecedor = st.selectbox("Fornecedor", fornecedores, index=0)

            status_op = []
            if "status" in df.columns:
                status_op = sorted([x for x in df["status"].dropna().unique().tolist() if str(x).strip() != ""])
            status_sel = st.multiselect("Status", status_op)

            periodo = st.selectbox("Período", ["Tudo", "7 dias", "30 dias", "90 dias"], index=0)
            aplicar = st.form_submit_button("Aplicar")

    if aplicar:
        st.session_state["da_fornecedor"] = fornecedor
        st.session_state["da_status"] = status_sel
        st.session_state["da_periodo"] = periodo

    fornecedor = st.session_state.get("da_fornecedor", "Todos")
    status_sel = st.session_state.get("da_status", [])
    periodo = st.session_state.get("da_periodo", "Tudo")

    out = df
    if fornecedor != "Todos" and "fornecedor" in out.columns:
        out = out[out["fornecedor"] == fornecedor]

    if status_sel and "status" in out.columns:
        out = out[out["status"].isin(status_sel)]

    if periodo != "Tudo":
        col_data = "data_solicitacao"
        if col_data in out.columns:
            dias = {"7 dias": 7, "30 dias": 30, "90 dias": 90}[periodo]
            limite = pd.Timestamp.now().normalize() - pd.Timedelta(days=dias)
            ds = pd.to_datetime(out[col_data], errors="coerce")
            out = out[ds >= limite]

    return out


# ----------------------------
# Gráficos
# ----------------------------

def criar_grafico_evolucao_temporal(df_pedidos: pd.DataFrame, formatar_moeda_br):
    """Cria gráfico de linha com evolução de pedidos e valores ao longo do tempo."""
    st.subheader("📈 Evolução Temporal de Pedidos e Valores")

    if df_pedidos.empty or "data_solicitacao" not in df_pedidos.columns:
        st.info("📭 Dados insuficientes para gerar o gráfico de evolução temporal")
        return

    df_small = df_pedidos[["id", "data_solicitacao", "valor_total"]].copy() if "valor_total" in df_pedidos.columns else df_pedidos[["id", "data_solicitacao"]].assign(valor_total=0)
    key = _df_key(df_pedidos)
    df_agrupado = _agg_evolucao(key, df_small)

    if df_agrupado.empty:
        st.info("📭 Não há pedidos com data de solicitação válida")
        return

    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=df_agrupado["mes_ano"],
            y=df_agrupado["qtd"],
            name="Quantidade de Pedidos",
            mode="lines+markers",
            line=dict(width=4),
            marker=dict(size=8),
            yaxis="y",
            hovertemplate="<b>%{x}</b><br>Pedidos: %{y}<extra></extra>",
        )
    )

    fig.add_trace(
        go.Scatter(
            x=df_agrupado["mes_ano"],
            y=df_agrupado["valor_total"],
            name="Valor Total",
            mode="lines+markers",
            line=dict(width=4, dash="dot"),
            marker=dict(size=8),
            yaxis="y2",
            hovertemplate="<b>%{x}</b><br>Valor: %{y}<extra></extra>",
        )
    )

    fig.update_layout(
        xaxis=dict(title="Mês/Ano", tickangle=-45),
        yaxis=dict(title="Quantidade de Pedidos", side="left", showgrid=True, gridcolor="#2d3748"),
        yaxis2=dict(title="Valor Total (R$)", side="right", overlaying="y", showgrid=False),
        height=450,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=40, r=40, t=60, b=80),
    )

    st.plotly_chart(fig, use_container_width=True)


def criar_funil_conversao(df_pedidos: pd.DataFrame):
    """Cria gráfico de funil de conversão de pedidos."""
    st.subheader("🎯 Funil de Conversão de Pedidos")

    if df_pedidos.empty:
        st.info("📭 Dados insuficientes para gerar o funil")
        return

    # Evita criar múltiplos dataframes temporários
    status = df_pedidos["status"] if "status" in df_pedidos.columns else pd.Series([], dtype=str)
    entregue = df_pedidos["entregue"] if "entregue" in df_pedidos.columns else pd.Series([False] * len(df_pedidos))
    atrasado = df_pedidos["atrasado"] if "atrasado" in df_pedidos.columns else pd.Series([False] * len(df_pedidos))

    total_pedidos = int(len(df_pedidos))
    em_transito = int((status == "Em trânsito").sum()) if len(status) else 0
    entregues = int((entregue == True).sum())
    no_prazo = int(((entregue == True) & (atrasado == False)).sum())

    fig = go.Figure(
        go.Funnel(
            y=["Pedidos Realizados", "Em Trânsito", "Entregues", "Entregues no Prazo"],
            x=[total_pedidos, em_transito, entregues, no_prazo],
            textposition="inside",
            textinfo="value+percent initial",
            connector=dict(line=dict(width=2)),
        )
    )
    fig.update_layout(height=380, margin=dict(l=20, r=20, t=20, b=20))
    st.plotly_chart(fig, use_container_width=True)

    col1, col2, col3 = st.columns(3)
    with col1:
        taxa_entrega = (entregues / total_pedidos * 100) if total_pedidos else 0
        st.metric("Taxa de Entrega", f"{taxa_entrega:.1f}%".replace(".", ","))
    with col2:
        taxa_prazo = (no_prazo / entregues * 100) if entregues else 0
        st.metric("Entregas no Prazo", f"{taxa_prazo:.1f}%".replace(".", ","))
    with col3:
        taxa_transito = (em_transito / total_pedidos * 100) if total_pedidos else 0
        st.metric("Em Trânsito", f"{taxa_transito:.1f}%".replace(".", ","))


def criar_heatmap_pedidos(df_pedidos: pd.DataFrame):
    """Cria heatmap de pedidos por dia da semana e período."""
    st.subheader("🔥 Mapa de Calor - Pedidos por Dia e Período")

    if df_pedidos.empty or "data_solicitacao" not in df_pedidos.columns:
        st.info("📭 Dados insuficientes para gerar o mapa de calor")
        return

    df_small = df_pedidos[["data_solicitacao"]].copy()
    key = _df_key(df_pedidos)
    pivot = _agg_heatmap(key, df_small)

    if pivot.empty:
        st.info("📭 Não há pedidos com data de solicitação válida")
        return

    fig = go.Figure(
        data=go.Heatmap(
            z=pivot.values,
            x=pivot.columns,
            y=pivot.index,
            colorscale="Purples",
            text=pivot.values,
            texttemplate="%{text}",
            hovertemplate="<b>%{y}</b><br>%{x}<br>Pedidos: %{z}<extra></extra>",
        )
    )
    fig.update_layout(height=420, margin=dict(l=20, r=20, t=20, b=20))
    st.plotly_chart(fig, use_container_width=True)


def criar_comparativo_periodos(df_pedidos: pd.DataFrame, formatar_moeda_br):
    """Cria comparativo entre períodos (mensal/trimestral)."""
    st.subheader("📊 Comparativo de Períodos")

    if df_pedidos.empty or "data_solicitacao" not in df_pedidos.columns:
        st.info("📭 Dados insuficientes para gerar o comparativo de períodos")
        return

    col1, col2 = st.columns(2)
    with col1:
        tipo_periodo = st.selectbox("Selecione o período:", ["Mensal", "Trimestral"], key="periodo_comparativo")
    with col2:
        metrica = st.selectbox("Métrica:", ["Quantidade de Pedidos", "Valor Total"], key="metrica_comparativo")

    cols = ["data_solicitacao", "id"]
    if "valor_total" in df_pedidos.columns:
        cols.append("valor_total")
    df_small = df_pedidos[cols].copy()
    key = _df_key(df_pedidos)

    df_agrupado = _agg_comparativo(key, df_small, tipo_periodo, metrica)
    if df_agrupado.empty:
        st.info("📭 Não há pedidos com data de solicitação válida")
        return

    titulo_y = "Quantidade de Pedidos" if metrica == "Quantidade de Pedidos" else "Valor Total (R$)"

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=df_agrupado["periodo"],
            y=df_agrupado["valor"],
            text=df_agrupado["valor"].apply(
                lambda x: formatar_moeda_br(x) if metrica == "Valor Total" else f"{int(x)}"
            ),
            textposition="outside",
            hovertemplate="<b>%{x}</b><br>" + titulo_y + ": %{text}<extra></extra>",
        )
    )

    media = float(df_agrupado["valor"].mean()) if not df_agrupado.empty else 0
    fig.add_hline(
        y=media,
        line_dash="dash",
        annotation_text=f"Média: {formatar_moeda_br(media) if metrica == 'Valor Total' else f'{int(media)}'}",
        annotation_position="right",
    )

    fig.update_layout(height=460, showlegend=False, margin=dict(l=20, r=20, t=20, b=60))
    st.plotly_chart(fig, use_container_width=True)

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("📈 Máximo", formatar_moeda_br(df_agrupado["valor"].max()) if metrica == "Valor Total" else f"{int(df_agrupado['valor'].max())}")
    with col2:
        st.metric("📉 Mínimo", formatar_moeda_br(df_agrupado["valor"].min()) if metrica == "Valor Total" else f"{int(df_agrupado['valor'].min())}")
    with col3:
        st.metric("📊 Média", formatar_moeda_br(media) if metrica == "Valor Total" else f"{int(media)}")
    with col4:
        desvio = float(df_agrupado["valor"].std()) if len(df_agrupado) > 1 else 0.0
        st.metric("📏 Desvio Padrão", formatar_moeda_br(desvio) if metrica == "Valor Total" else f"{int(desvio)}")


def exibir_dashboard_avancado(df_pedidos: pd.DataFrame, formatar_moeda_br):
    """Exibe o dashboard avançado completo."""
    st.title("📊 Dashboard Avançado")

    if df_pedidos.empty:
        st.info("📭 Nenhum pedido cadastrado ainda")
        return

    # UX: filtros no sidebar sem rerun a cada mudança
    df_view = _sidebar_filtros(df_pedidos)

    # UX: separa em abas para reduzir scroll e dar organização
    tab1, tab2, tab3, tab4 = st.tabs(["📈 Evolução", "🎯 Funil", "🔥 Heatmap", "📊 Comparativo"])

    with tab1:
        criar_grafico_evolucao_temporal(df_view, formatar_moeda_br)

    with tab2:
        criar_funil_conversao(df_view)

    with tab3:
        criar_heatmap_pedidos(df_view)

    with tab4:
        criar_comparativo_periodos(df_view, formatar_moeda_br)
