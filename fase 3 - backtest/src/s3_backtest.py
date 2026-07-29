"""
Bloco 3 do projeto SINAPSE: o motor de backtest.

Este script e uma MAQUINA VAZIA -- ele nao sabe o que e a Sinapse. Ele so
sabe fazer uma coisa: pegar uma tabela de pesos por mes (quem entra na
carteira e com quanto peso) e devolver a curva de patrimonio resultante
mais as metricas de performance. A ESTRATEGIA (a logica que decide os
pesos) mora fora do motor -- aqui dentro so tem uma "estrategia idiota"
de teste (equal-weight do universo), so pra provar que o motor funciona
antes dos Blocos 4/5 (a Sinapse de verdade) plugarem a tabela de pesos
deles no lugar.

O script:
1. Carrega os insumos dos Blocos 1 e 2: `retornos_diarios.parquet`
   (precos ja virados retorno diario, formato largo) e
   `universo_mensal.parquet` (quais tickers valiam a pena em cada mes).
2. Gera a tabela de pesos da "estrategia idiota": equal-weight entre
   todos os tickers do universo point-in-time de cada mes.
3. Roda o MOTOR: aplica esses pesos aos retornos diarios respeitando um
   rebalanceamento MENSAL com LAG de 1 mes (pesos decididos no fim do
   mes X so valem a partir do 1o pregao do mes X+1 -- nunca antes, pra
   nao dar look-ahead bias) e desconta custo de transacao proporcional
   ao giro (turnover) da carteira.
4. Baixa o Ibovespa (fonte provisoria via yfinance) so pra servir de
   referencia comparativa.
5. Alinha as duas curvas pelas datas em comum e roda um TESTE DE
   SANIDADE: a estrategia idiota tem que andar "no mesmo formato" que o
   Ibovespa (correlacao alta dos retornos diarios). Uma diferenca de
   NIVEL no retorno total e esperada (equal-weight != ponderado por
   valor de mercado); o alarme de verdade e a curva descolar de FORMA.
6. Salva as curvas diarias e a cobertura mensal em Parquet, e um grafico
   comparativo em PNG.

Quando a Sinapse (Blocos 4 e 5) estiver pronta, ela so precisa produzir
uma tabela [mes, ticker, peso] igual a da estrategia idiota -- o motor
(passos 3 em diante) nao muda nada.
"""

import os

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

# Caminhos RELATIVOS: supoe que o script e rodado com a pasta "fase 3 -
# backtest" como pasta atual (igual os outros blocos ja fazem com a
# propria pasta).
CAMINHO_RETORNOS = os.path.join(
    "..", "fase 1 - preço ajustado", "data", "precos", "retornos_diarios.parquet"
)
CAMINHO_UNIVERSO = os.path.join(
    "..", "fase 2 - universo liquidez", "data", "universo", "universo_mensal.parquet"
)

# Ticker do Ibovespa no Yahoo Finance (indice, nao acao -- por isso o "^").
TICKER_IBOVESPA = "^BVSP"

# Pasta onde salvamos os resultados deste bloco (curvas, cobertura, grafico).
PASTA_SAIDA = os.path.join("data", "backtest")

# Custo de transacao por unidade de giro (turnover) mensal. Ex: 0.001
# representaria 0.1% do valor girado. Por enquanto 0.0 -- a mecanica de
# desconto ja esta pronta (ver calcular_giro/rodar_motor), so falta o
# time decidir o valor com base em custo real de corretagem + slippage.
CUSTO = 0.0

# Taxa livre de risco anual, usada no calculo do Sharpe (retorno em
# EXCESSO sobre essa taxa). Por enquanto 0.0 -- ajustar depois pra uma
# proxy real (CDI/Selic anualizada), se o time decidir incluir.
TAXA_LIVRE_ANUAL = 0.0

# Dias uteis no ano, usado pra anualizar o Sharpe (padrao de mercado).
DIAS_UTEIS_ANO = 252

# Se a cobertura de um mes (tickers com preco disponivel / tickers
# pedidos pelo universo) ficar ABAIXO disso, imprime um ALERTA no log --
# carteira concentrada demais naquele mes distorce a metrica.
COBERTURA_MINIMA_ALERTA = 0.50


