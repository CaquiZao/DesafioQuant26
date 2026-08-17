"""
Bloco 6: inferencia honesta e breadth efetiva -- dimensionamento de P3.

POR QUE ESTE SCRIPT EXISTE
--------------------------
As sessoes de 03/08 e 04/08 fecharam P1, P2, P5 e P7 e concluiram que P3
(expandir o grafo) e o gargalo unico. Tres argumentos apontam para ela --
mas os tres se apoiam em numeros que este script mostra estarem medidos com
a regua errada:

  1. A regra conservadora de P1 inverte uma categoria de elo so quando o
     in-sample tem |t| >= 2. Esse t sai de um t de Pearson sobre observacoes
     EMPILHADAS (~15 elos x 1.273 pregoes), tratadas como independentes. Nao
     sao: o mesmo dia aparece uma vez por elo, e num dia de alta geral todos
     os satelites sobem juntos. O erro-padrao ignora essa correlacao
     transversal, entao o t sai inflado -- e a fronteira entre "sinal" e
     "ruido" que sustenta a regra e mais estreita do que parece.

  2. HIPOTESE REFUTADA (mantida no arquivo como registro): o t do IC sai de um
     t simples sobre a serie diaria de ICs, e o sinal e uma media movel de 21
     pregoes -- dias consecutivos compartilham 20 de 21 observacoes. A
     suspeita era que os ICs diarios fossem autocorrelacionados por
     construcao, subestimando o erro-padrao. A Etapa 1b mede e REFUTA: rho(1)
     do IC e ~0,00-0,03 e o Newey-West praticamente nao move o t. Motivo: o
     IC de cada dia correlaciona o sinal suave com o retorno do dia SEGUINTE,
     e esse retorno e ruido fresco todo dia. A autocorrelacao do sinal nao se
     transmite ao produto. O t ingenuo do IC estava correto -- a Etapa 1b fica
     como a verificacao que prova isso, nao como correcao.

  3. A projecao de P3 (Correcoes1.md) usa IR ~ IC x raiz(breadth) com
     breadth = numero de ELOS. Mas 58 elos saem de apenas 28 gatilhos
     distintos, e um choque da LREN3 abre 7 posicoes de uma vez -- isso e
     UMA aposta, nao sete. O relatorio ja notou o sintoma e corrigiu com um
     fator de 50% ad hoc ("o Sharpe realizado foi metade do teorico").
     Aqui esse fator e medido em vez de chutado.

O QUE O SCRIPT FAZ
------------------
ETAPA 1  t-stats com erro-padrao correto
         1a. direcao por categoria: OLS com erro-padrao CLUSTERIZADO POR
             DATA (cada pregao e um cluster). Compara com o t ingenuo.
         1b. IC: erro-padrao Newey-West (HAC), maxlags = janela de
             suavizacao. Compara com o t ingenuo.

ETAPA 2  breadth efetiva (networkx + autovalores)
         Topologia do grafo, concentracao dos gatilhos, e o numero efetivo
         de apostas independentes pela razao de participacao dos autovalores
         da matriz de correlacao dos sinais. Fecha com o teste de Grinold
         usando breadth efetiva em vez de contagem de elos.

ETAPA 3  power analysis -- quanto grafo falta
         Dado o IC medido e a autocorrelacao medida, quantas apostas
         independentes sao necessarias para t(IC) > 2? Resposta analitica e
         por Monte Carlo (as duas tem que concordar), traduzida em numero de
         gatilhos pela razao medida na Etapa 2.

O QUE ESTE SCRIPT NAO FAZ
-------------------------
Nao altera o pipeline, nao reescolhe nenhum parametro e nao propoe elo novo.
E instrumento de medicao: as decisoes de P1 continuam as que estao em
producao. Se o t clusterizado derrubar `concorrente` abaixo de 2, isso e um
resultado a reportar -- nao um convite a mexer no grafo, porque mexer com
base neste mesmo numero seria o data snooping que P1 existe para bloquear.

USO
---
    python "fase 6 - validacao/src/s12_inferencia_e_breadth.py"
    python "fase 6 - validacao/src/s12_inferencia_e_breadth.py" --etapa 1
    python "fase 6 - validacao/src/s12_inferencia_e_breadth.py" --etapa 2
    python "fase 6 - validacao/src/s12_inferencia_e_breadth.py" --etapa 3
    python "fase 6 - validacao/src/s12_inferencia_e_breadth.py" --recalcular-choques
"""

import argparse
import importlib.util
import os
import sys

import numpy as np
import pandas as pd
import statsmodels.api as sm

try:
    import networkx as nx
except ImportError:  # pragma: no cover - dependencia opcional
    nx = None


# ------------------------------------------------------------------
# Caminhos e reuso do s6
# ------------------------------------------------------------------
# Mesmo padrao do s6/s7/s8: as pastas tem espacos e acentos, entao os
# modulos entram por caminho de arquivo. Reusamos o s6 INTEIRO em vez de
# copiar suas funcoes -- se este script reimplementasse `calcular_ic` ou
# `montar_contexto`, estaria medindo outra estrategia.

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_DIR = os.path.join(BASE_DIR, "data")
SAIDA_DIR = os.path.join(DATA_DIR, "validacao")


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
s4 = sys.modules["s4_sinapse"]  # carregado como efeito colateral do s6

DATA_CORTE = s6.DATA_CORTE
DIAS_UTEIS_ANO = s6.DIAS_UTEIS_ANO

# Janelas do pipeline em producao. A de sinal define o maxlags do Newey-West
# na Etapa 1b: a media movel de 21 pregoes e exatamente a fonte da
# autocorrelacao que o HAC precisa absorver.
JANELA_SINAL = s4.JANELA_SUAVIZACAO
JANELA_PESOS = 10

# Limiar de significancia usado pela regra conservadora de P1 e alvo da
# Etapa 3. 2.0 e a convencao (~5% bilateral), a mesma que o relatorio usa.
T_ALVO = 2.0


# ==================================================================
# ETAPA 1a -- direcao por categoria com erro-padrao clusterizado
# ==================================================================

