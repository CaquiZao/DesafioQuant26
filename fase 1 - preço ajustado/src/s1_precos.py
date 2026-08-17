"""
Bloco 1 do projeto SINAPSE: baixar precos ajustados de acoes brasileiras.

Este script:
1. Descobre a lista de tickers a baixar -- ou o universo completo (253 acoes)
   que veio do Bloco 2, ou uma lista curta fixa (modo teste).
2. Baixa precos historicos ja ajustados (por dividendo e desdobramento) via yfinance,
   um ticker de cada vez, com uma pequena PAUSA entre pedidos (pra nao levar
   bloqueio do Yahoo por excesso de requisicoes) e ATE 2 TENTATIVAS por ticker
   antes de desistir. Nunca para o script todo se um ticker falhar.
3. Monta uma tabela de precos e uma tabela de retornos diarios, ambas em formato "largo"
   (cada coluna e um ticker, cada linha e uma data).
4. Salva as duas tabelas em arquivos Parquet.
5. Em vez de plotar um grafico por acao (o que nao faz sentido com 253 acoes),
   roda um conjunto de VERIFICACOES AUTOMATICAS: grafico-amostra, retornos
   extremos, cobertura de dados e diagnostico dos tickers faltantes (separando
   quem parece ter sido bloqueio temporario do Yahoo de quem parece ter saido
   mesmo da bolsa).

Alem disso, o script usa 2 arquivos de configuracao (pasta config/) pra
tratar os casos ja investigados manualmente:
  - tickers_depara.csv: tickers que MUDARAM DE CODIGO (renomeacao/fusao
    confirmada). O preco e baixado pelo codigo NOVO, mas a coluna final
    da tabela usa o codigo do UNIVERSO -- assim o resto do projeto, que
    usa os nomes do Bloco 2, encontra a serie normalmente.
  - tickers_sem_preco.csv: tickers que ja sabemos que NAO tem fonte de
    preco confiavel (empresa extinta, sucessor fora do escopo, etc.).
    Esses sao pulados no download -- nao adianta gastar tempo tentando
    de novo.
"""

import os
import time

import matplotlib
# "Agg" e um modo do matplotlib que so desenha o grafico em arquivo,
# sem tentar abrir uma janela na tela. Precisa vir antes de importar pyplot.
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
import yfinance as yf

# ------------------------------------------------------------------
# 1) CONFIGURACOES GERAIS (fica tudo no topo pra ser facil de mudar)
# ------------------------------------------------------------------

# MODO decide de onde vem a lista de tickers:
#   "universo" -> le os tickers unicos do arquivo do Bloco 2 (o padrao,
#                 usa o universo inteiro de acoes liquidas -- hoje sao 253).
#   "teste"    -> usa so os 2 tickers de TICKERS_TESTE, pra rodar rapido
#                 e conferir se o script ainda esta funcionando.
MODO = "universo"

# Lista curta usada so quando MODO = "teste".
TICKERS_TESTE = ["PETR4", "VALE3"]

# Caminho do arquivo gerado pelo Bloco 2 (universo de liquidez). E um
# caminho RELATIVO: supoe que o script e rodado com a pasta "fase 1 -
# preco ajustado" como pasta atual (igual ja funciona hoje pra PASTA_SAIDA).
CAMINHO_UNIVERSO = os.path.join(
    "..", "fase 2 - universo liquidez", "data", "universo", "universo_mensal.parquet"
)

# Pasta com os arquivos de configuracao (de-para e exclusao), dentro do
# proprio Bloco 1 -- diferente de data/, esses SAO versionados no Github,
# porque sao decisoes tomadas manualmente (nao dado baixado).
PASTA_CONFIG = "config"

# De-para de tickers renomeados/fundidos: coluna ticker_universo (nome
# usado no Bloco 2 e no resto do projeto) -> ticker_preco (codigo atual,
# usado so na hora de consultar o yfinance).
CAMINHO_DEPARA = os.path.join(PASTA_CONFIG, "tickers_depara.csv")

# Lista de tickers que ja sabemos nao ter fonte de preco confiavel --
# pulados no download em vez de tentar (e falhar) de novo.
CAMINHO_EXCLUSAO = os.path.join(PASTA_CONFIG, "tickers_sem_preco.csv")

# Liga/desliga o uso da lista de exclusao. Deixe True no uso normal --
# so faz sentido False pra depurar/conferir os motivos de falha na mao.
USAR_LISTA_EXCLUSAO = True

# Periodo fixo de dados que queremos baixar.
DATA_INICIO = "2016-01-01"
DATA_FIM = "2025-12-31"

# Pasta onde vamos salvar os resultados (tabelas, graficos e relatorios).
PASTA_SAIDA = os.path.join("data", "precos")