# ------------------------------------------------------------------
# 2) CARREGAR INSUMOS DOS BLOCOS 1 E 2
# ------------------------------------------------------------------

def carregar_retornos_diarios(caminho):
    """
    Le o Parquet do Bloco 1: formato largo, indice = datas diarias,
    colunas = tickers LIMPOS (sem ".SA"), valores = retorno diario.
    """
    return pd.read_parquet(caminho)


def carregar_universo_mensal(caminho):
    """
    Le o Parquet do Bloco 2: colunas mes (string "YYYY-MM"), ticker,
    volume_mes, rank. Cada linha e "este ticker valia a pena negociar
    neste mes, segundo o proxy de liquidez do COTAHIST".
    """
    return pd.read_parquet(caminho)


# ------------------------------------------------------------------
# 3) ESTRATEGIA IDIOTA (sinal de teste -- FORA do motor)
# ------------------------------------------------------------------
# Isto NAO faz parte do motor. E so um "sinal burro" pra provar que o
# motor funciona: peso igual entre TODOS os tickers do universo
# point-in-time de cada mes (sem filtrar por preco disponivel ainda --
# isso e responsabilidade do motor, na hora de EXECUTAR os pesos, porque
# e um problema de execucao, nao de estrategia).

def gerar_pesos_equal_weight(universo_mensal):
    """
    Devolve uma tabela [mes, ticker, peso] com peso = 1 / (numero de
    tickers do universo naquele mes), pra cada mes. Os pesos de cada mes
    somam exatamente 1.0.

    Quando a Sinapse (Blocos 4/5) estiver pronta, ela substitui esta
    funcao por outra que produz a MESMA tabela [mes, ticker, peso], com
    pesos vindos do sinal de verdade -- o motor abaixo nao muda.
    """
    tabela = universo_mensal[["mes", "ticker"]].copy()
    tickers_por_mes = tabela.groupby("mes")["ticker"].transform("count")
    tabela["peso"] = 1.0 / tickers_por_mes
    return tabela[["mes", "ticker", "peso"]]


# ------------------------------------------------------------------
# 4) MOTOR: FUNCOES AUXILIARES (mes seguinte, giro/turnover)
# ------------------------------------------------------------------

def mes_seguinte(mes):
    """
    Dado um mes no formato "YYYY-MM", devolve o mes seguinte no mesmo
    formato. Usado pra aplicar a REGRA DO LAG: pesos decididos com o
    universo do fim do mes X so valem a partir do mes X+1.
    """
    periodo = pd.Period(mes, freq="M") + 1
    return str(periodo)


def calcular_giro(pesos_anteriores, pesos_atuais):
    """
    Giro (turnover) = soma das mudancas absolutas de peso entre a
    carteira do mes anterior e a atual, usando a UNIAO dos tickers (quem
    sai ou entra conta como mudanca de peso 0 <-> peso). Se nao existe
    mes anterior (1a montagem da carteira), pesos_anteriores vem vazio e
    o giro da exatamente 1.0 (100%), como esperado.

    NOTA: aqui comparamos os pesos DE EXECUCAO (ja filtrados pelos
    tickers com preco disponivel e renormalizados pra somar 1.0), porque
    sao esses que definem a carteira REAL. Quando CUSTO > 0 de verdade,
    o jeito mais correto seria comparar com o peso DERIVADO do fim do
    mes anterior (que ja andou/driftou com os retornos daquele mes), e
    nao com o peso-alvo congelado no INICIO do mes anterior. Por ora,
    pra simplicidade (e porque CUSTO = 0.0), usamos o peso-alvo antigo
    mesmo -- ajustar aqui quando o time decidir ligar custo de verdade.
    """
    todos_tickers = pesos_anteriores.index.union(pesos_atuais.index)
    anteriores = pesos_anteriores.reindex(todos_tickers, fill_value=0.0)
    atuais = pesos_atuais.reindex(todos_tickers, fill_value=0.0)
    return (atuais - anteriores).abs().sum()


# ------------------------------------------------------------------
# 5) MOTOR: EXECUCAO (rebalance mensal, lag, custo, cobertura)
# ------------------------------------------------------------------

