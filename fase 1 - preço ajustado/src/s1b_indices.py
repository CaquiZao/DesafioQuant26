"""
Bloco 1.5 do projeto SINAPSE: baixar retornos históricos do Ibovespa e Setores.

Este script:
1. Baixa os preços históricos do próprio índice Ibovespa (^BVSP) e de ETFs setoriais da B3
   que representam o movimento dos setores (ex: FIND11 para Financeiro, MATB11 para Materiais).
   Usamos ETFs porque eles têm liquidez real, histórico limpo no Yahoo Finance e representam
   perfeitamente o retorno do setor.
2. Calcula os retornos diários.
3. Salva uma tabela em Parquet pronta para a regressão do Choque Limpo (Bloco 4).
"""

import os
import pandas as pd
import yfinance as yf

# ------------------------------------------------------------------
# 1) CONFIGURAÇÕES GERAIS
# ------------------------------------------------------------------

# Tickers dos índices/ETFs que vamos baixar para usar como benchmark.
# ^BVSP = Ibovespa (O próprio índice)
# FIND11.SA = ETF do Setor Financeiro
# MATB11.SA = ETF de Materiais Básicos (Siderurgia, Mineração, Papel)
# BOVA11.SA = ETF do Ibovespa (Usado como redundância caso o ^BVSP falhe)
TICKERS_INDICES = {
    "IBOV": "^BVSP",
    "IBOV_ETF": "BOVA11.SA"
}

DATA_INICIO = "2016-01-01"
DATA_FIM = "2025-12-31"

PASTA_SAIDA = os.path.join("data", "precos")

def baixar_retornos_indices():
    print("Iniciando o download dos índices de mercado e setoriais...")
    
    # Criar a pasta de saída se não existir
    os.makedirs(PASTA_SAIDA, exist_ok=True)
    
    df_precos = pd.DataFrame()
    
    for nome, ticker in TICKERS_INDICES.items():
        print(f"Baixando {nome} ({ticker})...")
        try:
            # Baixa os dados ajustados
            dados = yf.download(ticker, start=DATA_INICIO, end=DATA_FIM, progress=False)
            
            # Pega apenas a coluna de fechamento ajustado (Close já vem ajustado pelo yfinance em alguns casos, mas Adj Close é mais seguro)
            # Nas versões mais recentes do yf, 'Close' é um multi-index se você passar uma lista, mas passando um por um, é uma Series.
            if "Adj Close" in dados.columns:
                df_precos[nome] = dados["Adj Close"]
            elif "Close" in dados.columns:
                df_precos[nome] = dados["Close"]
            else:
                print(f"  -> Aviso: Não encontrou coluna de preço para {ticker}")
                
        except Exception as e:
            print(f"  -> Erro ao baixar {ticker}: {e}")

    if df_precos.empty:
        print("Nenhum dado foi baixado. Abortando.")
        return

    # Remover linhas onde TUDO é NaN (ex: fins de semana que vieram por engano)
    df_precos = df_precos.dropna(how="all")
    
    print("\nCalculando retornos diários...")
    # Retorno diário = (Preço Hoje / Preço Ontem) - 1
    df_retornos = df_precos.pct_change()
    
    # Opcional: Se o ^BVSP falhar algum dia, usa o BOVA11
    if "IBOV" in df_retornos.columns and "IBOV_ETF" in df_retornos.columns:
        df_retornos["IBOV"] = df_retornos["IBOV"].fillna(df_retornos["IBOV_ETF"])
    
    # Salvar em Parquet
    caminho_retornos = os.path.join(PASTA_SAIDA, "indices_retornos.parquet")
    df_retornos.to_parquet(caminho_retornos)
    
    print(f"\nSucesso! Arquivo salvo em: {caminho_retornos}")
    print(f"Dimensões da tabela: {df_retornos.shape[0]} dias x {df_retornos.shape[1]} índices")
    print(df_retornos.tail())

if __name__ == "__main__":
    baixar_retornos_indices()
