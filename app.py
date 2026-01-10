import streamlit as st
import pandas as pd
from datetime import datetime
from streamlit_gsheets import GSheetsConnection

# --- CONFIGURAÇÕES INICIAIS ---
st.set_page_config(page_title="Sistema Mercadinho", layout="wide")

# Lista de Categorias solicitada
CATEGORIAS = [
    "Mercadoria", "Frete", "Energia", "Comissão", "Manutenção", "Combustível",
    "Salário", "13° Salário", "Férias", "Simples Nacional", "INSS", "FGTS",
    "Internet", "Celular", "Locação", "Tarifa Bancária",
    "Integralização de Capital em Banco", "Cesta de Relacionamento de Banco",
    "Cartão de Crédito", "Empréstimo", "Consórcio", "Sistemas", "Outros"
]

# --- CONEXÃO COM O GOOGLE SHEETS ---
conn = st.connection("gsheets", type=GSheetsConnection)

def carregar_dados():
    # Carrega a aba de lançamentos
    return conn.read(worksheet="lancamentos", ttl=0)

def carregar_fornecedores():
    # Carrega a aba de fornecedores
    df = conn.read(worksheet="fornecedores", ttl=0)
    return df['nome'].dropna().unique().tolist()

def salvar_fornecedor(novo_nome):
    df = conn.read(worksheet="fornecedores", ttl=0)
    if novo_nome not in df['nome'].values:
        novo_registro = pd.DataFrame([{"nome": novo_nome}])
        df_atualizado = pd.concat([df, novo_registro], ignore_index=True)
        conn.update(worksheet="fornecedores", data=df_atualizado)

def salvar_lancamento(dados):
    df = conn.read(worksheet="lancamentos", ttl=0)
    novo_df = pd.DataFrame([dados])
    df_atualizado = pd.concat([df, novo_df], ignore_index=True)
    conn.update(worksheet="lancamentos", data=df_atualizado)

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
            # Verifica credenciais nos segredos do sistema
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
    menu = st.sidebar.radio("Navegar", ["Lançar Despesa", "Lançar Receita", "Relatórios"])

    # --- ABA: LANÇAR DESPESA ---
    if menu == "Lançar Despesa":
        st.header("📉 Nova Despesa")
        
        with st.form("form_despesa", clear_on_submit=True):
            col1, col2 = st.columns(2)
            
            with col1:
                valor = st.number_input("Valor Total (R$)", min_value=0.01, format="%.2f")
                data_liq = st.date_input("Data de Liquidação (Pagamento)")
                competencia = st.date_input("Mês de Competência", value=datetime.today())
                status = st.selectbox("Status", ["Pago", "A Pagar"])
            
            with col2:
                # Lógica de Fornecedor
                lista_fornecedores = carregar_fornecedores()
                usar_novo_fornecedor = st.checkbox("Cadastrar Novo Fornecedor?")
                
                if usar_novo_fornecedor:
                    fornecedor = st.text_input("Digite o nome do novo fornecedor")
                else:
                    fornecedor = st.selectbox("Selecione o Fornecedor", [""] + lista_fornecedores)
                
                categoria = st.selectbox("Classificação", CATEGORIAS)
                obs = st.text_area("Observação")

            submitted = st.form_submit_button("💾 Salvar Despesa")
            
            if submitted:
                if not fornecedor:
                    st.warning("Preencha o fornecedor.")
                else:
                    # Salva fornecedor se for novo
                    if usar_novo_fornecedor:
                        salvar_fornecedor(fornecedor)
                    
                    # Prepara dados
                    dados = {
                        "data_registro": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "tipo": "Despesa",
                        "valor": valor,
                        "fornecedor": fornecedor,
                        "data_liquidacao": data_liq.strftime("%Y-%m-%d"),
                        "competencia": competencia.strftime("%Y-%m"), # Salva apenas Ano-Mês
                        "status": status,
                        "categoria": categoria,
                        "observacao": obs
                    }
                    salvar_lancamento(dados)
                    st.success("Despesa registrada com sucesso!")

    # --- ABA: LANÇAR RECEITA ---
    elif menu == "Lançar Receita":
        st.header("📈 Nova Receita")
        with st.form("form_receita", clear_on_submit=True):
            valor = st.number_input("Valor Receita (R$)", min_value=0.01, format="%.2f")
            data_liq = st.date_input("Data Recebimento")
            competencia = st.date_input("Competência")
            obs = st.text_area("Observação")
            
            if st.form_submit_button("💾 Salvar Receita"):
                dados = {
                    "data_registro": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "tipo": "Receita",
                    "valor": valor,
                    "fornecedor": "Cliente Final", # Padrão para receitas
                    "data_liquidacao": data_liq.strftime("%Y-%m-%d"),
                    "competencia": competencia.strftime("%Y-%m"),
                    "status": "Recebido",
                    "categoria": "Vendas",
                    "observacao": obs
                }
                salvar_lancamento(dados)
                st.success("Receita registrada!")

    # --- ABA: RELATÓRIOS ---
    elif menu == "Relatórios":
        st.header("📊 Relatórios Gerenciais")
        if st.button("🔄 Atualizar Dados"):
            st.cache_data.clear()
            st.rerun()

        df = carregar_dados()
        
        if not df.empty:
            # Garantir tipos de dados corretos
            df['valor'] = pd.to_numeric(df['valor'])
            df['data_liquidacao'] = pd.to_datetime(df['data_liquidacao'])
            
            # Filtros laterais
            st.sidebar.markdown("---")
            st.sidebar.subheader("Filtros")
            
            filtro_comp = st.sidebar.multiselect("Filtrar Competência", df['competencia'].unique())
            filtro_cat = st.sidebar.multiselect("Filtrar Categoria", df['categoria'].unique())
            
            df_view = df.copy()
            if filtro_comp:
                df_view = df_view[df_view['competencia'].isin(filtro_comp)]
            if filtro_cat:
                df_view = df_view[df_view['categoria'].isin(filtro_cat)]

            # Cards Resumo
            total_rec = df_view[df_view['tipo'] == 'Receita']['valor'].sum()
            total_desp = df_view[df_view['tipo'] == 'Despesa']['valor'].sum()
            saldo = total_rec - total_desp
            
            c1, c2, c3 = st.columns(3)
            c1.metric("Receitas", f"R$ {total_rec:,.2f}")
            c2.metric("Despesas", f"R$ {total_desp:,.2f}", delta_color="inverse")
            c3.metric("Resultado", f"R$ {saldo:,.2f}")

            # Gráficos
            st.subheader("Despesas por Categoria")
            df_despesas = df_view[df_view['tipo'] == 'Despesa']
            if not df_despesas.empty:
                st.bar_chart(df_despesas.groupby("categoria")["valor"].sum())

            st.subheader("Extrato Detalhado")
            st.dataframe(df_view.sort_values("data_liquidacao", ascending=False), use_container_width=True)
        else:
            st.info("Nenhum dado lançado ainda.")