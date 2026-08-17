"""
Bloco 4d: gerador MECANICO do grafo -- ensemble A3 (lider composto).

POR QUE ESTE SCRIPT EXISTE
--------------------------
O grafo manual de 58 elos funciona, mas tem tres limitacoes que nenhuma
quantidade de trabalho resolve: nao e point-in-time (foi escrito em 2026 por
quem conhece o periodo), nao se atualiza sozinho, e expandi-lo a mao
reintroduz julgamento a cada linha.

Este script substitui o grafo por uma REGRA, reconstruida todo mes a partir
de dado observavel:

    Para cada SUBSETOR, a cada mes:
      1. ordena os membros por ADTV dos 21 pregoes ANTERIORES (point-in-time)
      2. deduplica por raiz de ticker (PETR3/PETR4 = uma empresa so)
      3. os K primeiros formam a CABECA
      4. gera elo de cada nome da CABECA para TODOS os membros do ramo,
         ex-self -- INCLUSIVE para as outras cabecas
      5. forca conforme a variante, direcao = +1

A PECA CENTRAL E O PASSO 4
--------------------------
A primeira versao desta regra proibia o lider de ser satelite: cada ramo
tinha um gatilho unico que so mandava sinal, nunca recebia. Ela entregava
Sharpe 0,33 contra 0,65 do grafo manual, e a conclusao natural era que a
curadoria humana era insubstituivel.

Estava errado. Com `alvo = todos`, formam-se elos MUTUOS entre os nomes mais
liquidos de cada ramo -- VALE3<->CSNA3, PETR3<->PETR4, SUZB3<->KLBN11. Que e
exatamente a topologia que o time escreveu a mao.

Verificado: esta regra reproduz **100% dos 40 elos same-subsetor** do grafo
manual, todos tambem na direcao inversa.

    O time nao descobriu pares. Descobriu uma topologia -- cabeca liquida do
    ramo, ligada mutuamente. E isso e mecanizavel.

POR QUE ENSEMBLE, E NAO A MELHOR VARIANTE
-----------------------------------------
As 6 variantes (K x peso) entram TODAS. Nenhuma e escolhida por desempenho.
Isso e o que torna a configuracao defensavel -- e ha evidencia direta de que
escolher e perigoso: nos testes de similaridade fatorial, o criterio de
escolha no in-sample elegeu o PIOR membro out-of-sample, duas vezes seguidas.
Cinco anos de IC nao tem poder para selecionar parametro aqui.

DUPLA LISTAGEM
--------------
ON e PN da mesma empresa sao deduplicadas na cabeca. Um elo PETR3->PETR4 nao
e propagacao economica, e arbitragem de classe -- capturar isso inflaria o
resultado sem relacao com a tese. Permitir daria Sharpe 0,548 contra 0,496;
proibimos mesmo custando desempenho, porque a alternativa nao e defensavel.

USO
---
    python "fase 4 - sinal da sinapse/src/s4d_grafo_regra.py"

Saida: data/grafo_regra_mensal.parquet
"""

import os
import re

import numpy as np
import pandas as pd

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_DIR = os.path.join(BASE_DIR, "data")

CAMINHO_ADTV = os.path.join(DATA_DIR, "universo", "adtv_diario.parquet")
CAMINHO_MAPA = os.path.join(BASE_DIR, "fase 4 - sinal da sinapse", "mapeamento_setores.csv")
CAMINHO_SAIDA = os.path.join(DATA_DIR, "grafo_regra_mensal.parquet")

# ------------------------------------------------------------------
# A CONFIGURACAO CONGELADA -- nao alterar sem refazer a validacao
# ------------------------------------------------------------------

# As 6 variantes do ensemble. Nenhuma escolhida por desempenho.
K_CABECA = (2, 3, 5)
PESOS_CABECA = ("igual", "adtv")

# Minimo de membros para um subsetor gerar elos. Abaixo disso a "cabeca" seria
# quase o ramo inteiro e o elo nao carrega informacao de lideranca.
MIN_MEMBROS_SUBSETOR = 4

# ADTV minimo para um ticker ser elegivel num mes. Abaixo disso ele nao
# negocia o suficiente para o preco significar alguma coisa.
ADTV_MINIMO = 100_000.0

