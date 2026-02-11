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
from src.core.config import configure_page
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


def main():
    # Verificar autenticação
    if not verificar_autenticacao():
        exibir_login(supabase)
        return

    
    df_pedidos = carregar_pedidos(supabase)
    df_fornecedores = carregar_fornecedores(supabase, incluir_inativos=True)
    
    alertas = (
        sa.calcular_alertas(df_pedidos, df_fornecedores)
        if not df_pedidos.empty
        else {"total": 0}
    )


    # Sidebar com informações do usuário
    with st.sidebar:
        st.markdown(
            f"""
        ### 👤 Bem-vindo(a)!
        **{st.session_state.usuario['nome']}**  
        *{st.session_state.usuario['perfil'].title()}*
        """
        )

        st.markdown("---")

        # Badge de alertas
        if alertas["total"] > 0:
            sa.exibir_badge_alertas(alertas)
            st.markdown("---")

        # Menu de navegação
        if st.session_state.usuario["perfil"] == "admin":
            pagina = st.radio(
                "📋 Menu",
                [
                    "Dashboard",
                    "🔔 Alertas e Notificações",
                    "Consultar Pedidos",
                    "Ficha de Material",
                    "Gestão de Pedidos",
                    "Mapa Geográfico",
                    "👥 Gestão de Usuários",
                    #"🔒 Auditoria e Logs",
                    "💾 Backup",
                ],
                label_visibility="collapsed",
            )
        else:
            pagina = st.radio(
                "📋 Menu",
                [
                    "Dashboard",
                    "🔔 Alertas e Notificações",
                    "Consultar Pedidos",
                    "Ficha de Material",
                    "Mapa Geográfico",
                ],
                label_visibility="collapsed",
            )

        st.markdown("---")

        if st.button("🚪 Sair", use_container_width=True):
            ba.registrar_acao(
                st.session_state.usuario,
                "Logout",
                {"timestamp": datetime.now().isoformat()},
                supabase,
            )
            del st.session_state.usuario
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
    #elif pagina == "🔒 Auditoria e Logs":
        #ba.exibir_painel_auditoria(supabase)
    elif pagina == "💾 Backup":
        ba.realizar_backup_manual(supabase)


if __name__ == "__main__":
    main()