# Tickers conhecidos usados so no grafico-amostra (nao precisam estar
# no universo -- se algum nao existir na tabela baixada, e so pulado).
TICKERS_AMOSTRA_GRAFICO = ["PETR4", "VALE3", "ITUB4", "ABEV3"]

# Um retorno diario com valor absoluto MAIOR que isso (0.50 = 50%) e
# considerado "extremo" -- quase sempre sinal de ajuste mal feito
# (ex: desdobramento nao tratado) ou evento real muito incomum.
LIMIAR_RETORNO_EXTREMO = 0.50

# Tickers com MENOS dias de dado do que isso levam destaque no relatorio
# (pode ser IPO recente, delisting no meio do periodo, ou falha parcial).
MIN_DIAS_COBERTURA = 250

# Pausa entre CADA download (mesmo os que dao certo). Existe so pra reduzir
# a chance de o Yahoo comecar a bloquear os pedidos por excesso de
# requisicoes seguidas (o que aparece como erro "possibly delisted; no
# timezone found" mesmo em tickers validos -- nao e delistagem de verdade).
PAUSA_ENTRE_DOWNLOADS_SEGUNDOS = 1.0

# Se a 1a tentativa de um ticker falhar, esperamos mais um pouco (pausa
# maior que a normal) antes da 2a e ultima tentativa -- da tempo do
# bloqueio temporario do Yahoo (se for esse o caso) passar.
PAUSA_SEGUNDA_TENTATIVA_SEGUNDOS = 5.0


# ------------------------------------------------------------------
# 2) DESCOBRIR A LISTA DE TICKERS (universo do Bloco 2, ou teste)
# ------------------------------------------------------------------

def obter_lista_tickers():
    """
    Devolve a lista de tickers a baixar, de acordo com o MODO configurado
    no topo do arquivo. Se MODO = "universo" e o arquivo do Bloco 2 nao
    existir, avisa com clareza (caminho procurado) e devolve None -- em
    vez de deixar o pandas estourar um erro criptico mais na frente.
    """
    if MODO == "teste":
        print(f"MODO = 'teste': usando lista fixa de {len(TICKERS_TESTE)} ticker(s).")
        return list(TICKERS_TESTE)

    if MODO != "universo":
        raise ValueError(f"MODO invalido: {MODO!r}. Use 'universo' ou 'teste'.")

    if not os.path.exists(CAMINHO_UNIVERSO):
        print("ERRO: nao encontrei o arquivo de universo do Bloco 2.")
        print(f"Caminho procurado: {os.path.abspath(CAMINHO_UNIVERSO)}")
        print(
            "Rode primeiro o script do Bloco 2 (s2_universo.py) para gerar esse "
            "arquivo, ou mude MODO para 'teste' no topo deste script."
        )
        return None

    tabela_universo = pd.read_parquet(CAMINHO_UNIVERSO, engine="pyarrow")

    # unique() pode devolver os tickers em qualquer ordem -- sorted() so
    # deixa o resultado (e o log de progresso) sempre na mesma ordem.
    tickers = sorted(tabela_universo["ticker"].unique().tolist())

    print(
        f"MODO = 'universo': lidos {len(tickers)} ticker(s) unico(s) de "
        f"{CAMINHO_UNIVERSO}"
    )
    return tickers


def carregar_tabela_depara():
    """
    Le config/tickers_depara.csv e devolve um dicionario
    {ticker_universo: ticker_preco}. Se o arquivo nao existir, devolve
    um dicionario vazio (sem depara nenhum) e avisa -- nao trava o script.
    """
    if not os.path.exists(CAMINHO_DEPARA):
        print(f"AVISO: arquivo de de-para nao encontrado em {os.path.abspath(CAMINHO_DEPARA)} (seguindo sem de-para).")
        return {}

    tabela = pd.read_csv(CAMINHO_DEPARA)
    depara = dict(zip(tabela["ticker_universo"], tabela["ticker_preco"]))
    print(f"De-para carregado: {len(depara)} ticker(s) renomeado(s) de {CAMINHO_DEPARA}")
    return depara


def carregar_lista_exclusao():
    """
    Le config/tickers_sem_preco.csv e devolve um dicionario
    {ticker: motivo}. Respeita USAR_LISTA_EXCLUSAO -- se estiver False,
    devolve um dicionario vazio mesmo que o arquivo exista (ninguem e
    pulado). Se o arquivo nao existir, tambem devolve vazio, com aviso.
    """
    if not USAR_LISTA_EXCLUSAO:
        print("USAR_LISTA_EXCLUSAO = False: lista de exclusao ignorada, nenhum ticker sera pulado.")
        return {}

    if not os.path.exists(CAMINHO_EXCLUSAO):
        print(f"AVISO: arquivo de exclusao nao encontrado em {os.path.abspath(CAMINHO_EXCLUSAO)} (seguindo sem exclusao).")
        return {}

    tabela = pd.read_csv(CAMINHO_EXCLUSAO)
    exclusao = dict(zip(tabela["ticker"], tabela["motivo"]))
    print(f"Lista de exclusao carregada: {len(exclusao)} ticker(s) de {CAMINHO_EXCLUSAO}")
    return exclusao


