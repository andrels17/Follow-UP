import streamlit as st
import json
import base64
import textwrap

st.set_page_config(
    page_title="Sistema de Follow-Up",
    layout="wide",
    page_icon="📊",
)

from datetime import datetime, timezone

import src.services.sistema_alertas as sa
import backup_auditoria as ba
from src.repositories.fornecedores import carregar_fornecedores
from src.core.config import configure_page  # noqa: F401
from src.core.db import init_supabase_admin, init_supabase_anon, get_supabase_user_client
from src.core.auth import verificar_autenticacao, exibir_login, fazer_logout
from src.repositories.pedidos import carregar_pedidos
from src.utils.formatting import formatar_moeda_br

from src.ui.dashboard import exibir_dashboard
from src.ui.mapa import exibir_mapa
from src.ui.consulta import exibir_consulta_pedidos
from src.ui.gestao_pedidos import exibir_gestao_pedidos
from src.ui.ficha_material_page import exibir_ficha_material
from src.ui.gestao_usuarios import exibir_gestao_usuarios

# Conexão (cacheada) com Supabase
supabase_admin = init_supabase_admin()
supabase_anon = init_supabase_anon()





def _jwt_claim_exp(token: str):
    """Extrai 'exp' (epoch seconds) do JWT sem validar assinatura."""
    try:
        parts = token.split(".")
        if len(parts) < 2:
            return None
        payload_b64 = parts[1]
        # base64url padding
        payload_b64 += "=" * (-len(payload_b64) % 4)
        payload = json.loads(base64.urlsafe_b64decode(payload_b64.encode("utf-8")).decode("utf-8"))
        return payload.get("exp")
    except Exception:
        return None


def _jwt_expirou() -> bool:
        exp = st.session_state.get("auth_expires_at")
        if not exp:
            token = st.session_state.get("auth_access_token")
            if token:
                exp = _jwt_claim_exp(token)
                # guarda pra próximas execuções
                if exp:
                    st.session_state.auth_expires_at = exp
            if not exp:
                # sem exp conhecido, tenta refresh preventivo
                return True
        try:
            return datetime.now(timezone.utc).timestamp() >= float(exp) - 30
        except Exception:
            return False


def _refresh_session() -> bool:
    """Tenta renovar a sessão usando refresh_token. Retorna True se renovou."""
    rt = st.session_state.get("auth_refresh_token")
    if not rt:
        return False
    try:
        res = supabase_anon.auth.refresh_session(rt)
        session = res.session
        st.session_state.auth_access_token = session.access_token
        st.session_state.auth_refresh_token = session.refresh_token
        st.session_state.auth_expires_at = session.expires_at
        return True
    except Exception:
        return False
def _safe_len(x) -> int:
    try:
        return int(len(x or []))
    except Exception:
        return 0


def _industrial_sidebar_css() -> None:
    """Tema corporativo industrial + barra lateral laranja no item ativo + animações suaves."""
    st.markdown(
        textwrap.dedent(r"""
        <style>
            :root {
                --fu-bg: #0b1220;
                --fu-card: rgba(255,255,255,0.06);
                --fu-border: rgba(255,255,255,0.10);
                --fu-text: rgba(255,255,255,0.92);
                --fu-muted: rgba(255,255,255,0.72);
                --fu-accent: #f59e0b;      /* industrial amber */
                --fu-accent2: #fb923c;     /* orange */
            }

            section[data-testid="stSidebar"] {
                background:
                    radial-gradient(1100px 420px at 15% 0%, rgba(245,158,11,0.12), transparent 55%),
                    radial-gradient(900px 380px at 80% 18%, rgba(59,130,246,0.10), transparent 55%),
                    var(--fu-bg);
            }

            section[data-testid="stSidebar"] > div { padding-top: 0.8rem; }

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

            /* Mini KPIs */
            .fu-kpi-row { display:flex; gap:8px; margin: 6px 0 12px 0; }
            .fu-kpi {
                flex: 1;
                background: rgba(255,255,255,0.04);
                border: 1px solid rgba(255,255,255,0.08);
                border-radius: 12px;
                padding: 10px 10px;
            }
            .fu-kpi-title { font-size: 11px; opacity: .78; margin: 0 0 2px 0; }
            .fu-kpi-value { font-size: 18px; font-weight: 900; margin: 0; }

            /* Menu radio */
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

            /* Item ativo: barra laranja */
            div[role="radiogroup"] input:checked + div {
                background: linear-gradient(135deg, rgba(245,158,11,0.22), rgba(255,255,255,0.04));
                border-radius: 12px;
                box-shadow: inset 4px 0 0 var(--fu-accent);
            }

            /* Expanders */
            details {
                background: rgba(255,255,255,0.02);
                border: 1px solid rgba(255,255,255,0.06);
                border-radius: 14px;
                padding: 6px 10px;
                margin-bottom: 10px;
            }
            summary { cursor: pointer; font-weight: 900; color: var(--fu-text); }

            /* Botões */
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
        """),
        unsafe_allow_html=True,
    )


