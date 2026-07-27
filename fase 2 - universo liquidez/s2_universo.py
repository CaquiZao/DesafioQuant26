"""
Bloco 2 do projeto SINAPSE: montar o universo de acoes mes a mes, usando
liquidez (volume financeiro negociado) como criterio.

REGRA DE FRONTEIRA: este e o UNICO script do projeto que pode ler os
arquivos COTAHIST da B3. Todos os outros blocos devem consumir o arquivo
de saida gerado aqui (data/universo/universo_mensal.parquet), nunca o
COTAHIST diretamente.

O que o script faz, passo a passo:
1. Acha todos os arquivos COTAHIST (.TXT) dentro da pasta configurada,
   varrendo as subpastas por ano.
2. Le cada arquivo linha por linha, mantendo so os registros de cotacao
   (tipo "01") do mercado a vista (TPMERC "010").
3. Soma o volume financeiro negociado de cada acao, mes a mes.
4. Em cada mes, ordena as acoes por volume e pega as 100 mais negociadas
   (esse e o "universo" daquele mes).
5. Salva o resultado em Parquet, com colunas fixas (contrato) que os
   proximos blocos vao usar.
6. Imprime um relatorio de conferencia (sanity check) no final.
"""

import os
import time

import pandas as pd

# ------------------------------------------------------------------
# 1) CONFIGURACOES GERAIS (fica tudo no topo pra ser facil de mudar)
# ------------------------------------------------------------------

# Pasta RAIZ onde estao as subpastas por ano do COTAHIST (fora do repo,
# por isso o caminho e especifico desta maquina). Dentro dela existem
# subpastas tipo "COTAHIST_A2016", "COTAHIST_A2017", etc, e o .TXT fica
# dentro de cada uma.
PASTA_COTAHIST = r"C:\Users\kakam\OneDrive\Documentos\PROJETOS\serie historica cotahist"

# Quantas acoes entram no universo de cada mes (as N mais negociadas).
N_UNIVERSO = 100

# Pasta de saida (dentro do repo, mas ja esta no .gitignore -> nao sobe
# pro Github, so o script fica versionado).
PASTA_SAIDA = os.path.join("data", "universo")
NOME_ARQUIVO_SAIDA = "universo_mensal.parquet"

# Todo registro do COTAHIST tem exatamente essa largura (numero de
# caracteres), sem contar a quebra de linha. Se uma linha vier com
# largura diferente, tratamos como "estranha" e nao processamos ela,
# so avisamos.
LARGURA_ESPERADA = 245

# A B3 usa esse "encoding" (jeito de guardar caracteres em bytes) nos
# arquivos do COTAHIST. Se abrirmos com o encoding errado o programa
# pode travar com erro de leitura.
ENCODING_ARQUIVO = "latin-1"

# A cada quantas linhas lidas o script imprime um "estou vivo, cheguei
# aqui" no terminal, pra dar pra acompanhar o andamento nos arquivos
# grandes.
LINHAS_POR_ATUALIZACAO_PROGRESSO = 2_000_000

# ------------------------------------------------------------------
# 1b) FILTROS DE UNIVERSO -- tirar ETF, BDR e FII (nao sao "acoes de
#     empresa" e atrapalham a estrategia SINAPSE).
#
#     Esses 3 criterios foram testados um por um num diagnostico manual
#     (rodando o script em modo exploratorio nos dados reais) antes de
#     virarem regra fixa aqui. Resumo do que foi descartado e por que:
#       - Tentamos usar so o campo BDI (posicao 11-12) pra tudo, mas ele
#         nao e confiavel: o mesmo ticker aparece com BDI diferente em
#         anos diferentes (ex: BOVA11 aparece como BDI "02" e "14"; nao
#         da pra usar o BDI da linha, tem que ser "o ticker ja apareceu
#         com esse BDI alguma vez no historico").
#       - Tentamos usar o BDI "22" pra achar as units de empresa (tipo
#         SANB11, KLBN11) e separar elas dos ETFs. Nao funcionou: NENHUM
#         dos tickers testados (nem unit nem ETF) apareceu com BDI "22"
#         nos nossos dados. Descartado.
# ------------------------------------------------------------------

# --- Criterio 1: BDR (recibo de acao estrangeira) ---
# Usamos o SUFIXO do ticker (2 ultimos caracteres), NAO o BDI. O sufixo
# se mostrou mais confiavel: 4 BDRs reais (DAGB33, FBOK34, GBIO33,
# INBR31) NUNCA saem do BDI generico "02" no historico todo -- se
# filtrassemos pelo BDI, esses 4 escapariam do filtro por engano.
SUFIXO_BDR_MIN = 31
SUFIXO_BDR_MAX = 39

