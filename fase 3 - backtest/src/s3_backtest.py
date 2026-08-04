"""
Bloco 3 do projeto SINAPSE: o motor de backtest.

Este script consome o output real da Sinapse: a matriz diaria de pesos
gerada pelo Bloco 5 (`df_weights_sinapse.parquet`), com o lag de execucao
T+1 ja aplicado nativamente (`df_weights.shift(1)` dentro do
`PortfolioBuilder`). O motor nao decide mais nada -- so multiplica pesos
por retornos, dia a dia, de forma vetorizada.

O script:
1. Carrega os retornos diarios (Bloco 1, `retornos_diarios.parquet`) e a
   matriz de pesos da Sinapse (Bloco 5, `df_weights_sinapse.parquet`) --
   colunas = tickers + `IBOV_SYNTHETIC` (o hedge vendido de Ibovespa que
   deixa a carteira beta-neutra).
2. Carrega o retorno diario do Ibovespa (preferencialmente do parquet ja
   calculado pelo Bloco 1.5; se nao existir, baixa via yfinance) e injeta
   essa serie em `retornos_diarios` sob a coluna `IBOV_SYNTHETIC`, pra que
   a multiplicacao matricial pesos * retornos funcione sem KeyError.
3. Roda o MOTOR: multiplicacao matricial direta `(pesos * retornos).sum(
   axis=1)`, sem loop, sem rebalanceamento mensal, sem renormalizacao --
   a matriz de pesos ja vem pronta e alinhada do Bloco 5. Desconta custo
   de transacao proporcional ao giro diario (soma das mudancas absolutas
   de peso dia a dia).
4. Alinha a curva da estrategia com a curva do Ibovespa pelas datas em
   comum e roda um TESTE DE SANIDADE: como a estrategia e beta-neutra
   (hedge de Ibovespa embutido via `IBOV_SYNTHETIC`), a correlacao diaria
   esperada com o Ibovespa e PROXIMA DE ZERO -- correlacao alta indicaria
   que o hedge nao esta funcionando.
5. Salva a curva diaria em Parquet e um grafico comparativo em PNG.
"""

import json
import os
import urllib.request

import matplotlib
# "Agg" e um modo do matplotlib que so desenha o grafico em arquivo, sem
# tentar abrir uma janela na tela. Precisa vir antes de importar pyplot.
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
import yfinance as yf

# ------------------------------------------------------------------
# 1) CONFIGURACOES GERAIS (fica tudo no topo pra ser facil de mudar)
# ------------------------------------------------------------------

# Raiz do repositorio, resolvida a partir deste arquivo (mesmo padrao do
# Bloco 5 em exec_s5.py) -- assim os caminhos funcionam independente da
# pasta de onde o script e chamado.
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_DIR = os.path.join(BASE_DIR, "data")

# Base COMPLETA de retornos (Bloco 1c): inclui as acoes ja deslistadas,
# entao nao carrega vies de sobrevivencia. Cai na base antiga (so
# yfinance, so sobreviventes) se o Bloco 1c ainda nao tiver rodado.
CAMINHO_RETORNOS = os.path.join(DATA_DIR, "precos", "retornos_diarios_completo.parquet")
if not os.path.exists(CAMINHO_RETORNOS):
    CAMINHO_RETORNOS = os.path.join(DATA_DIR, "precos", "retornos_diarios.parquet")
CAMINHO_PESOS_SINAPSE = os.path.join(DATA_DIR, "df_weights_sinapse.parquet")
CAMINHO_INDICES = os.path.join(DATA_DIR, "precos", "indices_retornos.parquet")

# Cache local do CDI (benchmark oficial). Se nao existir, o script busca na
# API do Banco Central e cria o arquivo -- ver carregar_retorno_cdi.
CAMINHO_CDI = os.path.join(DATA_DIR, "precos", "cdi_diario.parquet")

# Ticker do Ibovespa no Yahoo Finance (indice, nao acao -- por isso o "^").
# So usado como fallback, se CAMINHO_INDICES nao existir.
TICKER_IBOVESPA = "^BVSP"

# Pasta onde salvamos os resultados deste bloco (curva, grafico).
PASTA_SAIDA = os.path.join(DATA_DIR, "backtest")

