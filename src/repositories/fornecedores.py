"""Repositório de dados: fornecedores (Supabase)."""
import pandas as pd
import streamlit as st

@st.cache_data(ttl=300)
def carregar_fornecedores(_supabase):
    """Carrega lista de fornecedores"""
    try:
        resultado = _supabase.table('fornecedores').select('*').eq('ativo', True).execute()
        if resultado.data:
            return pd.DataFrame(resultado.data)
        return pd.DataFrame()
    except Exception as e:
        st.error(f"Erro ao carregar fornecedores: {e}")
        return pd.DataFrame()

