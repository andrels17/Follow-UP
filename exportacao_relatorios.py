"""
Módulo de Exportação de Relatórios - VERSÃO PREMIUM
PDFs profissionais com design avançado, gráficos e análises detalhadas
"""

import streamlit as st
import pandas as pd
from datetime import datetime
import io
from reportlab.platypus import LongTable

# Importações para PDF
try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.platypus import (
        SimpleDocTemplate, Table, TableStyle, Paragraph, 
        Spacer, PageBreak, KeepTogether
    )
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm, mm
    from reportlab.pdfgen import canvas
    from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
    from reportlab.platypus.flowables import HRFlowable
    from reportlab.graphics.shapes import Drawing, Rect
    from reportlab.graphics.charts.barcharts import VerticalBarChart
    from reportlab.graphics.charts.piecharts import Pie
    from reportlab.graphics import renderPDF
    PDF_DISPONIVEL = True
except ImportError:
    PDF_DISPONIVEL = False
    st.warning("⚠️ Para exportar em PDF Premium, instale: pip install reportlab")


# ============================================
# FUNÇÕES DE INTERFACE (STREAMLIT)
# ============================================

def gerar_botoes_exportacao(df_pedidos, formatar_moeda_br):
    """Gera botões de exportação em múltiplos formatos"""
    
    st.markdown("### 📄 Exportar Relatório Completo")
    st.info("📊 Exporte todos os pedidos em formatos profissionais")
    
    col1, col2, col3 = st.columns(3)
    
    df_export = preparar_dados_exportacao(df_pedidos)
    
    with col1:
        csv = df_export.to_csv(index=False, encoding='utf-8-sig', sep=';', decimal=',')
        st.download_button(
            label="📥 Download CSV",
            data=csv,
            file_name=f"relatorio_pedidos_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv",
            use_container_width=True
        )
    
    with col2:
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            df_export.to_excel(writer, index=False, sheet_name='Pedidos')
        
        st.download_button(
            label="📊 Download Excel",
            data=buffer.getvalue(),
            file_name=f"relatorio_pedidos_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )
    
    with col3:
        if PDF_DISPONIVEL:
            if st.button("📑 PDF Premium", use_container_width=True, type="primary"):
                with st.spinner("🎨 Gerando PDF profissional..."):
                    pdf_buffer = gerar_pdf_completo_premium(df_pedidos, formatar_moeda_br)
                    if pdf_buffer:
                        st.success("✅ PDF gerado!")
                        st.download_button(
                            label="💾 Download PDF",
                            data=pdf_buffer.getvalue(),
                            file_name=f"relatorio_premium_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
                            mime="application/pdf",
                            use_container_width=True
                        )
        else:
            st.error("❌ PDF indisponível")
    
    # Estatísticas
    st.markdown("---")
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.metric("📦 Pedidos", f"{len(df_pedidos):,}".replace(',', '.'))
    
    with col2:
        st.metric("💰 Valor Total", formatar_moeda_br(df_pedidos['valor_total'].sum()))
    
    with col3:
        entregues = (df_pedidos['entregue'] == True).sum()
        st.metric("✅ Entregues", entregues)
    
    with col4:
        st.metric("⚠️ Atrasados", (df_pedidos['atrasado'] == True).sum())
    
    with col5:
        st.metric("🏭 Fornecedores", df_pedidos['fornecedor_nome'].nunique())


def criar_relatorio_executivo(df_pedidos, formatar_moeda_br):
    """Cria relatório executivo"""
    
    st.markdown("### 📊 Relatório Executivo Premium")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("📦 Pedidos", len(df_pedidos))
    
    with col2:
        st.metric("💰 Valor Total", formatar_moeda_br(df_pedidos['valor_total'].sum()))
    
    with col3:
        taxa = (df_pedidos['entregue'] == True).sum() / len(df_pedidos) * 100 if len(df_pedidos) > 0 else 0
        st.metric("📈 Taxa Entrega", f"{taxa:.1f}%".replace('.', ','))
    
    with col4:
        ticket = df_pedidos['valor_total'].sum() / len(df_pedidos) if len(df_pedidos) > 0 else 0
        st.metric("🎯 Ticket Médio", formatar_moeda_br(ticket))
    
    st.markdown("---")
    st.markdown("#### 🏢 Análise por Departamento")
    
    df_dept = df_pedidos.groupby('departamento').agg({
        'id': 'count',
        'valor_total': 'sum',
        'entregue': lambda x: (x == True).sum(),
        'atrasado': lambda x: (x == True).sum()
    }).reset_index()
    
    df_dept.columns = ['Departamento', 'Pedidos', 'Valor Total', 'Entregues', 'Atrasados']
    df_dept['Taxa (%)'] = (df_dept['Entregues'] / df_dept['Pedidos'] * 100).round(1)
    df_dept = df_dept.sort_values('Valor Total', ascending=False)
    
    st.dataframe(df_dept, use_container_width=True, hide_index=True)
    
    st.markdown("---")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        csv = df_dept.to_csv(index=False, encoding='utf-8-sig', sep=';', decimal=',')
        st.download_button("📥 CSV", csv, f"exec_{datetime.now().strftime('%Y%m%d')}.csv", "text/csv", use_container_width=True)
    
    with col2:
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            df_dept.to_excel(writer, index=False, sheet_name='Resumo')
        st.download_button("📊 Excel", buffer.getvalue(), f"exec_{datetime.now().strftime('%Y%m%d')}.xlsx", use_container_width=True)
    
    with col3:
        if PDF_DISPONIVEL and st.button("📑 PDF Premium", key="pdf_exec", use_container_width=True, type="primary"):
            with st.spinner("Gerando..."):
                pdf = gerar_pdf_executivo_premium(df_pedidos, df_dept, formatar_moeda_br)
                if pdf:
                    st.download_button("💾 Download", pdf.getvalue(), f"exec_{datetime.now().strftime('%Y%m%d')}.pdf", "application/pdf", use_container_width=True)


def gerar_relatorio_fornecedor(df_pedidos, fornecedor, formatar_moeda_br):
    """Relatório de fornecedor"""
    
    st.markdown(f"### 🏭 {fornecedor}")
    
    df_forn = df_pedidos[df_pedidos['fornecedor_nome'] == fornecedor]
    
    if df_forn.empty:
        st.warning("Nenhum pedido encontrado")
        return
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("📦 Pedidos", len(df_forn))
    
    with col2:
        st.metric("💰 Valor", formatar_moeda_br(df_forn['valor_total'].sum()))
    
    with col3:
        st.metric("✅ Entregues", (df_forn['entregue'] == True).sum())
    
    with col4:
        st.metric("⚠️ Atrasados", (df_forn['atrasado'] == True).sum())
    
    st.markdown("---")
    st.dataframe(preparar_dados_exportacao(df_forn), use_container_width=True, hide_index=True)
    
    st.markdown("---")
    col1, col2, col3 = st.columns(3)
    
    df_export = preparar_dados_exportacao(df_forn)
    
    with col1:
        csv = df_export.to_csv(index=False, encoding='utf-8-sig', sep=';', decimal=',')
        st.download_button("📥 CSV", csv, f"forn_{datetime.now().strftime('%Y%m%d')}.csv", use_container_width=True)
    
    with col2:
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            df_export.to_excel(writer, index=False)
        st.download_button("📊 Excel", buffer.getvalue(), f"forn_{datetime.now().strftime('%Y%m%d')}.xlsx", use_container_width=True)
    
    with col3:
        if PDF_DISPONIVEL and st.button("📑 PDF", key=f"pdf_f_{fornecedor}", use_container_width=True, type="primary"):
            with st.spinner("Gerando..."):
                pdf = gerar_pdf_fornecedor_premium(df_forn, fornecedor, formatar_moeda_br)
                if pdf:
                    st.download_button("💾 Download", pdf.getvalue(), f"forn_{datetime.now().strftime('%Y%m%d')}.pdf", use_container_width=True)


def gerar_relatorio_departamento(df_pedidos, departamento, formatar_moeda_br):
    """Relatório de departamento"""
    
    st.markdown(f"### 🏢 {departamento}")
    
    df_dept = df_pedidos[df_pedidos['departamento'] == departamento]
    
    if df_dept.empty:
        st.warning("Nenhum pedido encontrado")
        return
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("📦 Pedidos", len(df_dept))
    
    with col2:
        st.metric("💰 Valor", formatar_moeda_br(df_dept['valor_total'].sum()))
    
    with col3:
        st.metric("🏭 Fornecedores", df_dept['fornecedor_nome'].nunique())
    
    with col4:
        st.metric("⚠️ Atrasados", (df_dept['atrasado'] == True).sum())
    
    st.markdown("---")
    st.dataframe(preparar_dados_exportacao(df_dept), use_container_width=True, hide_index=True)
    
    st.markdown("---")
    col1, col2, col3 = st.columns(3)
    
    df_export = preparar_dados_exportacao(df_dept)
    
    with col1:
        csv = df_export.to_csv(index=False, encoding='utf-8-sig', sep=';', decimal=',')
        st.download_button("📥 CSV", csv, f"dept_{datetime.now().strftime('%Y%m%d')}.csv", use_container_width=True)
    
    with col2:
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            df_export.to_excel(writer, index=False)
        st.download_button("📊 Excel", buffer.getvalue(), f"dept_{datetime.now().strftime('%Y%m%d')}.xlsx", use_container_width=True)
    
    with col3:
        if PDF_DISPONIVEL and st.button("📑 PDF", key=f"pdf_d_{departamento}", use_container_width=True, type="primary"):
            with st.spinner("Gerando..."):
                pdf = gerar_pdf_departamento_premium(df_dept, departamento, formatar_moeda_br)
                if pdf:
                    st.download_button("💾 Download", pdf.getvalue(), f"dept_{datetime.now().strftime('%Y%m%d')}.pdf", use_container_width=True)


def preparar_dados_exportacao(df):
    """Prepara dados para exportação"""
    
    colunas = [
        'nr_oc', 'nr_solicitacao', 'departamento', 'descricao',
        'cod_material', 'cod_equipamento',
        'qtde_solicitada', 'qtde_entregue', 'qtde_pendente',
        'fornecedor_nome', 'fornecedor_cidade', 'fornecedor_uf',
        'data_solicitacao', 'data_oc', 'previsao_entrega',
        'status', 'valor_total'
    ]
    
    colunas_existentes = [c for c in colunas if c in df.columns]
    df_export = df[colunas_existentes].copy()
    
    rename = {
        'nr_oc': 'N° OC',
        'nr_solicitacao': 'N° Solicitação',
        'departamento': 'Departamento',
        'descricao': 'Descrição',
        'cod_material': 'Código',
        'cod_equipamento': 'Equipamento',
        'qtde_solicitada': 'Qtd Solicitada',
        'qtde_entregue': 'Qtd Entregue',
        'qtde_pendente': 'Qtd Pendente',
        'fornecedor_nome': 'Fornecedor',
        'fornecedor_cidade': 'Cidade',
        'fornecedor_uf': 'UF',
        'data_solicitacao': 'Data Solicitação',
        'data_oc': 'Data OC',
        'previsao_entrega': 'Previsão',
        'status': 'Status',
        'valor_total': 'Valor (R$)'
    }
    
    return df_export.rename(columns=rename)


# ============================================
# FUNÇÕES PDF PREMIUM
# ============================================

class CabecalhoRodape:
    def __init__(self, titulo, subtitulo=""):
        self.titulo = titulo
        self.subtitulo = subtitulo

    def desenhar(self, canvas_obj, doc):
        canvas_obj.saveState()

        # Cabeçalho (faixa)
        canvas_obj.setFillColor(colors.HexColor("#667eea"))
        canvas_obj.rect(0, doc.height + doc.topMargin - 2*cm,
                        doc.width + doc.leftMargin + doc.rightMargin, 2.5*cm,
                        fill=1, stroke=0)

        canvas_obj.setFillColor(colors.white)
        canvas_obj.setFont("Helvetica-Bold", 18)
        canvas_obj.drawString(doc.leftMargin, doc.height + doc.topMargin - 1.2*cm, self.titulo)

        canvas_obj.setFont("Helvetica", 10)
        canvas_obj.drawString(doc.leftMargin, doc.height + doc.topMargin - 1.8*cm, self.subtitulo)

        # Rodapé
        canvas_obj.setStrokeColor(colors.HexColor("#667eea"))
        canvas_obj.setLineWidth(1)
        canvas_obj.line(doc.leftMargin, 18*mm, doc.width + doc.leftMargin, 18*mm)

        canvas_obj.setFillColor(colors.HexColor("#334155"))
        canvas_obj.setFont("Helvetica", 9)
        canvas_obj.drawString(doc.leftMargin, 12*mm, f"Follow-up de Compras © {datetime.now().year}")
        canvas_obj.drawRightString(doc.width + doc.leftMargin, 12*mm, f"Página {canvas_obj.getPageNumber()}")

        canvas_obj.restoreState()
    
    def rodape(self, canvas_obj, doc):
        canvas_obj.saveState()
        
        # Linha decorativa
        canvas_obj.setStrokeColorRGB(0.4, 0.49, 0.92)
        canvas_obj.setLineWidth(1.5)
        canvas_obj.line(doc.leftMargin, 2*cm, doc.width + doc.leftMargin, 2*cm)
        
        # Página
        canvas_obj.setFillColorRGB(0.3, 0.3, 0.3)
        canvas_obj.setFont('Helvetica', 9)
        canvas_obj.drawRightString(doc.width + doc.leftMargin, 1.5*cm, f"Página {canvas_obj.getPageNumber()}")
        
        # Sistema
        canvas_obj.drawString(doc.leftMargin, 1.5*cm, f"Follow-up de Compras © {datetime.now().year}")
        
        canvas_obj.restoreState()


def criar_tabela_kpi(dados, cores=True):
    """Cria tabela de KPIs estilizada"""
    
    tabela = LongTable(tabela_dados, repeatRows=1, colWidths=[...])
    
    estilo = [
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#667eea')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 13),
        ('FONTSIZE', (0, 1), (-1, -1), 11),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 12),
        ('RIGHTPADDING', (0, 0), (-1, -1), 12),
        ('TOPPADDING', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
        ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#cbd5e1')),
    ]
    
    if cores:
        estilo.append(('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor('#f8fafc'), colors.white]))
    
    table.setStyle(TableStyle(estilo))
    return table

def moeda_br(v):
    try:
        v = float(v)
    except Exception:
        v = 0.0
    s = f"{v:,.2f}"
    # troca padrão US para BR
    return "R$ " + s.replace(",", "X").replace(".", ",").replace("X", ".")

def gerar_pdf_completo_premium(df_pedidos, formatar_moeda_br):
    """PDF Premium - Relatório Completo"""
    
    if not PDF_DISPONIVEL:
        return None
    
    try:
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=landscape(A4),
            topMargin=3*cm,
            bottomMargin=2.5*cm,
            leftMargin=2*cm,
            rightMargin=2*cm
        )
        
        elements = []
        styles = getSampleStyleSheet()
        
        # Título
        titulo_style = ParagraphStyle(
            'Titulo',
            parent=styles['Heading1'],
            fontSize=26,
            textColor=colors.HexColor('#1e293b'),
            spaceAfter=15,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        )
        
        elements.append(Paragraph("Relatório Completo de Pedidos", titulo_style))
        elements.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor('#667eea'), spaceAfter=15))
        
        # KPIs
        total = len(df_pedidos)
        valor = df_pedidos['valor_total'].sum()
        entregues = (df_pedidos['entregue'] == True).sum()
        atrasados = (df_pedidos['atrasado'] == True).sum()
        
        kpi_dados = [
            ['INDICADOR', 'VALOR'],
            ['📦 Total de Pedidos', f'{total:,}'.replace(',', '.')],
            ['💰 Valor Total', formatar_moeda_br(valor)],
            ['✅ Pedidos Entregues', f'{entregues:,} ({entregues/total*100:.1f}%)'.replace(',', '.')],
            ['⚠️ Pedidos Atrasados', f'{atrasados:,} ({atrasados/total*100:.1f}%)'.replace(',', '.')]
        ]
        
        elements.append(criar_tabela_kpi(kpi_dados))
        elements.append(Spacer(1, 1*cm))
        
        # Tabela de pedidos
        subtitulo = ParagraphStyle('Subtitulo', parent=styles['Heading2'], fontSize=16, spaceBefore=10, spaceAfter=10)
        elements.append(Paragraph("Histórico de Pedidos (Top 50)", subtitulo))
        
        df_export = preparar_dados_exportacao(df_pedidos.head(50))
        colunas_pdf = ['N° OC', 'Departamento', 'Descrição', 'Fornecedor', 'Valor (R$)', 'Status']
        df_pdf = df_export[[c for c in colunas_pdf if c in df_export.columns]]
        
        if 'Descrição' in df_pdf.columns:
            df_pdf['Descrição'] = df_pdf['Descrição'].astype(str).str[:35] + '...'
        
        tabela_dados = [df_pdf.columns.tolist()] + df_pdf.values.tolist()
        
        tabela = Table(tabela_dados, colWidths=[3.5*cm, 3.5*cm, 7*cm, 5*cm, 3.5*cm, 3*cm])
        tabela.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#764ba2')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e1')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#faf5ff')])
        ]))
        
        elements.append(tabela)
        
        # Gerar PDF
        cab = CabecalhoRodape(
            f"Departamento: {departamento}",
            f"Gerado em {datetime.now().strftime('%d/%m/%Y %H:%M')}"
        )
        doc.build(elements, onFirstPage=cab.desenhar, onLaterPages=cab.desenhar)
        
        buffer.seek(0)
        return buffer
        
    except Exception as e:
        st.error(f"Erro ao gerar PDF: {e}")
        return None


