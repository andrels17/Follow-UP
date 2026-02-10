"""
Exportação de Relatórios (MVP)

Fornece funções chamadas pela UI:
- gerar_botoes_exportacao
- criar_relatorio_executivo
- gerar_relatorio_fornecedor
- gerar_relatorio_departamento
"""
from __future__ import annotations

from datetime import datetime
import io
import pandas as pd
import streamlit as st


def _to_csv_bytes(df: pd.DataFrame) -> bytes:
    return df.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")


def gerar_botoes_exportacao(df: pd.DataFrame, formatar_moeda_fn=None) -> None:
    st.caption("Exportação rápida (CSV).")
    if df is None or df.empty:
        st.info("Nada para exportar.")
        return
    st.download_button(
        "📄 Baixar CSV (completo)",
        data=_to_csv_bytes(df),
        file_name=f"relatorio_completo_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
        mime="text/csv",
        use_container_width=True,
    )


def criar_relatorio_executivo(df: pd.DataFrame, formatar_moeda_fn=None) -> None:
    st.caption("Relatório executivo (resumo).")
    if df is None or df.empty:
        st.info("Nada para exportar.")
        return

    cols = [c for c in ["status","departamento","fornecedor_nome","valor_total","previsao_entrega","entregue","atrasado"] if c in df.columns]
    view = df[cols].copy() if cols else df.copy()

    st.dataframe(view.head(200), use_container_width=True, hide_index=True)
    st.download_button(
        "📄 Baixar CSV (executivo)",
        data=_to_csv_bytes(view),
        file_name=f"relatorio_executivo_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
        mime="text/csv",
        use_container_width=True,
    )


def gerar_relatorio_fornecedor(df: pd.DataFrame, fornecedor: str, formatar_moeda_fn=None) -> None:
    if df is None or df.empty:
        st.info("Nada para exportar.")
        return
    sub = df[df.get("fornecedor_nome") == fornecedor].copy() if "fornecedor_nome" in df.columns else pd.DataFrame()
    if sub.empty:
        st.info("Sem dados para o fornecedor selecionado.")
        return
    st.dataframe(sub.head(200), use_container_width=True, hide_index=True)
    st.download_button(
        f"📄 Baixar CSV ({fornecedor})",
        data=_to_csv_bytes(sub),
        file_name=f"relatorio_fornecedor_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
        mime="text/csv",
        use_container_width=True,
    )


def gerar_relatorio_departamento(df: pd.DataFrame, departamento: str, formatar_moeda_fn=None) -> None:
    if df is None or df.empty:
        st.info("Nada para exportar.")
        return
    sub = df[df.get("departamento") == departamento].copy() if "departamento" in df.columns else pd.DataFrame()
    if sub.empty:
        st.info("Sem dados para o departamento selecionado.")
        return
    st.dataframe(sub.head(200), use_container_width=True, hide_index=True)
    st.download_button(
        f"📄 Baixar CSV ({departamento})",
        data=_to_csv_bytes(sub),
        file_name=f"relatorio_departamento_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
        mime="text/csv",
        use_container_width=True,
    )
