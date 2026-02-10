"""Tela: Gestão de pedidos."""
from __future__ import annotations

from datetime import datetime

import pandas as pd
import streamlit as st

import exportacao_relatorios as er
import filtros_avancados as fa
import backup_auditoria as ba

from src.repositories.pedidos import (
    carregar_pedidos,
    salvar_pedido,
    registrar_entrega,
)
from src.repositories.fornecedores import carregar_fornecedores
from src.utils.formatting import formatar_moeda_br, formatar_numero_br

def exibir_gestao_pedidos(_supabase):
    """Exibe página de gestão (criar/editar) pedidos - Apenas Admin"""
    
    if st.session_state.usuario['perfil'] != 'admin':
        st.error("⛔ Acesso negado. Apenas administradores podem gerenciar pedidos.")
        return
    
    st.title("✏️ Gestão de Pedidos")
    
    tab1, tab2, tab3 = st.tabs(["➕ Novo Pedido", "📤 Upload em Massa", "📝 Editar Pedido"])
    
    # ============================================
    # TAB 1: NOVO PEDIDO
    # ============================================
    with tab1:
        st.subheader("Cadastrar Novo Pedido")
        
        df_fornecedores = carregar_fornecedores(_supabase)
        
        with st.form("form_novo_pedido"):
            col1, col2 = st.columns(2)
            
            with col1:
                nr_solicitacao = st.text_input("N° Solicitação")
                nr_oc = st.text_input("N° Ordem de Compra")
                departamento = st.selectbox("Departamento", [
                    "Estoque", "Caminhões", "Oficina Geral", "Borracharia",
                    "Máquinas pesadas", "Veic. Leves", "Tratores", "Colhedoras",
                    "Irrigação", "Reboques", "Carregadeiras"
                ])
                cod_equipamento = st.text_input("Código Equipamento")
                cod_material = st.text_input("Código Material")
            
            with col2:
                descricao = st.text_area("Descrição do Material", height=100)
                qtde_solicitada = st.number_input("Quantidade Solicitada", min_value=0.0, step=1.0)
                
                if not df_fornecedores.empty:
                    fornecedor_opcoes = df_fornecedores.apply(
                        lambda x: f"{x['cod_fornecedor']} - {x['nome']}", axis=1
                    ).tolist()
                    fornecedor_selecionado = st.selectbox("Fornecedor", [""] + fornecedor_opcoes)
                else:
                    st.warning("⚠️ Nenhum fornecedor cadastrado")
                    fornecedor_selecionado = ""
            
            col3, col4 = st.columns(2)
            
            with col3:
                data_solicitacao = st.date_input("Data Solicitação", value=datetime.now())
                data_oc = st.date_input("Data OC")
                previsao_entrega = st.date_input("Previsão de Entrega")
            
            with col4:
                status = st.selectbox("Status", ["Sem OC", "Tem OC", "Em Transporte", "Entregue"])
                valor_total = st.number_input("Valor Total (R$)", min_value=0.0, step=0.01)
                observacoes = st.text_area("Observações")
            
            submitted = st.form_submit_button("💾 Salvar Pedido", use_container_width=True)
            
            if submitted:
                if not descricao:
                    st.error("⚠️ Descrição é obrigatória")
                elif qtde_solicitada <= 0:
                    st.error("⚠️ Quantidade deve ser maior que zero")
                else:
                    # Extrair ID do fornecedor
                    fornecedor_id = None
                    if fornecedor_selecionado and not df_fornecedores.empty:
                        cod_forn = int(fornecedor_selecionado.split(" - ")[0])
                        fornecedor_id = df_fornecedores[df_fornecedores['cod_fornecedor'] == cod_forn]['id'].values[0]
                    
                    pedido_data = {
                        "nr_solicitacao": nr_solicitacao or None,
                        "nr_oc": nr_oc or None,
                        "departamento": departamento,
                        "cod_equipamento": cod_equipamento or None,
                        "cod_material": cod_material or None,
                        "descricao": descricao,
                        "qtde_solicitada": qtde_solicitada,
                        "qtde_entregue": 0,
                        "data_solicitacao": data_solicitacao.isoformat(),
                        "data_oc": data_oc.isoformat() if data_oc else None,
                        "previsao_entrega": previsao_entrega.isoformat() if previsao_entrega else None,
                        "status": status,
                        "valor_total": valor_total,
                        "fornecedor_id": fornecedor_id,
                        "observacoes": observacoes or None
                    }
                    
                    sucesso, mensagem = salvar_pedido(pedido_data, _supabase)
                    if sucesso:
                        st.success(mensagem)
                        st.rerun()
                    else:
                        st.error(mensagem)
    
    # ============================================
    # TAB 2: UPLOAD EM MASSA
    # ============================================
    with tab2:
        st.subheader("📤 Importar Pedidos em Massa")
        
        st.info("""
        📋 **Instruções:**
        1. Baixe o template Excel abaixo
        2. Preencha com os dados dos pedidos
        3. Faça upload do arquivo preenchido
        4. Revise os dados antes de importar
        
        💡 **Dica:** Se o fornecedor não existir, o sistema pode criá-lo automaticamente!
        """)
        
        # Botão para baixar template
        template_data = {
            'nr_solicitacao': ['123456'],
            'nr_oc': ['OC-2024-001'],
            'departamento': ['Estoque'],
            'cod_equipamento': ['EQ-001'],
            'cod_material': ['MAT-001'],
            'descricao': ['Exemplo de material'],
            'qtde_solicitada': [10],
            'cod_fornecedor': [6691],
            'nome_fornecedor': ['Nome do Fornecedor (opcional)'],
            'cidade_fornecedor': ['São Paulo (opcional)'],
            'uf_fornecedor': ['SP (opcional)'],
            'data_solicitacao': ['2024-01-15'],
            'data_oc': ['2024-01-16'],
            'previsao_entrega': ['2024-02-15'],
            'status': ['Tem OC'],
            'valor_total': [1500.00]
        }
        
        df_template = pd.DataFrame(template_data)
        csv_template = df_template.to_csv(index=False, encoding='utf-8-sig', sep=';', decimal=',')
        
        st.download_button(
            label="📥 Baixar Template Excel",
            data=csv_template,
            file_name="template_importacao_pedidos.csv",
            mime="text/csv"
        )
        
        st.markdown("---")
        
        # Upload do arquivo
        arquivo_upload = st.file_uploader(
            "Selecione o arquivo Excel ou CSV",
            type=['xlsx', 'xls', 'csv'],
            help="Arquivo deve seguir o template fornecido"
        )
        
        if arquivo_upload:
            try:
                # Ler arquivo
                if arquivo_upload.name.endswith('.csv'):
                    # Tentar diferentes encodings e separadores
                    try:
                        df_upload = pd.read_csv(arquivo_upload, sep=';', decimal=',', encoding='utf-8-sig')
                    except:
                        try:
                            df_upload = pd.read_csv(arquivo_upload, encoding='utf-8-sig')
                        except:
                            df_upload = pd.read_csv(arquivo_upload, encoding='latin1')
                else:
                    df_upload = pd.read_excel(arquivo_upload)
                
                st.success(f"✅ Arquivo carregado: {len(df_upload)} registros encontrados")
                
                # Preview dos dados
                st.subheader("👀 Preview dos Dados")
                st.dataframe(df_upload.head(10), use_container_width=True)
                
                # Opções de importação
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    modo_importacao = st.radio(
                        "Modo de Importação",
                        ["Adicionar novos pedidos", "Atualizar pedidos existentes (por N° OC)"]
                    )
                
                with col2:
                    criar_fornecedores = st.checkbox(
                        "Criar fornecedores automaticamente se não existirem", 
                        value=True,
                        help="Se marcado, fornecedores não encontrados serão criados automaticamente"
                    )
                
                with col3:
                    limpar_antes = st.checkbox(
                        "🗑️ Limpar banco antes de importar",
                        value=False,
                        help="⚠️ ATENÇÃO: Remove todos os pedidos existentes antes da importação para evitar duplicidades"
                    )
                
                # Aviso sobre limpeza
                if limpar_antes:
                    st.warning("⚠️ **ATENÇÃO:** Todos os pedidos existentes serão **deletados** antes da importação. Esta ação não pode ser desfeita!")
                
                # Botão de importação
                if st.button("🚀 Importar Dados", type="primary", use_container_width=True):
                    with st.spinner("Processando importação..."):
                        # Limpeza do banco se solicitado
                        if limpar_antes:
                            try:
                                with st.spinner("🗑️ Limpando banco de dados..."):
                                    # Deletar todos os pedidos existentes
                                    resultado_limpeza = _supabase.table('pedidos').delete().neq('id', '00000000-0000-0000-0000-000000000000').execute()
                                    st.success(f"✅ Banco limpo com sucesso!")
                                    
                                    # Limpar cache para refletir mudanças
                                    st.cache_data.clear()
                            except Exception as e_limpeza:
                                st.error(f"❌ Erro ao limpar banco: {e_limpeza}")
                                st.stop()
                        
                        df_fornecedores = carregar_fornecedores(_supabase)
                        mapa_fornecedores = {int(f['cod_fornecedor']): f['id'] for _, f in df_fornecedores.iterrows()}
                        
                        registros_processados = 0
                        registros_inseridos = 0
                        registros_atualizados = 0
                        registros_erro = 0
                        fornecedores_criados = 0
                        erros = []
                        avisos = []
                        
                        for idx, row in df_upload.iterrows():
                            try:
                                # Validar e processar fornecedor
                                fornecedor_id = None
                                if 'cod_fornecedor' in row and pd.notna(row['cod_fornecedor']):
                                    cod_forn = int(row['cod_fornecedor'])
                                    
                                    # Verificar se fornecedor existe NO MAPA LOCAL
                                    if cod_forn not in mapa_fornecedores:
                                        # ✅ CORREÇÃO: Verificar no banco ANTES de tentar criar
                                        if criar_fornecedores:
                                            # PRIMEIRO: Buscar no banco para ter certeza que não existe
                                            try:
                                                busca_forn = _supabase.table('fornecedores').select('id').eq('cod_fornecedor', cod_forn).execute()
                                                
                                                if busca_forn.data and len(busca_forn.data) > 0:
                                                    # Fornecedor já existe no banco, apenas não estava no mapa
                                                    fornecedor_id = busca_forn.data[0]['id']
                                                    mapa_fornecedores[cod_forn] = fornecedor_id
                                                    avisos.append(f"Linha {idx + 2}: Fornecedor {cod_forn} já existia (adicionado ao cache)")
                                                else:
                                                    # Agora sim, criar novo fornecedor
                                                    novo_fornecedor = {
                                                        'cod_fornecedor': cod_forn,
                                                        'nome': str(row.get('nome_fornecedor', f'Fornecedor {cod_forn}')),
                                                        'cidade': str(row.get('cidade_fornecedor', 'Não informado')),
                                                        'uf': str(row.get('uf_fornecedor', 'SP'))[:2].upper(),
                                                        'ativo': True
                                                    }
                                                    
                                                    resultado_forn = _supabase.table('fornecedores').insert(novo_fornecedor).execute()
                                                    if resultado_forn.data:
                                                        fornecedor_id = resultado_forn.data[0]['id']
                                                        mapa_fornecedores[cod_forn] = fornecedor_id
                                                        fornecedores_criados += 1
                                                        avisos.append(f"Linha {idx + 2}: Fornecedor {cod_forn} criado automaticamente")
                                            
                                            except Exception as e_forn:
                                                # Se der erro de chave duplicada, tentar buscar novamente
                                                erro_str = str(e_forn)
                                                if 'duplicate key' in erro_str or '23505' in erro_str:
                                                    try:
                                                        busca_forn = _supabase.table('fornecedores').select('id').eq('cod_fornecedor', cod_forn).execute()
                                                        if busca_forn.data and len(busca_forn.data) > 0:
                                                            fornecedor_id = busca_forn.data[0]['id']
                                                            mapa_fornecedores[cod_forn] = fornecedor_id
                                                            avisos.append(f"Linha {idx + 2}: Fornecedor {cod_forn} recuperado após conflito")
                                                        else:
                                                            raise ValueError(f"Erro ao criar fornecedor {cod_forn}: {erro_str}")
                                                    except:
                                                        raise ValueError(f"Erro ao criar fornecedor {cod_forn}: {erro_str}")
                                                else:
                                                    raise ValueError(f"Erro ao criar fornecedor {cod_forn}: {erro_str}")
                                        else:
                                            raise ValueError(f"Fornecedor {cod_forn} não encontrado. Ative a opção 'Criar fornecedores automaticamente'")
                                    else:
                                        fornecedor_id = mapa_fornecedores[cod_forn]
                                
                                # ✅ VALIDAÇÃO: Campos obrigatórios
                                if not row.get('descricao') or pd.isna(row.get('descricao')):
                                    raise ValueError("Campo 'descricao' é obrigatório e não pode estar vazio")
                                
                                if not row.get('qtde_solicitada') or pd.isna(row.get('qtde_solicitada')):
                                    raise ValueError("Campo 'qtde_solicitada' é obrigatório e não pode estar vazio")
                                
                                # ✅ CORREÇÃO: Criar dicionário apenas com valores válidos (sem None em strings)
                                pedido_data = {
                                    "nr_solicitacao": str(row['nr_solicitacao']).strip() if pd.notna(row.get('nr_solicitacao')) and str(row.get('nr_solicitacao')).strip() else None,
                                    "nr_oc": str(row['nr_oc']).strip() if pd.notna(row.get('nr_oc')) and str(row.get('nr_oc')).strip() else None,
                                    "departamento": str(row['departamento']).strip() if pd.notna(row.get('departamento')) and str(row.get('departamento')).strip() else None,
                                    "cod_equipamento": str(row['cod_equipamento']).strip() if pd.notna(row.get('cod_equipamento')) and str(row.get('cod_equipamento')).strip() else None,
                                    "cod_material": str(row['cod_material']).strip() if pd.notna(row.get('cod_material')) and str(row.get('cod_material')).strip() else None,
                                    "descricao": str(row['descricao']).strip(),
                                    "qtde_solicitada": float(row['qtde_solicitada']),
                                    "qtde_entregue": float(row.get('qtde_entregue', 0)),
                                    "data_solicitacao": pd.to_datetime(row['data_solicitacao']).strftime('%Y-%m-%d') if pd.notna(row.get('data_solicitacao')) else None,
                                    "data_oc": pd.to_datetime(row['data_oc']).strftime('%Y-%m-%d') if pd.notna(row.get('data_oc')) else None,
                                    "previsao_entrega": pd.to_datetime(row['previsao_entrega']).strftime('%Y-%m-%d') if pd.notna(row.get('previsao_entrega')) else None,
                                    "status": str(row.get('status', 'Sem OC')).strip(),
                                    "valor_total": float(row.get('valor_total', 0)),
                                    "fornecedor_id": fornecedor_id
                                }
                                
                                # ✅ LIMPEZA: Remover campos None que causam erro "empty json"
                                pedido_data = {k: v for k, v in pedido_data.items() if v is not None or k in ['qtde_entregue', 'valor_total']}
                                
                                if modo_importacao == "Atualizar pedidos existentes (por N° OC)" and pedido_data['nr_oc']:
                                    # Verificar se pedido existe
                                    pedido_existente = _supabase.table('pedidos').select('id').eq('nr_oc', pedido_data['nr_oc']).execute()
                                    
                                    if pedido_existente.data:
                                        # Atualizar pedido existente
                                        resultado = _supabase.table('pedidos').update(pedido_data).eq('nr_oc', pedido_data['nr_oc']).execute()
                                        registros_atualizados += 1
                                    else:
                                        # Criar novo pedido se não existir
                                        pedido_data['criado_por'] = st.session_state.usuario['id']
                                        _supabase.table('pedidos').insert(pedido_data).execute()
                                        registros_inseridos += 1
                                else:
                                    # Inserir novo pedido
                                    pedido_data['criado_por'] = st.session_state.usuario['id']
                                    _supabase.table('pedidos').insert(pedido_data).execute()
                                    registros_inseridos += 1
                                
                                registros_processados += 1
                                
                            except Exception as e:
                                registros_erro += 1
                                erros.append(f"Linha {idx + 2}: {str(e)}")
                        
                        # Limpar cache
                        st.cache_data.clear()
                        
                        # Exibir resultado
                        if registros_erro == 0:
                            st.success(f"""
                            ✅ **Importação Concluída com Sucesso!**
                            - ✅ Processados: {registros_processados}
                            - ➕ Inseridos: {registros_inseridos}
                            - 🔄 Atualizados: {registros_atualizados}
                            - 🏭 Fornecedores criados: {fornecedores_criados}
                            """)
                        else:
                            st.warning(f"""
                            ⚠️ **Importação Concluída com Erros**
                            - ✅ Processados: {registros_processados}
                            - ➕ Inseridos: {registros_inseridos}
                            - 🔄 Atualizados: {registros_atualizados}
                            - 🏭 Fornecedores criados: {fornecedores_criados}
                            - ❌ Erros: {registros_erro}
                            """)
                        
                        if avisos:
                            with st.expander(f"ℹ️ Ver avisos ({len(avisos)})"):
                                for aviso in avisos[:50]:
                                    st.info(aviso)
                        
                        if erros:
                            with st.expander(f"⚠️ Ver erros ({len(erros)})"):
                                for erro in erros[:50]:
                                    st.error(erro)
                                
                                if len(erros) > 50:
                                    st.warning(f"... e mais {len(erros) - 50} erros não exibidos")
                        
                        # Registrar no log
                        try:
                            _supabase.table('log_importacoes').insert({
                                'usuario_id': st.session_state.usuario['id'],
                                'nome_arquivo': arquivo_upload.name,
                                'registros_processados': registros_processados,
                                'registros_inseridos': registros_inseridos,
                                'registros_atualizados': registros_atualizados,
                                'registros_erro': registros_erro,
                                'detalhes_erro': '\n'.join(erros[:100]) if erros else None
                            }).execute()
                        except:
                            pass  # Se tabela de log não existir, continuar
                
            except Exception as e:
                st.error(f"❌ Erro ao processar arquivo: {e}")
                st.info("💡 Verifique se o arquivo está no formato correto e contém todas as colunas necessárias")

    
    # ============================================
    # TAB 3: EDITAR PEDIDO
    # ============================================
    with tab3:
        st.subheader("Editar Pedido Existente")
        
        df_pedidos = carregar_pedidos(_supabase)
        
        if not df_pedidos.empty:
            pedido_editar = st.selectbox(
                "Selecione o pedido para editar",
                options=df_pedidos['id'].tolist(),
                format_func=lambda x: f"OC: {df_pedidos[df_pedidos['id']==x]['nr_oc'].values[0]} - {df_pedidos[df_pedidos['id']==x]['descricao'].values[0][:50]}"
            )
            
            if pedido_editar:
                pedido_atual = df_pedidos[df_pedidos['id'] == pedido_editar].iloc[0]
                
                st.markdown("---")
                
                # Formulário de edição
                with st.form("form_editar_pedido"):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.text_input("N° Solicitação", value=pedido_atual['nr_solicitacao'] or "", key="edit_nr_sol")
                        st.text_input("N° OC", value=pedido_atual['nr_oc'] or "", key="edit_nr_oc")
                        st.text_input("Departamento", value=pedido_atual['departamento'] or "", key="edit_dept")
                        st.text_area("Descrição", value=pedido_atual['descricao'], key="edit_desc")
                    
                    with col2:
                        st.number_input("Qtd. Solicitada", value=float(pedido_atual['qtde_solicitada']), key="edit_qtd_sol")
                        st.number_input("Qtd. Entregue", value=float(pedido_atual['qtde_entregue']), key="edit_qtd_ent")
                        st.selectbox("Status", ["Sem OC", "Tem OC", "Em Transporte", "Entregue"], 
                                    index=["Sem OC", "Tem OC", "Em Transporte", "Entregue"].index(pedido_atual['status']) if pedido_atual['status'] in ["Sem OC", "Tem OC", "Em Transporte", "Entregue"] else 0,
                                    key="edit_status")
                        st.number_input("Valor Total", value=float(pedido_atual['valor_total'] or 0), key="edit_valor")
                    
                    submitted_edit = st.form_submit_button("💾 Salvar Alterações", use_container_width=True)
                    
                    if submitted_edit:
                        pedido_atualizado = {
                            "id": pedido_editar,
                            "nr_solicitacao": st.session_state.edit_nr_sol or None,
                            "nr_oc": st.session_state.edit_nr_oc or None,
                            "departamento": st.session_state.edit_dept,
                            "descricao": st.session_state.edit_desc,
                            "qtde_solicitada": st.session_state.edit_qtd_sol,
                            "qtde_entregue": st.session_state.edit_qtd_ent,
                            "status": st.session_state.edit_status,
                            "valor_total": st.session_state.edit_valor
                        }
                        
                        sucesso, mensagem = salvar_pedido(pedido_atualizado, _supabase)
                        if sucesso:
                            st.success(mensagem)
                            st.rerun()
                        else:
                            st.error(mensagem)
                
                # Seção de registro de entregas
                st.markdown("---")
                st.subheader("📦 Registrar Entrega")
                
                qtde_pendente = pedido_atual['qtde_pendente']
                
                if qtde_pendente > 0:
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        qtde_entrega = st.number_input(
                            f"Quantidade entregue (Pendente: {qtde_pendente})",
                            min_value=0.0,
                            max_value=float(qtde_pendente),
                            step=1.0
                        )
                        data_entrega = st.date_input("Data da entrega", value=datetime.now())
                    
                    with col2:
                        obs_entrega = st.text_area("Observações da entrega")
                    
                    if st.button("✅ Registrar Entrega", type="primary"):
                        if qtde_entrega > 0:
                            sucesso, mensagem = registrar_entrega(
                                pedido_editar,
                                qtde_entrega,
                                data_entrega.isoformat(),
                                obs_entrega,
                                _supabase=_supabase,
                            )
                            
                            if sucesso:
                                st.success(mensagem)
                                st.rerun()
                            else:
                                st.error(mensagem)
                        else:
                            st.warning("⚠️ Informe a quantidade entregue")
                else:
                    st.success("✅ Pedido totalmente entregue!")
        else:
            st.info("📭 Nenhum pedido cadastrado ainda")

# ============================================
# PÁGINA DE FICHA TÉCNICA DO MATERIAL (NOVA)
# ============================================