# ------------------------------------------------------------------
# 3) BAIXAR OS PRECOS (um ticker de cada vez, com pausa e retry)
# ------------------------------------------------------------------

def tentar_baixar_um_ticker(ticker, data_inicio, data_fim):
    """
    Faz UMA tentativa de baixar o preco de fechamento ajustado de um ticker.

    Devolve uma dupla (serie, motivo_falha):
      - se deu certo: (serie_de_precos, None)
      - se falhou:    (None, texto curto explicando o motivo)
    """
    # No Yahoo Finance, acoes brasileiras precisam do sufixo ".SA" na
    # CONSULTA. A coluna final da tabela, porem, usa o nome limpo (sem
    # ".SA") -- por isso quem chama esta funcao guarda o resultado com
    # "ticker", nao "ticker_yahoo".
    ticker_yahoo = f"{ticker}.SA"

    # try/except em volta do download: se der QUALQUER erro (rede
    # instavel, Yahoo fora do ar, ticker mal formado, etc.), capturamos
    # aqui em vez de deixar o script inteiro quebrar.
    try:
        dados = yf.download(
            ticker_yahoo,
            start=data_inicio,
            end=data_fim,
            auto_adjust=True,
            progress=False,
        )
    except Exception as erro:
        return None, f"erro ao baixar: {erro}"

    # Se o yfinance nao achou nada, ele devolve uma tabela vazia -- pode
    # ser ticker deslistado, nome errado, OU bloqueio temporario do Yahoo.
    if dados.empty:
        return None, "sem dados"

    # Quando baixamos so 1 ticker por vez, a coluna "Close" pode vir como
    # uma tabela com varias colunas (MultiIndex). Aqui garantimos que
    # vamos pegar so a serie (uma coluna) de fechamento.
    coluna_fechamento = dados["Close"]
    if isinstance(coluna_fechamento, pd.DataFrame):
        coluna_fechamento = coluna_fechamento.iloc[:, 0]

    return coluna_fechamento, None


def baixar_precos_ajustados(tickers, data_inicio, data_fim, tabela_depara=None):
    """
    Baixa, para cada ticker da lista, a serie de precos de fechamento
    ja ajustada por dividendos e desdobramentos.

    tabela_depara: dicionario opcional {ticker_universo: ticker_preco}.
    Quando um ticker da lista tem entrada no de-para, a CONSULTA ao
    yfinance usa o ticker_preco (codigo novo/atual), mas o resultado e
    guardado na tabela final com o nome do ticker_universo (codigo
    antigo) -- assim o resto do projeto, que usa os nomes do Bloco 2,
    continua encontrando a serie normalmente.

    Roda um ticker de cada vez, mostra o progresso (ex: "45/253 ITUB4")
    e espera um pouco entre cada pedido (PAUSA_ENTRE_DOWNLOADS_SEGUNDOS)
    pra reduzir o risco de bloqueio do Yahoo por excesso de requisicoes.

    Cada ticker tem ATE 2 TENTATIVAS: se a 1a falhar, esperamos um pouco
    mais (PAUSA_SEGUNDA_TENTATIVA_SEGUNDOS) e tentamos de novo antes de
    desistir -- assim separamos "falha pontual/bloqueio temporario" de
    "realmente nao tem dado".

    Retorna 4 listas/dicionarios:
        - precos_por_ticker: {ticker_universo: serie_de_precos}, com todo
          ticker que deu certo (na 1a ou na 2a tentativa).
        - tickers_recuperados_2a_tentativa: tickers que SO vieram na 2a
          tentativa -- evidencia de que a 1a falha foi bloqueio/instabilidade
          temporaria, nao delistagem real.
        - tickers_faltantes: tickers que falharam nas DUAS tentativas --
          candidatos a delistagem real (mas ainda precisam ser cruzados
          com o universo do Bloco 2 pra confirmar, ver verificar_ultimo_mes_no_universo).
        - tickers_via_depara: tickers da lista que foram baixados usando
          o codigo do de-para (nao o proprio nome).
    """
    tabela_depara = tabela_depara or {}

    precos_por_ticker = {}
    tickers_recuperados_2a_tentativa = []
    tickers_faltantes = []
    tickers_via_depara = []
    total = len(tickers)

    for posicao, ticker_universo in enumerate(tickers, start=1):
        # Se este ticker mudou de codigo, consultamos o yfinance pelo
        # codigo NOVO (ticker_para_baixar) -- mas o resultado fica
        # guardado sob o nome do universo (ticker_universo).
        ticker_para_baixar = tabela_depara.get(ticker_universo, ticker_universo)
        via_depara = ticker_para_baixar != ticker_universo

        rotulo = f"{ticker_universo} (via {ticker_para_baixar})" if via_depara else ticker_universo
        print(f"[{posicao}/{total}] {rotulo}...", end=" ", flush=True)

        serie, motivo_falha = tentar_baixar_um_ticker(ticker_para_baixar, data_inicio, data_fim)

        if serie is not None:
            precos_por_ticker[ticker_universo] = serie
            if via_depara:
                tickers_via_depara.append(ticker_universo)
            print(f"OK ({len(serie)} dias)")
            time.sleep(PAUSA_ENTRE_DOWNLOADS_SEGUNDOS)
            continue

        # 1a tentativa falhou -- espera mais um pouco e tenta de novo
        # antes de desistir deste ticker.
        print(f"falhou na 1a tentativa ({motivo_falha}), tentando de novo...", end=" ", flush=True)
        time.sleep(PAUSA_SEGUNDA_TENTATIVA_SEGUNDOS)

        serie, motivo_falha = tentar_baixar_um_ticker(ticker_para_baixar, data_inicio, data_fim)

        if serie is not None:
            precos_por_ticker[ticker_universo] = serie
            tickers_recuperados_2a_tentativa.append(ticker_universo)
            if via_depara:
                tickers_via_depara.append(ticker_universo)
            print(f"OK na 2a tentativa ({len(serie)} dias)")
        else:
            tickers_faltantes.append(ticker_universo)
            print(f"FALHOU nas duas tentativas ({motivo_falha})")

        time.sleep(PAUSA_ENTRE_DOWNLOADS_SEGUNDOS)

    return precos_por_ticker, tickers_recuperados_2a_tentativa, tickers_faltantes, tickers_via_depara


