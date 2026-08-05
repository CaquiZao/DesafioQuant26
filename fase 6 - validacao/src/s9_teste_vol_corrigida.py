"""
Bloco 9: teste das correcoes de volatilidade (pendencia P4).

O QUE O DIAGNOSTICO (s8) MOSTROU
--------------------------------
A carteira roda a ~6% contra um alvo de 12%, e a causa NAO e a que o
relatorio de 03/08 supunha (trava de liquidez). Sao duas causas mecanicas:

1. O loop `vol-targeting -> travas` NAO converge em 3 rodadas. Cada
   passagem: o targeting leva a 12%, as travas derrubam. A sequencia
   observada foi 5,73% -> 6,73% -> 7,12% -- ainda subindo quando o loop
   termina.

2. A suavizacao dos pesos roda DEPOIS de todo o loop e derruba a vol em
   mais 16,4% (7,12% -> 5,95%), sem que ninguem recalibre depois. Isso e
   perda pura: a suavizacao existe para controlar giro, nao para reduzir
   risco, e o encolhimento que ela causa e um efeito colateral.

AS CORRECOES TESTADAS
---------------------
- `mais_iteracoes` : leva o loop atual a convergir de fato (10 rodadas).
- `suav_no_loop`   : move a suavizacao para DENTRO do loop, de modo que a
                     calibragem seguinte ja compense o encolhimento.
- `ambas`          : as duas juntas.

RESULTADO (04/08): NENHUMA FUNCIONOU
------------------------------------
A vol praticamente nao se move (6,29% -> 6,50% no melhor caso) e o Sharpe
DESPENCA (0,80 -> 0,39). A causa e que suavizar dentro do loop aplica a
media movel 3 vezes seguidas, o que equivale a uma janela muito maior e
destroi o sinal -- o giro caindo de 6,2% para 5,3% confirma o efeito.

A conclusao e que o gap ate 12% NAO e um erro de ordem de operacoes: e
estrutural. Com ~24 posicoes concentradas em poucos setores, a trava
setorial de 25% limita o tamanho do book, e nao ha reordenacao de etapas
que contorne isso. Ver o veredito no fim do script.

Este arquivo e mantido como REGISTRO DE UM RESULTADO NEGATIVO: sem ele, a
proxima pessoa tentaria as mesmas tres coisas.

O QUE ESPERAR
-------------
Escalar a carteira aumenta alfa e vol na mesma proporcao -- o Sharpe NAO
deve melhorar. Esse e justamente o teste de sanidade: se o Sharpe subir
muito, algo esta errado (nao se cria qualidade de sinal mexendo em
tamanho de posicao). Foi essa checagem que reprovou `suav_no_loop`.

SEGURANCA DAS TRAVAS -- E O BUG QUE ESTE SCRIPT ACHOU
-----------------------------------------------------
A verificacao numerica de travas aqui embutida flagrou um bug real no
pipeline oficial: a versao anterior do `build_portfolio` suavizava os
pesos DEPOIS das travas e nao as reaplicava, apoiada no argumento de
convexidade (|media(w)| <= media(|w|)). Esse argumento vale para limites
CONSTANTES -- mas a trava de liquidez varia no tempo. Resultado medido:
60% dos dias com ao menos uma posicao acima do limite de liquidez.
Corrigido no Bloco 5 em 04/08 (passo 3c) e coberto pelo teste
`test_suavizacao_respeita_trava_de_liquidez_variavel`.

USO
---
    python "fase 6 - validacao/src/s9_teste_vol_corrigida.py"
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


class PortfolioBuilderCorrigido(s5.PortfolioBuilder):
    """
    Variante do construtor com a suavizacao dentro do loop de calibragem.

    A unica mudanca e a ORDEM das operacoes. Nenhuma trava foi afrouxada,
    nenhum parametro de risco foi alterado -- `target_vol`, os limites por
    nome/setor/liquidez e a janela de suavizacao continuam identicos.
    """

    def __init__(self, *args, suavizar_no_loop=True, **kwargs):
        super().__init__(*args, **kwargs)
        self.suavizar_no_loop = suavizar_no_loop

    def build_portfolio(self, df_zscore, df_returns, df_adtv, df_betas, df_sectors):
        df_weights = df_zscore.copy()

        for _ in range(self.n_iteracoes_vol):
            df_weights = self._apply_vol_targeting(df_weights, df_returns)
            df_weights = self._apply_institutional_locks(df_weights, df_adtv, df_sectors)
            if self.suavizar_no_loop:
                # Suavizar AQUI, e nao depois do loop, faz com que a
                # proxima calibragem ja enxergue a carteira encolhida e
                # compense. Suavizar so no fim deixa o encolhimento sem
                # correcao nenhuma.
                df_weights = self._suavizar_pesos(df_weights)

        if not self.suavizar_no_loop:
            df_weights = self._suavizar_pesos(df_weights)

        # Mesma correcao do Bloco 5 (passo 3c): reaplicar as travas depois
        # da ultima suavizacao. Sem isso, a trava de liquidez -- que varia
        # no tempo -- fica violada, e a comparacao entre variantes seria
        # entre carteiras inexequiveis.
        df_weights = self._apply_institutional_locks(df_weights, df_adtv, df_sectors)

        df_weights = self._apply_beta_hedge(df_weights, df_betas)
        return df_weights.shift(1)


def verificar_travas(df_pesos, df_adtv, df_sectors, pb, tolerancia=1e-6):
    """
    Confere numericamente que a carteira final respeita as tres travas.
    Roda em TODAS as variantes -- mudar a ordem das operacoes so vale se os
    limites institucionais continuarem valendo.
    """
    pesos = df_pesos.drop(columns=["IBOV_SYNTHETIC"], errors="ignore").fillna(0.0)
    problemas = []

    excesso_nome = (pesos.abs().max().max() - pb.max_weight_name)
    if excesso_nome > tolerancia:
        problemas.append(f"trava por nome violada em {excesso_nome:.4f}")

    if df_sectors is not None:
        setor_por_ticker = df_sectors["Setor"].to_dict()
        grupos = {}
        for ticker in pesos.columns:
            grupos.setdefault(setor_por_ticker.get(ticker, "Outros"), []).append(ticker)
        pior = 0.0
        for _, tickers in grupos.items():
            soma = pesos[tickers].abs().sum(axis=1).max()
            pior = max(pior, soma)
        if pior - pb.max_weight_sector > tolerancia:
            problemas.append(f"trava setorial violada: max {pior:.4f} > {pb.max_weight_sector}")

    if df_adtv is not None:
        # O peso decidido em t so e executado em t+1 (o `shift(1)` no fim do
        # build_portfolio), e o ADTV de t+1 nao era conhecido na decisao.
        # Por isso o limite comparavel e o do dia da DECISAO -- dai o
        # shift(1) tambem aqui. Sem ele, mediriamos como "violacao" algo que
        # e consequencia inevitavel do lag de execucao.
        limite = ((df_adtv * pb.max_adtv_pct) / pb.aum).shift(1)
        limite = limite.reindex(index=pesos.index, columns=pesos.columns)
        excesso = (pesos.abs() - limite.fillna(float("inf"))).max().max()
        if excesso > tolerancia:
            problemas.append(f"trava de liquidez violada em {excesso:.4f}")

    return problemas


def avaliar(nome, construtor, contexto, grafo):
    df_sinal = s6.gerar_sinal(contexto["choques"], grafo, s6.s4.JANELA_SUAVIZACAO)

    df_ret, _ = contexto["retornos"].align(df_sinal, join="right")
    df_bet, _ = contexto["betas"].align(df_sinal, join="right")
    df_adt = None
    if contexto["adtv"] is not None:
        df_adt, _ = contexto["adtv"].align(df_sinal, join="right")

    df_pesos = construtor.build_portfolio(
        df_zscore=df_sinal, df_returns=df_ret, df_adtv=df_adt,
        df_betas=df_bet, df_sectors=contexto["setores"],
    )

    problemas = verificar_travas(df_pesos, df_adt, contexto["setores"], construtor)

    retorno_liq, pnl_bruto, giro = s6.rodar_backtest(
        df_pesos, contexto["retornos"], contexto["ibov"]
    )

    linhas = []
    for periodo in ("IS 16-20", "OOS 21-25"):
        mascara = contexto["periodos"][periodo]
        m = s6.metricas_periodo(
            retorno_liq, pnl_bruto, giro, contexto["cdi"], mascara, periodo
        )
        if m is None:
            continue
        m["variante"] = nome
        linhas.append(m)

    return pd.DataFrame(linhas), problemas


def main():
    print("=" * 74)
    print(" BLOCO 9 -- TESTE DAS CORRECOES DE VOLATILIDADE (pendencia P4)")
    print("=" * 74)

    contexto, df_grafo = s6.montar_contexto()
    direcoes_is = s6.medir_direcao_por_categoria(
        df_grafo, contexto["choques"], contexto["retornos"], ate=s6.DATA_CORTE
    )
    grafo = s6.construir_variantes(df_grafo, direcoes_is)["congelado_is"]

    variantes = {
        "atual": s5.PortfolioBuilder(aum=100e6),
        "mais_iteracoes": PortfolioBuilderCorrigido(
            aum=100e6, n_iteracoes_vol=10, suavizar_no_loop=False),
        "suav_no_loop": PortfolioBuilderCorrigido(
            aum=100e6, n_iteracoes_vol=3, suavizar_no_loop=True),
        "ambas": PortfolioBuilderCorrigido(
            aum=100e6, n_iteracoes_vol=10, suavizar_no_loop=True),
    }

    todas = []
    travas_ok = {}
    for nome, construtor in variantes.items():
        print(f"\n  --> variante '{nome}'")
        tabela, problemas = avaliar(nome, construtor, contexto, grafo)
        todas.append(tabela)
        travas_ok[nome] = problemas

    resultado = pd.concat(todas, ignore_index=True)

    print("\n" + "=" * 74)
    print(" RESULTADO")
    print("=" * 74)
    print(f"{'variante':<16} {'periodo':<11} {'vol':>7} {'alfa/ano':>9} "
          f"{'Sharpe':>7} {'giro':>7} {'dd max':>8}")
    print("-" * 74)
    for _, r in resultado.iterrows():
        print(f"{r['variante']:<16} {r['periodo']:<11} {r['vol_ano']:>6.2%} "
              f"{r['liquido_ano']:>+8.2%} {r['sharpe']:>7.2f} {r['giro_dia']:>6.1%} "
              f"{r['dd_max']:>7.1%}")

    print("\nVerificacao das travas institucionais na carteira final:")
    for nome, problemas in travas_ok.items():
        if problemas:
            print(f"  {nome:<16} FALHOU -> {'; '.join(problemas)}")
        else:
            print(f"  {nome:<16} OK (nome, setor e liquidez respeitados)")

    resultado.to_csv(os.path.join(s6.SAIDA_DIR, "teste_vol_corrigida.csv"), index=False)

    # ---------- Veredito ----------
    print("\n" + "=" * 74)
    print(" VEREDITO")
    print("=" * 74)

    oos = resultado[resultado["periodo"] == "OOS 21-25"].set_index("variante")
    base = oos.loc["atual"]
    melhor = oos["vol_ano"].idxmax()
    linha = oos.loc[melhor]

    print(f"Melhor variante por volatilidade: '{melhor}'")
    print(f"  Vol      : {base['vol_ano']:.2%} -> {linha['vol_ano']:.2%}  "
          f"(alvo: 12%)")
    print(f"  Alfa/ano : {base['liquido_ano']:+.2%} -> {linha['liquido_ano']:+.2%}")
    print(f"  Sharpe   : {base['sharpe']:.2f} -> {linha['sharpe']:.2f}")
    print(f"  Giro/dia : {base['giro_dia']:.1%} -> {linha['giro_dia']:.1%}")

    delta_sharpe = linha["sharpe"] - base["sharpe"]
    print(f"\nTeste de sanidade -- variacao do Sharpe: {delta_sharpe:+.2f}")
    if abs(delta_sharpe) < 0.15:
        print("  OK: o Sharpe ficou praticamente igual, como esperado. Mudar o")
        print("  TAMANHO das posicoes escala alfa e risco juntos; nao cria nem")
        print("  destroi qualidade de sinal.")
    else:
        print("  ATENCAO: o Sharpe mudou mais do que deveria para uma alteracao")
        print("  que so mexe em tamanho de posicao. Investigar antes de adotar.")

    if linha["vol_ano"] < 0.5 * 0.12:
        print("\n-> Mesmo corrigido, o book fica MUITO abaixo do alvo de 12%.")
        print("   O limite restante e ESTRUTURAL: com ~24 posicoes concentradas")
        print("   em poucos setores, a trava setorial de 25% impede um book")
        print("   maior. Nao ha ajuste de codigo que resolva -- so mais elos")
        print("   (pendencia P3) aumentam o teto de vol alcancavel.")
    else:
        print(f"\n-> A vol subiu para {linha['vol_ano']:.2%}. O restante do gap ate 12%")
        print("   depende de mais diversificacao (P3).")

    print(f"\nResultados salvos em: {s6.SAIDA_DIR}")


if __name__ == "__main__":
    main()
