"""
Mapa Geográfico (MVP)

Fornece funções usadas por src/ui/mapa.py.
Implementações simplificadas para manter a página funcionando.
"""
from __future__ import annotations
import pandas as pd
import streamlit as st
import plotly.express as px


def exibir_estatisticas_mapa(df: pd.DataFrame) -> None:
    st.subheader("📊 Estatísticas")
    if df is None or df.empty:
        st.info("Sem dados.")
        return
    st.metric("Pedidos", len(df))
    if "valor_total" in df.columns:
        st.metric("Valor total", float(pd.to_numeric(df["valor_total"], errors="coerce").fillna(0).sum()))


def exibir_metricas_estados(df: pd.DataFrame) -> None:
    # se houver coluna estado
    if df is None or df.empty or "estado" not in df.columns:
        return
    st.subheader("🗺️ Estados")
    vc = df["estado"].value_counts().head(10)
    st.dataframe(vc.reset_index().rename(columns={"index":"Estado","estado":"Qtde"}), use_container_width=True, hide_index=True)


def criar_mapa_fornecedores(df: pd.DataFrame) -> None:
    st.subheader("📍 Fornecedores (MVP)")
    st.info("Para mapa real, inclua lat/long ou município/UF no cadastro do fornecedor.")
    # gráfico por estado se existir
    if df is not None and not df.empty and "estado" in df.columns:
        vc = df["estado"].value_counts().reset_index()
        vc.columns = ["estado", "qtd"]
        fig = px.bar(vc, x="estado", y="qtd", title="Pedidos por estado")
        st.plotly_chart(fig, use_container_width=True)


def criar_mapa_coropletico_estados(df: pd.DataFrame) -> None:
    st.subheader("🇧🇷 Coroplético (MVP)")
    st.info("Para coroplético real, precisamos de UF padronizada na coluna 'estado'.")


def criar_ranking_fornecedores(df: pd.DataFrame) -> None:
    st.subheader("🏆 Ranking de Fornecedores")
    if df is None or df.empty or "fornecedor_nome" not in df.columns:
        st.info("Sem dados para ranking.")
        return
    top = df["fornecedor_nome"].value_counts().head(10)
    fig = px.bar(x=top.values, y=top.index, orientation="h", title="Top 10 fornecedores (qtde de pedidos)")
    st.plotly_chart(fig, use_container_width=True)


def criar_graficos_analise(df: pd.DataFrame) -> None:
    st.subheader("📈 Análises")
    if df is None or df.empty:
        st.info("Sem dados.")
        return
    if "status" in df.columns:
        s = df["status"].value_counts().reset_index()
        s.columns = ["status","qtd"]
        fig = px.pie(s, values="qtd", names="status", title="Pedidos por status")
        st.plotly_chart(fig, use_container_width=True)


def criar_tabela_detalhada(df: pd.DataFrame) -> None:
    st.subheader("📋 Detalhes")
    if df is None or df.empty:
        st.info("Sem dados.")
        return
    st.dataframe(df.head(500), use_container_width=True, hide_index=True)
