# ============================
# PDF PREMIUM (MELHORADO)
# Cole este bloco no seu exportacao_relatorios.py
# Substitua a classe CabecalhoRodape e a função gerar_pdf_departamento_premium
# ============================

from datetime import datetime
import io
import pandas as pd
import streamlit as st

# Se você já importou reportlab no topo, NÃO precisa repetir.
# Este bloco assume que PDF_DISPONIVEL já existe.

# --- helpers de formatação (BR) ---
def _moeda_br(v) -> str:
    try:
        v = float(v)
    except Exception:
        v = 0.0
    s = f"{v:,.2f}"
    return "R$ " + s.replace(",", "X").replace(".", ",").replace("X", ".")

def _inteiro_br(v) -> str:
    try:
        v = int(v)
    except Exception:
        v = 0
    return f"{v:,}".replace(",", ".")

# --- cabeçalho + rodapé em todas as páginas ---
class CabecalhoRodape:
    def __init__(self, titulo: str, subtitulo: str = ""):
        self.titulo = titulo
        self.subtitulo = subtitulo

    def desenhar(self, canvas_obj, doc):
        canvas_obj.saveState()

        # Cabeçalho (faixa)
        canvas_obj.setFillColor(colors.HexColor("#667eea"))
        canvas_obj.rect(
            0,
            doc.height + doc.topMargin - 2 * cm,
            doc.width + doc.leftMargin + doc.rightMargin,
            2.5 * cm,
            fill=1,
            stroke=0,
        )

        canvas_obj.setFillColor(colors.white)
        canvas_obj.setFont("Helvetica-Bold", 18)
        canvas_obj.drawString(
            doc.leftMargin,
            doc.height + doc.topMargin - 1.2 * cm,
            self.titulo,
        )

        canvas_obj.setFont("Helvetica", 10)
        if self.subtitulo:
            canvas_obj.drawString(
                doc.leftMargin,
                doc.height + doc.topMargin - 1.8 * cm,
                self.subtitulo,
            )

        # Rodapé
        canvas_obj.setStrokeColor(colors.HexColor("#667eea"))
        canvas_obj.setLineWidth(1)
        canvas_obj.line(
            doc.leftMargin,
            18 * mm,
            doc.width + doc.leftMargin,
            18 * mm,
        )

        canvas_obj.setFillColor(colors.HexColor("#334155"))
        canvas_obj.setFont("Helvetica", 9)
        canvas_obj.drawString(
            doc.leftMargin,
            12 * mm,
            f"Follow-up de Compras © {datetime.now().year}",
        )
        canvas_obj.drawRightString(
            doc.width + doc.leftMargin,
            12 * mm,
            f"Página {canvas_obj.getPageNumber()}",
        )

        canvas_obj.restoreState()


