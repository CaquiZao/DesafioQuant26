"""
Bloco 3b: modelo de custo de transacao realista para o mercado brasileiro.

POR QUE ESTE ARQUIVO EXISTE
---------------------------
O backtest usava um custo unico de 5 bps sobre o giro. Isso e um numero de
LARGE CAP LIQUIDA aplicado a um book majoritariamente mid cap: medido, 73% do
giro da carteira estava abaixo de R$150 milhoes de ADTV. O custo realizado
com o modelo abaixo e ~20 bps por unidade de giro -- 4x o assumido.

Alem disso faltavam dois componentes inteiros:
  - IMPACTO DE MERCADO: o custo de 5 bps era linear e independente do tamanho
    da ordem. Ordem grande contra livro fino custa mais, e isso e o que limita
    a capacidade de qualquer estrategia.
  - ALUGUEL (BTC) da ponta vendida, que e ~40% do AUM. Uma carteira long-short
    paga para tomar emprestado o que vende. Ignorar isso e o erro mais comum
    em backtest de long-short, e o mais facil de uma banca apontar.

Um backtest sem esses dois termos nao e conservador -- e otimista de um jeito
que nao aparece no numero final.

AS TRES CAMADAS
---------------
1. SPREAD + TAXAS, por faixa de liquidez. So os emolumentos sao observaveis;
   o meio-spread e estimativa e esta declarado como tal.
2. IMPACTO, pela lei da raiz quadrada (Almgren-Chriss / BARRA-Torre), que e o
   padrao de industria:  impacto = eta * sigma_diaria * sqrt(Q / ADTV)
3. ALUGUEL, por faixa de liquidez, sobre a ponta vendida.

O QUE E OBSERVAVEL E O QUE E ESTIMADO
-------------------------------------
Observavel : emolumentos + liquidacao da B3 (tabela publica).
Contratual : corretagem institucional (negociada; a faixa aqui e tipica).
ESTIMADO   : meio-spread por faixa, eta do impacto, taxa de aluguel. Estes
             tres exigiriam TAQ intradiario e dado de BTC da B3 para serem
             medidos. Sao os parametros que a analise de sensibilidade
             (`sensibilidade_eta`) existe para expor.

NAO CALIBRAMOS NENHUM DELES PARA MELHORAR O RESULTADO. Sao numeros de
mercado, e a tabela de sensibilidade mostra o resultado em toda a faixa
plausivel -- e o que separa "modelamos custo" de "escolhemos um custo".
"""

import numpy as np
import pandas as pd

DIAS_UTEIS_ANO = 252

# ------------------------------------------------------------------
# 1) SPREAD + TAXAS, por faixa de ADTV (em bps, por PONTA)
# ------------------------------------------------------------------
# Faixas em R$ milhoes de ADTV21. O total por ponta e
# meio-spread + emolumentos + corretagem.
FAIXAS_ADTV = [150e6, 50e6, 20e6, 0.0]          # limites inferiores, decrescente
MEIO_SPREAD_BPS = [2.0, 5.0, 11.0, 24.0]        # ESTIMADO
EMOLUMENTOS_BPS = 2.3                            # observavel (tabela B3)
CORRETAGEM_BPS = [3.0, 3.0, 3.5, 4.0]           # contratual

# ------------------------------------------------------------------
# 2) IMPACTO DE MERCADO
# ------------------------------------------------------------------
# impacto_bps = ETA * sigma_diaria_bps * sqrt(participacao)
# ETA entre 0,3 e 1,0 na literatura; 0,4 e o meio da faixa.
ETA_IMPACTO = 0.4
JANELA_VOL_IMPACTO = 60
PARTICIPACAO_MAXIMA = 0.25   # clip: acima disso a ordem nao seria executada assim

# ------------------------------------------------------------------
# 3) ALUGUEL (BTC), % ao ano sobre a ponta vendida, por faixa de ADTV
# ------------------------------------------------------------------
ALUGUEL_ANUAL = [0.010, 0.020, 0.035, 0.060]     # ESTIMADO


def _indice_faixa(adtv):
    """Devolve o indice da faixa de liquidez (0 = mais liquida)."""
    idx = np.full(adtv.shape, len(FAIXAS_ADTV) - 1, dtype=int)
    for i, limite in enumerate(FAIXAS_ADTV):
        idx = np.where(adtv >= limite, np.minimum(idx, i), idx)
    return idx


