# ============================================================
# BIBLIOTECA PESSOAL — Fase 2 (Streamlit + Google Sheets)
# ============================================================
import streamlit as st
import pandas as pd
import unicodedata
import gspread
import requests
from google.oauth2.service_account import Credentials


# --- CONFIGURAÇÃO ---
SHEET_ID = "1pz19lMUQEMx2HXDqJhchiNOHJ3PPRepSc4L60DeSKvE"
SHEET_NAME = "Página1"
COLUNAS = ["id", "dono", "titulo", "autor", "edicao"]
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

DONOS = ["Elisa", "Francisco", "Luisa", "Patrícia"]


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
    """Conecta ao Google Sheets usando os Secrets do Streamlit."""
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
    """Lê os dados do Google Sheets e retorna um DataFrame."""
    try:
        aba = conectar_sheets()
        dados = aba.get_all_records()

        if not dados:
            return pd.DataFrame(columns=COLUNAS)

        df = pd.DataFrame(dados, dtype=str)

        for coluna in COLUNAS:
            if coluna not in df.columns:
                df[coluna] = ""

        return df.fillna("")

    except Exception as e:
        st.error(f"Erro ao carregar o catálogo: {e}")
        return pd.DataFrame(columns=COLUNAS)


def salvar_linha(novo_livro):
    """Adiciona uma linha nova no Google Sheets."""
    try:
        aba = conectar_sheets()
        aba.append_row([
            novo_livro["id"],
            novo_livro["dono"],
            novo_livro["titulo"],
            novo_livro["autor"],
            novo_livro["edicao"],
        ])
        st.cache_data.clear()
        return True
    except Exception as e:
        st.error(f"Erro ao salvar: {e}")
        return False


def atualizar_linha(df, idx_df, dados_atualizados):
    """Atualiza uma linha existente no Google Sheets."""
    try:
        aba = conectar_sheets()
        todos = aba.get_all_values()
        id_busca = str(df.loc[idx_df, "id"])

        for i, linha in enumerate(todos):
            if linha[0] == id_busca:
                num_linha = i + 1
                aba.update(f"A{num_linha}:E{num_linha}", [[
                    dados_atualizados["id"],
                    dados_atualizados["dono"],
                    dados_atualizados["titulo"],
                    dados_atualizados["autor"],
                    dados_atualizados["edicao"],
                ]])
                st.cache_data.clear()
                return True

        st.error("Linha não encontrada na planilha.")
        return False

    except Exception as e:
        st.error(f"Erro ao atualizar: {e}")
        return False


def remover_linha(df, idx_df):
    """Remove uma linha do Google Sheets pelo ID."""
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


@st.cache_data(ttl=60)
def buscar_google_books(titulo):
    """
    Busca livros na API do Google Books pelo título.
    
    @st.cache_data(ttl=60) guarda o resultado por 60 segundos
    para não chamar a API a cada letra digitada.
    """
    if not titulo or len(titulo) < 3:
        return []

    try:
        url = "https://www.googleapis.com/books/v1/volumes"
        params = {
            "q": titulo,
            "maxResults": 5,
            "printType": "books",
            "key": st.secrets["google_books"]["api_key"]
        }

        resposta = requests.get(url, params=params, timeout=5)

        if resposta.status_code != 200:
            st.warning(f"API retornou status {resposta.status_code}: {resposta.text[:200]}")
            return []

        dados = resposta.json()

        if "items" not in dados:
            return []

        sugestoes = []
        for item in dados["items"]:
            info = item.get("volumeInfo", {})
            titulo_livro = info.get("title", "")
            autores = info.get("authors", [])
            autor = ", ".join(autores) if autores else ""

            if titulo_livro:
                sugestoes.append({
                    "titulo": titulo_livro,
                    "autor": autor,
                })

        return sugestoes

    except Exception as e:
        st.error(f"Erro na busca: {e}")
        return []


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

aba_comprar, aba_adicionar, aba_editar, aba_remover, aba_todos, aba_stats = st.tabs([
    "🛒 Verificar antes de comprar",
    "➕ Adicionar",
    "✏️ Editar",
    "🗑️ Remover",
    "📋 Todos os livros",
    "📊 Estatísticas"
])


# ============================================================
# ABA 1 — VERIFICAR ANTES DE COMPRAR
# ============================================================

