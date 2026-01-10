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

# --- CONEXÃO COM O GOOGLE SHEETS ---
conn = st.connection("gsheets", type=GSheetsConnection)

def carregar_dados():
    try:
        return conn.read(worksheet="lancamentos", ttl=0)
    except:
        return pd.DataFrame()

def carregar_fornecedores_df():
    # Carrega a tabela completa de fornecedores para edição
    try:
        df = conn.read(worksheet="fornecedores", ttl=0)
        
        # 1. Garante que as colunas existem
        if 'nome' not in df.columns:
            df['nome'] = pd.Series(dtype='str')
        if 'cnpj' not in df.columns:
            df['cnpj'] = pd.Series(dtype='str')
            
        # 2. CORREÇÃO DO ERRO: Converte tudo para texto para evitar conflito de tipos
        df = df.fillna("")  # Troca vazios por texto vazio
        df = df.astype(str) # Força tudo a ser texto
        
        return df
    except:
        return pd.DataFrame(columns=['nome', 'cnpj'])

def carregar_lista_nomes_fornecedores():
    # Carrega apenas a lista de nomes para o dropdown
    df = carregar_fornecedores_df()
    return df['nome'].dropna().unique().tolist()

def salvar_fornecedor_rapido(novo_nome):
    # Usado na tela de Despesa (apenas nome)
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
    # Usado na tela de Configurações (salva tudo)
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
        
        col1, col2 = st.columns(2)
        
        with col1:
            valor = st.number_input("Valor Total (R$)", min_value=0.01, format="%.2f")
            data_liq = st.date_input("Data de Liquidação (Pagamento)")
            competencia = st.date_input("Mês de Competência", value=datetime.today())
            status = st.selectbox("Status", ["Pago", "A Pagar"])
        
        with col2:
            lista_fornecedores = carregar_lista_nomes_fornecedores()
            usar_novo_fornecedor = st.checkbox("Cadastrar Novo Fornecedor?")
            
            if usar_novo_fornecedor:
                fornecedor = st.text_input("Digite o nome do novo fornecedor")
            else:
                fornecedor = st.selectbox("Selecione o Fornecedor", [""] + lista_fornecedores)
            
            categoria = st.selectbox("Classificação", CATEGORIAS)
            obs = st.text_area("Observação")

        if st.button("💾 Salvar Despesa"):
            if not fornecedor:
                st.warning("Preencha o fornecedor.")
            else:
                if usar_novo_fornecedor:
                    salvar_fornecedor_rapido(fornecedor)
                
                dados = {
                    "data_registro": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "tipo": "Despesa",
                    "valor": valor,
                    "fornecedor": fornecedor,
                    "data_liquidacao": data_liq.strftime("%Y-%m-%d"),
                    "competencia": competencia.strftime("%Y-%m"),
                    "status": status,
                    "categoria": categoria,
                    "observacao": obs
                }
                salvar_lancamento(dados)
                st.success("Despesa registrada com sucesso!")
                st.cache_data.clear()

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
                    "fornecedor": "Cliente Final",
                    "data_liquidacao": data_liq.strftime("%Y-%m-%d"),
                    "competencia": competencia.strftime("%Y-%m"),
                    "status": "Recebido",
                    "categoria": "Vendas",
                    "observacao": obs
                }
                salvar_lancamento(dados)
                st.success("Receita registrada!")
                st.cache_data.clear()

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
            
            st.sidebar.markdown("---")
            st.sidebar.subheader("Filtros")
            
            colunas_validas = df.columns.tolist()
            filtro_comp = None
            if 'competencia' in colunas_validas:
                filtro_comp = st.sidebar.multiselect("Filtrar Competência", df['competencia'].unique())
            
            filtro_cat = None
            if 'categoria' in colunas_validas:
                filtro_cat = st.sidebar.multiselect("Filtrar Categoria", df['categoria'].unique())
            
            df_view = df.copy()
            if filtro_comp:
                df_view = df_view[df_view['competencia'].isin(filtro_comp)]
            if filtro_cat:
                df_view = df_view[df_view['categoria'].isin(filtro_cat)]

            total_rec = df_view[df_view['tipo'] == 'Receita']['valor'].sum()
            total_desp = df_view[df_view['tipo'] == 'Despesa']['valor'].sum()
            saldo = total_rec - total_desp
            
            c1, c2, c3 = st.columns(3)
            c1.metric("Receitas", f"R$ {total_rec:,.2f}")
            c2.metric("Despesas", f"R$ {total_desp:,.2f}", delta_color="inverse")
            c3.metric("Resultado", f"R$ {saldo:,.2f}")

            st.subheader("Despesas por Categoria")
            df_despesas = df_view[df_view['tipo'] == 'Despesa']
            if not df_despesas.empty:
                st.bar_chart(df_despesas.groupby("categoria")["valor"].sum())

            st.subheader("Extrato Detalhado")
            st.dataframe(df_view.sort_values("data_liquidacao", ascending=False), use_container_width=True)
        else:
            st.info("Nenhum dado lançado ainda.")

    # --- ABA: CONFIGURAÇÕES ---
    elif menu == "Configurações":
        st.header("⚙️ Configurações")
        
        tab_fornecedores, tab_outros = st.tabs(["🏭 Fornecedores", "Outros"])
        
        with tab_fornecedores:
            st.subheader("Gerenciar Fornecedores")
            st.info("Edite os nomes, adicione CNPJs ou exclua linhas. Clique em 'Salvar Alterações' para confirmar.")
            
            # Carrega tabela
            df_fornecedores = carregar_fornecedores_df()
            
            # Editor de Dados
            df_editado = st.data_editor(
                df_fornecedores,
                num_rows="dynamic", 
                column_config={
                    "nome": st.column_config.TextColumn("Nome do Fornecedor", required=True),
                    "cnpj": st.column_config.TextColumn("CNPJ (Opcional)")
                },
                use_container_width=True,
                hide_index=True
            )
            
            if st.button("💾 Salvar Alterações nos Fornecedores"):
                salvar_tabela_fornecedores(df_editado)
                st.success("Lista de fornecedores atualizada com sucesso!")
                st.cache_data.clear()
                st.rerun()
