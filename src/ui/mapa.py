"""Tela: Mapa geográfico."""
from __future__ import annotations

import streamlit as st

import mapa_geografico as mg
from src.repositories.pedidos import carregar_pedidos

def exibir_mapa(_supabase):
    """Exibe mapa geográfico REAL dos fornecedores com mapa coroplético do Brasil"""
    
    st.title("🗺️ Mapa Geográfico de Fornecedores")
    
    df_pedidos = carregar_pedidos(_supabase)
    
    if df_pedidos.empty:
        st.info("📭 Nenhum pedido cadastrado ainda")
        return
    
    # Filtros
    st.markdown("### 🔍 Filtros")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        status_filtro = st.multiselect(
            "Status",
            options=df_pedidos['status'].unique(),
            default=df_pedidos['status'].unique()
        )
    
    with col2:
        apenas_pendentes = st.checkbox("Apenas pedidos pendentes", value=False)
    
    with col3:
        departamento_filtro = st.selectbox(
            "Departamento",
            options=['Todos'] + sorted(df_pedidos['departamento'].dropna().unique().tolist())
        )
    
    # Aplicar filtros
    df_filtrado = df_pedidos[df_pedidos['status'].isin(status_filtro)]
    
    if apenas_pendentes:
        df_filtrado = df_filtrado[df_filtrado['entregue'] == False]
    
    if departamento_filtro != 'Todos':
        df_filtrado = df_filtrado[df_filtrado['departamento'] == departamento_filtro]
    
    st.markdown("---")
    
    # Criar abas para diferentes visualizações
    tab1, tab2 = st.tabs(["🗺️ Mapa de Estados", "📍 Mapa de Fornecedores"])
    
    with tab1:
        # Mapa Coroplético dos Estados
        try:
            fig_coropletico, df_estados = mg.criar_mapa_coropletico_estados(df_filtrado)
            
            if fig_coropletico is not None:
                # Métricas dos estados
                mg.exibir_metricas_estados(df_estados)
                
                st.markdown("---")
                
                st.plotly_chart(fig_coropletico, use_container_width=True)
                
                st.markdown("---")
                
                # Gráficos de análise
                mg.criar_graficos_analise(df_estados)
                
                st.markdown("---")
                
                # Tabela detalhada
                mg.criar_tabela_detalhada(df_estados)
            else:
                st.warning("⚠️ Não foi possível criar o mapa de estados")
                
        except Exception as e:
            st.error(f"Erro ao criar mapa coroplético: {e}")
            st.info("💡 Tente ajustar os filtros ou verifique se há dados de fornecedores disponíveis")
    
    with tab2:
        # Mapa com marcadores de fornecedores
        try:
            fig_mapa, df_fornecedores = mg.criar_mapa_fornecedores(df_filtrado)
            
            if fig_mapa is not None and df_fornecedores is not None:
                # Estatísticas
                mg.exibir_estatisticas_mapa(df_fornecedores)
                
                st.markdown("---")
                
                # Mapa com marcadores
                st.plotly_chart(fig_mapa, use_container_width=True)
                
                st.markdown("---")
                
                # Ranking de fornecedores
                mg.criar_ranking_fornecedores(df_fornecedores)
            else:
                st.warning("⚠️ Não foi possível criar o mapa de fornecedores")
                
        except Exception as e:
            st.error(f"Erro ao criar mapa de fornecedores: {e}")
            st.info("💡 Tente ajustar os filtros ou verifique se há dados de fornecedores disponíveis")

# ============================================
# PÁGINA DE CONSULTA DE PEDIDOS
# ============================================

