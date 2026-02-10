"""
Módulo de Exportação de Relatórios - VERSÃO PREMIUM
PDFs profissionais com design avançado, gráficos e análises detalhadas
"""

import streamlit as st
import pandas as pd
from datetime import datetime
import io

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
    """Cabeçalho e rodapé premium (sem sobreposição com o conteúdo).

    Importante: o espaço do cabeçalho/rodapé deve ser reservado via topMargin/bottomMargin
    ao criar o SimpleDocTemplate (veja DEFAULT_DOC_KW).
    """

    HEADER_H = 2.6 * cm
    FOOTER_H = 1.6 * cm

    def __init__(self, titulo, subtitulo=""):
        self.titulo = titulo
        self.subtitulo = subtitulo or ""

    def _draw_header(self, canvas_obj):
        page_w, page_h = canvas_obj._pagesize

        # Fundo do cabeçalho (dentro da área de margem superior)
        canvas_obj.setFillColorRGB(0.4, 0.49, 0.92)  # #667eea
        canvas_obj.rect(0, page_h - self.HEADER_H, page_w, self.HEADER_H, fill=1, stroke=0)

        # Título
        canvas_obj.setFillColorRGB(1, 1, 1)
        canvas_obj.setFont('Helvetica-Bold', 18)
        canvas_obj.drawString(2 * cm, page_h - 1.15 * cm, self.titulo)

        # Subtítulo
        if self.subtitulo:
            canvas_obj.setFont('Helvetica', 10.5)
            canvas_obj.drawString(2 * cm, page_h - 1.85 * cm, self.subtitulo)

    def _draw_footer(self, canvas_obj):
        page_w, _ = canvas_obj._pagesize

        # Linha decorativa
        y = self.FOOTER_H + 0.45 * cm
        canvas_obj.setStrokeColorRGB(0.4, 0.49, 0.92)
        canvas_obj.setLineWidth(1.2)
        canvas_obj.line(2 * cm, y, page_w - 2 * cm, y)

        # Textos
        canvas_obj.setFillColorRGB(0.3, 0.3, 0.3)
        canvas_obj.setFont('Helvetica', 9)
        canvas_obj.drawString(2 * cm, 0.9 * cm, f"Follow-up de Compras © {datetime.now().year}")
        canvas_obj.drawRightString(page_w - 2 * cm, 0.9 * cm, f"Página {canvas_obj.getPageNumber()}")

    def on_page(self, canvas_obj, doc):
        canvas_obj.saveState()
        self._draw_header(canvas_obj)
        self._draw_footer(canvas_obj)
        canvas_obj.restoreState()

# ============================================
# HELPERS DE LAYOUT (ANTI-SOBREPOSIÇÃO)
# ============================================

# Margens padrão (reservam espaço real para cabeçalho/rodapé do CabecalhoRodape)
DEFAULT_DOC_KW = dict(
    topMargin=CabecalhoRodape.HEADER_H + 1.0 * cm,
    bottomMargin=CabecalhoRodape.FOOTER_H + 1.0 * cm,
    leftMargin=2.0 * cm,
    rightMargin=2.0 * cm,
)

def _safe_money(v, formatar_moeda_br):
    """Formata valores monetários e evita '0.0' poluindo o relatório."""
    try:
        if v is None:
            return "-"
        fv = float(v)
        if fv <= 0:
            return "-"
        return formatar_moeda_br(fv)
    except Exception:
        return "-"

def _chunk_df(df, rows_per_page):
    for i in range(0, len(df), rows_per_page):
        yield df.iloc[i:i+rows_per_page]

def criar_tabela_kpi(dados, cores=True):
    """Cria tabela de KPIs estilizada"""
    
    table = Table(dados, colWidths=[8*cm, 6*cm])
    
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