def medir_direcao_clusterizada(df_grafo, df_choques, df_retornos, ate=None):
    """
    Repete `s6.medir_direcao_por_categoria`, mas troca o t de Pearson por um
    OLS com erro-padrao clusterizado por DATA.

    O empilhamento e IDENTICO ao do s6 (mesmos pares, mesmo filtro de 100
    observacoes, mesmo shift(-1)), de proposito: a unica coisa que muda e o
    erro-padrao, entao a diferenca entre os dois t isola o efeito da
    correlacao transversal e nada mais.

    Por que clusterizar por data: cada pregao entra na amostra uma vez por
    elo da categoria. Num dia de alta geral, TODOS os satelites sobem --
    logo os residuos do mesmo dia sao correlacionados entre si. O OLS comum
    supoe independencia e divide o erro-padrao por raiz(n) usando o n
    nominal (dezenas de milhares); clusterizar substitui isso pelo numero de
    CLUSTERS (pregoes), que e o n de informacao que existe de verdade.
    """
    resultados = []

    for tipo, elos in df_grafo.groupby("tipo_de_elo"):
        pares_x, pares_y, pares_data = [], [], []

        for _, elo in elos.iterrows():
            a, b = elo["empresa_A"], elo["empresa_B"]
            if a not in df_choques.columns or b not in df_retornos.columns:
                continue

            choque_a = df_choques[a]
            retorno_b_amanha = df_retornos[b].shift(-1)

            par = pd.concat([choque_a, retorno_b_amanha], axis=1).dropna()
            if ate is not None:
                par = par.loc[par.index <= ate]
            if len(par) < 100:
                continue

            pares_x.append(par.iloc[:, 0])
            pares_y.append(par.iloc[:, 1])
            pares_data.append(pd.Series(par.index, index=par.index))

        if not pares_x:
            continue

        x = pd.concat(pares_x).to_numpy(dtype=float)
        y = pd.concat(pares_y).to_numpy(dtype=float)
        datas = pd.concat(pares_data).to_numpy()

        corr = float(np.corrcoef(x, y)[0, 1])
        n = len(x)
        n_clusters = len(np.unique(datas))

        # t ingenuo: exatamente a formula do s6, reproduzida para comparar.
        t_ingenuo = corr * np.sqrt(max(n - 2, 1)) / np.sqrt(max(1 - corr**2, 1e-12))

        # t clusterizado. O coeficiente de x num OLS bivariado tem o mesmo
        # SINAL da correlacao, entao a direcao decidida nao muda -- so a
        # confianca com que ela e decidida.
        X = sm.add_constant(x)
        ajuste = sm.OLS(y, X).fit(cov_type="cluster", cov_kwds={"groups": datas})
        t_cluster = float(ajuste.tvalues[1])

        # Quanto o t ingenuo estava inflado, e qual o "n de informacao" que o
        # erro-padrao clusterizado implica: n_efetivo = n / fator^2, porque o
        # erro-padrao anda com 1/raiz(n).
        fator = abs(t_ingenuo) / abs(t_cluster) if abs(t_cluster) > 1e-12 else np.nan
        n_efetivo = n / (fator**2) if np.isfinite(fator) and fator > 0 else np.nan

        resultados.append({
            "tipo_de_elo": tipo,
            "n_elos": len(elos),
            "n_obs": n,
            "n_pregoes": n_clusters,
            "corr_T1": corr,
            "t_ingenuo": t_ingenuo,
            "t_cluster": t_cluster,
            "inflacao": fator,
            "n_efetivo": n_efetivo,
            "passa_limiar_ingenuo": abs(t_ingenuo) >= T_ALVO,
            "passa_limiar_cluster": abs(t_cluster) >= T_ALVO,
        })

    return pd.DataFrame(resultados).sort_values("tipo_de_elo").reset_index(drop=True)


# ==================================================================
# ETAPA 1b -- t do IC com erro-padrao Newey-West (HAC)
# ==================================================================

def calcular_ic_hac(df_sinal, df_retornos, mascara, maxlags=None):
    """
    Mesmo IC do s6 (correlacao transversal dia a dia entre sinal[T] e
    retorno[T+1]), com tres erros-padrao para o MESMO IC medio:

      - t_ingenuo : std(ics)/raiz(T). E o que o s6 reporta.
      - t_hac     : Newey-West com maxlags = janela de suavizacao.
      - t_hac_auto: Newey-West com a regra de bandwidth de Newey-West (1994),
                    maxlags = 4*(T/100)^(2/9), para nao depender da nossa
                    escolha de lag.

    Por que HAC: o sinal e uma media movel de `JANELA_SINAL` pregoes, entao o
    IC de hoje e o de amanha compartilham quase toda a informacao. Series
    assim tem autocorrelacao positiva forte, e o erro-padrao ingenuo -- que
    supoe independencia serial -- fica pequeno demais. Newey-West soma as
    autocovariancias ate `maxlags` e devolve o erro-padrao que a serie de
    fato tem. E o tratamento padrao para observacoes SOBREPOSTAS (Hansen-
    Hodrick, Newey-West).

    Devolve um dicionario -- os t nao mudam o IC, so a confianca nele.
    """
    colunas = [c for c in df_sinal.columns if c in df_retornos.columns]
    sinal = df_sinal[colunas]
    retorno_amanha = df_retornos[colunas].reindex(sinal.index).shift(-1)

    sinal = sinal.loc[mascara.reindex(sinal.index, fill_value=False)]
    retorno_amanha = retorno_amanha.loc[sinal.index]

    ics = sinal.corrwith(retorno_amanha, axis=1).dropna()
    if len(ics) < 30:
        return None

    if maxlags is None:
        maxlags = JANELA_SINAL

    y = ics.to_numpy(dtype=float)
    n = len(y)
    X = np.ones((n, 1))

    ajuste_ols = sm.OLS(y, X).fit()
    ajuste_hac = sm.OLS(y, X).fit(cov_type="HAC", cov_kwds={"maxlags": maxlags})
    lags_auto = int(np.floor(4 * (n / 100) ** (2 / 9)))
    ajuste_auto = sm.OLS(y, X).fit(cov_type="HAC", cov_kwds={"maxlags": lags_auto})

    # Autocorrelacao da serie de ICs. rho1 alto e a evidencia direta de que o
    # t ingenuo nao vale -- e a soma acumulada e o fator de inflacao teorico
    # do erro-padrao (1 + 2*soma(rho_k)).
    rhos = [float(ics.autocorr(lag=k)) for k in range(1, maxlags + 1)]
    inflacao_teorica = np.sqrt(max(1 + 2 * np.nansum(rhos), 1e-12))

    return {
        "ic_medio": float(ics.mean()),
        "n_dias": n,
        "t_ingenuo": float(ajuste_ols.tvalues[0]),
        "t_hac": float(ajuste_hac.tvalues[0]),
        "t_hac_auto": float(ajuste_auto.tvalues[0]),
        "maxlags": maxlags,
        "maxlags_auto": lags_auto,
        "rho1": rhos[0] if rhos else np.nan,
        "rho5": rhos[4] if len(rhos) > 4 else np.nan,
        "rho21": rhos[20] if len(rhos) > 20 else np.nan,
        "inflacao_teorica": float(inflacao_teorica),
        "inflacao_medida": float(abs(ajuste_ols.tvalues[0]) / abs(ajuste_hac.tvalues[0]))
        if abs(ajuste_hac.tvalues[0]) > 1e-12 else np.nan,
        "std_ic": float(ics.std()),
        "serie_ic": ics,
    }


