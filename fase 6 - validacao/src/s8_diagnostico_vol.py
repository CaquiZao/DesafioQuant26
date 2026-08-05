"""
Bloco 8: diagnostico da pendencia P4 -- por que a vol roda em ~6% e nao 12%.

O SINTOMA
---------
O `PARAMETROS.md` fixa volatilidade-alvo de 12% ao ano. A carteira entrega
~6%. Isso nao e "seguranca extra": em gestao, retorno e risco sao a mesma
alavanca, entao rodar na metade do mandato e deixar metade do retorno na
mesa. O Bloco 3 ja emite um alerta sobre isso, mas ninguem mediu ONDE a
volatilidade se perde.

O QUE ESTE SCRIPT FAZ
---------------------
1. ESTAGIO A ESTAGIO: mede a vol estimada da carteira depois de cada etapa
   do `build_portfolio` -- vol-targeting, travas, suavizacao, hedge. A
   etapa em que a vol despenca e a culpada.

2. QUAL TRAVA MORDE: para cada uma das tres travas (liquidez, nome, setor),
   mede quanto peso ela corta. Se for a de liquidez, o problema e o AUM de
   R$100M contra o volume das small caps -- e nao ha o que "consertar" no
   codigo, e uma restricao real.

3. CURVA DE CAPACIDADE: roda com AUM de 20M, 100M e 300M. Este teste esta
   previsto no PARAMETROS.md secao 7 e nunca tinha sido feito. Ele separa
   de forma definitiva "a estrategia e fraca" de "a estrategia e boa mas
   nao cabe R$100M nela".

Este script NAO altera o pipeline. So mede.

USO
---
    python "fase 6 - validacao/src/s8_diagnostico_vol.py"
"""

import importlib.util
import os
import sys

import numpy as np
import pandas as pd

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _carregar_modulo(nome, caminho):
    spec = importlib.util.spec_from_file_location(nome, caminho)
    modulo = importlib.util.module_from_spec(spec)
    sys.modules[nome] = modulo
    spec.loader.exec_module(modulo)
    return modulo


s6 = _carregar_modulo(
    "s6_validacao",
    os.path.join(BASE_DIR, "fase 6 - validacao", "src", "s6_validacao_oos.py"),
)
s5 = s6.s5


def vol_media(pb, df_weights, df_returns, mascara=None):
    """Vol anualizada media estimada pelo proprio estimador do Bloco 5."""
    serie = pb._estimar_vol_portfolio(df_weights, df_returns)
    if mascara is not None:
        serie = serie.loc[mascara.reindex(serie.index, fill_value=False)]
    return float(serie.dropna().mean())


def gross_medio(df_weights, mascara=None):
    """Exposicao bruta media (soma dos |pesos|) -- o 'tamanho' da carteira."""
    g = df_weights.abs().sum(axis=1)
    if mascara is not None:
        g = g.loc[mascara.reindex(g.index, fill_value=False)]
    return float(g.mean())


def diagnostico_estagios(contexto, df_grafo, aum=100_000_000):
    """
    Reproduz `build_portfolio` passo a passo, medindo a vol depois de cada
    etapa. Usa os metodos do proprio PortfolioBuilder -- nao reimplementa a
    logica, so a instrumenta.
    """
    df_sinal = s6.gerar_sinal(contexto["choques"], df_grafo, s6.s4.JANELA_SUAVIZACAO)

    df_ret, _ = contexto["retornos"].align(df_sinal, join="right")
    df_bet, _ = contexto["betas"].align(df_sinal, join="right")
    df_adt = None
    if contexto["adtv"] is not None:
        df_adt, _ = contexto["adtv"].align(df_sinal, join="right")

    pb = s5.PortfolioBuilder(aum=aum)
    mascara = contexto["periodos"]["completo"]

    etapas = []
    w = df_sinal.copy()
    etapas.append(("0. sinal cru (z-score)", w.copy()))

    for i in range(pb.n_iteracoes_vol):
        w = pb._apply_vol_targeting(w, df_ret)
        etapas.append((f"{i+1}a. apos vol-targeting #{i+1}", w.copy()))
        w = pb._apply_institutional_locks(w, df_adt, contexto["setores"])
        etapas.append((f"{i+1}b. apos travas #{i+1}", w.copy()))

    w_antes_suav = w.copy()
    w = pb._suavizar_pesos(w)
    etapas.append(("4. apos suavizacao dos pesos", w.copy()))

    w = pb._apply_beta_hedge(w, df_bet)
    etapas.append(("5. apos hedge de beta", w.copy()))

    print("\n" + "=" * 70)
    print(f" ONDE A VOLATILIDADE SE PERDE  (AUM = R$ {aum/1e6:.0f}M)")
    print("=" * 70)
    print(f"{'etapa':<34} {'vol est.':>10} {'gross':>10} {'posicoes':>10}")
    print("-" * 70)
    for nome, pesos in etapas:
        colunas = [c for c in pesos.columns if c != "IBOV_SYNTHETIC"]
        v = vol_media(pb, pesos[colunas], df_ret, mascara)
        g = gross_medio(pesos[colunas], mascara)
        n = float((pesos[colunas].abs() > 1e-9).sum(axis=1).mean())
        print(f"{nome:<34} {v:>9.2%} {g:>10.2f} {n:>10.1f}")

    print(f"\nAlvo do projeto: {pb.target_vol:.0%}")

    # A suavizacao e a suspeita numero 1: ela e aplicada DEPOIS do
    # vol-targeting e ninguem recalibra a vol em seguida. Media movel de
    # carteiras parcialmente descorrelacionadas encolhe o book.
    colunas = [c for c in w_antes_suav.columns if c != "IBOV_SYNTHETIC"]
    v_antes = vol_media(pb, w_antes_suav[colunas], df_ret, mascara)
    v_depois = vol_media(pb, pb._suavizar_pesos(w_antes_suav)[colunas], df_ret, mascara)
    if v_antes > 0:
        print(f"\nEfeito isolado da suavizacao: {v_antes:.2%} -> {v_depois:.2%} "
              f"({v_depois/v_antes - 1:+.1%})")

    return pb, df_sinal, df_ret, df_adt, df_bet


