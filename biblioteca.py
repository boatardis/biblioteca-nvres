# ============================================================
# SISTEMA DE BIBLIOTECA PESSOAL — Fase 1
# ============================================================
# Este arquivo é o coração do sistema. Ele permite:
#   - Buscar livros por título, autor ou dono
#   - Verificar se um livro já existe antes de comprar
#   - Adicionar novos livros
#   - Editar informações de um livro existente
#   - Remover livros
#
# Como rodar:
#   python biblioteca.py
# ============================================================


# --- IMPORTS ---
# Pandas é a biblioteca mais usada para trabalhar com dados em Python.
# Pense nela como uma planilha inteligente dentro do código.
import pandas as pd

# 'os' permite verificar se arquivos existem no computador.
import os

# Unicodedata ajuda a comparar textos ignorando acentos e maiúsculas.
import unicodedata


# --- CONFIGURAÇÃO ---
# Aqui definimos o nome do arquivo CSV onde os livros ficam salvos.
# Se você quiser mudar o nome do arquivo, muda só aqui.
ARQUIVO_CSV = "catalogo.csv"

# Estas são as colunas que todo livro precisa ter.
COLUNAS = ["id", "dono", "titulo", "autor", "edicao"]


# ============================================================
# FUNÇÕES AUXILIARES
# Funções auxiliares fazem tarefas pequenas que outras funções
# precisam. Elas ficam aqui no topo para ficar organizado.
# ============================================================

def normalizar(texto):
    """
    Converte um texto para minúsculas e remove acentos.
    Isso permite buscar 'jose' e encontrar 'José', por exemplo.

    'unicodedata.normalize' separa as letras dos acentos,
    e o encode/decode remove os acentos em seguida.
    """
    if not isinstance(texto, str):
        return ""
    texto = texto.lower().strip()
    texto = unicodedata.normalize("NFD", texto)
    texto = texto.encode("ascii", "ignore").decode("utf-8")
    return texto


def carregar_catalogo():
    """
    Lê o arquivo CSV e retorna um DataFrame (tabela de dados).
    Se o arquivo não existir, cria um catálogo vazio.

    DataFrame é o tipo de dado principal do pandas —
    funciona como uma tabela com linhas e colunas.
    """
    if os.path.exists(ARQUIVO_CSV):
        df = pd.read_csv(ARQUIVO_CSV, dtype=str)
        # Garante que todas as colunas existam mesmo em arquivos antigos
        for coluna in COLUNAS:
            if coluna not in df.columns:
                df[coluna] = ""
        return df.fillna("")
    else:
        # Cria uma tabela vazia com as colunas certas
        return pd.DataFrame(columns=COLUNAS)


def salvar_catalogo(df):
    """
    Salva o DataFrame de volta no arquivo CSV.
    index=False evita que o pandas salve uma coluna extra de índice.
    """
    df.to_csv(ARQUIVO_CSV, index=False, encoding="utf-8")


def proximo_id(df):
    """
    Gera um ID único para o próximo livro.
    Pega o maior ID existente e soma 1.
    Se o catálogo estiver vazio, começa do 1.
    """
    if df.empty or df["id"].dropna().empty:
        return 1
    ids_validos = df["id"][df["id"].str.strip() != ""].dropna()
    if ids_validos.empty:
        return 1
    return int(ids_validos.astype(int).max()) + 1


def linha_divisoria():
    """ Imprime uma linha para separar seções no terminal. """
    print("\n" + "=" * 55 + "\n")


def exibir_livros(df):
    """
    Formata e exibe uma tabela de livros de forma legível no terminal.
    Recebe um DataFrame e imprime cada linha de forma organizada.
    """
    for _, row in df.iterrows():
        # O '_' é uma convenção para dizer "não vou usar o índice"
        print(f"  ID {row['id']:>4} | {row['titulo'][:45]:<45} | {row['autor'][:30]:<30} | {row['dono']}")
        if str(row.get("edicao", "")).strip():
            print(f"             Edição: {row['edicao']}")


