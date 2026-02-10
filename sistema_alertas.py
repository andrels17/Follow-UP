"""
Sistema de Alertas (MVP)
- Calcula alertas de pedidos atrasados / próximos do vencimento
- Exibe badges e painéis no Streamlit

Obs: Este módulo existe para compatibilidade com a versão modularizada.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Dict, Any

import pandas as pd
import streamlit as st


def _to_date(series: pd.Series) -> pd.Series:
    """Converte série para datetime.date quando possível."""
    if series is None:
        return series
    s = pd.to_datetime(series, errors="coerce")
    return s.dt.date


def calcular_alertas(df_pedidos: pd.DataFrame, dias_antecedencia: int = 3) -> Dict[str, Any]:
    """
    Retorna dict com contadores e subconjuntos úteis.
    Espera colunas comuns:
      - entregue (bool)
      - atrasado (bool) (opcional; se não houver, calculamos)
      - previsao_entrega (date/datetime/str)
    """
    if df_pedidos is None or df_pedidos.empty:
        return {"total": 0, "atrasados": 0, "vence_em_breve": 0, "df_atrasados": pd.DataFrame(), "df_vence": pd.DataFrame()}

    df = df_pedidos.copy()

    # Normalizar colunas esperadas
    if "entregue" not in df.columns:
        df["entregue"] = False

    if "previsao_entrega" in df.columns:
        prev = _to_date(df["previsao_entrega"])
    else:
        prev = pd.Series([pd.NaT] * len(df))
    hoje = date.today()

    # atrasado: se não existir, calcular
    if "atrasado" not in df.columns:
        df["atrasado"] = False
        mask_prev = prev.notna()
        df.loc[mask_prev, "atrasado"] = (prev[mask_prev] < hoje) & (df.loc[mask_prev, "entregue"] == False)

    df["__prev_date"] = prev

    df_pendentes = df[df["entregue"] == False].copy()

    df_atrasados = df_pendentes[df_pendentes["atrasado"] == True].copy()
    lim = hoje + timedelta(days=int(dias_antecedencia))
    df_vence = df_pendentes[(df_pendentes["atrasado"] == False) & (df_pendentes["__prev_date"].notna()) & (df_pendentes["__prev_date"] <= lim)].copy()

    return {
        "total": int(len(df_atrasados) + len(df_vence)),
        "atrasados": int(len(df_atrasados)),
        "vence_em_breve": int(len(df_vence)),
        "df_atrasados": df_atrasados.drop(columns=["__prev_date"], errors="ignore"),
        "df_vence": df_vence.drop(columns=["__prev_date"], errors="ignore"),
    }


def exibir_badge_alertas(alertas: Dict[str, Any]) -> None:
    """Badge compacto para sidebar."""
    total = int(alertas.get("total", 0))
    if total <= 0:
        st.success("✅ Sem alertas")
        return
    st.error(f"🔔 {total} alerta(s) ativo(s)")
    a = int(alertas.get("atrasados", 0))
    b = int(alertas.get("vence_em_breve", 0))
    st.caption(f"⚠️ Atrasados: {a}  •  ⏳ Vencem em breve: {b}")


def exibir_resumo_alertas_dashboard(alertas: Dict[str, Any]) -> None:
    """Resumo no topo do dashboard."""
    total = int(alertas.get("total", 0))
    if total <= 0:
        return
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("🔔 Alertas", total)
    with col2:
        st.metric("⚠️ Atrasados", int(alertas.get("atrasados", 0)))
    with col3:
        st.metric("⏳ Vencem em breve", int(alertas.get("vence_em_breve", 0)))


def exibir_painel_alertas(alertas: Dict[str, Any], formatar_moeda_fn=None) -> None:
    """Página de alertas (simples)."""
    st.title("🔔 Alertas e Notificações")

    total = int(alertas.get("total", 0))
    if total == 0:
        st.success("✅ Nenhum alerta no momento")
        return

    st.subheader("⚠️ Atrasados")
    df_a = alertas.get("df_atrasados", pd.DataFrame())
    if df_a is not None and not df_a.empty:
        _render_df_alerta(df_a, formatar_moeda_fn)
    else:
        st.info("Nenhum pedido atrasado.")

    st.subheader("⏳ Vencem em breve")
    df_v = alertas.get("df_vence", pd.DataFrame())
    if df_v is not None and not df_v.empty:
        _render_df_alerta(df_v, formatar_moeda_fn)
    else:
        st.info("Nenhum pedido vencendo em breve.")


def _render_df_alerta(df: pd.DataFrame, formatar_moeda_fn=None) -> None:
    cols_pref = [c for c in ["nr_oc","descricao","departamento","fornecedor_nome","previsao_entrega","valor_total","status"] if c in df.columns]
    view = df[cols_pref].copy() if cols_pref else df.copy()
    if "valor_total" in view.columns and formatar_moeda_fn:
        view["valor_total"] = view["valor_total"].apply(lambda x: formatar_moeda_fn(x))
    st.dataframe(view, use_container_width=True, hide_index=True)