# --- Criterio 2: FII (fundo imobiliario) ---
# Esses sim tem um BDI proprio e limpo: todo ticker que ja apareceu com
# esse BDI em qualquer momento do historico e um FII.
BDI_FII = "12"

# --- Criterio 3: ETF terminado em "11" ---
# Cuidado: units legitimas de empresa (SANB11, KLBN11, TAEE11, ...)
# TAMBEM terminam em "11" -- por isso so cortamos o "11" quando o
# ticker tambem ja apareceu com o BDI de fundo de indice.
BDI_ETF = "14"

# Excecao manual: tickers que sabemos ser ETF na vida real, mas que a
# B3 nunca marcou com BDI_ETF ("14") nos nossos dados -- ficam sempre
# no BDI generico "02", igual a uma unit legitima, entao nenhum criterio
# automatico consegue pega-los sozinho. Hoje so tem o IBOV11 (ETF do
# Ibovespa). Se no futuro aparecer outro ETF assim, ele entra aqui.
ETFS_EXCECAO_MANUAL = {"IBOV11"}


# ------------------------------------------------------------------
# 2) ENCONTRAR OS ARQUIVOS COTAHIST
# ------------------------------------------------------------------

def encontrar_arquivos_cotahist(pasta_raiz):
    """
    Varre a pasta_raiz e TODAS as suas subpastas, procurando arquivos
    que terminem em ".txt" (maiuscula ou minuscula -- os arquivos da B3
    costumam vir como ".TXT").

    Retorna uma lista de caminhos completos, em ordem alfabetica (o que
    aqui tambem da ordem cronologica, ja que o nome do arquivo tem o ano).
    """
    arquivos_encontrados = []

    # os.walk desce por todas as subpastas sozinho: pra cada pasta que
    # ele visita, devolve (pasta_atual, subpastas_dentro, arquivos_dentro).
    for pasta_atual, _subpastas, arquivos in os.walk(pasta_raiz):
        for nome_arquivo in arquivos:
            if nome_arquivo.lower().endswith(".txt"):
                caminho_completo = os.path.join(pasta_atual, nome_arquivo)
                arquivos_encontrados.append(caminho_completo)

    return sorted(arquivos_encontrados)


# ------------------------------------------------------------------
# 3) LER UM ARQUIVO E SOMAR VOLUME POR (MES, TICKER)
# ------------------------------------------------------------------