# ============================================================
# FUNÇÕES PRINCIPAIS
# Cada função abaixo corresponde a uma ação do menu.
# ============================================================

def buscar_livro(df):
    """
    Busca livros no catálogo por qualquer campo:
    título, autor, dono ou edição.

    O truque aqui é normalizar tanto o texto buscado quanto
    os dados do catálogo antes de comparar — assim 'jose'
    encontra 'José' e 'JOSE'.
    """
    linha_divisoria()
    print("BUSCAR LIVRO")
    print("(deixe em branco e pressione Enter para cancelar)\n")

    termo = input("Digite o título, autor, dono ou edição: ").strip()

    if not termo:
        print("Busca cancelada.")
        return

    termo_normalizado = normalizar(termo)

    # Para cada coluna de texto, verifica se o termo aparece no valor.
    # O resultado é uma tabela filtrada só com as linhas que batem.
    mask = df.apply(
        lambda row: any(
            termo_normalizado in normalizar(str(row[col]))
            for col in ["titulo", "autor", "dono", "edicao"]
        ),
        axis=1  # axis=1 significa "aplica linha por linha"
    )

    resultados = df[mask]

    if resultados.empty:
        print(f"\nNenhum livro encontrado para '{termo}'.")
    else:
        print(f"\n{len(resultados)} livro(s) encontrado(s):\n")
        exibir_livros(resultados)


def verificar_antes_de_comprar(df):
    """
    Função pensada para uso na livraria.
    Busca pelo título e avisa claramente se já temos o livro.
    Também detecta títulos parecidos para evitar variações de grafia.
    """
    linha_divisoria()
    print("VERIFICAR ANTES DE COMPRAR")
    print("(deixe em branco e pressione Enter para cancelar)\n")

    titulo = input("Digite o título do livro: ").strip()

    if not titulo:
        print("Verificação cancelada.")
        return

    titulo_normalizado = normalizar(titulo)

    # Busca correspondência no título
    exatos = df[df["titulo"].apply(normalizar).str.contains(titulo_normalizado, na=False)]

    if not exatos.empty:
        print(f"\n⚠️  ATENÇÃO: Já temos este livro na biblioteca!\n")
        exibir_livros(exatos)
    else:
        # Busca títulos parecidos (com pelo menos uma palavra em comum)
        palavras = [p for p in titulo_normalizado.split() if len(p) > 3]
        parecidos = pd.DataFrame(columns=COLUNAS)

        for palavra in palavras:
            encontrados = df[df["titulo"].apply(normalizar).str.contains(palavra, na=False)]
            parecidos = pd.concat([parecidos, encontrados]).drop_duplicates()

        if not parecidos.empty:
            print(f"\nNão encontramos '{titulo}' exatamente,")
            print("mas existem títulos parecidos na biblioteca:\n")
            exibir_livros(parecidos)
            print("\nConfirme se não é o mesmo livro antes de comprar.")
        else:
            print(f"\n✅  '{titulo}' não está na biblioteca. Pode comprar!")


