"""
Bloco 11: grafo point-in-time -- correcao da pendencia P2.

O QUE A P2 COBRA
----------------
O `grafo_manual_base.csv` foi escrito em 2025/2026 por alguem que ja sabe
quem sobreviveu. O `s10` mediu o tamanho disso: 45% do grafo usa empresas
que nao eram liquidas em 2016, e das 39 empresas top-60 de 2016 que
morreram, so 4 aparecem no grafo.

Ter preco das empresas mortas (resolvido em 03/08) nao adianta se o grafo
nunca aponta para elas. E o vies de selecao das RELACOES.

A CORRECAO
----------
`grafo_historico.csv` acrescenta 28 elos entre empresas que eram obvias em
2016-2020 e depois morreram ou foram absorvidas: Kroton/Estacio, B2W/
Magazine Luiza, Lojas Americanas/B2W, Hering/Renner, Cielo/Bradesco,
Gol/Azul, BR Malls/Multiplan, Fibria/Klabin, Linx/Totvs, NotreDame/Hapvida.

REGRA QUE ME IMPUS AO ESCREVER OS ELOS (importante para a defesa)
-----------------------------------------------------------------
So relacoes ESTRUTURAIS verificaveis na epoca -- mesmo setor com disputa
direta, ou controle acionario declarado em balanco. Nenhum elo foi escrito
com base em desfecho que eu conheco. Exemplos do que isso exclui: nao criei
elo "GNDI3 -> RDOR3" porque a Rede D'Or comprou a SulAmerica (evento
posterior), nem "LINX3 -> STNE" pela aquisicao da StoneCo (idem). O elo
LINX3->TOTS3 entra porque Linx e Totvs disputavam software de gestao em
2016, fato independente do que veio depois.

Vigencia: NAO precisa de coluna de data. Um elo morre sozinho quando a
empresa para de ter choque calculado (o `montar_sinal_propagado` ja trata
choque ausente como zero). O que este script PRECISA garantir e o outro
lado do problema -- ver "posicao fantasma" abaixo.

POSICAO FANTASMA
----------------
Se a empresa B morre mas a A continua viva, o grafo segue gerando sinal
para B. O Bloco 5 atribui peso a ela, mas o retorno dela e NaN -- a posicao
ocupa espaco no book (entra na conta de vol e das travas setoriais) e rende
exatamente zero. Isso e um artefato que so aparece quando o grafo inclui
empresas mortas, ou seja, e criado pela propria correcao da P2.

Este script mede o tamanho disso e testa a mascara de negociabilidade que
o resolve.

USO
---
    python "fase 6 - validacao/src/s11_grafo_point_in_time.py"
"""

import importlib.util
import os
import sys

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

CAMINHO_GRAFO_HISTORICO = os.path.join(
    BASE_DIR, "fase 4 - sinal da sinapse", "grafo_historico.csv"
)


def aplicar_regra_conservadora(grafo, contexto):
    """
    Recalcula as direcoes pela regra conservadora (prior economico, invertido
    so onde |t| do in-sample >= 2), usando o grafo passado.

    Precisa ser refeito para o grafo expandido: os t-stats mudam quando 28
    elos novos entram na conta de cada categoria.
    """
    direcoes = s6.medir_direcao_por_categoria(
        grafo, contexto["choques"], contexto["retornos"], ate=s6.DATA_CORTE
    )
    return s6.construir_variantes(grafo, direcoes)["conservador"], direcoes


def medir_posicao_fantasma(df_pesos, df_retornos, nome):
    """
    Quanto do book esta em acoes que NAO tem retorno no dia -- posicoes que
    consomem limite de risco e nao produzem P&L.
    """
    pesos = df_pesos.drop(columns=["IBOV_SYNTHETIC"], errors="ignore").fillna(0.0)
    retornos = df_retornos.reindex(index=pesos.index, columns=pesos.columns)
    gross = pesos.abs().sum(axis=1)

    # Duas medidas que e importante nao confundir:
    #
    # (a) POR CONSTRUCAO: a acao ja nao negociava no dia da DECISAO (t-1).
    #     Manter peso nela e defeito do construtor de carteira.
    # (b) POR LAG: negociava em t-1 e parou em t. Nao havia como saber --
    #     e o custo inevitavel de decidir num dia e executar no seguinte.
    #
    # So (a) e bug. Somar os dois superestima o problema, que foi o que a
    # primeira versao deste script fez.
    sem_retorno_hoje = retornos.isna()
    sem_retorno_na_decisao = retornos.shift(1).isna()

    def fracao(mascara):
        return ((pesos.abs() * mascara).sum(axis=1) / gross.where(gross > 0)).dropna()

    f_constr = fracao(sem_retorno_na_decisao & sem_retorno_hoje)
    f_total = fracao(sem_retorno_hoje)

    print(f"  {nome:<22} por construcao: {f_constr.mean():.2%} | "
          f"total (inclui lag inevitavel): {f_total.mean():.2%}")
    return float(f_constr.mean())