def _label_alertas(total_alertas: int) -> str:
    if total_alertas and total_alertas > 0:
        return f"🔔 Alertas e Notificações  🔴 ({int(total_alertas)})"
    return "🔔 Alertas e Notificações"


def _sidebar_footer(supabase_client) -> None:
    """Renderiza Sair + créditos (sempre por último na sidebar)."""
    st.markdown("---")
    if st.button("🚪 Sair", use_container_width=True, key="btn_logout_sidebar"):
        try:
            ba.registrar_acao(
                st.session_state.usuario,
                "Logout",
                {"timestamp": datetime.now().isoformat()},
                supabase_client,
            )
        except Exception:
            pass

        try:
            fazer_logout(supabase_anon)
        except Exception:
            pass

        st.rerun()

    st.markdown(
        """
        <div style="font-size:11px; opacity:0.6; margin-top:10px;">
            © Follow-up de Compras v3.0<br>
            Criado por André Luis e Yasmim Lima
        </div>
        """,
        unsafe_allow_html=True,
    )


def main():
    if not verificar_autenticacao():
        exibir_login(supabase_anon)
        return

    # Client do usuário autenticado (RLS ativo)
    # Renova JWT automaticamente se expirou

    if _jwt_expirou():

        ok = _refresh_session()

        if not ok:

            st.warning("Sessão expirada. Faça login novamente.")

            try:

                fazer_logout(supabase_anon)

            except Exception:

                pass

            st.rerun()


    supabase = get_supabase_user_client(st.session_state.auth_access_token)

    # Seleção de empresa (se o usuário tiver mais de uma)
    tenant_opts = st.session_state.get("tenant_options", []) or []
    tenant_id = st.session_state.get("tenant_id")

    # Define padrão
    if not tenant_id and tenant_opts:
        tenant_id = tenant_opts[0]["tenant_id"]
        st.session_state.tenant_id = tenant_id

    # Se o usuário tiver mais de uma empresa, permite escolher
    if tenant_opts and len(tenant_opts) > 1:
        with st.sidebar:
            nomes = {t["tenant_id"]: (t.get("nome") or t["tenant_id"]) for t in tenant_opts}
            current = st.session_state.get("tenant_id") or tenant_opts[0]["tenant_id"]
            ids = list(nomes.keys())
            idx = ids.index(current) if current in ids else 0
            escolhido = st.selectbox(
                "🏢 Empresa",
                options=ids,
                format_func=lambda x: nomes.get(x, x),
                index=idx,
            )

            if escolhido != current:
                st.session_state.tenant_id = escolhido
                # atualiza perfil conforme empresa selecionada
                role = next((t.get("role") for t in tenant_opts if t.get("tenant_id") == escolhido), "user")
                if "usuario" in st.session_state and isinstance(st.session_state.usuario, dict):
                    st.session_state.usuario["tenant_id"] = escolhido
                    st.session_state.usuario["perfil"] = role
                st.rerun()

    tenant_id = st.session_state.get("tenant_id") or tenant_id
    if not tenant_id:
        st.error("❌ Não foi possível determinar sua empresa (tenant).")
        return

    df_pedidos = carregar_pedidos(supabase, tenant_id)
    df_fornecedores = carregar_fornecedores(supabase, tenant_id, incluir_inativos=True)

    alertas = sa.calcular_alertas(df_pedidos, df_fornecedores)
    total_alertas = int(alertas.get("total", 0) or 0)

    atrasados = _safe_len(alertas.get("pedidos_atrasados"))
    criticos = _safe_len(alertas.get("pedidos_criticos"))
    vencendo = _safe_len(alertas.get("pedidos_vencendo"))

    _industrial_sidebar_css()

    # ===== Sidebar topo + menus (SEM botão sair/creditos aqui) =====
    with st.sidebar:
        nome = st.session_state.usuario.get("nome", "Usuário")
        perfil = str(st.session_state.usuario.get("perfil", "")).title() or "—"

        st.markdown(
            textwrap.dedent(f"""<div class="fu-card">
  <p class="fu-user-label">👷 Sistema de Follow-Up</p>
  <div class="fu-bar"></div>
  <p class="fu-user-name">{nome}</p>
  <p class="fu-user-role">{perfil}</p>

  <div class="fu-kpi-row">
    <div class="fu-kpi">
      <p class="fu-kpi-title">⚠️ Atrasados</p>
      <p class="fu-kpi-value">{atrasados}</p>
    </div>
    <div class="fu-kpi">
      <p class="fu-kpi-title">🚨 Críticos</p>
      <p class="fu-kpi-value">{criticos}</p>
    </div>
    <div class="fu-kpi">
      <p class="fu-kpi-title">⏰ Vencendo</p>
      <p class="fu-kpi-value">{vencendo}</p>
    </div>
  </div>
</div>
"""),
            unsafe_allow_html=True,
        )

        if total_alertas > 0:
            st.markdown(
                textwrap.dedent(f"""<div class="fu-card" style="
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
"""),
                unsafe_allow_html=True,
            )

        is_admin = st.session_state.usuario.get("perfil") == "admin"
        alertas_label = _label_alertas(total_alertas)

        # ✅ Controle de navegação (evita o bug "pagina_ops or pagina_gestao")
        if "current_page" not in st.session_state:
            st.session_state.current_page = "Dashboard"

        def _set_page_from_ops():
            st.session_state.current_page = st.session_state.get("menu_ops") or st.session_state.current_page

        def _set_page_from_gestao_admin():
            st.session_state.current_page = st.session_state.get("menu_gestao_admin") or st.session_state.current_page

        def _set_page_from_gestao_user():
            st.session_state.current_page = st.session_state.get("menu_gestao_user") or st.session_state.current_page

        # Sincroniza seleção inicial (menus começam fechados)
        if st.session_state.get("menu_ops") is None:
            st.session_state.menu_ops = "Dashboard"
        if is_admin and st.session_state.get("menu_gestao_admin") is None:
            st.session_state.menu_gestao_admin = "Ficha de Material"
        if (not is_admin) and st.session_state.get("menu_gestao_user") is None:
            st.session_state.menu_gestao_user = "Ficha de Material"

        with st.expander("📊 Operações", expanded=False):
            pagina_ops = st.radio(
                "",
                ["Dashboard", alertas_label, "Consultar Pedidos"],
                label_visibility="collapsed",
                key="menu_ops",
                on_change=_set_page_from_ops,
            )

        with st.expander("🛠️ Gestão", expanded=False):
            if is_admin:
                pagina_gestao = st.radio(
                    "",
                    ["Ficha de Material", "Gestão de Pedidos", "Mapa Geográfico", "👥 Gestão de Usuários", "💾 Backup"],
                    label_visibility="collapsed",
                    key="menu_gestao_admin",
                    on_change=_set_page_from_gestao_admin,
                )
            else:
                pagina_gestao = st.radio(
                    "",
                    ["Ficha de Material", "Mapa Geográfico"],
                    label_visibility="collapsed",
                    key="menu_gestao_user",
                    on_change=_set_page_from_gestao_user,
                )

        # Página atual (definida pelos callbacks)
        pagina = st.session_state.current_page

    # Normaliza label de alertas
    if pagina == alertas_label:
        pagina = "🔔 Alertas e Notificações"

    # ===== Página (pode adicionar filtros na sidebar aqui) =====
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

    # ===== Rodapé da sidebar: sempre depois dos filtros =====
    with st.sidebar:
        _sidebar_footer(supabase)


if __name__ == "__main__":
    main()
