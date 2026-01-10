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
        
        # Garante colunas necessárias
        colunas_necessarias = ['nome', 'cnpj', 'telefone', 'login_app', 'senha_app']
        for col in colunas_necessarias:
            if col not in df.columns:
                df[col] = pd.Series(dtype='str')
                
        df = df.fillna("")
        df = df.astype(str)
        return df
    except:
        return pd.DataFrame(columns=['nome', 'cnpj', 'telefone', 'login_app', 'senha_app'])

def carregar_lista_nomes_fornecedores():
    df = carregar_fornecedores_df()
    return df['nome'].dropna().unique().tolist()

def salvar_fornecedor_rapido(novo_nome):
    try:
        df = carregar_fornecedores_df()
        if novo_nome and novo_nome not in df['nome'].values:
            novo_registro = pd.DataFrame([{
                "nome": novo_nome, "cnpj": "", "telefone": "", "login_app": "", "senha_app": ""
            }])
            df_atualizado = pd.concat([df, novo_registro], ignore_index=True)
            conn.update(worksheet="fornecedores", data=df_atualizado)
    except:
        novo_registro = pd.DataFrame([{
            "nome": novo_nome, "cnpj": "", "telefone": "", "login_app": "", "senha_app": ""
        }])
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
        
        # Padrões iniciais (Mês/Ano Atual)
        mes_atual_nome = MESES_PT[datetime.now().month]
        ano_atual_str = str(datetime.now().year)
        
        idx_mes = list(MESES_PT.values()).index(mes_atual_nome)
        lista_anos = gerar_lista_anos()
        idx_ano = lista_anos.index(ano_atual_str) if ano_atual_str in lista_anos else 0

        # Lógica de memória (Checkbox)
        usar_anterior = st.session_state.get("check_repetir_comp", False)
        
        # Se o checkbox estiver marcado E tivermos memória, sobrescreve os índices
        if usar_anterior and "memoria_mes" in st.session_state:
            try:
                if st.session_state["memoria_mes"] in list(MESES_PT.values()):
                    idx_mes = list(MESES_PT.values()).index(st.session_state["memoria_mes"])
                if st.session_state["memoria_ano"] in lista_anos:
                    idx_ano = lista_anos.index(st.session_state["memoria_ano"])
            except:
                pass 

        col1, col2 = st.columns(2)
        
        with col1:
            # key=... é o segredo para poder limpar o campo depois
            valor = st.number_input("Valor Total (R$)", min_value=0.01, format="%.2f", key="val_desp")
            data_liq = st.date_input("Data de Liquidação (Pagamento)", format="DD/MM/YYYY", key="data_liq_desp")
            
            c_mes, c_ano = st.columns(2)
            with c_mes:
                mes_selecionado = st.selectbox("Mês de Competência", list(MESES_PT.values()), index=idx_mes, key="sel_mes_comp")
            with c_ano:
                ano_selecionado = st.selectbox("Ano de Competência", lista_anos, index=idx_ano, key="sel_ano_comp")
            
            # Checkbox de memória
            st.checkbox("Mesmo ano e mês de competência da despesa salva anteriormente?", 
                        key="check_repetir_comp",
                        disabled="memoria_mes" not in st.session_state) 

            status = st.selectbox("Status", ["Pago", "A Pagar"], key="status_desp")
        
        with col2:
            lista_fornecedores = carregar_lista_nomes_fornecedores()
            usar_novo_fornecedor = st.checkbox("Cadastrar Novo Fornecedor?", key="check_novo_forn")
            
            if usar_novo_fornecedor:
                fornecedor = st.text_input("Digite o nome do novo fornecedor", key="txt_novo_forn")
            else:
                fornecedor = st.selectbox("Selecione o Fornecedor", [""] + lista_fornecedores, key="sel_forn")
            
            categoria = st.selectbox("Classificação", CATEGORIAS, key="cat_desp")
