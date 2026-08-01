import streamlit as st
import pandas as pd
import time
import hashlib
import calendar
from datetime import datetime, date
import re
import io
from streamlit_gsheets import GSheetsConnection

# --- CONFIGURAÇÕES INICIAIS ---
st.set_page_config(page_title="Sistema Mercadinho", layout="wide")

# Lista Padrão Inicial (Caso a planilha esteja vazia)
CATEGORIAS_PADRAO = [
    "Mercadoria", "Frete", "Energia", "Comissão", "Manutenção", "Combustível",
    "Salário", "13° Salário", "Férias", "Simples Nacional", "INSS", "FGTS",
    "Internet", "Celular", "Locação", "Tarifa Bancária",
    "Integralização de Capital em Banco", "Cesta de Relacionamento de Banco",
    "Cartão de Crédito", "Empréstimo", "Consórcio", "Sistemas", 
    "Vale Alimentação", "Mão de obra", "Outros", "Vendas"
]

# Dicionário de Meses
MESES_PT = {
    1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril", 5: "Maio", 6: "Junho",
    7: "Julho", 8: "Agosto", 9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro"
}
MESES_PT_INV = {v: k for k, v in MESES_PT.items()}

# --- CONEXÃO COM O GOOGLE SHEETS ---
conn = st.connection("gsheets", type=GSheetsConnection)

# --- FUNÇÕES DE DADOS COM CACHE ATIVADO ---
def carregar_dados():
    try:
        df = conn.read(worksheet="lancamentos", ttl=600)
        return df
    except Exception as e:
        st.error(f"Erro de conexão com o banco de dados (Lançamentos): {e}")
        return pd.DataFrame()

# === FUNÇÕES DE FORNECEDORES ===
def carregar_fornecedores_df():
    try:
        df = conn.read(worksheet="fornecedores", ttl=600)
        # Adicionado o campo 'categoria_padrao'
        colunas_necessarias = ['nome', 'cnpj', 'telefone', 'login_app', 'senha_app', 'categoria_padrao']
        for col in colunas_necessarias:
            if col not in df.columns:
                df[col] = pd.Series(dtype='str')
        df = df.fillna("")
        df = df.astype(str)
        return df
    except Exception as e:
        return pd.DataFrame(columns=['nome', 'cnpj', 'telefone', 'login_app', 'senha_app', 'categoria_padrao'])

def carregar_lista_nomes_fornecedores():
    df = carregar_fornecedores_df()
    return df['nome'].dropna().unique().tolist()

def obter_dict_forn_cat():
    """Retorna um dicionário vinculando fornecedor à sua categoria padrão"""
    df_f = carregar_fornecedores_df()
    d = {}
    if not df_f.empty and 'categoria_padrao' in df_f.columns:
        for _, r in df_f.iterrows():
            fn = str(r['nome']).strip()
            fc = str(r.get('categoria_padrao', '')).strip()
            if fn and fc and fc != 'nan':
                d[fn] = fc
    return d

def salvar_fornecedor_rapido(novo_nome):
    try:
        df = conn.read(worksheet="fornecedores", ttl=0)
        if novo_nome and novo_nome.strip().lower() not in df['nome'].dropna().str.lower().values:
            novo_registro = pd.DataFrame([{"nome": novo_nome, "cnpj": "", "telefone": "", "login_app": "", "senha_app": "", "categoria_padrao": ""}])
            df_atualizado = pd.concat([df, novo_registro], ignore_index=True)
            conn.update(worksheet="fornecedores", data=df_atualizado)
    except:
        novo_registro = pd.DataFrame([{"nome": novo_nome, "cnpj": "", "telefone": "", "login_app": "", "senha_app": "", "categoria_padrao": ""}])
        conn.update(worksheet="fornecedores", data=novo_registro)

def salvar_tabela_fornecedores(df_editado):
    conn.update(worksheet="fornecedores", data=df_editado)

# === FUNÇÕES DE CATEGORIAS ===
def carregar_categorias_df():
    try:
        df = conn.read(worksheet="categorias", ttl=600)
        if 'nome' not in df.columns:
            df['nome'] = pd.Series(dtype='str')
        df = df.fillna("")
        df = df.astype(str)
        return df
    except Exception as e:
        return pd.DataFrame({'nome': CATEGORIAS_PADRAO})

def carregar_lista_categorias():
    df = carregar_categorias_df()
    lista = df['nome'].dropna().unique().tolist()
    if not lista:
        return CATEGORIAS_PADRAO
    return lista

def salvar_categoria_rapida(nova_categoria):
    try:
        df = conn.read(worksheet="categorias", ttl=0)
        if 'nome' not in df.columns:
             df = pd.DataFrame({'nome': CATEGORIAS_PADRAO})

        if nova_categoria and nova_categoria.strip().lower() not in df['nome'].dropna().str.lower().values:
            novo_registro = pd.DataFrame([{"nome": nova_categoria}])
            df_atualizado = pd.concat([df, novo_registro], ignore_index=True)
            conn.update(worksheet="categorias", data=df_atualizado)
    except Exception as e:
        novo_registro = pd.DataFrame([{"nome": nova_categoria}])
        conn.update(worksheet="categorias", data=novo_registro)

def salvar_tabela_categorias(df_editado):
    conn.update(worksheet="categorias", data=df_editado)

# === FUNÇÕES DE LANÇAMENTOS ===
def salvar_lancamento(dados):
    try:
        df = conn.read(worksheet="lancamentos", ttl=0)
        novo_df = pd.DataFrame([dados])
        df_atualizado = pd.concat([df, novo_df], ignore_index=True)
        conn.update(worksheet="lancamentos", data=df_atualizado)
    except:
        novo_df = pd.DataFrame([dados])
        conn.update(worksheet="lancamentos", data=novo_df)

def salvar_lote_lancamentos(df_novos):
    try:
        df = conn.read(worksheet="lancamentos", ttl=0)
        df_atualizado = pd.concat([df, df_novos], ignore_index=True)
        conn.update(worksheet="lancamentos", data=df_atualizado)
    except:
        conn.update(worksheet="lancamentos", data=df_novos)

def excluir_lancamentos(indices_para_excluir):
    try:
        df = conn.read(worksheet="lancamentos", ttl=0)
        df_atualizado = df.drop(indices_para_excluir).reset_index(drop=True)
        conn.update(worksheet="lancamentos", data=df_atualizado)
    except Exception as e:
        st.error(f"Erro ao excluir: {e}")

def editar_lancamento(indice, novos_dados):
    try:
        df = conn.read(worksheet="lancamentos", ttl=0)
        for chave, valor in novos_dados.items():
            df.at[indice, chave] = valor
        conn.update(worksheet="lancamentos", data=df)
    except Exception as e:
        st.error(f"Erro ao editar: {e}")

def editar_multiplos_lancamentos(atualizacoes_dict):
    try:
        df = conn.read(worksheet="lancamentos", ttl=0)
        for indice, novos_dados in atualizacoes_dict.items():
            for chave, valor in novos_dados.items():
                df.at[indice, chave] = valor
        conn.update(worksheet="lancamentos", data=df)
    except Exception as e:
        st.error(f"Erro ao salvar as edições: {e}")

# --- FUNÇÕES AUXILIARES ---
def gerar_lista_anos():
    ano_atual = datetime.now().year
    return [str(ano) for ano in range(2025, ano_atual + 3)]

def converter_moeda_br_para_float(valor_str):
    if not valor_str: return 0.0
    if isinstance(valor_str, (int, float)): return float(valor_str)
    limpo = str(valor_str).replace("R$", "").replace(" ", "").replace(".", "").replace(",", ".")
    try:
        return float(limpo)
    except ValueError:
        return 0.0

def formatar_input_br(key):
    valor_digitado = st.session_state[key]
    if not valor_digitado: return
    try:
        limpo = valor_digitado.replace("R$", "").strip()
        if "," in limpo and "." in limpo: limpo = limpo.replace(".", "").replace(",", ".")
        elif "," in limpo: limpo = limpo.replace(",", ".")
        valor_float = float(limpo)
        formatado = "{:,.2f}".format(valor_float).replace(",", "X").replace(".", ",").replace("X", ".")
        st.session_state[key] = formatado
    except: pass

def atualizar_data_liq():
    if st.session_state.get("check_repetir_data") and "memoria_data_liq" in st.session_state:
        st.session_state["data_liq_desp"] = st.session_state["memoria_data_liq"]

def auto_preencher_cat_individual():
    """Preenche a categoria automaticamente no Lançamento Individual se houver vínculo."""
    d = obter_dict_forn_cat()
    f = st.session_state.get("sel_forn")
    if f and f in d:
        c = d[f]
        cats = carregar_lista_categorias()
        if c in cats:
            st.session_state["cat_desp"] = c

# --- FUNÇÕES DE AUTENTICAÇÃO E LOGIN ---
def gerar_token_auth():
    email_secreto = st.secrets["login"]["email"]
    senha_secreta = st.secrets["login"]["senha"]
    texto_base = email_secreto + senha_secreta + "mercadinho_seguro_2026"
    return hashlib.sha256(texto_base.encode()).hexdigest()

def check_password():
    token_esperado = gerar_token_auth()
    if st.session_state.get("password_correct", False):
        return True
    if st.query_params.get("auth") == token_esperado:
        st.session_state["password_correct"] = True
        return True

    st.markdown("## 🔐 Acesso Restrito")
    col1, col2 = st.columns([1, 2])
    with col1:
        email = st.text_input("E-mail")
        password = st.text_input("Senha", type="password")
        if st.button("Entrar"):
            user_email = st.secrets["login"]["email"]
            user_pass = st.secrets["login"]["senha"]
            if email == user_email and password == user_pass:
                st.session_state["password_correct"] = True
                st.query_params["auth"] = token_esperado
                st.rerun()
            else:
                st.error("Dados incorretos.")
    return False

