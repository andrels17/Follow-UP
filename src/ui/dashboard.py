"""Tela: Dashboard."""
from __future__ import annotations

from datetime import datetime, timedelta

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

import dashboard_avancado as da
import exportacao_relatorios as er
import filtros_avancados as fa
import backup_auditoria as ba

from src.repositories.pedidos import carregar_pedidos, carregar_estatisticas_departamento
from src.repositories.fornecedores import carregar_fornecedores
from src.utils.formatting import formatar_moeda_br, formatar_numero_br

def exibir_dashboard(_supabase):
    """Exibe dashboard principal com KPIs e gráficos"""
    
    st.title("📊 Dashboard de Follow-up")
    
    # Carregar dados
    df_pedidos = carregar_pedidos(_supabase)
    
    if df_pedidos.empty:
        st.info("📭 Nenhum pedido cadastrado ainda")
        return
    
    # Botão de diagnóstico (temporário para debug) - COMENTADO
    # if st.button("🔍 Diagnosticar Problema de Datas"):
    #     diagnostico_datas.diagnosticar_datas(df_pedidos)
    
    # Calcular alertas
    alertas = sa.calcular_alertas(df_pedidos)
    
    # Exibir resumo de alertas
    if alertas['total'] > 0:
        sa.exibir_resumo_alertas_dashboard(alertas)
        st.markdown("---")
    
    # KPIs no topo
    col1, col2, col3, col4, col5 = st.columns(5)
    
    total_pedidos = len(df_pedidos)
    pedidos_entregues = len(df_pedidos[df_pedidos['entregue'] == True])
    pedidos_pendentes = len(df_pedidos[df_pedidos['entregue'] == False])
    pedidos_atrasados = len(df_pedidos[df_pedidos['atrasado'] == True])
    taxa_entrega = (pedidos_entregues / total_pedidos * 100) if total_pedidos > 0 else 0
    
    with col1:
        st.metric("📦 Total de Pedidos", formatar_numero_br(total_pedidos).split(',')[0])
    
    with col2:
        st.metric("✅ Entregues", formatar_numero_br(pedidos_entregues).split(',')[0], 
                 delta=f"{taxa_entrega:.1f}%".replace('.', ','))
    
    with col3:
        st.metric("⏳ Pendentes", formatar_numero_br(pedidos_pendentes).split(',')[0])
    
    with col4:
        st.metric("⚠️ Atrasados", formatar_numero_br(pedidos_atrasados).split(',')[0],
                 delta=f"-{pedidos_atrasados}" if pedidos_atrasados > 0 else "0",
                 delta_color="inverse")
    
    with col5:
        valor_total = df_pedidos['valor_total'].sum()
        st.metric("💰 Valor Total", formatar_moeda_br(valor_total))
    
    st.markdown("---")
    
    # Abas para diferentes visualizações
    tab1, tab2, tab3 = st.tabs(["📊 Visão Geral", "📈 Dashboard Avançado", "📥 Exportação"])
    
    with tab1:
        # Gráficos originais
        col1, col2 = st.columns(2)
        
        with col1:
            # Gráfico de status
            st.subheader("📈 Pedidos por Status")
            status_counts = df_pedidos['status'].value_counts()
            fig_status = px.pie(
                values=status_counts.values,
                names=status_counts.index,
                hole=0.4,
                color_discrete_sequence=px.colors.qualitative.Set3
            )
            fig_status.update_traces(textposition='inside', textinfo='percent+label')
            st.plotly_chart(fig_status, use_container_width=True)
        
        with col2:
            # Gráfico de departamentos
            st.subheader("🏢 Pedidos por Departamento")
            dept_counts = (
                df_pedidos["departamento"]
                .dropna()
                .astype(str)
                .str.strip()
                .loc[lambda s: s != ""]
                .value_counts()
                .head(10)
            )
            fig_dept = px.bar(
                x=dept_counts.values,
                y=dept_counts.index,
                orientation='h',
                color=dept_counts.values,
                color_continuous_scale='Blues'
            )
            fig_dept.update_layout(showlegend=False, xaxis_title="Quantidade", yaxis_title="")
            st.plotly_chart(fig_dept, use_container_width=True)
        
        # Timeline de entregas
        st.subheader("📅 Timeline de Entregas Previstas")
        
        df_timeline = df_pedidos[df_pedidos['entregue'] == False].copy()
        if not df_timeline.empty:
            df_timeline = df_timeline.sort_values('previsao_entrega')
            df_timeline_grouped = df_timeline.groupby('previsao_entrega').size().reset_index(name='quantidade')
            
            fig_timeline = px.line(
                df_timeline_grouped,
                x='previsao_entrega',
                y='quantidade',
                markers=True,
                title="Entregas previstas nos próximos dias"
            )
            fig_timeline.update_traces(line_color='#1f77b4', marker_size=8)
            st.plotly_chart(fig_timeline, use_container_width=True)
        else:
            st.success("✅ Todos os pedidos foram entregues!")
        
        # Tabela de pedidos atrasados
        if pedidos_atrasados > 0:
            st.subheader("⚠️ Pedidos Atrasados")
            df_atrasados = df_pedidos[df_pedidos['atrasado'] == True][
                ['nr_oc', 'descricao', 'departamento', 'fornecedor_nome', 'previsao_entrega', 'valor_total']
            ].sort_values('previsao_entrega').copy()
            
            # Formatar valor total no padrão brasileiro
            df_atrasados['valor_total_formatado'] = df_atrasados['valor_total'].apply(formatar_moeda_br)
            
            st.dataframe(
                df_atrasados[['nr_oc', 'descricao', 'departamento', 'fornecedor_nome', 'previsao_entrega', 'valor_total_formatado']],
                use_container_width=True,
                hide_index=True,
                column_config={
                    "nr_oc": "N° OC",
                    "descricao": "Descrição",
                    "departamento": "Departamento",
                    "fornecedor_nome": "Fornecedor",
                    "previsao_entrega": st.column_config.DateColumn("Previsão", format="DD/MM/YYYY"),
                    "valor_total_formatado": "Valor Total"
                }
            )
    
    with tab2:
        # Dashboard avançado
        da.exibir_dashboard_avancado(df_pedidos, formatar_moeda_br)
    
    with tab3:
        # Exportação de dados
        st.subheader("📥 Exportação de Relatórios")
        
        tipo_relatorio = st.selectbox(
            "Selecione o tipo de relatório:",
            ["Relatório Completo", "Relatório Executivo", "Por Fornecedor", "Por Departamento"]
        )
        
        if tipo_relatorio == "Relatório Completo":
            er.gerar_botoes_exportacao(df_pedidos, formatar_moeda_br)
        
        elif tipo_relatorio == "Relatório Executivo":
            er.criar_relatorio_executivo(df_pedidos, formatar_moeda_br)
        
        elif tipo_relatorio == "Por Fornecedor":
            fornecedor = st.selectbox(
                "Selecione o fornecedor:",
                sorted(df_pedidos['fornecedor_nome'].dropna().unique())
            )
            if fornecedor:
                er.gerar_relatorio_fornecedor(df_pedidos, fornecedor, formatar_moeda_br)
        
        elif tipo_relatorio == "Por Departamento":
            if "departamento" not in df_pedidos.columns:
                st.error("Coluna 'departamento' não encontrada nos dados.")
                st.caption(f"Colunas disponíveis: {list(df_pedidos.columns)}")
                return
        
            departamentos = (
                df_pedidos["departamento"]
                .dropna()
                .astype(str)
                .str.strip()
                .loc[lambda s: s != ""]
                .unique()
                .tolist()
            )
            departamentos = sorted(departamentos)
        
            departamento = st.selectbox(
                "Selecione o departamento:",
                departamentos
            )
        
            if departamento:
                er.gerar_relatorio_departamento(df_pedidos, departamento, formatar_moeda_br)


# ============================================
# PÁGINA DE MAPA GEOGRÁFICO (NOVA VERSÃO)
# ============================================

