"""
Dashboard Avançado (stub/MVP)

Este módulo existia na versão anterior. Aqui mantemos compatibilidade:
- exibir_dashboard_avancado(df_pedidos, formatar_moeda_fn)

Você pode evoluir depois com análises mais complexas.
"""
from __future__ import annotations
import pandas as pd
import streamlit as st
import plotly.express as px


def exibir_dashboard_avancado(df_pedidos: pd.DataFrame, formatar_moeda_fn=None) -> None:
    st.subheader("📈 Dashboard Avançado (MVP)")

    if df_pedidos is None or df_pedidos.empty:
        st.info("Sem dados para análise.")
        return

    # Exemplo simples: valor por fornecedor (top 10)
    if "fornecedor_nome" in df_pedidos.columns and "valor_total" in df_pedidos.columns:
        top = df_pedidos.groupby("fornecedor_nome", dropna=True)["valor_total"].sum().sort_values(ascending=False).head(10).reset_index()
        fig = px.bar(top, x="valor_total", y="fornecedor_nome", orientation="h", title="Top 10 fornecedores por valor")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.caption("Colunas 'fornecedor_nome' e 'valor_total' não encontradas para a visão avançada.")
