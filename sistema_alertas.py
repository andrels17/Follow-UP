"""
Módulo de Notificações e Alertas
Sistema de avisos proativos para gestão de pedidos
VERSÃO FINAL CORRIGIDA - Usando componentes nativos do Streamlit
"""

import streamlit as st
import pandas as pd
import re
import html
from datetime import datetime, timedelta

def calcular_alertas(df_pedidos):
    """Calcula todos os tipos de alertas do sistema"""
    
    hoje = pd.Timestamp.now().normalize()
    
    alertas = {
        'pedidos_atrasados': [],
        'pedidos_vencendo': [],
        'fornecedores_baixa_performance': [],
        'pedidos_criticos': [],
        'total': 0
    }
    
    if df_pedidos.empty:
        return alertas
    
    # OTIMIZAÇÃO: Converter datas UMA VEZ antes dos loops
    df_pedidos = df_pedidos.copy()
    df_pedidos['previsao_dt'] = pd.to_datetime(df_pedidos['previsao_entrega'], errors='coerce')
    
    # 1. Pedidos Atrasados
    df_atrasados = df_pedidos[
        (df_pedidos['entregue'] == False) & 
        (df_pedidos['previsao_dt'] < hoje) &
        (df_pedidos['previsao_dt'].notna())
    ]
    
    for _, pedido in df_atrasados.iterrows():
        dias_atraso = (hoje - pedido['previsao_dt']).days
        alertas['pedidos_atrasados'].append({
            'id': pedido.get('id'),
            'nr_oc': pedido.get('nr_oc'),
            'descricao': pedido.get('descricao', ''),
            'fornecedor': pedido.get('fornecedor_nome', 'N/A'),
            'dias_atraso': dias_atraso,
            'valor': pedido.get('valor_total', 0),
            'departamento': pedido.get('departamento', 'N/A')
        })
    
    # 2. Pedidos Vencendo (próximos 3 dias)
    data_limite = hoje + timedelta(days=3)
    df_vencendo = df_pedidos[
        (df_pedidos['entregue'] == False) & 
        (df_pedidos['previsao_dt'] >= hoje) &
        (df_pedidos['previsao_dt'] <= data_limite) &
        (df_pedidos['previsao_dt'].notna())
    ]
    
    for _, pedido in df_vencendo.iterrows():
        dias_restantes = (pedido['previsao_dt'] - hoje).days
        alertas['pedidos_vencendo'].append({
            'id': pedido.get('id'),
            'nr_oc': pedido.get('nr_oc'),
            'descricao': pedido.get('descricao', ''),
            'fornecedor': pedido.get('fornecedor_nome', 'N/A'),
            'dias_restantes': dias_restantes,
            'valor': pedido.get('valor_total', 0),
            'previsao': pedido.get('previsao_entrega')
        })
    
    # 3. Fornecedores com Baixa Performance
    if not df_pedidos.empty:
        df_fornecedores_stats = df_pedidos[df_pedidos['fornecedor_nome'].notna()].groupby('fornecedor_nome').agg({
            'id': 'count',
            'entregue': 'sum',
            'atrasado': 'sum'
        }).reset_index()
        
        df_fornecedores_stats.columns = ['fornecedor', 'total_pedidos', 'entregues', 'atrasados']
        df_fornecedores_stats['taxa_sucesso'] = (
            (df_fornecedores_stats['entregues'] - df_fornecedores_stats['atrasados']) / 
            df_fornecedores_stats['total_pedidos'] * 100
        ).fillna(0)
        
        df_baixa_perf = df_fornecedores_stats[
            (df_fornecedores_stats['taxa_sucesso'] < 70) & 
            (df_fornecedores_stats['total_pedidos'] >= 5)
        ]
        
        for _, fornecedor in df_baixa_perf.iterrows():
            alertas['fornecedores_baixa_performance'].append({
                'fornecedor': fornecedor['fornecedor'],
                'taxa_sucesso': fornecedor['taxa_sucesso'],
                'total_pedidos': fornecedor['total_pedidos'],
                'atrasados': fornecedor['atrasados']
            })
    
    # 4. Pedidos Críticos
    if not df_pedidos.empty and 'valor_total' in df_pedidos.columns:
        valor_critico = df_pedidos['valor_total'].quantile(0.75)
        df_criticos = df_pedidos[
            (df_pedidos['entregue'] == False) &
            (df_pedidos['valor_total'] >= valor_critico) &
            (df_pedidos['previsao_dt'] <= data_limite) &
            (df_pedidos['previsao_dt'].notna())
        ]
        
        for _, pedido in df_criticos.iterrows():
            alertas['pedidos_criticos'].append({
                'id': pedido.get('id'),
                'nr_oc': pedido.get('nr_oc'),
                'descricao': pedido.get('descricao', ''),
                'valor': pedido.get('valor_total', 0),
                'previsao': pedido.get('previsao_entrega'),
                'departamento': pedido.get('departamento', 'N/A')
            })
    
    # Total de alertas
    alertas['total'] = (
        len(alertas['pedidos_atrasados']) +
        len(alertas['pedidos_vencendo']) +
        len(alertas['fornecedores_baixa_performance']) +
        len(alertas['pedidos_criticos'])
    )
    
    return alertas