def rodar_motor(pesos_estrategia, retornos_diarios, custo_por_giro, cobertura_minima_alerta):
    """
    O coracao do Bloco 3. Para cada mes de DECISAO presente na tabela de
    pesos:
      1. Calcula o mes de EXECUCAO (mes_seguinte) -- REGRA DO LAG: os
         pesos decididos com o universo do fim do mes de decisao X so
         tocam retornos a partir do 1o pregao do mes de execucao X+1,
         nunca antes. Isso e o que evita look-ahead bias.
      2. Filtra os pesos-alvo para so os tickers que TEM coluna em
         retornos_diarios (nem todo ticker do universo tem preco
         baixado) e renormaliza pra somar 100% de novo -- carteira
         sempre totalmente investida, sem caixa parado artificial.
      3. Calcula o giro vs a carteira do mes anterior e desconta
         custo_por_giro * giro no retorno do PRIMEIRO pregao do mes.
      4. Compoe o retorno diario da carteira dentro do mes: em cada dia,
         retorno_carteira = soma(peso_i * retorno_i), com os pesos
         CONGELADOS durante todo o mes (aproximacao buy-and-hold: nao
         redistribui peso dia a dia). Encadear (multiplicar) esses
         retornos diarios da o mesmo retorno mensal total que usar so as
         pontas do mes, mas preserva o caminho (drawdown intra-mes).

    Bordas (ver modulo): o 1o mes de decisao nao tem mes anterior --
    pesos_anteriores comeca vazio e o giro da 1a carteira montada e
    100%, automaticamente (sem caso especial no codigo). O ULTIMO mes de
    decisao normalmente NAO tem mes de execucao com retorno (o proximo
    mes ainda nao tem preco baixado) -- esses meses sao contados e
    pulados, e isso e esperado, nao e bug.

    Devolve:
      - retorno_estrategia: Series diaria (uma linha por dia de pregao
        com carteira ativa) com o retorno diario da estrategia.
      - tabela_cobertura: DataFrame com uma linha por mes EXECUTADO,
        registrando tickers pedidos/disponiveis/cobertura/giro/custo --
        serve pra quantificar o survivorship bias no relatorio.
    """
    tickers_com_preco = set(retornos_diarios.columns)
    chave_mes_retornos = retornos_diarios.index.strftime("%Y-%m")

    meses_decisao = sorted(pesos_estrategia["mes"].unique())
    pesos_por_mes = {
        mes: grupo.set_index("ticker")["peso"]
        for mes, grupo in pesos_estrategia.groupby("mes")
    }

    retornos_por_mes_executado = []
    linhas_cobertura = []
    pesos_execucao_anteriores = pd.Series(dtype=float)
    meses_sem_retorno_correspondente = 0

    for mes_decisao in meses_decisao:
        pesos_alvo = pesos_por_mes[mes_decisao]

        # REGRA DO LAG (defesa contra look-ahead): decisao no fim de
        # `mes_decisao` -> P&L comeca no 1o pregao de `mes_execucao`.
        mes_execucao = mes_seguinte(mes_decisao)

        retornos_mes = retornos_diarios.loc[chave_mes_retornos == mes_execucao]

        if retornos_mes.empty:
            # Borda do periodo: normalmente o ULTIMO mes de decisao do
            # universo (o mes seguinte ainda nao tem preco baixado).
            # Esperado -- so contabiliza, nao e erro.
            meses_sem_retorno_correspondente += 1
            continue

        # Filtra pro que da pra realmente comprar (tem preco) e
        # renormaliza. Isso evita KeyError e mede o survivorship bias.
        tickers_disponiveis = [t for t in pesos_alvo.index if t in tickers_com_preco]
        pedidos = len(pesos_alvo)
        disponiveis = len(tickers_disponiveis)
        cobertura_pct = disponiveis / pedidos if pedidos > 0 else 0.0

        if cobertura_pct < cobertura_minima_alerta:
            print(
                f"  ALERTA: cobertura {cobertura_pct:.0%} no mes de execucao "
                f"{mes_execucao} (decisao {mes_decisao}) -- so {disponiveis}/{pedidos} "
                "tickers do universo tem preco disponivel."
            )

        if disponiveis == 0:
            # Nenhum ticker pedido esse mes tem preco -- nao da pra
            # montar carteira nenhuma. Registra e pula (o mes fica sem
            # retorno na curva; caso extremo, nao esperado na pratica).
            linhas_cobertura.append(
                {
                    "mes_decisao": mes_decisao,
                    "mes_execucao": mes_execucao,
                    "tickers_pedidos": pedidos,
                    "tickers_disponiveis": 0,
                    "cobertura_pct": 0.0,
                    "giro": None,
                    "custo_aplicado": None,
                }
            )
            continue

        pesos_disponiveis = pesos_alvo.loc[tickers_disponiveis]
        pesos_disponiveis = pesos_disponiveis / pesos_disponiveis.sum()

        giro = calcular_giro(pesos_execucao_anteriores, pesos_disponiveis)
        custo_do_mes = custo_por_giro * giro

        # Retorno diario da carteira: soma ponderada dos retornos de
        # cada ticker disponivel, com o peso congelado no mes inteiro.
        # Dias sem preco pontual (NaN, ex: gap de dado) contam como
        # retorno zero NAQUELE dia especifico, so pra nao propagar NaN
        # pro produto acumulado da curva.
        retornos_colunas = retornos_mes[pesos_disponiveis.index].fillna(0.0)
        retorno_diario_mes = retornos_colunas.dot(pesos_disponiveis)

        # Desconta o custo de transacao no 1o pregao do mes (unico
        # momento em que a carteira "gira" nesse mes). Com CUSTO = 0.0
        # isso e um no-op.
        primeiro_dia = retorno_diario_mes.index[0]
        retorno_diario_mes.loc[primeiro_dia] = retorno_diario_mes.loc[primeiro_dia] - custo_do_mes

        retornos_por_mes_executado.append(retorno_diario_mes)
        linhas_cobertura.append(
            {
                "mes_decisao": mes_decisao,
                "mes_execucao": mes_execucao,
                "tickers_pedidos": pedidos,
                "tickers_disponiveis": disponiveis,
                "cobertura_pct": cobertura_pct,
                "giro": giro,
                "custo_aplicado": custo_do_mes,
            }
        )

        pesos_execucao_anteriores = pesos_disponiveis

    print(
        f"\n{meses_sem_retorno_correspondente} mes(es) de decisao sem retorno "
        "correspondente (esperado na ponta final do periodo)."
    )

    retorno_estrategia = pd.concat(retornos_por_mes_executado).sort_index()
    tabela_cobertura = pd.DataFrame(linhas_cobertura)

    return retorno_estrategia, tabela_cobertura