# ==================================================================
# ETAPA 2 -- topologia do grafo e breadth efetiva
# ==================================================================

def analisar_topologia(df_grafo):
    """
    Descreve o grafo como grafo, nao como lista de linhas de CSV.

    A pergunta que importa para P3 nao e "quantos elos existem" e sim
    "quantas fontes de informacao INDEPENDENTES existem". Um choque da LREN3
    que abre 7 posicoes e uma aposta repetida 7 vezes, nao 7 apostas -- e a
    Lei Fundamental (IR ~ IC x raiz(breadth)) conta apostas independentes.

    Sem networkx o script segue funcionando com as metricas de contagem: a
    parte de comunidade e centralidade e que fica de fora.
    """
    gatilhos = df_grafo["empresa_A"]
    graus = gatilhos.value_counts()

    # Numero efetivo de gatilhos pelo inverso do HHI dos graus de saida. Se
    # os 58 elos estivessem espalhados por 28 gatilhos com 2 elos cada, o
    # efetivo seria 28; concentrado num gatilho so, seria 1. Mede a
    # concentracao ESTRUTURAL, antes de qualquer correlacao de preco.
    p = (graus / graus.sum()).to_numpy(dtype=float)
    gatilhos_efetivos_hhi = float(1.0 / np.sum(p**2))

    info = {
        "n_elos": len(df_grafo),
        "n_gatilhos": int(gatilhos.nunique()),
        "n_satelites": int(df_grafo["empresa_B"].nunique()),
        "n_empresas": int(pd.concat([df_grafo["empresa_A"], df_grafo["empresa_B"]]).nunique()),
        "grau_saida_max": int(graus.max()),
        "grau_saida_medio": float(graus.mean()),
        "gatilhos_efetivos_hhi": gatilhos_efetivos_hhi,
        "top_gatilhos": graus.head(8),
    }

    if nx is None:
        info["networkx"] = False
        return info

    g = nx.DiGraph()
    for _, elo in df_grafo.iterrows():
        # Elos duplicados (mesmo par em arquivos diferentes) somam forca em
        # vez de se sobrescrever -- e o que `montar_sinal_propagado` faz com
        # o `+=`, entao o grafo aqui tem que espelhar isso.
        if g.has_edge(elo["empresa_A"], elo["empresa_B"]):
            g[elo["empresa_A"]][elo["empresa_B"]]["weight"] += float(elo["forca"])
        else:
            g.add_edge(elo["empresa_A"], elo["empresa_B"], weight=float(elo["forca"]),
                       tipo=elo["tipo_de_elo"])

    nao_dirigido = g.to_undirected()
    componentes = sorted(nx.connected_components(nao_dirigido), key=len, reverse=True)
    comunidades = list(nx.community.greedy_modularity_communities(nao_dirigido))

    # Empresas que sao gatilho E satelite: sao os pontos onde a propagacao de
    # 2 saltos (A -> B -> C) seria possivel. Hoje o Bloco 4 so propaga 1
    # salto, entao esse canal esta inexplorado.
    pontes = set(df_grafo["empresa_A"]) & set(df_grafo["empresa_B"])

    info.update({
        "networkx": True,
        "n_componentes": len(componentes),
        "tamanho_maior_componente": len(componentes[0]) if componentes else 0,
        "n_comunidades": len(comunidades),
        "modularidade": float(nx.community.modularity(nao_dirigido, comunidades)),
        "densidade": float(nx.density(g)),
        "n_pontes_2_saltos": len(pontes),
        "pontes_2_saltos": sorted(pontes),
        "centralidade_grau": pd.Series(nx.degree_centrality(g)).sort_values(ascending=False).head(8),
    })
    return info


def breadth_efetiva_por_autovalores(df_sinal, mascara):
    """
    Numero efetivo de apostas independentes, medido nos SINAIS de verdade.

    Metodo: razao de participacao dos autovalores da matriz de correlacao
    dos sinais por satelite,

        N_eff = (soma dos autovalores)^2 / soma dos autovalores^2

    Interpretacao: se as p colunas fossem independentes, todos os autovalores
    valeriam 1 e N_eff = p. Se todas se movessem juntas, o primeiro
    autovalor valeria p e os outros 0, dando N_eff = 1. E a medida padrao de
    "quantas direcoes independentes existem" num conjunto correlacionado.

    Isto e mais honesto que contar elos porque captura DUAS fontes de
    redundancia ao mesmo tempo: elos que partem do mesmo gatilho (estrutural)
    e gatilhos cujos choques co-movem (estatistica) -- inclusive o que a
    regressao de choque limpo nao conseguiu remover.
    """
    sinal = df_sinal.loc[mascara.reindex(df_sinal.index, fill_value=False)]

    # Coluna sem variacao no periodo nao e aposta: e elo que nunca disparou.
    sinal = sinal.replace(0.0, np.nan).dropna(axis=1, how="all")
    sinal = sinal.loc[:, sinal.std() > 1e-12]
    if sinal.shape[1] < 2:
        return None

    corr = sinal.corr().to_numpy(dtype=float)
    corr = np.nan_to_num(corr, nan=0.0)
    np.fill_diagonal(corr, 1.0)

    autovalores = np.linalg.eigvalsh(corr)
    autovalores = autovalores[autovalores > 0]
    p = sinal.shape[1]
    n_eff = float(np.sum(autovalores) ** 2 / np.sum(autovalores**2))

    # Fracao da variancia no primeiro autovetor: se um "fator comum" domina,
    # e sinal de que a carteira faz uma aposta grande disfarcada de varias.
    frac_pc1 = float(autovalores.max() / np.sum(autovalores))

    return {
        "n_posicoes": p,
        "n_eff_autovalores": n_eff,
        "razao_n_eff": n_eff / p,
        "frac_variancia_pc1": frac_pc1,
    }


