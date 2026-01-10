import streamlit as st
import pandas as pd
from datetime import datetime
from streamlit_gsheets import GSheetsConnection

# --- CONFIGURAÇÕES INICIAIS ---
st.set_page_config(page_title="Sistema Mercadinho", layout="wide")

# Lista de Categorias
CATEGORIAS = [
    "Mercadoria", "Frete", "Energia", "Comissão", "Manutenção", "Combustível",
    "Salário", "13° Salário", "Férias", "Simples Nacional", "INSS", "FGTS",
    "Internet", "Celular", "Locação", "Tarifa Bancária",
    "Integralização de Capital em Banco", "Cesta de Relacionamento de Banco",
    "Cartão de Crédito", "Empréstimo", "Consórcio", "Sistemas", "Outros"
]

# Dicionário de Meses
MESES_PT = {
    1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril", 5: "Maio", 6: "Junho",
    7: "Julho", 8: "Agosto", 9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro"
}
# Inverte para facilitar busca (Nome -> Número)
MESES_PT_INV = {v: k for k, v in MESES_PT.items()}

# --- CONEXÃO COM O GOOGLE SHEETS ---
conn = st.connection("gsheets", type=GSheetsConnection)

def carregar_dados():
    try:
        return conn.read(worksheet="lancamentos", ttl=0)
    except:
        return pd.DataFrame()

def carregar_fornecedores_df():
    try:
        df = conn.read(worksheet="fornecedores", ttl=0)
        if 'nome' not in df.columns:
            df['nome'] = pd.Series(dtype='str')
        if 'cnpj' not in df.columns:
            df['cnpj'] = pd.Series(dtype='str')
        df = df.fillna("")
        df = df.astype(str)
        return df
    except:
        return pd.DataFrame(columns=['nome', 'cnpj'])

def carregar_lista_nomes_fornecedores():
    df = carregar_fornecedores_df()
    return df['nome'].dropna().unique().tolist()

def salvar_fornecedor_rapido(novo_nome):
    try:
        df = carregar_fornecedores_df()
        if novo_nome and novo_nome not in df['nome'].values:
            novo_registro = pd.DataFrame([{"nome": novo_nome, "cnpj": ""}])
            df_atualizado = pd.concat([df, novo_registro], ignore_index=True)
            conn.update(worksheet="fornecedores", data=df_atualizado)
    except:
        novo_registro = pd.DataFrame([{"nome": novo_nome, "cnpj": ""}])
        conn.update(worksheet="fornecedores", data=novo_registro)

def salvar_tabela_fornecedores(df_editado):
    conn.update(worksheet="fornecedores", data=df_editado)

def salvar_lancamento(dados):
    try:
        df = conn.read(worksheet="lancamentos", ttl=0)
        novo_df = pd.DataFrame([dados])
        df_atualizado = pd.concat([df, novo_df], ignore_index=True)
        conn.update(worksheet="lancamentos", data=df_atualizado)
    except:
        novo_df = pd.DataFrame([dados])
        conn.update(worksheet="lancamentos", data=novo_df)

def gerar_lista_anos():
    ano_atual = datetime.now().year
    # Gera lista de 2025 até o ano atual + 2 anos
    return [str(ano) for ano in range(2025, ano_atual + 3)]

# --- TELA DE LOGIN ---
def check_password():
    if "password_correct" not in st.session_state:
        st.session_state["password_correct"] = False

    if st.session_state["password_correct"]:
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
                st.rerun()
            else:
                st.error("Dados incorretos.")
    return False