# ------------------------------------------------------------------
# D1 -- teto de satelites por subsetor (decidido 16/08, so no in-sample)
# ------------------------------------------------------------------
# Com `alvo = todos ex-self`, TODO nao-lider de um subsetor recebe a mesma
# soma de choques das cabecas. Medido: correlacao media de +0,884 entre
# satelites do mesmo ramo (238 pares acima de 0,99). O sinal tem ~23
# dimensoes independentes (uma por subsetor), nao 174 -- segurar 15 nomes
# identicos expressa UMA aposta com o custo de quinze.
#
# Grade pre-especificada {3, 5, 8, 12, sem teto}, criterio Sharpe liquido
# in-sample com custo tiered. Resultado MONOTONICO na grade inteira:
#     teto 3 -> SR IS +0,263 | 5 -> +0,239 | 8 -> +0,163 | 12 -> +0,137
#     sem teto -> +0,123
#
# RESSALVA QUE PRECISA SER DECLARADA: o racional a priori ("cortar
# redundancia economiza custo") esta ERRADO. Medido, giro e custo sao
# invariantes ao teto (5,32% vs 5,29% de giro; 4,76% vs 4,80% de custo),
# porque o vol-targeting fixa o orcamento de risco -- cortar nomes
# redistribui o mesmo risco, nao o reduz. O ganho in-sample veio do RETORNO
# BRUTO (+6,59% vs +5,64%) e da breadth (17,0 vs 11,4).
#
# Ou seja: e uma decisao de ALFA disfarcada de decisao de capacidade.
#
# DECISAO FINAL: NAO ADOTADO (None).
#
# O ganho in-sample nao replicou: SR OOS -0,150 com teto contra -0,051 sem.
# Mais importante que isso, a grade OOS completa (5 tetos x 3 neutralizacoes)
# nao tem NENHUMA celula com Sharpe liquido positivo -- exceto exatamente a
# que os dois criterios in-sample rejeitaram por larga margem (beta+setor:
# SR IS -0,87, SR OOS +0,48 a +0,58). Inversao de sinal IS->OOS de manual.
#
# A leitura correta nao e "o teto de 3 e ruim", e "o in-sample deste projeto
# NAO SELECIONA". E se o criterio nao seleciona, adicionar um parametro
# escolhido por ele destroi o ativo principal desta configuracao: ter ZERO
# parametros escolhidos por desempenho.
#
# Por isso D1 fica registrado como TESTE FEITO E REPORTADO, nao como escolha
# adotada. `None` = sem teto, que e a versao sem parametro livre.
MAX_SATELITES_SUBSETOR = None

MARCADOR_VAZIO = "A DEFINIR"


def raiz_ticker(ticker):
    """
    PETR3, PETR4 -> PETR    |    KLBN11 -> KLBN    |    IGTI11 -> IGTI

    Deduplicar por raiz impede que ON e PN da mesma empresa virem um elo. Nao
    e heuristica frouxa: na B3 o codigo e sempre 4 letras + digito(s) de
    classe.
    """
    return re.sub(r"\d+$", "", str(ticker))


def carregar_insumos():
    if not os.path.exists(CAMINHO_ADTV):
        raise FileNotFoundError(
            f"{CAMINHO_ADTV} nao encontrado -- rode o Bloco 2 (s2_universo.py) antes.")

    df_adtv = pd.read_parquet(CAMINHO_ADTV)
    df_map = pd.read_csv(CAMINHO_MAPA, encoding="utf-8")

    if "Subsetor" not in df_map.columns:
        raise ValueError(
            "mapeamento_setores.csv sem a coluna 'Subsetor' -- rode "
            "'src/s4c_subsetores.py' antes.")

    sub = {t: s for t, s in zip(df_map["Ticker"], df_map["Subsetor"])
           if isinstance(s, str) and s != MARCADOR_VAZIO}
    return df_adtv, sub