def gerar_pdf_executivo_premium(df_pedidos, df_resumo, formatar_moeda_br):
    """PDF Premium - Relatório Executivo"""
    
    if not PDF_DISPONIVEL:
        return None
    
    try:
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=3*cm, bottomMargin=2.5*cm)
        
        elements = []
        styles = getSampleStyleSheet()
        
        titulo_style = ParagraphStyle('Titulo', parent=styles['Heading1'], fontSize=24, alignment=TA_CENTER, fontName='Helvetica-Bold', spaceAfter=20)
        
        elements.append(Paragraph("Relatório Executivo", titulo_style))
        elements.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor('#667eea'), spaceAfter=15))
        
        # KPIs
        total = len(df_pedidos)
        valor = df_pedidos['valor_total'].sum()
        taxa = (df_pedidos['entregue'] == True).sum() / total * 100 if total > 0 else 0
        
        kpi_dados = [
            ['INDICADOR', 'VALOR'],
            ['Total de Pedidos', f'{total:,}'.replace(',', '.')],
            ['Valor Total', formatar_moeda_br(valor)],
            ['Taxa de Entrega', f'{taxa:.1f}%'],
            ['Ticket Médio', formatar_moeda_br(valor / total if total > 0 else 0)]
        ]
        
        elements.append(criar_tabela_kpi(kpi_dados))
        elements.append(Spacer(1, 1*cm))
        
        # Departamentos
        elements.append(Paragraph("Análise por Departamento", ParagraphStyle('Sub', parent=styles['Heading2'], fontSize=16, spaceAfter=10)))
        
        dept_dados = [['Departamento', 'Pedidos', 'Valor', 'Taxa (%)']]
        for _, row in df_resumo.iterrows():
            dept_dados.append([
                str(row['Departamento']),
                str(int(row['Pedidos'])),
                formatar_moeda_br(row['Valor Total']),
                f"{row['Taxa (%)']:.1f}%"
            ])
        
        dept_table = Table(dept_dados, colWidths=[6*cm, 3*cm, 4*cm, 3*cm])
        dept_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#764ba2')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('ALIGN', (1, 1), (-1, -1), 'CENTER'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e1')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#faf5ff')])
        ]))
        
        elements.append(dept_table)
        
        cabecalho_rodape = CabecalhoRodape("Relatório Executivo", datetime.now().strftime('%d/%m/%Y'))
        doc.build(elements, onFirstPage=cabecalho_rodape.cabecalho)
        
        buffer.seek(0)
        return buffer
        
    except Exception as e:
        st.error(f"Erro: {e}")
        return None