def processar_arquivo(caminho_arquivo, volume_por_mes_ticker, bdi_por_ticker):
    """
    Le um arquivo COTAHIST inteiro, linha por linha, e vai somando o
    volume financeiro de cada acao dentro de cada mes.

    volume_por_mes_ticker: dicionario compartilhado entre todos os
    arquivos, no formato {(mes, ticker): volume_acumulado}. A funcao
    ATUALIZA esse dicionario (nao precisa devolver nada).

    bdi_por_ticker: dicionario compartilhado entre todos os arquivos, no
    formato {ticker: {conjunto de codigos BDI ja vistos para ele}}. E
    usado depois pra classificar o ticker como ETF/FII/acao normal.
    """
    tamanho_arquivo_bytes = os.path.getsize(caminho_arquivo)
    print(f"\n--- Processando: {caminho_arquivo}")
    print(f"    tamanho: {tamanho_arquivo_bytes / 1024 / 1024:.1f} MB")

    linhas_lidas = 0
    linhas_tipo01 = 0
    linhas_a_vista = 0
    linhas_largura_errada = 0
    tempo_inicio = time.time()

    # Abrimos o arquivo em modo texto, com o encoding certo. O "with"
    # garante que o arquivo e fechado sozinho no final, mesmo se der erro.
    with open(caminho_arquivo, "r", encoding=ENCODING_ARQUIVO) as arquivo:
        for linha in arquivo:
            # Tira a quebra de linha (\n ou \r\n) do final antes de medir
            # o tamanho, senao a largura sempre bateria errado.
            linha = linha.rstrip("\n").rstrip("\r")
            linhas_lidas += 1

            # ---- checagem de largura (regra de seguranca) ----
            if len(linha) != LARGURA_ESPERADA:
                linhas_largura_errada += 1
                continue  # pula essa linha, nao tenta fatiar ela

            # ---- filtro 1: so registro de cotacao (tipo "01") ----
            # Isso ja descarta sozinho o cabecalho (tipo "00") e o
            # rodape (tipo "99") do arquivo.
            tipreg = linha[0:2]
            if tipreg != "01":
                continue
            linhas_tipo01 += 1

            # ---- filtro 2: so mercado a vista (TPMERC "010") ----
            # Isso evita contar duas vezes o mesmo papel (ex: mercado
            # fracionario, que tem codigo TPMERC "020").
            tpmerc = linha[24:27]
            if tpmerc != "010":
                continue
            linhas_a_vista += 1

            # ---- extrai os campos que interessam ----
            data_pregao = linha[2:10]          # formato AAAAMMDD
            bdi = linha[10:12]                 # codigo BDI (grupo de negociacao)
            ticker = linha[12:24].strip()      # tira os espacos de preenchimento
            texto_volume = linha[170:188]      # 18 digitos, 2 casas decimais implicitas
            volume = int(texto_volume) / 100

            # "mes" no formato "AAAA-MM", ex "2018-05"
            ano = data_pregao[0:4]
            mes_num = data_pregao[4:6]
            mes = f"{ano}-{mes_num}"

            # Soma o volume dessa linha no total do (mes, ticker).
            # dict.get(chave, 0.0) devolve 0.0 se a chave ainda nao existe,
            # entao a soma funciona mesmo na primeira vez que o ticker aparece.
            chave = (mes, ticker)
            volume_por_mes_ticker[chave] = volume_por_mes_ticker.get(chave, 0.0) + volume

            # Guarda que este ticker ja apareceu com este BDI, alguma vez.
            # setdefault cria um conjunto vazio na primeira vez que ve o
            # ticker, e so depois adiciona o bdi -- assim nao apaga o que
            # ja tinha sido visto em arquivos (anos) anteriores.
            bdi_por_ticker.setdefault(ticker, set()).add(bdi)

            # ---- mensagem de progresso, de tempos em tempos ----
            if linhas_lidas % LINHAS_POR_ATUALIZACAO_PROGRESSO == 0:
                segundos_passados = time.time() - tempo_inicio
                print(
                    f"    ... {linhas_lidas:,} linhas lidas "
                    f"({segundos_passados:.0f}s)".replace(",", ".")
                )

    if linhas_largura_errada > 0:
        print(
            f"    AVISO: {linhas_largura_errada} linha(s) com largura "
            f"diferente de {LARGURA_ESPERADA} caracteres foram ignoradas."
        )

    segundos_total = time.time() - tempo_inicio
    print(
        f"    concluido: {linhas_lidas:,} linhas lidas, "
        f"{linhas_tipo01:,} de cotacao, {linhas_a_vista:,} a vista "
        f"({segundos_total:.0f}s)".replace(",", ".")
    )


# ------------------------------------------------------------------
# 4) CLASSIFICAR CADA TICKER (acao / BDR / FII / ETF)
# ------------------------------------------------------------------

def classificar_ticker(ticker, bdi_por_ticker):
    """
    Decide o que um ticker E, pra sabermos se ele fica ou sai do universo.
    Devolve uma destas strings: "acao", "BDR", "FII" ou "ETF".

    A ordem das checagens importa: primeiro BDR (pelo sufixo), depois FII
    (pelo BDI), depois ETF (BDI + excecao manual). Um ticker so cai numa
    categoria se nao se encaixou em nenhuma anterior.
    """
    # ---- BDR: 2 ultimos caracteres do ticker sao digitos 31-39 ----
    sufixo = ticker[-2:]
    if sufixo.isdigit() and SUFIXO_BDR_MIN <= int(sufixo) <= SUFIXO_BDR_MAX:
        return "BDR"

    # bdis_vistos: todos os codigos BDI que esse ticker ja teve, em
    # qualquer mes de qualquer ano do historico.
    bdis_vistos = bdi_por_ticker.get(ticker, set())

    # ---- FII: ja apareceu alguma vez com o BDI de fundo imobiliario ----
    if BDI_FII in bdis_vistos:
        return "FII"

    # ---- ETF: termina em "11" E (ja apareceu com BDI de fundo de indice
    # OU esta na lista manual de excecao) ----
    if ticker.endswith("11") and (BDI_ETF in bdis_vistos or ticker in ETFS_EXCECAO_MANUAL):
        return "ETF"

    # Se nao caiu em nenhum filtro acima, e uma acao normal -- fica.
    return "acao"


# ------------------------------------------------------------------
# 5) TRANSFORMAR O DICIONARIO EM TABELA, FILTRAR, RANQUEAR E CORTAR TOP N
# ------------------------------------------------------------------

