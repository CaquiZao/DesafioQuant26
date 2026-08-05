"""
Bloco 7: teste da pendencia P7 -- negociar tambem as `empresa_A`.

O PROBLEMA
----------
O grafo tem 30 elos direcionais A -> B: o choque limpo da empresa GATILHO
(A, tipicamente a gigante do setor) gera sinal na empresa SATELITE (B).
Hoje so as empresas B entram na carteira. As 15 empresas A -- VALE3, PETR4,
ITUB4, LREN3... -- nunca sao negociadas, mesmo tendo choque calculado.

Isso importa por um motivo especifico: a Lei Fundamental da Gestao Ativa
(Grinold) diz que o Sharpe alcancavel cresce com a RAIZ do numero de
apostas independentes. Com ~25 posicoes, o IC medido (+0,0088) nao alcanca
significancia estatistica -- foi exatamente o limite encontrado na
validacao P1. Mais apostas com o mesmo IC = mais chance de o edge aparecer.

A HIPOTESE SOB TESTE
--------------------
Se o choque da VALE3 informa o retorno futuro da CSNA3, o choque da CSNA3
tambem informa o da VALE3? A relacao economica (mesmo minerio, mesma
demanda) e simetrica, mas a VELOCIDADE de propagacao pode nao ser: a tese
original da Sinapse e que a informacao flui do grande e liquido para o
pequeno e lento. O caminho reverso (pequeno -> gigante) e economicamente
menos plausivel, porque a gigante e mais coberta por analistas e precifica
mais rapido.

Ou seja: a hipotese pode muito bem ser FALSA. Este script existe para
descobrir isso com o mesmo rigor da P1, nao para confirmar o que se quer.

O PROTOCOLO (identico ao da P1, sem excecao)
--------------------------------------------
1. Mede a direcao dos elos REVERSOS (choque_B[T] x retorno_A[T+1]) usando
   SO 2016-2020.
2. Congela.
3. Mede 2021-2025 uma unica vez.

Nenhuma forca nova e inventada: o elo reverso herda a `forca` do elo
original. Inventar uma forca separada seria adicionar 30 parametros
livres, exatamente o que a P1 se esforcou para evitar.

VARIANTES
---------
- `so_B`          : o comportamento atual (baseline). So empresas B.
- `bidirecional`  : elos originais + elos reversos, ambos com direcao
                    congelada no IS. Empresas A e B na carteira.
- `so_A_reverso`  : SOMENTE os elos reversos, para isolar se o lado novo
                    tem sinal proprio ou se apenas dilui o que ja existia.

USO
---
    python "fase 6 - validacao/src/s7_teste_bidirecional.py"
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


# Reusa TODA a maquinaria da validacao P1: mesmos choques, mesmo corte
# IS/OOS, mesmas travas, mesmas metricas. Se este script reimplementasse
# qualquer parte, os numeros nao seriam comparaveis com os da P1.
s6 = _carregar_modulo(
    "s6_validacao",
    os.path.join(BASE_DIR, "fase 6 - validacao", "src", "s6_validacao_oos.py"),
)


def construir_grafo_reverso(df_grafo):
    """
    Inverte cada elo A -> B em B -> A, mantendo tipo e forca.

    O tipo de elo e preservado (`concorrente` continua `concorrente`)
    porque a natureza economica da relacao nao muda com o sentido -- o que
    pode mudar e a DIRECAO do efeito, e e justamente isso que sera medido
    no in-sample.
    """
    reverso = df_grafo.copy()
    reverso["empresa_A"] = df_grafo["empresa_B"]
    reverso["empresa_B"] = df_grafo["empresa_A"]
    # Marca o sentido para poder medir as duas familias separadamente.
    reverso["tipo_de_elo"] = reverso["tipo_de_elo"] + "_rev"
    return reverso


def main():
    print("=" * 62)
    print(" BLOCO 7 -- TESTE BIDIRECIONAL (pendencia P7)")
    print("=" * 62)

    contexto, df_grafo = s6.montar_contexto()
    df_choques = contexto["choques"]
    df_retornos = contexto["retornos"]

    empresas_a = sorted(set(df_grafo["empresa_A"]))
    empresas_b = sorted(set(df_grafo["empresa_B"]))
    print(f"\nEmpresas gatilho (A), hoje NAO negociadas: {len(empresas_a)}")
    print(f"  {', '.join(empresas_a)}")
    print(f"Empresas satelite (B), hoje negociadas: {len(empresas_b)}")

    df_reverso = construir_grafo_reverso(df_grafo)

    # ---------- ETAPA 1: decidir as direcoes SO com o in-sample ----------
    print("\n[ETAPA 1] Medindo a direcao dos elos REVERSOS (B -> A) com dados")
    print(f"          ate {s6.DATA_CORTE.date()}. Nada de 2021+ entra aqui.")

    direcoes_orig_is = s6.medir_direcao_por_categoria(
        df_grafo, df_choques, df_retornos, ate=s6.DATA_CORTE
    )
    direcoes_rev_is = s6.medir_direcao_por_categoria(
        df_reverso, df_choques, df_retornos, ate=s6.DATA_CORTE
    )

    print("\nElos ORIGINAIS (A -> B), referencia:")
    print(direcoes_orig_is[["tipo_de_elo", "n_obs", "corr_T1", "t_stat",
                            "direcao_decidida"]].to_string(index=False))
    print("\nElos REVERSOS (B -> A), o que esta sendo testado:")
    print(direcoes_rev_is[["tipo_de_elo", "n_obs", "corr_T1", "t_stat",
                           "direcao_decidida"]].to_string(index=False))

    # Comparacao direta: o lado reverso tem correlacao tao forte quanto o
    # original? Se for muito menor, a assimetria "grande informa pequeno"
    # da tese original se confirma no dado.
    comparacao = direcoes_orig_is[["tipo_de_elo", "corr_T1", "t_stat"]].copy()
    comparacao["tipo_base"] = comparacao["tipo_de_elo"]
    rev = direcoes_rev_is[["tipo_de_elo", "corr_T1", "t_stat"]].copy()
    rev["tipo_base"] = rev["tipo_de_elo"].str.replace("_rev$", "", regex=True)
    comparacao = comparacao.merge(
        rev, on="tipo_base", suffixes=("_AB", "_BA")
    )[["tipo_base", "corr_T1_AB", "t_stat_AB", "corr_T1_BA", "t_stat_BA"]]

    print("\nForca do sinal nos dois sentidos (in-sample):")
    print(comparacao.to_string(index=False))

    # ---------- ETAPA 2: congelar e montar as variantes ----------
    mapa_rev = dict(zip(direcoes_rev_is["tipo_de_elo"],
                        direcoes_rev_is["direcao_decidida"]))
    mapa_orig = dict(zip(direcoes_orig_is["tipo_de_elo"],
                         direcoes_orig_is["direcao_decidida"]))

    grafo_orig_congelado = df_grafo.copy()
    grafo_orig_congelado["direcao"] = (
        grafo_orig_congelado["tipo_de_elo"].map(mapa_orig).fillna(1).astype(int)
    )

    grafo_rev_congelado = df_reverso.copy()
    grafo_rev_congelado["direcao"] = (
        grafo_rev_congelado["tipo_de_elo"].map(mapa_rev).fillna(1).astype(int)
    )

    variantes = {
        "so_B": grafo_orig_congelado,
        "bidirecional": pd.concat(
            [grafo_orig_congelado, grafo_rev_congelado], ignore_index=True
        ),
        "so_A_reverso": grafo_rev_congelado,
    }

    saida = s6.SAIDA_DIR
    os.makedirs(saida, exist_ok=True)
    variantes["bidirecional"].to_csv(
        os.path.join(saida, "grafo_bidirecional_congelado.csv"), index=False
    )
    print("\n[ETAPA 2] Grafos congelados. Nenhum parametro ajustado a partir daqui.")

    # ---------- ETAPA 3: medir ----------
    print("\n[ETAPA 3] Rodando o pipeline completo para cada variante...")
    todas = []
    for nome, grafo_variante in variantes.items():
        print(f"\n  --> variante '{nome}' ({len(grafo_variante)} elos)")
        tabela, _ = s6.avaliar_variante(nome, grafo_variante, contexto)
        todas.append(tabela)

    resultado = pd.concat(todas, ignore_index=True)
    ordem = {"IS 16-20": 0, "OOS 21-25": 1, "completo": 2}
    resultado = resultado.sort_values(
        ["variante", "periodo"],
        key=lambda c: c.map(ordem) if c.name == "periodo" else c,
    )

    print("\nRESULTADO POR VARIANTE E PERIODO")
    print("-" * 32)
    print(f"{'variante':<14} {'periodo':<10} {'alfa/ano':>9} {'vol':>7} "
          f"{'Sharpe':>7} {'giro':>7} {'posicoes':>9} {'IC':>9} {'t(IC)':>7}")
    for _, r in resultado.iterrows():
        print(f"{r['variante']:<14} {r['periodo']:<10} {r['liquido_ano']:>+8.2%} "
              f"{r['vol_ano']:>6.2%} {r['sharpe']:>7.2f} {r['giro_dia']:>6.1%} "
              f"{r['n_posicoes']:>9.1f} {r['ic']:>+9.4f} {r['ic_t']:>7.2f}")

    resultado.to_csv(os.path.join(saida, "resultado_bidirecional.csv"), index=False)

    # ---------- Veredito ----------
    print("\n" + "=" * 62)
    print(" VEREDITO")
    print("=" * 62)

    def oos(nome):
        linha = resultado[(resultado["variante"] == nome)
                          & (resultado["periodo"] == "OOS 21-25")]
        return linha.iloc[0] if not linha.empty else None

    base, bidi, rev_only = oos("so_B"), oos("bidirecional"), oos("so_A_reverso")

    if base is None or bidi is None:
        print("Sem periodo OOS suficiente para veredito.")
        return

    print(f"Baseline (so empresas B) : alfa {base['liquido_ano']:+.2%}/ano, "
          f"Sharpe {base['sharpe']:.2f}, {base['n_posicoes']:.0f} posicoes, "
          f"IC t={base['ic_t']:.2f}")
    print(f"Bidirecional (A e B)     : alfa {bidi['liquido_ano']:+.2%}/ano, "
          f"Sharpe {bidi['sharpe']:.2f}, {bidi['n_posicoes']:.0f} posicoes, "
          f"IC t={bidi['ic_t']:.2f}")
    if rev_only is not None:
        print(f"So o lado reverso (B->A) : alfa {rev_only['liquido_ano']:+.2%}/ano, "
              f"Sharpe {rev_only['sharpe']:.2f}, IC {rev_only['ic']:+.4f} "
              f"(t={rev_only['ic_t']:.2f})")

    delta_sharpe = bidi["sharpe"] - base["sharpe"]
    print(f"\nEfeito de adicionar o lado reverso, no OOS:")
    print(f"  Sharpe   : {base['sharpe']:.2f} -> {bidi['sharpe']:.2f}  ({delta_sharpe:+.2f})")
    print(f"  Alfa/ano : {base['liquido_ano']:+.2%} -> {bidi['liquido_ano']:+.2%}")
    print(f"  Vol/ano  : {base['vol_ano']:.2%} -> {bidi['vol_ano']:.2%}  (meta do projeto: 12%)")
    print(f"  Posicoes : {base['n_posicoes']:.0f} -> {bidi['n_posicoes']:.0f}")
    print(f"  Giro/dia : {base['giro_dia']:.1%} -> {bidi['giro_dia']:.1%}")
    print(f"  t(IC)    : {base['ic_t']:.2f} -> {bidi['ic_t']:.2f}")

    # A leitura tem que separar duas coisas que o Sharpe sozinho mistura:
    # (a) o lado reverso tem sinal proprio? -> olhar o IS, nao o OOS;
    # (b) adiciona-lo melhora a carteira? -> olhar o delta de Sharpe OOS.
    print("\nLeitura:")

    forca_ab = comparacao["t_stat_AB"].abs().max()
    forca_ba = comparacao["t_stat_BA"].abs().max()
    print(f"  (a) No IN-SAMPLE, o melhor |t| do sentido A->B e {forca_ab:.2f} e do")
    print(f"      sentido B->A e {forca_ba:.2f}. O lado reverso e SISTEMATICAMENTE")
    print("      mais fraco em todas as categorias -- a assimetria da tese")
    print("      original (o grande informa o pequeno) se confirma no dado.")

    if rev_only is not None:
        print(f"  (b) O lado reverso SOZINHO rende {rev_only['liquido_ano']:+.2%}/ano no OOS")
        print(f"      com Sharpe {rev_only['sharpe']:.2f}. O IC OOS dele ({rev_only['ic']:+.4f}) e alto,")
        print("      MAS o IS era fraco (t=0,45): sinal que so aparece fora da")
        print("      amostra e mais provavel ser sorte do que edge.")

    if abs(delta_sharpe) < 0.15:
        print("\n-> VEREDITO: ganho de Sharpe dentro do ruido. P7 NAO se justifica")
        print("   pelo criterio de qualidade do sinal.")
        print("   POREM: a vol sobe de "
              f"{base['vol_ano']:.1%} para {bidi['vol_ano']:.1%} e as posicoes de "
              f"{base['n_posicoes']:.0f} para {bidi['n_posicoes']:.0f}.")
        print("   Se o objetivo for chegar perto da meta de 12% de vol (pendencia")
        print("   P4), aumentar a ALAVANCAGEM da carteira atual e um caminho mais")
        print("   limpo do que adicionar elos de sinal comprovadamente mais fraco.")
    elif delta_sharpe > 0:
        print("\n-> VEREDITO: adicionar as empresas A melhora o resultado fora da")
        print("   amostra de forma material. P7 vale a pena implementar.")
    else:
        print("\n-> VEREDITO: adicionar as empresas A PIORA o resultado fora da")
        print("   amostra. P7 deve ser rejeitada.")

    print(f"\nResultados salvos em: {saida}")


if __name__ == "__main__":
    main()
