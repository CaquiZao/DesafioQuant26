"""
Bloco 6: o controle por SUBSETOR submetido ao protocolo IS/OOS.

POR QUE ESTE SCRIPT EXISTE
--------------------------
O controle por subsetor foi implementado (`fase 4/src/s4c_subsetores.py`),
medido e DESLIGADO -- ver o bloco `USAR_SUBSETOR` no topo do Bloco 4. Com
limiar de 5 pares minimos, o Sharpe OOS caiu de 0,50 para 0,14.

O diagnostico daquele teste mostrou que o dano se concentrava inteiramente
nos subsetores PEQUENOS (indice de 5 a 7 acoes perdeu -0,0111 de correlacao
T+1; de 8+ acoes ficou neutro). A conclusao obvia seria "sobe o limiar para
8". Mas 8 foi lido OLHANDO O OOS -- e escolher parametro assim e exatamente
o data snooping que a pendencia P1 existe para bloquear. Ceder ali teria
invalidado o resultado.

Este script faz a coisa certa: submete a escolha do limiar ao MESMO protocolo
que validou as direcoes do grafo.

O PROTOCOLO (fixado ANTES de rodar, e este arquivo e o compromisso)
-------------------------------------------------------------------
1. GRADE pre-especificada de limiares, incluindo o baseline. Nao se
   acrescenta valor a grade depois de ver resultado.
2. DECISAO mecanica: vence o maior IC medido SO em 2016-2020. Sem
   julgamento, sem desempate qualitativo, sem "mas o segundo colocado tem
   um perfil melhor".
3. CONGELA num CSV.
4. MEDE 2021-2025 uma vez. O numero que sair e o numero.

O BASELINE E CANDIDATO. Se "so setor" vencer no in-sample, a ideia do
subsetor esta rejeitada pelo proprio protocolo -- e essa e uma resposta tao
valida quanto a outra, obtida sem espiar o futuro.

POR QUE O CRITERIO E O IC, E NAO O SHARPE
-----------------------------------------
O IC mede a qualidade do SINAL, que e o que o subsetor mexe. Sharpe e alfa
passam por travas institucionais, vol-targeting e custo -- camadas que nao
tem nada a ver com a hipotese em teste e que adicionam ruido a decisao. O
projeto ja trata o IC como a metrica primaria pelo mesmo motivo (ver o
veredito do `s6`).

POR QUE NAO HA LOOK-AHEAD EM CALCULAR OS CHOQUES NA AMOSTRA INTEIRA
-------------------------------------------------------------------
A regressao do Bloco 4 e rolling de 252 dias e so olha para tras: o choque
do dia T usa apenas dados <= T. O corte IS/OOS entra na hora de MEDIR, nao
de calcular -- mesma premissa que o `s6` ja usa.

USO
---
    python "fase 6 - validacao/src/s13_protocolo_subsetor.py"
    python "fase 6 - validacao/src/s13_protocolo_subsetor.py" --recalcular
"""

import argparse
import importlib.util
import os
import sys

import numpy as np
import pandas as pd

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_DIR = os.path.join(BASE_DIR, "data")
SAIDA_DIR = os.path.join(DATA_DIR, "validacao", "subsetor")


def _carregar_modulo(nome, caminho_relativo):
    caminho = os.path.join(BASE_DIR, caminho_relativo)
    spec = importlib.util.spec_from_file_location(nome, caminho)
    modulo = importlib.util.module_from_spec(spec)
    sys.modules[nome] = modulo
    spec.loader.exec_module(modulo)
    return modulo


s6 = _carregar_modulo(
    "s6_validacao", os.path.join("fase 6 - validacao", "src", "s6_validacao_oos.py")
)
s4 = sys.modules["s4_sinapse"]
s5 = sys.modules["s5_builder"]
s3 = sys.modules["s3_backtest"]

DATA_CORTE = s6.DATA_CORTE
DIAS_UTEIS_ANO = s6.DIAS_UTEIS_ANO
JANELA_SINAL = s4.JANELA_SUAVIZACAO
JANELA_PESOS = 10


# ==================================================================
# O COMPROMISSO -- fixado antes de qualquer medicao
# ==================================================================

# `None` = baseline: so o setor B3, que e o que roda em producao hoje.
# Os demais sao o minimo de pares para o subsetor valer como controle.
#
# A grade cobre de "quase sem restricao" (3) ate "so subsetores grandes"
# (20). Acima de 20 sobram pouquissimos subsetores e o resultado converge
# para o baseline por construcao, entao estender nao acrescentaria
# informacao -- por isso ela para ali.
GRADE_MIN_PARES = [None, 3, 5, 8, 10, 12, 15, 20]

