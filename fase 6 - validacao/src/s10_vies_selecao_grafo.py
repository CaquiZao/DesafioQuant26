"""
Bloco 10: medicao do vies de selecao do grafo (pendencia P2).

O PROBLEMA
----------
As 44 empresas do `grafo_manual_base.csv` foram escolhidas em 2025/2026 por
alguem que ja sabe quais existem hoje. Um analista sentado em 2016 teria
escrito elos com Kroton, Cielo, B2W, Hering, Estacio, Linx -- todas gigantes
na epoca, todas mortas hoje, nenhuma no grafo.

Isso e vies de sobrevivencia na SELECAO das relacoes, e e diferente do vies
de PRECO (resolvido em 03/08 com a base COTAHIST). Ter preco das empresas
mortas nao adianta nada se o grafo nunca aponta para elas.

O QUE ESTE SCRIPT MEDE
----------------------
1. Quantas empresas do grafo atual ja eram liquidas em 2016, e quantas
   sequer existiam (IPO posterior). Uma empresa que abriu capital em 2020
   nao poderia estar num grafo escrito em 2016 -- se ela esta no grafo hoje,
   e porque o autor sabia que ela viria a existir.

2. Quais empresas eram GRANDES no inicio do periodo (top do universo de
   liquidez) e morreram antes do fim -- as candidatas obvias que o grafo
   atual ignora.

3. O tamanho da lacuna: quanto do universo liquido de 2016 o grafo cobre,
   contra quanto do universo liquido de 2025 ele cobre. Se a cobertura de
   2025 for muito maior, o grafo esta "olhando para o presente".

Este script NAO corrige nada. Ele quantifica o problema para que a correcao
(grafo point-in-time) possa ser medida contra uma linha de base.

USO
---
    python "fase 6 - validacao/src/s10_vies_selecao_grafo.py"
"""

import os

import pandas as pd

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_DIR = os.path.join(BASE_DIR, "data")
SAIDA_DIR = os.path.join(DATA_DIR, "validacao")

CAMINHO_UNIVERSO = os.path.join(DATA_DIR, "universo", "universo_mensal.parquet")
CAMINHO_GRAFO = os.path.join(BASE_DIR, "fase 4 - sinal da sinapse", "grafo_manual_base.csv")
# O grafo historico e a CORRECAO da P2. Este script tem que medir o grafo
# efetivo (os dois arquivos juntos), senao continuaria reportando o vies de
# antes da correcao.
CAMINHO_GRAFO_HIST = os.path.join(BASE_DIR, "fase 4 - sinal da sinapse", "grafo_historico.csv")

# Um ticker e considerado "liquido no periodo" se apareceu no universo do
# Bloco 2 em pelo menos este numero de meses dentro da janela analisada.
MIN_MESES_PARA_LIQUIDO = 6

# Corte de "empresa grande": posicao no ranking mensal de volume do Bloco 2.
# O universo tem ~100 nomes por mes, entao top 60 e uma definicao generosa
# de "estava no radar de qualquer analista".
RANK_GRANDE = 60


def carregar():
    universo = pd.read_parquet(CAMINHO_UNIVERSO)
    grafo = pd.read_csv(CAMINHO_GRAFO)
    if os.path.exists(CAMINHO_GRAFO_HIST):
        grafo = pd.concat([grafo, pd.read_csv(CAMINHO_GRAFO_HIST)], ignore_index=True)
    return universo, grafo


def classificar_vida(universo):
    """
    Para cada ticker do universo, quando ele entrou e quando saiu.

    `saiu_antes_do_fim` = o ticker deixou de aparecer no universo antes do
    ultimo mes coberto. Isso captura tanto delistagem quanto perda de
    liquidez -- os dois casos em que um elo escrito no passado deixaria de
    valer.
    """
    ultimo_mes_global = universo["mes"].max()
    primeiro_mes_global = universo["mes"].min()

    agrupado = universo.groupby("ticker")["mes"]
    vida = pd.DataFrame({
        "primeiro_mes": agrupado.min(),
        "ultimo_mes": agrupado.max(),
        "n_meses": agrupado.count(),
    })
    vida["existia_no_inicio"] = vida["primeiro_mes"] <= primeiro_mes_global
    vida["saiu_antes_do_fim"] = vida["ultimo_mes"] < ultimo_mes_global
    return vida, primeiro_mes_global, ultimo_mes_global


def empresas_liquidas_em(universo, ano_inicio, ano_fim, min_meses=MIN_MESES_PARA_LIQUIDO):
    janela = universo[
        (universo["mes"] >= f"{ano_inicio}-01") & (universo["mes"] <= f"{ano_fim}-12")
    ]
    contagem = janela.groupby("ticker")["mes"].count()
    return set(contagem[contagem >= min_meses].index)