def gerar_pdf_fornecedor_premium(df_fornecedor, fornecedor, formatar_moeda_br):
    """PDF Premium - Fornecedor"""
    
    if not PDF_DISPONIVEL:
        return None
    
    try:
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=landscape(A4), topMargin=3*cm, bottomMargin=2.5*cm)
        
        elements = []
        styles = getSampleStyleSheet()
        
        elements.append(Paragraph(f"Relatório: {fornecedor}", ParagraphStyle('T', parent=styles['Heading1'], fontSize=22, alignment=TA_CENTER, fontName='Helvetica-Bold', spaceAfter=15)))
        elements.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor('#667eea'), spaceAfter=15))
        
        stats_dados = [
            ['MÉTRICA', 'VALOR'],
            ['Pedidos', f'{len(df_fornecedor):,}'.replace(',', '.')],
            ['Valor Total', formatar_moeda_br(df_fornecedor['valor_total'].sum())],
            ['Entregues', f"{(df_fornecedor['entregue'] == True).sum():,}".replace(',', '.')],
            ['Atrasados', f"{(df_fornecedor['atrasado'] == True).sum():,}".replace(',', '.')]
        ]
        
        elements.append(criar_tabela_kpi(stats_dados))
        elements.append(Spacer(1, 1*cm))
        
        df_export = preparar_dados_exportacao(df_fornecedor.head(30))
        colunas = ['N° OC', 'Departamento', 'Descrição', 'Valor (R$)', 'Status']
        df_pdf = df_export[[c for c in colunas if c in df_export.columns]]
        
        styles = getSampleStyleSheet()
        cell_style = ParagraphStyle(
            "cell",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=8,
            leading=10,
        )
        
        def p(txt):
            return Paragraph(str(txt).replace("\n", " "), cell_style)
        
        # Exemplo: aplicar só na descrição
        if "Descrição" in df_pdf.columns:
            df_pdf["Descrição"] = df_pdf["Descrição"].apply(p)
        
        tabela_dados = [df_pdf.columns.tolist()] + df_pdf.values.tolist()
        tabela = Table(tabela_dados, colWidths=[4*cm, 4*cm, 10*cm, 4*cm, 3.5*cm])
        tabela.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#764ba2')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e1')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#faf5ff')])
        ]))
        
        elements.append(tabela)
        
        cabecalho_rodape = CabecalhoRodape(f"Fornecedor: {fornecedor}", datetime.now().strftime('%d/%m/%Y'))
        doc.build(elements, onFirstPage=cabecalho_rodape.cabecalho)
        
        buffer.seek(0)
        return buffer
        
    except Exception as e:
        st.error(f"Erro: {e}")
        return None