# ------------------------------------------------------------------
# 6) IBOVESPA (referencia externa -- FONTE PROVISORIA)
# ------------------------------------------------------------------

def baixar_retornos_ibovespa(data_inicio, data_fim):
    """
    Baixa o retorno diario do Ibovespa (^BVSP) via yfinance, so pra
    servir de referencia no teste de sanidade do motor.

    FONTE PROVISORIA: quando o parquet de indices do colega
    (s1b_indices.py, Bloco 4) estiver disponivel pra todo mundo, trocar
    esta funcao por uma leitura desse parquet -- o resto do script nao
    muda, so esta funcao fica isolada aqui de proposito.
    """
    dados = yf.download(
        TICKER_IBOVESPA, start=data_inicio, end=data_fim, auto_adjust=True, progress=False
    )
    fechamento = dados["Close"]
    if isinstance(fechamento, pd.DataFrame):
        fechamento = fechamento.iloc[:, 0]
    return fechamento.pct_change().dropna()


# ------------------------------------------------------------------
# 7) METRICAS (retorno total, Sharpe anualizado, drawdown maximo)
# ------------------------------------------------------------------

def calcular_retorno_total(curva):
    """Retorno acumulado do periodo inteiro, a partir da curva de patrimonio."""
    return curva.iloc[-1] / curva.iloc[0] - 1


def calcular_sharpe_anualizado(retorno_diario, taxa_livre_anual, dias_uteis_ano):
    """
    Sharpe = (retorno medio em excesso / desvio-padrao do retorno em
    excesso) * raiz(dias uteis no ano) -- forma padrao de anualizar um
    Sharpe calculado em base diaria.
    """
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
# 8) GRAFICO
# ------------------------------------------------------------------

