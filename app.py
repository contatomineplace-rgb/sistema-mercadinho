import streamlit as st
import pandas as pd
import time
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
        df = conn.read(worksheet="lancamentos", ttl=0)
        return df
    except:
        return pd.DataFrame()

def carregar_fornecedores_df():
    try:
        df = conn.read(worksheet="fornecedores", ttl=0)
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
        if novo_nome and novo_nome.strip().lower() not in df['nome'].str.lower().values:
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
        st.header("📉 Gestão de Despesas")
        
        tab_individual, tab_lote, tab_excluir = st.tabs(["📝 Individual", "📚 Despesa em Lote", "🗑️ Excluir Despesa"])

        # === 1. LANÇAMENTO INDIVIDUAL ===
        with tab_individual:
            # --- LIMPEZA: Define como None/Vazio ---
            if "limpar_despesa_agora" in st.session_state:
                st.session_state["val_desp"] = "" # Vazio
                st.session_state["obs_desp"] = ""
                st.session_state["sel_forn"] = None # None
                st.session_state["txt_novo_forn"] = ""
                st.session_state["check_novo_forn"] = False
                
                # Reseta data apenas se não for repetir
                if st.session_state.get("check_repetir_data", False) and "memoria_data_liq" in st.session_state:
                    st.session_state["data_liq_desp"] = st.session_state["memoria_data_liq"]
                else:
                    st.session_state["data_liq_desp"] = None # Data Vazia

                # Reseta competência apenas se não for repetir
                if not st.session_state.get("check_repetir_comp", False):
                    # Removemos as chaves para que o widget reinicie com index=None
                    if "sel_mes_comp" in st.session_state: del st.session_state["sel_mes_comp"]
                    if "sel_ano_comp" in st.session_state: del st.session_state["sel_ano_comp"]
                
                # Reseta outros selects
                if "status_desp" in st.session_state: del st.session_state["status_desp"]
                if "cat_desp" in st.session_state: del st.session_state["cat_desp"]

                del st.session_state["limpar_despesa_agora"]

            # --- PADRÕES INICIAIS (Começa tudo Vazio/None, exceto se tiver memória) ---
            idx_mes = None
            idx_ano = None
            lista_anos = gerar_lista_anos()

            # Memória Competência
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
                # CAMPO VALOR (Inicia vazio)
                valor_str = st.text_input(
                    "Valor Total (R$)", 
                    value="",  # Inicia vazio
                    key="val_desp", 
                    help="Digite o valor (ex: 150,00).",
                    on_change=formatar_input_br,
                    args=("val_desp",)
                )

                # CAMPO DATA (Inicia vazio = None)
                data_liq = st.date_input("Data de Liquidação (Pagamento)", value=None, format="DD/MM/YYYY", key="data_liq_desp")
                
                st.checkbox("Mesma data de liquidação da despesa anterior", key="check_repetir_data", disabled="memoria_data_liq" not in st.session_state, on_change=atualizar_data_liq)
                st.markdown("---") 
                
                c_mes, c_ano = st.columns(2)
                with c_mes: 
                    # index=None inicia com "Selecione..."
                    mes_selecionado = st.selectbox("Mês de Competência", list(MESES_PT.values()), index=idx_mes, placeholder="Selecione o Mês", key="sel_mes_comp")
                with c_ano: 
                    ano_selecionado = st.selectbox("Ano de Competência", lista_anos, index=idx_ano, placeholder="Selecione o Ano", key="sel_ano_comp")
                
                st.checkbox("Mesmo ano e mês de competência da despesa salva anteriormente?", key="check_repetir_comp", disabled="memoria_mes" not in st.session_state) 
                
                status = st.selectbox("Status", ["Pago", "A Pagar"], index=None, placeholder="Selecione o Status", key="status_desp")
            
            with col2:
                lista_fornecedores = carregar_lista_nomes_fornecedores()
                usar_novo_fornecedor = st.checkbox("Cadastrar Novo Fornecedor?", key="check_novo_forn")
                
                if usar_novo_fornecedor: 
                    fornecedor = st.text_input("Digite o nome do novo fornecedor", key="txt_novo_forn")
                else: 
                    fornecedor = st.selectbox("Selecione o Fornecedor", [""] + lista_fornecedores, index=None, placeholder="Selecione o Fornecedor", key="sel_forn")
                
                categoria = st.selectbox("Classificação", CATEGORIAS, index=None, placeholder="Selecione a Categoria", key="cat_desp")
                obs = st.text_area("Observação", key="obs_desp")

            st.markdown("---")
            if st.button("💾 Salvar Despesa", type="primary", use_container_width=True):
                # VALIDAÇÃO: Impede salvar se tiver campos vazios
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
            
            lista_anos = gerar_lista_anos()
            
            linhas_iniciais = [{
                "valor": None,
                "data_liquidacao": None,
                "mes_competencia": None,
                "ano_competencia": None,
                "fornecedor": "",
                "categoria": None,
                "observacao": "",
                "status": None
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
                    "fornecedor": st.column_config.TextColumn("Fornecedor (Digite)", required=True),
                    "categoria": st.column_config.SelectboxColumn("Classificação", options=CATEGORIAS, required=True),
                    "observacao": st.column_config.TextColumn("Observação"),
                    "status": st.column_config.SelectboxColumn("Status", options=["Pago", "A Pagar"])
                },
                hide_index=True
            )

            if st.button("💾 Salvar Lote de Despesas"):
                if lote_editado.empty:
                    st.warning("A tabela está vazia.")
                else:
                    df_forn_atual = carregar_fornecedores_df()
                    nomes_forn_existentes = set(df_forn_atual['nome'].str.lower().values)
                    
                    lista_dados_finais = []
                    erro_encontrado = False
                    
                    for index, row in lote_editado.iterrows():
                        if not row['fornecedor'] and pd.isna(row['valor']):
                            continue
                            
                        if not row['fornecedor'] or pd.isna(row['valor']) or pd.isna(row['data_liquidacao']) or not row['mes_competencia'] or not row['ano_competencia']:
                            st.warning(f"Linha {index + 1} incompleta. Verifique Valor, Data, Competência e Fornecedor.")
                            erro_encontrado = True
                            continue

                        nome_forn = str(row['fornecedor']).strip()
                        if nome_forn.lower() not in nomes_forn_existentes:
                            salvar_fornecedor_rapido(nome_forn)
                            nomes_forn_existentes.add(nome_forn.lower()) 

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
                            "categoria": row['categoria'] if row['categoria'] else "Outros",
                            "observacao": row['observacao']
                        }
                        lista_dados_finais.append(dados_linha)

                    if lista_dados_finais and not erro_encontrado:
                        df_para_salvar = pd.DataFrame(lista_dados_finais)
                        salvar_lote_lancamentos(df_para_salvar)
                        st.success(f"{len(lista_dados_finais)} despesas salvas com sucesso!")
                        time.sleep(2)
                        st.cache_data.clear()
                        st.rerun()
                    elif not lista_dados_finais and not erro_encontrado:
                        st.warning("Nenhuma linha preenchida para salvar.")

        # === 3. EXCLUIR DESPESA ===
        with tab_excluir:
            st.subheader("🔍 Localizar e Excluir")
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
                    valor_min = float(df_dados['valor'].min())
                    valor_max = float(df_dados['valor'].max())
                    filtro_valor = st.slider("Faixa de Valor", valor_min, valor_max, (valor_min, valor_max))

                df_filtrado = df_dados.copy()
                if filtro_ano: df_filtrado = df_filtrado[df_filtrado['competencia'].str[:4].isin(filtro_ano)]
                if filtro_mes: df_filtrado = df_filtrado[df_filtrado['competencia'].str[5:].isin(filtro_mes)]
                df_filtrado = df_filtrado[(df_filtrado['valor'] >= filtro_valor[0]) & (df_filtrado['valor'] <= filtro_valor[1])]
                df_filtrado = df_filtrado[df_filtrado['tipo'] == 'Despesa']

                st.markdown(f"**Encontrados:** {len(df_filtrado)} registros.")

                if not df_filtrado.empty:
                    df_filtrado_view = df_filtrado.copy()
                    df_filtrado_view.insert(0, "Excluir?", False)

                    editor_exclusao = st.data_editor(
                        df_filtrado_view,
                        column_config={
                            "Excluir?": st.column_config.CheckboxColumn(required=True),
                            "data_liquidacao": st.column_config.DateColumn("Data Liq.", format="DD/MM/YYYY"),
                            "valor": st.column_config.NumberColumn("Valor", format="R$ %.2f")
                        },
                        disabled=["tipo", "valor", "fornecedor", "data_liquidacao", "competencia", "categoria", "observacao"],
                        hide_index=True,
                        use_container_width=True
                    )

                    linhas_marcadas = editor_exclusao[editor_exclusao["Excluir?"] == True]

                    if not linhas_marcadas.empty:
                        st.error(f"Você selecionou {len(linhas_marcadas)} itens para exclusão.")
                        if st.button("🗑️ CONFIRMAR EXCLUSÃO"):
                            indices_para_deletar = linhas_marcadas.index.tolist()
                            excluir_lancamentos(indices_para_deletar)
                            st.success("Registros excluídos com sucesso!")
                            time.sleep(2)
                            st.cache_data.clear()
                            st.rerun()
                else:
                    st.info("Nenhuma despesa encontrada com esses filtros.")
            else:
                st.info("Não há dados cadastrados.")

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
            c1.metric("Receitas", f"R$ {total_rec:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
            c2.metric("Despesas", f"R$ {total_desp:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."), delta_color="inverse")
            c3.metric("Resultado", f"R$ {saldo:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))

            st.subheader("Despesas por Categoria")
            df_despesas = df_view[df_view['tipo'] == 'Despesa']
            if not df_despesas.empty:
                st.bar_chart(df_despesas.groupby("categoria")["valor"].sum())

            st.subheader("Extrato Detalhado")
            st.dataframe(
                df_view.sort_values("data_liquidacao", ascending=False), 
                use_container_width=True,
                column_config={
                    "data_liquidacao": st.column_config.DateColumn("Data Liq.", format="DD/MM/YYYY"),
                    "valor": st.column_config.NumberColumn("Valor", format="R$ %.2f")
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
