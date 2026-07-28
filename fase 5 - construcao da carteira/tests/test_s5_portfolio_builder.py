import pandas as pd
import numpy as np
import pytest
from src.s5_portfolio_builder import PortfolioBuilder

def test_polaridade_zscore():
    # Z-scores positivos e negativos
    df_zscore = pd.DataFrame({
        'PETR4': [2.0, -1.0],
        'VALE3': [-2.0, 1.5]
    })
    # Criar um df_returns de dummy só pra o vol targeting rodar liso, com desvio padrão = 1
    # Pra ter desvio padrão, precisamos de janelas longas.
    # Vamos simular um df_returns grande de 100 linhas e o df_zscore só no final
    np.random.seed(42)
    df_returns = pd.DataFrame(np.random.randn(100, 2)*0.02, columns=['PETR4', 'VALE3'])
    
    # Pad zscore shape
    df_zscore_full = pd.DataFrame(0.0, index=df_returns.index, columns=df_returns.columns)
    df_zscore_full.iloc[-1] = [2.0, -2.0]
    df_zscore_full.iloc[-2] = [-1.0, 1.5]
    
    pb = PortfolioBuilder(aum=100e6)
    df_w = pb.build_portfolio(df_zscore_full, df_returns, df_adtv=None, df_betas=None, df_sectors=None)
    
    # Row -1 da original sofre shift(1), então o peso gerado no -2 vai pro -1.
    # Row -2 tinha: PETR4 = -1.0, VALE3 = 1.5
    assert df_w.iloc[-1]['PETR4'] < 0
    assert df_w.iloc[-1]['VALE3'] > 0

def test_limite_peso_ativo():
    np.random.seed(42)
    df_returns = pd.DataFrame(np.random.randn(100, 1)*0.02, columns=['PETR4'])
    df_zscore = pd.DataFrame(0.0, index=df_returns.index, columns=['PETR4'])
    df_zscore.iloc[-2, 0] = 10.0
    
    pb = PortfolioBuilder(max_weight_name=0.05)
    df_w = pb.build_portfolio(df_zscore, df_returns, df_adtv=None, df_betas=None, df_sectors=None)
    
    assert abs(df_w.iloc[-1]['PETR4']) <= 0.05

def test_trava_liquidez_adtv():
    np.random.seed(42)
    df_returns = pd.DataFrame(np.random.randn(100, 1)*0.02, columns=['TICKER1'])
    df_zscore = pd.DataFrame(0.0, index=df_returns.index, columns=['TICKER1'])
    df_zscore.iloc[-2, 0] = 10.0
    
    df_adtv = pd.DataFrame(5_000_000.0, index=df_returns.index, columns=['TICKER1'])
    
    # 10% de 5M = 500k. 500k em 100M é 0.005.
    pb = PortfolioBuilder(aum=100_000_000, max_weight_name=1.0)
    df_w = pb.build_portfolio(df_zscore, df_returns, df_adtv=df_adtv, df_betas=None, df_sectors=None)
    
    assert abs(df_w.iloc[-1]['TICKER1']) <= 0.005

def test_limite_peso_setorial():
    np.random.seed(42)
    tickers = ['A1', 'A2', 'A3', 'A4']
    df_returns = pd.DataFrame(np.random.randn(100, 4)*0.02, columns=tickers)
    df_zscore = pd.DataFrame(0.0, index=df_returns.index, columns=tickers)
    df_zscore.iloc[-2] = [10.0, 10.0, 10.0, 10.0]
    
    df_sectors = pd.DataFrame({
        'Ticker': tickers,
        'Setor': ['Financeiro', 'Financeiro', 'Financeiro', 'Financeiro']
    }).set_index('Ticker')
    
    pb = PortfolioBuilder(max_weight_sector=0.25, max_weight_name=0.10)
    df_w = pb.build_portfolio(df_zscore, df_returns, df_adtv=None, df_betas=None, df_sectors=df_sectors)
    
    soma_setor = abs(df_w.iloc[-1]['A1']) + abs(df_w.iloc[-1]['A2']) + abs(df_w.iloc[-1]['A3']) + abs(df_w.iloc[-1]['A4'])
    assert np.isclose(soma_setor, 0.25, atol=1e-5)

def test_beta_neutrality():
    np.random.seed(42)
    df_returns = pd.DataFrame(np.random.randn(100, 2)*0.02, columns=['T1', 'T2'])
    df_zscore = pd.DataFrame(0.0, index=df_returns.index, columns=['T1', 'T2'])
    df_zscore.iloc[-2] = [1.0, -1.0]
    
    df_betas = pd.DataFrame(index=df_returns.index, columns=['T1', 'T2'])
    df_betas.iloc[-2] = [1.5, 0.5]
    
    pb = PortfolioBuilder(aum=100e6)
    df_w = pb.build_portfolio(df_zscore, df_returns, df_adtv=None, df_betas=df_betas, df_sectors=None)
    
    w1 = df_w.iloc[-1]['T1']
    w2 = df_w.iloc[-1]['T2']
    w_ibov = df_w.iloc[-1]['IBOV_SYNTHETIC']
    
    port_beta_original = w1 * 1.5 + w2 * 0.5
    assert np.isclose(port_beta_original + w_ibov, 0.0)