def gerar_pdf_completo_premium(df_pedidos, formatar_moeda_br):
    """PDF Premium - Relatório Completo (V3: paginação, quebra de linha, anti-sobreposição)."""

    if not PDF_DISPONIVEL:
        return None

    try:
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=landscape(A4),
            **DEFAULT_DOC_KW
        )

        elements = []
        styles = getSampleStyleSheet()

        titulo_style = ParagraphStyle(
            'Titulo',
            parent=styles['Heading1'],
            fontSize=22,
            textColor=colors.HexColor('#1e293b'),
            spaceAfter=10,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        )
        elements.append(Paragraph("Relatório Completo de Pedidos", titulo_style))
        elements.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor('#667eea'), spaceAfter=12))

        # KPIs
        total = len(df_pedidos)
        valor = df_pedidos['valor_total'].sum() if 'valor_total' in df_pedidos.columns else 0
        entregues = (df_pedidos['entregue'] == True).sum() if 'entregue' in df_pedidos.columns else 0
        atrasados = (df_pedidos['atrasado'] == True).sum() if 'atrasado' in df_pedidos.columns else 0

        kpi_dados = [
            ['INDICADOR', 'VALOR'],
            ['📦 Total de Pedidos', f'{total:,}'.replace(',', '.')],
            ['💰 Valor Total', _safe_money(valor, formatar_moeda_br)],
            ['✅ Pedidos Entregues', f'{entregues:,} ({(entregues/total*100 if total else 0):.1f}%)'.replace(',', '.')],
            ['⚠️ Pedidos Atrasados', f'{atrasados:,} ({(atrasados/total*100 if total else 0):.1f}%)'.replace(',', '.')],
        ]
        elements.append(criar_tabela_kpi(kpi_dados))
        elements.append(Spacer(1, 0.6 * cm))

        # Gráfico (Top fornecedores)
        graf = criar_grafico_barras_fornecedores(df_pedidos, doc_width_cm=24, max_itens=8)
        if graf is not None:
            elements.append(Paragraph("Top Fornecedores por Valor (R$)", ParagraphStyle('Sub', parent=styles['Heading2'], fontSize=14, spaceAfter=6)))
            elements.append(KeepTogether([graf, Spacer(1, 0.6 * cm)]))

        # Detalhamento com paginação
        elements.append(PageBreak())
        elements.append(Paragraph("Detalhamento de Pedidos", ParagraphStyle('Sub2', parent=styles['Heading2'], fontSize=14, spaceAfter=8)))

        df_export = preparar_dados_exportacao(df_pedidos)
        # Colunas padrão
        colunas_pdf = ['N° OC', 'Departamento', 'Fornecedor', 'Descrição', 'Valor (R$)', 'Status']
        cols = [c for c in colunas_pdf if c in df_export.columns]
        df_pdf = df_export[cols].copy()

        # Estilos de parágrafo (quebra de linha)
        desc_style = ParagraphStyle('Desc', parent=styles['BodyText'], fontSize=8, leading=10)
        forn_style = ParagraphStyle('Forn', parent=styles['BodyText'], fontSize=8, leading=10)

        # Converter para flowables
        rows = []
        for _, r in df_pdf.iterrows():
            row = []
            for c in df_pdf.columns:
                if c == 'Descrição':
                    row.append(Paragraph(str(r[c]), desc_style))
                elif c == 'Fornecedor':
                    row.append(Paragraph(str(r[c]), forn_style))
                elif c == 'Valor (R$)':
                    row.append(_safe_money(r[c], formatar_moeda_br))
                else:
                    row.append(str(r[c]))
            rows.append(row)

        df_flow = pd.DataFrame(rows, columns=df_pdf.columns)

        # Paginador (linhas por página)
        rows_per_page = 18
        col_widths = [3.0*cm, 3.6*cm, 5.0*cm, 10.5*cm, 3.2*cm, 3.2*cm]
        atraso_mask = None
        if 'atrasado' in df_pedidos.columns:
            # tenta alinhar por índice; fallback sem destaque se não casar
            try:
                atraso_mask = df_pedidos['atrasado'].astype(bool).tolist()
            except Exception:
                atraso_mask = None

        for page_i, chunk in enumerate(_chunk_df(df_flow, rows_per_page)):
            if page_i > 0:
                elements.append(PageBreak())
                elements.append(Paragraph("Detalhamento de Pedidos (continuação)", ParagraphStyle('Sub3', parent=styles['Heading2'], fontSize=12, spaceAfter=8)))

            # máscara do chunk (se existir)
            mask_chunk = None
            if atraso_mask is not None and len(atraso_mask) >= (page_i*rows_per_page + len(chunk)):
                mask_chunk = atraso_mask[page_i*rows_per_page : page_i*rows_per_page + len(chunk)]

            elements.append(_tabela_detalhamento(chunk, col_widths, atraso_mask=mask_chunk))
            elements.append(Spacer(1, 0.3*cm))

        cab = CabecalhoRodape("Follow-up de Compras", f"Gerado em {datetime.now().strftime('%d/%m/%Y às %H:%M')}")
        doc.build(elements, onFirstPage=cab.on_page, onLaterPages=cab.on_page)

        buffer.seek(0)
        return buffer

    except Exception as e:
        st.error(f"Erro ao gerar PDF: {e}")
        return None