def montar_tabela_precos(precos_por_ticker):
    """
    Junta as series de precos de cada ticker em uma unica tabela larga:
    - cada linha e uma data
    - cada coluna e um ticker
    """
    # pd.DataFrame(dict) ja junta tudo pelas datas (index) automaticamente,
    # alinhando cada preco com sua data certa.
    tabela_precos = pd.DataFrame(precos_por_ticker)

    # Coloca as datas em ordem crescente (da mais antiga pra mais nova).
    tabela_precos = tabela_precos.sort_index()

    return tabela_precos


def filtrar_calendario_b3(tabela_precos, caminho_cotahist=None):
    """
    Remove do painel do yfinance as datas em que a B3 NAO abriu.

    POR QUE ISTO EXISTE -- e a CAUSA RAIZ de tres bugs anteriores
    ------------------------------------------------------------
    O yfinance devolve linhas para 36 datas que NAO sao pregao na B3:
    Carnaval, Corpus Christi, Finados, Consciencia Negra, 25/01 (aniversario
    de Sao Paulo), 29/12/2017... Verificado: nenhuma delas existe no COTAHIST,
    que e o arquivo oficial da bolsa.

    Dessas 36 linhas fantasma:
      - 27 vem com preco NaN. O `pct_change()` propaga esse NaN para o
        PRIMEIRO PREGAO REAL seguinte -- o retorno de um dia legitimo vira
        ausente.
      - 9 vem com preco REPETIDO (stale) e geram retorno 0,0 falso para ~124
        tickers.

    A cadeia de dano medida: em 25 pregoes REAIS, apenas ~50 dos 214 tickers
    da carteira tinham retorno (contra mediana de 158). O Bloco 5 lia isso
    como "110 acoes pararam de negociar" e ZERAVA a carteira, com rebuild
    completo no dia seguinte -- 21 liquidacoes espurias, e o giro de 2018
    subindo para 13,5%/dia contra ~3% nos outros anos.

    Foi isso que fez tres correcoes anteriores (clip com NaN, ffill do ADTV,
    guarda de feriado) praticamente nao mexerem no resultado: os tres
    mecanismos disparavam nas MESMAS datas e eram redundantes entre si.
    Enquanto o retorno do dia seguinte continuasse NaN, a carteira zerava de
    qualquer jeito.

    O calendario oficial e o do COTAHIST. Se o arquivo nao existir, nao
    filtramos -- mas avisamos, porque rodar sem ele reintroduz o bug.
    """
    if caminho_cotahist is None:
        base = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        caminho_cotahist = os.path.join(base, "data", "precos", "precos_cotahist.parquet")

    if not os.path.exists(caminho_cotahist):
        print("  AVISO: precos_cotahist.parquet nao encontrado -- calendario da B3 NAO "
              "aplicado. Rode o Bloco 2 antes; sem ele, feriados do yfinance viram "
              "retorno NaN em pregao real.")
        return tabela_precos

    calendario = pd.read_parquet(caminho_cotahist, columns=[]).index
    antes = len(tabela_precos)
    tabela = tabela_precos.loc[tabela_precos.index.isin(calendario)]
    removidas = antes - len(tabela)
    print(f"  calendario da B3: {removidas} data(s) fantasma removida(s) "
          f"({antes} -> {len(tabela)} pregoes)")
    return tabela