def mascarar_nao_negociaveis(df_sinal, df_retornos):
    """
    Zera o sinal de uma acao nos dias em que ela nao tem retorno -- ou seja,
    nao esta negociando.

    Nao ha look-ahead: a decisao do dia t usa a informacao de que a acao
    negociou em t, e o peso so e executado em t+1 (o `shift(1)` do Bloco 5).
    E a mesma premissa que qualquer mesa usa: so mando ordem de papel que
    esta sendo negociado.
    """
    negociavel = df_retornos.reindex(
        index=df_sinal.index, columns=df_sinal.columns
    ).notna()
    return df_sinal.where(negociavel, 0.0)


def avaliar(nome, grafo, contexto, mascarar=False):
    df_sinal = s6.gerar_sinal(contexto["choques"], grafo, s6.s4.JANELA_SUAVIZACAO)

    if mascarar:
        df_sinal = mascarar_nao_negociaveis(df_sinal, contexto["retornos"])

    df_ret, _ = contexto["retornos"].align(df_sinal, join="right")
    df_bet, _ = contexto["betas"].align(df_sinal, join="right")
    df_adt = None
    if contexto["adtv"] is not None:
        df_adt, _ = contexto["adtv"].align(df_sinal, join="right")

    pb = s5.PortfolioBuilder(aum=100e6)
    df_pesos = pb.build_portfolio(
        df_zscore=df_sinal, df_returns=df_ret, df_adtv=df_adt,
        df_betas=df_bet, df_sectors=contexto["setores"],
    )

    retorno_liq, pnl_bruto, giro = s6.rodar_backtest(
        df_pesos, contexto["retornos"], contexto["ibov"]
    )

    linhas = []
    for periodo in ("IS 16-20", "OOS 21-25", "completo"):
        mascara = contexto["periodos"][periodo]
        m = s6.metricas_periodo(
            retorno_liq, pnl_bruto, giro, contexto["cdi"], mascara, periodo
        )
        if m is None:
            continue
        ic, ic_t, _ = s6.calcular_ic(df_sinal, contexto["retornos"], mascara)
        posicoes = df_pesos.drop(columns=["IBOV_SYNTHETIC"], errors="ignore")
        posicoes = posicoes.loc[posicoes.index.isin(mascara[mascara].index)]
        m.update({
            "variante": nome, "ic": ic, "ic_t": ic_t,
            "n_posicoes": float((posicoes.abs() > 1e-9).sum(axis=1).mean()),
        })
        linhas.append(m)

    return pd.DataFrame(linhas), df_pesos