def gerar_pdf_fornecedor_premium(df_fornecedor, fornecedor, formatar_moeda_br):
    """PDF Premium - Fornecedor (V3)."""

    if not PDF_DISPONIVEL:
        return None

    try:
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=landscape(A4),
            **DEFAULT_DOC_KW
        )

        elements = []
        styles = getSampleStyleSheet()

        elements.append(Paragraph(f"Relatório: {fornecedor}", ParagraphStyle('T', parent=styles['Heading1'], fontSize=20, alignment=TA_CENTER, fontName='Helvetica-Bold', spaceAfter=10)))
        elements.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor('#667eea'), spaceAfter=10))

        stats_dados = [
            ['MÉTRICA', 'VALOR'],
            ['Pedidos', f'{len(df_fornecedor):,}'.replace(',', '.')],
            ['Valor Total', _safe_money(df_fornecedor['valor_total'].sum() if 'valor_total' in df_fornecedor.columns else 0, formatar_moeda_br)],
            ['Entregues', f"{(df_fornecedor['entregue'] == True).sum() if 'entregue' in df_fornecedor.columns else 0:,}".replace(',', '.')],
            ['Atrasados', f"{(df_fornecedor['atrasado'] == True).sum() if 'atrasado' in df_fornecedor.columns else 0:,}".replace(',', '.')],
        ]
        elements.append(criar_tabela_kpi(stats_dados))
        elements.append(Spacer(1, 0.6 * cm))

        # Gráfico (Top itens por valor dentro do fornecedor) – opcional
        graf = criar_grafico_barras_fornecedores(df_fornecedor, doc_width_cm=24, max_itens=6)
        if graf is not None:
            elements.append(Paragraph("Top (por valor) dentro do fornecedor", ParagraphStyle('Sub', parent=styles['Heading2'], fontSize=14, spaceAfter=6)))
            elements.append(KeepTogether([graf, Spacer(1, 0.6 * cm)]))

        # Detalhamento
        elements.append(PageBreak())
        elements.append(Paragraph("Detalhamento de Pedidos", ParagraphStyle('Sub2', parent=styles['Heading2'], fontSize=14, spaceAfter=8)))

        df_export = preparar_dados_exportacao(df_fornecedor)
        colunas = ['N° OC', 'Departamento', 'Fornecedor', 'Descrição', 'Valor (R$)', 'Status']
        cols = [c for c in colunas if c in df_export.columns]
        df_pdf = df_export[cols].copy()

        desc_style = ParagraphStyle('Desc', parent=styles['BodyText'], fontSize=8, leading=10)
        forn_style = ParagraphStyle('Forn', parent=styles['BodyText'], fontSize=8, leading=10)

        rows = []
        for _, r in df_pdf.iterrows():
            row = []
            for c in df_pdf.columns:
                if c == 'Descrição':
                    row.append(Paragraph(str(r[c]), desc_style))
                elif c == 'Fornecedor':
                    row.append(Paragraph(str(r[c]), forn_style))
                elif c == 'Valor (R$)':
                    row.append(_safe_money(r[c], formatar_moeda_br))
                else:
                    row.append(str(r[c]))
            rows.append(row)

        df_flow = pd.DataFrame(rows, columns=df_pdf.columns)

        rows_per_page = 18
        col_widths = [3.0*cm, 3.6*cm, 5.0*cm, 10.5*cm, 3.2*cm, 3.2*cm]

        atraso_mask = None
        if 'atrasado' in df_fornecedor.columns:
            try:
                atraso_mask = df_fornecedor['atrasado'].astype(bool).tolist()
            except Exception:
                atraso_mask = None

        for page_i, chunk in enumerate(_chunk_df(df_flow, rows_per_page)):
            if page_i > 0:
                elements.append(PageBreak())
                elements.append(Paragraph("Detalhamento de Pedidos (continuação)", ParagraphStyle('Sub3', parent=styles['Heading2'], fontSize=12, spaceAfter=8)))

            mask_chunk = None
            if atraso_mask is not None and len(atraso_mask) >= (page_i*rows_per_page + len(chunk)):
                mask_chunk = atraso_mask[page_i*rows_per_page : page_i*rows_per_page + len(chunk)]

            elements.append(_tabela_detalhamento(chunk, col_widths, atraso_mask=mask_chunk))
            elements.append(Spacer(1, 0.3*cm))

        cab = CabecalhoRodape(f"Fornecedor: {fornecedor}", f"Gerado em {datetime.now().strftime('%d/%m/%Y às %H:%M')}")
        doc.build(elements, onFirstPage=cab.on_page, onLaterPages=cab.on_page)

        buffer.seek(0)
        return buffer

    except Exception as e:
        st.error(f"Erro: {e}")
        return None


