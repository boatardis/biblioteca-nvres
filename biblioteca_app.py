# ============================================================
# BIBLIOTECA PESSOAL — Fase 2 (Streamlit + Google Sheets)
# ============================================================
# Este arquivo é a interface web do sistema.
# Usa o Streamlit para criar a página no navegador e
# o Google Sheets como banco de dados permanente.
#
# Como rodar localmente:
#   streamlit run biblioteca_app.py
# ============================================================


# --- IMPORTS ---
import streamlit as st
import pandas as pd
import unicodedata
import gspread
from google.oauth2.service_account import Credentials


# --- CONFIGURAÇÃO ---
# ID da planilha do Google Sheets
SHEET_ID = "1pz19lMUQEMx2HXDqJhchiNOHJ3PPRepSc4L60DeSKvE"

# Nome da aba dentro da planilha
SHEET_NAME = "Página1"

# Colunas do catálogo
COLUNAS = ["id", "dono", "titulo", "autor", "edicao"]

# Escopos de acesso — o que o sistema pode fazer no Google
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]


# ============================================================
# FUNÇÕES AUXILIARES
# ============================================================

def normalizar(texto):
    """Converte texto para minúsculas e remove acentos."""
    if not isinstance(texto, str):
        return ""
    texto = texto.lower().strip()
    texto = unicodedata.normalize("NFD", texto)
    texto = texto.encode("ascii", "ignore").decode("utf-8")
    return texto


def conectar_sheets():
    """
    Conecta ao Google Sheets usando as credenciais guardadas
    nos Secrets do Streamlit Cloud.

    st.secrets lê o arquivo de secrets configurado no Streamlit —
    é como um cofre seguro que guarda informações sensíveis
    sem expor no código ou no GitHub.
    """
    credenciais = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=SCOPES
    )
    cliente = gspread.authorize(credenciais)
    planilha = cliente.open_by_key(SHEET_ID)
    aba = planilha.worksheet(SHEET_NAME)
    return aba


@st.cache_data(ttl=30)
def carregar_catalogo():
    """
    Lê os dados do Google Sheets e retorna um DataFrame.

    @st.cache_data(ttl=30) guarda os dados em memória por 30 segundos.
    Isso evita chamar a API do Google a cada clique do usuário.
    Após 30 segundos, recarrega os dados frescos da planilha.
    """
    try:
        aba = conectar_sheets()
        dados = aba.get_all_records()

        if not dados:
            return pd.DataFrame(columns=COLUNAS)

        df = pd.DataFrame(dados, dtype=str)

        # Garante que todas as colunas existam
        for coluna in COLUNAS:
            if coluna not in df.columns:
                df[coluna] = ""

        return df.fillna("")

    except Exception as e:
        st.error(f"Erro ao carregar o catálogo: {e}")
        return pd.DataFrame(columns=COLUNAS)


def salvar_linha(novo_livro):
    """
    Adiciona uma linha nova no Google Sheets.
    Mais eficiente que reescrever a planilha inteira.
    """
    try:
        aba = conectar_sheets()
        aba.append_row([
            novo_livro["id"],
            novo_livro["dono"],
            novo_livro["titulo"],
            novo_livro["autor"],
            novo_livro["edicao"]
        ])
        st.cache_data.clear()
        return True
    except Exception as e:
        st.error(f"Erro ao salvar: {e}")
        return False


def atualizar_linha(df, idx_df, dados_atualizados):
    """
    Atualiza uma linha existente no Google Sheets.
    Encontra a linha pelo ID e substitui os valores.
    """
    try:
        aba = conectar_sheets()

        # Pega todos os valores para encontrar a linha certa
        todos = aba.get_all_values()
        id_busca = str(df.loc[idx_df, "id"])

        # Percorre as linhas procurando o ID
        # A linha 1 é o cabeçalho, então começamos do índice 2
        for i, linha in enumerate(todos):
            if linha[0] == id_busca:
                num_linha = i + 1  # Sheets usa índice começando em 1
                aba.update(f"A{num_linha}:E{num_linha}", [[
                    dados_atualizados["id"],
                    dados_atualizados["dono"],
                    dados_atualizados["titulo"],
                    dados_atualizados["autor"],
                    dados_atualizados["edicao"]
                ]])
                st.cache_data.clear()
                return True

        st.error("Linha não encontrada na planilha.")
        return False

    except Exception as e:
        st.error(f"Erro ao atualizar: {e}")
        return False


def remover_linha(df, idx_df):
    """
    Remove uma linha do Google Sheets pelo ID.
    """
    try:
        aba = conectar_sheets()
        todos = aba.get_all_values()
        id_busca = str(df.loc[idx_df, "id"])

        for i, linha in enumerate(todos):
            if linha[0] == id_busca:
                num_linha = i + 1
                aba.delete_rows(num_linha)
                st.cache_data.clear()
                return True

        st.error("Linha não encontrada na planilha.")
        return False

    except Exception as e:
        st.error(f"Erro ao remover: {e}")
        return False