def _por_faixa(adtv, valores):
    """Mapeia cada celula de ADTV para o valor da sua faixa."""
    idx = _indice_faixa(adtv.to_numpy(dtype=float))
    arr = np.asarray(valores, dtype=float)[idx]
    return pd.DataFrame(arr, index=adtv.index, columns=adtv.columns)


def custo_por_dia(df_weights, df_adtv, df_returns, aum,
                  eta=ETA_IMPACTO, usar_impacto=True, usar_aluguel=True):
    """
    Custo diario total, em fracao do AUM. Devolve (custo_total, componentes).

    `df_weights` deve ser a matriz FINAL (ja com lag), incluindo
    IBOV_SYNTHETIC -- o hedge tem custo proprio, tratado como large cap.
    """
    acoes = [c for c in df_weights.columns if c != "IBOV_SYNTHETIC"]
    W = df_weights[acoes].fillna(0.0)

    adtv = df_adtv.reindex(index=W.index, columns=W.columns)
    # ADTV desconhecido: tratamos como a faixa MENOS liquida, nunca como a
    # mais liquida. Erro para o lado conservador.
    adtv = adtv.fillna(0.0)

    dW = W.diff().abs().fillna(0.0)

    # ---- camada 1: spread + taxas ----
    bps_ponta = (_por_faixa(adtv, MEIO_SPREAD_BPS)
                 + EMOLUMENTOS_BPS
                 + _por_faixa(adtv, CORRETAGEM_BPS))
    c_spread = (dW * bps_ponta / 1e4).sum(axis=1)

    # ---- camada 2: impacto ----
    if usar_impacto:
        sigma = df_returns.reindex(index=W.index, columns=W.columns) \
                          .rolling(JANELA_VOL_IMPACTO, min_periods=20).std()
        sigma = sigma.fillna(sigma.median(axis=1).median())
        # participacao da ordem no volume do dia
        with np.errstate(divide="ignore", invalid="ignore"):
            part = (dW * aum) / adtv.replace(0.0, np.nan)
        part = part.clip(upper=PARTICIPACAO_MAXIMA).fillna(PARTICIPACAO_MAXIMA)
        impacto_frac = eta * sigma * np.sqrt(part)
        c_impacto = (dW * impacto_frac).sum(axis=1)
    else:
        c_impacto = pd.Series(0.0, index=W.index)

    # ---- camada 3: aluguel da ponta vendida ----
    if usar_aluguel:
        short = W.clip(upper=0.0).abs()
        taxa_dia = _por_faixa(adtv, ALUGUEL_ANUAL) / DIAS_UTEIS_ANO
        c_aluguel = (short * taxa_dia).sum(axis=1)
    else:
        c_aluguel = pd.Series(0.0, index=W.index)

    # ---- hedge de indice: futuro, custo baixo ----
    if "IBOV_SYNTHETIC" in df_weights.columns:
        d_hedge = df_weights["IBOV_SYNTHETIC"].fillna(0.0).diff().abs().fillna(0.0)
        c_hedge = d_hedge * (0.2 + 2.0) / 1e4      # emolumento + meio-spread do 1o vencimento
    else:
        c_hedge = pd.Series(0.0, index=W.index)

    total = c_spread + c_impacto + c_aluguel + c_hedge
    componentes = pd.DataFrame({
        "spread_taxas": c_spread,
        "impacto": c_impacto,
        "aluguel": c_aluguel,
        "hedge": c_hedge,
        "total": total,
    })
    return total, componentes


def resumo_custo(componentes, giro_diario):
    """Decomposicao anualizada e custo implicito por unidade de giro."""
    ano = componentes.mean() * DIAS_UTEIS_ANO
    giro_medio = float(giro_diario.mean())
    bps_por_giro = (float(componentes["total"].mean()) / giro_medio * 1e4) if giro_medio else np.nan
    return ano, giro_medio, bps_por_giro


def tabela_breakeven(pnl_bruto, giro_diario):
    """
    Custo (em bps por unidade de giro) que zera o alfa.

    E o numero mais defensavel do projeto: mostra que o resultado NAO depende
    da nossa calibracao de custo, e sim de uma propriedade do sinal -- quanto
    alfa ele produz por unidade de negociacao.
    """
    alfa_dia = float(pnl_bruto.mean())
    giro_medio = float(giro_diario.mean())
    if giro_medio <= 0:
        return np.nan, np.nan
    breakeven_bps = alfa_dia / giro_medio * 1e4
    alfa_por_giro_bps = breakeven_bps
    return breakeven_bps, alfa_por_giro_bps
