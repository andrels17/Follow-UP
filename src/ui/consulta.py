"""Tela: Consultar pedidos."""
from __future__ import annotations

from datetime import datetime

import pandas as pd
import plotly.express as px
import streamlit as st

import exportacao_relatorios as er
import filtros_avancados as fa

from src.repositories.pedidos import carregar_pedidos
from src.utils.formatting import formatar_moeda_br, formatar_numero_br

def exibir_consulta_pedidos(_supabase):
    """Exibe página de consulta e filtros de pedidos"""
    
    st.title("🔍 Consultar Pedidos")
    
    df_pedidos = carregar_pedidos(_supabase)
    
    if df_pedidos.empty:
        st.info("📭 Nenhum pedido cadastrado ainda")
        return
    
    # Filtros laterais
    with st.sidebar:
        st.subheader("🔎 Filtros")
        
        # Filtro de texto
        busca = st.text_input("🔍 Buscar", placeholder="N° OC, Descrição, Fornecedor...")
        
        # Filtro de departamento
        departamentos = ['Todos'] + sorted(df_pedidos['departamento'].dropna().unique().tolist())
        dept_selecionado = st.selectbox("🏢 Departamento", departamentos)
        
        # Filtro de status
        status_opcoes = ['Todos'] + sorted(df_pedidos['status'].dropna().unique().tolist())
        status_selecionado = st.selectbox("📊 Status", status_opcoes)
        
        # Filtro de entrega
        entrega_filtro = st.radio("📦 Situação", ["Todos", "Pendentes", "Entregues", "Atrasados"])
        
        # Filtro de data
        st.markdown("---")
        filtrar_data = st.checkbox("Filtrar por período")
        if filtrar_data:
            data_inicio = st.date_input("Data início", value=datetime.now() - timedelta(days=30))
            data_fim = st.date_input("Data fim", value=datetime.now())
        
        # Botão limpar filtros
        if st.button("🔄 Limpar Filtros"):
            st.rerun()
    
    # Aplicar filtros
    df_filtrado = df_pedidos.copy()
    
    if busca:
        mask = (
            df_filtrado['nr_oc'].astype(str).str.contains(busca, case=False, na=False) |
            df_filtrado['descricao'].astype(str).str.contains(busca, case=False, na=False) |
            df_filtrado['fornecedor_nome'].astype(str).str.contains(busca, case=False, na=False)
        )
        df_filtrado = df_filtrado[mask]
    
    if dept_selecionado != 'Todos':
        df_filtrado = df_filtrado[df_filtrado['departamento'] == dept_selecionado]
    
    if status_selecionado != 'Todos':
        df_filtrado = df_filtrado[df_filtrado['status'] == status_selecionado]
    
    if entrega_filtro == "Pendentes":
        df_filtrado = df_filtrado[df_filtrado['entregue'] == False]
    elif entrega_filtro == "Entregues":
        df_filtrado = df_filtrado[df_filtrado['entregue'] == True]
    elif entrega_filtro == "Atrasados":
        df_filtrado = df_filtrado[df_filtrado['atrasado'] == True]
    
    if filtrar_data and 'data_inicio' in locals() and 'data_fim' in locals():
        df_filtrado = df_filtrado[
            (df_filtrado['data_solicitacao'] >= pd.to_datetime(data_inicio)) &
            (df_filtrado['data_solicitacao'] <= pd.to_datetime(data_fim))
        ]
    
    # Exibir resultados
    st.info(f"📊 {len(df_filtrado)} pedidos encontrados")
    
    # Detalhes do pedido selecionado (MOVIDO PARA CIMA)
    if not df_filtrado.empty:
        st.markdown("---")
        st.subheader("📋 Detalhes do Pedido")
        
        # Busca aprimorada por pedido
        col_busca1, col_busca2 = st.columns([3, 1])
        
        with col_busca1:
            busca_pedido = st.text_input(
                "🔍 Buscar pedido por N° OC, Descrição ou Fornecedor",
                placeholder="Digite para buscar...",
                key="busca_detalhes_pedido"
            )
        
        with col_busca2:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("🔄 Limpar Busca", key="limpar_busca_detalhes"):
                st.rerun()
        
        # Filtrar pedidos para o selectbox
        df_para_selecao = df_filtrado.copy()
        if busca_pedido:
            mascara_busca = (
                df_para_selecao['nr_oc'].astype(str).str.contains(busca_pedido, case=False, na=False) |
                df_para_selecao['descricao'].astype(str).str.contains(busca_pedido, case=False, na=False) |
                df_para_selecao['fornecedor_nome'].astype(str).str.contains(busca_pedido, case=False, na=False)
            )
            df_para_selecao = df_para_selecao[mascara_busca]
            
            if df_para_selecao.empty:
                st.warning(f"⚠️ Nenhum pedido encontrado com '{busca_pedido}'")
                df_para_selecao = df_filtrado.copy()
        
        pedido_selecionado = st.selectbox(
            "Selecione um pedido para ver detalhes:",
            options=df_para_selecao['id'].tolist(),
            format_func=lambda x: f"OC: {df_para_selecao[df_para_selecao['id']==x]['nr_oc'].values[0]} - {df_para_selecao[df_para_selecao['id']==x]['descricao'].values[0][:50]}",
            key="select_pedido_detalhes"
        )
        
        if pedido_selecionado:
            pedido_info = df_filtrado[df_filtrado['id'] == pedido_selecionado].iloc[0]
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown(f"""
                **N° Solicitação:** {pedido_info['nr_solicitacao']}  
                **N° OC:** {pedido_info['nr_oc']}  
                **Departamento:** {pedido_info['departamento']}  
                **Equipamento:** {pedido_info['cod_equipamento']}  
                **Código Material:** {pedido_info['cod_material']}  
                **Descrição:** {pedido_info['descricao']}
                """)
            
            with col2:
                st.markdown(f"""
                **Fornecedor:** {pedido_info['fornecedor_nome']}  
                **Cidade/UF:** {pedido_info['fornecedor_cidade']}/{pedido_info['fornecedor_uf']}  
                **Data Solicitação:** {pedido_info['data_solicitacao'].strftime('%d/%m/%Y') if pd.notna(pedido_info['data_solicitacao']) else 'N/A'}  
                **Previsão Entrega:** {pedido_info['previsao_entrega'].strftime('%d/%m/%Y') if pd.notna(pedido_info['previsao_entrega']) else 'N/A'}  
                **Status:** {pedido_info['status']}  
                **Valor Total:** {formatar_moeda_br(pedido_info['valor_total'])}
                """)
            
            # Barra de progresso
            progresso = (pedido_info['qtde_entregue'] / pedido_info['qtde_solicitada'] * 100) if pedido_info['qtde_solicitada'] > 0 else 0
            st.progress(progresso / 100)
            
            # Formatação das quantidades com padrão brasileiro
            qtde_sol_formatada = formatar_numero_br(pedido_info['qtde_solicitada'])
            qtde_ent_formatada = formatar_numero_br(pedido_info['qtde_entregue'])
            st.caption(f"Entregue: {qtde_ent_formatada} / {qtde_sol_formatada} ({progresso:.1f}%)")
        
        st.markdown("---")
    
    # Botão de exportação
    col1, col2, col3 = st.columns([2, 1, 1])
    with col3:
        if st.button("📥 Exportar para Excel"):
            # Preparar dados para exportação
            df_export = df_filtrado[[
                'nr_oc', 'nr_solicitacao', 'departamento', 'descricao', 
                'qtde_solicitada', 'qtde_entregue', 'qtde_pendente',
                'status', 'fornecedor_nome', 'fornecedor_cidade', 'fornecedor_uf',
                'data_solicitacao', 'previsao_entrega', 'valor_total'
            ]].copy()
            
            # Converter para CSV
            csv = df_export.to_csv(index=False, encoding='utf-8-sig', decimal=',', sep=';')
            st.download_button(
                label="💾 Download CSV",
                data=csv,
                file_name=f"pedidos_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )
    
    # Tabela de pedidos (MOVIDA PARA BAIXO)
    st.subheader("📊 Lista de Pedidos")
    
    # Preparar DataFrame com formatação brasileira para exibição
    df_display = df_filtrado.copy()
    df_display['valor_total_formatado'] = df_display['valor_total'].apply(formatar_moeda_br)
    df_display['qtde_solicitada_formatada'] = df_display['qtde_solicitada'].apply(formatar_numero_br)
    df_display['qtde_entregue_formatada'] = df_display['qtde_entregue'].apply(formatar_numero_br)
    df_display['qtde_pendente_formatada'] = df_display['qtde_pendente'].apply(formatar_numero_br)
    
    st.dataframe(
        df_display[[
            'nr_oc', 'descricao', 'departamento', 'fornecedor_nome',
            'qtde_solicitada_formatada', 'qtde_entregue_formatada', 'qtde_pendente_formatada',
            'previsao_entrega', 'status', 'valor_total_formatado'
        ]],
        use_container_width=True,
        hide_index=True,
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
            "valor_total_formatado": "Valor Total"
        }
    )

# ============================================
# PÁGINA DE GESTÃO DE PEDIDOS (ADMIN)
# ============================================