def proximo_id(df):
    """Gera o próximo ID único."""
    if df.empty or df["id"].dropna().empty:
        return 1
    ids_validos = df["id"][df["id"].str.strip() != ""].dropna()
    if ids_validos.empty:
        return 1
    return int(ids_validos.astype(int).max()) + 1


# ============================================================
# CONFIGURAÇÃO DA PÁGINA
# ============================================================

st.set_page_config(
    page_title="Biblioteca Pessoal",
    page_icon="📚",
    layout="wide"
)

df = carregar_catalogo()

st.title("📚 Biblioteca Pessoal")
st.caption(f"{len(df)} livros catalogados")
st.divider()


# ============================================================
# ABAS
# ============================================================

aba_busca, aba_comprar, aba_adicionar, aba_editar, aba_remover, aba_todos, aba_stats = st.tabs([
    "🔍 Buscar",
    "🛒 Verificar antes de comprar",
    "➕ Adicionar",
    "✏️ Editar",
    "🗑️ Remover",
    "📋 Todos os livros",
    "📊 Estatísticas"
])


# ============================================================
# ABA 1 — BUSCAR
# ============================================================

with aba_busca:
    st.subheader("Buscar livro")
    st.write("Busque por título, autor, dono ou edição.")

    termo = st.text_input("Digite sua busca:", placeholder="ex: Machado de Assis")

    if termo:
        termo_normalizado = normalizar(termo)

        mask = df.apply(
            lambda row: any(
                termo_normalizado in normalizar(str(row[col]))
                for col in ["titulo", "autor", "dono", "edicao"]
            ),
            axis=1
        )
        resultados = df[mask]

        if resultados.empty:
            st.warning(f"Nenhum livro encontrado para '{termo}'.")
        else:
            st.success(f"{len(resultados)} livro(s) encontrado(s).")
            st.dataframe(
                resultados[["id", "titulo", "autor", "dono", "edicao"]],
                use_container_width=True,
                hide_index=True
            )


# ============================================================
# ABA 2 — VERIFICAR ANTES DE COMPRAR
# ============================================================

with aba_comprar:
    st.subheader("Verificar antes de comprar")
    st.write("Digite o título e descubra se já temos o livro.")

    titulo_busca = st.text_input("Título do livro:", placeholder="ex: Grande Sertão", key="comprar")

    if titulo_busca:
        titulo_normalizado = normalizar(titulo_busca)
        exatos = df[df["titulo"].apply(normalizar).str.contains(titulo_normalizado, na=False)]

        if not exatos.empty:
            st.error("⚠️ Já temos este livro na biblioteca!")
            st.dataframe(
                exatos[["id", "titulo", "autor", "dono", "edicao"]],
                use_container_width=True,
                hide_index=True
            )
        else:
            palavras = [p for p in titulo_normalizado.split() if len(p) > 3]
            parecidos = pd.DataFrame(columns=COLUNAS)

            for palavra in palavras:
                encontrados = df[df["titulo"].apply(normalizar).str.contains(palavra, na=False)]
                parecidos = pd.concat([parecidos, encontrados]).drop_duplicates()

            if not parecidos.empty:
                st.warning("Não encontramos esse título exato, mas existem títulos parecidos:")
                st.dataframe(
                    parecidos[["id", "titulo", "autor", "dono", "edicao"]],
                    use_container_width=True,
                    hide_index=True
                )
            else:
                st.success(f"✅ '{titulo_busca}' não está na biblioteca. Pode comprar!")


# ============================================================
# ABA 3 — ADICIONAR
# ============================================================

with aba_adicionar:
    st.subheader("Adicionar livro")

    with st.form("form_adicionar", clear_on_submit=True):
        col1, col2 = st.columns(2)

        with col1:
            novo_titulo = st.text_input("Título *")
            novo_autor = st.text_input("Autor *")

        with col2:
            novo_dono = st.text_input("De quem é *", placeholder="ex: Elisa")
            nova_edicao = st.text_input("Edição/Editora (opcional)")

        submitted = st.form_submit_button("Adicionar livro", type="primary")

        if submitted:
            if not all([novo_titulo, novo_autor, novo_dono]):
                st.error("Preencha todos os campos obrigatórios (*).")
            else:
                titulo_norm = normalizar(novo_titulo)
                existentes = df[df["titulo"].apply(normalizar).str.contains(titulo_norm, na=False)]

                if not existentes.empty:
                    st.warning("Já existe um livro com título parecido:")
                    st.dataframe(existentes[["titulo", "autor", "dono"]], hide_index=True)
                    st.info("Se quiser adicionar mesmo assim, clique em Adicionar novamente.")

                novo_livro = {
                    "id": str(proximo_id(df)),
                    "dono": novo_dono,
                    "titulo": novo_titulo,
                    "autor": novo_autor,
                    "edicao": nova_edicao
                }

                if salvar_linha(novo_livro):
                    st.success(f"✅ '{novo_titulo}' adicionado com sucesso!")
                    st.rerun()