# Criterio de decisao: maior IC no in-sample. Mecanico, sem desempate.
CRITERIO = "IC in-sample (2016-2020), maior vence"

CAMINHO_CONGELADO = os.path.join(SAIDA_DIR, "limiar_congelado.csv")


def rotulo(k):
    return "baseline (so setor)" if k is None else f"subsetor, min {k} pares"


# ==================================================================
# Calculo dos choques por limiar (com cache)
# ==================================================================

def choques_para_limiar(k, df_retornos, df_indices, df_map, tickers_alvo, recalcular=False):
    """
    Roda `calcular_choque_limpo` do Bloco 4 com o limiar `k`.

    Ajusta as globais do modulo do Bloco 4 em vez de reimplementar a
    regressao -- o teste tem que exercitar EXATAMENTE o codigo de producao,
    senao estaria validando outra coisa. O estado e restaurado ao final para
    nao contaminar chamadas seguintes no mesmo processo.
    """
    os.makedirs(SAIDA_DIR, exist_ok=True)
    sufixo = "setor" if k is None else f"k{k}"
    cache_ch = os.path.join(SAIDA_DIR, f"choques_{sufixo}.parquet")
    cache_bt = os.path.join(SAIDA_DIR, f"betas_{sufixo}.parquet")

    if not recalcular and os.path.exists(cache_ch) and os.path.exists(cache_bt):
        return pd.read_parquet(cache_ch), pd.read_parquet(cache_bt)

    usar_antes, min_antes = s4.USAR_SUBSETOR, s4.MIN_PARES_SUBSETOR
    try:
        s4.USAR_SUBSETOR = k is not None
        if k is not None:
            s4.MIN_PARES_SUBSETOR = k
        ch, bt = s4.calcular_choque_limpo(
            df_retornos, df_indices, df_map, tickers_alvo=tickers_alvo
        )
    finally:
        s4.USAR_SUBSETOR, s4.MIN_PARES_SUBSETOR = usar_antes, min_antes

    ch = ch.astype(float)
    bt = bt.astype(float)
    ch.to_parquet(cache_ch, engine="pyarrow")
    bt.to_parquet(cache_bt, engine="pyarrow")
    return ch, bt


# ==================================================================
# Metricas
# ==================================================================

def medir_ic(df_choques, df_grafo, df_retornos, mascara):
    df_sinal = s6.gerar_sinal(df_choques, df_grafo, JANELA_SINAL)
    ic, t, n = s6.calcular_ic(df_sinal, df_retornos, mascara)
    return {"ic": ic, "t_ic": t, "n_dias": n, "sinal": df_sinal}


def medir_desempenho(df_sinal, contexto, mascara, nome_periodo):
    """Pipeline completo (Bloco 5 -> 3) para o periodo pedido."""
    df_pesos = s6.gerar_pesos(
        df_sinal, contexto["retornos"], contexto["betas_variante"],
        contexto["adtv"], contexto["setores"], JANELA_PESOS,
    )
    liq, bruto, giro = s6.rodar_backtest(df_pesos, contexto["retornos"], contexto["ibov"])
    return s6.metricas_periodo(liq, bruto, giro, contexto["cdi"], mascara, nome_periodo)


def breadth(df_sinal, mascara):
    """Numero efetivo de apostas -- mesma conta da Etapa 2 do s12."""
    sinal = df_sinal.loc[mascara.reindex(df_sinal.index, fill_value=False)]
    sinal = sinal.replace(0.0, np.nan).dropna(axis=1, how="all")
    sinal = sinal.loc[:, sinal.std() > 1e-12]
    if sinal.shape[1] < 2:
        return np.nan, np.nan
    c = np.nan_to_num(sinal.corr().to_numpy(dtype=float), nan=0.0)
    np.fill_diagonal(c, 1.0)
    ev = np.linalg.eigvalsh(c)
    ev = ev[ev > 0]
    n_eff = float(ev.sum() ** 2 / (ev**2).sum())
    return sinal.shape[1], n_eff