def montar_tabela_retornos(tabela_precos):
    """
    Calcula o retorno diario de cada ticker a partir da tabela de precos:
        retorno_hoje = (preco_hoje / preco_ontem) - 1

    A primeira linha fica vazia (NaN) porque nao existe "dia anterior"
    para o primeiro dia da serie. Isso e esperado.

    O filtro de calendario roda ANTES do pct_change -- e obrigatorio que seja
    antes, porque o dano do feriado fantasma e justamente contaminar o retorno
    do pregao seguinte. Ver `filtrar_calendario_b3`.
    """
    tabela_precos = filtrar_calendario_b3(tabela_precos)
    # pct_change() ja faz exatamente essa conta (preco_hoje / preco_ontem - 1)
    # para cada coluna (cada ticker) separadamente.
    tabela_retornos = tabela_precos.pct_change()
    return tabela_retornos


def salvar_tickers_faltantes(tickers_faltantes, pasta_saida):
    """
    Escreve, um por linha, os tickers que nao conseguimos baixar, no
    arquivo data/precos/faltantes.txt. Com o universo completo, essa
    lista e o resultado MAIS importante do script: sao as candidatas a
    "saiu da bolsa" (deslistagem) que precisam ser tratadas a parte no
    resto do projeto (survivorship bias).
    """
    caminho_arquivo = os.path.join(pasta_saida, "faltantes.txt")
    with open(caminho_arquivo, "w", encoding="utf-8") as arquivo:
        for ticker in tickers_faltantes:
            arquivo.write(ticker + "\n")
    return caminho_arquivo


def verificar_ultimo_mes_no_universo(tickers_faltantes, caminho_universo):
    """
    Para cada ticker que falhou nas DUAS tentativas de download, procura
    no arquivo do Bloco 2 (universo de liquidez) qual foi o ULTIMO mes em
    que esse ticker apareceu no universo -- em toda a historia (2016-01
    a 2025-12), nao so num periodo especifico.

    A logica pra separar "delistagem real" de "ainda e so problema de
    download" e simples:
      - Se o ultimo mes no universo for BEM ANTES do ultimo mes coberto
        pelo Bloco 2 (ex: parou em 2021-03, mas o Bloco 2 vai ate
        2025-12): e evidencia de que a acao realmente saiu da bolsa ali
        (delistagem real).
      - Se o ultimo mes no universo for igual (ou quase igual) ao ultimo
        mes coberto pelo Bloco 2: e SUSPEITO -- a acao provavelmente
        ainda estava sendo negociada normalmente, entao o problema foi
        mesmo no download (ex: bloqueio do Yahoo que nem o retry resolveu,
        ou o ticker mudou de codigo).

    Devolve uma dupla (tabela_diagnostico, ultimo_mes_do_bloco2):
      - tabela_diagnostico: colunas ticker, ultimo_mes_no_universo,
        suspeita_ainda_negociando (True/False).
      - ultimo_mes_do_bloco2: o ultimo mes coberto pelo Bloco 2 inteiro
        (ex: "2025-12"), usado como referencia no relatorio. Vem None
        se o arquivo do Bloco 2 nao existir.
    """
    colunas_vazias = ["ticker", "ultimo_mes_no_universo", "suspeita_ainda_negociando"]

    if not tickers_faltantes:
        return pd.DataFrame(columns=colunas_vazias), None

    if not os.path.exists(caminho_universo):
        print(
            "AVISO: nao foi possivel checar o ultimo mes no universo do Bloco 2 "
            f"(arquivo nao encontrado em {os.path.abspath(caminho_universo)})."
        )
        return pd.DataFrame(columns=colunas_vazias), None

    tabela_universo = pd.read_parquet(caminho_universo, engine="pyarrow")

    # ultimo mes em que CADA ticker do universo inteiro apareceu (nao so
    # os que falharam) -- pra depois so consultar o que interessa.
    ultimo_mes_por_ticker = tabela_universo.groupby("ticker")["mes"].max()

    # ultimo mes coberto pelo Bloco 2 inteiro -- e o "ponto de referencia":
    # ainda estar no universo neste mes = provavelmente ainda existe.
    ultimo_mes_do_bloco2 = tabela_universo["mes"].max()

    linhas = []
    for ticker in tickers_faltantes:
        ultimo_mes = ultimo_mes_por_ticker.get(ticker)

        linhas.append(
            {
                "ticker": ticker,
                "ultimo_mes_no_universo": ultimo_mes if ultimo_mes is not None else "nunca apareceu",
                "suspeita_ainda_negociando": (ultimo_mes == ultimo_mes_do_bloco2),
            }
        )

    tabela_diagnostico = pd.DataFrame(linhas)
    return tabela_diagnostico, ultimo_mes_do_bloco2