def gerar_pdf_departamento_premium(df_dept, departamento, formatar_moeda_br):
    """PDF Premium - Departamento (V3: anti-sobreposição + paginação)."""

    if not PDF_DISPONIVEL:
        return None

    try:
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=landscape(A4),
            **DEFAULT_DOC_KW
        )

        elements = []
        styles = getSampleStyleSheet()

        elements.append(Paragraph(f"Departamento: {departamento}", ParagraphStyle('T', parent=styles['Heading1'], fontSize=20, alignment=TA_CENTER, fontName='Helvetica-Bold', spaceAfter=10)))
        elements.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor('#667eea'), spaceAfter=10))

        stats_dados = [
            ['MÉTRICA', 'VALOR'],
            ['Pedidos', f'{len(df_dept):,}'.replace(',', '.')],
            ['Valor Total', _safe_money(df_dept['valor_total'].sum() if 'valor_total' in df_dept.columns else 0, formatar_moeda_br)],
            ['Fornecedores', f"{df_dept['fornecedor_nome'].nunique() if 'fornecedor_nome' in df_dept.columns else 0:,}".replace(',', '.')],
            ['Atrasados', f"{(df_dept['atrasado'] == True).sum() if 'atrasado' in df_dept.columns else 0:,}".replace(',', '.')],
        ]
        elements.append(criar_tabela_kpi(stats_dados))
        elements.append(Spacer(1, 0.6 * cm))

        # Gráfico fixo com tamanho previsível + KeepTogether
        graf = criar_grafico_barras_fornecedores(df_dept, doc_width_cm=24, max_itens=8)
        if graf is not None:
            elements.append(Paragraph("Top Fornecedores por Valor (R$)", ParagraphStyle('Sub', parent=styles['Heading2'], fontSize=14, spaceAfter=6)))
            elements.append(KeepTogether([graf, Spacer(1, 0.4 * cm)]))

        # Começa detalhamento sempre em nova página (evita colidir com gráfico)
        elements.append(PageBreak())
        elements.append(Paragraph("Detalhamento de Pedidos", ParagraphStyle('Sub2', parent=styles['Heading2'], fontSize=14, spaceAfter=8)))

        df_export = preparar_dados_exportacao(df_dept)
        colunas = ['N° OC', 'Fornecedor', 'Descrição', 'Valor (R$)', 'Status']
        cols = [c for c in colunas if c in df_export.columns]
        df_pdf = df_export[cols].copy()

        desc_style = ParagraphStyle('Desc', parent=styles['BodyText'], fontSize=8, leading=10)
        forn_style = ParagraphStyle('Forn', parent=styles['BodyText'], fontSize=8, leading=10)

        rows = []
        for _, r in df_pdf.iterrows():
            row = []
            for c in df_pdf.columns:
                if c == 'Descrição':
                    row.append(Paragraph(str(r[c]), desc_style))
                elif c == 'Fornecedor':
                    row.append(Paragraph(str(r[c]), forn_style))
                elif c == 'Valor (R$)':
                    row.append(_safe_money(r[c], formatar_moeda_br))
                else:
                    row.append(str(r[c]))
            rows.append(row)

        df_flow = pd.DataFrame(rows, columns=df_pdf.columns)

        rows_per_page = 18
        col_widths = [3.0*cm, 6.0*cm, 12.0*cm, 3.4*cm, 3.0*cm]

        atraso_mask = None
        if 'atrasado' in df_dept.columns:
            try:
                atraso_mask = df_dept['atrasado'].astype(bool).tolist()
            except Exception:
                atraso_mask = None

        for page_i, chunk in enumerate(_chunk_df(df_flow, rows_per_page)):
            if page_i > 0:
                elements.append(PageBreak())
                elements.append(Paragraph("Detalhamento de Pedidos (continuação)", ParagraphStyle('Sub3', parent=styles['Heading2'], fontSize=12, spaceAfter=8)))

            mask_chunk = None
            if atraso_mask is not None and len(atraso_mask) >= (page_i*rows_per_page + len(chunk)):
                mask_chunk = atraso_mask[page_i*rows_per_page : page_i*rows_per_page + len(chunk)]

            elements.append(_tabela_detalhamento(chunk, col_widths, atraso_mask=mask_chunk))
            elements.append(Spacer(1, 0.3*cm))

        cabecalho_rodape = CabecalhoRodape(f"Departamento: {departamento}", f"Gerado em {datetime.now().strftime('%d/%m/%Y às %H:%M')}")
        doc.build(elements, onFirstPage=cabecalho_rodape.on_page, onLaterPages=cabecalho_rodape.on_page)

        buffer.seek(0)
        return buffer

    except Exception as e:
        st.error(f"Erro: {e}")
        return None

