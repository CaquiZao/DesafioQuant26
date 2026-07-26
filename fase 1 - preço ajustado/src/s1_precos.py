"""
Bloco 1 do projeto SINAPSE: baixar precos ajustados de acoes brasileiras.

Este script:
1. Baixa precos historicos ja ajustados (por dividendo e desdobramento) via yfinance.
2. Monta uma tabela de precos e uma tabela de retornos diarios, ambas em formato "largo"
   (cada coluna e um ticker, cada linha e uma data).
3. Salva as duas tabelas em arquivos Parquet.
4. Gera um grafico simples para conferir visualmente os dados baixados.
"""

import os

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

# Lendo os tickers diretamente do grafo para garantir que a base de dados cubra nosso teste
try:
    caminho_grafo = os.path.join(os.path.dirname(__file__), '..', '..', 'fase 4 - sinal da sinapse', 'grafo_manual_base.csv')
    df_grafo = pd.read_csv(caminho_grafo)
    TICKERS = list(set(df_grafo['empresa_A'].tolist() + df_grafo['empresa_B'].tolist()))
    TICKERS.sort()
except Exception as e:
    print(f"Aviso: Não encontrou o grafo. Usando fallback. Erro: {e}")
    TICKERS = ["PETR4", "VALE3"]

# Periodo fixo de dados que queremos baixar.
DATA_INICIO = "2016-01-01"
DATA_FIM = "2025-12-31"

# Pasta onde vamos salvar os resultados (tabelas e grafico).
PASTA_SAIDA = os.path.join("data", "precos")


def baixar_precos_ajustados(tickers, data_inicio, data_fim):
    """
    Baixa, para cada ticker da lista, a serie de precos de fechamento
    ja ajustada por dividendos e desdobramentos.

    Retorna:
        - um dicionario {ticker_limpo: serie_de_precos} com os tickers que deram certo.
        - uma lista com os tickers que falharam (nao vieram dados).
    """
    precos_por_ticker = {}
    tickers_faltantes = []

    for ticker in tickers:
        # No Yahoo Finance, acoes brasileiras precisam do sufixo ".SA".
        ticker_yahoo = f"{ticker}.SA"

        # auto_adjust=True faz o yfinance devolver o preco JA ajustado
        # (equivalente ao antigo "Adj Close") na propria coluna "Close".
        dados = yf.download(
            ticker_yahoo,
            start=data_inicio,
            end=data_fim,
            auto_adjust=True,
            progress=False,
        )

        # Se o yfinance nao achou nada, ele devolve uma tabela vazia.
        if dados.empty:
            print(f"AVISO: nao foi possivel baixar dados para {ticker} ({ticker_yahoo}).")
            tickers_faltantes.append(ticker)
            continue

        # Quando baixamos so 1 ticker por vez, a coluna "Close" pode vir
        # como uma tabela com varias colunas (MultiIndex). Aqui garantimos
        # que vamos pegar so a serie (uma coluna) de fechamento.
        coluna_fechamento = dados["Close"]
        if isinstance(coluna_fechamento, pd.DataFrame):
            coluna_fechamento = coluna_fechamento.iloc[:, 0]

        # Guardamos a serie usando o nome LIMPO do ticker (sem ".SA").
        precos_por_ticker[ticker] = coluna_fechamento

    return precos_por_ticker, tickers_faltantes


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


def montar_tabela_retornos(tabela_precos):
    """
    Calcula o retorno diario de cada ticker a partir da tabela de precos:
        retorno_hoje = (preco_hoje / preco_ontem) - 1

    A primeira linha fica vazia (NaN) porque nao existe "dia anterior"
    para o primeiro dia da serie. Isso e esperado.
    """
    # pct_change() ja faz exatamente essa conta (preco_hoje / preco_ontem - 1)
    # para cada coluna (cada ticker) separadamente.
    tabela_retornos = tabela_precos.pct_change()
    return tabela_retornos


def salvar_tickers_faltantes(tickers_faltantes, pasta_saida):
    """
    Escreve, um por linha, os tickers que nao conseguimos baixar,
    no arquivo data/precos/faltantes.txt.
    """
    caminho_arquivo = os.path.join(pasta_saida, "faltantes.txt")
    with open(caminho_arquivo, "w", encoding="utf-8") as arquivo:
        for ticker in tickers_faltantes:
            arquivo.write(ticker + "\n")
    return caminho_arquivo