def montar_universo_mensal(volume_por_mes_ticker, bdi_por_ticker, n_universo):
    """
    Recebe o dicionario {(mes, ticker): volume_acumulado} e devolve:
      - tabela_universo: DataFrame so com as N acoes mais negociadas de
        cada mes (ja SEM ETF/BDR/FII), colunas mes, ticker, volume_mes, rank.
      - contagem_removidos: dicionario {"BDR": n, "FII": n, "ETF": n} com
        quantos tickers UNICOS (de todo o historico) caíram em cada motivo.
    """
    # Passo 1: transforma o dicionario numa tabela "crua", com uma linha
    # por (mes, ticker) -- ainda sem corte nenhum.
    linhas = [
        {"mes": mes, "ticker": ticker, "volume_mes": volume}
        for (mes, ticker), volume in volume_por_mes_ticker.items()
    ]
    tabela_crua = pd.DataFrame(linhas)

    # Passo 2: classifica cada ticker UNICO uma unica vez (mais rapido do
    # que classificar linha por linha), depois "cola" o motivo de volta
    # em cada linha da tabela crua.
    tickers_unicos = tabela_crua["ticker"].unique()
    motivo_por_ticker = {
        ticker: classificar_ticker(ticker, bdi_por_ticker) for ticker in tickers_unicos
    }
    tabela_crua["motivo"] = tabela_crua["ticker"].map(motivo_por_ticker)

    # Conta quantos tickers UNICOS (nao linhas) caíram em cada motivo de
    # remocao -- serve pro relatorio final.
    tickers_por_motivo = pd.Series(motivo_por_ticker).value_counts()
    contagem_removidos = {
        motivo: int(tickers_por_motivo.get(motivo, 0)) for motivo in ["BDR", "FII", "ETF"]
    }

    # Passo 3: remove as linhas de ETF/BDR/FII ANTES de ranquear -- assim
    # uma acao de verdade que estava no rank 101 sobe pro rank 100 no
    # lugar do fundo/BDR removido, em vez de o mes ficar com menos de 100.
    tabela_filtrada = tabela_crua[tabela_crua["motivo"] == "acao"].copy()

    # Passo 4: dentro de cada mes, ordena do maior volume pro menor.
    tabela_filtrada = tabela_filtrada.sort_values(
        ["mes", "volume_mes"], ascending=[True, False]
    )

    # Passo 5: numera o rank (1, 2, 3, ...) dentro de cada mes.
    # groupby("mes").cumcount() conta a posicao de cada linha dentro do
    # seu grupo (mes), comecando em 0 -- por isso o "+ 1".
    tabela_filtrada["rank"] = tabela_filtrada.groupby("mes").cumcount() + 1

    # Passo 6: mantem so as N primeiras posicoes de cada mes.
    tabela_universo = tabela_filtrada[tabela_filtrada["rank"] <= n_universo].copy()

    # Reorganiza as colunas na ordem pedida e reseta o indice (so estetica).
    tabela_universo = tabela_universo[["mes", "ticker", "volume_mes", "rank"]]
    tabela_universo = tabela_universo.reset_index(drop=True)

    return tabela_universo, contagem_removidos


# ------------------------------------------------------------------
# 5) RELATORIO DE SANIDADE (conferencia visual do resultado)
# ------------------------------------------------------------------