def limpar_html_completo(value, max_length=None, default='N/A'):
    """
    Remove COMPLETAMENTE qualquer HTML de uma string.
    VERSÃO ULTRA AGRESSIVA - Remove múltiplas camadas de HTML.
    """
    if value is None or pd.isna(value):
        return default
    
    texto = str(value).strip()
    
    if not texto:
        return default
    
    # LOOP: Continuar removendo HTML até não sobrar nenhuma tag
    # Máximo 10 iterações para evitar loop infinito
    iteracoes = 0
    while ('<' in texto and '>' in texto) and iteracoes < 10:
        iteracoes += 1
        
        # PASSO 1: Decodificar entidades HTML escapadas
        texto = html.unescape(texto)
        
        # PASSO 2: Remover tags completas
        texto = re.sub(r'<[^<>]+>', '', texto)
        
        # PASSO 3: Remover tags incompletas
        texto = re.sub(r'<[^>]*', '', texto)
        texto = re.sub(r'[^<]*>', '', texto)
    
    # PASSO 4: Limpar espaços, quebras e tabs
    texto = re.sub(r'[\n\r\t]+', ' ', texto)
    texto = re.sub(r'\s+', ' ', texto)
    texto = texto.strip()
    
    if not texto:
        return default
    
    # PASSO 5: Truncar se necessário
    if max_length and len(texto) > max_length:
        return texto[:max_length].rstrip() + '...'
    
    return texto

def safe_text(value, max_length=None, default='N/A'):
    """
    Texto seguro para exibição.
    Usa limpar_html_completo para garantia remoção total de HTML.
    """
    return limpar_html_completo(value, max_length, default)