def gerar_grafico_validacao(tabela_precos, pasta_saida):
    """
    Gera um grafico simples com as series de PETR4 e VALE3 (se existirem
    na tabela) so para conferir visualmente se os dados baixados fazem sentido.
    """
    tickers_para_plotar = [t for t in ["PETR4", "VALE3"] if t in tabela_precos.columns]

    if not tickers_para_plotar:
        print("AVISO: nenhum dos tickers PETR4/VALE3 esta disponivel para o grafico.")
        return None

    # Cria a figura (a "tela" do grafico).
    plt.figure(figsize=(10, 5))

    for ticker in tickers_para_plotar:
        plt.plot(tabela_precos.index, tabela_precos[ticker], label=ticker)

    plt.title("Preco ajustado de fechamento - PETR4 vs VALE3")
    plt.xlabel("Data")
    plt.ylabel("Preco ajustado (R$)")
    plt.legend()
    plt.tight_layout()

    caminho_grafico = os.path.join(pasta_saida, "teste_petr4_vale3.png")
    plt.savefig(caminho_grafico)
    # Fecha a figura pra liberar memoria (nao precisamos mostrar na tela).
    plt.close()

    return caminho_grafico


def main():
    # Garante que a pasta de saida existe (cria, se nao existir).
    os.makedirs(PASTA_SAIDA, exist_ok=True)

    # Passo 1: baixar os precos de cada ticker.
    precos_por_ticker, tickers_faltantes = baixar_precos_ajustados(
        TICKERS, DATA_INICIO, DATA_FIM
    )

    if not precos_por_ticker:
        print("Nenhum ticker foi baixado com sucesso. Encerrando o script.")
        salvar_tickers_faltantes(tickers_faltantes, PASTA_SAIDA)
        return

    # Passo 2: montar a TABELA 1 (precos) e a TABELA 2 (retornos).
    tabela_precos = montar_tabela_precos(precos_por_ticker)
    tabela_retornos = montar_tabela_retornos(tabela_precos)

    # Passo 3: salvar as duas tabelas em Parquet.
    caminho_precos = os.path.join(PASTA_SAIDA, "precos_ajustados.parquet")
    caminho_retornos = os.path.join(PASTA_SAIDA, "retornos_diarios.parquet")

    tabela_precos.to_parquet(caminho_precos, engine="pyarrow")
    tabela_retornos.to_parquet(caminho_retornos, engine="pyarrow")

    # Passo 4: salvar a lista de tickers que falharam (mesmo que esteja vazia).
    caminho_faltantes = salvar_tickers_faltantes(tickers_faltantes, PASTA_SAIDA)

    # Passo 5: gerar o grafico de validacao.
    caminho_grafico = gerar_grafico_validacao(tabela_precos, PASTA_SAIDA)

    # ------------------------------------------------------------------
    # Resumo final no terminal
    # ------------------------------------------------------------------
    print("\n===== RESUMO =====")
    print(f"Tickers pedidos: {len(TICKERS)}")
    print(f"Tickers baixados com sucesso: {len(precos_por_ticker)} -> {list(precos_por_ticker.keys())}")
    print(f"Linhas (dias) na tabela de precos: {len(tabela_precos)}")
    print(f"Linhas (dias) na tabela de retornos: {len(tabela_retornos)}")

    if len(tabela_precos) > 0:
        primeira_data = tabela_precos.index.min().date()
        ultima_data = tabela_precos.index.max().date()
        print(f"Intervalo de datas: {primeira_data} até {ultima_data}")

    if tickers_faltantes:
        print(f"Tickers faltantes (salvos em {caminho_faltantes}): {tickers_faltantes}")
    else:
        print("Nenhum ticker faltante.")

    print(f"Tabela de precos salva em: {caminho_precos}")
    print(f"Tabela de retornos salva em: {caminho_retornos}")
    if caminho_grafico:
        print(f"Grafico de validacao salvo em: {caminho_grafico}")


if __name__ == "__main__":
    main()