def diagnostico_travas(pb, df_sinal, df_ret, df_adt, df_sectors, mascara):
    """
    Mede quanto peso cada trava corta, aplicando-as ISOLADAMENTE sobre a
    mesma carteira de entrada. Identifica qual e a restricao que morde.
    """
    w = pb._apply_vol_targeting(df_sinal.copy(), df_ret)
    gross_entrada = gross_medio(w, mascara)

    print("\n" + "=" * 70)
    print(" QUAL TRAVA MORDE  (aplicada isoladamente sobre a mesma carteira)")
    print("=" * 70)
    print(f"Exposicao bruta antes de qualquer trava: {gross_entrada:.2f}")
    print(f"\n{'trava':<28} {'gross depois':>14} {'corte':>10}")
    print("-" * 70)

    # Liquidez
    if df_adt is not None:
        limite = (df_adt * pb.max_adtv_pct) / pb.aum
        limite, w_alinhado = limite.align(w, join="right")
        w_liq = w_alinhado.clip(lower=-limite, upper=limite)
        g = gross_medio(w_liq, mascara)
        print(f"{'liquidez (10% do ADTV)':<28} {g:>14.2f} {g/gross_entrada - 1:>+9.1%}")

    # Nome
    w_nome = w.clip(lower=-pb.max_weight_name, upper=pb.max_weight_name)
    g = gross_medio(w_nome, mascara)
    print(f"{'por nome (5%)':<28} {g:>14.2f} {g/gross_entrada - 1:>+9.1%}")

    # Setor
    w_setor = pb._apply_institutional_locks(w.copy(), None, df_sectors)
    g = gross_medio(w_setor, mascara)
    print(f"{'por setor (25%)':<28} {g:>14.2f} {g/gross_entrada - 1:>+9.1%}")

    # Todas juntas
    w_todas = pb._apply_institutional_locks(w.copy(), df_adt, df_sectors)
    g = gross_medio(w_todas, mascara)
    print(f"{'TODAS juntas':<28} {g:>14.2f} {g/gross_entrada - 1:>+9.1%}")

    # Quanto o proprio limitador de alavancagem esta segurando
    port_vol = pb._estimar_vol_portfolio(df_sinal, df_ret)
    scalar = (pb.target_vol / port_vol.replace(0, np.nan)).replace([np.inf, -np.inf], np.nan)
    scalar = scalar.dropna()
    no_teto = float((scalar >= pb.max_leverage).mean())
    print(f"\nEscalar de vol pedido pelo alvo -- mediana: {scalar.median():.2f}, "
          f"teto permitido: {pb.max_leverage:.1f}")
    print(f"Dias em que o escalar BATE no teto de alavancagem: {no_teto:.1%}")
    if no_teto > 0.2:
        print("  -> o teto de alavancagem (max_leverage) e uma restricao ativa.")