def adicionar_livro(df):
    """
    Adiciona um novo livro ao catálogo.
    Pede cada campo separadamente e valida se os obrigatórios
    foram preenchidos antes de salvar.
    """
    linha_divisoria()
    print("ADICIONAR LIVRO")
    print("(campos com * são obrigatórios)\n")

    titulo = input("* Título: ").strip()
    if not titulo:
        print("Título é obrigatório. Operação cancelada.")
        return

    autor = input("* Autor: ").strip()
    if not autor:
        print("Autor é obrigatório. Operação cancelada.")
        return

    dono = input("* De quem é (nome da pessoa): ").strip()
    if not dono:
        print("Dono é obrigatório. Operação cancelada.")
        return

    edicao = input("  Edição/Editora (opcional): ").strip()

    # Antes de salvar, verifica se já existe um livro igual
    titulo_normalizado = normalizar(titulo)
    existentes = df[df["titulo"].apply(normalizar).str.contains(titulo_normalizado, na=False)]

    if not existentes.empty:
        print(f"\n⚠️  Atenção: já existe(m) livro(s) com título parecido:\n")
        exibir_livros(existentes)
        confirmacao = input("\nMesmo assim, deseja adicionar? (s/n): ").strip().lower()
        if confirmacao != "s":
            print("Operação cancelada.")
            return

    # Cria um dicionário com os dados do novo livro
    # Um dicionário em Python é uma estrutura chave: valor
    novo_livro = {
        "id": proximo_id(df),
        "dono": dono,
        "titulo": titulo,
        "autor": autor,
        "edicao": edicao
    }

    # pd.concat junta o DataFrame existente com o novo livro
    # ignore_index=True reorganiza os índices internos do pandas
    df = pd.concat([df, pd.DataFrame([novo_livro])], ignore_index=True)
    salvar_catalogo(df)

    print(f"\n✅  '{titulo}' adicionado com sucesso! (ID: {novo_livro['id']})")
    return df


def editar_livro(df):
    """
    Edita as informações de um livro existente.
    O usuário busca pelo título primeiro. Se houver mais de
    um resultado, confirma pelo ID. Deixar em branco mantém
    o valor atual.
    """
    linha_divisoria()
    print("EDITAR LIVRO\n")

    # Passo 1: busca pelo título
    titulo = input("Digite o título do livro a editar: ").strip()
    if not titulo:
        print("Operação cancelada.")
        return df

    titulo_normalizado = normalizar(titulo)
    resultados = df[df["titulo"].apply(normalizar).str.contains(titulo_normalizado, na=False)]

    if resultados.empty:
        print(f"\nNenhum livro encontrado com '{titulo}'.")
        return df

    # Passo 2: mostra o que encontrou
    print(f"\n{len(resultados)} livro(s) encontrado(s):\n")
    exibir_livros(resultados)

    # Passo 3: se encontrou mais de um, pede confirmação pelo ID
    # Se encontrou só um, já vai direto para a edição
    if len(resultados) == 1:
        idx = resultados.index[0]
    else:
        print("\nMais de um livro encontrado.")
        try:
            id_livro = int(input("Digite o ID do livro que deseja editar: ").strip())
        except ValueError:
            print("ID inválido. Operação cancelada.")
            return df

        linha = df[df["id"] == str(id_livro)]
        if linha.empty:
            print("ID não encontrado. Operação cancelada.")
            return df
        idx = linha.index[0]

    # Passo 4: edição campo a campo
    livro_atual = df.loc[idx]
    print(f"\nEditando: {livro_atual['titulo']}")
    print("(pressione Enter para manter o valor atual)\n")

    campos = ["titulo", "autor", "dono", "edicao"]
    for campo in campos:
        valor_atual = livro_atual[campo] if pd.notna(livro_atual[campo]) else ""
        novo_valor = input(f"{campo.capitalize()} [{valor_atual}]: ").strip()
        if novo_valor:
            df.at[idx, campo] = novo_valor

    salvar_catalogo(df)
    print(f"\n✅  Livro atualizado com sucesso!")
    return df


