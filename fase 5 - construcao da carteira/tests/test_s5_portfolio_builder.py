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
    # Sinal SUSTENTADO (e nao um pico de um dia so): o builder suaviza os
    # pesos finais com media movel, entao um pico isolado e diluido de
    # proposito. Pra testar que a trava setorial BATE no limite, o sinal
    # precisa durar mais que a janela de suavizacao.
    DIAS_DE_SINAL = 15
    JANELA_SUAVIZACAO = 10
    assert DIAS_DE_SINAL > JANELA_SUAVIZACAO
    df_zscore.iloc[-DIAS_DE_SINAL:] = 10.0

    df_sectors = pd.DataFrame({
        'Ticker': tickers,
        'Setor': ['Financeiro', 'Financeiro', 'Financeiro', 'Financeiro']
    }).set_index('Ticker')

    pb = PortfolioBuilder(max_weight_sector=0.25, max_weight_name=0.10,
                          janela_suavizacao_pesos=JANELA_SUAVIZACAO)
    df_w = pb.build_portfolio(df_zscore, df_returns, df_adtv=None, df_betas=None, df_sectors=df_sectors)

    soma_setor = abs(df_w.iloc[-1]['A1']) + abs(df_w.iloc[-1]['A2']) + abs(df_w.iloc[-1]['A3']) + abs(df_w.iloc[-1]['A4'])
    assert np.isclose(soma_setor, 0.25, atol=1e-5)


def test_suavizacao_nao_viola_travas():
    """A media movel dos pesos e uma combinacao convexa, entao ela nunca
    pode ESTOURAR uma trava que ja valia antes -- garante que suavizar
    depois das travas (e nao antes) e seguro."""
    np.random.seed(7)
    tickers = ['A1', 'A2', 'A3']
    df_returns = pd.DataFrame(np.random.randn(200, 3)*0.02, columns=tickers)
    df_zscore = pd.DataFrame(np.random.randn(200, 3)*5, columns=tickers)

    df_sectors = pd.DataFrame({
        'Ticker': tickers, 'Setor': ['Financeiro']*3
    }).set_index('Ticker')

    pb = PortfolioBuilder(max_weight_name=0.05, max_weight_sector=0.10,
                          janela_suavizacao_pesos=10)
    df_w = pb.build_portfolio(df_zscore, df_returns, df_adtv=None,
                              df_betas=None, df_sectors=df_sectors).dropna()

    acoes = df_w[tickers]
    assert (acoes.abs() <= 0.05 + 1e-9).all().all(), "trava por nome estourada"
    assert (acoes.abs().sum(axis=1) <= 0.10 + 1e-9).all(), "trava setorial estourada"

def test_suavizacao_respeita_trava_de_liquidez_variavel():
    """A trava de liquidez varia no tempo (o limite do dia t depende do ADTV
    do dia t), diferente das travas por nome e setor, que sao constantes.

    O argumento de convexidade que justifica suavizar DEPOIS das travas
    ("a media de vetores que respeitam um teto tambem respeita o teto") so
    vale para tetos CONSTANTES. Se o volume negociado despenca, a media dos
    pesos dos 10 pregoes anteriores -- calculada quando a acao ainda era
    liquida -- estoura o limite de hoje.

    Este teste reproduz esse cenario: liquidez alta que cai para quase zero.
    A versao anterior do build_portfolio falhava aqui (medido em 04/08:
    60,5% dos dias reais tinham ao menos uma violacao).
    """
    np.random.seed(11)
    tickers = ['LIQ1', 'LIQ2']
    n = 200
    df_returns = pd.DataFrame(np.random.randn(n, 2) * 0.02, columns=tickers)
    df_zscore = pd.DataFrame(np.random.randn(n, 2) * 5, columns=tickers)

    aum = 100e6
    # ADTV alto na primeira metade, colapsando na segunda: o limite de peso
    # cai junto, e a media movel dos pesos "antigos" fica grande demais.
    adtv = pd.DataFrame(index=df_returns.index, columns=tickers, dtype=float)
    adtv.iloc[:n // 2] = 200e6      # limite = 200M * 10% / 100M = 20% -> folgado
    adtv.iloc[n // 2:] = 1e6        # limite = 1M * 10% / 100M = 0,1% -> apertado

    pb = PortfolioBuilder(aum=aum, janela_suavizacao_pesos=10)
    df_w = pb.build_portfolio(df_zscore, df_returns, df_adtv=adtv,
                              df_betas=None, df_sectors=None).dropna()

    # O peso decidido no dia t so e executado em t+1 (shift(1)), e o ADTV de
    # t+1 ainda nao era conhecido na hora da decisao. Por isso o limite
    # relevante e o do dia da DECISAO -- por isso o shift(1) tambem aqui.
    # Uma violacao que so aparece por causa do lag e inerente a execucao
    # real, nao um erro de construcao da carteira.
    limite = ((adtv * pb.max_adtv_pct) / aum).shift(1)
    limite = limite.reindex(df_w.index)
    pesos = df_w[tickers].abs()

    excesso = (pesos - limite).max().max()
    assert excesso <= 1e-9, (
        f"trava de liquidez estourada em {excesso:.4f} apos a suavizacao dos pesos"
    )


def test_acao_delistada_nao_carrega_posicao_fantasma():
    """Acao que para de negociar (retorno vira NaN) nao pode continuar com
    peso na carteira.

    Uma posicao assim consome limite de risco e de setor, entra na conta de
    volatilidade, e rende exatamente zero -- nao pode gerar nem lucro nem
    prejuizo. Num backtest ela mascara o tamanho real do book.

    O ponto sutil: nao basta zerar o SINAL de entrada. A suavizacao dos
    pesos e uma media dos 10 pregoes anteriores, entao ela ressuscita o peso
    de uma acao que ja morreu -- pelo mesmo mecanismo que ressuscitava pesos
    acima da trava de liquidez. Por isso a mascara roda depois de suavizar.
    """
    np.random.seed(3)
    tickers = ['VIVA1', 'MORTA1']
    n = 200
    df_returns = pd.DataFrame(np.random.randn(n, 2) * 0.02, columns=tickers)
    # MORTA1 deixa de negociar na metade da serie.
    df_returns.loc[n // 2:, 'MORTA1'] = np.nan

    df_zscore = pd.DataFrame(np.random.randn(n, 2) * 5, columns=tickers)

    pb = PortfolioBuilder(aum=100e6, janela_suavizacao_pesos=10)
    df_w = pb.build_portfolio(df_zscore, df_returns, df_adtv=None,
                              df_betas=None, df_sectors=None).dropna()

    # Depois do shift(1), o peso da linha t vem da decisao de t-1. A acao
    # morre no indice n//2, entao a partir de n//2+1 nao pode haver peso.
    depois_da_morte = df_w.loc[n // 2 + 1:, 'MORTA1']
    assert (depois_da_morte.abs() < 1e-9).all(), (
        f"posicao fantasma: peso maximo {depois_da_morte.abs().max():.6f} "
        "em acao que parou de negociar"
    )


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

