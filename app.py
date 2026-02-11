import streamlit as st

st.set_page_config(
    page_title="Sistema de Follow-Up",
    layout="wide",
    page_icon="📊"
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
from src.ui.ficha_material_page import ficha_material
from src.ui.gestao_usuarios import exibir_gestao_usuarios

# Conexão (cacheada) com Supabase
supabase = init_supabase()


def main():
    # Verificar autenticação
    if not verificar_autenticacao():
        exibir_login(supabase)
        return

    # Carregar dados
    df_pedidos = carregar_pedidos(supabase)
    df_fornecedores = carregar_fornecedores(supabase, incluir_inativos=True)

    # Alertas (sempre retorna dict completo)
    alertas = sa.calcular_alertas(df_pedidos, df_fornecedores)

    # CSS global (sidebar + menu)
    st.markdown(
        """
        <style>
            /* Sidebar */
            section[data-testid="stSidebar"] {
                background-color: #111827;
            }
            section[data-testid="stSidebar"] > div {
                padding-top: 1rem;
            }

            /* Radio/menu */
            div[role="radiogroup"] label {
                padding: 10px 12px;
                border-radius: 10px;
                margin-bottom: 6px;
            }
            div[role="radiogroup"] label:hover {
                background-color: rgba(255,255,255,0.06);
            }
            div[role="radiogroup"] input:checked + div {
                background-color: #2563eb !important;
                border-radius: 10px;
            }

            /* Sidebar headings */
            .fu-side-title {
                font-size: 12px;
                letter-spacing: 0.06em;
                text-transform: uppercase;
                opacity: 0.75;
                margin: 8px 0 6px 0;
            }

            /* User card */
            .fu-user-card {
                background-color: rgba(255,255,255,0.06);
                border: 1px solid rgba(255,255,255,0.10);
                border-radius: 14px;
                padding: 12px 12px;
                margin-bottom: 10px;
            }
            .fu-user-label {
                font-size: 12px;
                opacity: 0.8;
                margin: 0 0 4px 0;
            }
            .fu-user-name {
                font-size: 16px;
                font-weight: 700;
                margin: 0;
            }
            .fu-user-role {
                font-size: 12px;
                opacity: 0.75;
                margin: 4px 0 0 0;
            }

            /* Logout button (best-effort) */
            button[kind="secondary"] {
                background-color: rgba(255,255,255,0.06);
                border: 1px solid rgba(255,255,255,0.12);
            }
        </style>
        """,
        unsafe_allow_html=True,
    )

    # Sidebar
    with st.sidebar:
        nome = st.session_state.usuario.get("nome", "Usuário")
        perfil = str(st.session_state.usuario.get("perfil", "")).title() or "—"

        st.markdown(
            f"""
            <div class="fu-user-card">
                <p class="fu-user-label">👤 Usuário</p>
                <p class="fu-user-name">{nome}</p>
                <p class="fu-user-role">{perfil}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Badge de alertas
        try:
            if int(alertas.get("total", 0)) > 0:
                sa.exibir_badge_alertas(alertas)
                st.markdown("---")
        except Exception:
            pass

        # Menu de navegação
        if st.session_state.usuario.get("perfil") == "admin":
            st.markdown('<div class="fu-side-title">Menu</div>', unsafe_allow_html=True)
            pagina = st.radio(
                "",
                [
                    "Dashboard",
                    "🔔 Alertas e Notificações",
                    "Consultar Pedidos",
                    "Ficha de Material",
                    "Gestão de Pedidos",
                    "Mapa Geográfico",
                    "👥 Gestão de Usuários",
                    "💾 Backup",
                ],
                label_visibility="collapsed",
            )
        else:
            st.markdown('<div class="fu-side-title">📊 Operações</div>', unsafe_allow_html=True)
            pagina_ops = st.radio(
                "",
                ["Dashboard", "🔔 Alertas e Notificações", "Consultar Pedidos"],
                label_visibility="collapsed",
                key="menu_ops",
            )

            st.markdown('<div class="fu-side-title">🛠️ Gestão</div>', unsafe_allow_html=True)
            pagina_gestao = st.radio(
                "",
                ["Ficha de Material", "Mapa Geográfico"],
                label_visibility="collapsed",
                key="menu_gestao",
            )

            # unifica seleção (sempre define `pagina`)
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

        st.markdown("---")
        st.caption("© Follow-up de Compras v3.0")
        st.caption("Criado por André Luis e Yasmim Lima")

    # Renderizar página selecionada
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
