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
        # TAB 2: BUSCA POR EQUIPAMENTO
        # ============================================================
        with tab2:
            st.markdown("### 🔧 Materiais por Equipamento")

            if not col_equip or col_equip not in df_pedidos.columns:
                st.warning("⚠️ Coluna de equipamento não encontrada nos pedidos")
            else:
                equipamentos_todos = df_pedidos[col_equip].dropna().astype(str).str.strip().unique().tolist()
                equipamentos_todos = sorted([eq for eq in equipamentos_todos if eq])

                if not equipamentos_todos:
                    st.warning("⚠️ Nenhum equipamento cadastrado nos pedidos")
                else:
                    st.markdown("#### 🔍 Buscar Equipamento")
                    c1, c2 = st.columns([4, 1])

                    with c1:
                        busca_equipamento = st.text_input(
                            "Digite o código ou nome do equipamento:",
                            placeholder="Ex: TR-001, TRATOR, ESCAVADEIRA...",
                            help="Busca por código ou descrição do equipamento",
                            key="busca_equipamento",
                        )

                    with c2:
                        st.markdown("<br>", unsafe_allow_html=True)
                        if st.button("🔄 Limpar", key="limpar_busca_equipamento"):
                            st.session_state.pop("material_fixo", None)
                            st.session_state.pop("tipo_busca_ficha", None)
                            st.session_state.pop("equipamento_ctx", None)
                            st.session_state.pop("departamento_ctx", None)
                            st.rerun()

                    if busca_equipamento:
                        equipamentos_filtrados = [
                            eq for eq in equipamentos_todos if busca_equipamento.upper() in eq.upper()
                        ]
                        if not equipamentos_filtrados:
                            st.warning(f"⚠️ Nenhum equipamento encontrado com '{busca_equipamento}'")
                            equipamentos_filtrados = []
                        else:
                            st.success(f"✅ {len(equipamentos_filtrados)} equipamento(s) encontrado(s)")
                    else:
                        equipamentos_filtrados = equipamentos_todos

                    equipamento_selecionado = ""
                    if equipamentos_filtrados:
                        equipamento_selecionado = st.selectbox(
                            "Selecione o Equipamento:",
                            options=[""] + equipamentos_filtrados,
                            format_func=lambda x: "Selecione..." if x == "" else x,
                            key="select_equipamento",
                        )

                    if equipamento_selecionado:
                        df_equipamento = df_pedidos[df_pedidos[col_equip] == equipamento_selecionado].copy()
                        st.markdown("---")

                        st.markdown("#### 🎛️ Filtros Avançados")
                        c1, c2, c3 = st.columns(3)

                        with c1:
                            if col_status and col_status in df_equipamento.columns:
                                status_options = df_equipamento[col_status].dropna().unique().tolist()
                            else:
                                status_options = []
                            status_filtro_eq = st.multiselect(
                                "📊 Status",
                                options=status_options,
                                default=status_options,
                                key="status_eq",
                            )

                        with c2:
                            periodo_eq = st.selectbox(
                                "📅 Período",
                                ["Todos", "Último mês", "Últimos 3 meses", "Últimos 6 meses", "Último ano"],
                                key="periodo_eq",
                            )

                        with c3:
                            filtro_entrega_eq = st.selectbox(
                                "🚚 Entrega",
                                ["Todos", "Apenas Entregues", "Apenas Pendentes"],
                                key="entrega_eq",
                            )

                        df_eq_filtrado = df_equipamento.copy()

                        if status_filtro_eq and col_status:
                            df_eq_filtrado = df_eq_filtrado[df_eq_filtrado[col_status].isin(status_filtro_eq)]

                        if periodo_eq != "Todos" and col_data:
                            hoje = datetime.now()
                            if periodo_eq == "Último mês":
                                data_limite = hoje - pd.DateOffset(months=1)
                            elif periodo_eq == "Últimos 3 meses":
                                data_limite = hoje - pd.DateOffset(months=3)
                            elif periodo_eq == "Últimos 6 meses":
                                data_limite = hoje - pd.DateOffset(months=6)
                            else:
                                data_limite = hoje - pd.DateOffset(years=1)

                            dt = _safe_datetime_series(df_eq_filtrado[col_data])
                            df_eq_filtrado = df_eq_filtrado[dt >= data_limite]

                        if col_entregue and col_entregue in df_eq_filtrado.columns:
                            if filtro_entrega_eq == "Apenas Entregues":
                                df_eq_filtrado = df_eq_filtrado[df_eq_filtrado[col_entregue] == True]
                            elif filtro_entrega_eq == "Apenas Pendentes":
                                df_eq_filtrado = df_eq_filtrado[df_eq_filtrado[col_entregue] == False]

                        st.markdown("---")

                        c1, c2, c3, c4 = st.columns(4)

                        with c1:
                            st.metric("📦 Total de Pedidos", len(df_eq_filtrado))

                        with c2:
                            st.metric(
                                "🔧 Materiais Diferentes",
                                int(df_eq_filtrado["descricao"].nunique()) if "descricao" in df_eq_filtrado.columns else 0,
                            )

                        with c3:
                            valor_total = float(df_eq_filtrado[col_total].sum()) if col_total else 0.0
                            st.metric("💰 Valor Total", formatar_moeda_br(valor_total))

                        with c4:
                            if col_entregue:
                                entregues = int((df_eq_filtrado[col_entregue] == True).sum())
                                st.metric("✅ Entregues", f"{entregues}/{len(df_eq_filtrado)}")
                            else:
                                st.metric("✅ Entregues", "—")

                        st.markdown("---")

                        if df_eq_filtrado.empty:
                            st.warning("⚠️ Nenhum material encontrado com os filtros aplicados")
                        else:
                            # Agrupar por código+descrição para evitar ambiguidade
                            group_cols = ["descricao"]
                            if "cod_material" in df_eq_filtrado.columns:
                                group_cols = ["cod_material", "descricao"]

                            agg_map = {
                                "id": "count" if "id" in df_eq_filtrado.columns else "size",
                            }
                            if col_total:
                                agg_map[col_total] = "sum"
                            if col_qtd:
                                agg_map[col_qtd] = "sum"
                            if col_entregue:
                                agg_map[col_entregue] = lambda x: int((x == True).sum())

                            materiais_equipamento = (
                                df_eq_filtrado.groupby(group_cols, dropna=False)
                                .agg(agg_map)
                                .reset_index()
                            )

                            # Renomear colunas
                            rename_map = {}
                            if "id" in materiais_equipamento.columns:
                                rename_map["id"] = "Pedidos"
                            else:
                                rename_map["size"] = "Pedidos"
                            if col_total:
                                rename_map[col_total] = "Valor Total"
                            if col_qtd:
                                rename_map[col_qtd] = "Qtd Total"
                            if col_entregue:
                                rename_map[col_entregue] = "Entregues"

                            materiais_equipamento = materiais_equipamento.rename(columns=rename_map)
                            if "Pedidos" in materiais_equipamento.columns:
                                materiais_equipamento = materiais_equipamento.sort_values("Pedidos", ascending=False)

                            st.markdown(f"#### 📋 Materiais do Equipamento **{equipamento_selecionado}**")
                            st.caption(f"Mostrando {len(materiais_equipamento)} material(is) • {len(df_eq_filtrado)} pedido(s)")

                            for idx, row in materiais_equipamento.iterrows():
                                cols = st.columns([3, 1, 1, 1, 1])
                                cod = row.get("cod_material") if "cod_material" in materiais_equipamento.columns else None
                                desc = row.get("descricao", "")

                                with cols[0]:
                                    titulo = f"{desc}"
                                    if pd.notna(cod) and str(cod).strip():
                                        titulo = f"{desc}  ·  ({cod})"
                                    st.markdown(f"**{titulo}**")

                                with cols[1]:
                                    st.metric("Pedidos", int(row.get("Pedidos", 0)))

                                with cols[2]:
                                    vt = float(row.get("Valor Total", 0.0)) if "Valor Total" in row else 0.0
                                    st.metric("Valor", formatar_moeda_br(vt))

                                with cols[3]:
                                    if "Entregues" in row and "Pedidos" in row:
                                        st.metric("Entregues", f"{int(row.get('Entregues', 0))}/{int(row.get('Pedidos', 0))}")
                                    else:
                                        st.metric("Entregues", "—")

                                with cols[4]:
                                    if st.button("Ver Ficha", key=f"eq_{idx}"):
                                        st.session_state["material_fixo"] = {"cod": cod, "desc": desc}
                                        st.session_state["tipo_busca_ficha"] = "equipamento"
                                        st.session_state["equipamento_ctx"] = equipamento_selecionado
                                        st.session_state["departamento_ctx"] = ""
                                        st.session_state["modo_ficha_material"] = True
                                        st.rerun()

                                st.markdown("---")

        # ============================================================
        # TAB 3: BUSCA POR DEPARTAMENTO
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
                    c1, c2 = st.columns([4, 1])

                    with c1:
                        departamento_selecionado = st.selectbox(
                            "Selecione o Departamento:",
                            options=[""] + departamentos,
                            format_func=lambda x: "Selecione..." if x == "" else x,
                            key="select_departamento",
                        )

                    with c2:
                        st.markdown("<br>", unsafe_allow_html=True)
                        if st.button("🔄 Limpar", key="limpar_departamento"):
                            st.session_state.pop("material_fixo", None)
                            st.session_state.pop("tipo_busca_ficha", None)
                            st.session_state.pop("equipamento_ctx", None)
                            st.session_state.pop("departamento_ctx", None)
                            st.rerun()

                    if departamento_selecionado:
                        df_departamento = df_pedidos[df_pedidos[col_dep] == departamento_selecionado].copy()
                        st.markdown("---")

                        st.markdown("#### 🎛️ Filtros Avançados")
                        c1, c2, c3, c4 = st.columns(4)

                        with c1:
                            if col_status and col_status in df_departamento.columns:
                                status_options_dep = df_departamento[col_status].dropna().unique().tolist()
                            else:
                                status_options_dep = []
                            status_filtro_dep = st.multiselect(
                                "📊 Status",
                                options=status_options_dep,
                                default=status_options_dep,
                                key="status_dep",
                            )

                        with c2:
                            periodo_dep = st.selectbox(
                                "📅 Período",
                                ["Todos", "Último mês", "Últimos 3 meses", "Últimos 6 meses", "Último ano"],
                                key="periodo_dep",
                            )

                        with c3:
                            filtro_entrega_dep = st.selectbox(
                                "🚚 Entrega",
                                ["Todos", "Apenas Entregues", "Apenas Pendentes"],
                                key="entrega_dep",
                            )

                        with c4:
                            if col_equip and col_equip in df_departamento.columns:
                                equipamentos_dep = ["Todos"] + sorted(
                                    df_departamento[col_equip].dropna().astype(str).unique().tolist()
                                )
                            else:
                                equipamentos_dep = ["Todos"]
                            filtro_equipamento_dep = st.selectbox(
                                "🔧 Equipamento",
                                options=equipamentos_dep,
                                key="equipamento_dep",
                            )

                        df_dep_filtrado = df_departamento.copy()

                        if status_filtro_dep and col_status:
                            df_dep_filtrado = df_dep_filtrado[df_dep_filtrado[col_status].isin(status_filtro_dep)]

                        if periodo_dep != "Todos" and col_data:
                            hoje = datetime.now()
                            if periodo_dep == "Último mês":
                                data_limite = hoje - pd.DateOffset(months=1)
                            elif periodo_dep == "Últimos 3 meses":
                                data_limite = hoje - pd.DateOffset(months=3)
                            elif periodo_dep == "Últimos 6 meses":
                                data_limite = hoje - pd.DateOffset(months=6)
                            else:
                                data_limite = hoje - pd.DateOffset(years=1)

                            dt = _safe_datetime_series(df_dep_filtrado[col_data])
                            df_dep_filtrado = df_dep_filtrado[dt >= data_limite]

                        if col_entregue and col_entregue in df_dep_filtrado.columns:
                            if filtro_entrega_dep == "Apenas Entregues":
                                df_dep_filtrado = df_dep_filtrado[df_dep_filtrado[col_entregue] == True]
                            elif filtro_entrega_dep == "Apenas Pendentes":
                                df_dep_filtrado = df_dep_filtrado[df_dep_filtrado[col_entregue] == False]

                        if filtro_equipamento_dep != "Todos" and col_equip:
                            df_dep_filtrado = df_dep_filtrado[df_dep_filtrado[col_equip] == filtro_equipamento_dep]

                        st.markdown("---")

                        c1, c2, c3, c4 = st.columns(4)

                        with c1:
                            st.metric("📦 Total de Pedidos", len(df_dep_filtrado))

                        with c2:
                            st.metric(
                                "🔧 Materiais Diferentes",
                                int(df_dep_filtrado["descricao"].nunique()) if "descricao" in df_dep_filtrado.columns else 0,
                            )

                        with c3:
                            valor_total = float(df_dep_filtrado[col_total].sum()) if col_total else 0.0
                            st.metric("💰 Valor Total", formatar_moeda_br(valor_total))

                        with c4:
                            equipamentos_unicos = int(df_dep_filtrado[col_equip].nunique()) if col_equip else 0
                            st.metric("⚙️ Equipamentos", equipamentos_unicos)

                        st.markdown("---")

                        if df_dep_filtrado.empty:
                            st.warning("⚠️ Nenhum material encontrado com os filtros aplicados")
                        else:
                            group_cols = ["descricao"]
                            if "cod_material" in df_dep_filtrado.columns:
                                group_cols = ["cod_material", "descricao"]

                            agg_map = {
                                "id": "count" if "id" in df_dep_filtrado.columns else "size",
                            }
                            if col_total:
                                agg_map[col_total] = "sum"
                            if col_qtd:
                                agg_map[col_qtd] = "sum"
                            if col_equip:
                                agg_map[col_equip] = "nunique"
                            if col_entregue:
                                agg_map[col_entregue] = lambda x: int((x == True).sum())

                            materiais_departamento = (
                                df_dep_filtrado.groupby(group_cols, dropna=False)
                                .agg(agg_map)
                                .reset_index()
                            )

                            rename_map = {}
                            if "id" in materiais_departamento.columns:
                                rename_map["id"] = "Pedidos"
                            else:
                                rename_map["size"] = "Pedidos"
                            if col_total:
                                rename_map[col_total] = "Valor Total"
                            if col_qtd:
                                rename_map[col_qtd] = "Qtd Total"
                            if col_equip:
                                rename_map[col_equip] = "Equipamentos"
                            if col_entregue:
                                rename_map[col_entregue] = "Entregues"

                            materiais_departamento = materiais_departamento.rename(columns=rename_map)
                            if "Pedidos" in materiais_departamento.columns:
                                materiais_departamento = materiais_departamento.sort_values("Pedidos", ascending=False)

                            st.markdown(f"#### 📋 Materiais do Departamento **{departamento_selecionado}**")
                            st.caption(
                                f"Mostrando {len(materiais_departamento)} material(is) • {len(df_dep_filtrado)} pedido(s)"
                            )

                            for idx, row in materiais_departamento.iterrows():
                                cols = st.columns([3, 1, 1, 1, 1, 1])

                                cod = row.get("cod_material") if "cod_material" in materiais_departamento.columns else None
                                desc = row.get("descricao", "")

                                with cols[0]:
                                    titulo = f"{desc}"
                                    if pd.notna(cod) and str(cod).strip():
                                        titulo = f"{desc}  ·  ({cod})"
                                    st.markdown(f"**{titulo}**")

                                with cols[1]:
                                    st.metric("Pedidos", int(row.get("Pedidos", 0)))

                                with cols[2]:
                                    vt = float(row.get("Valor Total", 0.0)) if "Valor Total" in row else 0.0
                                    st.metric("Valor", formatar_moeda_br(vt))

                                with cols[3]:
                                    st.metric("Equip.", int(row.get("Equipamentos", 0)) if "Equipamentos" in row else 0)

                                with cols[4]:
                                    if "Entregues" in row and "Pedidos" in row:
                                        st.metric("Entregues", f"{int(row.get('Entregues', 0))}/{int(row.get('Pedidos', 0))}")
                                    else:
                                        st.metric("Entregues", "—")

                                with cols[5]:
                                    if st.button("Ver Ficha", key=f"dep_{idx}"):
                                        st.session_state["material_fixo"] = {"cod": cod, "desc": desc}
                                        st.session_state["tipo_busca_ficha"] = "departamento"
                                        st.session_state["equipamento_ctx"] = (
                                            filtro_equipamento_dep if filtro_equipamento_dep != "Todos" else ""
                                        )
                                        st.session_state["departamento_ctx"] = departamento_selecionado
                                        st.session_state["modo_ficha_material"] = True
                                        st.rerun()

                                st.markdown("---")


    # ============================================================
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
        tab_ficha, tab_hist = st.tabs(["📄 Ficha Técnica", "📚 Histórico Detalhado"])

        with tab_ficha:
            # Cards de KPIs existentes
            fm.criar_cards_kpis(historico_material)

            # KPIs novos (planejamento / gestão)
            st.markdown("#### 🧠 Indicadores avançados")
            k1, k2, k3 = st.columns(3)

            with k1:
                # Volatilidade de preço (desvio padrão da variação percentual)
                volatilidade = None
                if col_unit and col_unit in historico_material.columns:
                    unit = pd.to_numeric(historico_material[col_unit], errors="coerce")
                    volatilidade = float(unit.pct_change().std() * 100) if unit.notna().sum() >= 3 else None

                st.metric("📉 Volatilidade de Preço", f"{volatilidade:.1f}%" if volatilidade is not None else "—")

            with k2:
                # Tempo médio entre compras (dias)
                tempo_medio = None
                if col_data and col_data in historico_material.columns:
                    datas = _safe_datetime_series(historico_material[col_data]).dropna().sort_values()
                    if len(datas) >= 3:
                        tempo_medio = float(datas.diff().dt.days.mean())
                st.metric("⏱️ Dias entre Compras", f"{int(tempo_medio)}" if tempo_medio is not None else "—")

            with k3:
                # Fornecedor mais frequente (se existir)
                fornecedor_top = None
                if col_fornecedor and col_fornecedor in historico_material.columns:
                    fornecedor_top = historico_material[col_fornecedor].dropna().astype(str).value_counts().head(1)
                    fornecedor_top = fornecedor_top.index[0] if not fornecedor_top.empty else None
                st.metric("🏷️ Fornecedor mais frequente", fornecedor_top if fornecedor_top else "—")

            st.markdown("<br>", unsafe_allow_html=True)

            col1, col2 = st.columns([2, 1])

            with col1:
                fm.criar_grafico_evolucao_precos(historico_material)
                st.markdown("<br>", unsafe_allow_html=True)
                fm.criar_comparacao_visual_precos(historico_material)

            with col2:
                fm.criar_mini_mapa_fornecedores(historico_material)

            st.markdown("---")
            fm.criar_ranking_fornecedores_visual(historico_material)

            st.markdown("---")
            fm.criar_timeline_compras(historico_material)

            st.markdown("---")
            _call_insights_automaticos(historico_material, material_atual)

        with tab_hist:
            st.markdown("### 📚 Histórico Detalhado")
            st.caption("Aqui você consegue auditar compras, comparar condições e exportar para análise externa.")

            # Tabela compacta e útil
            cols_preferidas = []
            for c in [col_data, col_qtd, col_unit, col_total, col_fornecedor, col_status, col_entregue, col_equip, col_dep]:
                if c and c in historico_material.columns and c not in cols_preferidas:
                    cols_preferidas.append(c)

            if not cols_preferidas:
                cols_preferidas = historico_material.columns.tolist()

            df_hist = historico_material.copy()
            if col_data and col_data in df_hist.columns:
                df_hist["_dt"] = _safe_datetime_series(df_hist[col_data])
                df_hist = df_hist.sort_values("_dt", ascending=False).drop(columns=["_dt"], errors="ignore")

            st.dataframe(
                df_hist[cols_preferidas],
                use_container_width=True,
                hide_index=True,
            )

            st.markdown("---")

            # Exportação CSV contextual
            csv_bytes = df_hist.to_csv(index=False).encode("utf-8")
            nome = str(cod_show or "material").replace(" ", "_")
            st.download_button(
                "📥 Exportar histórico do material (CSV)",
                data=csv_bytes,
                file_name=f"historico_{nome}.csv",
                mime="text/csv",
                use_container_width=True,
            )

            # Botão de "desfixar"
            if st.button("🧹 Limpar material selecionado", use_container_width=True):
                st.session_state.pop("material_fixo", None)
                st.session_state.pop("tipo_busca_ficha", None)
                st.session_state.pop("equipamento_ctx", None)
                st.session_state.pop("departamento_ctx", None)
                st.rerun()

        st.markdown("---")
        if st.button("← Voltar para Consulta", use_container_width=True):
            st.session_state.pagina = "Consultar Pedidos"
            st.rerun()