def main():
    print("=" * 78)
    print(" BLOCO 11 -- GRAFO POINT-IN-TIME (correcao da pendencia P2)")
    print("=" * 78)

    contexto, grafo_atual = s6.montar_contexto()

    grafo_historico = pd.read_csv(CAMINHO_GRAFO_HISTORICO)
    grafo_completo = pd.concat([grafo_atual, grafo_historico], ignore_index=True)

    empresas_atual = set(grafo_atual["empresa_A"]) | set(grafo_atual["empresa_B"])
    empresas_hist = set(grafo_historico["empresa_A"]) | set(grafo_historico["empresa_B"])
    novas = empresas_hist - empresas_atual

    print(f"\nGrafo atual     : {len(grafo_atual)} elos, {len(empresas_atual)} empresas")
    print(f"Grafo historico : {len(grafo_historico)} elos, {len(novas)} empresas novas")
    print(f"Grafo completo  : {len(grafo_completo)} elos, "
          f"{len(empresas_atual | empresas_hist)} empresas")
    print(f"\nEmpresas acrescentadas: {', '.join(sorted(novas))}")

    # Os choques em cache cobrem so as 44 empresas do grafo atual. Com o
    # grafo expandido precisamos recalcular para as novas.
    print("\nRecalculando choques para o grafo expandido (regressao rolling)...")
    tickers = set(grafo_completo["empresa_A"]) | set(grafo_completo["empresa_B"])
    df_choques, df_betas = s6.s4.calcular_choque_limpo(
        contexto["retornos"],
        pd.read_parquet(os.path.join(BASE_DIR, "data", "precos", "indices_retornos.parquet")),
        pd.read_csv(os.path.join(BASE_DIR, "fase 4 - sinal da sinapse", "mapeamento_setores.csv")),
        tickers_alvo=tickers,
    )
    contexto["choques"] = df_choques.astype(float)
    contexto["betas"] = df_betas.astype(float)

    # ---------- Direcoes pela regra conservadora, recalculadas ----------
    print("\n[ETAPA 1] Direcoes pela regra conservadora sobre o grafo EXPANDIDO")
    print("          (in-sample apenas; os t-stats mudam com 28 elos novos)")
    grafo_completo_cons, direcoes = aplicar_regra_conservadora(grafo_completo, contexto)
    print()
    print(direcoes[["tipo_de_elo", "n_elos", "n_obs", "corr_T1", "t_stat",
                    "direcao_decidida"]].to_string(index=False))

    grafo_atual_cons, _ = aplicar_regra_conservadora(grafo_atual, contexto)

    # ---------- Posicao fantasma ----------
    print("\n[ETAPA 2] Posicao fantasma (peso em acao que nao negocia)")
    _, pesos_atual = avaliar("atual", grafo_atual_cons, contexto)
    _, pesos_exp = avaliar("expandido", grafo_completo_cons, contexto)
    medir_posicao_fantasma(pesos_atual, contexto["retornos"], "grafo atual")
    medir_posicao_fantasma(pesos_exp, contexto["retornos"], "grafo expandido")
    _, pesos_exp_m = avaliar("expandido+mascara", grafo_completo_cons, contexto, mascarar=True)
    medir_posicao_fantasma(pesos_exp_m, contexto["retornos"], "expandido + mascara")

    # ---------- Resultado ----------
    print("\n[ETAPA 3] Desempenho")
    variantes = [
        ("atual (30 elos)", grafo_atual_cons, False),
        ("expandido (58)", grafo_completo_cons, False),
        ("expandido+masc", grafo_completo_cons, True),
    ]

    todas = []
    for nome, grafo, mascarar in variantes:
        tabela, _ = avaliar(nome, grafo, contexto, mascarar=mascarar)
        todas.append(tabela)

    resultado = pd.concat(todas, ignore_index=True)
    ordem = {"IS 16-20": 0, "OOS 21-25": 1, "completo": 2}
    resultado = resultado.sort_values(
        ["variante", "periodo"],
        key=lambda c: c.map(ordem) if c.name == "periodo" else c,
    )

    print(f"\n{'variante':<17} {'periodo':<11} {'alfa/ano':>9} {'vol':>7} {'Sharpe':>7} "
          f"{'giro':>7} {'posic':>7} {'IC':>9} {'t(IC)':>7}")
    print("-" * 86)
    for _, r in resultado.iterrows():
        print(f"{r['variante']:<17} {r['periodo']:<11} {r['liquido_ano']:>+8.2%} "
              f"{r['vol_ano']:>6.2%} {r['sharpe']:>7.2f} {r['giro_dia']:>6.1%} "
              f"{r['n_posicoes']:>7.1f} {r['ic']:>+9.4f} {r['ic_t']:>7.2f}")

    resultado.to_csv(os.path.join(s6.SAIDA_DIR, "resultado_point_in_time.csv"), index=False)

    # ---------- Veredito ----------
    print("\n" + "=" * 78)
    print(" VEREDITO")
    print("=" * 78)

    def linha(nome, periodo="OOS 21-25"):
        sel = resultado[(resultado["variante"] == nome) & (resultado["periodo"] == periodo)]
        return sel.iloc[0] if not sel.empty else None

    base = linha("atual (30 elos)")
    exp = linha("expandido+masc")

    if base is None or exp is None:
        print("Sem dados suficientes.")
        return

    print(f"{'':<22}{'atual':>12}{'point-in-time':>16}")
    for rotulo, campo, fmt in [
        ("alfa/ano (OOS)", "liquido_ano", "{:+.2%}"),
        ("Sharpe (OOS)", "sharpe", "{:.2f}"),
        ("volatilidade", "vol_ano", "{:.2%}"),
        ("posicoes", "n_posicoes", "{:.0f}"),
        ("IC", "ic", "{:+.4f}"),
        ("t(IC)", "ic_t", "{:.2f}"),
    ]:
        print(f"{rotulo:<22}{fmt.format(base[campo]):>12}{fmt.format(exp[campo]):>16}")

    base_is = linha("atual (30 elos)", "IS 16-20")
    exp_is = linha("expandido+masc", "IS 16-20")
    print(f"\nAlfa no IN-SAMPLE:    {base_is['liquido_ano']:+.2%}  ->  "
          f"{exp_is['liquido_ano']:+.2%}")

    print("\nComo ler:")
    print("  - O grafo point-in-time inclui empresas que QUEBRARAM. Se o alfa")
    print("    CAIR, isso e a medida direta do vies de selecao que existia --")
    print("    e o numero corrigido e o honesto, mesmo sendo pior.")
    print("  - Se o t(IC) SUBIR, a breadth extra esta ajudando a significancia,")
    print("    que era o gargalo apontado pela P1.")

    if exp["ic_t"] > base["ic_t"]:
        print(f"\n-> t(IC) subiu de {base['ic_t']:.2f} para {exp['ic_t']:.2f}.")
        if exp["ic_t"] > 2.0:
            print("   ULTRAPASSOU o limiar de significancia (t > 2).")
    print(f"\nResultados salvos em: {s6.SAIDA_DIR}")


if __name__ == "__main__":
    main()