# Custo de transacao por unidade de giro (turnover) diario. giro_diario
# (ver rodar_motor) soma a mudanca ABSOLUTA de peso dos dois lados (o que
# entra + o que sai), entao 0.0005 aqui representa 0.05% (5 bps) sobre
# esse giro de "duas pontas" -- estimativa de corretagem + emolumentos +
# slippage moderado para acoes liquidas brasileiras.
CUSTO = 0.0005

# Taxa livre de risco anual, usada no calculo do Sharpe (retorno em
# EXCESSO sobre essa taxa). Por enquanto 0.0 -- ajustar depois pra uma
# proxy real (CDI/Selic anualizada), se o time decidir incluir.
TAXA_LIVRE_ANUAL = 0.0

# Dias uteis no ano, usado pra anualizar o Sharpe (padrao de mercado).
DIAS_UTEIS_ANO = 252


# ------------------------------------------------------------------
# 2) CARREGAR INSUMOS (Bloco 1 e Bloco 5)
# ------------------------------------------------------------------

def carregar_retornos_diarios(caminho):
    """
    Le o Parquet do Bloco 1: formato largo, indice = datas diarias,
    colunas = tickers LIMPOS (sem ".SA"), valores = retorno diario.
    """
    return pd.read_parquet(caminho)


def carregar_pesos_sinapse(caminho):
    """
    Le o Parquet do Bloco 5: formato largo, indice = datas diarias,
    colunas = tickers + `IBOV_SYNTHETIC` (peso do hedge de Ibovespa),
    valores = peso percentual (positivo = LONG, negativo = SHORT). O lag
    de execucao T+1 ja vem aplicado nativamente -- o peso no dia T ja e o
    peso que deve ser multiplicado pelo retorno do dia T.
    """
    return pd.read_parquet(caminho)


# ------------------------------------------------------------------
# 3) IBOVESPA (referencia externa + insumo do hedge IBOV_SYNTHETIC)
# ------------------------------------------------------------------

def baixar_retornos_ibovespa(data_inicio, data_fim):
    """
    Baixa o retorno diario do Ibovespa (^BVSP) via yfinance. FALLBACK: so
    e usado se CAMINHO_INDICES nao existir -- o caminho principal e ler o
    parquet ja calculado pelo Bloco 1.5 (s1b_indices.py).
    """
    dados = yf.download(
        TICKER_IBOVESPA, start=data_inicio, end=data_fim, auto_adjust=True, progress=False
    )
    fechamento = dados["Close"]
    if isinstance(fechamento, pd.DataFrame):
        fechamento = fechamento.iloc[:, 0]
    return fechamento.pct_change().dropna()


def carregar_retorno_ibovespa(caminho_indices, data_inicio, data_fim):
    """
    Devolve a serie de retorno diario do Ibovespa. Preferencialmente le
    `indices_retornos.parquet` (Bloco 1.5, coluna "IBOV" com fallback
    "IBOV_ETF" ja tratado na origem); se o arquivo nao existir, baixa via
    yfinance (`baixar_retornos_ibovespa`).
    """
    if os.path.exists(caminho_indices):
        indices = pd.read_parquet(caminho_indices)
        return indices["IBOV"].dropna()
    return baixar_retornos_ibovespa(data_inicio, data_fim)


# ------------------------------------------------------------------
# 3b) CDI (benchmark oficial do fundo e taxa livre de risco)
# ------------------------------------------------------------------

def carregar_retorno_cdi(caminho_cdi, data_inicio, data_fim):
    """
    Devolve a serie de retorno diario do CDI (taxa livre de risco e
    benchmark oficial de performance deste projeto).

    Le do cache local se existir; senao busca na API publica de series
    temporais do Banco Central (SGS, serie 12 = CDI diario) e salva o
    cache, pra nao depender de rede nas execucoes seguintes.

    A API devolve a taxa em PERCENTUAL ao dia (ex: "0.052496" = 0,0525%
    no dia), por isso a divisao por 100.
    """
    if os.path.exists(caminho_cdi):
        return pd.read_parquet(caminho_cdi)["CDI"].dropna()

    print("  CDI nao encontrado em cache -- buscando na API do Banco Central...")
    url = (
        "https://api.bcb.gov.br/dados/serie/bcdata.sgs.12/dados?formato=json"
        f"&dataInicial={pd.Timestamp(data_inicio).strftime('%d/%m/%Y')}"
        f"&dataFinal={pd.Timestamp(data_fim).strftime('%d/%m/%Y')}"
    )
    with urllib.request.urlopen(url, timeout=60) as resposta:
        registros = json.load(resposta)

    serie = pd.DataFrame(registros)
    serie["Date"] = pd.to_datetime(serie["data"], format="%d/%m/%Y")
    serie["CDI"] = serie["valor"].astype(float) / 100.0
    serie = serie.set_index("Date")[["CDI"]].sort_index()

    os.makedirs(os.path.dirname(caminho_cdi), exist_ok=True)
    serie.to_parquet(caminho_cdi, engine="pyarrow")
    print(f"  CDI salvo em cache: {caminho_cdi}")

    return serie["CDI"].dropna()