def gerar_pdf_departamento_premium(df_dept, departamento, formatar_moeda_br):
    """PDF Premium - Departamento"""
    
    if not PDF_DISPONIVEL:
        return None
    
    try:
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=landscape(A4), topMargin=3*cm, bottomMargin=2.5*cm)
        
        elements = []
        styles = getSampleStyleSheet()
        
        elements.append(Paragraph(f"Departamento: {departamento}", ParagraphStyle('T', parent=styles['Heading1'], fontSize=22, alignment=TA_CENTER, fontName='Helvetica-Bold', spaceAfter=15)))
        elements.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor('#667eea'), spaceAfter=15))
        
        stats_dados = [
            ['MÉTRICA', 'VALOR'],
            ['Pedidos', f'{len(df_dept):,}'.replace(',', '.')],
            ['Valor Total', formatar_moeda_br(df_dept['valor_total'].sum())],
            ['Fornecedores', f"{df_dept['fornecedor_nome'].nunique():,}".replace(',', '.')],
            ['Atrasados', f"{(df_dept['atrasado'] == True).sum():,}".replace(',', '.')]
        ]
        
        elements.append(criar_tabela_kpi(stats_dados))
        elements.append(Spacer(1, 1*cm))
        
        df_export = preparar_dados_exportacao(df_dept.head(30))
        colunas = ['N° OC', 'Fornecedor', 'Descrição', 'Valor (R$)', 'Status']
        df_pdf = df_export[[c for c in colunas if c in df_export.columns]]
        
        if 'Descrição' in df_pdf.columns:
            df_pdf['Descrição'] = df_pdf['Descrição'].astype(str).str[:45] + '...'
        
        tabela_dados = [df_pdf.columns.tolist()] + df_pdf.values.tolist()
        tabela = Table(tabela_dados, colWidths=[4*cm, 5*cm, 9*cm, 4*cm, 3.5*cm])
        tabela.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#764ba2')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e1')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#faf5ff')])
        ]))
        
        elements.append(tabela)
        
        cabecalho_rodape = CabecalhoRodape(f"Departamento: {departamento}", datetime.now().strftime('%d/%m/%Y'))
        doc.build(elements, onFirstPage=cabecalho_rodape.cabecalho)
        
        buffer.seek(0)
        return buffer
        
    except Exception as e:
        st.error(f"Erro: {e}")
        return None
