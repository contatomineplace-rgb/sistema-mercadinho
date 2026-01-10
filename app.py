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
        
        # 1. LÓGICA (Calcula os índices antes de desenhar)
        mes_atual_nome = MESES_PT[datetime.now().month]
        ano_atual_str = str(datetime.now().year)
        
        idx_mes = list(MESES_PT.values()).index(mes_atual_nome)
        lista_anos = gerar_lista_anos()
        idx_ano = lista_anos.index(ano_atual_str) if ano_atual_str in lista_anos else 0

        # Verifica se o checkbox (que será desenhado lá embaixo) está marcado no Session State
        usar_anterior = st.session_state.get("check_repetir_comp", False)
        
        if usar_anterior and "memoria_mes" in st.session_state:
            try:
                idx_mes = list(MESES_PT.values()).index(st.session_state["memoria_mes"])
                if st.session_state["memoria_ano"] in lista_anos:
                    idx_ano = lista_anos.index(st.session_state["memoria_ano"])
            except:
                pass 

        # 2. DESENHO DA TELA
        col1, col2 = st.columns(2)
        
        with col1:
            valor = st.number_input("Valor Total (R$)", min_value=0.01, format="%.2f", key="val_desp")
            data_liq = st.date_input("Data de Liquidação (Pagamento)", format="DD/MM/YYYY", key="data_liq_desp")
            
            # Colunas Mês e Ano
            c_mes, c_ano = st.columns(2)
            with c_mes:
                mes_selecionado = st.selectbox("Mês de Competência", list(MESES_PT.values()), index=idx_mes, key="sel_mes_comp")
            with c_ano:
                ano_selecionado = st.selectbox("Ano de Competência", lista_anos, index=idx_ano, key="sel_ano_comp")
            
            # --- CHECKBOX AGORA ESTÁ AQUI EMBAIXO ---
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
            obs = st.text_area("Observação", key="obs_desp")

        if st.button("💾 Salvar Despesa"):
            if not fornecedor:
                st.warning("Preencha o fornecedor.")
            else:
                if usar_novo_fornecedor:
                    salvar_fornecedor_rapido(fornecedor)
                
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
                
                # Salva na memória
                st.session_state["memoria_mes"] = mes_selecionado
                st.session_state["memoria_ano"] = ano_selecionado

                # Limpeza (Mantém check_repetir_comp para o usuário decidir se desmarca ou não)
                chaves_para_limpar = ["val_desp", "data_liq_desp", "status_desp", "sel_mes_comp", "sel_ano_comp",
                                      "check_novo_forn", "txt_novo_forn", "sel_forn", "cat_desp", "obs_desp"]
                for chave in chaves_para_limpar:
                    if chave in st.session_state:
                        del st.session_state[chave]
                
                st.cache_data.clear()
                st.rerun()

    # --- ABA: LANÇAR RECEITA ---
    elif menu == "Lançar Receita":
        st.header("📈 Nova Receita")
        
        mes_atual_nome = MESES_PT[datetime.now().month]
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
                comps_unicas = sorted(df['competencia'].unique())
                filtro_comp = st.sidebar.multiselect("Filtrar Competência (Ano-Mês)", comps_unicas)
            
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
            st.dataframe(
                df_view.sort_values("data_liquidacao", ascending=False), 
                use_container_width=True,
                column_config={
                    "data_liquidacao": st.column_config.DateColumn("Data Liq.", format="DD/MM/YYYY")
                }
            )
        else:
            st.info("Nenhum dado lançado ainda.")

    # --- ABA: CONFIGURAÇÕES ---
    elif menu == "Configurações":
        st.header("⚙️ Configurações")
        
        tab_fornecedores, tab_outros = st.tabs(["🏭 Fornecedores", "Outros"])
        
        with tab_fornecedores:
            st.subheader("Gerenciar Fornecedores")
            st.info("Edite os nomes, adicione CNPJs ou exclua linhas. Clique em 'Salvar Alterações' para confirmar.")
            
            df_fornecedores = carregar_fornecedores_df()
            
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