# ------------------------------------------------------------------
# 4) VERIFICACOES AUTOMATICAS (no lugar de 253 graficos)
# ------------------------------------------------------------------

def gerar_grafico_amostra(tabela_precos, pasta_saida):
    """
    Gera UM grafico so, com uma amostra de 4 acoes conhecidas (definidas
    em TICKERS_AMOSTRA_GRAFICO), so pra conferir visualmente se os dados
    baixados fazem sentido. Se algum desses tickers nao estiver na tabela
    (ex: modo teste, que so tem PETR4/VALE3), ele e simplesmente pulado.
    """
    tickers_disponiveis = [t for t in TICKERS_AMOSTRA_GRAFICO if t in tabela_precos.columns]

    if not tickers_disponiveis:
        print("AVISO: nenhum dos tickers da amostra esta disponivel para o grafico.")
        return None

    plt.figure(figsize=(10, 5))

    for ticker in tickers_disponiveis:
        plt.plot(tabela_precos.index, tabela_precos[ticker], label=ticker)

    plt.title("Preco ajustado de fechamento - amostra de acoes")
    plt.xlabel("Data")
    plt.ylabel("Preco ajustado (R$)")
    plt.legend()
    plt.tight_layout()

    caminho_grafico = os.path.join(pasta_saida, "amostra_4_acoes.png")
    plt.savefig(caminho_grafico)
    # Fecha a figura pra liberar memoria (nao precisamos mostrar na tela).
    plt.close()

    return caminho_grafico


def encontrar_retornos_extremos(tabela_retornos, limiar):
    """
    Procura, em TODA a tabela de retornos, os dias em que algum ticker
    teve retorno diario acima de +limiar ou abaixo de -limiar (ex: acima
    de +50% ou abaixo de -50%). Isso costuma pegar ajustes malfeitos
    (desdobramento nao refletido no preco) ou eventos reais extremos.

    Devolve uma tabela "longa" com uma linha por caso, colunas:
    ticker, data, retorno -- ja ordenada do retorno mais negativo pro
    mais positivo (assim os "piores" casos ficam no topo).
    """
    tabela = tabela_retornos.copy()
    tabela.index.name = "data"

    # reset_index + melt transforma a tabela larga (1 coluna por ticker)
    # numa tabela longa (1 linha por combinacao data+ticker) -- fica mais
    # facil de filtrar e de ler.
    tabela_longa = tabela.reset_index().melt(
        id_vars="data", var_name="ticker", value_name="retorno"
    )

    # Tira as linhas sem retorno (primeiro dia de cada ticker, sempre NaN).
    tabela_longa = tabela_longa.dropna(subset=["retorno"])

    extremos = tabela_longa[tabela_longa["retorno"].abs() > limiar].copy()
    extremos = extremos.sort_values("retorno")  # mais negativo primeiro
    extremos = extremos[["ticker", "data", "retorno"]].reset_index(drop=True)

    return extremos


def calcular_cobertura(tabela_precos):
    """
    Para cada ticker (coluna), conta quantos dias tem dado de verdade
    (nao-NaN) e qual a primeira e a ultima data com dado. Serve pra
    achar tickers com historico curto (IPO recente, delisting no meio
    do periodo, ou uma falha parcial no download).
    """
    linhas = []
    for ticker in tabela_precos.columns:
        serie = tabela_precos[ticker]
        primeira_data_valida = serie.first_valid_index()
        ultima_data_valida = serie.last_valid_index()

        linhas.append(
            {
                "ticker": ticker,
                "dias_com_dado": int(serie.notna().sum()),
                "primeira_data": primeira_data_valida.date() if primeira_data_valida is not None else None,
                "ultima_data": ultima_data_valida.date() if ultima_data_valida is not None else None,
            }
        )

    tabela_cobertura = pd.DataFrame(linhas).sort_values("dias_com_dado").reset_index(drop=True)
    return tabela_cobertura