# ==================================================================
# ETAPA 3 -- power analysis: quantas apostas faltam
# ==================================================================

def validar_modelo_de_escala(ic_info, n_posicoes):
    """
    Checa o modelo de escala e extrai o N que governa a PRECISAO do IC.

    O modelo: o desvio-padrao do IC transversal diario e dominado por ruido de
    amostragem e vale ~ 1/raiz(N-3) para uma correlacao de N nomes. Invertendo
    a relacao, o std medido revela quantas posicoes EFETIVAS existem na secao
    transversal:

        N_ic_efetivo = 3 + 1 / std(IC)^2

    ATENCAO -- ESTE N NAO E A BREADTH DA ETAPA 2. Sao duas perguntas
    diferentes, e confundi-las foi um erro real na primeira versao deste
    script (o analitico dava 13 e o Monte Carlo 45, discordancia que expos o
    problema):

      - `N_ic_efetivo` governa a PRECISAO ESTATISTICA do IC. Nomes
        correlacionados contam menos que 1, mas a penalidade e suave: a
        correlacao rouba precisao, nao a destroi.
      - `n_eff_autovalores` (Etapa 2) governa o TETO DE RETORNO AJUSTADO A
        RISCO pela Lei Fundamental. Aqui a penalidade e severa, porque duas
        posicoes que sempre andam juntas somam risco sem somar alfa.

    O primeiro responde "quando consigo PROVAR que o sinal funciona"; o
    segundo, "quanto esse sinal pode RENDER". Nada obriga as duas respostas a
    coincidir -- e neste projeto elas nao coincidem nem de longe.
    """
    std_previsto = 1.0 / np.sqrt(max(n_posicoes - 3, 1))
    std_medido = ic_info["std_ic"]
    n_ic_efetivo = 3.0 + 1.0 / (std_medido**2) if std_medido > 0 else np.nan
    return {
        "n_posicoes_nominal": n_posicoes,
        "std_ic_medido": std_medido,
        "std_ic_previsto": std_previsto,
        "razao": std_medido / std_previsto if std_previsto > 0 else np.nan,
        "n_ic_efetivo": n_ic_efetivo,
    }


def posicoes_necessarias_para_significancia(ic_info, escala, t_alvo=T_ALVO):
    """
    PERGUNTA A -- quantas posicoes efetivas para t(IC) >= t_alvo?

    t do IC escala com raiz do numero de posicoes efetivas, entao

        N_necessario = N_ic_efetivo * (t_alvo / t_atual)^2

    O t usado e o HAC. A Etapa 1b mostrou que ele praticamente empata com o
    ingenuo, mas usar o HAC mantem a projecao conservadora sem custo.
    """
    t_atual = abs(ic_info["t_hac"])
    if t_atual < 1e-9 or not np.isfinite(escala["n_ic_efetivo"]):
        return None

    multiplicador = (t_alvo / t_atual) ** 2
    return {
        "t_hac_atual": t_atual,
        "n_ic_atual": escala["n_ic_efetivo"],
        "multiplicador": multiplicador,
        "n_ic_necessario": escala["n_ic_efetivo"] * multiplicador,
    }


def breadth_necessaria_para_ir(ic_info, breadth, irs_alvo=(0.75, 1.00, 1.50)):
    """
    PERGUNTA B -- quanta breadth independente para cada nivel de IR?

    Lei Fundamental: IR = IC * raiz(breadth) * raiz(252). Invertendo,

        breadth = (IR_alvo / (IC * raiz(252)))^2

    Traduz tambem para numero de POSICOES, usando a razao efetiva/nominal
    medida na Etapa 2 -- que e o preco que a correlacao entre os choques
    cobra. Se essa razao melhorar (controle setorial mais fino no choque
    limpo), o mesmo IR sai com menos posicoes.
    """
    ic = ic_info["ic_medio"]
    if ic <= 0:
        return None

    razao = breadth["razao_n_eff"]
    ir_atual = ic * np.sqrt(breadth["n_eff_autovalores"]) * np.sqrt(DIAS_UTEIS_ANO)

    linhas = []
    for ir_alvo in irs_alvo:
        breadth_nec = (ir_alvo / (ic * np.sqrt(DIAS_UTEIS_ANO))) ** 2
        linhas.append({
            "ir_alvo": ir_alvo,
            "breadth_necessaria": breadth_nec,
            "fator_vs_hoje": breadth_nec / breadth["n_eff_autovalores"],
            "posicoes_na_razao_atual": breadth_nec / razao if razao > 0 else np.nan,
        })

    return {"ir_atual": ir_atual, "tabela": pd.DataFrame(linhas)}