def gerar_grafico_comparativo(curva_estrategia, curva_ibovespa, pasta_saida):
    plt.figure(figsize=(12, 6))
    plt.plot(curva_estrategia.index, curva_estrategia.values, label="Estrategia idiota (equal-weight)")
    plt.plot(curva_ibovespa.index, curva_ibovespa.values, label="Ibovespa")
    plt.title("Bloco 3 -- curva de patrimonio (base 1.0): estrategia idiota vs Ibovespa")
    plt.xlabel("Data")
    plt.ylabel("Patrimonio (base 1.0)")
    plt.legend()
    plt.grid(alpha=0.3)

    caminho = os.path.join(pasta_saida, "curva_patrimonio.png")
    plt.savefig(caminho, dpi=120, bbox_inches="tight")
    plt.close()
    return caminho


# ------------------------------------------------------------------
# 9) MAIN
# ------------------------------------------------------------------

def main():
    os.makedirs(PASTA_SAIDA, exist_ok=True)

    print("Passo 1: carregando insumos dos Blocos 1 e 2...")
    retornos_diarios = carregar_retornos_diarios(CAMINHO_RETORNOS)
    universo_mensal = carregar_universo_mensal(CAMINHO_UNIVERSO)
    print(
        f"  retornos_diarios: {retornos_diarios.shape[0]} dias, "
        f"{retornos_diarios.shape[1]} tickers com preco"
    )
    print(
        f"  universo_mensal: {universo_mensal['mes'].nunique()} meses, "
        f"{universo_mensal['ticker'].nunique()} tickers unicos"
    )

    print("\nPasso 2: gerando pesos da estrategia idiota (equal-weight do universo point-in-time)...")
    pesos_estrategia = gerar_pesos_equal_weight(universo_mensal)

    print("\nPasso 3: rodando o motor (rebalance mensal, lag de 1 mes, custo de giro)...")
    retorno_estrategia, tabela_cobertura = rodar_motor(
        pesos_estrategia, retornos_diarios, CUSTO, COBERTURA_MINIMA_ALERTA
    )
    # Convencao de retorno: composicao por (1+r).cumprod() -- retorno
    # simples composto, nunca soma de log-retornos.
    curva_estrategia = (1 + retorno_estrategia).cumprod()

    print("\nPasso 4: baixando Ibovespa (fonte provisoria via yfinance)...")
    data_inicio = retorno_estrategia.index.min().strftime("%Y-%m-%d")
    data_fim = retorno_estrategia.index.max().strftime("%Y-%m-%d")
    retorno_ibovespa = baixar_retornos_ibovespa(data_inicio, data_fim)
    curva_ibovespa = (1 + retorno_ibovespa).cumprod()

    print("\nPasso 5: alinhando as duas curvas pelas datas em comum...")
    # Feriado que existe numa fonte e nao na outra nao pode desalinhar
    # as curvas -- por isso a interseccao dos indices, nunca um merge
    # "as cegas" pela posicao.
    datas_em_comum = curva_estrategia.index.intersection(curva_ibovespa.index)
    if len(datas_em_comum) == 0:
        raise ValueError(
            "Estrategia e Ibovespa nao tem NENHUMA data em comum -- confira o "
            "download do Ibovespa (periodo, feriados, fuso)."
        )

    curva_estrategia = curva_estrategia.loc[datas_em_comum].sort_index()
    curva_ibovespa = curva_ibovespa.loc[datas_em_comum].sort_index()

    # Base 1.0 na PRIMEIRA DATA EM COMUM (nao na primeira data de cada
    # serie isolada, que pode ser diferente por causa do lag do motor).
    curva_estrategia = curva_estrategia / curva_estrategia.iloc[0]
    curva_ibovespa = curva_ibovespa / curva_ibovespa.iloc[0]

    print("\nPasso 6: calculando metricas...")
    retorno_diario_estrategia = curva_estrategia.pct_change().dropna()
    retorno_diario_ibovespa = curva_ibovespa.pct_change().dropna()

    metricas = {
        "estrategia idiota": {
            "retorno_total": calcular_retorno_total(curva_estrategia),
            "sharpe_anualizado": calcular_sharpe_anualizado(
                retorno_diario_estrategia, TAXA_LIVRE_ANUAL, DIAS_UTEIS_ANO
            ),
            "drawdown_maximo": calcular_drawdown_maximo(curva_estrategia),
        },
        "ibovespa": {
            "retorno_total": calcular_retorno_total(curva_ibovespa),
            "sharpe_anualizado": calcular_sharpe_anualizado(
                retorno_diario_ibovespa, TAXA_LIVRE_ANUAL, DIAS_UTEIS_ANO
            ),
            "drawdown_maximo": calcular_drawdown_maximo(curva_ibovespa),
        },
    }

    print("\nPasso 7: gerando grafico comparativo...")
    caminho_grafico = gerar_grafico_comparativo(curva_estrategia, curva_ibovespa, PASTA_SAIDA)

    print("\nPasso 8: salvando parquets de saida...")
    caminho_curvas = os.path.join(PASTA_SAIDA, "curvas_diarias.parquet")
    tabela_curvas = pd.DataFrame(
        {
            "patrimonio_estrategia": curva_estrategia,
            "patrimonio_ibovespa": curva_ibovespa,
        }
    )
    tabela_curvas.to_parquet(caminho_curvas, engine="pyarrow")

    caminho_cobertura = os.path.join(PASTA_SAIDA, "cobertura_mensal.parquet")
    tabela_cobertura.to_parquet(caminho_cobertura, engine="pyarrow")

    # ------------------------------------------------------------------
    # Teste de sanidade -- O MAIS IMPORTANTE deste bloco
    # ------------------------------------------------------------------
    print("\n===== TESTE DE SANIDADE =====")
    diferenca_retorno_total = (
        metricas["estrategia idiota"]["retorno_total"] - metricas["ibovespa"]["retorno_total"]
    )
    correlacao_diaria = retorno_diario_estrategia.corr(retorno_diario_ibovespa)

    print(
        f"Retorno total -- estrategia idiota: {metricas['estrategia idiota']['retorno_total']:.1%} "
        f"| Ibovespa: {metricas['ibovespa']['retorno_total']:.1%}"
    )
    print(f"Diferenca de retorno total (estrategia - Ibovespa): {diferenca_retorno_total:+.1%}")
    print(f"Correlacao dos retornos diarios (forma da curva): {correlacao_diaria:.2f}")
    print(
        "\nComo ler isso: a estrategia idiota e equal-weight (peso igual pra cada "
        "acao do universo), enquanto o Ibovespa e ponderado por valor de mercado -- "
        "entao uma DIFERENCA DE NIVEL pequena/moderada no retorno total e esperada e "
        "SAUDAVEL, nao indica bug. O que importa de verdade e a FORMA da curva: "
        "correlacao dos retornos diarios perto de 1.0 significa que as duas andam "
        "juntas (mesmo regime de mercado), evidencia de que o motor esta certo. "
        "Correlacao baixa ou negativa e QUE e alarme -- sugere lag trocado, "
        "desalinhamento de datas, ou bug no calculo dos pesos/retornos."
    )
    if correlacao_diaria < 0.5:
        print(
            "\nALERTA: correlacao abaixo de 0.5 -- isso NAO e normal pra uma "
            "estrategia equal-weight do proprio universo domestico vs o Ibovespa. "
            "Revise o motor antes de confiar em qualquer resultado daqui."
        )

    print("\n===== RESUMO DAS METRICAS =====")
    for nome, m in metricas.items():
        print(
            f"{nome}: retorno_total={m['retorno_total']:.1%} | "
            f"sharpe_anualizado={m['sharpe_anualizado']:.2f} | "
            f"drawdown_maximo={m['drawdown_maximo']:.1%}"
        )

    print(f"\nCobertura media mensal: {tabela_cobertura['cobertura_pct'].mean():.1%}")
    print(f"Meses com carteira executada: {len(tabela_cobertura)}")
    print(f"\nCurvas diarias salvas em: {caminho_curvas}")
    print(f"Cobertura mensal salva em: {caminho_cobertura}")
    print(f"Grafico salvo em: {caminho_grafico}")


if __name__ == "__main__":
    main()
