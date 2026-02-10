"""Autenticação e login."""
from __future__ import annotations

import hashlib
from datetime import datetime

import streamlit as st

import backup_auditoria as ba

def criar_senha_hash(senha: str) -> str:
    """Cria hash SHA256 da senha"""
    return hashlib.sha256(senha.encode()).hexdigest()

def fazer_login(email: str, senha: str, _supabase):
    """Valida credenciais do usuário"""
    try:
        senha_hash = criar_senha_hash(senha)
        resultado = _supabase.table('usuarios').select('*').eq('email', email).eq('senha_hash', senha_hash).eq('ativo', True).execute()
        
        if resultado.data:
            return resultado.data[0]
        return None
    except Exception as e:
        st.error(f"Erro ao fazer login: {e}")
        return None

def verificar_autenticacao():
    """Verifica se usuário está autenticado"""
    if 'usuario' not in st.session_state:
        return False
    return True

def exibir_login(_supabase):
    """Exibe tela de login"""
    st.markdown("""
    <style>
    .login-container {
        max-width: 400px;
        margin: 100px auto;
        padding: 2rem;
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
    </style>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("## 📦 Follow-up de Compras")
        st.markdown("---")
        
        email = st.text_input("📧 Email", key="login_email")
        senha = st.text_input("🔒 Senha", type="password", key="login_senha")
        
        if st.button("🚀 Entrar", use_container_width=True):
            if email and senha:
                usuario = fazer_login(email, senha, _supabase)
                if usuario:
                    st.session_state.usuario = usuario
                    st.success("✅ Login realizado com sucesso!")
                    st.rerun()
                else:
                    st.error("❌ Email ou senha incorretos")
            else:
                st.warning("⚠️ Preencha todos os campos")
        
        st.markdown("---")
        st.caption("💡 Primeira vez? Entre em contato com o administrador")

# ============================================
# FUNÇÕES DE DADOS
# ============================================