def gerar_pdf_departamento_premium(df_dept, departamento, formatar_moeda_br):
    """
    PDF Premium - Departamento (versão melhorada)
    - Cabeçalho/rodapé em todas as páginas
    - KPI bonito e moeda BR
    - Tabela com quebra de linha (Descrição) e cabeçalho repetido (LongTable)
    - Destaque visual para atrasados/pendentes pelo status (se existir)
    """
    if not PDF_DISPONIVEL:
        return None

    try:
        buffer = io.BytesIO()

        # Landscape costuma ficar melhor para tabela
        doc = SimpleDocTemplate(
            buffer,
            pagesize=landscape(A4),
            topMargin=3 * cm,
            bottomMargin=2.5 * cm,
            leftMargin=1.6 * cm,
            rightMargin=1.6 * cm,
        )

        styles = getSampleStyleSheet()

        titulo_style = ParagraphStyle(
            "titulo",
            parent=styles["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=20,
            alignment=TA_CENTER,
            textColor=colors.HexColor("#0f172a"),
            spaceAfter=10,
        )

        subtitulo_style = ParagraphStyle(
            "sub",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=10,
            alignment=TA_CENTER,
            textColor=colors.HexColor("#334155"),
            spaceAfter=12,
        )

        h2 = ParagraphStyle(
            "h2",
            parent=styles["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=14,
            textColor=colors.HexColor("#0f172a"),
            spaceBefore=6,
            spaceAfter=8,
        )

        cell_style = ParagraphStyle(
            "cell",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=8.5,
            leading=10,
            textColor=colors.HexColor("#0f172a"),
        )

        def P(txt):
            return Paragraph(str(txt).replace("\n", " "), cell_style)

        elements = []

        # Título no corpo (só uma vez)
        elements.append(Paragraph(f"Relatório por Departamento", titulo_style))
        elements.append(Paragraph(f"{departamento}", subtitulo_style))
        elements.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor("#667eea"), spaceAfter=10))

        # KPIs
        total = len(df_dept)
        valor_total = float(df_dept.get("valor_total", pd.Series([0])).fillna(0).sum())
        entregues = int((df_dept.get("entregue", pd.Series([False])) == True).sum())
        atrasados = int((df_dept.get("atrasado", pd.Series([False])) == True).sum())
        fornecedores = int(df_dept.get("fornecedor_nome", pd.Series([])).nunique())

        kpi = [
            ["MÉTRICA", "VALOR"],
            ["📦 Pedidos", _inteiro_br(total)],
            ["💰 Valor Total", _moeda_br(valor_total)],
            ["🏭 Fornecedores", _inteiro_br(fornecedores)],
            ["✅ Entregues", _inteiro_br(entregues)],
            ["⚠️ Atrasados", _inteiro_br(atrasados)],
        ]

        tabela_kpi = Table(kpi, colWidths=[7.5 * cm, 6.5 * cm])
        tabela_kpi.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#667eea")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, 0), 11),
                    ("FONTSIZE", (0, 1), (-1, -1), 10),
                    ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                    ("ALIGN", (1, 1), (1, -1), "RIGHT"),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 10),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                    ("TOPPADDING", (0, 0), (-1, -1), 8),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#f8fafc"), colors.white]),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                ]
            )
        )
        elements.append(tabela_kpi)
        elements.append(Spacer(1, 8 * mm))

        # Tabela de pedidos
        elements.append(Paragraph("Pedidos (amostra / últimos 80)", h2))

        # Use sua função existente de preparo (se existir) para padronizar colunas
        df_export = preparar_dados_exportacao(df_dept)

        # Escolha de colunas para o PDF (use apenas as que existirem)
        colunas = ["N° OC", "Fornecedor", "Descrição", "Valor (R$)", "Status", "Previsão"]
        cols_ok = [c for c in colunas if c in df_export.columns]
        if not cols_ok:
            st.warning("Sem colunas suficientes para gerar o PDF.")
            return None

        df_pdf = df_export[cols_ok].copy()

        # Limpeza e formatação
        if "Valor (R$)" in df_pdf.columns:
            # se veio numérico, formata BR; se já veio string, mantém
            df_pdf["Valor (R$)"] = df_pdf["Valor (R$)"].apply(_moeda_br)

        # Transformar descrição em Paragraph para quebrar linha
        if "Descrição" in df_pdf.columns:
            df_pdf["Descrição"] = df_pdf["Descrição"].apply(P)

        # Tratar strings nas demais
        for c in df_pdf.columns:
            if c != "Descrição":
                df_pdf[c] = df_pdf[c].astype(str).fillna("").str.strip()

        # Limitar linhas (evita PDF gigante no Cloud; ajuste se quiser)
        df_pdf = df_pdf.head(80)

        # Monta tabela (LongTable repete header)
        tabela_dados = [df_pdf.columns.tolist()] + df_pdf.values.tolist()

        # Larguras (ajuste fino se quiser)
        # Se não tiver "Previsão", redistribui.
        widths_map = {
            "N° OC": 3.2 * cm,
            "Fornecedor": 5.0 * cm,
            "Descrição": 10.0 * cm,
            "Valor (R$)": 3.6 * cm,
            "Status": 3.4 * cm,
            "Previsão": 3.2 * cm,
        }
        colWidths = [widths_map.get(c, 4.0 * cm) for c in df_pdf.columns]

        tabela = LongTable(tabela_dados, repeatRows=1, colWidths=colWidths)
        estilo = TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#764ba2")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 9),
                ("FONTSIZE", (0, 1), (-1, -1), 8.2),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#cbd5e1")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#faf5ff")]),
            ]
        )

        # Destaques por status (se existir)
        if "Status" in df_pdf.columns:
            status_idx = df_pdf.columns.tolist().index("Status")
            for i, row in enumerate(df_pdf.values.tolist(), start=1):  # 1 = após header
                status = str(row[status_idx]).lower()
                if "atras" in status:
                    estilo.add("BACKGROUND", (0, i), (-1, i), colors.HexColor("#fff1f2"))
                    estilo.add("TEXTCOLOR", (0, i), (-1, i), colors.HexColor("#b91c1c"))
                elif "pend" in status:
                    estilo.add("BACKGROUND", (0, i), (-1, i), colors.HexColor("#fffbeb"))
                    estilo.add("TEXTCOLOR", (0, i), (-1, i), colors.HexColor("#92400e"))
                elif "entreg" in status:
                    estilo.add("TEXTCOLOR", (0, i), (-1, i), colors.HexColor("#065f46"))

        tabela.setStyle(estilo)
        elements.append(tabela)

        # Build com cabeçalho/rodapé (todas as páginas)
        cab = CabecalhoRodape(
            f"Departamento: {departamento}",
            f"Gerado em {datetime.now().strftime('%d/%m/%Y %H:%M')}",
        )
        doc.build(elements, onFirstPage=cab.desenhar, onLaterPages=cab.desenhar)

        buffer.seek(0)
        return buffer

    except Exception as e:
        st.error(f"Erro ao gerar PDF (Departamento): {e}")
        return None
