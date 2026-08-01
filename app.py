"""
App: Gestor de Clientes - Extrator de Telefones por POP/Bairro
Autor: Gerado com apoio de Engenharia de Software
Descrição:
    Aplicativo Streamlit que recebe uma planilha .xlsx de clientes,
    filtra por POP e Bairro, extrai todos os números de celular
    válidos das colunas "Celulares" e "Telefones" (mesmo quando há
    múltiplos números em uma única célula), formata no padrão
    (XX) 9XXXX-XXXX e gera uma planilha final para download,
    tudo em memória (sem gravar arquivos temporários em disco).
"""

import io
import re

import pandas as pd
import streamlit as st

# ---------------------------------------------------------------------------
# CONFIGURAÇÃO DA PÁGINA
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Gestor de Clientes - Extrator de Telefones",
    page_icon="📞",
    layout="centered",
)

# Nomes EXATOS das colunas na planilha original (linha 9 = cabeçalho real)
COL_NOME = "Nome/Razão Social"
COL_POP = "POP"
COL_CELULARES = "Celulares"
COL_TELEFONES = "Telefones"
COL_BAIRRO = "Bairro"

# Linha do cabeçalho real no Excel (0-indexed). Como as 8 primeiras linhas
# são metadados, o cabeçalho está na linha 9 -> header=8 no pandas.
HEADER_ROW = 8

# ---------------------------------------------------------------------------
# REGEX E FUNÇÕES DE LIMPEZA DE TELEFONE
# ---------------------------------------------------------------------------

# Padrão que localiza "blocos" que se parecem com números de telefone dentro
# de um texto livre, mesmo com rótulos como "WhatsApp:", "Celular:", etc.
# Ele procura: DDD opcionalmente entre parênteses + opcional dígito 9 +
# 4 dígitos + separador opcional + 4 dígitos.
PHONE_PATTERN = re.compile(r"\(?\d{2}\)?[\s.\-]*9?\d{4}[\s.\-]?\d{4}")


def extrair_numeros(texto: str) -> list[str]:
    """
    Recebe o conteúdo bruto de uma célula (ex: "WhatsApp: (11) 91234-5678
    Celular: 11 3344-5566") e retorna uma lista de números já limpos
    (somente dígitos), um para cada ocorrência encontrada.
    """
    if not isinstance(texto, str) or not texto.strip():
        return []

    candidatos = PHONE_PATTERN.findall(texto)
    numeros_limpos = []
    for candidato in candidatos:
        somente_digitos = re.sub(r"\D", "", candidato)
        if somente_digitos:
            numeros_limpos.append(somente_digitos)
    return numeros_limpos


def formatar_celular(digitos: str) -> str | None:
    """
    Recebe uma string apenas com dígitos e retorna o número formatado
    como (XX) 9XXXX-XXXX SOMENTE se for um celular válido:
      - Precisa ter exatamente 11 dígitos (DDD + 9 + 8 dígitos)
      - O primeiro dígito após o DDD precisa ser '9'
    Caso contrário (fixo com 10 dígitos, ou lixo), retorna None e a
    linha deve ser descartada.
    """
    if len(digitos) != 11:
        return None  # fixo (10 dígitos) ou número inválido -> descarta

    ddd = digitos[:2]
    resto = digitos[2:]  # 9 dígitos: 9XXXXXXXX

    if resto[0] != "9":
        return None  # não é celular -> descarta

    return f"({ddd}) {resto[:5]}-{resto[5:]}"


def gerar_linhas_cliente(nome: str, celulares_raw: str, telefones_raw: str) -> list[dict]:
    """
    Para um cliente, junta os números encontrados em "Celulares" e
    "Telefones", formata cada um e retorna uma lista de dicionários
    {"Nome": ..., "Numero": ...} — uma linha por número válido.
    Se nenhum número válido for encontrado, retorna lista vazia
    (o cliente é descartado).
    """
    todos_numeros_brutos = extrair_numeros(celulares_raw) + extrair_numeros(telefones_raw)

    linhas = []
    numeros_ja_usados = set()  # evita duplicar o mesmo número para o mesmo cliente
    for bruto in todos_numeros_brutos:
        formatado = formatar_celular(bruto)
        if formatado and formatado not in numeros_ja_usados:
            linhas.append({"Nome": nome, "Numero": formatado})
            numeros_ja_usados.add(formatado)

    return linhas


# ---------------------------------------------------------------------------
# LEITURA E PROCESSAMENTO DA PLANILHA
# ---------------------------------------------------------------------------