with aba_comprar:
    st.subheader("Verificar antes de comprar")
    st.write("Digite o título e descubra se já temos o livro.")

    titulo_busca = st.text_input("Título do livro:", placeholder="ex: Grande Sertão")

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
# ABA 2 — ADICIONAR
# ============================================================

with aba_adicionar:
    st.subheader("Adicionar livro")

    # Inicializa session_state para guardar sugestão selecionada
    # session_state persiste valores entre interações do usuário
    if "autor_preenchido" not in st.session_state:
        st.session_state.autor_preenchido = ""
    if "titulo_selecionado" not in st.session_state:
        st.session_state.titulo_selecionado = ""

    st.write("**Buscar na base do Google Books:**")
    st.caption("Digite pelo menos 3 letras e clique em Buscar")

    # Usamos um botão explícito de busca em vez de buscar
    # enquanto digita — mais confiável no Streamlit
    col_input, col_btn = st.columns([4, 1])
    with col_input:
        titulo_digitado = st.text_input(
            "Título para buscar:",
            placeholder="ex: Grande Sertão",
            key="titulo_busca_api",
            label_visibility="collapsed"
        )
    with col_btn:
        buscar = st.button("🔍 Buscar", use_container_width=True)

    # Busca só quando o botão é clicado
    if buscar and titulo_digitado and len(titulo_digitado) >= 3:
        with st.spinner("Buscando..."):
            sugestoes = buscar_google_books(titulo_digitado)

        if sugestoes:
            st.write("**Selecione para preencher automaticamente:**")
            for s in sugestoes:
                label = f"📖 {s['titulo']}" + (f" — {s['autor']}" if s['autor'] else "")
                if st.button(label, key=f"sug_{s['titulo']}"):
                    st.session_state.titulo_selecionado = s["titulo"]
                    st.session_state.autor_preenchido = s["autor"]
                    st.rerun()
        else:
            st.info("Nenhuma sugestão encontrada. Preencha os campos manualmente.")

    st.divider()
    st.write("**Preencha os dados do livro:**")

    # Formulário principal
    with st.form("form_adicionar", clear_on_submit=True):
        col1, col2 = st.columns(2)

        with col1:
            novo_titulo = st.text_input(
                "Título *",
                value=st.session_state.titulo_selecionado
            )
            novo_autor = st.text_input(
                "Autor *",
                value=st.session_state.autor_preenchido
            )
            nova_edicao = st.text_input("Edição/Editora (opcional)")

        with col2:
            novo_dono = st.selectbox("De quem é *", DONOS)

        submitted = st.form_submit_button("Adicionar livro", type="primary")

        if submitted:
            if not all([novo_titulo, novo_autor]):
                st.error("Título e autor são obrigatórios.")
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
                    "edicao": nova_edicao,
                }

                if salvar_linha(novo_livro):
                    st.session_state.titulo_selecionado = ""
                    st.session_state.autor_preenchido = ""
                    st.success(f"✅ '{novo_titulo}' adicionado com sucesso!")
                    st.rerun()


# ============================================================
# ABA 3 — EDITAR
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
                    ed_edicao = st.text_input("Edição/Editora", value=livro["edicao"])

                with col2:
                    dono_idx = DONOS.index(livro["dono"]) if livro["dono"] in DONOS else 0
                    ed_dono = st.selectbox("De quem é", DONOS, index=dono_idx)

                salvar = st.form_submit_button("Salvar alterações", type="primary")

                if salvar:
                    dados_atualizados = {
                        "id": livro["id"],
                        "dono": ed_dono,
                        "titulo": ed_titulo,
                        "autor": ed_autor,
                        "edicao": ed_edicao,
                    }
                    if atualizar_linha(df, idx_editar, dados_atualizados):
                        st.success("✅ Livro atualizado com sucesso!")
                        st.rerun()


# ============================================================
# ABA 4 — REMOVER
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
# ABA 5 — TODOS OS LIVROS
# ============================================================

with aba_todos:
    st.subheader("Todos os livros")

    if df.empty:
        st.info("O catálogo está vazio.")
    else:
        donos_filtro = ["Todos"] + DONOS
        filtro_dono = st.selectbox("Filtrar por dono:", donos_filtro)

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
# ABA 6 — ESTATÍSTICAS
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