def main():
    print("=" * 72)
    print(" BLOCO 10 -- VIES DE SELECAO DO GRAFO (pendencia P2)")
    print("=" * 72)

    universo, grafo = carregar()
    vida, primeiro_mes, ultimo_mes = classificar_vida(universo)

    empresas_grafo = sorted(set(grafo["empresa_A"]) | set(grafo["empresa_B"]))
    print(f"\nPeriodo do universo: {primeiro_mes} a {ultimo_mes}")
    print(f"Empresas no grafo atual: {len(empresas_grafo)}")

    # ---------- 1. As empresas do grafo existiam em 2016? ----------
    print("\n" + "=" * 72)
    print(" 1. O GRAFO PODERIA TER SIDO ESCRITO EM 2016?")
    print("=" * 72)

    liquidas_2016 = empresas_liquidas_em(universo, 2016, 2016)
    nao_existiam = []
    for t in empresas_grafo:
        if t not in vida.index:
            nao_existiam.append((t, "nunca no universo"))
        elif t not in liquidas_2016:
            primeiro = vida.loc[t, "primeiro_mes"]
            nao_existiam.append((t, f"entrou em {primeiro}"))

    print(f"\nEmpresas do grafo que NAO eram liquidas em 2016: "
          f"{len(nao_existiam)} de {len(empresas_grafo)}")
    for t, motivo in nao_existiam:
        print(f"  {t:<8} {motivo}")

    print(f"\n  -> {len(nao_existiam)/len(empresas_grafo):.0%} do grafo depende de "
          "empresas que um analista em 2016 nao conhecia.")
    print("     Cada uma dessas so entrou porque o autor sabia que existiria.")

    # ---------- 2. Quem era grande em 2016 e morreu? ----------
    print("\n" + "=" * 72)
    print(" 2. AS GRANDES DE 2016 QUE MORRERAM (e que o grafo ignora)")
    print("=" * 72)

    inicio = universo[universo["mes"] <= "2016-12"]
    grandes_2016 = set(inicio[inicio["rank"] <= RANK_GRANDE]["ticker"].unique())

    mortas = []
    for t in sorted(grandes_2016):
        if t not in vida.index:
            continue
        if vida.loc[t, "saiu_antes_do_fim"]:
            mortas.append({
                "ticker": t,
                "ultimo_mes": vida.loc[t, "ultimo_mes"],
                "meses_vivo": int(vida.loc[t, "n_meses"]),
                "no_grafo": t in empresas_grafo,
            })

    df_mortas = pd.DataFrame(mortas).sort_values("ultimo_mes")
    print(f"\nEmpresas top-{RANK_GRANDE} em 2016 que sairam do universo antes de "
          f"{ultimo_mes}: {len(df_mortas)}")
    print(f"Dessas, quantas estao no grafo atual: "
          f"{int(df_mortas['no_grafo'].sum())}")
    print()
    print(df_mortas.to_string(index=False))

    # ---------- 3. Cobertura: o grafo olha para o presente? ----------
    print("\n" + "=" * 72)
    print(" 3. O GRAFO OLHA PARA O PRESENTE?")
    print("=" * 72)

    liq_inicio = empresas_liquidas_em(universo, 2016, 2018)
    liq_fim = empresas_liquidas_em(universo, 2023, 2025)

    cob_inicio = len(set(empresas_grafo) & liq_inicio) / max(len(liq_inicio), 1)
    cob_fim = len(set(empresas_grafo) & liq_fim) / max(len(liq_fim), 1)

    print(f"\nCobertura do grafo sobre o universo liquido:")
    print(f"  2016-2018: {len(set(empresas_grafo) & liq_inicio):>3} de "
          f"{len(liq_inicio):>3} acoes = {cob_inicio:.1%}")
    print(f"  2023-2025: {len(set(empresas_grafo) & liq_fim):>3} de "
          f"{len(liq_fim):>3} acoes = {cob_fim:.1%}")

    if cob_fim > cob_inicio * 1.3:
        print(f"\n  -> O grafo cobre {cob_fim/cob_inicio:.1f}x mais do universo RECENTE.")
        print("     Confirmacao quantitativa do vies: ele foi escrito olhando")
        print("     a bolsa de hoje, nao a bolsa do inicio do periodo.")
    else:
        print("\n  -> Cobertura parecida nos dois extremos.")

    os.makedirs(SAIDA_DIR, exist_ok=True)
    df_mortas.to_csv(os.path.join(SAIDA_DIR, "grandes_mortas_2016.csv"), index=False)
    print(f"\nLista salva em: {os.path.join(SAIDA_DIR, 'grandes_mortas_2016.csv')}")


if __name__ == "__main__":
    main()
