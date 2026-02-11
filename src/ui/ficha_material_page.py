"""Tela: Ficha de material."""
from __future__ import annotations

from datetime import datetime

import pandas as pd
import streamlit as st

import ficha_material as fm
from src.repositories.pedidos import carregar_pedidos
from src.utils.formatting import formatar_moeda_br

import inspect

def _call_insights_automaticos(historico: pd.DataFrame, material_atual: dict) -> None:
    """Chama fm.criar_insights_automaticos de forma compatível com diferentes assinaturas."""
    fn = getattr(fm, "criar_insights_automaticos", None)
    if fn is None:
        return

    try:
        sig = inspect.signature(fn)
        params = [
            p for p in sig.parameters.values()
            if p.kind in (p.POSITIONAL_ONLY, p.POSITIONAL_OR_KEYWORD)
        ]
        n = len(params)
    except Exception:
        n = 2

    try:
        if n >= 2:
            fn(historico, material_atual)
        elif n == 1:
            fn(historico)
        else:
            fn()
        return
    except TypeError:
        pass
    except Exception as e:
        st.warning(f"⚠️ Erro ao gerar insights automáticos: {e}")
        return

    for args in ((historico,), (material_atual,), ()):
        try:
            fn(*args)
            return
        except Exception:
            continue

    st.warning("⚠️ Não foi possível gerar insights automáticos (assinatura incompatível).")



@st.cache_data(ttl=300)
def _carregar_pedidos_cache(_supabase):
    # Cache simples para deixar a página mais rápida e reduzir chamadas ao banco
    return carregar_pedidos(_supabase)


def _pick_col(df: pd.DataFrame, candidates: list[str]) -> str | None:
    """Retorna a primeira coluna existente no df dentre as candidatas."""
    for c in candidates:
        if c in df.columns:
            return c
    return None


def _safe_datetime_series(s: pd.Series) -> pd.Series:
    return pd.to_datetime(s, errors="coerce", dayfirst=True)


def _to_num(s: pd.Series) -> pd.Series:
    """Converte série para numérico de forma tolerante (string, vírgula, etc.)."""
    if s is None:
        return pd.Series(dtype="float")
    ss = s.astype(str).str.replace(".", "", regex=False).str.replace(",", ".", regex=False)
    return pd.to_numeric(ss, errors="coerce")


def _due_date_series(df: pd.DataFrame, col_prev: str | None, col_prazo: str | None, col_data_oc: str | None) -> pd.Series:
    """Calcula a data de vencimento (previsão > prazo > data_oc + 30d)."""
    base = pd.Series([pd.NaT] * len(df), index=df.index, dtype="datetime64[ns]")
    if col_prev and col_prev in df.columns:
        prev = _safe_datetime_series(df[col_prev])
        base = base.fillna(prev)
    if col_prazo and col_prazo in df.columns:
        prazo = _safe_datetime_series(df[col_prazo])
        base = base.fillna(prazo)
    if col_data_oc and col_data_oc in df.columns:
        dtoc = _safe_datetime_series(df[col_data_oc])
        base = base.fillna(dtoc + pd.to_timedelta(30, unit="D"))
    return base


def _is_atrasado(df: pd.DataFrame, col_entregue: str | None, due: pd.Series) -> pd.Series:
    """Atrasado se não entregue e due_date < hoje."""
    hoje = pd.Timestamp(datetime.now().date())
    entregue = pd.Series([False] * len(df), index=df.index)
    if col_entregue and col_entregue in df.columns:
        entregue = df[col_entregue] == True
    return (~entregue) & due.notna() & (due.dt.normalize() < hoje)