# --- INTERFACE PRINCIPAL ---
if check_password():
    st.sidebar.title("Menu")
    menu = st.sidebar.radio("Navegar", ["Lançar Despesa", "Lançar Receita", "Relatórios", "Conciliação Bancária", "Configurações"])

    # --- ABA: LANÇAR DESPESA ---
    if menu == "Lançar Despesa":
        st.header("📉 Gestão de Despesas")
        tab_individual, tab_lote, tab_importar, tab_editar_excluir = st.tabs([
            "📝 Individual", 
            "📚 Despesa em Lote", 
            "📥 Importar Planilha", 
            "✏️ Editar ou Excluir"
        ])

        # === 1. LANÇAMENTO INDIVIDUAL ===
        with tab_individual:
            if "limpar_despesa_agora" in st.session_state:
                st.session_state["val_desp"] = ""
                st.session_state["obs_desp"] = ""
                st.session_state["sel_forn"] = None
                st.session_state["txt_novo_forn"] = ""
                st.session_state["check_novo_forn"] = False
                
                if st.session_state.get("check_repetir_data", False) and "memoria_data_liq" in st.session_state:
                    st.session_state["data_liq_desp"] = st.session_state["memoria_data_liq"]
                else:
                    st.session_state["data_liq_desp"] = None

                if not st.session_state.get("check_repetir_comp", False):
                    if "sel_mes_comp" in st.session_state: del st.session_state["sel_mes_comp"]
                    if "sel_ano_comp" in st.session_state: del st.session_state["sel_ano_comp"]
                
                if "status_desp" in st.session_state: del st.session_state["status_desp"]
                if "cat_desp" in st.session_state: del st.session_state["cat_desp"]
                del st.session_state["limpar_despesa_agora"]

            idx_mes, idx_ano = None, None
            lista_anos = gerar_lista_anos()

            usar_anterior_comp = st.session_state.get("check_repetir_comp", False)
            if usar_anterior_comp and "memoria_mes" in st.session_state:
                st.session_state["sel_mes_comp"] = st.session_state["memoria_mes"]
                st.session_state["sel_ano_comp"] = st.session_state["memoria_ano"]
                try:
                    if st.session_state["memoria_mes"] in list(MESES_PT.values()):
                        idx_mes = list(MESES_PT.values()).index(st.session_state["memoria_mes"])
                    if st.session_state["memoria_ano"] in lista_anos:
                        idx_ano = lista_anos.index(st.session_state["memoria_ano"])
                except: pass

            col1, col2 = st.columns(2)
            with col1:
                valor_str = st.text_input("Valor Total (R$)", value="", key="val_desp", help="Digite o valor (ex: 150,00).", on_change=formatar_input_br, args=("val_desp",))
                data_liq = st.date_input("Data de Liquidação (Pagamento)", value=None, format="DD/MM/YYYY", key="data_liq_desp")
                st.checkbox("Mesma data de liquidação da despesa anterior", key="check_repetir_data", disabled="memoria_data_liq" not in st.session_state, on_change=atualizar_data_liq)
                st.markdown("---") 
                c_mes, c_ano = st.columns(2)
                with c_mes: mes_selecionado = st.selectbox("Mês de Competência", list(MESES_PT.values()), index=idx_mes, placeholder="Selecione o Mês", key="sel_mes_comp")
                with c_ano: ano_selecionado = st.selectbox("Ano de Competência", lista_anos, index=idx_ano, placeholder="Selecione o Ano", key="sel_ano_comp")
                st.checkbox("Mesmo ano e mês de competência da despesa salva anteriormente?", key="check_repetir_comp", disabled="memoria_mes" not in st.session_state) 
                status = st.selectbox("Status", ["Pago", "A Pagar"], index=None, placeholder="Selecione o Status", key="status_desp")
            
            with col2:
                lista_fornecedores = carregar_lista_nomes_fornecedores()
                usar_novo_fornecedor = st.checkbox("Cadastrar Novo Fornecedor?", key="check_novo_forn")
                if usar_novo_fornecedor: 
                    fornecedor = st.text_input("Digite o nome do novo fornecedor", key="txt_novo_forn")
                else: 
                    fornecedor = st.selectbox("Selecione o Fornecedor", [""] + lista_fornecedores, index=None, placeholder="Selecione o Fornecedor", key="sel_forn", on_change=auto_preencher_cat_individual)
                
                lista_categorias = carregar_lista_categorias()
                categoria = st.selectbox("Classificação", lista_categorias, index=None, placeholder="Selecione a Categoria", key="cat_desp")
                obs = st.text_area("Observação", key="obs_desp")

            st.markdown("---")
            if st.button("💾 Salvar Despesa", type="primary", use_container_width=True):
                erro_campos = []
                if not valor_str: erro_campos.append("Valor Total")
                if not data_liq: erro_campos.append("Data de Liquidação")
                if not mes_selecionado: erro_campos.append("Mês de Competência")
                if not ano_selecionado: erro_campos.append("Ano de Competência")
                if not status: erro_campos.append("Status")
                if not categoria: erro_campos.append("Classificação")
                if not fornecedor: erro_campos.append("Fornecedor")

                if erro_campos:
                    st.warning(f"⚠️ Por favor, preencha os seguintes campos antes de salvar: {', '.join(erro_campos)}")
                else:
                    valor_float = converter_moeda_br_para_float(valor_str)
                    if usar_novo_fornecedor: salvar_fornecedor_rapido(fornecedor)
                    mes_num = MESES_PT_INV[mes_selecionado]
                    competencia_formatada = f"{ano_selecionado}-{mes_num:02d}"
                    dados = {
                        "data_registro": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "tipo": "Despesa",
                        "valor": valor_float,
                        "fornecedor": fornecedor,
                        "data_liquidacao": data_liq.strftime("%Y-%m-%d"),
                        "competencia": competencia_formatada,
                        "status": status,
                        "categoria": categoria,
                        "observacao": obs
                    }
                    salvar_lancamento(dados)
                    st.success("Despesa registrada com sucesso! A tela será limpa em 3 segundos...")
                    time.sleep(3) 
                    st.session_state["memoria_mes"] = mes_selecionado
                    st.session_state["memoria_ano"] = ano_selecionado
                    st.session_state["memoria_data_liq"] = data_liq
                    st.session_state["limpar_despesa_agora"] = True
                    st.cache_data.clear()
                    st.rerun()

        # === 2. LANÇAMENTO EM LOTE ===
        with tab_lote:
            st.info("💡 **Dica de Produtividade:** Ao selecionar um fornecedor, o sistema preencherá a Classificação automaticamente se houver um padrão configurado (Ajuste isso no menu Configurações).")
            
            with st.expander("➕ O Fornecedor não está na lista? Cadastre aqui."):
                c_fn1, c_fn2 = st.columns([3, 1])
                with c_fn1:
                    novo_forn_lote = st.text_input("Digite o nome do novo Fornecedor", key="novo_forn_lote")
                with c_fn2:
                    st.markdown("<div style='margin-top: 28px;'></div>", unsafe_allow_html=True)
                    if st.button("Cadastrar Fornecedor", key="btn_novo_forn_lote", use_container_width=True):
                        if novo_forn_lote.strip():
                            salvar_fornecedor_rapido(novo_forn_lote)
                            st.success(f"Fornecedor '{novo_forn_lote}' cadastrado com sucesso!")
                            time.sleep(1)
                            st.cache_data.clear() 
                            st.rerun() 
                        else:
                            st.error("Digite um nome válido.")
            
            with st.expander("➕ A Classificação não está na lista? Cadastre aqui."):
                c_cat1, c_cat2 = st.columns([3, 1])
                with c_cat1:
                    nova_cat_lote = st.text_input("Digite o nome da nova Classificação", key="nova_cat_lote")
                with c_cat2:
                    st.markdown("<div style='margin-top: 28px;'></div>", unsafe_allow_html=True)
                    if st.button("Cadastrar Classificação", key="btn_nova_cat_lote", use_container_width=True):
                        if nova_cat_lote.strip():
                            salvar_categoria_rapida(nova_cat_lote)
                            st.success(f"Classificação '{nova_cat_lote}' cadastrada com sucesso!")
                            time.sleep(1)
                            st.cache_data.clear()
                            st.rerun()
                        else:
                            st.error("Digite um nome válido.")

            lista_anos = gerar_lista_anos()
            lista_fornecedores_cadastrados = carregar_lista_nomes_fornecedores()
            lista_categorias_cadastradas = carregar_lista_categorias()
            d_forn_cat = obter_dict_forn_cat()
            
            # Gerenciamento de Estado da Planilha para Auto-preenchimento
            if "df_lote" not in st.session_state:
                linhas_iniciais = [{
                    "valor": None, "data_liquidacao": None, "mes_competencia": None, "ano_competencia": None,
                    "fornecedor": None, "categoria": None, "observacao": "", "status": None
                } for _ in range(10)]
                st.session_state.df_lote = pd.DataFrame(linhas_iniciais)

            lote_editado = st.data_editor(
                st.session_state.df_lote,
                key="editor_lote",
                num_rows="dynamic",
                use_container_width=True,
                column_config={
                    "valor": st.column_config.NumberColumn("Valor (R$)", min_value=0.0, format="R$ %.2f", required=True),
                    "data_liquidacao": st.column_config.DateColumn("Data Pagamento", format="DD/MM/YYYY", required=True),
                    "mes_competencia": st.column_config.SelectboxColumn("Mês Comp.", options=list(MESES_PT.values()), required=True),
                    "ano_competencia": st.column_config.SelectboxColumn("Ano Comp.", options=lista_anos, required=True),
                    "fornecedor": st.column_config.SelectboxColumn("Fornecedor (Selecione)", options=lista_fornecedores_cadastrados, required=True),
                    "categoria": st.column_config.SelectboxColumn("Classificação (Selecione)", options=lista_categorias_cadastradas, required=True),
                    "observacao": st.column_config.TextColumn("Observação"),
                    "status": st.column_config.SelectboxColumn("Status", options=["Pago", "A Pagar"])
                },
                hide_index=True
            )

            # --- LÓGICA DE AUTO-PREENCHIMENTO DE CATEGORIA ---
            mudou_lote = False
            df_verificacao = lote_editado.copy()
            
            for idx, row in df_verificacao.iterrows():
                f = str(row['fornecedor']).strip() if pd.notna(row['fornecedor']) else ""
                c = str(row['categoria']).strip() if pd.notna(row['categoria']) else ""
                
                # Se tem fornecedor, mas não tem categoria, aplica a sugestão padrão
                if f and not c:
                    cat_sug = d_forn_cat.get(f, "")
                    if cat_sug and cat_sug in lista_categorias_cadastradas:
                        df_verificacao.at[idx, 'categoria'] = cat_sug
                        mudou_lote = True

            # Se houve alguma alteração automática, nós resetamos o editor para mostrar o preenchimento
            if mudou_lote:
                st.session_state.df_lote = df_verificacao
                if "editor_lote" in st.session_state:
                    del st.session_state["editor_lote"]
                st.rerun()

            if st.button("💾 Salvar Lote de Despesas"):
                if lote_editado.empty:
                    st.warning("A tabela está vazia.")
                else:
                    lista_dados_finais = []
                    erro_encontrado = False
                    for index, row in lote_editado.iterrows():
                        if pd.isna(row['fornecedor']) and pd.isna(row['valor']): continue
                        
                        if pd.isna(row['fornecedor']) or str(row['fornecedor']).strip() == "" or pd.isna(row['valor']) or pd.isna(row['data_liquidacao']) or not row['mes_competencia'] or not row['ano_competencia']:
                            st.warning(f"Linha {index + 1} incompleta. Verifique Valor, Data, Competência e Fornecedor.")
                            erro_encontrado = True
                            continue
                            
                        if pd.isna(row['categoria']) or str(row['categoria']).strip() == "":
                            st.warning(f"Linha {index + 1} incompleta. Verifique a Classificação.")
                            erro_encontrado = True
                            continue
                            
                        nome_forn = str(row['fornecedor']).strip()
                        nome_cat = str(row['categoria']).strip()
                        mes_num = MESES_PT_INV[row['mes_competencia']]
                        comp_fmt = f"{row['ano_competencia']}-{mes_num:02d}"
                        
                        dados_linha = {
                            "data_registro": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            "tipo": "Despesa",
                            "valor": row['valor'],
                            "fornecedor": nome_forn,
                            "data_liquidacao": pd.to_datetime(row['data_liquidacao']).strftime("%Y-%m-%d"),
                            "competencia": comp_fmt,
                            "status": row['status'] if row['status'] else "Pago",
                            "categoria": nome_cat,
                            "observacao": row['observacao']
                        }
                        lista_dados_finais.append(dados_linha)
                        
                    if lista_dados_finais and not erro_encontrado:
                        salvar_lote_lancamentos(pd.DataFrame(lista_dados_finais))
                        st.success(f"{len(lista_dados_finais)} despesas salvas com sucesso!")
                        # Limpando o formulário para a próxima vez
                        if "df_lote" in st.session_state:
                            del st.session_state["df_lote"]
                        if "editor_lote" in st.session_state:
                            del st.session_state["editor_lote"]
                        time.sleep(2)
                        st.cache_data.clear()
                        st.rerun()
                    elif not lista_dados_finais and not erro_encontrado:
                        st.warning("Nenhuma linha preenchida para salvar.")

        # === 3. IMPORTAR PLANILHA ===
        with tab_importar:
            st.subheader("📥 Importar Lançamentos via Planilha (Excel)")
            
            st.info("""
            **Siga o padrão abaixo para a sua planilha Excel:**
            A primeira linha deve conter EXATAMENTE os seguintes cabeçalhos (nomes das colunas em minúsculo):
            
            1. **`valor`**: Apenas números e vírgula (ex: 1500,50).
            2. **`data_liquidacao`**: Formato DD/MM/AAAA (ex: 25/01/2026).
            3. **`mes_competencia`**: Nome do mês por extenso (ex: Janeiro).
            4. **`ano_competencia`**: Ano com 4 dígitos (ex: 2026).
            5. **`fornecedor`**: Nome do fornecedor (novos serão cadastrados automaticamente).
            6. **`categoria`**: Classificação (Opcional: Se deixar em branco, o sistema preencherá com a Categoria Padrão).
            7. **`status`**: Preencher com 'Pago' ou 'A Pagar'.
            8. **`observacao`**: Opcional.
            """)

            arquivo_importacao = st.file_uploader("📂 Arraste ou selecione a planilha (.xlsx)", type=["xlsx"])

            if arquivo_importacao is not None:
                if st.button("🚀 Processar e Importar Planilha", type="primary"):
                    try:
                        df_import = pd.read_excel(arquivo_importacao)
                        colunas_esperadas = ['valor', 'data_liquidacao', 'mes_competencia', 'ano_competencia', 'fornecedor']
                        colunas_faltantes = [c for c in colunas_esperadas if c not in df_import.columns.str.lower()]

                        if colunas_faltantes:
                            st.error(f"⚠️ Erro: Faltam as seguintes colunas obrigatórias na sua planilha: {', '.join(colunas_faltantes)}")
                        else:
                            with st.spinner("Processando dados e cadastrando novos fornecedores/classificações..."):
                                df_import.columns = df_import.columns.str.lower()
                                
                                df_forn_atual = carregar_fornecedores_df()
                                nomes_forn_existentes = set(df_forn_atual['nome'].dropna().str.lower().values)
                                
                                df_cat_atual = carregar_categorias_df()
                                nomes_cat_existentes = set(df_cat_atual['nome'].dropna().str.lower().values)
                                
                                d_forn_cat_import = obter_dict_forn_cat()
                                lista_dados_finais = []

                                for index, row in df_import.iterrows():
                                    if pd.isna(row.get('fornecedor')) or pd.isna(row.get('valor')):
                                        continue 

                                    nome_forn = str(row['fornecedor']).strip()
                                    if nome_forn.lower() not in nomes_forn_existentes:
                                        salvar_fornecedor_rapido(nome_forn)
                                        nomes_forn_existentes.add(nome_forn.lower())

                                    cat_str = str(row.get('categoria', '')).strip()
                                    if not cat_str or cat_str.lower() == 'nan':
                                        cat_str = d_forn_cat_import.get(nome_forn, 'Outros')

                                    if cat_str.lower() not in nomes_cat_existentes:
                                        salvar_categoria_rapida(cat_str)
                                        nomes_cat_existentes.add(cat_str.lower())

                                    valor_float = converter_moeda_br_para_float(row['valor'])
                                    mes_nome = str(row['mes_competencia']).strip().capitalize()
                                    ano = str(row['ano_competencia']).strip().replace(".0", "")
                                    
                                    if mes_nome in MESES_PT_INV:
                                        mes_num = MESES_PT_INV[mes_nome]
                                        comp_fmt = f"{ano}-{mes_num:02d}"
                                    else:
                                        comp_fmt = f"{ano}-01"

                                    try:
                                        data_fmt = pd.to_datetime(row['data_liquidacao'], dayfirst=True).strftime("%Y-%m-%d")
                                    except:
                                        data_fmt = datetime.now().strftime("%Y-%m-%d")

                                    status_str = str(row.get('status', 'Pago')).strip()
                                    if status_str.lower() not in ['pago', 'a pagar']: status_str = 'Pago'

                                    obs_str = str(row.get('observacao', '')) if pd.notna(row.get('observacao')) else ""

                                    dados_linha = {
                                        "data_registro": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                        "tipo": "Despesa",
                                        "valor": valor_float,
                                        "fornecedor": nome_forn,
                                        "data_liquidacao": data_fmt,
                                        "competencia": comp_fmt,
                                        "status": status_str,
                                        "categoria": cat_str,
                                        "observacao": obs_str
                                    }
                                    lista_dados_finais.append(dados_linha)

                                if lista_dados_finais:
                                    salvar_lote_lancamentos(pd.DataFrame(lista_dados_finais))
                                    st.success(f"🎉 Sucesso! {len(lista_dados_finais)} despesas foram importadas para o banco de dados.")
                                    time.sleep(3)
                                    st.cache_data.clear()
                                    st.rerun()
                                else:
                                    st.warning("Nenhuma despesa válida encontrada. Verifique se as células de fornecedor e valor estão preenchidas.")
                    
                    except Exception as e:
                        st.error(f"Erro ao ler a planilha. Detalhe técnico: {e}")

        # === 4. EDITAR OU EXCLUIR DESPESA ===
        with tab_editar_excluir:
            st.subheader("🔍 Localizar, Editar ou Excluir")
            df_dados = carregar_dados()
            if not df_dados.empty:
                df_dados['valor'] = pd.to_numeric(df_dados['valor'])
                df_dados['data_liquidacao'] = pd.to_datetime(df_dados['data_liquidacao'], errors='coerce')
                
                col_f1, col_f2, col_f3 = st.columns(3)
                with col_f1:
                    anos_disponiveis = sorted(df_dados['competencia'].str[:4].unique())
                    filtro_ano = st.multiselect("Filtrar por Ano", anos_disponiveis)
                with col_f2:
                    meses_disponiveis = sorted(df_dados['competencia'].str[5:].unique())
                    filtro_mes = st.multiselect("Filtrar por Mês (Numérico)", meses_disponiveis)
                with col_f3:
                    if not df_dados['valor'].empty:
                        valor_min = float(df_dados['valor'].min())
                        valor_max = float(df_dados['valor'].max())
                        if valor_min == valor_max: valor_max += 1.0
                        filtro_valor = st.slider("Faixa de Valor (R$)", valor_min, valor_max, (valor_min, valor_max))
                    else: filtro_valor = (0.0, 0.0)

                col_f4, col_f5 = st.columns(2)
                with col_f4:
                    fornecedores_disponiveis = sorted(df_dados[df_dados['tipo'] == 'Despesa']['fornecedor'].dropna().unique())
                    filtro_forn = st.multiselect("Filtrar por Fornecedor", fornecedores_disponiveis)
                with col_f5:
                    categorias_disponiveis = sorted(df_dados[df_dados['tipo'] == 'Despesa']['categoria'].dropna().unique())
                    filtro_cat = st.multiselect("Filtrar por Categoria", categorias_disponiveis)

                df_filtrado = df_dados.copy()
                df_filtrado = df_filtrado[df_filtrado['tipo'] == 'Despesa']
                
                if filtro_ano: df_filtrado = df_filtrado[df_filtrado['competencia'].str[:4].isin(filtro_ano)]
                if filtro_mes: df_filtrado = df_filtrado[df_filtrado['competencia'].str[5:].isin(filtro_mes)]
                df_filtrado = df_filtrado[(df_filtrado['valor'] >= filtro_valor[0]) & (df_filtrado['valor'] <= filtro_valor[1])]
                if filtro_forn: df_filtrado = df_filtrado[df_filtrado['fornecedor'].isin(filtro_forn)]
                if filtro_cat: df_filtrado = df_filtrado[df_filtrado['categoria'].isin(filtro_cat)]

                st.markdown(f"**Encontrados:** {len(df_filtrado)} registros.")
                if not df_filtrado.empty:
                    df_filtrado_view = df_filtrado.copy()
                    df_filtrado_view.insert(0, "Selecionar", False)
                    editor_acao = st.data_editor(
                        df_filtrado_view,
                        column_config={
                            "Selecionar": st.column_config.CheckboxColumn(required=True),
                            "data_liquidacao": st.column_config.DateColumn("Data Liq.", format="DD/MM/YYYY"),
                            "valor": st.column_config.NumberColumn("Valor", format="R$ %.2f")
                        },
                        disabled=["tipo", "valor", "fornecedor", "data_liquidacao", "competencia", "categoria", "observacao"],
                        hide_index=True,
                        use_container_width=True
                    )
                    
                    linhas_marcadas = editor_acao[editor_acao["Selecionar"] == True]
                    
                    if not linhas_marcadas.empty:
                        indices_selecionados = linhas_marcadas.index.tolist()
                        qtd_selecionada = len(indices_selecionados)
                        
                        st.markdown("---")
                        col_btn1, col_btn2 = st.columns(2)
                        
                        with col_btn1:
                            if st.button("🗑️ CONFIRMAR EXCLUSÃO", type="secondary", use_container_width=True):
                                excluir_lancamentos(indices_selecionados)
                                st.success(f"{qtd_selecionada} registro(s) excluído(s) com sucesso!")
                                time.sleep(2)
                                st.cache_data.clear()
                                st.rerun()

                        with col_btn2:
                            if qtd_selecionada == 1:
                                if st.button("✏️ EDITAR DESPESA", type="primary", use_container_width=True):
                                    st.session_state["editando_idx"] = indices_selecionados[0]
                            elif qtd_selecionada > 1:
                                st.warning("⚠️ Selecione apenas UMA despesa para editar.")

                        if "editando_idx" in st.session_state and st.session_state["editando_idx"] in indices_selecionados:
                            idx = st.session_state["editando_idx"]
                            linha_atual = df_filtrado.loc[idx]
                            
                            st.markdown("### 📝 Editar Informações")
                            with st.form(key=f"form_editar_{idx}"):
                                c1, c2 = st.columns(2)
                                with c1:
                                    novo_valor = st.number_input("Valor (R$)", value=float(linha_atual['valor']), min_value=0.0)
                                    nova_data = st.date_input("Data de Liquidação", value=pd.to_datetime(linha_atual['data_liquidacao']).date(), format="DD/MM/YYYY")
                                    
                                    ano_atual = str(linha_atual['competencia'])[:4]
                                    mes_atual_num = int(str(linha_atual['competencia'])[5:])
                                    mes_atual_nome = MESES_PT[mes_atual_num]
                                    
                                    novo_mes = st.selectbox("Mês de Competência", list(MESES_PT.values()), index=list(MESES_PT.values()).index(mes_atual_nome))
                                    novo_ano = st.selectbox("Ano de Competência", gerar_lista_anos(), index=gerar_lista_anos().index(ano_atual))
                                    
                                    status_atual = linha_atual.get('status', 'Pago')
                                    if pd.isna(status_atual): status_atual = 'Pago'
                                    novo_status = st.selectbox("Status", ["Pago", "A Pagar"], index=["Pago", "A Pagar"].index(status_atual))

                                with c2:
                                    lista_forn = carregar_lista_nomes_fornecedores()
                                    idx_forn = lista_forn.index(linha_atual['fornecedor']) if linha_atual['fornecedor'] in lista_forn else 0
                                    novo_fornecedor = st.selectbox("Fornecedor", lista_forn, index=idx_forn)
                                    
                                    lista_cats = carregar_lista_categorias()
                                    idx_cat = lista_cats.index(linha_atual['categoria']) if linha_atual['categoria'] in lista_cats else 0
                                    nova_categoria = st.selectbox("Categoria", lista_cats, index=idx_cat)
                                    nova_obs = st.text_area("Observação", value=str(linha_atual.get('observacao', '')))

                                if st.form_submit_button("💾 Salvar Edição", type="primary", use_container_width=True):
                                    mes_num = MESES_PT_INV[novo_mes]
                                    nova_comp = f"{novo_ano}-{mes_num:02d}"
                                    
                                    dados_atualizados = {
                                        "valor": novo_valor,
                                        "fornecedor": novo_fornecedor,
                                        "data_liquidacao": nova_data.strftime("%Y-%m-%d"),
                                        "competencia": nova_comp,
                                        "status": novo_status,
                                        "categoria": nova_categoria,
                                        "observacao": nova_obs
                                    }
                                    
                                    editar_lancamento(idx, dados_atualizados)
                                    st.success("Despesa atualizada com sucesso!")
                                    del st.session_state["editando_idx"]
                                    time.sleep(2)
                                    st.cache_data.clear()
                                    st.rerun()

                else: st.info("Nenhuma despesa encontrada.")
            else: st.info("Não há dados cadastrados.")

    # --- ABA: LANÇAR RECEITA ---
    elif menu == "Lançar Receita":
        st.header("📈 Gestão de Receitas")
        
        tab_rec_nova, tab_rec_edit = st.tabs(["📝 Lançar Nova Receita", "✏️ Editar Receitas Lançadas"])
        
        with tab_rec_nova:
            if "limpar_receita_agora" in st.session_state:
                st.session_state["val_rec"] = ""
                st.session_state["obs_rec"] = ""
                st.session_state["data_rec"] = None
                if "mes_rec" in st.session_state: del st.session_state["mes_rec"]
                if "ano_rec" in st.session_state: del st.session_state["ano_rec"]
                del st.session_state["limpar_receita_agora"]

            mes_atual_nome = MESES_PT[datetime.now().month]
            idx_mes = list(MESES_PT.values()).index(mes_atual_nome)
            lista_anos = gerar_lista_anos()

            with st.container():
                valor_str = st.text_input("Valor Receita (R$)", value="", key="val_rec", help="Ex: 15.000,00", on_change=formatar_input_br, args=("val_rec",))
                data_liq = st.date_input("Data Recebimento", value=None, format="DD/MM/YYYY", key="data_rec")
                c_mes, c_ano = st.columns(2)
                with c_mes: mes_rec = st.selectbox("Mês Competência", list(MESES_PT.values()), index=idx_mes, key="mes_rec")
                with c_ano: ano_rec = st.selectbox("Ano Competência", lista_anos, key="ano_rec")
                obs = st.text_area("Observação", key="obs_rec")
                
                st.markdown("---")
                if st.button("💾 Salvar Receita", type="primary"):
                    if not valor_str or not data_liq:
                        st.warning("Preencha o Valor e a Data.")
                    else:
                        valor_float = converter_moeda_br_para_float(valor_str)
                        mes_num = MESES_PT_INV[mes_rec]
                        comp_formatada = f"{ano_rec}-{mes_num:02d}"
                        dados = {
                            "data_registro": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            "tipo": "Receita",
                            "valor": valor_float,
                            "fornecedor": "Cliente Final",
                            "data_liquidacao": data_liq.strftime("%Y-%m-%d"),
                            "competencia": comp_formatada,
                            "status": "Recebido",
                            "categoria": "Vendas",
                            "observacao": obs
                        }
                        salvar_lancamento(dados)
                        st.success("Receita registrada! Limpando em 3 segundos...")
                        time.sleep(3)
                        st.session_state["limpar_receita_agora"] = True
                        st.cache_data.clear()
                        st.rerun()

        with tab_rec_edit:
            st.subheader("🔍 Localizar, Editar ou Excluir Receitas")
            df_rec = carregar_dados()
            
            if not df_rec.empty:
                df_rec['valor'] = pd.to_numeric(df_rec['valor'])
                df_rec['data_liquidacao'] = pd.to_datetime(df_rec['data_liquidacao'], errors='coerce')
                df_rec = df_rec[df_rec['tipo'] == 'Receita'].copy()
                
            if not df_rec.empty:
                df_rec['ano_comp'] = df_rec['competencia'].str[:4]
                df_rec['mes_comp_num'] = df_rec['competencia'].str[5:7].astype(int)
                df_rec['mes_comp_nome'] = df_rec['mes_comp_num'].map(MESES_PT)

                col_fr1, col_fr2 = st.columns(2)
                anos_disponiveis = sorted(df_rec['ano_comp'].dropna().unique(), reverse=True)
                if not anos_disponiveis: anos_disponiveis = [str(datetime.today().year)]
                filtro_ano_rec = col_fr1.selectbox("Filtrar por Ano", ["Todos"] + list(anos_disponiveis))
                
                meses_disponiveis = list(MESES_PT.values())
                filtro_mes_rec = col_fr2.selectbox("Filtrar por Mês", ["Todos"] + meses_disponiveis)

                df_rec_filtrado = df_rec.copy()
                if filtro_ano_rec != "Todos":
                    df_rec_filtrado = df_rec_filtrado[df_rec_filtrado['ano_comp'] == filtro_ano_rec]
                if filtro_mes_rec != "Todos":
                    df_rec_filtrado = df_rec_filtrado[df_rec_filtrado['mes_comp_nome'] == filtro_mes_rec]

                st.markdown(f"**Encontradas:** {len(df_rec_filtrado)} receitas no período selecionado.")
                
                if not df_rec_filtrado.empty:
                    st.markdown("💡 **Dica:** Altere os dados de qualquer receita na tabela abaixo e clique no botão de Salvar. Para apagar, marque a caixa Excluir na primeira coluna.")
                    
                    df_rec_edit = df_rec_filtrado.copy()
                    df_rec_edit.insert(0, "🗑️ Excluir", False)
                    df_rec_edit['data_liquidacao'] = pd.to_datetime(df_rec_edit['data_liquidacao']).dt.date
                    df_rec_edit = df_rec_edit.sort_values("data_liquidacao", ascending=False)
                    
                    lista_cats_rec = carregar_lista_categorias()
                    lista_anos_comp_rec = gerar_lista_anos()
                    lista_meses_comp_rec = list(MESES_PT.values())

                    editor_rec = st.data_editor(
                        df_rec_edit,
                        use_container_width=True,
                        hide_index=True,
                        disabled=["data_registro", "tipo", "competencia", "mes_comp_num", "fornecedor"],
                        column_config={
                            "🗑️ Excluir": st.column_config.CheckboxColumn("Excluir?", required=True),
                            "data_liquidacao": st.column_config.DateColumn("Data Recebimento", format="DD/MM/YYYY"),
                            "valor": st.column_config.NumberColumn("Valor (R$)", format="R$ %.2f", min_value=0.0),
                            "categoria": st.column_config.SelectboxColumn("Categoria", options=lista_cats_rec),
                            "status": st.column_config.SelectboxColumn("Status", options=["Recebido", "A Receber"]),
                            "ano_comp": st.column_config.SelectboxColumn("Ano Comp.", options=lista_anos_comp_rec),
                            "mes_comp_nome": st.column_config.SelectboxColumn("Mês Comp.", options=lista_meses_comp_rec),
                            "observacao": st.column_config.TextColumn("Observação"),
                            "data_registro": None, 
                            "tipo": None,
                            "competencia": None, 
                            "mes_comp_num": None,
                            "fornecedor": None
                        }
                    )

                    mudancas_rec = {}
                    excluir_rec = []

                    for idx in df_rec_edit.index:
                        linha_orig = df_rec_edit.loc[idx]
                        linha_edit = editor_rec.loc[idx]

                        if linha_edit["🗑️ Excluir"]:
                            excluir_rec.append(idx)
                            continue

                        alteracoes = {}
                        if str(linha_orig['data_liquidacao']) != str(linha_edit['data_liquidacao']):
                            alteracoes['data_liquidacao'] = pd.to_datetime(linha_edit['data_liquidacao']).strftime("%Y-%m-%d")
                        if str(linha_orig['categoria']) != str(linha_edit['categoria']):
                            alteracoes['categoria'] = linha_edit['categoria']
                        if str(linha_orig['status']) != str(linha_edit['status']):
                            alteracoes['status'] = linha_edit['status']
                        if float(linha_orig['valor']) != float(linha_edit['valor']):
                            alteracoes['valor'] = float(linha_edit['valor'])
                        if str(linha_orig['mes_comp_nome']) != str(linha_edit['mes_comp_nome']) or str(linha_orig['ano_comp']) != str(linha_edit['ano_comp']):
                            mes_num = MESES_PT_INV[linha_edit['mes_comp_nome']]
                            alteracoes['competencia'] = f"{linha_edit['ano_comp']}-{mes_num:02d}"
                        
                        obs_orig = "" if pd.isna(linha_orig['observacao']) else str(linha_orig['observacao'])
                        obs_edit = "" if pd.isna(linha_edit['observacao']) else str(linha_edit['observacao'])
                        if obs_orig != obs_edit:
                            alteracoes['observacao'] = obs_edit

                        if alteracoes:
                            mudancas_rec[idx] = alteracoes

                    if mudancas_rec or excluir_rec:
                        st.markdown("---")
                        c_btn1, c_btn2 = st.columns(2)
                        with c_btn1:
                            if mudancas_rec:
                                if st.button(f"💾 Salvar {len(mudancas_rec)} Alteração(ões)", key="btn_salvar_rec", type="primary", use_container_width=True):
                                    editar_multiplos_lancamentos(mudancas_rec)
                                    st.success("Receita(s) atualizada(s) com sucesso!")
                                    time.sleep(1.5)
                                    st.cache_data.clear()
                                    st.rerun()
                        with c_btn2:
                            if excluir_rec:
                                if st.button(f"🗑️ Excluir {len(excluir_rec)} Receita(s)", key="btn_excluir_rec", type="secondary", use_container_width=True):
                                    excluir_lancamentos(excluir_rec)
                                    st.success("Receita(s) excluída(s) com sucesso!")
                                    time.sleep(1.5)
                                    st.cache_data.clear()
                                    st.rerun()
                else:
                    st.info("Nenhuma receita encontrada para os filtros aplicados.")
            else:
                st.info("Nenhuma receita cadastrada ainda no sistema.")

    # --- ABA: RELATÓRIOS ---
    elif menu == "Relatórios":
        st.header("📊 Relatórios Gerenciais")
        if st.button("🔄 Atualizar Dados"):
            st.cache_data.clear()
            st.rerun()

        df = carregar_dados()
        
        if not df.empty:
            df['valor'] = pd.to_numeric(df['valor'])
            df['data_liquidacao'] = pd.to_datetime(df['data_liquidacao'], errors='coerce')
            df['ano_comp'] = df['competencia'].str[:4]
            df['mes_comp_num'] = df['competencia'].str[5:].astype(int)
            df['mes_comp_nome'] = df['mes_comp_num'].map(MESES_PT)

            # Abas para separar os relatórios
            tab_dash, tab_calendario, tab_contabil, tab_cat_detalhe = st.tabs([
                "📊 Dashboard e Extrato", 
                "📅 Calendário de Vencimentos (A Pagar)", 
                "📋 Visão Contábil (DRE p/ Contador)",
                "📑 Despesas por Categoria"
            ])

            with tab_dash:
                # 1. Filtros Principais na Tela (Acima dos gráficos)
                st.markdown("### 📅 Filtro de Competência")
                
                def formatar_comp(c):
                    try:
                        ano, mes = c.split('-')
                        return f"{MESES_PT[int(mes)]}/{ano}"
                    except:
                        return c
                
                comps_ordenadas = sorted(df['competencia'].dropna().unique())
                if not comps_ordenadas: 
                    comps_ordenadas = [f"{datetime.now().year}-{datetime.now().month:02d}"]

                col_comp1, col_comp2, col_comp3 = st.columns([1, 1, 2])
                with col_comp1:
                    comp_inicial = st.selectbox("De (Mês/Ano):", options=comps_ordenadas, index=0, format_func=formatar_comp)
                with col_comp2:
                    comp_final = st.selectbox("Até (Mês/Ano):", options=comps_ordenadas, index=len(comps_ordenadas)-1, format_func=formatar_comp)
                
                if comp_inicial > comp_final:
                    comp_final = comp_inicial
                    
                st.markdown("---")

                # 2. Filtros Adicionais na Barra Lateral (Sidebar)
                # IMPORTANTE: Configurados para iniciar vazios para evitar ocultação acidental de novos dados
                st.sidebar.markdown("### Outros Filtros do Relatório")
                filtro_tipo = st.sidebar.multiselect("Tipo", options=["Receita", "Despesa"], placeholder="Todos")
                
                categorias_disp = sorted(df['categoria'].dropna().unique())
                filtro_categoria = st.sidebar.multiselect("Categoria", options=categorias_disp, placeholder="Todas")
                
                if 'status' in df.columns:
                    status_disp = sorted(df['status'].dropna().unique())
                else:
                    status_disp = []
                filtro_status = st.sidebar.multiselect("Status", options=status_disp, placeholder="Todos")
                
                if 'fornecedor' in df.columns:
                    fornecedores_disp = sorted(df['fornecedor'].dropna().astype(str).unique())
                else:
                    fornecedores_disp = []
                filtro_fornecedor = st.sidebar.multiselect("Fornecedor", options=fornecedores_disp, placeholder="Todos")
                
                st.sidebar.markdown("---")
                try:
                    min_date = df['data_liquidacao'].dropna().min().date()
                    max_date = df['data_liquidacao'].dropna().max().date()
                except:
                    min_date = datetime.today().date()
                    max_date = datetime.today().date()

                periodo = st.sidebar.date_input("Filtro por Data de Liquidação (Opcional)", value=[], help="Selecione um período se quiser cruzar a competência com a data exata do pagamento.")

                # 3. Aplicação de Todos os Filtros
                df_filtered = df.copy()
                
                # Aplica o Filtro de Competência da Tela Principal
                df_filtered = df_filtered[(df_filtered['competencia'] >= comp_inicial) & (df_filtered['competencia'] <= comp_final)]
                
                # Aplica os Filtros da Barra Lateral APENAS SE houver algo selecionado
                if filtro_tipo: df_filtered = df_filtered[df_filtered['tipo'].isin(filtro_tipo)]
                if filtro_categoria: df_filtered = df_filtered[df_filtered['categoria'].isin(filtro_categoria)]
                if filtro_status: df_filtered = df_filtered[df_filtered['status'].isin(filtro_status)]
                if filtro_fornecedor: df_filtered = df_filtered[df_filtered['fornecedor'].isin(filtro_fornecedor)]
                
                if isinstance(periodo, tuple) and len(periodo) == 2:
                    df_filtered = df_filtered[(df_filtered['data_liquidacao'].dt.date >= periodo[0]) & (df_filtered['data_liquidacao'].dt.date <= periodo[1])]

                total_rec = df_filtered[df_filtered['tipo'] == 'Receita']['valor'].sum()
                total_desp = df_filtered[df_filtered['tipo'] == 'Despesa']['valor'].sum()
                saldo = total_rec - total_desp
                
                c1, c2, c3 = st.columns(3)
                c1.metric("Receitas", f"R$ {total_rec:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
                c2.metric("Despesas", f"R$ {total_desp:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."), delta_color="inverse")
                c3.metric("Resultado", f"R$ {saldo:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))

                st.markdown("---")
                if not df_filtered.empty:
                    col_g1, col_g2 = st.columns(2)
                    with col_g1:
                        st.subheader("Evolução Mensal (Receita x Despesa)")
                        df_chart1 = df_filtered.groupby(['competencia', 'tipo'])['valor'].sum().unstack().fillna(0)
                        st.bar_chart(df_chart1, use_container_width=True)
                    with col_g2:
                        st.subheader("Distribuição por Categoria")
                        df_cat = df_filtered.groupby("categoria")["valor"].sum().sort_values(ascending=False)
                        st.bar_chart(df_cat, use_container_width=True)
                else:
                    st.info("Sem dados para exibir nos gráficos com os filtros atuais.")

                # ==========================================
                # EXTRATO EDITÁVEL EM MASSA
                # ==========================================
                st.subheader("Extrato Detalhado Interativo")
                st.markdown("💡 **Dica:** Altere qualquer dado diretamente na tabela abaixo e clique no botão de Salvar que aparecerá. Para excluir lançamentos, marque a caixinha na primeira coluna.")
                
                df_extrato_view = df_filtered.copy()
                df_extrato_view.insert(0, "🗑️ Excluir", False)
                df_sorted = df_extrato_view.sort_values("data_liquidacao", ascending=False)
                
                df_sorted['data_liquidacao'] = pd.to_datetime(df_sorted['data_liquidacao']).dt.date
                
                lista_forn = carregar_lista_nomes_fornecedores()
                lista_cats = carregar_lista_categorias()
                lista_anos_comp = gerar_lista_anos()
                lista_meses_comp = list(MESES_PT.values())

                editor_extrato = st.data_editor(
                    df_sorted, 
                    use_container_width=True,
                    hide_index=True,
                    disabled=["data_registro", "tipo", "competencia", "mes_comp_num"],
                    column_config={
                        "🗑️ Excluir": st.column_config.CheckboxColumn("Excluir?", required=True),
                        "data_liquidacao": st.column_config.DateColumn("Data Liq.", format="DD/MM/YYYY"),
                        "valor": st.column_config.NumberColumn("Valor", format="R$ %.2f", min_value=0.0),
                        "fornecedor": st.column_config.SelectboxColumn("Fornecedor/Cliente", options=lista_forn),
                        "categoria": st.column_config.SelectboxColumn("Categoria", options=lista_cats),
                        "status": st.column_config.SelectboxColumn("Status", options=["Pago", "A Pagar", "Recebido", "A Receber"]),
                        "ano_comp": st.column_config.SelectboxColumn("Ano Comp.", options=lista_anos_comp),
                        "mes_comp_nome": st.column_config.SelectboxColumn("Mês Comp.", options=lista_meses_comp),
                        "observacao": st.column_config.TextColumn("Observação"),
                        "data_registro": None, 
                        "tipo": None,
                        "competencia": None, 
                        "mes_comp_num": None 
                    }
                )

                mudancas_dict = {}
                linhas_para_excluir = []

                for idx in df_sorted.index:
                    linha_original = df_sorted.loc[idx]
                    linha_editada = editor_extrato.loc[idx]

                    if linha_editada["🗑️ Excluir"]:
                        linhas_para_excluir.append(idx)
                        continue

                    alteracoes_linha = {}
                    
                    if str(linha_original['data_liquidacao']) != str(linha_editada['data_liquidacao']):
                        alteracoes_linha['data_liquidacao'] = pd.to_datetime(linha_editada['data_liquidacao']).strftime("%Y-%m-%d")
                    if str(linha_original['fornecedor']) != str(linha_editada['fornecedor']):
                        alteracoes_linha['fornecedor'] = linha_editada['fornecedor']
                    if str(linha_original['categoria']) != str(linha_editada['categoria']):
                        alteracoes_linha['categoria'] = linha_editada['categoria']
                    if str(linha_original['status']) != str(linha_editada['status']):
                        alteracoes_linha['status'] = linha_editada['status']
                    if float(linha_original['valor']) != float(linha_editada['valor']):
                        alteracoes_linha['valor'] = float(linha_editada['valor'])
                    if str(linha_original['mes_comp_nome']) != str(linha_editada['mes_comp_nome']) or str(linha_original['ano_comp']) != str(linha_editada['ano_comp']):
                        mes_num = MESES_PT_INV[linha_editada['mes_comp_nome']]
                        nova_comp = f"{linha_editada['ano_comp']}-{mes_num:02d}"
                        alteracoes_linha['competencia'] = nova_comp

                    obs_orig = "" if pd.isna(linha_original['observacao']) else str(linha_original['observacao'])
                    obs_edit = "" if pd.isna(linha_editada['observacao']) else str(linha_editada['observacao'])
                    if obs_orig != obs_edit:
                        alteracoes_linha['observacao'] = obs_edit
                        
                    if alteracoes_linha:
                        mudancas_dict[idx] = alteracoes_linha

                if mudancas_dict or linhas_para_excluir:
                    st.markdown("---")
                    c_btn1, c_btn2 = st.columns(2)
                    
                    with c_btn1:
                        if mudancas_dict:
                            if st.button(f"💾 Salvar {len(mudancas_dict)} Alteração(ões)", type="primary", use_container_width=True):
                                editar_multiplos_lancamentos(mudancas_dict)
                                st.success("Lançamento(s) atualizado(s) com sucesso!")
                                time.sleep(1.5)
                                st.cache_data.clear()
                                st.rerun()
                                
                    with c_btn2:
                        if linhas_para_excluir:
                            if st.button(f"🗑️ Confirmar Exclusão de {len(linhas_para_excluir)} Lançamento(s)", type="secondary", use_container_width=True):
                                excluir_lancamentos(linhas_para_excluir)
                                st.success("Lançamento(s) excluído(s) com sucesso!")
                                time.sleep(1.5)
                                st.cache_data.clear()
                                st.rerun()

            with tab_calendario:
                st.subheader("🗓️ Calendário de Vencimentos")
                st.markdown("Os dias marcados em destaque (**🚨**) possuem despesas com o status **A Pagar**. Clique num dia para ver os detalhes.")
                
                if 'status' not in df.columns:
                    st.warning("O seu banco de dados ainda não tem a coluna de Status configurada corretamente.")
                else:
                    df_a_pagar = df[(df['tipo'] == 'Despesa') & (df['status'] == 'A Pagar')].copy()
                    
                    col_c1, col_c2 = st.columns(2)
                    with col_c1:
                        cal_mes = st.selectbox("Mês do Calendário", list(MESES_PT.values()), index=datetime.today().month - 1, key="cal_mes")
                    with col_c2:
                        cal_ano = st.selectbox("Ano do Calendário", gerar_lista_anos(), index=gerar_lista_anos().index(str(datetime.today().year)), key="cal_ano")

                    mes_num = MESES_PT_INV[cal_mes]
                    ano_num = int(cal_ano)

                    df_a_pagar_mes = df_a_pagar[
                        (df_a_pagar['data_liquidacao'].dt.month == mes_num) & 
                        (df_a_pagar['data_liquidacao'].dt.year == ano_num)
                    ]
                    
                    datas_com_pendencia = df_a_pagar_mes['data_liquidacao'].dt.date.unique()

                    st.markdown('''
                        <style>
                        div[data-testid="column"] button {
                            width: 100%;
                            height: 60px;
                            font-size: 18px;
                        }
                        </style>
                    ''', unsafe_allow_html=True)

                    dias_semana = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"]
                    cols_header = st.columns(7)
                    for i, dia in enumerate(dias_semana):
                        cols_header[i].markdown(f"<div style='text-align: center; font-weight: bold;'>{dia}</div>", unsafe_allow_html=True)

                    cal = calendar.monthcalendar(ano_num, mes_num)
                    
                    for semana in cal:
                        cols = st.columns(7)
                        for i, dia in enumerate(semana):
                            if dia == 0:
                                cols[i].write("") 
                            else:
                                data_atual = date(ano_num, mes_num, dia)
                                tem_pendencia = data_atual in datas_com_pendencia
                                
                                if tem_pendencia:
                                    if cols[i].button(f"🚨 {dia}", key=f"btn_cal_{data_atual}", type="primary", help="Há despesas a pagar neste dia!"):
                                        st.session_state['cal_data_selecionada'] = data_atual
                                else:
                                    if cols[i].button(f"{dia}", key=f"btn_cal_{data_atual}", help="Sem pendências para este dia."):
                                        st.session_state['cal_data_selecionada'] = data_atual

                    st.markdown("---")
                    
                    if 'cal_data_selecionada' in st.session_state:
                        data_sel = st.session_state['cal_data_selecionada']
                        
                        if data_sel.month == mes_num and data_sel.year == ano_num:
                            st.markdown(f"#### 🔎 Despesas para o dia {data_sel.strftime('%d/%m/%Y')}")
                            df_dia = df[(df['tipo'] == 'Despesa') & (df['data_liquidacao'].dt.date == data_sel)]
                            
                            if not df_dia.empty:
                                st.markdown("💡 **Dica:** Altere qualquer dado (Data, Status, Valor, Fornecedor, etc.) diretamente na tabela abaixo e clique em Salvar.")
                                
                                lista_fornecedores_cadastrados = carregar_lista_nomes_fornecedores()
                                lista_categorias_cadastradas = carregar_lista_categorias()
                                
                                df_dia_view = df_dia[['data_liquidacao', 'fornecedor', 'categoria', 'status', 'valor', 'observacao']].copy()
                                df_dia_view['data_liquidacao'] = pd.to_datetime(df_dia_view['data_liquidacao']).dt.date
                                
                                edited_dia = st.data_editor(
                                    df_dia_view,
                                    use_container_width=True,
                                    hide_index=True,
                                    column_config={
                                        "data_liquidacao": st.column_config.DateColumn("Data Liq.", format="DD/MM/YYYY", required=True),
                                        "status": st.column_config.SelectboxColumn("Status", options=["Pago", "A Pagar"], required=True),
                                        "valor": st.column_config.NumberColumn("Valor (R$)", format="R$ %.2f", required=True),
                                        "fornecedor": st.column_config.SelectboxColumn("Fornecedor", options=lista_fornecedores_cadastrados, required=True),
                                        "categoria": st.column_config.SelectboxColumn("Categoria", options=lista_categorias_cadastradas, required=True),
                                        "observacao": st.column_config.TextColumn("Observação")
                                    }
                                )
                                
                                mudancas_dict = {}
                                for idx in df_dia_view.index:
                                    linha_original = df_dia_view.loc[idx]
                                    linha_editada = edited_dia.loc[idx]
                                    
                                    alteracoes_linha = {}
                                    
                                    if str(linha_original['data_liquidacao']) != str(linha_editada['data_liquidacao']):
                                        alteracoes_linha['data_liquidacao'] = pd.to_datetime(linha_editada['data_liquidacao']).strftime("%Y-%m-%d")
                                    if linha_original['fornecedor'] != linha_editada['fornecedor']:
                                        alteracoes_linha['fornecedor'] = linha_editada['fornecedor']
                                    if linha_original['categoria'] != linha_editada['categoria']:
                                        alteracoes_linha['categoria'] = linha_editada['categoria']
                                    if linha_original['status'] != linha_editada['status']:
                                        alteracoes_linha['status'] = linha_editada['status']
                                    if float(linha_original['valor']) != float(linha_editada['valor']):
                                        alteracoes_linha['valor'] = float(linha_editada['valor'])
                                        
                                    obs_orig = "" if pd.isna(linha_original['observacao']) else str(linha_original['observacao'])
                                    obs_edit = "" if pd.isna(linha_editada['observacao']) else str(linha_editada['observacao'])
                                    if obs_orig != obs_edit:
                                        alteracoes_linha['observacao'] = obs_edit
                                        
                                    if alteracoes_linha:
                                        mudancas_dict[idx] = alteracoes_linha
                                
                                if mudancas_dict:
                                    if st.button(f"💾 Salvar {len(mudancas_dict)} Alteração(ões)", type="primary"):
                                        editar_multiplos_lancamentos(mudancas_dict)
                                        st.success("Lançamento(s) atualizado(s) com sucesso!")
                                        time.sleep(1.5)
                                        st.cache_data.clear()
                                        st.rerun()

                                total_dia = edited_dia['valor'].sum()
                                total_pendente_view = edited_dia[edited_dia['status'] == 'A Pagar']['valor'].sum()
                                
                                c1, c2 = st.columns(2)
                                c1.metric("Total Agendado no Dia", f"R$ {total_dia:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
                                c2.metric("Total A Pagar (Pendente)", f"R$ {total_pendente_view:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."), delta_color="inverse")

                            else:
                                st.success("Nenhuma despesa lançada para este dia! 🎉")

            with tab_contabil:
                st.subheader("📋 Demonstração do Resultado do Exercício (DRE) e Dados Tributários")
                st.markdown("Esta visão agrupa os lançamentos para facilitar o planejamento tributário pelo seu contador (Simples Nacional, Lucro Presumido ou Real).")
                
                ano_dre = st.selectbox("Selecione o Ano Base para Análise Contábil", sorted(df['ano_comp'].dropna().unique(), reverse=True), key="sel_ano_dre")
                
                df_dre = df[df['ano_comp'] == ano_dre].copy()
                
                if not df_dre.empty:
                    cats_folha = ["Salário", "13° Salário", "Férias", "INSS", "FGTS", "Vale Alimentação", "Mão de obra"]
                    cats_impostos = ["Simples Nacional"]
                    cats_cpv = ["Mercadoria", "Frete"] 
                    
                    receita_bruta = df_dre[(df_dre['tipo'] == 'Receita')]['valor'].sum()
                    custo_mercadorias = df_dre[(df_dre['tipo'] == 'Despesa') & (df_dre['categoria'].isin(cats_cpv))]['valor'].sum()
                    despesas_folha = df_dre[(df_dre['tipo'] == 'Despesa') & (df_dre['categoria'].isin(cats_folha))]['valor'].sum()
                    impostos = df_dre[(df_dre['tipo'] == 'Despesa') & (df_dre['categoria'].isin(cats_impostos))]['valor'].sum()
                    outras_despesas = df_dre[(df_dre['tipo'] == 'Despesa') & (~df_dre['categoria'].isin(cats_cpv + cats_folha + cats_impostos))]['valor'].sum()
                    
                    lucro_bruto = receita_bruta - custo_mercadorias
                    lucro_liquido = lucro_bruto - despesas_folha - impostos - outras_despesas
                    
                    margem_lucro = (lucro_liquido / receita_bruta * 100) if receita_bruta > 0 else 0
                    
                    st.markdown(f"### Resumo Anual ({ano_dre})")
                    col_dre1, col_dre2, col_dre3, col_dre4 = st.columns(4)
                    col_dre1.metric("1. Faturamento Bruto", f"R$ {receita_bruta:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
                    col_dre2.metric("2. Custos (Mercadorias/Frete)", f"R$ {custo_mercadorias:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."), delta_color="inverse")
                    col_dre3.metric("3. Despesas (Folha + Operacional)", f"R$ {(despesas_folha + outras_despesas):,.2f}".replace(",", "X").replace(".", ",").replace("X", "."), delta_color="inverse")
                    col_dre4.metric("4. Lucro Líquido", f"R$ {lucro_liquido:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."), f"Margem: {margem_lucro:.1f}%")
                    
                    st.markdown("---")
                    st.markdown("### DRE Mensalizada (Exportável)")
                    
                    df_dre['conta_contabil'] = 'Outras Despesas Operacionais'
                    df_dre.loc[df_dre['tipo'] == 'Receita', 'conta_contabil'] = '1. Receita Bruta'
                    df_dre.loc[(df_dre['tipo'] == 'Despesa') & (df_dre['categoria'].isin(cats_cpv)), 'conta_contabil'] = '2. Custo das Mercadorias (CPV)'
                    df_dre.loc[(df_dre['tipo'] == 'Despesa') & (df_dre['categoria'].isin(cats_folha)), 'conta_contabil'] = '3. Despesas com Folha/RH'
                    df_dre.loc[(df_dre['tipo'] == 'Despesa') & (df_dre['categoria'].isin(cats_impostos)), 'conta_contabil'] = '4. Impostos Recolhidos'
                    df_dre.loc[(df_dre['tipo'] == 'Despesa') & (df_dre['conta_contabil'] == 'Outras Despesas Operacionais'), 'conta_contabil'] = '5. Outras Despesas Operacionais'
                    
                    dre_pivot = pd.pivot_table(
                        df_dre, 
                        values='valor', 
                        index='conta_contabil', 
                        columns='mes_comp_num', 
                        aggfunc='sum', 
                        fill_value=0
                    )
                    
                    dre_pivot.columns = [MESES_PT[col] for col in dre_pivot.columns]
                    dre_pivot['TOTAL ANUAL'] = dre_pivot.sum(axis=1)
                    
                    st.dataframe(
                        dre_pivot.style.format("R$ {:,.2f}"),
                        use_container_width=True
                    )
                    
                    st.info("💡 **Dica para o Contador:** Passe o mouse sobre a tabela acima e clique no ícone de download (flecha apontando para baixo) no canto superior direito para exportar esta DRE como um arquivo CSV.")
                else:
                    st.warning(f"Não há lançamentos registrados no ano de {ano_dre}.")

            with tab_cat_detalhe:
                st.subheader("📑 Detalhamento de Despesas por Categoria")
                st.markdown("Visualize suas despesas agrupadas por classificação e faça edições rápidas.")

                c_f1, c_f2, c_f3 = st.columns(3)
                
                anos_cat = sorted(df[df['tipo'] == 'Despesa']['ano_comp'].dropna().unique(), reverse=True)
                if not anos_cat: anos_cat = [str(datetime.today().year)]
                ano_cat_sel = c_f1.selectbox("Ano de Competência", ["Todos"] + list(anos_cat), key="ano_cat_sel")

                meses_cat = list(MESES_PT.values())
                mes_cat_sel = c_f2.selectbox("Mês de Competência", ["Todos"] + meses_cat, key="mes_cat_sel")
                
                categorias_existentes = sorted(df[df['tipo'] == 'Despesa']['categoria'].dropna().unique())
                cat_filtro_sel = c_f3.selectbox("Filtrar por Categoria", ["Todas"] + list(categorias_existentes), key="cat_filtro_sel")

                df_cat_view = df[df['tipo'] == 'Despesa'].copy()
                if ano_cat_sel != "Todos":
                    df_cat_view = df_cat_view[df_cat_view['ano_comp'] == ano_cat_sel]
                if mes_cat_sel != "Todos":
                    df_cat_view = df_cat_view[df_cat_view['mes_comp_nome'] == mes_cat_sel]
                if cat_filtro_sel != "Todas":
                    df_cat_view = df_cat_view[df_cat_view['categoria'] == cat_filtro_sel]

                if not df_cat_view.empty:
                    df_resumo = df_cat_view.groupby('categoria')['valor'].sum().reset_index()
                    df_resumo.columns = ['Categoria', 'Total (R$)']
                    df_resumo = df_resumo.sort_values('Total (R$)', ascending=False)

                    st.markdown("### Resumo por Categoria")
                    st.dataframe(df_resumo.style.format({'Total (R$)': 'R$ {:,.2f}'}), use_container_width=True, hide_index=True)

                    st.markdown("---")
                    st.markdown("### Lançamentos Detalhados (Editáveis)")
                    st.markdown("💡 **Dica:** Altere os dados diretamente na tabela e clique no botão Salvar que aparecerá embaixo. Para excluir, marque a caixinha na primeira coluna.")
                    
                    df_detalhe_edit = df_cat_view.copy()
                    df_detalhe_edit.insert(0, "🗑️ Excluir", False)
                    df_detalhe_edit['data_liquidacao'] = pd.to_datetime(df_detalhe_edit['data_liquidacao']).dt.date
                    df_detalhe_edit = df_detalhe_edit.sort_values(['categoria', 'data_liquidacao'])
                    
                    lista_forn_cat = carregar_lista_nomes_fornecedores()
                    lista_cats_cat = carregar_lista_categorias()
                    lista_anos_comp_cat = gerar_lista_anos()
                    lista_meses_comp_cat = list(MESES_PT.values())
                    
                    editor_cat = st.data_editor(
                        df_detalhe_edit,
                        use_container_width=True,
                        hide_index=True,
                        disabled=["data_registro", "tipo", "competencia", "mes_comp_num"],
                        column_config={
                            "🗑️ Excluir": st.column_config.CheckboxColumn("Excluir?", required=True),
                            "data_liquidacao": st.column_config.DateColumn("Data Liq.", format="DD/MM/YYYY"),
                            "categoria": st.column_config.SelectboxColumn("Categoria", options=lista_cats_cat),
                            "fornecedor": st.column_config.SelectboxColumn("Fornecedor", options=lista_forn_cat),
                            "observacao": st.column_config.TextColumn("Observação"),
                            "status": st.column_config.SelectboxColumn("Status", options=["Pago", "A Pagar"]),
                            "valor": st.column_config.NumberColumn("Valor (R$)", format="R$ %.2f", min_value=0.0),
                            "ano_comp": st.column_config.SelectboxColumn("Ano Comp.", options=lista_anos_comp_cat),
                            "mes_comp_nome": st.column_config.SelectboxColumn("Mês Comp.", options=lista_meses_comp_cat),
                            "data_registro": None, 
                            "tipo": None,
                            "competencia": None, 
                            "mes_comp_num": None 
                        }
                    )
                    
                    mudancas_cat = {}
                    excluir_cat = []

                    for idx in df_detalhe_edit.index:
                        linha_orig = df_detalhe_edit.loc[idx]
                        linha_edit = editor_cat.loc[idx]

                        if linha_edit["🗑️ Excluir"]:
                            excluir_cat.append(idx)
                            continue

                        alteracoes = {}
                        if str(linha_orig['data_liquidacao']) != str(linha_edit['data_liquidacao']):
                            alteracoes['data_liquidacao'] = pd.to_datetime(linha_edit['data_liquidacao']).strftime("%Y-%m-%d")
                        if str(linha_orig['fornecedor']) != str(linha_edit['fornecedor']):
                            alteracoes['fornecedor'] = linha_edit['fornecedor']
                        if str(linha_orig['categoria']) != str(linha_edit['categoria']):
                            alteracoes['categoria'] = linha_edit['categoria']
                        if str(linha_orig['status']) != str(linha_edit['status']):
                            alteracoes['status'] = linha_edit['status']
                        if float(linha_orig['valor']) != float(linha_edit['valor']):
                            alteracoes['valor'] = float(linha_edit['valor'])
                        if str(linha_orig['mes_comp_nome']) != str(linha_edit['mes_comp_nome']) or str(linha_orig['ano_comp']) != str(linha_edit['ano_comp']):
                            mes_num = MESES_PT_INV[linha_edit['mes_comp_nome']]
                            alteracoes['competencia'] = f"{linha_edit['ano_comp']}-{mes_num:02d}"
                        
                        obs_orig = "" if pd.isna(linha_orig['observacao']) else str(linha_orig['observacao'])
                        obs_edit = "" if pd.isna(linha_edit['observacao']) else str(linha_edit['observacao'])
                        if obs_orig != obs_edit:
                            alteracoes['observacao'] = obs_edit

                        if alteracoes:
                            mudancas_cat[idx] = alteracoes

                    if mudancas_cat or excluir_cat:
                        c_btn1, c_btn2 = st.columns(2)
                        with c_btn1:
                            if mudancas_cat:
                                if st.button(f"💾 Salvar {len(mudancas_cat)} Alteração(ões) na Categoria", key="btn_salvar_cat", type="primary", use_container_width=True):
                                    editar_multiplos_lancamentos(mudancas_cat)
                                    st.success("Atualizado com sucesso!")
                                    time.sleep(1.5)
                                    st.cache_data.clear()
                                    st.rerun()
                        with c_btn2:
                            if excluir_cat:
                                if st.button(f"🗑️ Excluir {len(excluir_cat)} Lançamento(s)", key="btn_excluir_cat", type="secondary", use_container_width=True):
                                    excluir_lancamentos(excluir_cat)
                                    st.success("Excluído com sucesso!")
                                    time.sleep(1.5)
                                    st.cache_data.clear()
                                    st.rerun()

                    df_export = df_cat_view[['data_liquidacao', 'categoria', 'fornecedor', 'observacao', 'status', 'valor']].copy()
                    df_export.columns = ['Data Liq.', 'Categoria', 'Fornecedor', 'Observação', 'Status', 'Valor (R$)']
                    df_export['Data Liq.'] = pd.to_datetime(df_export['Data Liq.']).dt.strftime('%d/%m/%Y')
                    df_export = df_export.sort_values(['Categoria', 'Data Liq.'])

                    output = io.BytesIO()
                    with pd.ExcelWriter(output, engine='openpyxl') as writer:
                        df_resumo.to_excel(writer, index=False, sheet_name='Resumo de Categorias')
                        df_export.to_excel(writer, index=False, sheet_name='Lançamentos Detalhados')
                    excel_data = output.getvalue()

                    st.markdown("---")
                    st.download_button(
                        label="📥 Baixar Relatório Completo em Excel (.xlsx)",
                        data=excel_data,
                        file_name=f"Despesas_por_Categoria_{ano_cat_sel}_{mes_cat_sel}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        type="primary"
                    )
                else:
                    st.info("Nenhuma despesa encontrada para os filtros selecionados.")

        else:
            st.info("Nenhum dado lançado ainda.")

    # --- ABA: CONCILIAÇÃO BANCÁRIA ---
    elif menu == "Conciliação Bancária":
        st.header("🏦 Conciliação Bancária Automática (OFX)")
        
        st.markdown("""
        **Como funciona:**
        Exporte o extrato da sua conta bancária no formato **.ofx** e faça o upload abaixo.
        O sistema identificará automaticamente as saídas e as cruzará com as despesas cadastradas no sistema.
        """)

        arquivo_ofx = st.file_uploader("📥 Envie o extrato bancário (.ofx)", type=["ofx"])

        if arquivo_ofx is not None:
            with st.spinner("Analisando e processando arquivo OFX..."):
                try:
                    conteudo = arquivo_ofx.getvalue().decode('latin1', errors='ignore')
                    transacoes = re.findall(r'<STMTTRN>(.*?)</STMTTRN>', conteudo, re.DOTALL)
                    
                    dados_extrato = []
                    for t in transacoes:
                        dt_match = re.search(r'<DTPOSTED>(\d{8})', t)
                        data_str = dt_match.group(1) if dt_match else None
                        val_match = re.search(r'<TRNAMT>([\-\d\.]+)', t)
                        valor_str = val_match.group(1) if val_match else None
                        memo_match = re.search(r'<MEMO>(.*?)(?:<|\r|\n)', t)
                        name_match = re.search(r'<NAME>(.*?)(?:<|\r|\n)', t)
                        
                        if memo_match: desc = memo_match.group(1).strip()
                        elif name_match: desc = name_match.group(1).strip()
                        else: desc = "Sem descrição"
                        
                        if data_str and valor_str:
                            data_obj = datetime.strptime(data_str, '%Y%m%d').date()
                            valor_float = float(valor_str)
                            dados_extrato.append({
                                'Data': data_obj,
                                'Historico': desc,
                                'Valor': valor_float
                            })
                            
                    df_extrato = pd.DataFrame(dados_extrato)

                    if not df_extrato.empty:
                        df_ext_saidas = df_extrato[df_extrato['Valor'] < 0].copy()
                        df_ext_saidas['Valor_Absoluto'] = df_ext_saidas['Valor'].abs() 
                        df_ext_saidas['CHAVE_DATA'] = df_ext_saidas['Data'].astype(str).str.strip()
                        df_ext_saidas['CHAVE_VALOR'] = df_ext_saidas['Valor_Absoluto'].apply(lambda x: "{:.2f}".format(x))
                        # Criar um número de sequência para desempatar transações de mesmo valor no mesmo dia
                        df_ext_saidas['SEQ'] = df_ext_saidas.groupby(['CHAVE_DATA', 'CHAVE_VALOR']).cumcount()

                        df_sistema = carregar_dados()
                        df_sistema = df_sistema[df_sistema['tipo'] == 'Despesa'].copy()
                        df_sistema['valor'] = pd.to_numeric(df_sistema['valor'])
                        
                        df_sistema['CHAVE_DATA'] = pd.to_datetime(df_sistema['data_liquidacao']).dt.date.astype(str).str.strip()
                        df_sistema['CHAVE_VALOR'] = df_sistema['valor'].apply(lambda x: "{:.2f}".format(x))
                        # Criar o mesmo número de sequência no sistema
                        df_sistema['SEQ'] = df_sistema.groupby(['CHAVE_DATA', 'CHAVE_VALOR']).cumcount()

                        # O merge agora exige Data, Valor e Sequência iguais (1 para 1)
                        df_conciliados = pd.merge(df_ext_saidas, df_sistema, on=['CHAVE_DATA', 'CHAVE_VALOR', 'SEQ'], how='inner')
                        
                        # Atualiza as chaves únicas para incluir a sequência
                        chaves_conciliadas = df_conciliados['CHAVE_DATA'] + df_conciliados['CHAVE_VALOR'] + df_conciliados['SEQ'].astype(str)
                        df_ext_saidas['CHAVE_UNICA'] = df_ext_saidas['CHAVE_DATA'] + df_ext_saidas['CHAVE_VALOR'] + df_ext_saidas['SEQ'].astype(str)
                        df_nao_encontrados = df_ext_saidas[~df_ext_saidas['CHAVE_UNICA'].isin(chaves_conciliadas)]

                        st.markdown("---")
                        c1, c2 = st.columns(2)
                        c1.metric("✅ Despesas Encontradas (Conciliadas)", len(df_conciliados))
                        c2.metric("⚠️ Despesas NÃO Lançadas no Sistema", len(df_nao_encontrados))

                        tab_pendentes, tab_ok = st.tabs(["🔴 Pendentes de Lançamento (Faltando)", "🟢 Já Conciliados (Tudo Certo)"])

                        with tab_pendentes:
                            if not df_nao_encontrados.empty:
                                st.warning("Atenção! As seguintes saídas constam no extrato do Banco, mas NÃO foram localizadas no seu Sistema. Preencha os dados abaixo e marque a caixinha para registrá-las.")
                                
                                with st.expander("➕ O Fornecedor não está na lista? Cadastre aqui."):
                                    c_fn1, c_fn2 = st.columns([3, 1])
                                    with c_fn1:
                                        novo_forn_extrato = st.text_input("Digite o nome do novo Fornecedor", key="novo_forn_extrato")
                                    with c_fn2:
                                        st.markdown("<div style='margin-top: 28px;'></div>", unsafe_allow_html=True)
                                        if st.button("Cadastrar Fornecedor", use_container_width=True):
                                            if novo_forn_extrato.strip():
                                                salvar_fornecedor_rapido(novo_forn_extrato)
                                                st.success(f"Fornecedor '{novo_forn_extrato}' cadastrado com sucesso!")
                                                time.sleep(1)
                                                st.cache_data.clear() 
                                                st.rerun() 
                                            else:
                                                st.error("Digite um nome válido.")
                                
                                with st.expander("➕ A Classificação não está na lista? Cadastre aqui."):
                                    c_cat1, c_cat2 = st.columns([3, 1])
                                    with c_cat1:
                                        nova_cat_extrato = st.text_input("Digite o nome da nova Classificação", key="nova_cat_extrato")
                                    with c_cat2:
                                        st.markdown("<div style='margin-top: 28px;'></div>", unsafe_allow_html=True)
                                        if st.button("Cadastrar Classificação", key="btn_nova_cat", use_container_width=True):
                                            if nova_cat_extrato.strip():
                                                salvar_categoria_rapida(nova_cat_extrato)
                                                st.success(f"Classificação '{nova_cat_extrato}' cadastrada com sucesso!")
                                                time.sleep(1)
                                                st.cache_data.clear()
                                                st.rerun()
                                            else:
                                                st.error("Digite um nome válido.")

                                mes_atual = MESES_PT[datetime.today().month]
                                ano_atual = str(datetime.today().year)
                                lista_anos = gerar_lista_anos()
                                
                                lista_fornecedores_cadastrados = carregar_lista_nomes_fornecedores()
                                lista_categorias_cadastradas = carregar_lista_categorias()

                                df_edit_pendentes = df_nao_encontrados[['Data', 'Historico', 'Valor_Absoluto']].copy()
                                df_edit_pendentes.columns = ['Data Extrato', 'Descrição do Banco', 'Valor (R$)']

                                df_edit_pendentes.insert(0, "Lançar?", False)
                                df_edit_pendentes['Mês Comp.'] = mes_atual
                                df_edit_pendentes['Ano Comp.'] = ano_atual
                                df_edit_pendentes['Fornecedor'] = None 
                                df_edit_pendentes['Categoria'] = None 
                                df_edit_pendentes['Observação'] = ""

                                edited_pendentes = st.data_editor(
                                    df_edit_pendentes,
                                    use_container_width=True,
                                    hide_index=True,
                                    column_config={
                                        "Lançar?": st.column_config.CheckboxColumn("Lançar?", required=True),
                                        "Data Extrato": st.column_config.DateColumn("Data Extrato", format="DD/MM/YYYY", disabled=True),
                                        "Descrição do Banco": st.column_config.TextColumn("Descrição do Banco", disabled=True),
                                        "Valor (R$)": st.column_config.NumberColumn("Valor (R$)", format="R$ %.2f", disabled=True),
                                        "Mês Comp.": st.column_config.SelectboxColumn("Mês Comp.", options=list(MESES_PT.values()), required=True),
                                        "Ano Comp.": st.column_config.SelectboxColumn("Ano Comp.", options=lista_anos, required=True),
                                        "Fornecedor": st.column_config.SelectboxColumn(
                                            "Fornecedor (Selecione)", 
                                            options=lista_fornecedores_cadastrados, 
                                            required=True
                                        ),
                                        "Categoria": st.column_config.SelectboxColumn(
                                            "Classificação (Selecione)", 
                                            options=lista_categorias_cadastradas, 
                                            required=True
                                        ),
                                        "Observação": st.column_config.TextColumn("Observação")
                                    }
                                )

                                if st.button("💾 Lançar Despesas Selecionadas", type="primary"):
                                    linhas_marcadas = edited_pendentes[edited_pendentes["Lançar?"] == True]

                                    if linhas_marcadas.empty:
                                        st.warning("Selecione pelo menos uma despesa marcando a caixinha 'Lançar?'.")
                                    else:
                                        lista_dados_finais = []
                                        erro_encontrado = False

                                        for index, row in linhas_marcadas.iterrows():
                                            if not row['Fornecedor'] or str(row['Fornecedor']).strip() == "":
                                                st.error(f"⚠️ Selecione um Fornecedor na lista para a despesa de R$ {row['Valor (R$)']:.2f}")
                                                erro_encontrado = True
                                                continue
                                            
                                            if not row['Categoria'] or str(row['Categoria']).strip() == "":
                                                st.error(f"⚠️ Selecione uma Classificação na lista para a despesa de R$ {row['Valor (R$)']:.2f}")
                                                erro_encontrado = True
                                                continue

                                            nome_forn = str(row['Fornecedor']).strip()
                                            nome_cat = str(row['Categoria']).strip()
                                            mes_num = MESES_PT_INV[row['Mês Comp.']]
                                            comp_fmt = f"{row['Ano Comp.']}-{mes_num:02d}"

                                            dados_linha = {
                                                "data_registro": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                                "tipo": "Despesa",
                                                "valor": row['Valor (R$)'],
                                                "fornecedor": nome_forn,
                                                "data_liquidacao": pd.to_datetime(row['Data Extrato']).strftime("%Y-%m-%d"),
                                                "competencia": comp_fmt,
                                                "status": "Pago", 
                                                "categoria": nome_cat,
                                                "observacao": str(row['Observação']) if pd.notna(row['Observação']) else ""
                                            }
                                            lista_dados_finais.append(dados_linha)

                                        if lista_dados_finais and not erro_encontrado:
                                            salvar_lote_lancamentos(pd.DataFrame(lista_dados_finais))
                                            st.success(f"🎉 {len(lista_dados_finais)} despesa(s) lançada(s) com sucesso!")
                                            time.sleep(2)
                                            st.cache_data.clear()
                                            st.rerun()

                            else:
                                st.success("🎉 Sensacional! Todas as despesas de saída identificadas neste extrato bancário já estão devidamente lançadas no sistema.")

                        with tab_ok:
                            if not df_conciliados.empty:
                                st.success("As despesas abaixo foram localizadas tanto no extrato bancário quanto no seu sistema:")
                                view_ok = df_conciliados[['Data', 'Historico', 'Valor_Absoluto', 'fornecedor', 'categoria']].copy()
                                view_ok.columns = ['📅 Data', '🏦 Histórico (Banco)', '💵 Valor', '🛒 Fornecedor (Sistema)', '📂 Categoria (Sistema)']
                                view_ok['📅 Data'] = pd.to_datetime(view_ok['📅 Data']).dt.strftime('%d/%m/%Y')
                                st.dataframe(view_ok, use_container_width=True, column_config={"💵 Valor": st.column_config.NumberColumn(format="R$ %.2f")}, hide_index=True)
                            else:
                                st.error("Nenhum lançamento foi conciliado. (Talvez o arquivo anexado não contemple os dias das despesas lançadas).")
                    
                    else:
                        st.warning("O arquivo OFX parece estar vazio ou não possui transações em um formato reconhecível.")

                except Exception as e:
                    st.error(f"Erro ao processar o arquivo OFX. Detalhe técnico: {e}")

    # --- ABA: CONFIGURAÇÕES ---
    elif menu == "Configurações":
        st.header("⚙️ Configurações")
        tab_fornecedores, tab_categorias, tab_outros = st.tabs(["🏭 Fornecedores", "📂 Classificações", "Outros"])
        
        with tab_fornecedores:
            st.subheader("Gerenciar Fornecedores")
            st.info("Edite os nomes e dados de acesso. Para facilitar os lançamentos, vincule uma 'Classificação Padrão' aos fornecedores mais recorrentes.")
            df_fornecedores = carregar_fornecedores_df()
            lista_cats_config = carregar_lista_categorias()
            
            df_editado = st.data_editor(
                df_fornecedores,
                num_rows="dynamic", 
                column_config={
                    "nome": st.column_config.TextColumn("Nome do Fornecedor", required=True),
                    "cnpj": st.column_config.TextColumn("CNPJ"),
                    "telefone": st.column_config.TextColumn("Telefone"),
                    "login_app": st.column_config.TextColumn("Login App"),
                    "senha_app": st.column_config.TextColumn("Senha App"),
                    "categoria_padrao": st.column_config.SelectboxColumn("Classificação Padrão (Auto-preenchimento)", options=[""] + lista_cats_config)
                },
                use_container_width=True,
                hide_index=True
            )
            if st.button("💾 Salvar Alterações nos Fornecedores"):
                salvar_tabela_fornecedores(df_editado)
                st.success("Lista de fornecedores atualizada com sucesso!")
                st.cache_data.clear()
                st.rerun()
                
        with tab_categorias:
            st.subheader("Gerenciar Classificações (Categorias)")
            st.info("Edite ou adicione novos nomes de classificação. Clique em 'Salvar Alterações' para confirmar.")
            df_categorias = carregar_categorias_df()
            df_cat_editado = st.data_editor(
                df_categorias,
                num_rows="dynamic", 
                column_config={
                    "nome": st.column_config.TextColumn("Nome da Classificação", required=True)
                },
                use_container_width=True,
                hide_index=True
            )
            if st.button("💾 Salvar Alterações nas Classificações"):
                salvar_tabela_categorias(df_cat_editado)
                st.success("Lista de classificações atualizada com sucesso!")
                st.cache_data.clear()
                st.rerun()