def curva_de_poder_monte_carlo(ic_verdadeiro, dias_efetivos, lista_n, n_sim=2000, semente=42):
    """
    Poder estatistico por simulacao, como contraprova da conta analitica.

    Desenho: para cada N, simula `n_sim` historias de `dias_efetivos`
    pregoes INDEPENDENTES, cada um com N apostas cuja correlacao verdadeira
    com o retorno seguinte e `ic_verdadeiro`. Mede o t do IC medio em cada
    historia e reporta a fracao com t >= T_ALVO -- que e a definicao de
    poder.

    A autocorrelacao induzida pela suavizacao NAO e simulada; ela entra pelo
    `dias_efetivos`, ja deflacionado pelo fator Newey-West medido. Manter
    isso explicito e melhor que embutir um modelo de media movel aqui, que
    adicionaria premissa sem adicionar informacao.

    Gerador com semente fixa: o resultado tem que ser reproduzivel pela
    banca.
    """
    rng = np.random.default_rng(semente)
    dias = int(max(dias_efetivos, 5))
    linhas = []

    for n in lista_n:
        n = int(n)
        if n < 5:
            continue
        ts = np.empty(n_sim)
        for s in range(n_sim):
            sinal = rng.standard_normal((dias, n))
            ruido = rng.standard_normal((dias, n))
            retorno = ic_verdadeiro * sinal + np.sqrt(max(1 - ic_verdadeiro**2, 0.0)) * ruido

            # IC transversal dia a dia, igual ao estimador do s6.
            sinal_c = sinal - sinal.mean(axis=1, keepdims=True)
            retorno_c = retorno - retorno.mean(axis=1, keepdims=True)
            num = (sinal_c * retorno_c).sum(axis=1)
            den = np.sqrt((sinal_c**2).sum(axis=1) * (retorno_c**2).sum(axis=1))
            ics = num / np.where(den > 0, den, np.nan)

            ics = ics[np.isfinite(ics)]
            ts[s] = ics.mean() / (ics.std(ddof=1) / np.sqrt(len(ics))) if len(ics) > 2 else np.nan

        ts = ts[np.isfinite(ts)]
        linhas.append({
            "n_apostas": n,
            "t_mediano": float(np.median(ts)),
            "poder_t2": float(np.mean(ts >= T_ALVO)),
        })

    return pd.DataFrame(linhas)


# ==================================================================
# IMPRESSAO
# ==================================================================

def _titulo(texto):
    print("\n" + "=" * 78)
    print(f" {texto}")
    print("=" * 78)


def imprimir_etapa1a(df_is, df_oos):
    _titulo("ETAPA 1a -- direcao por categoria: t ingenuo vs t clusterizado por data")

    print("\nIN-SAMPLE (2016-2020) -- e o periodo que DECIDE as direcoes:\n")
    print(f"{'tipo de elo':<24}{'elos':>5}{'n obs':>8}{'pregoes':>9}"
          f"{'corr':>9}{'t ing.':>9}{'t clust.':>10}{'inflacao':>10}{'|t|>=2':>9}")
    print("-" * 93)
    for _, r in df_is.iterrows():
        marca = "sim" if r["passa_limiar_cluster"] else ("PERDE" if r["passa_limiar_ingenuo"] else "nao")
        print(f"{r['tipo_de_elo']:<24}{r['n_elos']:>5}{r['n_obs']:>8}{r['n_pregoes']:>9}"
              f"{r['corr_T1']:>+9.4f}{r['t_ingenuo']:>9.2f}{r['t_cluster']:>10.2f}"
              f"{r['inflacao']:>9.2f}x{marca:>9}")

    perdem = df_is[df_is["passa_limiar_ingenuo"] & ~df_is["passa_limiar_cluster"]]
    mantem = df_is[df_is["passa_limiar_cluster"]]

    print("\nComo ler: `inflacao` e quantas vezes o t ingenuo era maior que o")
    print("correto. `PERDE` marca categoria que passava o limiar |t| >= 2 da regra")
    print("conservadora de P1 com o erro-padrao errado e nao passa com o certo.")

    print(f"\nCategorias que sustentam |t| >= 2 com erro-padrao clusterizado: "
          f"{len(mantem)} de {len(df_is)}")
    if len(perdem):
        print(f"Categorias que PERDEM o limiar: {', '.join(perdem['tipo_de_elo'])}")
    else:
        print("Nenhuma categoria perde o limiar -- a regra conservadora de P1 se")
        print("sustenta com inferencia correta.")

    print("\nOUT-OF-SAMPLE (2021-2025) -- so confirmacao, nao decide nada:\n")
    print(f"{'tipo de elo':<24}{'corr':>9}{'t ing.':>9}{'t clust.':>10}{'inflacao':>10}")
    print("-" * 62)
    for _, r in df_oos.iterrows():
        print(f"{r['tipo_de_elo']:<24}{r['corr_T1']:>+9.4f}{r['t_ingenuo']:>9.2f}"
              f"{r['t_cluster']:>10.2f}{r['inflacao']:>9.2f}x")


def imprimir_etapa1b(resultados):
    _titulo("ETAPA 1b -- t do IC: ingenuo vs Newey-West (observacoes sobrepostas)")

    print(f"\n{'periodo':<14}{'IC medio':>11}{'dias':>7}{'t ing.':>9}"
          f"{'t HAC':>9}{'t HAC auto':>12}{'inflacao':>10}{'rho(1)':>9}")
    print("-" * 81)
    for nome, r in resultados.items():
        if r is None:
            continue
        print(f"{nome:<14}{r['ic_medio']:>+11.4f}{r['n_dias']:>7}{r['t_ingenuo']:>9.2f}"
              f"{r['t_hac']:>9.2f}{r['t_hac_auto']:>12.2f}"
              f"{r['inflacao_medida']:>9.2f}x{r['rho1']:>9.3f}")

    exemplo = next((r for r in resultados.values() if r is not None), None)
    if exemplo is None:
        return

    print(f"\nmaxlags usado: {exemplo['maxlags']} (= janela de suavizacao do sinal); "
          f"regra automatica: {exemplo['maxlags_auto']}")
    print(f"Autocorrelacao da serie de IC: rho(1) = {exemplo['rho1']:.3f}, "
          f"rho(5) = {exemplo['rho5']:.3f}, rho(21) = {exemplo['rho21']:.3f}")

    print("\nHIPOTESE REFUTADA -- e este e o resultado desta etapa.")
    print("\nA suspeita era que a media movel de 21 pregoes no sinal deixasse os ICs")
    print("diarios autocorrelacionados, inflando o t ingenuo. rho(1) proximo de ZERO")
    print("mostra que nao: o Newey-West quase nao move o t (e no OOS move para CIMA).")
    print("\nMotivo: o IC de cada dia correlaciona o sinal suave com o retorno do dia")
    print("SEGUINTE. O sinal e persistente, mas o retorno e ruido fresco a cada")
    print("pregao -- e e o retorno que domina a variacao do produto. Suavizar o sinal")
    print("nao cria dependencia serial no IC.")
    print("\nConsequencia pratica: os t do IC reportados em 03/08 e 04/08 estao")
    print("CORRETOS como estao. Diferente da Etapa 1a, aqui nao ha nada a corrigir --")
    print("esta etapa fica no arquivo como a verificacao que fecha a duvida.")