def curva_capacidade(contexto, df_grafo, aums=(20e6, 100e6, 300e6)):
    """
    Roda o pipeline completo para diferentes tamanhos de fundo.

    Previsto no PARAMETROS.md secao 7 e nunca executado. E o teste que
    separa 'a estrategia e fraca' de 'a estrategia nao cabe em R$100M':
    se o alfa cresce muito ao reduzir o AUM, a trava de liquidez e o
    gargalo e a tese continua viva -- so que com capacidade limitada.
    """
    print("\n" + "=" * 70)
    print(" CURVA DE CAPACIDADE  (PARAMETROS.md secao 7)")
    print("=" * 70)
    print(f"{'AUM':>8} {'periodo':<11} {'alfa/ano':>9} {'vol':>7} {'Sharpe':>7} "
          f"{'giro':>7} {'posicoes':>9}")
    print("-" * 70)

    linhas = []
    for aum in aums:
        df_sinal = s6.gerar_sinal(contexto["choques"], df_grafo, s6.s4.JANELA_SUAVIZACAO)

        df_ret, _ = contexto["retornos"].align(df_sinal, join="right")
        df_bet, _ = contexto["betas"].align(df_sinal, join="right")
        df_adt = None
        if contexto["adtv"] is not None:
            df_adt, _ = contexto["adtv"].align(df_sinal, join="right")

        pb = s5.PortfolioBuilder(aum=aum)
        df_pesos = pb.build_portfolio(
            df_zscore=df_sinal, df_returns=df_ret, df_adtv=df_adt,
            df_betas=df_bet, df_sectors=contexto["setores"],
        )
        retorno_liq, pnl_bruto, giro = s6.rodar_backtest(
            df_pesos, contexto["retornos"], contexto["ibov"]
        )

        for nome_periodo in ("IS 16-20", "OOS 21-25"):
            mascara = contexto["periodos"][nome_periodo]
            m = s6.metricas_periodo(
                retorno_liq, pnl_bruto, giro, contexto["cdi"], mascara, nome_periodo
            )
            if m is None:
                continue
            posicoes = df_pesos.drop(columns=["IBOV_SYNTHETIC"], errors="ignore")
            posicoes = posicoes.loc[posicoes.index.isin(mascara[mascara].index)]
            m["n_posicoes"] = float((posicoes.abs() > 1e-9).sum(axis=1).mean())
            m["aum"] = aum
            linhas.append(m)
            print(f"{aum/1e6:>7.0f}M {nome_periodo:<11} {m['liquido_ano']:>+8.2%} "
                  f"{m['vol_ano']:>6.2%} {m['sharpe']:>7.2f} {m['giro_dia']:>6.1%} "
                  f"{m['n_posicoes']:>9.1f}")

    df = pd.DataFrame(linhas)
    df.to_csv(os.path.join(s6.SAIDA_DIR, "curva_capacidade.csv"), index=False)

    oos = df[df["periodo"] == "OOS 21-25"].sort_values("aum")
    if len(oos) >= 2:
        menor, maior = oos.iloc[0], oos.iloc[-1]
        print(f"\nDo menor ao maior AUM (OOS): alfa {menor['liquido_ano']:+.2%} -> "
              f"{maior['liquido_ano']:+.2%}, vol {menor['vol_ano']:.2%} -> "
              f"{maior['vol_ano']:.2%}")
        if menor["vol_ano"] > maior["vol_ano"] * 1.2:
            print("  -> A trava de LIQUIDEZ e o gargalo: com fundo menor a carteira")
            print("     consegue se aproximar do alvo de vol. Nao ha bug a corrigir;")
            print("     e uma restricao real de capacidade.")
        else:
            print("  -> O AUM quase nao muda a vol: o gargalo NAO e liquidez.")
            print("     Procurar a causa nas outras etapas (suavizacao, travas fixas).")

    return df


def main():
    print("=" * 70)
    print(" BLOCO 8 -- DIAGNOSTICO DA VOLATILIDADE (pendencia P4)")
    print("=" * 70)

    contexto, df_grafo = s6.montar_contexto()

    # Usa o grafo com as direcoes congeladas no in-sample -- o mesmo da
    # validacao P1. Diagnosticar em cima do grafo contaminado daria numeros
    # que nao conversam com o resto da sessao.
    direcoes_is = s6.medir_direcao_por_categoria(
        df_grafo, contexto["choques"], contexto["retornos"], ate=s6.DATA_CORTE
    )
    grafo = s6.construir_variantes(df_grafo, direcoes_is)["congelado_is"]

    pb, df_sinal, df_ret, df_adt, df_bet = diagnostico_estagios(contexto, grafo)
    diagnostico_travas(pb, df_sinal, df_ret, df_adt, contexto["setores"],
                       contexto["periodos"]["completo"])
    curva_capacidade(contexto, grafo)

    print(f"\nResultados salvos em: {s6.SAIDA_DIR}")


if __name__ == "__main__":
    main()
