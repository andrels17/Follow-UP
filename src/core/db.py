import os
import streamlit as st
from supabase import create_client


def _get_secret(name: str) -> str | None:
    if "SUPABASE_URL" in st.secrets and name in st.secrets:
        return st.secrets.get(name)
    return os.getenv(name)


@st.cache_resource
def init_supabase_admin():
    """Cliente Supabase com SERVICE ROLE (bypass RLS). Use apenas para tarefas administrativas."""
    url = _get_secret("SUPABASE_URL")
    key = _get_secret("SUPABASE_SERVICE_ROLE_KEY") or _get_secret("SUPABASE_KEY")
    if not url or not key:
        raise RuntimeError("SUPABASE_URL e SUPABASE_SERVICE_ROLE_KEY (ou SUPABASE_KEY) não configurados.")
    return create_client(url, key)


@st.cache_resource
def init_supabase_anon():
    """Cliente Supabase com ANON KEY (respeita RLS quando autenticado)."""
    url = _get_secret("SUPABASE_URL")
    key = _get_secret("SUPABASE_ANON_KEY") or _get_secret("SUPABASE_KEY")
    if not url or not key:
        raise RuntimeError("SUPABASE_URL e SUPABASE_ANON_KEY (ou SUPABASE_KEY) não configurados.")
    return create_client(url, key)


def get_supabase_user_client(access_token: str):
    """Cria um client Supabase autenticado com JWT do usuário (RLS ativo)."""
    supa = init_supabase_anon()
    # supabase-py: aplica JWT no PostgREST
    try:
        supa.postgrest.auth(access_token)
    except Exception:
        # fallback: algumas versões usam "auth" em outro ponto
        try:
            supa.auth.set_session(access_token, "")  # type: ignore
        except Exception:
            pass
    return supa