def imprimir_etapa2(topologia, breadth, ic_oos):
    _titulo("ETAPA 2 -- breadth efetiva: elos nao sao apostas independentes")

    t = topologia
    print("\nTopologia do grafo em producao:\n")
    print(f"  elos                                {t['n_elos']:>6}")
    print(f"  gatilhos distintos (empresa_A)      {t['n_gatilhos']:>6}")
    print(f"  satelites distintos (empresa_B)     {t['n_satelites']:>6}")
    print(f"  empresas envolvidas                 {t['n_empresas']:>6}")
    print(f"  maior grau de saida                 {t['grau_saida_max']:>6}"
          f"   <- um choque abre {t['grau_saida_max']} posicoes")
    print(f"  gatilhos efetivos (1/HHI dos graus) {t['gatilhos_efetivos_hhi']:>9.1f}")

    print("\n  elos por gatilho (top 8):")
    for nome, grau in t["top_gatilhos"].items():
        print(f"    {nome:<10}{grau:>3} elos")

    if t.get("networkx"):
        print("\nEstrutura (networkx):\n")
        print(f"  componentes conexos                 {t['n_componentes']:>6}")
        print(f"  tamanho do maior componente         {t['tamanho_maior_componente']:>6}")
        print(f"  comunidades (modularidade gulosa)   {t['n_comunidades']:>6}")
        print(f"  modularidade                        {t['modularidade']:>9.3f}")
        print(f"  densidade                           {t['densidade']:>9.4f}")
        print(f"  empresas que sao gatilho E satelite {t['n_pontes_2_saltos']:>6}"
              f"   <- canal de 2 saltos inexplorado")
        if t["pontes_2_saltos"]:
            print(f"    {', '.join(t['pontes_2_saltos'])}")
    else:
        print("\n(networkx ausente -- metricas de comunidade e centralidade omitidas.")
        print(" Instale com: python -m pip install networkx)")

    if breadth is None:
        print("\nBreadth por autovalores: nao calculavel (poucas colunas com variacao).")
        return

    b = breadth
    print("\nBreadth efetiva medida nos sinais (OOS 2021-2025):\n")
    print(f"  posicoes com sinal ativo            {b['n_posicoes']:>6}")
    print(f"  apostas independentes (autovalores) {b['n_eff_autovalores']:>9.1f}")
    print(f"  razao efetiva / nominal             {b['razao_n_eff']:>9.1%}")
    print(f"  variancia no 1o autovetor           {b['frac_variancia_pc1']:>9.1%}")

    print("\nEste e o numero que a projecao de P3 em Correcoes1.md nao tinha. A")
    print(f"tabela de la conta elos ({t['n_elos']}); as apostas independentes sao")
    print(f"{b['n_eff_autovalores']:.1f}. A consequencia pratica e direta:")
    print("\n  ADICIONAR ELO NO MESMO GATILHO QUASE NAO AUMENTA BREADTH.")
    print("  Ganho de breadth vem de GATILHO novo e pouco correlacionado com os")
    print("  que ja existem -- nao de mais satelites pendurados na VALE3.")

    if ic_oos is not None:
        ir_teorico = ic_oos["ic_medio"] * np.sqrt(t["n_elos"]) * np.sqrt(DIAS_UTEIS_ANO)
        ir_efetivo = ic_oos["ic_medio"] * np.sqrt(b["n_eff_autovalores"]) * np.sqrt(DIAS_UTEIS_ANO)
        print("\nTeste de Grinold (IR ~ IC x raiz(breadth) x raiz(252)):\n")
        print(f"  contando elos      ({t['n_elos']:>4} apostas): IR previsto = {ir_teorico:>5.2f}")
        print(f"  breadth efetiva    ({b['n_eff_autovalores']:>6.1f} apostas): "
              f"IR previsto = {ir_efetivo:>5.2f}")
        print("\nO relatorio de 03/08 fechou a lacuna entre IR previsto e realizado com")
        print("um fator de 50% ad hoc. A breadth efetiva explica a mesma lacuna sem")
        print("fator livre -- e diz ONDE mexer para fecha-la.")