# ------------------------------------------------------------------
# 4) MOTOR: EXECUCAO (multiplicacao matricial diaria direta)
# ------------------------------------------------------------------

def rodar_motor(df_weights, df_returns, custo_por_giro):
    """
    O coracao do Bloco 3. A estrategia real (Sinapse) ja vem com pesos
    diarios prontos e com lag aplicado -- o motor so precisa:
      1. Alinhar `df_weights` e `df_returns` pelas datas em comum.
      2. Calcular o giro diario (soma das mudancas absolutas de peso de
         um dia pro outro) e o custo de transacao correspondente.
      3. Compor o P&L diario: soma ponderada (peso_i * retorno_i) em cada
         dia, menos o custo do dia.

    Devolve uma tupla:
      - retorno_estrategia: Series diaria com o retorno diario JA LIQUIDO
        de custo de transacao.
      - pnl_bruto: o mesmo retorno ANTES do custo (serve pra separar
        "o sinal perdeu dinheiro" de "o custo comeu o resultado").
      - giro_diario: giro (turnover) de cada dia, pra diagnostico.
    """
    datas_em_comum = df_weights.index.intersection(df_returns.index)
    df_weights = df_weights.loc[datas_em_comum].sort_index()
    df_returns = df_returns.loc[datas_em_comum].sort_index()

    df_mudanca = df_weights.fillna(0).diff().abs()
    giro_diario = df_mudanca.sum(axis=1)
    custo_diario = giro_diario * custo_por_giro

    pnl_bruto = (df_weights.fillna(0) * df_returns.fillna(0)).sum(axis=1)
    retorno_estrategia = pnl_bruto - custo_diario.fillna(0)

    return retorno_estrategia, pnl_bruto, giro_diario


# ------------------------------------------------------------------
# 5) METRICAS (retorno total, Sharpe anualizado, drawdown maximo)
# ------------------------------------------------------------------

def calcular_retorno_total(curva):
    """Retorno acumulado do periodo inteiro, a partir da curva de patrimonio."""
    return curva.iloc[-1] / curva.iloc[0] - 1


def calcular_sharpe_anualizado(retorno_diario, taxa_livre_anual, dias_uteis_ano, retorno_livre_diario=None):
    """
    Sharpe = (retorno medio em excesso / desvio-padrao do retorno em
    excesso) * raiz(dias uteis no ano) -- forma padrao de anualizar um
    Sharpe calculado em base diaria.

    Se `retorno_livre_diario` vier preenchido (serie diaria do CDI), ele e
    usado como taxa livre de risco no lugar da taxa anual constante -- que
    e o correto, ja que o CDI variou de ~14% a ~2% ao ano no periodo.
    """
    if retorno_livre_diario is not None:
        livre = retorno_livre_diario.reindex(retorno_diario.index).fillna(0.0)
        excesso = retorno_diario - livre
    else:
        taxa_livre_diaria = (1 + taxa_livre_anual) ** (1 / dias_uteis_ano) - 1
        excesso = retorno_diario - taxa_livre_diaria
    desvio = excesso.std()
    if desvio == 0:
        return float("nan")
    return (excesso.mean() / desvio) * (dias_uteis_ano ** 0.5)


def calcular_drawdown_maximo(curva):
    """Maior queda percentual da curva em relacao ao pico anterior (sempre <= 0)."""
    pico_ate_aqui = curva.cummax()
    drawdown = curva / pico_ate_aqui - 1
    return drawdown.min()


# ------------------------------------------------------------------
# 6) GRAFICO
# ------------------------------------------------------------------