def exibir_badge_alertas(alertas):
    """Exibe badge com total de alertas no sidebar"""
    
    total = alertas['total']
    
    if total > 0:
        cor = "🔴" if total >= 10 else "🟡" if total >= 5 else "🟢"
        st.sidebar.markdown(f"""
        <div style="
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 15px;
            border-radius: 10px;
            text-align: center;
            margin: 10px 0;
            box-shadow: 0 4px 6px rgba(0,0,0,0.3);
        ">
            <h2 style="color: white; margin: 0;">{cor} {total}</h2>
            <p style="color: white; margin: 5px 0 0 0; font-size: 14px;">Alertas Ativos</p>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.sidebar.success("✅ Nenhum alerta ativo")

def criar_card_pedido(alerta, tipo, formatar_moeda_br):
    """Cria um card para pedido usando componentes nativos do Streamlit"""
    
    with st.container():
        if tipo == "atrasado":
            # Determinar cores e ícone
            if alerta['dias_atraso'] >= 30:
                cor_borda = "#dc2626"
                icone = "🔴"
            elif alerta['dias_atraso'] >= 15:
                cor_borda = "#ef4444"
                icone = "🔴"
            else:
                cor_borda = "#f97316"
                icone = "🟠"
            
            # Layout do card
            col1, col2 = st.columns([3, 1])
            
            with col1:
                st.markdown(f"**{icone} OC {safe_text(alerta.get('nr_oc', 'N/A'))}**")
                st.markdown(f"**Departamento:** {safe_text(alerta.get('departamento', 'N/A'), max_length=30)}")
                st.markdown(f"**Descrição:** {limpar_html_completo(alerta.get('descricao', ''), max_length=120)}")
                st.markdown(f"**Fornecedor:** {safe_text(alerta.get('fornecedor', 'N/A'), max_length=25)}")
            
            with col2:
                st.markdown(f'<div style="border-left: 4px solid {cor_borda}; padding-left: 10px;">', unsafe_allow_html=True)
                st.markdown(f"**{alerta['dias_atraso']} dias**")
                st.markdown(f"**Valor:** {formatar_moeda_br(alerta.get('valor', 0))}")
                st.markdown("</div>", unsafe_allow_html=True)
        
        elif tipo == "vencendo":
            if alerta['dias_restantes'] == 0:
                cor_borda = "#dc2626"
                icone = "🔴"
                urgencia = "HOJE"
            elif alerta['dias_restantes'] == 1:
                cor_borda = "#f59e0b"
                icone = "🟡"
                urgencia = "AMANHÃ"
            else:
                cor_borda = "#3b82f6"
                icone = "🔵"
                urgencia = f"{alerta['dias_restantes']} dias"
            
            col1, col2 = st.columns([3, 1])
            
            with col1:
                st.markdown(f"**{icone} OC {safe_text(alerta.get('nr_oc', 'N/A'))}**")
                
                try:
                    data_previsao = pd.to_datetime(alerta['previsao']).strftime('%d/%m/%Y')
                except:
                    data_previsao = 'N/A'
                
                st.markdown(f"**Previsão:** {data_previsao}")
                st.markdown(f"**Descrição:** {limpar_html_completo(alerta.get('descricao', ''), max_length=120)}")
                st.markdown(f"**Fornecedor:** {safe_text(alerta.get('fornecedor', 'N/A'), max_length=25)}")
            
            with col2:
                st.markdown(f'<div style="border-left: 4px solid {cor_borda}; padding-left: 10px;">', unsafe_allow_html=True)
                st.markdown(f"**{urgencia}**")
                st.markdown(f"**Valor:** {formatar_moeda_br(alerta.get('valor', 0))}")
                st.markdown("</div>", unsafe_allow_html=True)
        
        elif tipo == "critico":
            col1, col2 = st.columns([3, 1])
            
            with col1:
                st.markdown(f"**🚨 OC {safe_text(alerta.get('nr_oc', 'N/A'))}**")
                st.markdown(f"**Departamento:** {safe_text(alerta.get('departamento', 'N/A'), max_length=30)}")
                st.markdown(f"**Descrição:** {limpar_html_completo(alerta.get('descricao', ''), max_length=120)}")
                
                try:
                    data_previsao = pd.to_datetime(alerta['previsao']).strftime('%d/%m/%Y')
                except:
                    data_previsao = 'N/A'
                st.markdown(f"**Previsão:** {data_previsao}")
            
            with col2:
                st.markdown('<div style="border-left: 4px solid #ef4444; padding-left: 10px;">', unsafe_allow_html=True)
                st.markdown("**CRÍTICO**")
                st.markdown(f"**Valor:** {formatar_moeda_br(alerta.get('valor', 0))}")
                st.markdown("</div>", unsafe_allow_html=True)
        
        # Separador
        st.markdown("---")

def criar_card_fornecedor(fornecedor, formatar_moeda_br):
    """Cria um card para fornecedor usando componentes nativos"""
    
    with st.container():
        # Garantir que a taxa de sucesso esteja entre 0 e 100
        taxa_sucesso = max(0, min(100, fornecedor['taxa_sucesso']))
        
        if taxa_sucesso < 40:
            cor_borda = "#dc2626"
            cor_badge = "#7f1d1d"
            nivel = "CRÍTICO"
        elif taxa_sucesso < 55:
            cor_borda = "#ea580c"
            cor_badge = "#7c2d12"
            nivel = "GRAVE"
        else:
            cor_borda = "#f59e0b"
            cor_badge = "#78350f"
            nivel = "ATENÇÃO"
        
        st.markdown(f'<div style="border-left: 4px solid {cor_borda}; padding-left: 10px;">', unsafe_allow_html=True)
        
        # Cabeçalho
        col_titulo, col_badge = st.columns([3, 1])
        with col_titulo:
            nome_fornecedor = safe_text(fornecedor.get('fornecedor', 'N/A'), max_length=30)
            st.markdown(f"**📉 {nome_fornecedor}**")
            st.markdown(f"**Total de Pedidos:** {int(fornecedor['total_pedidos'])}")
        
        with col_badge:
            st.markdown(f'<div style="background-color: {cor_badge}; color: white; padding: 6px 12px; border-radius: 15px; text-align: center; font-weight: bold;">{nivel}</div>', unsafe_allow_html=True)
        
        # Métricas
        col_met1, col_met2, col_met3 = st.columns(3)
        with col_met1:
            st.metric(
                "Atrasados", 
                f"{int(fornecedor['atrasados'])}",
                f"{fornecedor['atrasados']/fornecedor['total_pedidos']*100:.1f}%" if fornecedor['total_pedidos'] > 0 else "0%",
                delta_color="inverse"
            )
        
        with col_met2:
            st.metric(
                "No Prazo", 
                f"{int(fornecedor['total_pedidos'] - fornecedor['atrasados'])}",
                f"{(fornecedor['total_pedidos'] - fornecedor['atrasados'])/fornecedor['total_pedidos']*100:.1f}%" if fornecedor['total_pedidos'] > 0 else "0%"
            )
        
        with col_met3:
            st.metric(
                "Taxa de Sucesso",
                f"{taxa_sucesso:.1f}%"
            )
        
        # Barra de progresso customizada
        st.markdown(
            f"""
            <div style="margin: 10px 0;">
                <div style="display: flex; justify-content: space-between; margin-bottom: 5px;">
                    <span style="color: #64748b; font-size: 12px;">Taxa de Sucesso</span>
                    <span style="color: #94a3b8; font-size: 12px;">{taxa_sucesso:.1f}%</span>
                </div>
                <div style="background: #e2e8f0; border-radius: 10px; height: 8px; overflow: hidden;">
                    <div style="background: {cor_borda}; width: {taxa_sucesso}%; height: 100%;"></div>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )
        
        st.markdown("</div>", unsafe_allow_html=True)
        st.markdown("---")