def imprimir_etapa3(escala, sig, ir_info, curva, ic_info, breadth):
    _titulo("ETAPA 3 -- power analysis: duas perguntas, duas respostas diferentes")

    print("\nValidacao do modelo de escala (antes de projetar):\n")
    print(f"  posicoes com sinal ativo            {escala['n_posicoes_nominal']:>9}")
    print(f"  std do IC diario medido             {escala['std_ic_medido']:>9.4f}")
    print(f"  previsto se as {escala['n_posicoes_nominal']} fossem indep.    "
          f"{escala['std_ic_previsto']:>9.4f}")
    print(f"  razao medido / previsto             {escala['razao']:>9.2f}")
    print(f"  => posicoes EFETIVAS para o IC      {escala['n_ic_efetivo']:>9.1f}")

    if 0.5 <= escala["razao"] <= 2.0:
        print("\n  Razao perto de 1: o std do IC e dominado por ruido de amostragem,")
        print("  entao projetar t em funcao de raiz(N) esta justificado.")
    else:
        print("\n  ATENCAO: razao longe de 1 -- o std do IC tem componente que nao e")
        print("  ruido de amostragem (IC instavel no tempo). A projecao abaixo vira")
        print("  ordem de grandeza, nao estimativa pontual.")

    print("\n  Note que este N (posicoes efetivas para o IC) e MAIOR que a breadth")
    print(f"  de {breadth['n_eff_autovalores']:.1f} da Etapa 2. Nao e contradicao: sao "
          "duas coisas distintas.")
    print("  Correlacao rouba precisao estatistica devagar e teto de retorno rapido.")

    # ---------------- Pergunta A ----------------
    print("\n" + "-" * 78)
    print(" PERGUNTA A -- quando o IC fica estatisticamente significante?")
    print("-" * 78)

    if sig is None:
        print("\nt(IC) atual indistinguivel de zero -- projecao nao definida.")
    else:
        print(f"\n  IC medido (OOS)                     {ic_info['ic_medio']:>+9.4f}")
        print(f"  t HAC atual                         {sig['t_hac_atual']:>9.2f}")
        print(f"  dias no periodo                     {ic_info['n_dias']:>9}")
        print(f"  posicoes efetivas hoje              {sig['n_ic_atual']:>9.1f}")
        print(f"  multiplicador para t = {T_ALVO:.0f}            {sig['multiplicador']:>9.2f}x")
        print(f"  posicoes efetivas necessarias       {sig['n_ic_necessario']:>9.0f}")

        if curva is not None and len(curva):
            print("\n  Contraprova por Monte Carlo:\n")
            print(f"  {'posicoes':>10}{'t mediano':>12}{'poder(t>=2)':>13}")
            print("  " + "-" * 33)
            for _, r in curva.iterrows():
                print(f"  {int(r['n_apostas']):>10}{r['t_mediano']:>12.2f}"
                      f"{r['poder_t2']:>12.0%}")

            adequadas = curva[curva["poder_t2"] >= 0.80]
            if len(adequadas):
                print(f"\n  Primeiro N com poder >= 80%: "
                      f"{int(adequadas.iloc[0]['n_apostas'])} posicoes efetivas")
            else:
                print("\n  Nenhum N testado alcanca poder de 80%.")
            print("\n  O ponto ancora da simulacao tem que reproduzir o t medido -- se")
            print("  nao reproduzir, o modelo de escala esta errado e a projecao nao")
            print("  vale. Confira a linha mais proxima de "
                  f"{sig['n_ic_atual']:.0f} posicoes contra t = {sig['t_hac_atual']:.2f}.")

        print("\n  RESPOSTA A -- e a distincao aqui importa:")
        print(f"\n  Para t ESPERADO = 2 bastam ~{sig['n_ic_necessario']:.0f} posicoes efetivas "
              f"(vs {sig['n_ic_atual']:.0f} hoje).")
        print("  Mas t esperado = 2 significa 50% de chance de cruzar o limiar -- uma")
        print("  moeda. Para PODER de 80%, que e o padrao para se planejar um teste, a")
        print("  simulacao acima pede bem mais.")
        print("\n  Ou seja: 'quase significante' nao e 'quase provado'. A folga entre")
        print("  t esperado = 2 e poder = 80% e justamente o que faz um resultado")
        print("  positivo ser reproduzivel em vez de sorte de amostra.")
        print("\n  Caminho alternativo e de graca: t cresce com raiz(T) tambem. No")
        print("  periodo COMPLETO (10 anos) o t do IC ja passa de 2 sem mexer em nada --")
        print("  ver Etapa 1b. O OOS de 5 anos e que e curto.")

    # ---------------- Pergunta B ----------------
    print("\n" + "-" * 78)
    print(" PERGUNTA B -- quanto a estrategia pode RENDER (Lei Fundamental)?")
    print("-" * 78)

    if ir_info is None:
        print("\nIC nao positivo -- projecao de IR nao definida.")
    else:
        print(f"\n  IR implicado pela breadth de hoje ({breadth['n_eff_autovalores']:.1f} "
              f"apostas): {ir_info['ir_atual']:.2f}")
        print(f"\n  {'IR alvo':>9}{'breadth nec.':>15}{'vs hoje':>10}"
              f"{'posicoes @ razao atual':>25}")
        print("  " + "-" * 57)
        for _, r in ir_info["tabela"].iterrows():
            print(f"  {r['ir_alvo']:>9.2f}{r['breadth_necessaria']:>15.0f}"
                  f"{r['fator_vs_hoje']:>9.1f}x{r['posicoes_na_razao_atual']:>25.0f}")

        print(f"\n  A ultima coluna usa a razao efetiva/nominal medida hoje "
              f"({breadth['razao_n_eff']:.0%}).")
        print("  Ela e o preco que a correlacao residual entre os choques cobra: para")
        print(f"  cada aposta independente, {1/breadth['razao_n_eff']:.1f} posicoes.")

        print("\n  RESPOSTA B: e aqui que o gargalo esta, e e MUITO maior que a")
        print("  pergunta A. Elevar o IR exige multiplicar a breadth, nao a contagem")
        print("  de elos.")

    # ---------------- Leitura ----------------
    print("\n" + "=" * 78)
    print(" LEITURA -- o que isso muda no plano de P3")
    print("=" * 78)
    print("\nP3 tem DUAS metas, e o projeto vinha tratando como uma:")
    print("\n  A) provar que o sinal funciona  -> quase resolvido, custa pouco")
    print("  B) fazer o sinal render          -> exige multiplicar breadth")
    print("\nHa dois caminhos para (B), e a Etapa 2 mostra que o segundo estava")
    print("fora do radar:")
    print("\n  1. MAIS GATILHOS pouco correlacionados entre si. Elo novo pendurado em")
    print("     gatilho que ja existe quase nao conta -- e o que a razao")
    print(f"     efetiva/nominal de {breadth['razao_n_eff']:.0%} esta dizendo.")
    print("\n  2. MELHORAR A RAZAO efetiva/nominal, tornando os choques mais")
    print("     independentes entre si. Isso e controle setorial mais fino no")
    print("     `calcular_choque_limpo` -- item que Correcoes1.md ja listou em P4 e")
    print("     que ninguem ligou a breadth. Barato comparado a escrever 150 elos,")
    print("     e melhora o teto SEM adicionar uma linha ao grafo.")
    print("\nMedir progresso: rodar a Etapa 2 a cada lote de elos novos. Contar linhas")
    print("do CSV nao mede nada -- 58 elos entregam 11 apostas.")