# ============================================================
# ABA 4 — EDITAR
# ============================================================

with aba_editar:
    st.subheader("Editar livro")
    st.write("Busque pelo título para encontrar o livro.")

    termo_editar = st.text_input("Título do livro:", key="editar_busca")

    if termo_editar:
        termo_norm = normalizar(termo_editar)
        resultados_editar = df[df["titulo"].apply(normalizar).str.contains(termo_norm, na=False)]

        if resultados_editar.empty:
            st.warning("Nenhum livro encontrado.")
        else:
            opcoes = {
                f"ID {row['id']} — {row['titulo']} ({row['autor']})": idx
                for idx, row in resultados_editar.iterrows()
            }
            escolha = st.selectbox("Selecione o livro:", list(opcoes.keys()))
            idx_editar = opcoes[escolha]
            livro = df.loc[idx_editar]

            with st.form("form_editar"):
                col1, col2 = st.columns(2)

                with col1:
                    ed_titulo = st.text_input("Título", value=livro["titulo"])
                    ed_autor = st.text_input("Autor", value=livro["autor"])

                with col2:
                    ed_dono = st.text_input("De quem é", value=livro["dono"])
                    ed_edicao = st.text_input("Edição/Editora", value=livro["edicao"])

                salvar = st.form_submit_button("Salvar alterações", type="primary")

                if salvar:
                    dados_atualizados = {
                        "id": livro["id"],
                        "dono": ed_dono,
                        "titulo": ed_titulo,
                        "autor": ed_autor,
                        "edicao": ed_edicao
                    }
                    if atualizar_linha(df, idx_editar, dados_atualizados):
                        st.success("✅ Livro atualizado com sucesso!")
                        st.rerun()


# ============================================================
# ABA 5 — REMOVER
# ============================================================

with aba_remover:
    st.subheader("Remover livro")
    st.write("Busque pelo título para encontrar o livro.")

    termo_remover = st.text_input("Título do livro:", key="remover_busca")

    if termo_remover:
        termo_norm_rem = normalizar(termo_remover)
        resultados_remover = df[df["titulo"].apply(normalizar).str.contains(termo_norm_rem, na=False)]

        if resultados_remover.empty:
            st.warning("Nenhum livro encontrado.")
        else:
            opcoes_rem = {
                f"ID {row['id']} — {row['titulo']} ({row['autor']})": idx
                for idx, row in resultados_remover.iterrows()
            }
            escolha_rem = st.selectbox("Selecione o livro:", list(opcoes_rem.keys()))
            idx_remover = opcoes_rem[escolha_rem]
            livro_rem = df.loc[idx_remover]

            st.dataframe(
                pd.DataFrame([livro_rem])[["titulo", "autor", "dono", "edicao"]],
                hide_index=True,
                use_container_width=True
            )

            if st.button(f"🗑️ Remover '{livro_rem['titulo']}'", type="primary"):
                if remover_linha(df, idx_remover):
                    st.success("✅ Livro removido com sucesso!")
                    st.rerun()


# ============================================================
# ABA 6 — TODOS OS LIVROS
# ============================================================

with aba_todos:
    st.subheader("Todos os livros")

    if df.empty:
        st.info("O catálogo está vazio.")
    else:
        donos = ["Todos"] + sorted(df["dono"].unique().tolist())
        filtro_dono = st.selectbox("Filtrar por dono:", donos)

        df_filtrado = df.copy()
        if filtro_dono != "Todos":
            df_filtrado = df_filtrado[df_filtrado["dono"] == filtro_dono]

        df_filtrado = df_filtrado.sort_values(by=["dono", "titulo"])

        st.caption(f"{len(df_filtrado)} livro(s)")
        st.dataframe(
            df_filtrado[["id", "titulo", "autor", "dono", "edicao"]],
            use_container_width=True,
            hide_index=True
        )


# ============================================================
# ABA 7 — ESTATÍSTICAS
# ============================================================

with aba_stats:
    st.subheader("Estatísticas da biblioteca")

    if df.empty:
        st.info("O catálogo está vazio.")
    else:
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Total de livros", len(df))
        with col2:
            st.metric("Donos", df["dono"].nunique())

        st.divider()

        st.write("**Por dono:**")
        contagem_dono = df["dono"].value_counts().reset_index()
        contagem_dono.columns = ["Dono", "Livros"]
        st.dataframe(contagem_dono, hide_index=True, use_container_width=True)