# --- INTERFACE PRINCIPAL ---
if check_password():
    st.sidebar.title("Menu")
    menu = st.sidebar.radio("Navegar", ["Lançar Despesa", "Lançar Receita", "Relatórios", "Configurações"])

    # --- ABA: LANÇAR DESPESA ---
    if menu == "Lançar Despesa":
        st.header("📉 Nova Despesa")
        
        # Lógica para definir os valores padrões (Default)
        # Padrão Inicial: Mês e Ano atuais
        mes_atual_nome = MESES_PT[datetime.now().month]
        ano_atual_str = str(datetime.now().year)
        
        idx_mes = list(MESES_PT.values()).index(mes_atual_nome)
        lista_anos = gerar_lista_anos()
        idx_ano = lista_anos.index(ano_atual_str) if ano_atual_str in lista_anos else 0

        # Verifica se o usuário marcou a opção de repetir
        usar_anterior = st.checkbox("Mesmo ano e mês de competência da despesa salva anteriormente?", 
                                    key="check_repetir_comp",
                                    disabled="memoria_mes" not in st.session_state) # Desabilita se não tiver memória
        
        if usar_anterior and "memoria_mes" in st.session_state:
            # Sobrescreve os índices com o que está na memória
            try:
                idx_mes = list(MESES_PT.values()).index(st.session_state["memoria_mes"])
                if st.session_state["memoria_ano"] in lista_anos:
                    idx_ano = lista_anos.index(st.session_state["memoria_ano"])
            except:
                pass # Se der erro, mantem o atual

        col1, col2 = st.columns(2)
        
        with col1:
            valor = st.number_input("Valor Total (R$)", min_value=0.01, format="%.2f", key="val_desp")
            data_liq = st.date_input("Data de Liquidação (Pagamento)", format="DD/MM/YYYY", key="data_liq_desp")
            
            # --- NOVOS CAMPOS SEPARADOS ---
            c_mes, c_ano = st.columns(2)
            with c_mes:
                mes_selecionado = st.selectbox("Mês de Competência", list(MESES_PT.values()), index=idx_mes, key="sel_mes_comp")
            with c_ano:
                ano_selecionado = st.selectbox("Ano de Competência", lista_anos, index=idx_ano, key="sel_ano_comp")
            # ------------------------------

            status = st.selectbox("Status", ["Pago", "A Pagar"], key="status_desp")
        
        with col2:
            lista_fornecedores = carregar_lista_nomes_fornecedores()
            usar_novo_fornecedor = st.checkbox("Cadastrar Novo Fornecedor?", key="check_novo_forn")
            
            if usar_novo_fornecedor:
                fornecedor = st.text_input("Digite o nome do novo fornecedor", key="txt_novo_forn")
            else:
                fornecedor = st.selectbox("Selecione o Fornecedor", [""] + lista_fornecedores, key="sel_forn")
            
            categoria = st.selectbox("Classificação", CATEGORIAS, key="cat_desp")
            obs = st.text_area("Observação", key="obs_desp")

        if st.button("💾 Salvar Despesa"):
            if not fornecedor:
                st.warning("Preencha o fornecedor.")
            else:
                if usar_novo_fornecedor:
                    salvar_fornecedor_rapido(fornecedor)
                
                # Monta a data para o banco (YYYY-MM-01)
                mes_num = MESES_PT_INV[mes_selecionado]
                competencia_formatada = f"{ano_selecionado}-{mes_num:02d}"

                dados = {
                    "data_registro": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "tipo": "Despesa",
                    "valor": valor,
                    "fornecedor": fornecedor,
                    "data_liquidacao": data_liq.strftime("%Y-%m-%d"),
                    "competencia": competencia_formatada,
                    "status": status,
                    "categoria": categoria,
                    "observacao": obs
                }
                salvar_lancamento(dados)
                st.success("Despesa registrada com sucesso!")
                
                # --- SALVA NA MEMÓRIA ---
                st.session_state["memoria_mes"] = mes_selecionado
                st.session_state["memoria_ano"] = ano_selecionado

                # --- LIMPEZA DOS CAMPOS ---
                # Removemos as chaves (menos a memória)
                chaves_para_limpar = ["val_desp", "data_liq_desp", "status_desp", "sel_mes_comp", "sel_ano_comp",
                                      "check_novo_forn", "txt_novo_forn", "sel_forn", "cat_desp", "obs_desp", "check_repetir_comp"]
                for chave in chaves_para_limpar:
                    if chave in st.session_state:
                        del st.session_state[chave]
                
                st.cache_data.clear()
                st.rerun()

    # --- ABA: LANÇAR RECEITA ---
    elif menu == "Lançar Receita":
        st.header("📈 Nova Receita")
        
        # Apliquei a mesma lógica de lista separada para Receita também
        mes_atual_nome = MESES_PT[datetime.now().month]
        ano_atual_str = str(datetime.now().year)
        idx_mes = list(MESES_PT.values()).index(mes_atual_nome)
        lista_anos = gerar_lista_anos()

        with st.container():
            valor = st.number_input("Valor Receita (R$)", min_value=0.01, format="%.2f", key="val_rec")
            data_liq = st.date_input("Data Recebimento", format="DD/MM/YYYY", key="data_rec")
            
            c_mes, c_ano = st.columns(2)
            with c_mes:
                mes_rec = st.selectbox("Mês Competência", list(MESES_PT.values()), index=idx_mes, key="mes_rec")
            with c_ano:
                ano_rec = st.selectbox("Ano Competência", lista_anos, key="ano_rec")

            obs = st.text_area("Observação", key="obs_rec")
            
            if st.button("💾 Salvar Receita"):
                mes_num = MESES_PT_INV[mes_rec]
                comp_formatada = f"{ano_rec}-{mes_num:02d}"

                dados = {
                    "data_registro": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "tipo": "Receita",
                    "valor": valor,
                    "fornecedor": "Cliente Final",
                    "data_liquidacao": data_liq.strftime("%Y-%m-%d"),
                    "competencia": comp_formatada,
                    "status": "Recebido",
                    "categoria": "Vendas",
                    "observacao": obs
                }
                salvar_lancamento(dados)
                st.success("Receita registrada!")
                
                chaves_rec = ["val_rec", "data_rec", "mes_rec", "ano_rec", "obs_rec"]
                for chave in chaves_rec:
                    if chave in st.session_state:
                        del st.session_state[chave]
                
                st.cache_data.clear()
                st.rerun()

    # ---
