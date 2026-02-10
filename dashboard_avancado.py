"""
Módulo de Dashboard Avançado
Gráficos interativos e análises preditivas
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta

def criar_grafico_evolucao_temporal(df_pedidos, formatar_moeda_br):
    """Cria gráfico de linha com evolução de pedidos e valores ao longo do tempo"""
    
    st.subheader("📈 Evolução Temporal de Pedidos e Valores")
    
    # Validar se há dados
    if df_pedidos.empty or 'data_solicitacao' not in df_pedidos.columns:
        st.info("📭 Dados insuficientes para gerar o gráfico de evolução temporal")
        return
    
    # Preparar dados
    df_temporal = df_pedidos.copy()
    
    # Remover valores nulos
    df_temporal = df_temporal[df_temporal['data_solicitacao'].notna()].copy()
    
    if df_temporal.empty:
        st.info("📭 Não há pedidos com data de solicitação válida")
        return
    
    # Converter para datetime se ainda não for
    try:
        if not pd.api.types.is_datetime64_any_dtype(df_temporal['data_solicitacao']):
            df_temporal['data_solicitacao'] = pd.to_datetime(df_temporal['data_solicitacao'], errors='coerce')
            # Remover valores que não puderam ser convertidos
            df_temporal = df_temporal[df_temporal['data_solicitacao'].notna()].copy()
            
        if df_temporal.empty:
            st.info("📭 Não há pedidos com data de solicitação válida")
            return
    except Exception as e:
        st.error(f"Erro ao processar datas: {e}")
        return
    
    df_temporal['mes_ano'] = df_temporal['data_solicitacao'].dt.to_period('M')
    
    # Agrupar por mês
    df_agrupado = df_temporal.groupby('mes_ano').agg({
        'id': 'count',
        'valor_total': 'sum'
    }).reset_index()
    
    df_agrupado['mes_ano_str'] = df_agrupado['mes_ano'].astype(str)
    
    # Criar figura com dois eixos Y
    fig = go.Figure()
    
    # Linha de quantidade de pedidos
    fig.add_trace(go.Scatter(
        x=df_agrupado['mes_ano_str'],
        y=df_agrupado['id'],
        name='Quantidade de Pedidos',
        mode='lines+markers',
        line=dict(color='#667eea', width=3),
        marker=dict(size=10, color='#667eea'),
        yaxis='y',
        hovertemplate='<b>%{x}</b><br>Pedidos: %{y}<extra></extra>'
    ))
    
    # Linha de valor total
    fig.add_trace(go.Scatter(
        x=df_agrupado['mes_ano_str'],
        y=df_agrupado['valor_total'],
        name='Valor Total (R$)',
        mode='lines+markers',
        line=dict(color='#f093fb', width=3, dash='dot'),
        marker=dict(size=10, color='#f093fb', symbol='diamond'),
        yaxis='y2',
        hovertemplate='<b>%{x}</b><br>Valor: R$ %{y:,.2f}<extra></extra>'
    ))
    
    # Layout com dois eixos Y
    fig.update_layout(
        xaxis=dict(
            title='Mês/Ano',
            titlefont=dict(color='white'),
            tickfont=dict(color='white'),
            showgrid=True,
            gridcolor='#2d3748'
        ),
        yaxis=dict(
            title='Quantidade de Pedidos',
            titlefont=dict(color='#667eea'),
            tickfont=dict(color='#667eea'),
            showgrid=True,
            gridcolor='#2d3748'
        ),
        yaxis2=dict(
            title='Valor Total (R$)',
            titlefont=dict(color='#f093fb'),
            tickfont=dict(color='#f093fb'),
            overlaying='y',
            side='right',
            showgrid=False
        ),
        height=450,
        hovermode='x unified',
        paper_bgcolor='#0e1117',
        plot_bgcolor='#1a1d29',
        font=dict(color='white'),
        legend=dict(
            orientation='h',
            yanchor='bottom',
            y=1.02,
            xanchor='right',
            x=1,
            bgcolor='rgba(0,0,0,0.5)',
            bordercolor='white',
            borderwidth=1
        )
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Calcular tendências
    if len(df_agrupado) >= 2:
        variacao_pedidos = ((df_agrupado['id'].iloc[-1] - df_agrupado['id'].iloc[-2]) / df_agrupado['id'].iloc[-2] * 100)
        variacao_valor = ((df_agrupado['valor_total'].iloc[-1] - df_agrupado['valor_total'].iloc[-2]) / df_agrupado['valor_total'].iloc[-2] * 100)
        
        col1, col2 = st.columns(2)
        with col1:
            delta_pedidos = f"+{variacao_pedidos:.1f}%" if variacao_pedidos > 0 else f"{variacao_pedidos:.1f}%"
            st.metric(
                "📊 Variação de Pedidos (mês anterior)",
                f"{int(df_agrupado['id'].iloc[-1])} pedidos",
                delta=delta_pedidos.replace('.', ',')
            )
        
        with col2:
            delta_valor = f"+{variacao_valor:.1f}%" if variacao_valor > 0 else f"{variacao_valor:.1f}%"
            st.metric(
                "💰 Variação de Valor (mês anterior)",
                formatar_moeda_br(df_agrupado['valor_total'].iloc[-1]),
                delta=delta_valor.replace('.', ',')
            )

def criar_funil_conversao(df_pedidos):
    """Cria gráfico de funil de conversão de pedidos"""
    
    st.subheader("🎯 Funil de Conversão de Pedidos")
    
    total_pedidos = len(df_pedidos)
    em_transito = len(df_pedidos[df_pedidos['status'] == 'Em trânsito'])
    entregues = len(df_pedidos[df_pedidos['entregue'] == True])
    no_prazo = len(df_pedidos[(df_pedidos['entregue'] == True) & (df_pedidos['atrasado'] == False)])
    
    fig = go.Figure(go.Funnel(
        y=['Pedidos Realizados', 'Em Trânsito', 'Entregues', 'Entregues no Prazo'],
        x=[total_pedidos, em_transito, entregues, no_prazo],
        textposition="inside",
        textinfo="value+percent initial",
        marker=dict(
            color=['#667eea', '#764ba2', '#f093fb', '#00d4ff'],
            line=dict(width=2, color='#0e1117')
        ),
        connector=dict(line=dict(color='#2d3748', width=2))
    ))
    
    fig.update_layout(
        height=400,
        paper_bgcolor='#0e1117',
        plot_bgcolor='#1a1d29',
        font=dict(color='white', size=14)
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Taxa de conversão
    col1, col2, col3 = st.columns(3)
    
    with col1:
        taxa_entrega = (entregues / total_pedidos * 100) if total_pedidos > 0 else 0
        st.metric("Taxa de Entrega", f"{taxa_entrega:.1f}%".replace('.', ','))
    
    with col2:
        taxa_prazo = (no_prazo / entregues * 100) if entregues > 0 else 0
        st.metric("Entregas no Prazo", f"{taxa_prazo:.1f}%".replace('.', ','))
    
    with col3:
        taxa_transito = (em_transito / total_pedidos * 100) if total_pedidos > 0 else 0
        st.metric("Em Trânsito", f"{taxa_transito:.1f}%".replace('.', ','))

def criar_heatmap_pedidos(df_pedidos):
    """Cria heatmap de pedidos por dia da semana e hora"""
    
    st.subheader("🔥 Mapa de Calor - Pedidos por Dia e Período")
    
    df_heat = df_pedidos.copy()
    
    # Validar se há dados
    if df_heat.empty or 'data_solicitacao' not in df_heat.columns:
        st.info("📭 Dados insuficientes para gerar o mapa de calor")
        return
    
    # Remover valores nulos
    df_heat = df_heat[df_heat['data_solicitacao'].notna()].copy()
    
    if df_heat.empty:
        st.info("📭 Não há pedidos com data de solicitação válida")
        return
    
    # Converter para datetime se ainda não for
    try:
        if not pd.api.types.is_datetime64_any_dtype(df_heat['data_solicitacao']):
            df_heat['data_solicitacao'] = pd.to_datetime(df_heat['data_solicitacao'], errors='coerce')
            # Remover valores que não puderam ser convertidos
            df_heat = df_heat[df_heat['data_solicitacao'].notna()].copy()
            
        if df_heat.empty:
            st.info("📭 Não há pedidos com data de solicitação válida")
            return
    except Exception as e:
        st.error(f"Erro ao processar datas: {e}")
        return
    
    df_heat['dia_semana'] = df_heat['data_solicitacao'].dt.day_name()
    df_heat['hora'] = df_heat['data_solicitacao'].dt.hour
    
    # Mapear dias para português
    dias_pt = {
        'Monday': 'Segunda',
        'Tuesday': 'Terça',
        'Wednesday': 'Quarta',
        'Thursday': 'Quinta',
        'Friday': 'Sexta',
        'Saturday': 'Sábado',
        'Sunday': 'Domingo'
    }
    df_heat['dia_semana'] = df_heat['dia_semana'].map(dias_pt)
    
    # Categorizar períodos do dia
    def categorizar_periodo(hora):
        if 6 <= hora < 12:
            return 'Manhã (6h-12h)'
        elif 12 <= hora < 18:
            return 'Tarde (12h-18h)'
        elif 18 <= hora < 24:
            return 'Noite (18h-24h)'
        else:
            return 'Madrugada (0h-6h)'
    
    df_heat['periodo'] = df_heat['hora'].apply(categorizar_periodo)
    
    # Agrupar
    heatmap_data = df_heat.groupby(['dia_semana', 'periodo']).size().reset_index(name='quantidade')
    
    # Pivot para matriz
    ordem_dias = ['Segunda', 'Terça', 'Quarta', 'Quinta', 'Sexta', 'Sábado', 'Domingo']
    ordem_periodos = ['Manhã (6h-12h)', 'Tarde (12h-18h)', 'Noite (18h-24h)', 'Madrugada (0h-6h)']
    
    pivot_data = heatmap_data.pivot(index='dia_semana', columns='periodo', values='quantidade').fillna(0)
    
    # Reindexar linhas (dias) e colunas (períodos) para garantir que todas existam
    pivot_data = pivot_data.reindex(index=ordem_dias, columns=ordem_periodos, fill_value=0)
    
    # Criar heatmap
    fig = go.Figure(data=go.Heatmap(
        z=pivot_data.values,
        x=pivot_data.columns,
        y=pivot_data.index,
        colorscale='Purples',
        text=pivot_data.values,
        texttemplate='%{text}',
        textfont=dict(size=14, color='white'),
        hovertemplate='<b>%{y}</b><br>%{x}<br>Pedidos: %{z}<extra></extra>',
        colorbar=dict(
            title='Pedidos',
            titlefont=dict(color='white'),
            tickfont=dict(color='white'),
            bgcolor='rgba(0,0,0,0.6)',
            bordercolor='white',
            borderwidth=2
        )
    ))
    
    fig.update_layout(
        height=400,
        xaxis=dict(title='Período do Dia', titlefont=dict(color='white'), tickfont=dict(color='white')),
        yaxis=dict(title='Dia da Semana', titlefont=dict(color='white'), tickfont=dict(color='white')),
        paper_bgcolor='#0e1117',
        plot_bgcolor='#1a1d29',
        font=dict(color='white')
    )
    
    st.plotly_chart(fig, use_container_width=True)

def criar_comparativo_periodos(df_pedidos, formatar_moeda_br):
    """Cria comparativo entre períodos (mensal/trimestral)"""
    
    st.subheader("📊 Comparativo de Períodos")
    
    # Validar se há dados
    if df_pedidos.empty or 'data_solicitacao' not in df_pedidos.columns:
        st.info("📭 Dados insuficientes para gerar o comparativo de períodos")
        return
    
    col1, col2 = st.columns(2)
    
    with col1:
        tipo_periodo = st.selectbox(
            "Selecione o período:",
            ["Mensal", "Trimestral"],
            key="periodo_comparativo"
        )
    
    with col2:
        metrica = st.selectbox(
            "Métrica:",
            ["Quantidade de Pedidos", "Valor Total"],
            key="metrica_comparativo"
        )
    
    # Preparar dados
    df_comp = df_pedidos.copy()
    
    # Remover valores nulos
    df_comp = df_comp[df_comp['data_solicitacao'].notna()].copy()
    
    if df_comp.empty:
        st.info("📭 Não há pedidos com data de solicitação válida")
        return
    
    # Converter para datetime se ainda não for
    try:
        if not pd.api.types.is_datetime64_any_dtype(df_comp['data_solicitacao']):
            df_comp['data_solicitacao'] = pd.to_datetime(df_comp['data_solicitacao'], errors='coerce')
            # Remover valores que não puderam ser convertidos
            df_comp = df_comp[df_comp['data_solicitacao'].notna()].copy()
            
        if df_comp.empty:
            st.info("📭 Não há pedidos com data de solicitação válida")
            return
    except Exception as e:
        st.error(f"Erro ao processar datas: {e}")
        return
    
    if tipo_periodo == "Mensal":
        df_comp['periodo'] = df_comp['data_solicitacao'].dt.to_period('M').astype(str)
    else:  # Trimestral
        df_comp['periodo'] = df_comp['data_solicitacao'].dt.to_period('Q').astype(str)
    
    if metrica == "Quantidade de Pedidos":
        df_agrupado = df_comp.groupby('periodo').size().reset_index(name='valor')
        titulo_y = 'Quantidade de Pedidos'
    else:
        df_agrupado = df_comp.groupby('periodo')['valor_total'].sum().reset_index(name='valor')
        titulo_y = 'Valor Total (R$)'
    
    # Criar gráfico de barras com comparação
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        x=df_agrupado['periodo'],
        y=df_agrupado['valor'],
        marker=dict(
            color=df_agrupado['valor'],
            colorscale='Purples',
            line=dict(color='#ffffff', width=2)
        ),
        text=df_agrupado['valor'].apply(lambda x: formatar_moeda_br(x) if metrica == "Valor Total" else f"{int(x)}"),
        textposition='outside',
        hovertemplate='<b>%{x}</b><br>' + titulo_y + ': %{text}<extra></extra>'
    ))
    
    # Adicionar linha de média
    media = df_agrupado['valor'].mean()
    fig.add_hline(
        y=media,
        line_dash="dash",
        line_color="#00d4ff",
        annotation_text=f"Média: {formatar_moeda_br(media) if metrica == 'Valor Total' else f'{int(media)}'}",
        annotation_position="right",
        annotation_font_color="#00d4ff"
    )
    
    fig.update_layout(
        xaxis=dict(title='Período', titlefont=dict(color='white'), tickfont=dict(color='white')),
        yaxis=dict(title=titulo_y, titlefont=dict(color='white'), tickfont=dict(color='white'), gridcolor='#2d3748'),
        height=450,
        showlegend=False,
        paper_bgcolor='#0e1117',
        plot_bgcolor='#1a1d29',
        font=dict(color='white')
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Estatísticas do período
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("📈 Máximo", formatar_moeda_br(df_agrupado['valor'].max()) if metrica == "Valor Total" else f"{int(df_agrupado['valor'].max())}")
    
    with col2:
        st.metric("📉 Mínimo", formatar_moeda_br(df_agrupado['valor'].min()) if metrica == "Valor Total" else f"{int(df_agrupado['valor'].min())}")
    
    with col3:
        st.metric("📊 Média", formatar_moeda_br(df_agrupado['valor'].mean()) if metrica == "Valor Total" else f"{int(df_agrupado['valor'].mean())}")
    
    with col4:
        desvio = df_agrupado['valor'].std()
        st.metric("📏 Desvio Padrão", formatar_moeda_br(desvio) if metrica == "Valor Total" else f"{int(desvio)}")

def exibir_dashboard_avancado(df_pedidos, formatar_moeda_br):
    """Exibe o dashboard avançado completo"""
    
    st.title("📊 Dashboard Avançado")
    
    if df_pedidos.empty:
        st.info("📭 Nenhum pedido cadastrado ainda")
        return
    
    # Evolução Temporal
    criar_grafico_evolucao_temporal(df_pedidos, formatar_moeda_br)
    
    st.markdown("---")
    
    # Funil de Conversão
    criar_funil_conversao(df_pedidos)
    
    st.markdown("---")
    
    # Heatmap
    criar_heatmap_pedidos(df_pedidos)
    
    st.markdown("---")
    
    # Comparativo de Períodos
    criar_comparativo_periodos(df_pedidos, formatar_moeda_br)
