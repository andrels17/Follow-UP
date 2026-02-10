"""Tela: Gestão de usuários."""
from __future__ import annotations

from datetime import datetime

import pandas as pd
import plotly.express as px
import streamlit as st

import backup_auditoria as ba
from src.core.auth import criar_senha_hash

def exibir_gestao_usuarios(_supabase):
    """
    Gestão completa de usuários - Apenas Admin
    Permite criar, editar, ativar/desativar e controlar permissões
    """
    
    # Verificar se é admin
    if st.session_state.usuario['perfil'] != 'admin':
        st.error("⛔ Acesso negado. Apenas administradores podem gerenciar usuários.")
        return
    
    st.title("👥 Gestão de Usuários")
    
    # Definir perfis e permissões
    PERFIS_PERMISSOES = {
        'admin': {
            'nome': 'Administrador',
            'descricao': 'Acesso total ao sistema',
            'cor': '🔴',
            'permissoes': [
                'Dashboard',
                'Alertas e Notificações',
                'Consultar Pedidos',
                'Ficha de Material',
                'Gestão de Pedidos',
                'Mapa Geográfico',
                'Gestão de Usuários',
                'Auditoria e Logs',
                'Backup'
            ]
        },
        'gestor': {
            'nome': 'Gestor',
            'descricao': 'Visualização completa + Gestão de pedidos',
            'cor': '🟡',
            'permissoes': [
                'Dashboard',
                'Alertas e Notificações',
                'Consultar Pedidos',
                'Ficha de Material',
                'Gestão de Pedidos',
                'Mapa Geográfico'
            ]
        },
        'usuario': {
            'nome': 'Usuário',
            'descricao': 'Apenas visualização',
            'cor': '🟢',
            'permissoes': [
                'Dashboard',
                'Alertas e Notificações',
                'Consultar Pedidos',
                'Ficha de Material',
                'Mapa Geográfico'
            ]
        }
    }
    
    # Abas
    tab1, tab2, tab3, tab4 = st.tabs([
        "📋 Lista de Usuários",
        "➕ Novo Usuário",
        "✏️ Editar Usuário",
        "🔐 Perfis e Permissões"
    ])
    
    # ============================================
    # TAB 1: LISTA DE USUÁRIOS
    # ============================================
    with tab1:
        st.subheader("👥 Usuários Cadastrados")
        
        # Carregar usuários
        try:
            resultado = _supabase.table('usuarios').select('*').order('nome').execute()
            
            if resultado.data:
                df_usuarios = pd.DataFrame(resultado.data)
                
                # Filtros
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    filtro_perfil = st.selectbox(
                        "Filtrar por Perfil",
                        ["Todos"] + list(PERFIS_PERMISSOES.keys())
                    )
                
                with col2:
                    filtro_status = st.selectbox(
                        "Filtrar por Status",
                        ["Todos", "Ativos", "Inativos"]
                    )
                
                with col3:
                    busca_usuario = st.text_input(
                        "🔍 Buscar usuário",
                        placeholder="Nome ou email..."
                    )
                
                # Aplicar filtros
                df_filtrado = df_usuarios.copy()
                
                if filtro_perfil != "Todos":
                    df_filtrado = df_filtrado[df_filtrado['perfil'] == filtro_perfil]
                
                if filtro_status == "Ativos":
                    df_filtrado = df_filtrado[df_filtrado['ativo'] == True]
                elif filtro_status == "Inativos":
                    df_filtrado = df_filtrado[df_filtrado['ativo'] == False]
                
                if busca_usuario:
                    mask = (
                        df_filtrado['nome'].str.contains(busca_usuario, case=False, na=False) |
                        df_filtrado['email'].str.contains(busca_usuario, case=False, na=False)
                    )
                    df_filtrado = df_filtrado[mask]
                
                st.info(f"📊 {len(df_filtrado)} usuário(s) encontrado(s)")
                
                # Exibir usuários em cards
                for idx, usuario in df_filtrado.iterrows():
                    with st.container():
                        col1, col2, col3, col4 = st.columns([3, 2, 1, 1])
                        
                        with col1:
                            status_icon = "✅" if usuario['ativo'] else "🚫"
                            perfil_info = PERFIS_PERMISSOES.get(usuario['perfil'], {})
                            perfil_cor = perfil_info.get('cor', '⚪')
                            
                            st.markdown(f"""
                            **{status_icon} {usuario['nome']}**  
                            📧 {usuario['email']}
                            """)
                        
                        with col2:
                            st.markdown(f"""
                            {perfil_cor} **{perfil_info.get('nome', usuario['perfil'])}**  
                            {perfil_info.get('descricao', '')}
                            """)
                        
                        with col3:
                            if usuario['ativo']:
                                if st.button("🚫 Desativar", key=f"desativar_{usuario['id']}"):
                                    _supabase.table('usuarios').update({'ativo': False}).eq('id', usuario['id']).execute()
                                    st.success("Usuário desativado!")
                                    st.rerun()
                            else:
                                if st.button("✅ Ativar", key=f"ativar_{usuario['id']}"):
                                    _supabase.table('usuarios').update({'ativo': True}).eq('id', usuario['id']).execute()
                                    st.success("Usuário ativado!")
                                    st.rerun()
                        
                        with col4:
                            if st.button("✏️ Editar", key=f"editar_{usuario['id']}"):
                                st.session_state.usuario_editar_id = usuario['id']
                                st.session_state.tab_usuarios = 2
                                st.rerun()
                        
                        st.markdown("---")
                
            else:
                st.warning("Nenhum usuário cadastrado")
                
        except Exception as e:
            st.error(f"Erro ao carregar usuários: {e}")
    
    # ============================================
    # TAB 2: NOVO USUÁRIO
    # ============================================
    with tab2:
        st.subheader("➕ Cadastrar Novo Usuário")
        
        with st.form("form_novo_usuario"):
            col1, col2 = st.columns(2)
            
            with col1:
                nome = st.text_input("Nome Completo *", max_chars=100)
                email = st.text_input("Email *", max_chars=100)
                perfil = st.selectbox(
                    "Perfil *",
                    options=list(PERFIS_PERMISSOES.keys()),
                    format_func=lambda x: f"{PERFIS_PERMISSOES[x]['cor']} {PERFIS_PERMISSOES[x]['nome']}"
                )
            
            with col2:
                senha = st.text_input("Senha *", type="password", max_chars=50)
                senha_confirmacao = st.text_input("Confirmar Senha *", type="password", max_chars=50)
                ativo = st.checkbox("Usuário Ativo", value=True)
            
            # Mostrar permissões do perfil selecionado
            st.markdown("---")
            st.markdown("### 🔐 Permissões deste Perfil")
            perfil_info = PERFIS_PERMISSOES[perfil]
            
            cols = st.columns(3)
            for idx, permissao in enumerate(perfil_info['permissoes']):
                with cols[idx % 3]:
                    st.markdown(f"✅ {permissao}")
            
            st.markdown("---")
            
            submitted = st.form_submit_button("🚀 Criar Usuário", use_container_width=True)
            
            if submitted:
                # Validações
                erros = []
                
                if not nome or not nome.strip():
                    erros.append("Nome é obrigatório")
                
                if not email or not email.strip():
                    erros.append("Email é obrigatório")
                elif '@' not in email:
                    erros.append("Email inválido")
                
                if not senha:
                    erros.append("Senha é obrigatória")
                elif len(senha) < 6:
                    erros.append("Senha deve ter no mínimo 6 caracteres")
                
                if senha != senha_confirmacao:
                    erros.append("Senhas não coincidem")
                
                if erros:
                    for erro in erros:
                        st.error(f"❌ {erro}")
                else:
                    try:
                        # Verificar se email já existe
                        verifica_email = _supabase.table('usuarios').select('id').eq('email', email.lower().strip()).execute()
                        
                        if verifica_email.data:
                            st.error("❌ Email já cadastrado!")
                        else:
                            # Criar usuário
                            novo_usuario = {
                                'nome': nome.strip(),
                                'email': email.lower().strip(),
                                'senha_hash': criar_senha_hash(senha),
                                'perfil': perfil,
                                'ativo': ativo
                            }
                            
                            resultado = _supabase.table('usuarios').insert(novo_usuario).execute()
                            
                            if resultado.data:
                                st.success("✅ Usuário criado com sucesso!")
                                
                                # Registrar na auditoria
                                ba.registrar_acao(
                                    st.session_state.usuario,
                                    "Criação de Usuário",
                                    {
                                        "usuario_criado": email,
                                        "perfil": perfil
                                    },
                                    _supabase
                                )
                                
                                st.balloons()
                                st.rerun()
                            else:
                                st.error("❌ Erro ao criar usuário")
                                
                    except Exception as e:
                        st.error(f"❌ Erro: {e}")
    
    # ============================================
    # TAB 3: EDITAR USUÁRIO
    # ============================================
    with tab3:
        st.subheader("✏️ Editar Usuário")
        
        # Carregar usuários para seleção
        try:
            resultado = _supabase.table('usuarios').select('*').order('nome').execute()
            
            if resultado.data:
                df_usuarios = pd.DataFrame(resultado.data)
                
                # Seletor de usuário
                usuario_id_selecionado = st.selectbox(
                    "Selecione o usuário para editar:",
                    options=df_usuarios['id'].tolist(),
                    format_func=lambda x: f"{df_usuarios[df_usuarios['id']==x]['nome'].values[0]} ({df_usuarios[df_usuarios['id']==x]['email'].values[0]})"
                )
                
                if usuario_id_selecionado:
                    usuario_atual = df_usuarios[df_usuarios['id'] == usuario_id_selecionado].iloc[0]
                    
                    st.markdown("---")
                    
                    with st.form("form_editar_usuario"):
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            nome_edit = st.text_input("Nome Completo *", value=usuario_atual['nome'], max_chars=100)
                            email_edit = st.text_input("Email *", value=usuario_atual['email'], max_chars=100)
                            perfil_edit = st.selectbox(
                                "Perfil *",
                                options=list(PERFIS_PERMISSOES.keys()),
                                index=list(PERFIS_PERMISSOES.keys()).index(usuario_atual['perfil']),
                                format_func=lambda x: f"{PERFIS_PERMISSOES[x]['cor']} {PERFIS_PERMISSOES[x]['nome']}"
                            )
                        
                        with col2:
                            ativo_edit = st.checkbox("Usuário Ativo", value=bool(usuario_atual['ativo']))
                            
                            st.markdown("**Alterar Senha** *(opcional)*")
                            nova_senha = st.text_input("Nova Senha", type="password", max_chars=50)
                            nova_senha_conf = st.text_input("Confirmar Nova Senha", type="password", max_chars=50)
                        
                        # Mostrar permissões
                        st.markdown("---")
                        st.markdown("### 🔐 Permissões deste Perfil")
                        perfil_info_edit = PERFIS_PERMISSOES[perfil_edit]
                        
                        cols = st.columns(3)
                        for idx, permissao in enumerate(perfil_info_edit['permissoes']):
                            with cols[idx % 3]:
                                st.markdown(f"✅ {permissao}")
                        
                        st.markdown("---")
                        
                        col_btn1, col_btn2 = st.columns(2)
                        
                        with col_btn1:
                            submitted_edit = st.form_submit_button("💾 Salvar Alterações", use_container_width=True)
                        
                        with col_btn2:
                            if st.form_submit_button("🗑️ Excluir Usuário", use_container_width=True):
                                st.session_state.confirmar_exclusao = usuario_id_selecionado
                        
                        if submitted_edit:
                            # Validações
                            erros = []
                            
                            if not nome_edit or not nome_edit.strip():
                                erros.append("Nome é obrigatório")
                            
                            if not email_edit or not email_edit.strip():
                                erros.append("Email é obrigatório")
                            elif '@' not in email_edit:
                                erros.append("Email inválido")
                            
                            if nova_senha:
                                if len(nova_senha) < 6:
                                    erros.append("Senha deve ter no mínimo 6 caracteres")
                                if nova_senha != nova_senha_conf:
                                    erros.append("Senhas não coincidem")
                            
                            if erros:
                                for erro in erros:
                                    st.error(f"❌ {erro}")
                            else:
                                try:
                                    # Atualizar dados
                                    dados_atualizacao = {
                                        'nome': nome_edit.strip(),
                                        'email': email_edit.lower().strip(),
                                        'perfil': perfil_edit,
                                        'ativo': ativo_edit
                                    }
                                    
                                    # Se houver nova senha
                                    if nova_senha:
                                        dados_atualizacao['senha_hash'] = criar_senha_hash(nova_senha)
                                    
                                    resultado = _supabase.table('usuarios').update(dados_atualizacao).eq('id', usuario_id_selecionado).execute()
                                    
                                    if resultado.data:
                                        st.success("✅ Usuário atualizado com sucesso!")
                                        
                                        # Registrar na auditoria
                                        ba.registrar_acao(
                                            st.session_state.usuario,
                                            "Atualização de Usuário",
                                            {
                                                "usuario_atualizado": email_edit,
                                                "alteracoes": dados_atualizacao
                                            },
                                            _supabase
                                        )
                                        
                                        st.rerun()
                                    else:
                                        st.error("❌ Erro ao atualizar usuário")
                                        
                                except Exception as e:
                                    st.error(f"❌ Erro: {e}")
                    
                    # Confirmação de exclusão
                    if st.session_state.get('confirmar_exclusao') == usuario_id_selecionado:
                        st.markdown("---")
                        st.warning("⚠️ **ATENÇÃO: Esta ação não pode ser desfeita!**")
                        
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            if st.button("✅ Sim, Excluir Permanentemente", type="primary"):
                                try:
                                    _supabase.table('usuarios').delete().eq('id', usuario_id_selecionado).execute()
                                    
                                    # Registrar na auditoria
                                    ba.registrar_acao(
                                        st.session_state.usuario,
                                        "Exclusão de Usuário",
                                        {
                                            "usuario_excluido": usuario_atual['email']
                                        },
                                        _supabase
                                    )
                                    
                                    st.success("✅ Usuário excluído!")
                                    del st.session_state.confirmar_exclusao
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"❌ Erro ao excluir: {e}")
                        
                        with col2:
                            if st.button("❌ Cancelar"):
                                del st.session_state.confirmar_exclusao
                                st.rerun()
            else:
                st.warning("Nenhum usuário cadastrado")
                
        except Exception as e:
            st.error(f"Erro ao carregar usuários: {e}")
    
    # ============================================
    # TAB 4: PERFIS E PERMISSÕES
    # ============================================
    with tab4:
        st.subheader("🔐 Perfis e Permissões do Sistema")
        
        st.info("""
        **Como funciona:**
        - Cada usuário possui um **perfil** que define suas permissões
        - As permissões controlam quais páginas/funcionalidades o usuário pode acessar
        - Apenas **Administradores** podem gerenciar usuários e acessar logs
        """)
        
        st.markdown("---")
        
        # Exibir cada perfil
        for perfil_key, perfil_data in PERFIS_PERMISSOES.items():
            with st.expander(f"{perfil_data['cor']} **{perfil_data['nome']}** - {perfil_data['descricao']}", expanded=True):
                st.markdown(f"**Código do perfil:** `{perfil_key}`")
                st.markdown("**Permissões:**")
                
                cols = st.columns(3)
                for idx, permissao in enumerate(perfil_data['permissoes']):
                    with cols[idx % 3]:
                        st.markdown(f"✅ {permissao}")
        
        st.markdown("---")
        
        # Estatísticas
        st.subheader("📊 Estatísticas de Usuários")
        
        try:
            resultado = _supabase.table('usuarios').select('perfil, ativo').execute()
            
            if resultado.data:
                df_stats = pd.DataFrame(resultado.data)
                
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    total_usuarios = len(df_stats)
                    st.metric("Total de Usuários", total_usuarios)
                
                with col2:
                    usuarios_ativos = df_stats['ativo'].sum()
                    st.metric("Usuários Ativos", usuarios_ativos)
                
                with col3:
                    usuarios_inativos = len(df_stats) - usuarios_ativos
                    st.metric("Usuários Inativos", usuarios_inativos)
                
                with col4:
                    admins = len(df_stats[df_stats['perfil'] == 'admin'])
                    st.metric("Administradores", admins)
                
                # Gráfico de distribuição por perfil
                st.markdown("---")
                st.markdown("### 📈 Distribuição por Perfil")
                
                perfil_counts = df_stats['perfil'].value_counts()
                
                fig = px.pie(
                    values=perfil_counts.values,
                    names=[PERFIS_PERMISSOES[p]['nome'] for p in perfil_counts.index],
                    title="Usuários por Perfil"
                )
                
                st.plotly_chart(fig, use_container_width=True)
                
        except Exception as e:
            st.error(f"Erro ao carregar estatísticas: {e}")

# ============================================
# ROTEAMENTO PRINCIPAL
# ============================================