def remover_livro(df):
    """
    Remove um livro do catálogo.
    O usuário busca pelo título primeiro. Se houver mais de
    um resultado, confirma pelo ID. Pede confirmação antes
    de deletar para evitar acidentes.
    """
    linha_divisoria()
    print("REMOVER LIVRO\n")

    # Passo 1: busca pelo título
    titulo = input("Digite o título do livro a remover: ").strip()
    if not titulo:
        print("Operação cancelada.")
        return df

    titulo_normalizado = normalizar(titulo)
    resultados = df[df["titulo"].apply(normalizar).str.contains(titulo_normalizado, na=False)]

    if resultados.empty:
        print(f"\nNenhum livro encontrado com '{titulo}'.")
        return df

    # Passo 2: mostra o que encontrou
    print(f"\n{len(resultados)} livro(s) encontrado(s):\n")
    exibir_livros(resultados)

    # Passo 3: se encontrou mais de um, pede confirmação pelo ID
    if len(resultados) == 1:
        idx = resultados.index[0]
    else:
        print("\nMais de um livro encontrado.")
        try:
            id_livro = int(input("Digite o ID do livro que deseja remover: ").strip())
        except ValueError:
            print("ID inválido. Operação cancelada.")
            return df

        linha = df[df["id"] == str(id_livro)]
        if linha.empty:
            print("ID não encontrado. Operação cancelada.")
            return df
        idx = linha.index[0]

    # Passo 4: confirmação final antes de deletar
    livro = df.loc[idx]
    print(f"\nLivro selecionado: '{livro['titulo']}' — {livro['autor']}")
    confirmacao = input("Tem certeza que deseja remover? (s/n): ").strip().lower()

    if confirmacao == "s":
        df = df.drop(idx)
        salvar_catalogo(df)
        print(f"✅  '{livro['titulo']}' removido com sucesso.")
    else:
        print("Operação cancelada.")

    return df


def listar_todos(df):
    """
    Lista todos os livros do catálogo, ordenados por dono e título.
    Útil para ter uma visão geral da biblioteca.
    """
    linha_divisoria()
    print("TODOS OS LIVROS\n")

    if df.empty:
        print("O catálogo está vazio.")
        return

    # sort_values ordena o DataFrame pelas colunas indicadas
    df_ordenado = df.sort_values(by=["dono", "titulo"])
    exibir_livros(df_ordenado)
    print(f"\nTotal: {len(df)} livro(s) no catálogo.")


def estatisticas(df):
    """
    Mostra um resumo da biblioteca: total de livros e livros por dono.

    value_counts() é uma função do pandas que conta
    quantas vezes cada valor aparece numa coluna.
    """
    linha_divisoria()
    print("ESTATÍSTICAS DA BIBLIOTECA\n")

    if df.empty:
        print("O catálogo está vazio.")
        return

    print(f"Total de livros: {len(df)}\n")

    print("Por dono:")
    for dono, qtd in df["dono"].value_counts().items():
        print(f"  {dono:<20} {qtd} livro(s)")


# ============================================================
# MENU PRINCIPAL
# Esta é a função que roda o programa em loop.
# O 'while True' mantém o menu aberto até o usuário sair.
# ============================================================

def menu():
    """
    Exibe o menu principal e chama a função correspondente
    à escolha do usuário. Roda em loop até escolher sair.
    """
    # Carrega o catálogo uma vez ao iniciar
    df = carregar_catalogo()

    while True:
        linha_divisoria()
        print("BIBLIOTECA PESSOAL")
        print(f"({len(df)} livros catalogados)\n")
        print("  1. Buscar livro")
        print("  2. Verificar antes de comprar")
        print("  3. Adicionar livro")
        print("  4. Editar livro")
        print("  5. Remover livro")
        print("  6. Listar todos os livros")
        print("  7. Estatísticas")
        print("  0. Sair")

        escolha = input("\nEscolha uma opção: ").strip()

        if escolha == "1":
            buscar_livro(df)

        elif escolha == "2":
            verificar_antes_de_comprar(df)

        elif escolha == "3":
            resultado = adicionar_livro(df)
            if resultado is not None:
                df = resultado

        elif escolha == "4":
            df = editar_livro(df)

        elif escolha == "5":
            df = remover_livro(df)

        elif escolha == "6":
            listar_todos(df)

        elif escolha == "7":
            estatisticas(df)

        elif escolha == "0":
            print("\nAté logo!\n")
            break

        else:
            print("Opção inválida. Digite um número de 0 a 7.")


# ============================================================
# PONTO DE ENTRADA
# Esta linha garante que o menu() só roda quando você executa
# este arquivo diretamente (python biblioteca.py).
# Se outro arquivo importar este, o menu não roda sozinho.
# ============================================================
if __name__ == "__main__":
    menu()