def exibir_ficha_material(_supabase):
    """Exibe ficha técnica completa e moderna do material"""

    st.title("📋 Ficha Técnica de Material")
    modo_ficha = bool(st.session_state.get("modo_ficha_material", False))


    df_pedidos = _carregar_pedidos_cache(_supabase)

    if df_pedidos.empty:
        st.info("📭 Nenhum pedido cadastrado ainda")
        return

    # Normalizações leves (evitam bugs em filtros e cálculos)
    if "cod_material" in df_pedidos.columns:
        df_pedidos["cod_material"] = df_pedidos["cod_material"].astype(str).str.strip()

    if "descricao" in df_pedidos.columns:
        df_pedidos["descricao"] = df_pedidos["descricao"].astype(str).str.strip()

    # Colunas prováveis (para evitar quebrar se o schema variar)
    col_unit = _pick_col(df_pedidos, ["valor_unitario", "preco_unitario", "vl_unitario", "unitario"])
    col_fornecedor = _pick_col(df_pedidos, ["fornecedor", "nome_fornecedor", "razao_social", "fornec"])
    col_data = _pick_col(df_pedidos, ["data_oc", "data", "data_pedido", "dt_oc"])
    col_qtd = _pick_col(df_pedidos, ["qtde_solicitada", "quantidade", "qtd", "qtde"])
    col_total = _pick_col(df_pedidos, ["valor_total", "total", "vl_total"])
    col_status = _pick_col(df_pedidos, ["status"])
    col_entregue = _pick_col(df_pedidos, ["entregue", "entrega", "is_entregue"])
    col_equip = _pick_col(df_pedidos, ["cod_equipamento", "equipamento"])
    col_dep = _pick_col(df_pedidos, ["departamento", "setor"])

    col_prev = _pick_col(df_pedidos, ["previsao_entrega", "previsao", "dt_previsao"])  # data prevista
    col_prazo = _pick_col(df_pedidos, ["prazo_entrega", "prazo"])  # prazo informado
    col_entrega_real = _pick_col(df_pedidos, ["data_entrega_real", "dt_entrega_real", "entrega_real"])  # data real
    col_qtd_pend = _pick_col(df_pedidos, ["qtde_pendente", "qtd_pendente", "pendente"])  # quantidade pendente
    col_oc = _pick_col(df_pedidos, ["nr_oc", "oc", "numero_oc"])  # ordem de compra
    col_solic = _pick_col(df_pedidos, ["nr_solicitacao", "solicitacao", "nr_req"])  # solicitação
    if not modo_ficha:

        # ============================================================
        # SISTEMA DE ABAS PARA BUSCA
        # ============================================================
        tab1, tab2, tab3 = st.tabs(
            ["🔍 Buscar Material", "🔧 Buscar por Equipamento", "🏢 Buscar por Departamento"]
        )

        # Estado/Contexto (não deixar variável "sumir" fora das tabs)
        material_key = st.session_state.get("material_fixo", {"cod": None, "desc": None})
        material_selecionado_cod = material_key.get("cod")
        material_selecionado_desc = material_key.get("desc")
        tipo_busca = st.session_state.get("tipo_busca_ficha", None)
        equipamento_ctx = st.session_state.get("equipamento_ctx", "")
        departamento_ctx = st.session_state.get("departamento_ctx", "")

        historico_material = pd.DataFrame()

        # ============================================================
        # TAB 1: BUSCA POR MATERIAL (COM BARRA DE PESQUISA)
        # ============================================================
        with tab1:
            st.markdown("### 🔎 Buscar Material Específico")

            # Agrupar materiais (preferir por código + descrição)
            if "cod_material" in df_pedidos.columns:
                materiais_unicos = (
                    df_pedidos.groupby(["cod_material"], dropna=True)
                    .agg(
                        descricao=("descricao", "first"),
                        compras=("id", "count") if "id" in df_pedidos.columns else ("descricao", "count"),
                    )
                    .reset_index()
                )
                materiais_unicos = materiais_unicos.sort_values("compras", ascending=False)
            else:
                materiais_unicos = (
                    df_pedidos.groupby(["descricao"], dropna=True)
                    .agg(
                        compras=("id", "count") if "id" in df_pedidos.columns else ("descricao", "count"),
                    )
                    .reset_index()
                    .rename(columns={"descricao": "descricao"})
                    .sort_values("compras", ascending=False)
                )
                materiais_unicos["cod_material"] = None

            col1, col2 = st.columns([4, 1])

            with col1:
                busca_texto = st.text_input(
                    "Digite o código do material:",
                    placeholder="Ex: MAT001, 12345, FILT-200...",
                    help="Digite o código completo ou parcial do material para buscar",
                    key="busca_material",
                )

            with col2:
                st.markdown("<br>", unsafe_allow_html=True)
                if st.button("🔄 Limpar", key="limpar_material"):
                    st.session_state.pop("material_fixo", None)
                    st.session_state.pop("tipo_busca_ficha", None)
                    st.session_state.pop("equipamento_ctx", None)
                    st.session_state.pop("departamento_ctx", None)
                    st.rerun()

            if busca_texto:
                if "cod_material" in materiais_unicos.columns:
                    materiais_filtrados = materiais_unicos[
                        materiais_unicos["cod_material"]
                        .astype(str)
                        .str.contains(str(busca_texto).upper(), case=False, na=False)
                    ]
                else:
                    materiais_filtrados = materiais_unicos[
                        materiais_unicos["descricao"]
                        .astype(str)
                        .str.contains(str(busca_texto).upper(), case=False, na=False)
                    ]

                if materiais_filtrados.empty:
                    st.warning(f"⚠️ Nenhum material encontrado com código '{busca_texto}'")
                    st.info("💡 Tente códigos mais genéricos ou verifique se o código está correto")
                else:
                    st.success(f"✅ {len(materiais_filtrados)} material(is) encontrado(s)")
                    st.markdown("#### Selecione um material:")

                    for idx, row in materiais_filtrados.head(10).iterrows():
                        c1, c2, c3 = st.columns([3, 1, 1])

                        with c1:
                            cod = row.get("cod_material")
                            desc = row.get("descricao", "")
                            st.markdown(f"**Código:** {cod if pd.notna(cod) and str(cod).strip() else 'N/A'}")
                            if pd.notna(desc) and str(desc).strip():
                                st.caption(str(desc))

                        with c2:
                            st.metric("Compras", int(row.get("compras", 0)))

                        with c3:
                            if st.button("Ver Ficha", key=f"ver_{idx}"):
                                st.session_state["material_fixo"] = {
                                    "cod": row.get("cod_material"),
                                    "desc": row.get("descricao"),
                                }
                                st.session_state["tipo_busca_ficha"] = "material"
                                st.session_state["equipamento_ctx"] = ""
                                st.session_state["departamento_ctx"] = ""
                                st.session_state["modo_ficha_material"] = True
                                st.rerun()

                        st.markdown("---")

                    if len(materiais_filtrados) > 10:
                        st.info(
                            f"ℹ️ Mostrando 10 de {len(materiais_filtrados)} resultados. Refine sua busca para ver mais."
                        )
            else:
                st.info("💡 Digite o código do material no campo acima para começar a busca")

                st.markdown("#### 📊 Top 10 Materiais Mais Comprados")
                for idx, row in materiais_unicos.head(10).iterrows():
                    c1, c2, c3 = st.columns([3, 1, 1])

                    with c1:
                        desc = row.get("descricao", "")
                        cod = row.get("cod_material")
                        st.markdown(f"**{desc if pd.notna(desc) else 'Material'}**")
                        if pd.notna(cod) and str(cod).strip():
                            st.caption(f"Código: {cod}")

                    with c2:
                        st.metric("Compras", int(row.get("compras", 0)))

                    with c3:
                        if st.button("Ver Ficha", key=f"top_{idx}"):
                            st.session_state["material_fixo"] = {
                                "cod": row.get("cod_material"),
                                "desc": row.get("descricao"),
                            }
                            st.session_state["tipo_busca_ficha"] = "material"
                            st.session_state["equipamento_ctx"] = ""
                            st.session_state["departamento_ctx"] = ""
                            st.session_state["modo_ficha_material"] = True
                            st.rerun()

                    st.markdown("---")

        # ============================================================
        # ============================================================
        # TAB 2: BUSCA POR EQUIPAMENTO (MODELO ERP)
        # ============================================================
        with tab2:
            st.markdown("### 🔧 Materiais por Equipamento")

            if not col_equip or col_equip not in df_pedidos.columns:
                st.warning("⚠️ Coluna de equipamento não encontrada nos pedidos")
            else:
                equipamentos_todos = (
                    df_pedidos[col_equip].dropna().astype(str).str.strip().unique().tolist()
                )
                equipamentos_todos = sorted([eq for eq in equipamentos_todos if eq])

                if not equipamentos_todos:
                    st.warning("⚠️ Nenhum equipamento cadastrado nos pedidos")
                else:
                    c1, c2 = st.columns([6, 1])

                    with c1:
                        busca_equipamento = st.text_input(
                            "Digite o código ou nome do equipamento:",
                            placeholder="Ex: TR-001, TRATOR, ESCAVADEIRA...",
                            key="busca_equipamento_erp",
                        )

                    with c2:
                        st.markdown("<br>", unsafe_allow_html=True)
                        if st.button("🧹 Limpar", key="limpar_busca_equipamento_erp", use_container_width=True):
                            for k in [
                                "busca_equipamento_erp",
                                "select_equipamento_erp",
                                "status_eq_erp",
                                "periodo_eq_erp",
                                "entrega_eq_erp",
                                "somente_pendentes_eq_erp",
                                "busca_material_eq_erp",
                            ]:
                                st.session_state.pop(k, None)
                            st.rerun()

                    if busca_equipamento:
                        equipamentos_filtrados = [
                            eq for eq in equipamentos_todos if busca_equipamento.lower() in eq.lower()
                        ]
                        if not equipamentos_filtrados:
                            st.warning(f"⚠️ Nenhum equipamento encontrado com '{busca_equipamento}'")
                            equipamentos_filtrados = []
                    else:
                        equipamentos_filtrados = equipamentos_todos

                    equipamento_selecionado = st.selectbox(
                        "Selecione o Equipamento:",
                        options=[""] + equipamentos_filtrados,
                        format_func=lambda x: "Selecione..." if x == "" else x,
                        key="select_equipamento_erp",
                    )

                    if equipamento_selecionado:
                        df_equipamento = df_pedidos[df_pedidos[col_equip] == equipamento_selecionado].copy()

                        # --------------------
                        # Filtros (compactos)
                        # --------------------
                        with st.expander("🎛️ Filtros avançados", expanded=True):
                            f1, f2, f3, f4 = st.columns([3, 2, 2, 2])

                            with f1:
                                status_options = (
                                    df_equipamento[col_status].dropna().astype(str).unique().tolist()
                                    if col_status and col_status in df_equipamento.columns
                                    else []
                                )
                                status_filtro = st.multiselect(
                                    "📊 Status",
                                    options=status_options,
                                    default=status_options,
                                    key="status_eq_erp",
                                )

                            with f2:
                                periodo = st.selectbox(
                                    "📅 Período",
                                    ["Todos", "Último mês", "Últimos 3 meses", "Últimos 6 meses", "Último ano"],
                                    key="periodo_eq_erp",
                                )

                            with f3:
                                entrega = st.selectbox(
                                    "🚚 Entrega",
                                    ["Todos", "Apenas Entregues", "Apenas Pendentes"],
                                    key="entrega_eq_erp",
                                )

                            with f4:
                                somente_pendentes = st.checkbox(
                                    "Somente com pendência",
                                    value=True,
                                    key="somente_pendentes_eq_erp",
                                    help="Mostra apenas materiais que ainda têm quantidade pendente.",
                                )

                        df_fil = df_equipamento.copy()

                        # status
                        if status_filtro and col_status:
                            df_fil = df_fil[df_fil[col_status].astype(str).isin([str(s) for s in status_filtro])]

                        # período
                        if periodo != "Todos" and col_data and col_data in df_fil.columns:
                            hoje = datetime.now()
                            if periodo == "Último mês":
                                data_limite = hoje - pd.DateOffset(months=1)
                            elif periodo == "Últimos 3 meses":
                                data_limite = hoje - pd.DateOffset(months=3)
                            elif periodo == "Últimos 6 meses":
                                data_limite = hoje - pd.DateOffset(months=6)
                            else:
                                data_limite = hoje - pd.DateOffset(years=1)
                            dt = _safe_datetime_series(df_fil[col_data])
                            df_fil = df_fil[dt >= data_limite]

                        # entrega
                        if col_entregue and col_entregue in df_fil.columns:
                            if entrega == "Apenas Entregues":
                                df_fil = df_fil[df_fil[col_entregue] == True]
                            elif entrega == "Apenas Pendentes":
                                df_fil = df_fil[df_fil[col_entregue] == False]

                        # KPIs follow-up (por equipamento)
                        due = _due_date_series(df_fil, col_prev, col_prazo, col_data)
                        atrasado_flag = _is_atrasado(df_fil, col_entregue, due)

                        total_pedidos = len(df_fil)
                        pendentes = int((df_fil[col_entregue] == False).sum()) if col_entregue else 0
                        atrasados = int(atrasado_flag.sum())
                        valor_total_num = float(_to_num(df_fil[col_total]).sum()) if col_total and col_total in df_fil.columns else 0.0

                        # materiais diferentes
                        if "cod_material" in df_fil.columns:
                            materiais_diff = int(df_fil["cod_material"].nunique())
                        else:
                            materiais_diff = int(df_fil["descricao"].nunique()) if "descricao" in df_fil.columns else 0

                        k1, k2, k3, k4 = st.columns(4)
                        k1.metric("📦 Total de Pedidos", total_pedidos)
                        k2.metric("🧩 Materiais Diferentes", materiais_diff)
                        k3.metric("💰 Valor Total", formatar_moeda_br(valor_total_num))
                        k4.metric("🔴 Atrasados", f"{atrasados}/{pendentes}" if pendentes else f"{atrasados}/0")

                        st.markdown("---")

                        # --------------------
                        # Materiais do equipamento (visão ERP)
                        # --------------------
                        st.markdown(f"#### 📋 Materiais do Equipamento **{equipamento_selecionado}**")

                        # Agregação por material (cod + descrição)
                        group_cols = ["descricao"]
                        if "cod_material" in df_fil.columns:
                            group_cols = ["cod_material", "descricao"]

                        df_tmp = df_fil.copy()
                        # normalizar valor_total e qtde_pendente se existirem
                        if col_total and col_total in df_tmp.columns:
                            df_tmp[col_total] = _to_num(df_tmp[col_total])
                        if col_qtd_pend and col_qtd_pend in df_tmp.columns:
                            df_tmp[col_qtd_pend] = _to_num(df_tmp[col_qtd_pend])

                        df_tmp["_due"] = due
                        df_tmp["_atrasado"] = atrasado_flag

                        agg = {
                            "id": "count" if "id" in df_tmp.columns else "size",
                        }
                        if col_total and col_total in df_tmp.columns:
                            agg[col_total] = "sum"
                        if col_qtd_pend and col_qtd_pend in df_tmp.columns:
                            agg[col_qtd_pend] = "sum"
                        if col_entregue and col_entregue in df_tmp.columns:
                            agg[col_entregue] = lambda x: int((x == False).sum())
                        agg["_atrasado"] = "sum"

                        mat = df_tmp.groupby(group_cols, dropna=False).agg(agg).reset_index()

                        # renomear
                        mat = mat.rename(
                            columns={
                                ("id" if "id" in mat.columns else "size"): "Pedidos",
                                (col_total if col_total in mat.columns else col_total): "Valor Total",
                                (col_qtd_pend if col_qtd_pend in mat.columns else col_qtd_pend): "Qtd Pendente",
                                (col_entregue if col_entregue in mat.columns else col_entregue): "Pedidos Pendentes",
                                "_atrasado": "Pedidos Atrasados",
                            }
                        )

                        # fallback se colunas não existirem
                        if "Valor Total" not in mat.columns:
                            mat["Valor Total"] = 0.0
                        if "Qtd Pendente" not in mat.columns:
                            mat["Qtd Pendente"] = 0.0
                        if "Pedidos Pendentes" not in mat.columns:
                            mat["Pedidos Pendentes"] = 0
                        if "Pedidos Atrasados" not in mat.columns:
                            mat["Pedidos Atrasados"] = 0

                        if somente_pendentes:
                            mat = mat[mat["Qtd Pendente"] > 0]

                        # Busca dentro dos materiais (melhora muito a usabilidade)
                        busca_mat = st.text_input(
                            "Buscar material dentro do equipamento:",
                            placeholder="Digite parte do código ou descrição…",
                            key="busca_material_eq_erp",
                        )
                        if busca_mat:
                            t = busca_mat.lower().strip()
                            mask = mat["descricao"].astype(str).str.lower().str.contains(t, na=False)
                            if "cod_material" in mat.columns:
                                mask = mask | mat["cod_material"].astype(str).str.lower().str.contains(t, na=False)
                            mat = mat[mask]

                        # Ordenação (prioridade follow-up)
                        mat = mat.sort_values(
                            ["Pedidos Atrasados", "Valor Total", "Pedidos"],
                            ascending=[False, False, False],
                            na_position="last",
                        )

                        # Exibição (tabela compacta)
                        show_cols = []
                        if "cod_material" in mat.columns:
                            show_cols.append("cod_material")
                        show_cols += ["descricao", "Pedidos", "Qtd Pendente", "Pedidos Atrasados", "Valor Total"]

                        st.dataframe(
                            mat[show_cols].head(50),
                            use_container_width=True,
                            hide_index=True,
                            column_config={
                                "cod_material": st.column_config.TextColumn("Código"),
                                "descricao": st.column_config.TextColumn("Descrição"),
                                "Pedidos": st.column_config.NumberColumn("Pedidos"),
                                "Qtd Pendente": st.column_config.NumberColumn("Qtd. Pendente"),
                                "Pedidos Atrasados": st.column_config.NumberColumn("Atrasados"),
                                "Valor Total": st.column_config.NumberColumn("Valor", format="R$ %.2f"),
                            },
                        )

                        # Selecionar e abrir ficha (menos “scroll” do que botão por linha)
                        st.markdown("##### ▶️ Abrir ficha do material")
                        opções = []
                        for _, r in mat.head(200).iterrows():
                            cod = r.get("cod_material", "")
                            desc = str(r.get("descricao", "")).strip()
                            ped = int(r.get("Pedidos", 0))
                            label = f"{cod} - {desc}  (Pedidos: {ped})" if cod else f"{desc}  (Pedidos: {ped})"
                            opções.append((label, cod, desc))

                        if opções:
                            sel = st.selectbox(
                                "Selecione um material:",
                                options=opções,
                                format_func=lambda x: x[0],
                                key="select_material_eq_erp",
                            )
                            if st.button("Ver Ficha", key="btn_ver_ficha_eq_erp", use_container_width=True):
                                _, cod, desc = sel
                                st.session_state["material_fixo"] = {"cod": cod, "desc": desc}
                                st.session_state["tipo_busca_ficha"] = "equipamento"
                                st.session_state["equipamento_ctx"] = equipamento_selecionado
                                st.session_state["departamento_ctx"] = ""
                                st.session_state["modo_ficha_material"] = True
                                st.rerun()
                        else:
                            st.info("Nenhum material encontrado com os filtros atuais.")

        # ============================================================
        # TAB 3: BUSCA POR DEPARTAMENTO (MODELO ERP)
        # ============================================================
        with tab3:
            st.markdown("### 🏢 Materiais por Departamento")

            if not col_dep or col_dep not in df_pedidos.columns:
                st.warning("⚠️ Coluna de departamento não encontrada nos pedidos")
            else:
                departamentos = df_pedidos[col_dep].dropna().astype(str).str.strip().unique().tolist()
                departamentos = sorted([d for d in departamentos if d])

                if not departamentos:
                    st.warning("⚠️ Nenhum departamento cadastrado nos pedidos")
                else:
                    c1, c2 = st.columns([6, 1])

                    with c1:
                        departamento_selecionado = st.selectbox(
                            "Selecione o Departamento:",
                            options=[""] + departamentos,
                            format_func=lambda x: "Selecione..." if x == "" else x,
                            key="select_departamento_erp",
                        )

                    with c2:
                        st.markdown("<br>", unsafe_allow_html=True)
                        if st.button("🧹 Limpar", key="limpar_departamento_erp", use_container_width=True):
                            for k in [
                                "select_departamento_erp",
                                "status_dep_erp",
                                "periodo_dep_erp",
                                "entrega_dep_erp",
                                "equipamento_dep_erp",
                                "somente_pendentes_dep_erp",
                                "busca_material_dep_erp",
                            ]:
                                st.session_state.pop(k, None)
                            st.rerun()

                    if departamento_selecionado:
                        df_dep = df_pedidos[df_pedidos[col_dep] == departamento_selecionado].copy()

                        with st.expander("🎛️ Filtros avançados", expanded=True):
                            f1, f2, f3, f4, f5 = st.columns([3, 2, 2, 2, 3])

                            with f1:
                                status_options = (
                                    df_dep[col_status].dropna().astype(str).unique().tolist()
                                    if col_status and col_status in df_dep.columns
                                    else []
                                )
                                status_filtro = st.multiselect(
                                    "📊 Status",
                                    options=status_options,
                                    default=status_options,
                                    key="status_dep_erp",
                                )

                            with f2:
                                periodo = st.selectbox(
                                    "📅 Período",
                                    ["Todos", "Último mês", "Últimos 3 meses", "Últimos 6 meses", "Último ano"],
                                    key="periodo_dep_erp",
                                )

                            with f3:
                                entrega = st.selectbox(
                                    "🚚 Entrega",
                                    ["Todos", "Apenas Entregues", "Apenas Pendentes"],
                                    key="entrega_dep_erp",
                                )

                            with f4:
                                somente_pendentes = st.checkbox(
                                    "Somente com pendência",
                                    value=True,
                                    key="somente_pendentes_dep_erp",
                                )

                            with f5:
                                # filtro de equipamento dentro do departamento
                                if col_equip and col_equip in df_dep.columns:
                                    equipamentos_dep = ["Todos"] + sorted(
                                        df_dep[col_equip].dropna().astype(str).str.strip().unique().tolist()
                                    )
                                else:
                                    equipamentos_dep = ["Todos"]
                                filtro_equip = st.selectbox(
                                    "🔧 Equipamento",
                                    options=equipamentos_dep,
                                    key="equipamento_dep_erp",
                                )

                        df_fil = df_dep.copy()

                        if status_filtro and col_status:
                            df_fil = df_fil[df_fil[col_status].astype(str).isin([str(s) for s in status_filtro])]

                        if periodo != "Todos" and col_data and col_data in df_fil.columns:
                            hoje = datetime.now()
                            if periodo == "Último mês":
                                data_limite = hoje - pd.DateOffset(months=1)
                            elif periodo == "Últimos 3 meses":
                                data_limite = hoje - pd.DateOffset(months=3)
                            elif periodo == "Últimos 6 meses":
                                data_limite = hoje - pd.DateOffset(months=6)
                            else:
                                data_limite = hoje - pd.DateOffset(years=1)
                            dt = _safe_datetime_series(df_fil[col_data])
                            df_fil = df_fil[dt >= data_limite]

                        if col_entregue and col_entregue in df_fil.columns:
                            if entrega == "Apenas Entregues":
                                df_fil = df_fil[df_fil[col_entregue] == True]
                            elif entrega == "Apenas Pendentes":
                                df_fil = df_fil[df_fil[col_entregue] == False]

                        if filtro_equip != "Todos" and col_equip and col_equip in df_fil.columns:
                            df_fil = df_fil[df_fil[col_equip].astype(str) == str(filtro_equip)]

                        due = _due_date_series(df_fil, col_prev, col_prazo, col_data)
                        atrasado_flag = _is_atrasado(df_fil, col_entregue, due)

                        total_pedidos = len(df_fil)
                        pendentes = int((df_fil[col_entregue] == False).sum()) if col_entregue else 0
                        atrasados = int(atrasado_flag.sum())
                        valor_total_num = float(_to_num(df_fil[col_total]).sum()) if col_total and col_total in df_fil.columns else 0.0

                        if "cod_material" in df_fil.columns:
                            materiais_diff = int(df_fil["cod_material"].nunique())
                        else:
                            materiais_diff = int(df_fil["descricao"].nunique()) if "descricao" in df_fil.columns else 0

                        k1, k2, k3, k4 = st.columns(4)
                        k1.metric("📦 Total de Pedidos", total_pedidos)
                        k2.metric("🧩 Materiais Diferentes", materiais_diff)
                        k3.metric("💰 Valor Total", formatar_moeda_br(valor_total_num))
                        k4.metric("🔴 Atrasados", f"{atrasados}/{pendentes}" if pendentes else f"{atrasados}/0")

                        st.markdown("---")

                        st.markdown(f"#### 📋 Materiais do Departamento **{departamento_selecionado}**")

                        group_cols = ["descricao"]
                        if "cod_material" in df_fil.columns:
                            group_cols = ["cod_material", "descricao"]

                        df_tmp = df_fil.copy()
                        if col_total and col_total in df_tmp.columns:
                            df_tmp[col_total] = _to_num(df_tmp[col_total])
                        if col_qtd_pend and col_qtd_pend in df_tmp.columns:
                            df_tmp[col_qtd_pend] = _to_num(df_tmp[col_qtd_pend])

                        df_tmp["_due"] = due
                        df_tmp["_atrasado"] = atrasado_flag

                        agg = {"id": "count" if "id" in df_tmp.columns else "size"}
                        if col_total and col_total in df_tmp.columns:
                            agg[col_total] = "sum"
                        if col_qtd_pend and col_qtd_pend in df_tmp.columns:
                            agg[col_qtd_pend] = "sum"
                        if col_entregue and col_entregue in df_tmp.columns:
                            agg[col_entregue] = lambda x: int((x == False).sum())
                        if col_equip and col_equip in df_tmp.columns:
                            agg[col_equip] = "nunique"
                        agg["_atrasado"] = "sum"

                        mat = df_tmp.groupby(group_cols, dropna=False).agg(agg).reset_index()

                        mat = mat.rename(
                            columns={
                                ("id" if "id" in mat.columns else "size"): "Pedidos",
                                (col_total if col_total in mat.columns else col_total): "Valor Total",
                                (col_qtd_pend if col_qtd_pend in mat.columns else col_qtd_pend): "Qtd Pendente",
                                (col_entregue if col_entregue in mat.columns else col_entregue): "Pedidos Pendentes",
                                (col_equip if col_equip in mat.columns else col_equip): "Equipamentos",
                                "_atrasado": "Pedidos Atrasados",
                            }
                        )

                        if "Valor Total" not in mat.columns:
                            mat["Valor Total"] = 0.0
                        if "Qtd Pendente" not in mat.columns:
                            mat["Qtd Pendente"] = 0.0
                        if "Pedidos Pendentes" not in mat.columns:
                            mat["Pedidos Pendentes"] = 0
                        if "Pedidos Atrasados" not in mat.columns:
                            mat["Pedidos Atrasados"] = 0
                        if "Equipamentos" not in mat.columns:
                            mat["Equipamentos"] = 0

                        if somente_pendentes:
                            mat = mat[mat["Qtd Pendente"] > 0]

                        busca_mat = st.text_input(
                            "Buscar material dentro do departamento:",
                            placeholder="Digite parte do código ou descrição…",
                            key="busca_material_dep_erp",
                        )
                        if busca_mat:
                            t = busca_mat.lower().strip()
                            mask = mat["descricao"].astype(str).str.lower().str.contains(t, na=False)
                            if "cod_material" in mat.columns:
                                mask = mask | mat["cod_material"].astype(str).str.lower().str.contains(t, na=False)
                            mat = mat[mask]

                        mat = mat.sort_values(
                            ["Pedidos Atrasados", "Valor Total", "Pedidos"],
                            ascending=[False, False, False],
                            na_position="last",
                        )

                        show_cols = []
                        if "cod_material" in mat.columns:
                            show_cols.append("cod_material")
                        show_cols += ["descricao", "Pedidos", "Qtd Pendente", "Pedidos Atrasados", "Equipamentos", "Valor Total"]

                        st.dataframe(
                            mat[show_cols].head(50),
                            use_container_width=True,
                            hide_index=True,
                            column_config={
                                "cod_material": st.column_config.TextColumn("Código"),
                                "descricao": st.column_config.TextColumn("Descrição"),
                                "Pedidos": st.column_config.NumberColumn("Pedidos"),
                                "Qtd Pendente": st.column_config.NumberColumn("Qtd. Pendente"),
                                "Pedidos Atrasados": st.column_config.NumberColumn("Atrasados"),
                                "Equipamentos": st.column_config.NumberColumn("Equip."),
                                "Valor Total": st.column_config.NumberColumn("Valor", format="R$ %.2f"),
                            },
                        )

                        st.markdown("##### ▶️ Abrir ficha do material")
                        opções = []
                        for _, r in mat.head(200).iterrows():
                            cod = r.get("cod_material", "")
                            desc = str(r.get("descricao", "")).strip()
                            ped = int(r.get("Pedidos", 0))
                            label = f"{cod} - {desc}  (Pedidos: {ped})" if cod else f"{desc}  (Pedidos: {ped})"
                            opções.append((label, cod, desc))

                        if opções:
                            sel = st.selectbox(
                                "Selecione um material:",
                                options=opções,
                                format_func=lambda x: x[0],
                                key="select_material_dep_erp",
                            )
                            if st.button("Ver Ficha", key="btn_ver_ficha_dep_erp", use_container_width=True):
                                _, cod, desc = sel
                                st.session_state["material_fixo"] = {"cod": cod, "desc": desc}
                                st.session_state["tipo_busca_ficha"] = "departamento"
                                st.session_state["equipamento_ctx"] = filtro_equip if filtro_equip != "Todos" else ""
                                st.session_state["departamento_ctx"] = departamento_selecionado
                                st.session_state["modo_ficha_material"] = True
                                st.rerun()
                        else:
                            st.info("Nenhum material encontrado com os filtros atuais.")


    # EXIBIR FICHA DO MATERIAL SELECIONADO (COM ABAS)
    # ============================================================

    if modo_ficha:
        c1, c2 = st.columns([1, 7])
        with c1:
            if st.button("← Nova busca", use_container_width=True):
                st.session_state["modo_ficha_material"] = False
                st.session_state["material_fixo"] = {"cod": None, "desc": None}
                st.session_state["tipo_busca_ficha"] = None
                st.session_state["equipamento_ctx"] = ""
                st.session_state["departamento_ctx"] = ""
                st.rerun()

    material_key = st.session_state.get("material_fixo", {"cod": None, "desc": None})
    material_selecionado_cod = material_key.get("cod")
    material_selecionado_desc = material_key.get("desc")
    tipo_busca = st.session_state.get("tipo_busca_ficha", None)
    equipamento_ctx = st.session_state.get("equipamento_ctx", "")
    departamento_ctx = st.session_state.get("departamento_ctx", "")

    # Montar histórico (preferir cod_material quando existir)
    if material_selecionado_cod and "cod_material" in df_pedidos.columns:
        historico_material = df_pedidos[df_pedidos["cod_material"] == str(material_selecionado_cod)].copy()
    elif material_selecionado_desc and "descricao" in df_pedidos.columns:
        historico_material = df_pedidos[df_pedidos["descricao"] == str(material_selecionado_desc)].copy()

    if not historico_material.empty and (material_selecionado_desc or material_selecionado_cod):
        # Pedido mais recente para "material atual"
        if col_data and col_data in historico_material.columns:
            historico_material["_dt"] = _safe_datetime_series(historico_material[col_data])
            material_atual = (
                historico_material.sort_values("_dt", ascending=False)
                .drop(columns=["_dt"], errors="ignore")
                .iloc[0]
                .to_dict()
            )
        else:
            material_atual = historico_material.iloc[0].to_dict()

        st.markdown("---")

        # Contexto claro (histórico completo vs filtrado)
        contexto = "(histórico completo)" if tipo_busca == "material" else "(histórico filtrado)"
        detalhes = []
        if equipamento_ctx:
            detalhes.append(f"Equipamento: **{equipamento_ctx}**")
        if departamento_ctx:
            detalhes.append(f"Departamento: **{departamento_ctx}**")
        detalhes_txt = " • " + " • ".join(detalhes) if detalhes else ""

        st.info(
            f"📌 Exibindo ficha do material {contexto}{detalhes_txt}",
            icon="ℹ️",
        )

        # Header com informações básicas
        cod_show = material_atual.get("cod_material", material_selecionado_cod) if "cod_material" in material_atual else material_selecionado_cod
        dep_show = material_atual.get(col_dep, "N/A") if col_dep else material_atual.get("departamento", "N/A")
        equip_show = material_atual.get(col_equip, "N/A") if col_equip else material_atual.get("cod_equipamento", "N/A")
        desc_show = material_selecionado_desc or material_atual.get("descricao", "Material")

        st.markdown(
            f"""
            <div style='background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                        padding: 25px; border-radius: 15px; color: white; margin-bottom: 20px;'>
                <h2 style='margin: 0; font-size: 28px;'>📦 {desc_show}</h2>
                <p style='margin: 10px 0 0 0; font-size: 16px; opacity: 0.9;'>
                    Código: {cod_show if cod_show else 'N/A'} •
                    Departamento: {dep_show if dep_show else 'N/A'} •
                    Equipamento: {equip_show if equip_show else 'N/A'}
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # ============================================================
        # ABAS: FICHA TÉCNICA vs HISTÓRICO DETALHADO
        # ============================================================

        # ============================================================
        # ABAS (ERP FOLLOW-UP): Acompanhamento / Histórico / Fornecedores / Entregas / Preço
        # ============================================================
        tab_acomp, tab_hist, tab_forn, tab_ent, tab_preco = st.tabs(
            ["📌 Acompanhamento", "📦 Histórico", "🏷️ Fornecedores", "🚚 Entregas (SLA)", "📈 Preço & Insights"]
        )

        # Preparar dados para cálculos de follow-up
        df_mat = historico_material.copy()

        # Datas-base
        if col_data and col_data in df_mat.columns:
            df_mat["_data_oc"] = _safe_datetime_series(df_mat[col_data])
        else:
            df_mat["_data_oc"] = pd.NaT

        # Previsões/prazo e entrega real
        df_mat["_prev"] = _safe_datetime_series(df_mat[col_prev]) if col_prev and col_prev in df_mat.columns else pd.NaT
        df_mat["_prazo"] = _safe_datetime_series(df_mat[col_prazo]) if col_prazo and col_prazo in df_mat.columns else pd.NaT
        df_mat["_entrega_real"] = _safe_datetime_series(df_mat[col_entrega_real]) if col_entrega_real and col_entrega_real in df_mat.columns else pd.NaT

        hoje = pd.Timestamp.now().normalize()

        # Due date: previsao > prazo > data_oc + 30d
        df_mat["_due"] = df_mat["_prev"]
        df_mat.loc[df_mat["_due"].isna(), "_due"] = df_mat.loc[df_mat["_due"].isna(), "_prazo"]
        df_mat.loc[df_mat["_due"].isna(), "_due"] = df_mat.loc[df_mat["_due"].isna(), "_data_oc"] + pd.Timedelta(days=30)

        # Pendente: entregue False OU qtde_pendente > 0
        if col_entregue and col_entregue in df_mat.columns:
            pendente_flag = df_mat[col_entregue] != True
        else:
            pendente_flag = pd.Series([True] * len(df_mat), index=df_mat.index)

        if col_qtd_pend and col_qtd_pend in df_mat.columns:
            qtd_pend = pd.to_numeric(df_mat[col_qtd_pend], errors="coerce").fillna(0)
            pendente_flag = pendente_flag | (qtd_pend > 0)

        df_mat["_pendente"] = pendente_flag
        df_mat["_atrasado"] = df_mat["_pendente"] & df_mat["_due"].notna() & (df_mat["_due"] < hoje)

        # Dias em aberto
        df_mat["_dias_aberto"] = (hoje - df_mat["_data_oc"]).dt.days

        # Valor (para KPIs)
        if col_total and col_total in df_mat.columns:
            df_mat["_valor_total"] = pd.to_numeric(df_mat[col_total], errors="coerce").fillna(0.0)
        else:
            df_mat["_valor_total"] = 0.0

        # Score de criticidade simples (follow-up)
        qtd_atrasados = int(df_mat["_atrasado"].sum())
        valor_pendente = float(df_mat.loc[df_mat["_pendente"], "_valor_total"].sum())
        fornecedor_unico = 0
        if col_fornecedor and col_fornecedor in df_mat.columns:
            fornecedor_unico = int(df_mat[col_fornecedor].dropna().nunique() == 1)

        score = 0
        if qtd_atrasados > 0:
            score += 3
        if valor_pendente >= 50000:
            score += 2
        elif valor_pendente >= 15000:
            score += 1
        if fornecedor_unico:
            score += 2
        if len(df_mat) >= 15:
            score += 1

        if score >= 5:
            nivel = "🔴 CRÍTICO"
        elif score >= 3:
            nivel = "🟡 ATENÇÃO"
        else:
            nivel = "🟢 SAUDÁVEL"

        # KPI bar (ERP)
        k1, k2, k3, k4, k5 = st.columns(5)
        k1.metric("📦 Pedidos", int(len(df_mat)))
        k2.metric("⏳ Pendentes", int(df_mat["_pendente"].sum()))
        k3.metric("🔴 Atrasados", qtd_atrasados)
        k4.metric("💰 Valor pendente", formatar_moeda_br(valor_pendente))
        mais_antigo = df_mat.loc[df_mat["_pendente"], "_dias_aberto"].max()
        k5.metric("🧭 Mais antigo (dias)", f"{int(mais_antigo)}" if pd.notna(mais_antigo) else "—")

        st.caption(f"Criticidade do follow-up: **{nivel}** • Regra de atraso: previsão > prazo > OC + 30 dias")

        with tab_acomp:
            st.markdown("### 📌 Fila de Follow-up (pedidos pendentes)")

            f1, f2, f3, f4 = st.columns([1.2, 1.2, 1.2, 1.4])
            only_atrasados = f1.toggle("Só atrasados", value=False)
            only_pendentes = f2.toggle("Só pendentes", value=True)
            ordenar = f3.selectbox("Ordenar por", ["Prioridade", "Maior valor", "Mais antigo"], index=0)
            limite = f4.selectbox("Mostrar", [20, 50, 100, 200], index=0)

            df_work = df_mat.copy()
            if only_pendentes:
                df_work = df_work[df_work["_pendente"]]
            if only_atrasados:
                df_work = df_work[df_work["_atrasado"]]

            # Prioridade: atrasado, maior valor, mais antigo
            df_work["_prio_atraso"] = df_work["_atrasado"].astype(int)
            df_work["_prio_valor"] = df_work["_valor_total"]
            df_work["_prio_dias"] = df_work["_dias_aberto"].fillna(-1)

            if ordenar == "Prioridade":
                df_work = df_work.sort_values(
                    ["_prio_atraso", "_prio_valor", "_prio_dias"],
                    ascending=[False, False, False],
                )
            elif ordenar == "Maior valor":
                df_work = df_work.sort_values(["_valor_total"], ascending=[False])
            else:
                df_work = df_work.sort_values(["_dias_aberto"], ascending=[False])

            cols_show = []
            if col_oc and col_oc in df_work.columns:
                cols_show.append(col_oc)
            if col_solic and col_solic in df_work.columns:
                cols_show.append(col_solic)
            if col_fornecedor and col_fornecedor in df_work.columns:
                cols_show.append(col_fornecedor)
            if col_status and col_status in df_work.columns:
                cols_show.append(col_status)
            if col_qtd and col_qtd in df_work.columns:
                cols_show.append(col_qtd)
            if col_qtd_pend and col_qtd_pend in df_work.columns:
                cols_show.append(col_qtd_pend)

            cols_show += ["_due", "_dias_aberto", "_valor_total", "_atrasado"]

            df_view = df_work[cols_show].head(int(limite)).copy()

            rename = {"_due": "Vencimento", "_dias_aberto": "Dias em aberto", "_valor_total": "Valor Total", "_atrasado": "Atrasado?"}
            if col_oc:
                rename[col_oc] = "OC"
            if col_solic:
                rename[col_solic] = "Solicitação"
            if col_fornecedor:
                rename[col_fornecedor] = "Fornecedor"
            if col_status:
                rename[col_status] = "Status"
            if col_qtd:
                rename[col_qtd] = "Qtd Sol."
            if col_qtd_pend:
                rename[col_qtd_pend] = "Qtd Pend."

            df_view = df_view.rename(columns=rename)

            st.dataframe(
                df_view,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Vencimento": st.column_config.DateColumn(format="DD/MM/YYYY"),
                    "Valor Total": st.column_config.NumberColumn(format="R$ %.2f"),
                    "Atrasado?": st.column_config.CheckboxColumn(),
                },
            )

            st.caption("Priorize os itens **atrasados** e/ou de **maior valor** para cobrar fornecedor e destravar entrega.")

        with tab_hist:
            st.markdown("### 📦 Histórico do material")
            st.caption("Auditoria e histórico completo (com filtros e exportação).")

            c1, c2, c3 = st.columns([1.2, 1.2, 1.6])
            filtro_status = None
            if col_status and col_status in df_mat.columns:
                status_opts = sorted(df_mat[col_status].dropna().astype(str).unique().tolist())
                filtro_status = c1.multiselect("Status", status_opts, default=status_opts)
            filtro_entrega = c2.selectbox("Entrega", ["Todos", "Entregues", "Pendentes"], index=0)
            janela = c3.selectbox("Período", ["Tudo", "Últimos 3 meses", "Últimos 6 meses", "Último ano"], index=0)

            dfh = df_mat.copy()
            if filtro_status is not None and col_status:
                dfh = dfh[dfh[col_status].astype(str).isin(filtro_status)]

            if filtro_entrega == "Entregues":
                dfh = dfh[~dfh["_pendente"]]
            elif filtro_entrega == "Pendentes":
                dfh = dfh[dfh["_pendente"]]

            if janela != "Tudo" and dfh["_data_oc"].notna().any():
                if janela == "Últimos 3 meses":
                    lim = hoje - pd.DateOffset(months=3)
                elif janela == "Últimos 6 meses":
                    lim = hoje - pd.DateOffset(months=6)
                else:
                    lim = hoje - pd.DateOffset(years=1)
                dfh = dfh[dfh["_data_oc"] >= lim]

            cols_core = []
            for c in [col_data, col_oc, col_solic, col_status, col_fornecedor, col_qtd, col_qtd_pend, col_total, col_entregue, col_prev, col_prazo, col_entrega_real, "observacoes"]:
                if c and c in dfh.columns and c not in cols_core:
                    cols_core.append(c)

            df_core = dfh.sort_values("_data_oc", ascending=False)
            st.dataframe(
                df_core[cols_core],
                use_container_width=True,
                hide_index=True,
                column_config={
                    col_data: st.column_config.DateColumn("Data OC", format="DD/MM/YYYY") if col_data else None,
                    col_total: st.column_config.NumberColumn("Valor Total", format="R$ %.2f") if col_total else None,
                },
            )

            with st.expander("🔎 Ver colunas completas (auditoria)"):
                cols_all = [c for c in historico_material.columns if c in dfh.columns]
                st.dataframe(df_core[cols_all], use_container_width=True, hide_index=True)

            csv_bytes = df_core.drop(columns=[c for c in df_core.columns if c.startswith("_")], errors="ignore").to_csv(index=False).encode("utf-8")
            nome = str(cod_show or "material").replace(" ", "_")
            st.download_button(
                "📥 Exportar histórico do material (CSV)",
                data=csv_bytes,
                file_name=f"historico_{nome}.csv",
                mime="text/csv",
                use_container_width=True,
            )

        with tab_forn:
            st.markdown("### 🏷️ Análise de fornecedores (follow-up)")
            if not (col_fornecedor and col_fornecedor in df_mat.columns):
                st.info("ℹ️ Não encontrei coluna de fornecedor nos pedidos para este material.")
            else:
                df_f = df_mat.copy()
                df_f["Fornecedor"] = df_f[col_fornecedor].astype(str)

                resumo = (
                    df_f.groupby("Fornecedor", dropna=False)
                    .agg(
                        Pedidos=("id", "count") if "id" in df_f.columns else ("Fornecedor", "size"),
                        Pendentes=("_pendente", "sum"),
                        Atrasados=("_atrasado", "sum"),
                        Valor=("_valor_total", "sum"),
                        DiasMedio=("_dias_aberto", "mean"),
                    )
                    .reset_index()
                )
                resumo["% Atraso"] = (resumo["Atrasados"] / resumo["Pedidos"]).fillna(0) * 100
                resumo = resumo.sort_values(["Atrasados", "Pendentes", "Valor"], ascending=[False, False, False])

                st.dataframe(
                    resumo,
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "Valor": st.column_config.NumberColumn(format="R$ %.2f"),
                        "DiasMedio": st.column_config.NumberColumn("Dias em aberto (média)", format="%.0f"),
                        "% Atraso": st.column_config.NumberColumn(format="%.1f%%"),
                    },
                )

                st.caption("Use **% Atraso** e **Pendentes** para decidir onde cobrar primeiro.")

        with tab_ent:
            st.markdown("### 🚚 Entregas e SLA")
            st.caption("Baseado em vencimento (previsão/prazo) vs entrega real. Para pendentes, considera vencimento.")

            df_ent = df_mat.copy()
            entregues_mask = ~df_ent["_pendente"]
            df_done = df_ent[entregues_mask & df_ent["_entrega_real"].notna() & df_ent["_due"].notna()].copy()

            if df_done.empty:
                st.info("ℹ️ Não há entregas com datas suficientes (vencimento e entrega real) para calcular SLA.")
            else:
                df_done["_no_prazo"] = df_done["_entrega_real"] <= df_done["_due"]
                sla = float(df_done["_no_prazo"].mean() * 100)

                atraso_dias = (df_done["_entrega_real"] - df_done["_due"]).dt.days
                atraso_medio = float(atraso_dias[atraso_dias > 0].mean()) if (atraso_dias > 0).any() else 0.0

                a1, a2, a3 = st.columns(3)
                a1.metric("✅ SLA (no prazo)", f"{sla:.1f}%")
                a2.metric("⏱️ Atraso médio (dias)", f"{atraso_medio:.0f}")
                a3.metric("📦 Entregas analisadas", int(len(df_done)))

                view_cols = []
                for c in [col_oc, col_solic, col_fornecedor, col_status]:
                    if c and c in df_done.columns:
                        view_cols.append(c)
                view_cols += ["_due", "_entrega_real"]

                st.dataframe(
                    df_done[view_cols].rename(columns={"_due": "Vencimento", "_entrega_real": "Entrega real"}),
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "Vencimento": st.column_config.DateColumn(format="DD/MM/YYYY"),
                        "Entrega real": st.column_config.DateColumn(format="DD/MM/YYYY"),
                    },
                )

        with tab_preco:
            st.markdown("### 📈 Preço e Insights")

            # Guard rails: só desenhar preço se houver dados
            if col_unit and col_unit in historico_material.columns and pd.to_numeric(historico_material[col_unit], errors="coerce").notna().sum() >= 2:
                col1, col2 = st.columns([2, 1])
                with col1:
                    fm.criar_grafico_evolucao_precos(historico_material)
                    st.markdown("<br>", unsafe_allow_html=True)
                    fm.criar_comparacao_visual_precos(historico_material)
                with col2:
                    fm.criar_mini_mapa_fornecedores(historico_material)

                st.markdown("---")
                fm.criar_ranking_fornecedores_visual(historico_material)
            else:
                st.info("📊 Ainda não há histórico suficiente de preço para gráficos comparativos.")

            st.markdown("---")
            fm.criar_timeline_compras(historico_material)

            st.markdown("---")
            _call_insights_automaticos(historico_material, material_atual)



        st.markdown("---")
        if st.button("← Voltar para Consulta", use_container_width=True):
            st.session_state.pagina = "Consultar Pedidos"
            st.rerun()