# ------------------------------------------------------------------
# 5) FUNCAO PRINCIPAL
# ------------------------------------------------------------------

def main():
    # Garante que a pasta de saida existe (cria, se nao existir).
    os.makedirs(PASTA_SAIDA, exist_ok=True)

    # Passo 1: descobrir quais tickers baixar (universo do Bloco 2, ou teste).
    tickers = obter_lista_tickers()
    if not tickers:
        print("Nenhum ticker para baixar. Encerrando o script.")
        return

    # Passo 1b: carregar de-para (renomeacoes confirmadas) e lista de
    # exclusao (tickers sem fonte de preco confiavel, ja investigados).
    tabela_depara = carregar_tabela_depara()
    lista_exclusao = carregar_lista_exclusao()

    # Separa os tickers do universo em "pular" (estao na exclusao) e
    # "tentar baixar" (todo o resto, incluindo os que tem de-para).
    tickers_excluidos = [t for t in tickers if t in lista_exclusao]
    tickers_para_baixar = [t for t in tickers if t not in lista_exclusao]

    if tickers_excluidos:
        print(
            f"\n{len(tickers_excluidos)} ticker(s) pulado(s) por estarem na lista de "
            f"exclusao (nao serao baixados): {tickers_excluidos}"
        )

    # Passo 2: baixar os precos de cada ticker (com pausa, retry e de-para).
    precos_por_ticker, tickers_recuperados_2a_tentativa, tickers_faltantes, tickers_via_depara = baixar_precos_ajustados(
        tickers_para_baixar, DATA_INICIO, DATA_FIM, tabela_depara=tabela_depara
    )

    if not precos_por_ticker:
        print("Nenhum ticker foi baixado com sucesso. Encerrando o script.")
        salvar_tickers_faltantes(tickers_faltantes, PASTA_SAIDA)
        return

    # Passo 3: montar a TABELA 1 (precos) e a TABELA 2 (retornos).
    tabela_precos = montar_tabela_precos(precos_por_ticker)
    tabela_retornos = montar_tabela_retornos(tabela_precos)

    # Passo 4: salvar as duas tabelas em Parquet.
    caminho_precos = os.path.join(PASTA_SAIDA, "precos_ajustados.parquet")
    caminho_retornos = os.path.join(PASTA_SAIDA, "retornos_diarios.parquet")
    tabela_precos.to_parquet(caminho_precos, engine="pyarrow")
    tabela_retornos.to_parquet(caminho_retornos, engine="pyarrow")

    # Passo 5: salvar a lista de tickers que falharam (mesmo que esteja vazia).
    caminho_faltantes = salvar_tickers_faltantes(tickers_faltantes, PASTA_SAIDA)

    # Passo 5b: para quem falhou nas duas tentativas, checa no Bloco 2
    # qual foi o ultimo mes no universo -- ajuda a separar delistagem
    # real de suspeita de bloqueio do Yahoo.
    tabela_diagnostico_faltantes, ultimo_mes_do_bloco2 = verificar_ultimo_mes_no_universo(
        tickers_faltantes, CAMINHO_UNIVERSO
    )
    caminho_diagnostico = os.path.join(PASTA_SAIDA, "diagnostico_faltantes.csv")
    tabela_diagnostico_faltantes.to_csv(caminho_diagnostico, index=False)

    # Passo 6: grafico-amostra (so 4 acoes conhecidas, nao 253 graficos).
    caminho_grafico = gerar_grafico_amostra(tabela_precos, PASTA_SAIDA)

    # Passo 7: retornos extremos (possiveis erros de ajuste ou eventos raros).
    tabela_extremos = encontrar_retornos_extremos(tabela_retornos, LIMIAR_RETORNO_EXTREMO)
    caminho_extremos = os.path.join(PASTA_SAIDA, "retornos_extremos.csv")
    tabela_extremos.to_csv(caminho_extremos, index=False)

    # Passo 8: cobertura de dados (dias, primeira e ultima data por ticker).
    tabela_cobertura = calcular_cobertura(tabela_precos)
    caminho_cobertura = os.path.join(PASTA_SAIDA, "cobertura.csv")
    tabela_cobertura.to_csv(caminho_cobertura, index=False)
    tickers_baixa_cobertura = tabela_cobertura[
        tabela_cobertura["dias_com_dado"] < MIN_DIAS_COBERTURA
    ]

    # ------------------------------------------------------------------
    # Relatorio final no terminal
    # ------------------------------------------------------------------
    baixados_diretos = len(precos_por_ticker) - len(tickers_via_depara)
    cobertura_final_pct = 100 * len(precos_por_ticker) / len(tickers)

    print("\n===== RESUMO =====")
    print(f"Total no universo (Bloco 2): {len(tickers)}")
    print(f"Baixados diretos (proprio codigo): {baixados_diretos}")
    print(f"Baixados via de-para (codigo renomeado): {len(tickers_via_depara)} -> {tickers_via_depara}")
    print(f"Excluidos (pulados, ja investigados): {len(tickers_excluidos)}")
    print(f"Faltantes novos (nao previstos no de-para/exclusao): {len(tickers_faltantes)}")
    print(f"Cobertura final: {len(precos_por_ticker)}/{len(tickers)} = {cobertura_final_pct:.1f}% do universo com preco")
    print(f"Linhas (dias) na tabela de precos: {len(tabela_precos)}")

    if len(tabela_precos) > 0:
        primeira_data = tabela_precos.index.min().date()
        ultima_data = tabela_precos.index.max().date()
        print(f"Intervalo de datas: {primeira_data} ate {ultima_data}")

    # ---- excluidos, quebrados por motivo ----
    if tickers_excluidos:
        contagem_por_motivo = pd.Series(
            [lista_exclusao[t] for t in tickers_excluidos]
        ).value_counts()
        print(f"\n--- EXCLUIDOS POR MOTIVO ({len(tickers_excluidos)} no total) ---")
        for motivo, contagem in contagem_por_motivo.items():
            print(f"  {motivo}: {contagem}")

    # ---- grupo (a): recuperados na 2a tentativa -> era bloqueio/instabilidade ----
    print(
        f"\n--- (a) RECUPERADOS NA 2a TENTATIVA (era bloqueio/instabilidade "
        f"temporaria, nao delistagem): {len(tickers_recuperados_2a_tentativa)} ---"
    )
    if tickers_recuperados_2a_tentativa:
        print(tickers_recuperados_2a_tentativa)
    else:
        print("Nenhum -- todo ticker que deu certo, deu certo ja na 1a tentativa.")

    # ---- grupo (b): falharam nas duas tentativas -> candidatos a delistagem real ----
    print(
        f"\n--- (b) FALHARAM NAS DUAS TENTATIVAS (candidatos a delistagem real): "
        f"{len(tickers_faltantes)} ---"
    )
    if tickers_faltantes:
        print(tickers_faltantes)
        print(
            "\nDiagnostico -- ultimo mes de cada um no universo do Bloco 2 "
            f"(referencia: universo vai ate {ultimo_mes_do_bloco2 or 'N/D'}):"
        )
        print(tabela_diagnostico_faltantes.to_string(index=False))

        n_suspeitos = int(tabela_diagnostico_faltantes["suspeita_ainda_negociando"].sum())
        n_delistagem_provavel = len(tabela_diagnostico_faltantes) - n_suspeitos
        print(
            f"\n  -> {n_delistagem_provavel} com ultimo mes BEM ANTES do fim do "
            "periodo: evidencia de delistagem REAL."
        )
        print(
            f"  -> {n_suspeitos} com ultimo mes ATE o fim do periodo coberto "
            "pelo Bloco 2: SUSPEITO -- provavelmente ainda existiam e o "
            "problema foi so no download (nao confiar como delistagem)."
        )
    else:
        print("Nenhum ticker faltante.")

    print(
        f"\n--- RETORNOS EXTREMOS (|retorno diario| > {LIMIAR_RETORNO_EXTREMO:.0%}): "
        f"{len(tabela_extremos)} caso(s) ---"
    )
    if len(tabela_extremos) > 0:
        print("10 piores (maiores quedas):")
        print(tabela_extremos.head(10).to_string(index=False))

    print(
        f"\n--- COBERTURA: {len(tickers_baixa_cobertura)} ticker(s) com menos de "
        f"{MIN_DIAS_COBERTURA} dias de dado ---"
    )
    if len(tickers_baixa_cobertura) > 0:
        if len(tickers_baixa_cobertura) <= 20:
            print(tickers_baixa_cobertura.to_string(index=False))
        else:
            print(f"(mostrando 20 de {len(tickers_baixa_cobertura)}, lista completa no CSV)")
            print(tickers_baixa_cobertura.head(20).to_string(index=False))

    print(f"\nTabela de precos salva em: {caminho_precos}")
    print(f"Tabela de retornos salva em: {caminho_retornos}")
    print(f"Faltantes salvos em: {caminho_faltantes}")
    print(f"Diagnostico dos faltantes salvo em: {caminho_diagnostico}")
    print(f"Retornos extremos salvos em: {caminho_extremos}")
    print(f"Cobertura salva em: {caminho_cobertura}")
    if caminho_grafico:
        print(f"Grafico de amostra salvo em: {caminho_grafico}")


if __name__ == "__main__":
    main()
