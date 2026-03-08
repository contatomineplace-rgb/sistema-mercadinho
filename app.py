import streamlit as st
import pandas as pd
import time
import hashlib
import calendar
from datetime import datetime, date
import re
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
        colunas_necessarias = ['nome', 'cnpj', 'telefone', 'login_app', 'senha_app']
        for col in colunas_necessarias:
            if col not in df.columns:
                df[col] = pd.Series(dtype='str')
        df = df.fillna("")
        df = df.astype(str)
        return df
    except Exception as e:
        return pd.DataFrame(columns=['nome', 'cnpj', 'telefone', 'login_app', 'senha_app'])

def carregar_lista_nomes_fornecedores():
    df = carregar_fornecedores_df()
    return df['nome'].dropna().unique().tolist()

def salvar_fornecedor_rapido(novo_nome):
    try:
        df = conn.read(worksheet="fornecedores", ttl=0)
        if novo_nome and novo_nome.strip().lower() not in df['nome'].dropna().str.lower().values:
            novo_registro = pd.DataFrame([{"nome": novo_nome, "cnpj": "", "telefone": "", "login_app": "", "senha_app": ""}])
            df_atualizado = pd.concat([df, novo_registro], ignore_index=True)
            conn.update(worksheet="fornecedores", data=df_atualizado)
    except:
        novo_registro = pd.DataFrame([{"nome": novo_nome, "cnpj": "", "telefone": "", "login_app": "", "senha_app": ""}])
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
                if usar_novo_fornecedor: fornecedor = st.text_input("Digite o nome do novo fornecedor", key="txt_novo_forn")
                else: fornecedor = st.selectbox("Selecione o Fornecedor", [""] + lista_fornecedores, index=None, placeholder="Selecione o Fornecedor", key="sel_forn")
                
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
            st.info("💡 **Dica:** Copie e cole do Excel. O valor será formatado automaticamente na tabela.")
            
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
            
            linhas_iniciais = [{
                "valor": None, "data_liquidacao": None, "mes_competencia": None, "ano_competencia": None,
                "fornecedor": None, "categoria": None, "observacao": "", "status": None
            } for _ in range(10)]
            df_template = pd.DataFrame(linhas_iniciais)

            lote_editado = st.data_editor(
                df_template,
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
            6. **`categoria`**: Classificação (ex: Mercadoria, Celular, etc - novas serão cadastradas automaticamente).
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
                                
                                lista_dados_finais = []

                                for index, row in df_import.iterrows():
                                    if pd.isna(row.get('fornecedor')) or pd.isna(row.get('valor')):
                                        continue 

                                    nome_forn = str(row['fornecedor']).strip()
                                    if nome_forn.lower() not in nomes_forn_existentes:
                                        salvar_fornecedor_rapido(nome_forn)
                                        nomes_forn_existentes.add(nome_forn.lower())

                                    cat_str = str(row.get('categoria', 'Outros')).strip()
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
                df_dados['data_liquidacao'] = pd.to_datetime(df_dados['data_liquidacao'])
                
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
        st.header("📈 Nova Receita")
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

    # --- ABA: RELATÓRIOS ---
    elif menu == "Relatórios":
        st.header("📊 Relatórios Gerenciais")
        if st.button("🔄 Atualizar Dados"):
            st.cache_data.clear()
            st.rerun()

        df = carregar_dados()
        
        if not df.empty:
            df['valor'] = pd.to_numeric(df['valor'])
            df['data_liquidacao'] = pd.to_datetime(df['data_liquidacao'])
            df['ano_comp'] = df['competencia'].str[:4]
            df['mes_comp_num'] = df['competencia'].str[5:].astype(int)
            df['mes_comp_nome'] = df['mes_comp_num'].map(MESES_PT)

            # Abas para separar o Dashboard do Calendário
            tab_dash, tab_calendario = st.tabs(["📊 Dashboard e Extrato", "📅 Calendário de Vencimentos (A Pagar)"])

            with tab_dash:
                st.sidebar.markdown("### Filtros do Relatório")
                filtro_tipo = st.sidebar.multiselect("Tipo", options=["Receita", "Despesa"], default=["Receita", "Despesa"])
                
                categorias_disp = sorted(df['categoria'].dropna().unique())
                filtro_categoria = st.sidebar.multiselect("Categoria", options=categorias_disp, default=categorias_disp)
                
                if 'status' in df.columns:
                    status_disp = sorted(df['status'].dropna().unique())
                else:
                    status_disp = []
                filtro_status = st.sidebar.multiselect("Status", options=status_disp, default=status_disp)
                
                if 'fornecedor' in df.columns:
                    fornecedores_disp = sorted(df['fornecedor'].dropna().astype(str).unique())
                else:
                    fornecedores_disp = []
                filtro_fornecedor = st.sidebar.multiselect("Fornecedor", options=fornecedores_disp, default=fornecedores_disp)
                
                anos_disp = sorted(df['ano_comp'].unique())
                filtro_ano = st.sidebar.multiselect("Ano de Competência", options=anos_disp, default=anos_disp)
                meses_disp_nome = [MESES_PT[m] for m in sorted(df['mes_comp_num'].unique())]
                filtro_mes = st.sidebar.multiselect("Mês de Competência", options=meses_disp_nome, default=meses_disp_nome)
                min_date = df['data_liquidacao'].min().date()
                max_date = df['data_liquidacao'].max().date()
                periodo = st.sidebar.date_input("Período (Data Liquidação)", value=(min_date, max_date), min_value=min_date, max_value=max_date)

                df_filtered = df.copy()
                if filtro_tipo: df_filtered = df_filtered[df_filtered['tipo'].isin(filtro_tipo)]
                if filtro_categoria: df_filtered = df_filtered[df_filtered['categoria'].isin(filtro_categoria)]
                if filtro_status: df_filtered = df_filtered[df_filtered['status'].isin(filtro_status)]
                if filtro_fornecedor: df_filtered = df_filtered[df_filtered['fornecedor'].isin(filtro_fornecedor)]
                if filtro_ano: df_filtered = df_filtered[df_filtered['ano_comp'].isin(filtro_ano)]
                if filtro_mes: df_filtered = df_filtered[df_filtered['mes_comp_nome'].isin(filtro_mes)]
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

                # --- NOVO BLOCO: EXTRATO EDITÁVEL ---
                st.subheader("Extrato Detalhado Interativo")
                st.markdown("Marque a caixa **'Editar?'** ao lado de qualquer lançamento para alterar os seus dados ou excluí-lo.")
                
                df_extrato_view = df_filtered.copy()
                df_extrato_view.insert(0, "✏️ Editar", False)
                df_sorted = df_extrato_view.sort_values("data_liquidacao", ascending=False)
                
                colunas_desabilitadas = df_sorted.columns.tolist()
                colunas_desabilitadas.remove("✏️ Editar")
                
                editor_extrato = st.data_editor(
                    df_sorted, 
                    use_container_width=True,
                    hide_index=True,
                    disabled=colunas_desabilitadas,
                    column_config={
                        "✏️ Editar": st.column_config.CheckboxColumn("Editar?", required=True),
                        "data_liquidacao": st.column_config.DateColumn("Data Liq.", format="DD/MM/YYYY"),
                        "valor": st.column_config.NumberColumn("Valor", format="R$ %.2f"),
                        "ano_comp": None, 
                        "mes_comp_num": None, 
                        "mes_comp_nome": None 
                    }
                )

                linhas_editar = editor_extrato[editor_extrato["✏️ Editar"] == True]

                if not linhas_editar.empty:
                    st.markdown("---")
                    if len(linhas_editar) > 1:
                        st.warning("⚠️ Selecione apenas UM lançamento para editar por vez.")
                    else:
                        idx = linhas_editar.index[0]
                        linha_atual = df_filtered.loc[idx]
                        tipo_lanc = linha_atual['tipo']
                        
                        st.markdown(f"### 📝 Editar Lançamento ({tipo_lanc})")
                        with st.form(key=f"form_edit_relatorio_{idx}"):
                            c_ed1, c_ed2 = st.columns(2)
                            with c_ed1:
                                novo_valor = st.number_input("Valor (R$)", value=float(linha_atual['valor']), min_value=0.0)
                                nova_data = st.date_input("Data", value=pd.to_datetime(linha_atual['data_liquidacao']).date(), format="DD/MM/YYYY")
                                
                                ano_atual = str(linha_atual['competencia'])[:4]
                                mes_atual_num = int(str(linha_atual['competencia'])[5:7])
                                mes_atual_nome = MESES_PT[mes_atual_num]
                                
                                novo_mes = st.selectbox("Mês Comp.", list(MESES_PT.values()), index=list(MESES_PT.values()).index(mes_atual_nome))
                                novo_ano = st.selectbox("Ano Comp.", gerar_lista_anos(), index=gerar_lista_anos().index(ano_atual))
                                
                                status_atual = str(linha_atual.get('status', 'Pago' if tipo_lanc == 'Despesa' else 'Recebido'))
                                opcoes_status = ["Pago", "A Pagar"] if tipo_lanc == 'Despesa' else ["Recebido", "A Receber"]
                                if status_atual not in opcoes_status:
                                    opcoes_status.append(status_atual)
                                novo_status = st.selectbox("Status", opcoes_status, index=opcoes_status.index(status_atual))

                            with c_ed2:
                                lista_forn = carregar_lista_nomes_fornecedores()
                                forn_atual = str(linha_atual.get('fornecedor', ''))
                                if forn_atual and forn_atual not in lista_forn:
                                    lista_forn = [forn_atual] + lista_forn
                                novo_fornecedor = st.selectbox("Fornecedor/Cliente", lista_forn, index=lista_forn.index(forn_atual) if forn_atual in lista_forn else 0)
                                
                                lista_cats = carregar_lista_categorias()
                                cat_atual = str(linha_atual.get('categoria', ''))
                                if cat_atual and cat_atual not in lista_cats:
                                    lista_cats = [cat_atual] + lista_cats
                                nova_categoria = st.selectbox("Categoria", lista_cats, index=lista_cats.index(cat_atual) if cat_atual in lista_cats else 0)
                                
                                nova_obs = st.text_area("Observação", value=str(linha_atual.get('observacao', '')))

                            col_btn1, col_btn2 = st.columns([1, 1])
                            with col_btn1:
                                submit_edit = st.form_submit_button("💾 Salvar Alterações", type="primary", use_container_width=True)
                            with col_btn2:
                                submit_del = st.form_submit_button("🗑️ Excluir Lançamento", type="secondary", use_container_width=True)
                                
                            if submit_edit:
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
                                st.success("Lançamento atualizado com sucesso!")
                                time.sleep(2)
                                st.cache_data.clear()
                                st.rerun()
                                
                            if submit_del:
                                excluir_lancamentos([idx])
                                st.success("Lançamento excluído com sucesso!")
                                time.sleep(2)
                                st.cache_data.clear()
                                st.rerun()
                # -----------------------------------------------

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
                                df_dia_view = df_dia[['fornecedor', 'categoria', 'status', 'valor', 'observacao']].copy()
                                st.dataframe(
                                    df_dia_view,
                                    use_container_width=True,
                                    column_config={
                                        "valor": st.column_config.NumberColumn("Valor (R$)", format="R$ %.2f")
                                    },
                                    hide_index=True
                                )
                                
                                total_dia = df_dia['valor'].sum()
                                total_pendente = df_dia[df_dia['status'] == 'A Pagar']['valor'].sum()
                                
                                c1, c2 = st.columns(2)
                                c1.metric("Total Agendado no Dia", f"R$ {total_dia:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
                                c2.metric("Total A Pagar (Pendente)", f"R$ {total_pendente:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."), delta_color="inverse")
                            else:
                                st.success("Nenhuma despesa lançada para este dia! 🎉")

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

                        df_sistema = carregar_dados()
                        df_sistema = df_sistema[df_sistema['tipo'] == 'Despesa'].copy()
                        df_sistema['valor'] = pd.to_numeric(df_sistema['valor'])
                        
                        df_sistema['CHAVE_DATA'] = pd.to_datetime(df_sistema['data_liquidacao']).dt.date.astype(str).str.strip()
                        df_sistema['CHAVE_VALOR'] = df_sistema['valor'].apply(lambda x: "{:.2f}".format(x))

                        df_conciliados = pd.merge(df_ext_saidas, df_sistema, on=['CHAVE_DATA', 'CHAVE_VALOR'], how='inner')
                        chaves_conciliadas = df_conciliados['CHAVE_DATA'] + df_conciliados['CHAVE_VALOR']
                        df_ext_saidas['CHAVE_UNICA'] = df_ext_saidas['CHAVE_DATA'] + df_ext_saidas['CHAVE_VALOR']
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
            st.info("Edite os nomes e dados de acesso. Clique em 'Salvar Alterações' para confirmar.")
            df_fornecedores = carregar_fornecedores_df()
            df_editado = st.data_editor(
                df_fornecedores,
                num_rows="dynamic", 
                column_config={
                    "nome": st.column_config.TextColumn("Nome do Fornecedor", required=True),
                    "cnpj": st.column_config.TextColumn("CNPJ"),
                    "telefone": st.column_config.TextColumn("Telefone"),
                    "login_app": st.column_config.TextColumn("Login App"),
                    "senha_app": st.column_config.TextColumn("Senha App")
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