def exibir_painel_alertas(alertas, formatar_moeda_br, df_pedidos_original=None):
    """Exibe painel completo de alertas usando componentes nativos do Streamlit"""
    
    st.title("🔔 Central de Notificações e Alertas")
    
    # Resumo de alertas
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "⚠️ Atrasados",
            len(alertas['pedidos_atrasados']),
            delta=f"-{len(alertas['pedidos_atrasados'])}" if len(alertas['pedidos_atrasados']) > 0 else "0",
            delta_color="inverse"
        )
    
    with col2:
        st.metric(
            "⏰ Vencendo em 3 dias",
            len(alertas['pedidos_vencendo'])
        )
    
    with col3:
        st.metric(
            "🚨 Pedidos Críticos",
            len(alertas['pedidos_criticos'])
        )
    
    with col4:
        st.metric(
            "📉 Fornecedores Problema",
            len(alertas['fornecedores_baixa_performance'])
        )
    
    st.markdown("---")
    
    # Abas para cada tipo de alerta
    tab1, tab2, tab3, tab4 = st.tabs([
        f"⚠️ Atrasados ({len(alertas['pedidos_atrasados'])})",
        f"⏰ Vencendo ({len(alertas['pedidos_vencendo'])})",
        f"🚨 Críticos ({len(alertas['pedidos_criticos'])})",
        f"📉 Fornecedores ({len(alertas['fornecedores_baixa_performance'])})"
    ])
    
    with tab1:
        st.subheader("⚠️ Pedidos Atrasados")
        
        if alertas['pedidos_atrasados']:
            # Extrair departamentos únicos
            departamentos = sorted(list(set(
                [safe_text(p.get('departamento', 'N/A')) for p in alertas['pedidos_atrasados']]
            )))
            
            fornecedores = sorted(list(set(
                [safe_text(p.get('fornecedor', 'N/A')) for p in alertas['pedidos_atrasados']]
            )))
            
            # Filtros
            col_filtro1, col_filtro2, col_filtro3 = st.columns(3)
            
            with col_filtro1:
                ordem = st.selectbox(
                    "Ordenar por:",
                    ["Dias de Atraso (maior primeiro)", "Dias de Atraso (menor primeiro)", 
                     "Valor (maior primeiro)", "Valor (menor primeiro)"],
                    key="filtro_atrasados_ordem"
                )
            
            with col_filtro2:
                dept_filtro = st.multiselect(
                    "Filtrar por Departamento:",
                    options=departamentos,
                    default=[],
                    key="filtro_atrasados_dept"
                )
            
            with col_filtro3:
                fornecedor_filtro = st.multiselect(
                    "Filtrar por Fornecedor:",
                    options=fornecedores,
                    default=[],
                    key="filtro_atrasados_fornecedor"
                )
            
            # Aplicar ordenação
            if "Dias de Atraso (maior primeiro)" in ordem:
                pedidos_filtrados = sorted(alertas['pedidos_atrasados'], key=lambda x: x['dias_atraso'], reverse=True)
            elif "Dias de Atraso (menor primeiro)" in ordem:
                pedidos_filtrados = sorted(alertas['pedidos_atrasados'], key=lambda x: x['dias_atraso'])
            elif "Valor (maior primeiro)" in ordem:
                pedidos_filtrados = sorted(alertas['pedidos_atrasados'], key=lambda x: x.get('valor', 0), reverse=True)
            elif "Valor (menor primeiro)" in ordem:
                pedidos_filtrados = sorted(alertas['pedidos_atrasados'], key=lambda x: x.get('valor', 0))
            else:
                pedidos_filtrados = alertas['pedidos_atrasados']
            
            # Aplicar filtros de departamento
            if dept_filtro:
                pedidos_filtrados = [p for p in pedidos_filtrados if safe_text(p.get('departamento', 'N/A')) in dept_filtro]
            
            # Aplicar filtros de fornecedor
            if fornecedor_filtro:
                pedidos_filtrados = [p for p in pedidos_filtrados if safe_text(p.get('fornecedor', 'N/A')) in fornecedor_filtro]
            
            # Mostrar contador de resultados
            st.caption(f"📊 Mostrando {len(pedidos_filtrados)} de {len(alertas['pedidos_atrasados'])} pedidos atrasados")
            
            if pedidos_filtrados:
                for pedido in pedidos_filtrados:
                    criar_card_pedido(pedido, "atrasado", formatar_moeda_br)
            else:
                st.info("📭 Nenhum pedido atrasado corresponde aos filtros selecionados")
        else:
            st.success("✅ Nenhum pedido atrasado!")
    
    with tab2:
        st.subheader("⏰ Pedidos Vencendo nos Próximos 3 Dias")
        
        if alertas['pedidos_vencendo']:
            # Extrair departamentos e fornecedores únicos
            departamentos_venc = sorted(list(set(
                [safe_text(p.get('departamento', 'N/A')) for p in alertas['pedidos_vencendo']]
            )))
            
            fornecedores_venc = sorted(list(set(
                [safe_text(p.get('fornecedor', 'N/A')) for p in alertas['pedidos_vencendo']]
            )))
            
            # Filtros
            col_filtro1, col_filtro2, col_filtro3 = st.columns(3)
            
            with col_filtro1:
                ordem_venc = st.selectbox(
                    "Ordenar por:",
                    ["Urgência (hoje primeiro)", "Dias Restantes (crescente)", 
                     "Dias Restantes (decrescente)", "Valor (maior primeiro)"],
                    key="filtro_vencendo_ordem"
                )
            
            with col_filtro2:
                dept_venc_filtro = st.multiselect(
                    "Filtrar por Departamento:",
                    options=departamentos_venc,
                    default=[],
                    key="filtro_vencendo_dept"
                )
            
            with col_filtro3:
                fornecedor_venc_filtro = st.multiselect(
                    "Filtrar por Fornecedor:",
                    options=fornecedores_venc,
                    default=[],
                    key="filtro_vencendo_fornecedor"
                )
            
            # Aplicar ordenação
            if "Urgência (hoje primeiro)" in ordem_venc:
                pedidos_filtrados = sorted(alertas['pedidos_vencendo'], key=lambda x: x['dias_restantes'])
            elif "Dias Restantes (crescente)" in ordem_venc:
                pedidos_filtrados = sorted(alertas['pedidos_vencendo'], key=lambda x: x['dias_restantes'])
            elif "Dias Restantes (decrescente)" in ordem_venc:
                pedidos_filtrados = sorted(alertas['pedidos_vencendo'], key=lambda x: x['dias_restantes'], reverse=True)
            elif "Valor (maior primeiro)" in ordem_venc:
                pedidos_filtrados = sorted(alertas['pedidos_vencendo'], key=lambda x: x.get('valor', 0), reverse=True)
            else:
                pedidos_filtrados = alertas['pedidos_vencendo']
            
            # Aplicar filtros de departamento
            if dept_venc_filtro:
                pedidos_filtrados = [p for p in pedidos_filtrados if safe_text(p.get('departamento', 'N/A')) in dept_venc_filtro]
            
            # Aplicar filtros de fornecedor
            if fornecedor_venc_filtro:
                pedidos_filtrados = [p for p in pedidos_filtrados if safe_text(p.get('fornecedor', 'N/A')) in fornecedor_venc_filtro]
            
            # Mostrar contador
            st.caption(f"📊 Mostrando {len(pedidos_filtrados)} de {len(alertas['pedidos_vencendo'])} pedidos vencendo")
            
            if pedidos_filtrados:
                for pedido in pedidos_filtrados:
                    criar_card_pedido(pedido, "vencendo", formatar_moeda_br)
            else:
                st.info("📭 Nenhum pedido vencendo corresponde aos filtros selecionados")
        else:
            st.info("📭 Nenhum pedido vencendo nos próximos 3 dias")
    
    with tab3:
        st.subheader("🚨 Pedidos Críticos (Alto Valor + Urgente)")
        
        if alertas['pedidos_criticos']:
            # Extrair departamentos e fornecedores únicos
            departamentos_crit = sorted(list(set(
                [safe_text(p.get('departamento', 'N/A')) for p in alertas['pedidos_criticos']]
            )))
            
            fornecedores_crit = sorted(list(set(
                [safe_text(p.get('fornecedor', 'N/A')) for p in alertas['pedidos_criticos']]
            )))
            
            # Filtros
            col_filtro1, col_filtro2, col_filtro3 = st.columns(3)
            
            with col_filtro1:
                ordem_crit = st.selectbox(
                    "Ordenar por:",
                    ["Valor (maior primeiro)", "Valor (menor primeiro)", 
                     "Previsão (próxima primeiro)"],
                    key="filtro_criticos_ordem"
                )
            
            with col_filtro2:
                dept_crit_filtro = st.multiselect(
                    "Filtrar por Departamento:",
                    options=departamentos_crit,
                    default=[],
                    key="filtro_criticos_dept"
                )
            
            with col_filtro3:
                fornecedor_crit_filtro = st.multiselect(
                    "Filtrar por Fornecedor:",
                    options=fornecedores_crit,
                    default=[],
                    key="filtro_criticos_fornecedor"
                )
            
            # Aplicar ordenação
            if "Valor (maior primeiro)" in ordem_crit:
                pedidos_filtrados = sorted(alertas['pedidos_criticos'], key=lambda x: x.get('valor', 0), reverse=True)
            elif "Valor (menor primeiro)" in ordem_crit:
                pedidos_filtrados = sorted(alertas['pedidos_criticos'], key=lambda x: x.get('valor', 0))
            elif "Previsão (próxima primeiro)" in ordem_crit:
                pedidos_filtrados = sorted(alertas['pedidos_criticos'], 
                                          key=lambda x: pd.to_datetime(x.get('previsao', '')) if x.get('previsao') else pd.Timestamp.max)
            else:
                pedidos_filtrados = alertas['pedidos_criticos']
            
            # Aplicar filtros de departamento
            if dept_crit_filtro:
                pedidos_filtrados = [p for p in pedidos_filtrados if safe_text(p.get('departamento', 'N/A')) in dept_crit_filtro]
            
            # Aplicar filtros de fornecedor
            if fornecedor_crit_filtro:
                pedidos_filtrados = [p for p in pedidos_filtrados if safe_text(p.get('fornecedor', 'N/A')) in fornecedor_crit_filtro]
            
            # Mostrar contador
            st.caption(f"📊 Mostrando {len(pedidos_filtrados)} de {len(alertas['pedidos_criticos'])} pedidos críticos")
            
            if pedidos_filtrados:
                st.warning("⚠️ Pedidos de alto valor com previsão de entrega próxima")
                
                for pedido in pedidos_filtrados:
                    criar_card_pedido(pedido, "critico", formatar_moeda_br)
            else:
                st.info("📭 Nenhum pedido crítico corresponde aos filtros selecionados")
        else:
            st.success("✅ Nenhum pedido crítico no momento")
    
    with tab4:
        st.subheader("📉 Fornecedores com Baixa Performance")
        
        if alertas['fornecedores_baixa_performance']:
            # Extrair nomes de fornecedores únicos
            nomes_fornecedores = sorted(list(set(
                [safe_text(f.get('fornecedor', 'N/A')) for f in alertas['fornecedores_baixa_performance']]
            )))
            
            # Filtros
            col_filtro1, col_filtro2, col_filtro3 = st.columns(3)
            
            with col_filtro1:
                ordem_forn = st.selectbox(
                    "Ordenar por:",
                    ["Taxa de Sucesso (menor primeiro)", "Taxa de Sucesso (maior primeiro)",
                     "Atrasados (maior primeiro)", "Total Pedidos (maior primeiro)"],
                    key="filtro_fornecedores_ordem"
                )
            
            with col_filtro2:
                nivel_filtro = st.multiselect(
                    "Filtrar por Nível de Risco:",
                    options=["CRÍTICO", "GRAVE", "ATENÇÃO"],
                    default=["CRÍTICO", "GRAVE", "ATENÇÃO"],
                    key="filtro_fornecedores_nivel"
                )
            
            with col_filtro3:
                fornecedor_nome_filtro = st.multiselect(
                    "Filtrar por Fornecedor:",
                    options=nomes_fornecedores,
                    default=[],
                    key="filtro_fornecedores_nome"
                )
            
            # Aplicar filtro de nível
            fornecedores_filtrados = []
            for fornecedor in alertas['fornecedores_baixa_performance']:
                taxa = max(0, min(100, fornecedor['taxa_sucesso']))
                
                # Verificar nível
                nivel_correspondente = False
                if taxa < 40 and "CRÍTICO" in nivel_filtro:
                    nivel_correspondente = True
                elif taxa < 55 and "GRAVE" in nivel_filtro:
                    nivel_correspondente = True
                elif taxa >= 55 and "ATENÇÃO" in nivel_filtro:
                    nivel_correspondente = True
                
                # Verificar nome do fornecedor
                nome_correspondente = True
                if fornecedor_nome_filtro:
                    nome_correspondente = safe_text(fornecedor.get('fornecedor', 'N/A')) in fornecedor_nome_filtro
                
                if nivel_correspondente and nome_correspondente:
                    fornecedores_filtrados.append(fornecedor)
            
            # Aplicar ordenação
            if "Taxa de Sucesso (menor primeiro)" in ordem_forn:
                fornecedores_filtrados = sorted(fornecedores_filtrados, key=lambda x: x['taxa_sucesso'])
            elif "Taxa de Sucesso (maior primeiro)" in ordem_forn:
                fornecedores_filtrados = sorted(fornecedores_filtrados, key=lambda x: x['taxa_sucesso'], reverse=True)
            elif "Atrasados (maior primeiro)" in ordem_forn:
                fornecedores_filtrados = sorted(fornecedores_filtrados, key=lambda x: x['atrasados'], reverse=True)
            elif "Total Pedidos (maior primeiro)" in ordem_forn:
                fornecedores_filtrados = sorted(fornecedores_filtrados, key=lambda x: x['total_pedidos'], reverse=True)
            
            # Mostrar contador
            st.caption(f"📊 Mostrando {len(fornecedores_filtrados)} de {len(alertas['fornecedores_baixa_performance'])} fornecedores")
            
            if fornecedores_filtrados:
                st.warning("⚠️ Fornecedores com taxa de sucesso abaixo de 70%")
                
                for fornecedor in fornecedores_filtrados:
                    criar_card_fornecedor(fornecedor, formatar_moeda_br)
            else:
                st.info("📭 Nenhum fornecedor corresponde aos filtros selecionados")
        else:
            st.success("✅ Todos os fornecedores com boa performance!")

def exibir_resumo_alertas_dashboard(alertas):
    """Exibe resumo de alertas no dashboard principal"""
    
    if alertas['total'] > 0:
        st.warning(f"⚠️ **Atenção:** Você tem {alertas['total']} alerta(s) que requerem atenção!")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if alertas['pedidos_atrasados']:
                st.error(f"🔴 {len(alertas['pedidos_atrasados'])} pedido(s) atrasado(s)")
        
        with col2:
            if alertas['pedidos_vencendo']:
                st.warning(f"⏰ {len(alertas['pedidos_vencendo'])} vencendo em 3 dias")
        
        with col3:
            if alertas['pedidos_criticos']:
                st.warning(f"🚨 {len(alertas['pedidos_criticos'])} pedido(s) crítico(s)")
        
        if st.button("🔔 Ver Todos os Alertas", use_container_width=True):
            st.session_state.pagina_alertas = True
            st.rerun()