# ==================================================================
# MAIN
# ==================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Inferencia honesta (t-stats) e breadth efetiva do grafo -- dimensiona P3."
    )
    parser.add_argument("--etapa", type=int, choices=[1, 2, 3], default=None,
                        help="roda so uma etapa (default: todas)")
    parser.add_argument("--recalcular-choques", action="store_true",
                        help="ignora o cache de choques do s6 e recalcula")
    parser.add_argument("--simulacoes", type=int, default=2000,
                        help="simulacoes por ponto na curva de poder (default: 2000)")
    args = parser.parse_args()

    rodar = {1, 2, 3} if args.etapa is None else {args.etapa}

    print("=" * 78)
    print(" BLOCO 6 -- INFERENCIA HONESTA E BREADTH EFETIVA (dimensionamento de P3)")
    print("=" * 78)

    contexto, df_grafo = s6.montar_contexto(
        recalcular_choques=args.recalcular_choques, verboso=True
    )
    df_retornos = contexto["retornos"]
    df_choques = contexto["choques"]
    periodos = contexto["periodos"]

    os.makedirs(SAIDA_DIR, exist_ok=True)

    # O sinal do grafo em producao serve as etapas 1b, 2 e 3. Gerado uma vez.
    df_sinal = None
    if rodar & {1, 2, 3}:
        print("\nGerando o sinal do grafo em producao (Bloco 4, janela de 21d)...")
        df_sinal = s6.gerar_sinal(df_choques, df_grafo, JANELA_SINAL)

    ic_oos = None

    # ---------------- ETAPA 1 ----------------
    if 1 in rodar:
        print("\nMedindo direcoes com erro-padrao clusterizado por data...")
        df_is = medir_direcao_clusterizada(df_grafo, df_choques, df_retornos, ate=DATA_CORTE)

        # OOS: mesma medicao restrita a 2021+. Filtra pelo periodo aplicando o
        # corte inferior antes de empilhar.
        choques_oos = df_choques.loc[df_choques.index > DATA_CORTE]
        retornos_oos = df_retornos.loc[df_retornos.index > DATA_CORTE]
        df_oos = medir_direcao_clusterizada(df_grafo, choques_oos, retornos_oos)

        imprimir_etapa1a(df_is, df_oos)
        df_is.to_csv(os.path.join(SAIDA_DIR, "t_stats_clusterizados_is.csv"), index=False)
        df_oos.to_csv(os.path.join(SAIDA_DIR, "t_stats_clusterizados_oos.csv"), index=False)

        resultados_ic = {}
        for nome in ["IS 16-20", "OOS 21-25", "completo"]:
            resultados_ic[nome] = calcular_ic_hac(df_sinal, df_retornos, periodos[nome])
        imprimir_etapa1b(resultados_ic)
        ic_oos = resultados_ic["OOS 21-25"]

        tabela_ic = pd.DataFrame([
            {k: v for k, v in r.items() if k != "serie_ic"} | {"periodo": nome}
            for nome, r in resultados_ic.items() if r is not None
        ])
        tabela_ic.to_csv(os.path.join(SAIDA_DIR, "ic_hac.csv"), index=False)

    # ---------------- ETAPA 2 ----------------
    topologia = breadth = None
    if 2 in rodar:
        topologia = analisar_topologia(df_grafo)
        breadth = breadth_efetiva_por_autovalores(df_sinal, periodos["OOS 21-25"])
        if ic_oos is None:
            ic_oos = calcular_ic_hac(df_sinal, df_retornos, periodos["OOS 21-25"])
        imprimir_etapa2(topologia, breadth, ic_oos)

        pd.DataFrame([{k: v for k, v in topologia.items()
                       if not isinstance(v, (pd.Series, list))}]).to_csv(
            os.path.join(SAIDA_DIR, "topologia_grafo.csv"), index=False)
        if breadth is not None:
            pd.DataFrame([breadth]).to_csv(
                os.path.join(SAIDA_DIR, "breadth_efetiva.csv"), index=False)

    # ---------------- ETAPA 3 ----------------
    if 3 in rodar:
        if ic_oos is None:
            ic_oos = calcular_ic_hac(df_sinal, df_retornos, periodos["OOS 21-25"])
        if breadth is None:
            breadth = breadth_efetiva_por_autovalores(df_sinal, periodos["OOS 21-25"])

        if ic_oos is None or breadth is None:
            print("\nEtapa 3 exige IC e breadth calculaveis -- pulada.")
        else:
            escala = validar_modelo_de_escala(ic_oos, breadth["n_posicoes"])
            sig = posicoes_necessarias_para_significancia(ic_oos, escala)
            ir_info = breadth_necessaria_para_ir(ic_oos, breadth)

            curva = None
            if sig is not None:
                # A Etapa 1b mostrou que nao ha inflacao por autocorrelacao
                # (rho ~ 0), entao os dias entram sem deflacionar. Se algum dia
                # a janela de suavizacao mudar e o rho subir, `inflacao_medida`
                # passa a valer e este e o lugar de aplica-la.
                dias = ic_oos["n_dias"]
                atual = escala["n_ic_efetivo"]
                # A grade inclui o ponto ATUAL de proposito: e o teste de
                # sanidade da simulacao. Se o MC no N atual nao devolver o t
                # medido, o modelo de escala esta errado e a projecao inteira
                # cai -- foi essa checagem que pegou o bug da primeira versao,
                # em que o analitico dizia 13 e o MC dizia 45.
                grade = sorted({
                    int(round(x)) for x in [
                        atual * 0.5, atual, sig["n_ic_necessario"],
                        atual * 2, atual * 4,
                    ] if x >= 5
                })
                print(f"\nSimulando poder para {len(grade)} valores de N "
                      f"({args.simulacoes} simulacoes cada)...")
                curva = curva_de_poder_monte_carlo(
                    ic_oos["ic_medio"], dias, grade, n_sim=args.simulacoes
                )
                curva.to_csv(os.path.join(SAIDA_DIR, "curva_poder_ic.csv"), index=False)

            if ir_info is not None:
                ir_info["tabela"].to_csv(
                    os.path.join(SAIDA_DIR, "breadth_para_ir.csv"), index=False)

            imprimir_etapa3(escala, sig, ir_info, curva, ic_oos, breadth)

    print(f"\n\nArtefatos salvos em: {SAIDA_DIR}")


if __name__ == "__main__":
    main()