def gerar_grafo_mensal(df_adtv, ticker_to_sub):
    """
    Devolve um DataFrame longo: mes_vigencia, variante, empresa_A, empresa_B,
    forca, direcao.

    `mes_vigencia` e o mes em que o grafo VALE. O ADTV usado e o do ultimo
    pregao do mes ANTERIOR -- por isso o `shift(1)` no resample. Sem ele, o
    grafo de janeiro usaria liquidez de janeiro, o que e look-ahead dentro do
    proprio mes.
    """
    # ADTV no ultimo pregao de cada mes, deslocado: o grafo do mes M usa o
    # ADTV observado ate o fim de M-1.
    adtv_mensal = df_adtv.resample("ME").last().shift(1)

    linhas = []
    for mes, serie in adtv_mensal.iterrows():
        v = serie.dropna()
        v = v[v >= ADTV_MINIMO]
        if v.empty:
            continue

        # agrupa por subsetor
        por_sub = {}
        for ticker, adtv in v.items():
            s = ticker_to_sub.get(ticker)
            if s is not None:
                por_sub.setdefault(s, []).append((ticker, float(adtv)))

        for _, membros in por_sub.items():
            if len(membros) < MIN_MEMBROS_SUBSETOR:
                continue
            membros.sort(key=lambda x: -x[1])
            todos = [t for t, _ in membros]

            for K in K_CABECA:
                # cabeca com deduplicacao por raiz: percorre em ordem de
                # liquidez e pula quem repete empresa
                cabeca, raizes = [], set()
                for t, a in membros:
                    r = raiz_ticker(t)
                    if r in raizes:
                        continue
                    raizes.add(r)
                    cabeca.append((t, a))
                    if len(cabeca) == K:
                        break
                if len(cabeca) < 2:
                    continue

                # D1: alvos = as cabecas + os MAX_SATELITES mais liquidos entre
                # os demais. Os nao-lideres excedentes teriam sinal IDENTICO
                # aos que ficam -- nao acrescentam aposta, so posicao.
                nomes_cabeca = {t for t, _ in cabeca}
                satelites = [t for t in todos if t not in nomes_cabeca]
                if MAX_SATELITES_SUBSETOR is not None:
                    satelites = satelites[:MAX_SATELITES_SUBSETOR]   # ja ordenado por ADTV
                # ORDEM DETERMINISTICA: `list(set)` segue o PYTHONHASHSEED, que
                # e aleatorizado por processo -- 26% das linhas saiam em ordem
                # diferente a cada execucao. Hoje e inofensivo (a propagacao usa
                # `np.add.at`, que e comutativo, e o sinal sai bit-a-bit igual),
                # mas basta um `drop_duplicates` ou `groupby(sort=False)` a
                # jusante para o resultado passar a oscilar sem motivo.
                elegiveis = [t for t, _ in cabeca] + satelites

                soma_adtv = sum(a for _, a in cabeca)
                for peso in PESOS_CABECA:
                    variante = f"K{K}_{peso}"
                    for t_h, a_h in cabeca:
                        f = (1.0 / len(cabeca)) if peso == "igual" else (a_h / soma_adtv)
                        raiz_h = raiz_ticker(t_h)
                        for alvo in elegiveis:
                            # ex-self E ex-mesma-empresa: PETR3 nao informa PETR4
                            if raiz_ticker(alvo) == raiz_h:
                                continue
                            linhas.append((mes, variante, t_h, alvo, f, 1))

    return pd.DataFrame(
        linhas,
        columns=["mes_vigencia", "variante", "empresa_A", "empresa_B", "forca", "direcao"],
    )


def main():
    print("=" * 78)
    print(" BLOCO 4d -- GRAFO MECANICO (ensemble A3, lider composto)")
    print("=" * 78)

    df_adtv, ticker_to_sub = carregar_insumos()
    print(f"\nADTV: {df_adtv.shape[0]} pregoes x {df_adtv.shape[1]} tickers")
    print(f"Subsetores mapeados: {len(set(ticker_to_sub.values()))} "
          f"({len(ticker_to_sub)} tickers)")
    print(f"Variantes do ensemble: {len(K_CABECA) * len(PESOS_CABECA)} "
          f"(K {list(K_CABECA)} x peso {list(PESOS_CABECA)})")

    df_grafo = gerar_grafo_mensal(df_adtv, ticker_to_sub)
    if df_grafo.empty:
        raise RuntimeError("nenhum elo gerado -- confira ADTV e mapa de subsetores")

    os.makedirs(DATA_DIR, exist_ok=True)
    df_grafo.to_parquet(CAMINHO_SAIDA, engine="pyarrow")

    meses = df_grafo["mes_vigencia"].nunique()
    pares = df_grafo.groupby(["empresa_A", "empresa_B"]).ngroups
    print(f"\nElos gerados : {len(df_grafo):,} linhas (elo x mes x variante)")
    print(f"Meses        : {meses}")
    print(f"Pares unicos : {pares:,}")

    print(f"\n{'variante':<12}{'elos/mes':>10}{'gatilhos':>10}{'satelites':>11}")
    print("-" * 43)
    for var, g in df_grafo.groupby("variante"):
        print(f"{var:<12}{len(g)/meses:>10.0f}{g.empresa_A.nunique():>10}"
              f"{g.empresa_B.nunique():>11}")

    # Diagnostico temporal: a regra tem que gerar elos nos anos iniciais
    print(f"\n{'ano':<8}{'elos/mes':>10}{'nomes':>8}")
    print("-" * 26)
    por_ano = df_grafo.groupby(df_grafo["mes_vigencia"].dt.year)
    for ano, g in por_ano:
        n_meses = g["mes_vigencia"].nunique()
        nomes = len(set(g.empresa_A) | set(g.empresa_B))
        print(f"{ano:<8}{len(g)/n_meses:>10.0f}{nomes:>8}")

    print(f"\nSalvo em: {CAMINHO_SAIDA}")


if __name__ == "__main__":
    main()