@st.cache_data(show_spinner=False)
def carregar_planilha(arquivo_bytes: bytes) -> pd.DataFrame:
    """
    Lê o arquivo .xlsx a partir dos bytes enviados via upload.
    header=8 pula as 8 primeiras linhas de metadados e usa a linha 9
    como cabeçalho real das colunas.
    """
    df = pd.read_excel(io.BytesIO(arquivo_bytes), header=HEADER_ROW, dtype=str)

    colunas_esperadas = [COL_NOME, COL_POP, COL_CELULARES, COL_TELEFONES, COL_BAIRRO]
    faltando = [c for c in colunas_esperadas if c not in df.columns]
    if faltando:
        raise ValueError(
            "As seguintes colunas não foram encontradas na planilha: "
            f"{', '.join(faltando)}. Verifique se o arquivo está no "
            "formato esperado (cabeçalho na linha 9)."
        )

    return df


def montar_planilha_final(df_filtrado: pd.DataFrame) -> pd.DataFrame:
    """
    Aplica a lógica de extração/limpeza/formatação em todas as linhas
    já filtradas por POP e Bairro, retornando o DataFrame final com
    apenas as colunas Nome e Numero.
    """
    linhas_finais = []

    for _, linha in df_filtrado.iterrows():
        nome = str(linha.get(COL_NOME, "")).strip()
        celulares_raw = linha.get(COL_CELULARES, "")
        telefones_raw = linha.get(COL_TELEFONES, "")

        if not nome or nome.lower() == "nan":
            continue

        linhas_finais.extend(gerar_linhas_cliente(nome, celulares_raw, telefones_raw))

    return pd.DataFrame(linhas_finais, columns=["Nome", "Numero"])


def gerar_excel_em_memoria(df_final: pd.DataFrame) -> io.BytesIO:
    """
    Gera o arquivo .xlsx final em memória (BytesIO), sem escrever nada
    em disco no servidor. Formato: apenas texto puro, sem bordas,
    sem negrito, idêntico ao template solicitado.
    """
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df_final.to_excel(writer, index=False, sheet_name="Contatos")

    buffer.seek(0)
    return buffer


# ---------------------------------------------------------------------------
# INTERFACE (UI)
# ---------------------------------------------------------------------------

st.title("📞 Extrator de Telefones por POP e Bairro")
st.caption(
    "Faça upload da planilha de clientes, escolha o POP e o Bairro, "
    "e baixe uma planilha limpa apenas com Nome e Número (celular)."
)

arquivo = st.file_uploader(
    "1. Envie a planilha (.xlsx) — tamanho máximo 50 MB",
    type=["xlsx"],
)

if arquivo is not None:
    try:
        df = carregar_planilha(arquivo.getvalue())
    except ValueError as erro:
        st.error(str(erro))
        st.stop()
    except Exception as erro:  # noqa: BLE001 - queremos capturar qualquer erro de leitura
        st.error(f"Não foi possível ler o arquivo. Detalhe técnico: {erro}")
        st.stop()

    st.success(f"Planilha carregada com sucesso! {len(df)} linhas encontradas.")

    # --- Selectbox 1: POP ---
    pops_disponiveis = sorted(df[COL_POP].dropna().unique().tolist())
    pop_selecionado = st.selectbox("2. Selecione o POP", options=pops_disponiveis)

    # --- Selectbox 2: Bairro, filtrado dinamicamente pelo POP escolhido ---
    df_pop = df[df[COL_POP] == pop_selecionado]
    bairros_disponiveis = sorted(df_pop[COL_BAIRRO].dropna().unique().tolist())

    if not bairros_disponiveis:
        st.warning("Nenhum bairro encontrado para o POP selecionado.")
        st.stop()

    bairro_selecionado = st.selectbox("3. Selecione o Bairro", options=bairros_disponiveis)

    # --- Filtro final ---
    df_filtrado = df_pop[df_pop[COL_BAIRRO] == bairro_selecionado]
    st.info(f"{len(df_filtrado)} clientes encontrados para este POP + Bairro.")

    # --- Botão de geração ---
    if st.button("4. Gerar e Baixar Planilha", type="primary"):
        with st.spinner("Processando números e gerando planilha..."):
            df_final = montar_planilha_final(df_filtrado)

        if df_final.empty:
            st.warning(
                "Nenhum número de celular válido foi encontrado para este "
                "filtro. Nenhuma planilha foi gerada."
            )
        else:
            st.success(f"{len(df_final)} números extraídos e formatados com sucesso!")
            st.dataframe(df_final, use_container_width=True)

            excel_buffer = gerar_excel_em_memoria(df_final)

            st.download_button(
                label="⬇️ Baixar Planilha (.xlsx)",
                data=excel_buffer,
                file_name=f"contatos_{pop_selecionado}_{bairro_selecionado}.xlsx".replace(" ", "_"),
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
else:
    st.info("Aguardando upload da planilha .xlsx.")