def imprimir_relatorio_sanidade(tabela_universo, contagem_removidos):
    meses_ordenados = sorted(tabela_universo["mes"].unique())
    primeiro_mes = meses_ordenados[0]
    ultimo_mes = meses_ordenados[-1]

    print("\n===== RELATORIO DE SANIDADE =====")
    print(f"Intervalo coberto: {primeiro_mes} até {ultimo_mes}")
    print(f"Total de meses: {len(meses_ordenados)}")

    tickers_unicos = tabela_universo["ticker"].nunique()
    print(
        f"Tickers UNICOS ao longo de todo o periodo: {tickers_unicos} "
        f"(esperado: bem maior que {N_UNIVERSO}, senao o universo nao "
        f"estaria mudando no tempo)"
    )

    def top10_do_mes(mes):
        tabela_mes = tabela_universo[tabela_universo["mes"] == mes]
        tabela_mes = tabela_mes.sort_values("rank").head(10)
        return list(tabela_mes["ticker"])

    print(f"\nTop 10 do primeiro mes ({primeiro_mes}):")
    print(top10_do_mes(primeiro_mes))

    print(f"\nTop 10 do ultimo mes ({ultimo_mes}):")
    print(top10_do_mes(ultimo_mes))

    # Tickers que estavam no universo do primeiro mes mas sumiram do
    # universo do ultimo mes -- candidatos a "saiu da bolsa" ou "ficou
    # ilíquido", e prova de que o survivorship bias esta sendo evitado.
    tickers_inicio = set(
        tabela_universo[tabela_universo["mes"] == primeiro_mes]["ticker"]
    )
    tickers_fim = set(
        tabela_universo[tabela_universo["mes"] == ultimo_mes]["ticker"]
    )
    tickers_sumiram = sorted(tickers_inicio - tickers_fim)

    print(
        f"\nTickers no universo de {primeiro_mes} que NAO estao mais no "
        f"universo de {ultimo_mes} ({len(tickers_sumiram)} no total, "
        f"mostrando até 20):"
    )
    print(tickers_sumiram[:20])

    print("\nRemovidos por filtro (tickers UNICOS de todo o historico):")
    print(f"  BDR: {contagem_removidos['BDR']}")
    print(f"  FII: {contagem_removidos['FII']}")
    print(f"  ETF: {contagem_removidos['ETF']}")

    # ---- salvaguarda: tickers terminados em "11" que sobraram no universo ----
    # Serve pra revisar a olho se algum ETF escapou do filtro automatico.
    # Se essa lista crescer no futuro sem explicacao, e sinal de que
    # apareceu um ETF novo que nao esta no BDI_ETF nem na ETFS_EXCECAO_MANUAL.
    tickers_terminados_em_11 = sorted(
        t for t in tabela_universo["ticker"].unique() if t.endswith("11")
    )
    print(
        f"\nSALVAGUARDA -- tickers terminados em '11' que sobraram no "
        f"universo ({len(tickers_terminados_em_11)}, revisar a olho se "
        f"aparecer algum ETF aqui):"
    )
    print(tickers_terminados_em_11)

    # ---- confirmacoes pontuais pedidas ----
    tickers_no_universo = set(tabela_universo["ticker"].unique())

    print("\nConfirmacao -- devem ter SUMIDO do universo:")
    for ticker_removido in ["BOVA11", "IBOV11", "SMAL11", "AAPL34"]:
        sumiu = ticker_removido not in tickers_no_universo
        print(f"  {ticker_removido}: sumiu = {sumiu}")

    print("\nConfirmacao -- units legitimas devem CONTINUAR no universo:")
    for ticker_deve_ficar in [
        "SANB11", "KLBN11", "TAEE11", "ALUP11", "BPAC11",
        "ENGI11", "SAPR11", "IGTI11", "BIDI11", "BMGB11",
    ]:
        continua = ticker_deve_ficar in tickers_no_universo
        print(f"  {ticker_deve_ficar}: continua = {continua}")


# ------------------------------------------------------------------
# 6) FUNCAO PRINCIPAL
# ------------------------------------------------------------------

def main():
    arquivos = encontrar_arquivos_cotahist(PASTA_COTAHIST)
    print(f"Encontrados {len(arquivos)} arquivo(s) COTAHIST em {PASTA_COTAHIST}")
    for caminho in arquivos:
        print(f"  - {caminho}")

    if not arquivos:
        print("Nenhum arquivo encontrado. Verifique PASTA_COTAHIST. Encerrando.")
        return

    # Dicionario compartilhado que vai acumulando o volume de TODOS os
    # arquivos, mes a mes.
    volume_por_mes_ticker = {}

    # Dicionario compartilhado que vai guardando, pra cada ticker, todos
    # os codigos BDI que ele ja teve em qualquer mes/ano do historico.
    bdi_por_ticker = {}

    for caminho in arquivos:
        processar_arquivo(caminho, volume_por_mes_ticker, bdi_por_ticker)

    print("\nMontando o universo mensal (filtro de ETF/BDR/FII, ranking e corte top N)...")
    tabela_universo, contagem_removidos = montar_universo_mensal(
        volume_por_mes_ticker, bdi_por_ticker, N_UNIVERSO
    )

    # Garante que a pasta de saida existe (cria, se nao existir).
    os.makedirs(PASTA_SAIDA, exist_ok=True)
    caminho_saida = os.path.join(PASTA_SAIDA, NOME_ARQUIVO_SAIDA)
    tabela_universo.to_parquet(caminho_saida, engine="pyarrow", index=False)
    print(f"Universo mensal salvo em: {caminho_saida}")

    imprimir_relatorio_sanidade(tabela_universo, contagem_removidos)


if __name__ == "__main__":
    main()