def gerar_grafico_comparativo(curva_estrategia, curva_ibovespa, pasta_saida, curva_cdi=None):
    plt.figure(figsize=(12, 6))
    plt.plot(curva_estrategia.index, curva_estrategia.values, label="Estrategia Sinapse (market-neutral)")
    plt.plot(curva_ibovespa.index, curva_ibovespa.values, label="Ibovespa")
    if curva_cdi is not None:
        plt.plot(curva_cdi.index, curva_cdi.values, label="CDI (benchmark)", linestyle="--")
    plt.title("Bloco 3 -- curva de patrimonio (base 1.0): Sinapse vs Ibovespa vs CDI")
    plt.xlabel("Data")
    plt.ylabel("Patrimonio (base 1.0)")
    plt.legend()
    plt.grid(alpha=0.3)

    caminho = os.path.join(pasta_saida, "curva_patrimonio.png")
    plt.savefig(caminho, dpi=120, bbox_inches="tight")
    plt.close()
    return caminho


# ------------------------------------------------------------------
# 7) MAIN
# ------------------------------------------------------------------

def main():
    os.makedirs(PASTA_SAIDA, exist_ok=True)

    print("Passo 1: carregando retornos diarios (Bloco 1) e pesos da Sinapse (Bloco 5)...")
    retornos_diarios = carregar_retornos_diarios(CAMINHO_RETORNOS)
    pesos_sinapse = carregar_pesos_sinapse(CAMINHO_PESOS_SINAPSE)
    print(
        f"  retornos_diarios: {retornos_diarios.shape[0]} dias, "
        f"{retornos_diarios.shape[1]} tickers com preco"
    )
    print(
        f"  pesos_sinapse: {pesos_sinapse.shape[0]} dias, "
        f"{pesos_sinapse.shape[1]} colunas (tickers + IBOV_SYNTHETIC)"
    )

    print("\nPasso 2: carregando retorno do Ibovespa e injetando IBOV_SYNTHETIC nos retornos...")
    data_inicio = pesos_sinapse.index.min().strftime("%Y-%m-%d")
    data_fim = pesos_sinapse.index.max().strftime("%Y-%m-%d")
    retorno_ibovespa = carregar_retorno_ibovespa(CAMINHO_INDICES, data_inicio, data_fim)
    retornos_diarios = retornos_diarios.copy()
    retornos_diarios["IBOV_SYNTHETIC"] = retorno_ibovespa.reindex(retornos_diarios.index)

    # Dias em que retornos_diarios tem uma data que NAO existe na fonte do
    # Ibovespa (feriado/desalinhamento de calendario entre as duas fontes)
    # ficam com IBOV_SYNTHETIC = NaN. Descartamos esses dias inteiros do
    # backtest em vez de deixar o motor tratar como retorno 0 -- se
    # tratasse como 0, o hedge "desapareceria" silenciosamente naquele
    # dia (peso continua existindo, retorno finge que foi zero), um
    # vazamento de beta nao coberto.
    dias_sem_ibov = retornos_diarios["IBOV_SYNTHETIC"].isna()
    if dias_sem_ibov.any():
        print(
            f"  Aviso: descartando {dias_sem_ibov.sum()} dia(s) sem retorno "
            "do Ibovespa disponivel (evita 'vazamento' do hedge IBOV_SYNTHETIC)."
        )
        retornos_diarios = retornos_diarios.loc[~dias_sem_ibov]

    print("\nPasso 3: rodando o motor (multiplicacao matricial diaria, custo de giro)...")
    retorno_estrategia, pnl_bruto, giro_diario = rodar_motor(
        pesos_sinapse, retornos_diarios, CUSTO
    )
    peso_hedge_max = pesos_sinapse["IBOV_SYNTHETIC"].abs().max()
    print(f"  Peso absoluto maximo observado em IBOV_SYNTHETIC: {peso_hedge_max:.1%}")
    # Convencao de retorno: composicao por (1+r).cumprod() -- retorno
    # simples composto, nunca soma de log-retornos.
    curva_estrategia = (1 + retorno_estrategia.fillna(0)).cumprod()

    print("\nPasso 4: carregando CDI e alinhando as curvas pelas datas em comum...")
    retorno_cdi = carregar_retorno_cdi(CAMINHO_CDI, data_inicio, data_fim)
    curva_ibovespa = (1 + retorno_ibovespa).cumprod()

    # Feriado que existe numa fonte e nao na outra nao pode desalinhar as
    # curvas -- por isso a interseccao dos indices, nunca um merge "as
    # cegas" pela posicao.
    datas_em_comum = curva_estrategia.index.intersection(curva_ibovespa.index)
    if len(datas_em_comum) == 0:
        raise ValueError(
            "Estrategia e Ibovespa nao tem NENHUMA data em comum -- confira a "
            "fonte do retorno do Ibovespa (periodo, feriados, fuso)."
        )

    curva_estrategia = curva_estrategia.loc[datas_em_comum].sort_index()
    curva_ibovespa = curva_ibovespa.loc[datas_em_comum].sort_index()

    # CDI acumulado nas mesmas datas (o CDI so rende em dia util, entao
    # dias sem cotacao entram como 0 e nao como buraco na curva).
    retorno_cdi_alinhado = retorno_cdi.reindex(datas_em_comum).fillna(0.0).sort_index()
    curva_cdi = (1 + retorno_cdi_alinhado).cumprod()

    # Base 1.0 na PRIMEIRA DATA EM COMUM (nao na primeira data de cada
    # serie isolada, que pode ser diferente por causa do lag do Bloco 5).
    curva_estrategia = curva_estrategia / curva_estrategia.iloc[0]
    curva_ibovespa = curva_ibovespa / curva_ibovespa.iloc[0]
    curva_cdi = curva_cdi / curva_cdi.iloc[0]

    print("\nPasso 5: calculando metricas...")
    retorno_diario_estrategia = curva_estrategia.pct_change().dropna()
    retorno_diario_ibovespa = curva_ibovespa.pct_change().dropna()

    # Sharpe medido contra o CDI (taxa livre de risco de verdade -- o CDI
    # variou de ~14% a ~2% ao ano no periodo, entao usar uma constante
    # distorceria a metrica).
    metricas = {
        "estrategia sinapse": {
            "retorno_total": calcular_retorno_total(curva_estrategia),
            "sharpe_anualizado": calcular_sharpe_anualizado(
                retorno_diario_estrategia, TAXA_LIVRE_ANUAL, DIAS_UTEIS_ANO,
                retorno_livre_diario=retorno_cdi_alinhado,
            ),
            "drawdown_maximo": calcular_drawdown_maximo(curva_estrategia),
        },
        "ibovespa": {
            "retorno_total": calcular_retorno_total(curva_ibovespa),
            "sharpe_anualizado": calcular_sharpe_anualizado(
                retorno_diario_ibovespa, TAXA_LIVRE_ANUAL, DIAS_UTEIS_ANO,
                retorno_livre_diario=retorno_cdi_alinhado,
            ),
            "drawdown_maximo": calcular_drawdown_maximo(curva_ibovespa),
        },
        "cdi (benchmark)": {
            "retorno_total": calcular_retorno_total(curva_cdi),
            "sharpe_anualizado": float("nan"),  # Sharpe do proprio livre de risco nao faz sentido
            "drawdown_maximo": calcular_drawdown_maximo(curva_cdi),
        },
    }

    print("\nPasso 6: gerando grafico comparativo...")
    caminho_grafico = gerar_grafico_comparativo(
        curva_estrategia, curva_ibovespa, PASTA_SAIDA, curva_cdi
    )

    print("\nPasso 7: salvando parquet de saida...")
    caminho_curvas = os.path.join(PASTA_SAIDA, "curvas_diarias.parquet")
    tabela_curvas = pd.DataFrame(
        {
            "patrimonio_estrategia": curva_estrategia,
            "patrimonio_ibovespa": curva_ibovespa,
            "patrimonio_cdi": curva_cdi,
        }
    )
    tabela_curvas.to_parquet(caminho_curvas, engine="pyarrow")

    # ------------------------------------------------------------------
    # Teste de sanidade -- O MAIS IMPORTANTE deste bloco
    # ------------------------------------------------------------------
    print("\n===== TESTE DE SANIDADE =====")
    diferenca_retorno_total = (
        metricas["estrategia sinapse"]["retorno_total"] - metricas["ibovespa"]["retorno_total"]
    )
    correlacao_diaria = retorno_diario_estrategia.corr(retorno_diario_ibovespa)

    print(
        f"Retorno total -- estrategia Sinapse: {metricas['estrategia sinapse']['retorno_total']:.1%} "
        f"| Ibovespa: {metricas['ibovespa']['retorno_total']:.1%}"
    )
    print(f"Diferenca de retorno total (estrategia - Ibovespa): {diferenca_retorno_total:+.1%}")
    print(f"Correlacao dos retornos diarios com o Ibovespa: {correlacao_diaria:.2f}")
    print(
        "\nComo ler isso: a estrategia Sinapse e MARKET-NEUTRAL -- ela carrega um "
        "hedge vendido de Ibovespa embutido na coluna IBOV_SYNTHETIC, desenhado "
        "exatamente pra zerar a exposicao a beta de mercado. Por isso, DIFERENTE de "
        "uma estrategia long-only, aqui o esperado e uma correlacao diaria PROXIMA "
        "DE ZERO com o Ibovespa -- e o alfa descorrelacionado que a estrategia busca. "
        "Correlacao ALTA (positiva ou negativa) e que e o alarme aqui -- sugere que o "
        "hedge de beta nao esta funcionando (peso de IBOV_SYNTHETIC errado, retorno do "
        "Ibovespa mal alinhado, ou bug na injecao da coluna nos retornos)."
    )
    if abs(correlacao_diaria) > 0.3:
        print(
            "\nALERTA: correlacao acima de 0.3 em modulo -- isso NAO e esperado pra "
            "uma estrategia beta-neutra. Revise o hedge de IBOV_SYNTHETIC (peso e "
            "retorno injetado) antes de confiar em qualquer resultado daqui."
        )

    # ------------------------------------------------------------------
    # Diagnostico de execucao -- separa "o sinal e ruim" de "o custo comeu"
    # ------------------------------------------------------------------
    print("\n===== DIAGNOSTICO DE EXECUCAO =====")
    giro_medio = giro_diario.mean()
    custo_ano = giro_medio * CUSTO * DIAS_UTEIS_ANO
    bruto_ano = pnl_bruto.mean() * DIAS_UTEIS_ANO
    liquido_ano = retorno_estrategia.mean() * DIAS_UTEIS_ANO
    vol_realizada = retorno_estrategia.std() * (DIAS_UTEIS_ANO ** 0.5)

    print(f"Giro medio diario:            {giro_medio:.1%} do book")
    print(f"Retorno BRUTO (sem custo):    {bruto_ano:+.2%} ao ano")
    print(f"Custo de transacao implicito: {custo_ano:.2%} ao ano  (a {CUSTO:.2%} por giro)")
    print(f"Retorno LIQUIDO:              {liquido_ano:+.2%} ao ano")
    print(f"Volatilidade realizada:       {vol_realizada:.2%} ao ano  (alvo do projeto: 12%)")
    if bruto_ano > 0 and liquido_ano <= 0:
        print(
            "\nATENCAO: o sinal e lucrativo no BRUTO mas o custo de transacao "
            "inverte o resultado. O problema esta na EXECUCAO (giro alto demais), "
            "nao na qualidade do sinal -- aumentar a suavizacao do Bloco 4."
        )
    if vol_realizada < 0.5 * 0.12:
        print(
            "\nATENCAO: a carteira esta rodando MUITO abaixo do alvo de vol -- "
            "as travas institucionais (liquidez/nome/setor) devem estar limitando. "
            "O retorno esperado escala junto com a vol, entao isso segura o resultado."
        )

    print("\n===== RESUMO DAS METRICAS =====")
    for nome, m in metricas.items():
        print(
            f"{nome}: retorno_total={m['retorno_total']:.1%} | "
            f"sharpe_anualizado={m['sharpe_anualizado']:.2f} | "
            f"drawdown_maximo={m['drawdown_maximo']:.1%}"
        )

    # O CDI e o benchmark oficial de performance do projeto.
    excesso_cdi = (
        metricas["estrategia sinapse"]["retorno_total"] - metricas["cdi (benchmark)"]["retorno_total"]
    )
    print(f"\nExcesso sobre o CDI (benchmark oficial): {excesso_cdi:+.1%} no periodo")
    if excesso_cdi < 0:
        print("  -> a estrategia ainda NAO bate o CDI.")

    print(f"\nCurvas diarias salvas em: {caminho_curvas}")
    print(f"Grafico salvo em: {caminho_grafico}")


if __name__ == "__main__":
    main()