# ==================================================================
# MAIN
# ==================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Escolhe o limiar de subsetor SO no in-sample, congela e mede o OOS uma vez."
    )
    parser.add_argument("--recalcular", action="store_true",
                        help="ignora o cache de choques por limiar")
    args = parser.parse_args()

    print("=" * 78)
    print(" BLOCO 6 -- CONTROLE POR SUBSETOR SOB O PROTOCOLO IS/OOS")
    print("=" * 78)
    print(f"\nGrade fixada: {[rotulo(k) for k in GRADE_MIN_PARES]}")
    print(f"Criterio    : {CRITERIO}")
    print(f"Corte       : IS ate {DATA_CORTE.date()}, OOS depois")

    contexto, df_grafo = s6.montar_contexto(verboso=True)
    df_retornos = contexto["retornos"]
    periodos = contexto["periodos"]

    # Os insumos crus do Bloco 4 (o contexto do s6 ja traz choques prontos,
    # mas aqui precisamos recalcula-los por limiar).
    df_ret4, df_indices, _, df_map = s4.carregar_dados()
    tickers_alvo = set(df_grafo["empresa_A"]) | set(df_grafo["empresa_B"])

    # ------------------------------------------------------------------
    # ETAPA 1 -- medir o IC no IN-SAMPLE para cada limiar
    # ------------------------------------------------------------------
    print("\n" + "=" * 78)
    print(" ETAPA 1 -- IC in-sample por limiar (2016-2020). SO ISTO DECIDE.")
    print("=" * 78)

    linhas, sinais, betas_por_k = [], {}, {}
    for k in GRADE_MIN_PARES:
        print(f"\n  calculando {rotulo(k)}...")
        ch, bt = choques_para_limiar(
            k, df_ret4, df_indices, df_map, tickers_alvo, recalcular=args.recalcular
        )
        r_is = medir_ic(ch, df_grafo, df_retornos, periodos["IS 16-20"])
        sinais[k] = r_is["sinal"]
        betas_por_k[k] = bt
        n_pos_is, n_eff_is = breadth(r_is["sinal"], periodos["IS 16-20"])
        linhas.append({
            "limiar": rotulo(k), "k": -1 if k is None else k,
            "ic_is": r_is["ic"], "t_ic_is": r_is["t_ic"],
            "posicoes_is": n_pos_is, "breadth_is": n_eff_is,
        })

    df_is = pd.DataFrame(linhas)

    print(f"\n{'limiar':<24}{'IC (IS)':>11}{'t(IC)':>9}{'posicoes':>11}{'breadth':>10}")
    print("-" * 65)
    for _, r in df_is.iterrows():
        print(f"{r['limiar']:<24}{r['ic_is']:>+11.4f}{r['t_ic_is']:>9.2f}"
              f"{r['posicoes_is']:>11.0f}{r['breadth_is']:>10.1f}")

    # ------------------------------------------------------------------
    # ETAPA 2 -- congelar
    # ------------------------------------------------------------------
    vencedor_idx = int(df_is["ic_is"].idxmax())
    k_vencedor = df_is.loc[vencedor_idx, "k"]
    k_vencedor = None if k_vencedor == -1 else int(k_vencedor)

    print("\n" + "=" * 78)
    print(" ETAPA 2 -- CONGELAMENTO")
    print("=" * 78)
    print(f"\nVencedor por {CRITERIO}:")
    print(f"  >>> {rotulo(k_vencedor).upper()} <<<")
    print(f"  IC in-sample = {df_is.loc[vencedor_idx, 'ic_is']:+.4f} "
          f"(t = {df_is.loc[vencedor_idx, 't_ic_is']:.2f})")

    os.makedirs(SAIDA_DIR, exist_ok=True)
    pd.DataFrame([{
        "criterio": CRITERIO,
        "grade": ";".join(rotulo(k) for k in GRADE_MIN_PARES),
        "vencedor": rotulo(k_vencedor),
        "k": -1 if k_vencedor is None else k_vencedor,
        "ic_is": df_is.loc[vencedor_idx, "ic_is"],
        "data_corte": str(DATA_CORTE.date()),
    }]).to_csv(CAMINHO_CONGELADO, index=False)
    df_is.to_csv(os.path.join(SAIDA_DIR, "ic_in_sample_por_limiar.csv"), index=False)
    print(f"\nCongelado em: {CAMINHO_CONGELADO}")

    if k_vencedor is None:
        print("\nO BASELINE VENCEU NO IN-SAMPLE.")
        print("A ideia do subsetor esta rejeitada pelo proprio protocolo, sem")
        print("precisar olhar o OOS. O OOS abaixo e so registro.")

    # ------------------------------------------------------------------
    # ETAPA 3 -- medir o OOS uma vez
    # ------------------------------------------------------------------
    print("\n" + "=" * 78)
    print(" ETAPA 3 -- MEDICAO OUT-OF-SAMPLE (2021-2025), UMA VEZ")
    print("=" * 78)

    def avaliar(k):
        df_sinal = sinais[k]
        contexto["betas_variante"] = betas_por_k[k]
        ic_oos, t_oos, _ = s6.calcular_ic(df_sinal, df_retornos, periodos["OOS 21-25"])
        m = medir_desempenho(df_sinal, contexto, periodos["OOS 21-25"], "OOS 21-25")
        n_pos, n_eff = breadth(df_sinal, periodos["OOS 21-25"])
        # `liquido_ano` e o alfa: o P&L long-short ja E excesso sobre o CDI
        # (ver o comentario em `metricas_periodo`).
        return {
            "limiar": rotulo(k), "ic_oos": ic_oos, "t_ic_oos": t_oos,
            "alfa_ano": m["liquido_ano"], "vol": m["vol_ano"], "sharpe": m["sharpe"],
            "giro_dia": m["giro_dia"], "breadth_oos": n_eff, "posicoes_oos": n_pos,
        }

    print(f"\n  avaliando o vencedor ({rotulo(k_vencedor)})...")
    resultado_vencedor = avaliar(k_vencedor)

    comparacao = [resultado_vencedor]
    if k_vencedor is not None:
        print(f"  avaliando o baseline, para referencia...")
        comparacao.insert(0, avaliar(None))

    df_oos = pd.DataFrame(comparacao)
    print(f"\n{'limiar':<24}{'IC (OOS)':>11}{'t':>7}{'alfa/ano':>11}"
          f"{'vol':>8}{'Sharpe':>9}{'breadth':>10}")
    print("-" * 80)
    for _, r in df_oos.iterrows():
        print(f"{r['limiar']:<24}{r['ic_oos']:>+11.4f}{r['t_ic_oos']:>7.2f}"
              f"{r['alfa_ano']:>+11.2%}{r['vol']:>8.2%}{r['sharpe']:>9.2f}"
              f"{r['breadth_oos']:>10.1f}")

    df_oos.to_csv(os.path.join(SAIDA_DIR, "resultado_oos_congelado.csv"), index=False)

    # ------------------------------------------------------------------
    # VEREDITO
    # ------------------------------------------------------------------
    print("\n" + "=" * 78)
    print(" VEREDITO")
    print("=" * 78)

    v = resultado_vencedor
    if k_vencedor is None:
        print("\nO in-sample escolheu o BASELINE. O controle por subsetor nao se")
        print("justifica nem antes de olhar o futuro -- a hipotese cai sem que o")
        print("OOS precise ser consultado, que e o desfecho mais limpo possivel.")
        print(f"\nProducao permanece como esta: alfa OOS {v['alfa_ano']:+.2%}/ano, "
              f"Sharpe {v['sharpe']:.2f}.")
    else:
        base = comparacao[0]
        d_sharpe = v["sharpe"] - base["sharpe"]
        d_breadth = v["breadth_oos"] - base["breadth_oos"]
        print(f"\nO in-sample escolheu {rotulo(k_vencedor)}. No OOS, contra o baseline:")
        print(f"  Sharpe   {base['sharpe']:>6.2f} -> {v['sharpe']:>6.2f}   ({d_sharpe:+.2f})")
        print(f"  alfa/ano {base['alfa_ano']:>6.2%} -> {v['alfa_ano']:>6.2%}")
        print(f"  breadth  {base['breadth_oos']:>6.1f} -> {v['breadth_oos']:>6.1f}   "
              f"({d_breadth:+.1f})")
        if d_sharpe > 0.05 and d_breadth > 1.0:
            print("\n  ADOTAR: melhora o retorno ajustado a risco E a breadth, com o")
            print("  limiar escolhido sem olhar o OOS. Ligar `USAR_SUBSETOR` no Bloco 4.")
        elif d_sharpe > 0.05:
            print("\n  RESULTADO MISTO: Sharpe melhora mas a breadth nao. Como a")
            print("  hipotese ERA sobre breadth, isso e mais provavel ser sorte de")
            print("  amostra que efeito real -- o mesmo padrao que fez P7 ser")
            print("  rejeitada. Nao adotar sem uma terceira amostra.")
        else:
            print("\n  NAO ADOTAR: o limiar escolhido honestamente no in-sample nao")
            print("  entrega ganho fora da amostra. A conclusao do teste anterior se")
            print("  mantem, agora sem a objecao de que 5 era um limiar mal escolhido.")

    print(f"\nArtefatos em: {SAIDA_DIR}")


if __name__ == "__main__":
    main()
