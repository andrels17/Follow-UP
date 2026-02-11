"""Tela: Ficha de material."""
from __future__ import annotations

import streamlit as st
import pandas as pd
import ficha_material as fm
from src.repositories.pedidos import carregar_pedidos
from src.utils.formatting import formatar_moeda_br

def exibir_ficha_material(_supabase):
    # Ponte vinda da Consulta: pré-preenche filtros
    tipo_pre = st.session_state.pop("fm_open_tipo", None)
    cod_pre = st.session_state.pop("fm_open_codigo", None)
    desc_pre = st.session_state.pop("fm_open_descricao", None)

    if tipo_pre:
        st.session_state["tipo_busca"] = tipo_pre
    if cod_pre:
        st.session_state["busca_texto"] = str(cod_pre)
    elif desc_pre:
        st.session_state["busca_texto"] = str(desc_pre)

    """Exibe ficha técnica completa e moderna do material"""
    
    st.title("📋 Ficha Técnica de Material")
    
    df_pedidos = carregar_pedidos(_supabase)
    
    if df_pedidos.empty:
        st.info("📭 Nenhum pedido cadastrado ainda")
        return
    
    # ============================================
    # SISTEMA DE ABAS PARA FILTROS
    # ============================================
    
    tab1, tab2, tab3 = st.tabs([
        "🔍 Buscar Material", 
        "🔧 Buscar por Equipamento",
        "🏢 Buscar por Departamento"
    ])
    
    material_selecionado = None
    historico_material = pd.DataFrame()
    tipo_busca = None
    
    # ============================================
    # TAB 1: BUSCA POR MATERIAL (COM BARRA DE PESQUISA)
    # ============================================
    with tab1:
        st.markdown("### 🔎 Buscar Material Específico")
        
        # Criar lista de materiais únicos com código e contagem
        materiais_unicos = df_pedidos.groupby('cod_material').agg({
            'descricao': 'first',
            'id': 'count'
        }).reset_index()
        materiais_unicos = materiais_unicos.sort_values('id', ascending=False)
        
        # Barra de pesquisa com autocompletar
        col1, col2 = st.columns([4, 1])
        
        with col1:
            busca_texto = st.text_input(
                "Digite o código do material:",
                placeholder="Ex: MAT001, 12345, FILT-200...",
                help="Digite o código completo ou parcial do material para buscar",
                key="busca_material"
            )
        
        with col2:
            st.markdown("<br>", unsafe_allow_html=True)
            limpar_busca = st.button("🔄 Limpar", key="limpar_material")
            if limpar_busca:
                st.rerun()
        
        # Filtrar materiais baseado na busca
        if busca_texto:
            materiais_filtrados = materiais_unicos[
                materiais_unicos['cod_material'].astype(str).str.contains(busca_texto.upper(), case=False, na=False)
            ]
            
            if materiais_filtrados.empty:
                st.warning(f"⚠️ Nenhum material encontrado com código '{busca_texto}'")
                st.info("💡 Tente códigos mais genéricos ou verifique se o código está correto")
            else:
                st.success(f"✅ {len(materiais_filtrados)} material(is) encontrado(s)")
                
                # Mostrar resultados em cards
                st.markdown("#### Selecione um material:")
                
                for idx, row in materiais_filtrados.head(10).iterrows():
                    col1, col2, col3 = st.columns([3, 1, 1])
                    
                    with col1:
                        st.markdown(f"**Código:** {row['cod_material']}")
                        if pd.notna(row['descricao']):
                            st.caption(f"{row['descricao']}")
                    
                    with col2:
                        st.metric("Compras", row['id'])
                    
                    with col3:
                        if st.button("Ver Ficha", key=f"ver_{idx}"):
                            material_selecionado = row['descricao']
                            tipo_busca = "material"
                    
                    st.markdown("---")
                
                if len(materiais_filtrados) > 10:
                    st.info(f"ℹ️ Mostrando 10 de {len(materiais_filtrados)} resultados. Refine sua busca para ver mais.")
        else:
            st.info("💡 Digite o nome do material no campo acima para começar a busca")
            
            # Mostrar top 10 materiais mais comprados
            st.markdown("#### 📊 Top 10 Materiais Mais Comprados")
            
            for idx, row in materiais_unicos.head(10).iterrows():
                col1, col2, col3 = st.columns([3, 1, 1])
                
                with col1:
                    st.markdown(f"**{row['descricao']}**")
                    if pd.notna(row['cod_material']):
                        st.caption(f"Código: {row['cod_material']}")
                
                with col2:
                    st.metric("Compras", row['id'])
                
                with col3:
                    if st.button("Ver Ficha", key=f"top_{idx}"):
                        material_selecionado = row['descricao']
                        tipo_busca = "material"
                
                st.markdown("---")
    
    # ============================================
    # TAB 2: BUSCA POR EQUIPAMENTO (COM FILTROS)
    # ============================================
    with tab2:
        st.markdown("### 🔧 Materiais por Equipamento")
        
        # Lista de equipamentos únicos
        equipamentos_todos = df_pedidos['cod_equipamento'].dropna().unique()
        equipamentos_todos = sorted([str(eq) for eq in equipamentos_todos if str(eq).strip()])
        
        if not equipamentos_todos:
            st.warning("⚠️ Nenhum equipamento cadastrado nos pedidos")
        else:
            # ============================================
            # BARRA DE PESQUISA DE EQUIPAMENTO
            # ============================================
            st.markdown("#### 🔍 Buscar Equipamento")
            
            col1, col2 = st.columns([4, 1])
            
            with col1:
                busca_equipamento = st.text_input(
                    "Digite o código ou nome do equipamento:",
                    placeholder="Ex: TR-001, TRATOR, ESCAVADEIRA...",
                    help="Busca por código ou descrição do equipamento",
                    key="busca_equipamento"
                )
            
            with col2:
                st.markdown("<br>", unsafe_allow_html=True)
                if st.button("🔄 Limpar", key="limpar_busca_equipamento"):
                    st.rerun()
            
            # Filtrar equipamentos pela busca
            if busca_equipamento:
                equipamentos_filtrados = [
                    eq for eq in equipamentos_todos 
                    if busca_equipamento.upper() in eq.upper()
                ]
                
                if not equipamentos_filtrados:
                    st.warning(f"⚠️ Nenhum equipamento encontrado com '{busca_equipamento}'")
                    equipamentos_filtrados = []
                else:
                    st.success(f"✅ {len(equipamentos_filtrados)} equipamento(s) encontrado(s)")
            else:
                equipamentos_filtrados = equipamentos_todos
            
            # ============================================
            # SELEÇÃO DE EQUIPAMENTO
            # ============================================
            if equipamentos_filtrados:
                equipamento_selecionado = st.selectbox(
                    "Selecione o Equipamento:",
                    options=[''] + equipamentos_filtrados,
                    format_func=lambda x: "Selecione..." if x == '' else x,
                    key="select_equipamento"
                )
            else:
                equipamento_selecionado = ''
            
            if equipamento_selecionado:
                # Filtrar pedidos do equipamento
                df_equipamento = df_pedidos[df_pedidos['cod_equipamento'] == equipamento_selecionado].copy()
                
                st.markdown("---")
                
                # ============================================
                # FILTROS AVANÇADOS
                # ============================================
                st.markdown("#### 🎛️ Filtros Avançados")
                
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    # Filtro de Status
                    status_options = df_equipamento['status'].dropna().unique().tolist()
                    status_filtro_eq = st.multiselect(
                        "📊 Status",
                        options=status_options,
                        default=status_options,
                        key="status_eq"
                    )
                
                with col2:
                    # Filtro de Período
                    periodo_eq = st.selectbox(
                        "📅 Período",
                        ["Todos", "Último mês", "Últimos 3 meses", "Últimos 6 meses", "Último ano"],
                        key="periodo_eq"
                    )
                
                with col3:
                    # Filtro de Entrega
                    filtro_entrega_eq = st.selectbox(
                        "🚚 Entrega",
                        ["Todos", "Apenas Entregues", "Apenas Pendentes"],
                        key="entrega_eq"
                    )
                
                # Aplicar filtros
                df_eq_filtrado = df_equipamento.copy()
                
                # Filtro de status
                if status_filtro_eq:
                    df_eq_filtrado = df_eq_filtrado[df_eq_filtrado['status'].isin(status_filtro_eq)]
                
                # Filtro de período
                if periodo_eq != "Todos":
                    from datetime import datetime
                    hoje = datetime.now()
                    if periodo_eq == "Último mês":
                        data_limite = hoje - pd.DateOffset(months=1)
                    elif periodo_eq == "Últimos 3 meses":
                        data_limite = hoje - pd.DateOffset(months=3)
                    elif periodo_eq == "Últimos 6 meses":
                        data_limite = hoje - pd.DateOffset(months=6)
                    else:  # Último ano
                        data_limite = hoje - pd.DateOffset(years=1)
                    
                    df_eq_filtrado = df_eq_filtrado[
                        pd.to_datetime(df_eq_filtrado['data_oc'], errors='coerce') >= data_limite
                    ]
                
                # Filtro de entrega
                if filtro_entrega_eq == "Apenas Entregues":
                    df_eq_filtrado = df_eq_filtrado[df_eq_filtrado['entregue'] == True]
                elif filtro_entrega_eq == "Apenas Pendentes":
                    df_eq_filtrado = df_eq_filtrado[df_eq_filtrado['entregue'] == False]
                
                st.markdown("---")
                
                # ============================================
                # ESTATÍSTICAS DO EQUIPAMENTO
                # ============================================
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.metric("📦 Total de Pedidos", len(df_eq_filtrado))
                
                with col2:
                    st.metric("🔧 Materiais Diferentes", df_eq_filtrado['descricao'].nunique())
                
                with col3:
                    valor_total = df_eq_filtrado['valor_total'].sum()
                    st.metric("💰 Valor Total", formatar_moeda_br(valor_total))
                
                with col4:
                    entregues = (df_eq_filtrado['entregue'] == True).sum()
                    st.metric("✅ Entregues", f"{entregues}/{len(df_eq_filtrado)}")
                
                st.markdown("---")
                
                # ============================================
                # LISTA DE MATERIAIS DO EQUIPAMENTO
                # ============================================
                if df_eq_filtrado.empty:
                    st.warning("⚠️ Nenhum material encontrado com os filtros aplicados")
                else:
                    materiais_equipamento = df_eq_filtrado.groupby('descricao').agg({
                        'id': 'count',
                        'valor_total': 'sum',
                        'qtde_solicitada': 'sum',
                        'entregue': lambda x: (x == True).sum()
                    }).reset_index()
                    
                    materiais_equipamento.columns = ['Material', 'Pedidos', 'Valor Total', 'Qtd Total', 'Entregues']
                    materiais_equipamento = materiais_equipamento.sort_values('Pedidos', ascending=False)
                    
                    st.markdown(f"#### 📋 Materiais do Equipamento **{equipamento_selecionado}**")
                    st.caption(f"Mostrando {len(materiais_equipamento)} material(is) • {len(df_eq_filtrado)} pedido(s)")
                    
                    for idx, row in materiais_equipamento.iterrows():
                        col1, col2, col3, col4, col5 = st.columns([3, 1, 1, 1, 1])
                        
                        with col1:
                            st.markdown(f"**{row['Material']}**")
                        
                        with col2:
                            st.metric("Pedidos", row['Pedidos'])
                        
                        with col3:
                            st.metric("Valor", f"R$ {row['Valor Total']:,.0f}")
                        
                        with col4:
                            st.metric("Entregues", f"{row['Entregues']}/{row['Pedidos']}")
                        
                        with col5:
                            if st.button("Ver Ficha", key=f"eq_{idx}"):
                                material_selecionado = row['Material']
                                tipo_busca = "equipamento"
                                historico_material = df_eq_filtrado[
                                    df_eq_filtrado['descricao'] == material_selecionado
                                ].copy()
                        
                        st.markdown("---")
    
    # ============================================
    # TAB 3: BUSCA POR DEPARTAMENTO (COM FILTROS)
    # ============================================
    with tab3:
        st.markdown("### 🏢 Materiais por Departamento")
        
        # Lista de departamentos únicos
        departamentos = df_pedidos['departamento'].dropna().unique()
        departamentos = sorted([str(dep) for dep in departamentos if str(dep).strip()])
        
        if not departamentos:
            st.warning("⚠️ Nenhum departamento cadastrado nos pedidos")
        else:
            col1, col2 = st.columns([4, 1])
            
            with col1:
                departamento_selecionado = st.selectbox(
                    "Selecione o Departamento:",
                    options=[''] + departamentos,
                    format_func=lambda x: "Selecione..." if x == '' else x,
                    key="select_departamento"
                )
            
            with col2:
                st.markdown("<br>", unsafe_allow_html=True)
                if st.button("🔄 Limpar", key="limpar_departamento"):
                    st.rerun()
            
            if departamento_selecionado:
                # Filtrar pedidos do departamento
                df_departamento = df_pedidos[df_pedidos['departamento'] == departamento_selecionado].copy()
                
                st.markdown("---")
                
                # ============================================
                # FILTROS AVANÇADOS
                # ============================================
                st.markdown("#### 🎛️ Filtros Avançados")
                
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    # Filtro de Status
                    status_options_dep = df_departamento['status'].dropna().unique().tolist()
                    status_filtro_dep = st.multiselect(
                        "📊 Status",
                        options=status_options_dep,
                        default=status_options_dep,
                        key="status_dep"
                    )
                
                with col2:
                    # Filtro de Período
                    periodo_dep = st.selectbox(
                        "📅 Período",
                        ["Todos", "Último mês", "Últimos 3 meses", "Últimos 6 meses", "Último ano"],
                        key="periodo_dep"
                    )
                
                with col3:
                    # Filtro de Entrega
                    filtro_entrega_dep = st.selectbox(
                        "🚚 Entrega",
                        ["Todos", "Apenas Entregues", "Apenas Pendentes"],
                        key="entrega_dep"
                    )
                
                with col4:
                    # Filtro de Equipamento
                    equipamentos_dep = ['Todos'] + sorted(df_departamento['cod_equipamento'].dropna().unique().tolist())
                    filtro_equipamento_dep = st.selectbox(
                        "🔧 Equipamento",
                        options=equipamentos_dep,
                        key="equipamento_dep"
                    )
                
                # Aplicar filtros
                df_dep_filtrado = df_departamento.copy()
                
                # Filtro de status
                if status_filtro_dep:
                    df_dep_filtrado = df_dep_filtrado[df_dep_filtrado['status'].isin(status_filtro_dep)]
                
                # Filtro de período
                if periodo_dep != "Todos":
                    from datetime import datetime
                    hoje = datetime.now()
                    if periodo_dep == "Último mês":
                        data_limite = hoje - pd.DateOffset(months=1)
                    elif periodo_dep == "Últimos 3 meses":
                        data_limite = hoje - pd.DateOffset(months=3)
                    elif periodo_dep == "Últimos 6 meses":
                        data_limite = hoje - pd.DateOffset(months=6)
                    else:  # Último ano
                        data_limite = hoje - pd.DateOffset(years=1)
                    
                    df_dep_filtrado = df_dep_filtrado[
                        pd.to_datetime(df_dep_filtrado['data_oc'], errors='coerce') >= data_limite
                    ]
                
                # Filtro de entrega
                if filtro_entrega_dep == "Apenas Entregues":
                    df_dep_filtrado = df_dep_filtrado[df_dep_filtrado['entregue'] == True]
                elif filtro_entrega_dep == "Apenas Pendentes":
                    df_dep_filtrado = df_dep_filtrado[df_dep_filtrado['entregue'] == False]
                
                # Filtro de equipamento
                if filtro_equipamento_dep != 'Todos':
                    df_dep_filtrado = df_dep_filtrado[
                        df_dep_filtrado['cod_equipamento'] == filtro_equipamento_dep
                    ]
                
                st.markdown("---")
                
                # ============================================
                # ESTATÍSTICAS DO DEPARTAMENTO
                # ============================================
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.metric("📦 Total de Pedidos", len(df_dep_filtrado))
                
                with col2:
                    st.metric("🔧 Materiais Diferentes", df_dep_filtrado['descricao'].nunique())
                
                with col3:
                    valor_total = df_dep_filtrado['valor_total'].sum()
                    st.metric("💰 Valor Total", f"R$ {valor_total:,.2f}")
                
                with col4:
                    equipamentos_unicos = df_dep_filtrado['cod_equipamento'].nunique()
                    st.metric("⚙️ Equipamentos", equipamentos_unicos)
                
                st.markdown("---")
                
                # ============================================
                # LISTA DE MATERIAIS DO DEPARTAMENTO
                # ============================================
                if df_dep_filtrado.empty:
                    st.warning("⚠️ Nenhum material encontrado com os filtros aplicados")
                else:
                    materiais_departamento = df_dep_filtrado.groupby('descricao').agg({
                        'id': 'count',
                        'valor_total': 'sum',
                        'qtde_solicitada': 'sum',
                        'cod_equipamento': 'nunique',
                        'entregue': lambda x: (x == True).sum()
                    }).reset_index()
                    
                    materiais_departamento.columns = ['Material', 'Pedidos', 'Valor Total', 'Qtd Total', 'Equipamentos', 'Entregues']
                    materiais_departamento = materiais_departamento.sort_values('Pedidos', ascending=False)
                    
                    st.markdown(f"#### 📋 Materiais do Departamento **{departamento_selecionado}**")
                    st.caption(f"Mostrando {len(materiais_departamento)} material(is) • {len(df_dep_filtrado)} pedido(s)")
                    
                    for idx, row in materiais_departamento.iterrows():
                        col1, col2, col3, col4, col5, col6 = st.columns([3, 1, 1, 1, 1, 1])
                        
                        with col1:
                            st.markdown(f"**{row['Material']}**")
                        
                        with col2:
                            st.metric("Pedidos", row['Pedidos'])
                        
                        with col3:
                            st.metric("Valor", f"R$ {row['Valor Total']:,.0f}")
                        
                        with col4:
                            st.metric("Equip.", row['Equipamentos'])
                        
                        with col5:
                            st.metric("Entregues", f"{row['Entregues']}/{row['Pedidos']}")
                        
                        with col6:
                            if st.button("Ver Ficha", key=f"dep_{idx}"):
                                material_selecionado = row['Material']
                                tipo_busca = "departamento"
                                historico_material = df_dep_filtrado[
                                    df_dep_filtrado['descricao'] == material_selecionado
                                ].copy()
                        
                        st.markdown("---")
    
    # ============================================
    # EXIBIR FICHA DO MATERIAL SELECIONADO
    # ============================================
    
    # Se material foi selecionado via busca normal (tab1)
    if material_selecionado and tipo_busca == "material":
        historico_material = df_pedidos[df_pedidos['descricao'] == material_selecionado].copy()
    
    # Se material foi selecionado via busca normal (tab1)
    if material_selecionado and tipo_busca == "material":
        historico_material = df_pedidos[df_pedidos['descricao'] == material_selecionado].copy()
    
    if not historico_material.empty and material_selecionado:
        # Informações do material atual (pedido mais recente)
        material_atual = historico_material.sort_values('data_oc', ascending=False).iloc[0].to_dict()
        
        st.markdown("---")
        
        # Header com informações básicas
        filtro_info = ""
        if tipo_busca == "equipamento":
            filtro_info = f" • Equipamento: {equipamento_selecionado}"
        elif tipo_busca == "departamento":
            filtro_info = f" • Departamento: {departamento_selecionado}"
        
        st.markdown(f"""
        <div style='background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                    padding: 25px; border-radius: 15px; color: white; margin-bottom: 20px;'>
            <h2 style='margin: 0; font-size: 28px;'>📦 {material_selecionado}</h2>
            <p style='margin: 10px 0 0 0; font-size: 16px; opacity: 0.9;'>
                Código: {material_atual.get('cod_material', 'N/A')} • 
                Departamento: {material_atual.get('departamento', 'N/A')} • 
                Equipamento: {material_atual.get('cod_equipamento', 'N/A')}{filtro_info}
            </p>
        </div>
        """, unsafe_allow_html=True)
        
        # Cards de KPIs
        fm.criar_cards_kpis(historico_material)
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        # Layout em colunas
        col1, col2 = st.columns([2, 1])
        
        with col1:
            # Gráfico de evolução de preços
            fm.criar_grafico_evolucao_precos(historico_material)
            
            st.markdown("<br>", unsafe_allow_html=True)
            
            # Comparação visual de preços
            fm.criar_comparacao_visual_precos(historico_material)
        
        with col2:
            # Mini-mapa de fornecedores
            fm.criar_mini_mapa_fornecedores(historico_material)
        
        st.markdown("---")
        
        # Ranking de fornecedores (visual moderno)
        fm.criar_ranking_fornecedores_visual(historico_material)
        
        st.markdown("---")
        
        # Timeline de compras
        fm.criar_timeline_compras(historico_material)
        
        st.markdown("---")
        
        # Insights automáticos
        fm.criar_insights_automaticos(historico_material, material_atual)
        
        st.markdown("---")
        
        # Botão para voltar
        if st.button("← Voltar para Consulta", use_container_width=True):
            st.session_state.pagina = "Consultar Pedidos"
            st.rerun()

# ============================================
# PÁGINA DE GESTÃO DE USUÁRIOS (ADMIN ONLY)
# ============================================

