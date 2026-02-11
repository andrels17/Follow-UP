import streamlit as st

st.set_page_config(
    page_title="Sistema de Follow-Up",
    layout="wide",
    page_icon="📊",
)

from datetime import datetime

import src.services.sistema_alertas as sa
import backup_auditoria as ba
from src.repositories.fornecedores import carregar_fornecedores
from src.core.config import configure_page  # noqa: F401
from src.core.db import init_supabase
from src.core.auth import verificar_autenticacao, exibir_login
from src.repositories.pedidos import carregar_pedidos
from src.utils.formatting import formatar_moeda_br

from src.ui.dashboard import exibir_dashboard
from src.ui.mapa import exibir_mapa
from src.ui.consulta import exibir_consulta_pedidos
from src.ui.gestao_pedidos import exibir_gestao_pedidos
from src.ui.ficha_material_page import exibir_ficha_material
from src.ui.gestao_usuarios import exibir_gestao_usuarios

# Conexão (cacheada) com Supabase
supabase = init_supabase()


def _industrial_sidebar_css() -> None:
    """Tema corporativo industrial (dark slate + laranja) + animações suaves."""
    st.markdown(
        r"""
        <style>
            :root {
                --fu-bg: #0b1220;
                --fu-card: rgba(255,255,255,0.06);
                --fu-border: rgba(255,255,255,0.10);
                --fu-text: rgba(255,255,255,0.92);
                --fu-muted: rgba(255,255,255,0.72);
                --fu-accent: #f59e0b;      /* industrial amber */
                --fu-accent2: #fb923c;     /* orange */
                --fu-blue: #2563eb;
            }

            section[data-testid="stSidebar"] {
                background:
                    radial-gradient(1100px 420px at 15% 0%, rgba(245,158,11,0.12), transparent 55%),
                    radial-gradient(900px 380px at 80% 18%, rgba(59,130,246,0.10), transparent 55%),
                    var(--fu-bg);
            }

            section[data-testid="stSidebar"] > div {
                padding-top: 0.8rem;
            }

            .fu-card {
                background: var(--fu-card);
                border: 1px solid var(--fu-border);
                border-radius: 14px;
                padding: 12px 12px;
                margin-bottom: 10px;
                color: var(--fu-text);
                box-shadow: 0 10px 25px rgba(0,0,0,0.25);
            }

            .fu-user-label { font-size: 12px; opacity: .8; margin: 0 0 4px 0; }
            .fu-user-name { font-size: 16px; font-weight: 800; margin: 0; letter-spacing: .2px; }
            .fu-user-role { font-size: 12px; opacity: .75; margin: 4px 0 0 0; }

            div[role="radiogroup"] label {
                padding: 10px 12px;
                border-radius: 12px;
                margin-bottom: 6px;
                transition: transform .12s ease, background-color .12s ease, border .12s ease;
                border: 1px solid transparent;
            }
            div[role="radiogroup"] label:hover {
                background-color: rgba(255,255,255,0.06);
                transform: translateX(2px);
                border: 1px solid rgba(245,158,11,0.22);
            }
            div[role="radiogroup"] input:checked + div {
                background: linear-gradient(135deg, rgba(245,158,11,0.22), rgba(37,99,235,0.18));
                border-radius: 12px;
                border: 1px solid rgba(245,158,11,0.35);
            }

            details {
                background: rgba(255,255,255,0.02);
                border: 1px solid rgba(255,255,255,0.06);
                border-radius: 14px;
                padding: 6px 10px;
                margin-bottom: 10px;
            }
            summary {
                cursor: pointer;
                font-weight: 800;
                color: var(--fu-text);
            }

            button[kind="secondary"] {
                background-color: rgba(255,255,255,0.06);
                border: 1px solid rgba(255,255,255,0.12);
                transition: transform .08s ease;
            }
            button[kind="secondary"]:hover { transform: translateY(-1px); }

            .fu-bar {
                height: 3px;
                border-radius: 999px;
                background: linear-gradient(90deg, var(--fu-accent), rgba(251,146,60,0.0));
                margin: 10px 0 8px 0;
                opacity: .9;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _label_alertas(total_alertas: int) -> str:
    if total_alertas and total_alertas > 0:
        return f"🔔 Alertas e Notificações  🔴 ({int(total_alertas)})"
    return "🔔 Alertas e Notificações"


def main():
    if not verificar_autenticacao():
        exibir_login(supabase)
        return

    df_pedidos = carregar_pedidos(supabase)
    df_fornecedores = carregar_fornecedores(supabase, incluir_inativos=True)

    alertas = sa.calcular_alertas(df_pedidos, df_fornecedores)
    total_alertas = int(alertas.get("total", 0) or 0)

    _industrial_sidebar_css()

    with st.sidebar:
        nome = st.session_state.usuario.get("nome", "Usuário")
        perfil = str(st.session_state.usuario.get("perfil", "")).title() or "—"

        st.markdown(
            f"""
            <div class="fu-card">
                <p class="fu-user-label">👷 Sistema de Follow-Up</p>
                <div class="fu-bar"></div>
                <p class="fu-user-name">{nome}</p>
                <p class="fu-user-role">{perfil}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Contador no topo (card)
        if total_alertas > 0:
            st.markdown(
                f"""
                <div class="fu-card" style="
                    border: 1px solid rgba(245,158,11,0.35);
                    background: linear-gradient(135deg, rgba(245,158,11,0.18), rgba(255,255,255,0.04));
                ">
                    <div style="display:flex; align-items:center; justify-content:space-between;">
                        <div style="font-weight:900;">🔔 Alertas</div>
                        <div style="
                            background: rgba(239,68,68,0.95);
                            color: white;
                            padding: 2px 10px;
                            border-radius: 999px;
                            font-weight: 900;
                            font-size: 12px;
                        ">{total_alertas}</div>
                    </div>
                    <div style="margin-top:6px; font-size: 12px; opacity: .82;">
                        Revise atrasos, vencimentos e fornecedores.
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        is_admin = st.session_state.usuario.get("perfil") == "admin"
        alertas_label = _label_alertas(total_alertas)

        # Menu colapsável (expanders)
        with st.expander("📊 Operações", expanded=True):
            pagina_ops = st.radio(
                "",
                ["Dashboard", alertas_label, "Consultar Pedidos"],
                label_visibility="collapsed",
                key="menu_ops",
            )

        with st.expander("🛠️ Gestão", expanded=is_admin):
            if is_admin:
                pagina_gestao = st.radio(
                    "",
                    ["Ficha de Material", "Gestão de Pedidos", "Mapa Geográfico", "👥 Gestão de Usuários", "💾 Backup"],
                    label_visibility="collapsed",
                    key="menu_gestao_admin",
                )
            else:
                pagina_gestao = st.radio(
                    "",
                    ["Ficha de Material", "Mapa Geográfico"],
                    label_visibility="collapsed",
                    key="menu_gestao_user",
                )

        pagina = pagina_ops or pagina_gestao

        st.markdown("---")

        if st.button("🚪 Sair", use_container_width=True):
            try:
                ba.registrar_acao(
                    st.session_state.usuario,
                    "Logout",
                    {"timestamp": datetime.now().isoformat()},
                    supabase,
                )
            except Exception:
                pass
            try:
                del st.session_state.usuario
            except Exception:
                pass
            st.rerun()

        st.caption("© Follow-up de Compras v3.0")
        st.caption("Criado por André Luis e Yasmim Lima")

    # Normaliza label de alertas
    if pagina == alertas_label:
        pagina = "🔔 Alertas e Notificações"

    if pagina == "Dashboard":
        exibir_dashboard(supabase)
    elif pagina == "🔔 Alertas e Notificações":
        sa.exibir_painel_alertas(alertas, formatar_moeda_br)
    elif pagina == "Consultar Pedidos":
        exibir_consulta_pedidos(supabase)
    elif pagina == "Ficha de Material":
        exibir_ficha_material(supabase)
    elif pagina == "Gestão de Pedidos":
        exibir_gestao_pedidos(supabase)
    elif pagina == "Mapa Geográfico":
        exibir_mapa(supabase)
    elif pagina == "👥 Gestão de Usuários":
        exibir_gestao_usuarios(supabase)
    elif pagina == "💾 Backup":
        ba.realizar_backup_manual(supabase)


if __name__ == "__main__":
    main()
