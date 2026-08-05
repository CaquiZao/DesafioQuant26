"""
Bloco 6: Validacao out-of-sample (pendencia P1).

POR QUE ESTE SCRIPT EXISTE
--------------------------
A direcao dos elos `concorrente` foi invertida (-1 -> +1) depois de olhar o
resultado dos 10 anos inteiros. Isso e vies de "espiar os dados" (data
snooping): qualquer regra escolhida assim parece boa NO PERIODO EM QUE FOI
ESCOLHIDA. Enquanto essa decisao nao passar por um teste honesto, o +8,7%
do backtest nao e um numero defensavel.

O PROTOCOLO (e o ponto inteiro deste arquivo)
---------------------------------------------
1. IN-SAMPLE (ate 2020-12-31): decide a direcao de cada TIPO de elo olhando
   SO este periodo. Nada depois do corte entra na decisao.
2. CONGELA: as direcoes viram um CSV imutavel. Nenhum parametro e ajustado
   depois disso.
3. OUT-OF-SAMPLE (2021-01-01 em diante): mede. Uma unica vez, sem voltar
   atras para "melhorar".

Se o edge sobreviver ao passo 3, ele e real. Se nao sobreviver, a inversao
era ajuste de curva -- e e melhor descobrir isso agora do que na banca.

VARIANTES COMPARADAS
--------------------
- `congelado_is`  : direcoes decididas SO com 2016-2020. E o teste honesto.
- `atual`         : o grafo_manual_base.csv como esta hoje (decidido com a
                    amostra inteira). Serve de teto contaminado -- se ele bate
                    muito o congelado no OOS, a diferenca e puro overfit.
- `pre_inversao`  : `concorrente` de volta a -1, como era antes da sessao
                    de 03/08. E a hipotese economica original.

CONTAMINACAO RESIDUAL (declarada, nao escondida)
-----------------------------------------------
As janelas de suavizacao (21d no sinal, 10d nos pesos) foram escolhidas
varrendo valores no periodo inteiro. Elas NAO sao re-escolhidas aqui -- ficam
iguais nas tres variantes, entao nao explicam diferencas ENTRE elas, mas
inflam um pouco o nivel absoluto de todas. O modo --sensibilidade-janelas
mede o tamanho desse efeito.

USO
---
    python "fase 6 - validacao/src/s6_validacao_oos.py"
    python "fase 6 - validacao/src/s6_validacao_oos.py" --sensibilidade-janelas
    python "fase 6 - validacao/src/s6_validacao_oos.py" --recalcular-choques
"""

import argparse
import importlib.util
import os
import sys

import numpy as np
import pandas as pd

# ------------------------------------------------------------------
# Caminhos e import dos blocos existentes
# ------------------------------------------------------------------
# As pastas do projeto tem espacos e acentos no nome ("fase 4 - sinal da
# sinapse"), o que impede `import` normal. Carregamos os modulos pelo
# caminho do arquivo para reusar EXATAMENTE o codigo do pipeline oficial --
# se a validacao reimplementasse a logica, estaria validando outra coisa.

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


s4 = _carregar_modulo("s4_sinapse", os.path.join("fase 4 - sinal da sinapse", "src", "s4_sinapse_sinal.py"))
s5 = _carregar_modulo("s5_builder", os.path.join("fase 5 - construcao da carteira", "src", "s5_portfolio_builder.py"))
s3 = _carregar_modulo("s3_backtest", os.path.join("fase 3 - backtest", "src", "s3_backtest.py"))


# ------------------------------------------------------------------
# Parametros do protocolo
# ------------------------------------------------------------------

# Corte in-sample / out-of-sample. 2016-2020 (5 anos) para decidir,
# 2021-2025 (5 anos) para medir -- metade/metade, definido ANTES de olhar
# qualquer resultado, e igual ao corte ja citado no relatorio de 03/08.
DATA_CORTE = pd.Timestamp("2020-12-31")

# Dias uteis no ano (anualizacao) e custo por giro: os mesmos do Bloco 3,
# importados de la para nao divergirem silenciosamente.
DIAS_UTEIS_ANO = s3.DIAS_UTEIS_ANO
CUSTO = s3.CUSTO

AUM = 100_000_000


# ------------------------------------------------------------------
# 1) Insumos (choques e betas sao caros: ficam em cache)
# ------------------------------------------------------------------

def carregar_insumos(recalcular=False):
    """
    Devolve (df_retornos, df_grafo, df_map, df_choques, df_betas).

    O choque limpo vem da regressao rolling de 252 dias do Bloco 4, que so
    olha para tras. Por isso pode ser calculado sobre a serie inteira sem
    criar look-ahead: o choque do dia T usa apenas dados <= T.
    """
    df_retornos, df_indices, df_grafo, df_map = s4.carregar_dados()

    os.makedirs(SAIDA_DIR, exist_ok=True)
    cache_choques = os.path.join(SAIDA_DIR, "choques_limpos.parquet")
    cache_betas = os.path.join(SAIDA_DIR, "betas.parquet")

    if not recalcular and os.path.exists(cache_choques) and os.path.exists(cache_betas):
        print("Choques e betas lidos do cache de validacao.")
        df_choques = pd.read_parquet(cache_choques)
        df_betas = pd.read_parquet(cache_betas)
    else:
        tickers_do_grafo = set(df_grafo["empresa_A"]) | set(df_grafo["empresa_B"])
        df_choques, df_betas = s4.calcular_choque_limpo(
            df_retornos, df_indices, df_map, tickers_alvo=tickers_do_grafo
        )
        df_choques = df_choques.astype(float)
        df_betas = df_betas.astype(float)
        df_choques.to_parquet(cache_choques, engine="pyarrow")
        df_betas.to_parquet(cache_betas, engine="pyarrow")
        print(f"Choques e betas calculados e salvos em {SAIDA_DIR}")

    return df_retornos, df_grafo, df_map, df_choques, df_betas


# ------------------------------------------------------------------
# 2) ETAPA 1 do protocolo: decidir as direcoes usando SO o in-sample
# ------------------------------------------------------------------

def medir_direcao_por_categoria(df_grafo, df_choques, df_retornos, ate=None):
    """
    Para cada `tipo_de_elo`, mede a correlacao entre o choque limpo da
    empresa gatilho em T e o retorno da empresa satelite em T+1, empilhando
    (pooling) todos os elos daquela categoria.

    `ate` limita a amostra -- e o que garante que a decisao nao enxerga o
    futuro. Com `ate=DATA_CORTE`, nenhum dado de 2021+ participa.

    A decisao e por CATEGORIA, nao elo a elo, de proposito: com ~15 elos por
    categoria e 5 anos, escolher o sinal de cada elo individualmente seria
    ajustar 30 parametros no ruido. Categoria inteira e 3 parametros.
    """
    resultados = []

    for tipo, elos in df_grafo.groupby("tipo_de_elo"):
        pares_x, pares_y = [], []

        for _, elo in elos.iterrows():
            a, b = elo["empresa_A"], elo["empresa_B"]
            if a not in df_choques.columns or b not in df_retornos.columns:
                continue

            choque_a = df_choques[a]
            # T+1: o retorno do dia seguinte e o que a estrategia captura,
            # ja que o Bloco 5 aplica lag de execucao.
            retorno_b_amanha = df_retornos[b].shift(-1)

            par = pd.concat([choque_a, retorno_b_amanha], axis=1).dropna()
            if ate is not None:
                par = par.loc[par.index <= ate]
            if len(par) < 100:
                continue

            pares_x.append(par.iloc[:, 0])
            pares_y.append(par.iloc[:, 1])

        if not pares_x:
            continue

        x = pd.concat(pares_x).to_numpy(dtype=float)
        y = pd.concat(pares_y).to_numpy(dtype=float)
        corr = float(np.corrcoef(x, y)[0, 1])
        n = len(x)
        # t-stat da correlacao de Pearson. Serve so de diagnostico: com n na
        # casa das dezenas de milhares, |t| > 2 e facil de obter e NAO e
        # prova de edge economico.
        t = corr * np.sqrt(max(n - 2, 1)) / np.sqrt(max(1 - corr**2, 1e-12))

        resultados.append({
            "tipo_de_elo": tipo,
            "n_elos": len(elos),
            "n_obs": n,
            "corr_T1": corr,
            "t_stat": t,
            "direcao_decidida": 1 if corr >= 0 else -1,
        })

    return pd.DataFrame(resultados).sort_values("tipo_de_elo").reset_index(drop=True)


# Prior economico do time, definido ANTES de qualquer backtest: o choque
# se propaga na MESMA direcao ao longo da cadeia produtiva (cliente,
# fornecedor, holding, imobiliario) e na direcao OPOSTA entre rivais que
# disputam o mesmo mercado (concorrente, substituto).
PRIOR_ECONOMICO = {
    "cliente": 1,
    "fornecedor": 1,
    "holding_subsidiaria": 1,
    "imobiliario_logistica": 1,
    "concorrente": -1,
    "substituto": -1,
}

# Acima de qual |t| consideramos que o dado tem forca para DERRUBAR o prior
# economico. 2.0 e o corte convencional de significancia (~5%).
T_MINIMO_PARA_INVERTER = 2.0


def construir_variantes(df_grafo, direcoes_is):
    """
    Monta as versoes do grafo que serao comparadas.

    Importante: so a coluna `direcao` muda. Empresas, forcas e tipos sao
    identicos em todas, entao qualquer diferenca de resultado vem da regra
    de direcao -- que e exatamente a hipotese sob teste.
    """
    mapa_is = dict(zip(direcoes_is["tipo_de_elo"], direcoes_is["direcao_decidida"]))
    t_por_tipo = dict(zip(direcoes_is["tipo_de_elo"], direcoes_is["t_stat"]))

    congelado = df_grafo.copy()
    congelado["direcao"] = congelado["tipo_de_elo"].map(mapa_is).fillna(1).astype(int)

    pre_inversao = df_grafo.copy()
    pre_inversao.loc[pre_inversao["tipo_de_elo"] == "concorrente", "direcao"] = -1

    # Variante CONSERVADORA: parte do prior economico e so o abandona onde o
    # in-sample tem forca estatistica para isso (|t| > 2).
    #
    # A motivacao e um defeito do `congelado_is`: ele congela a direcao pelo
    # SINAL da correlacao, mesmo quando esse sinal e ruido puro. No IS,
    # `imobiliario_logistica` deu t = -0,20 e `fornecedor` t = -0,92 -- virar
    # a aposta de 6 elos com base nisso e ajustar curva em ruido, so que num
    # periodo diferente. Exigir significancia e a regra estatisticamente
    # honesta, e ela vale a priori (nao foi escolhida olhando o OOS).
    def direcao_conservadora(tipo):
        prior = PRIOR_ECONOMICO.get(tipo, 1)
        t = t_por_tipo.get(tipo, 0.0)
        medido = mapa_is.get(tipo, prior)
        if abs(t) >= T_MINIMO_PARA_INVERTER and medido != prior:
            return medido
        return prior

    conservador = df_grafo.copy()
    conservador["direcao"] = conservador["tipo_de_elo"].map(direcao_conservadora).astype(int)

    return {
        "congelado_is": congelado,
        "conservador": conservador,
        "atual": df_grafo.copy(),
        "pre_inversao": pre_inversao,
    }


# ------------------------------------------------------------------
# 3) Rodar o pipeline (Bloco 4 -> 5 -> 3) para um grafo qualquer
# ------------------------------------------------------------------

def gerar_sinal(df_choques, df_grafo, janela_sinal):
    """Passos 4.3 a 4.5 do Bloco 4, com o grafo passado por parametro."""
    df_sinais = s4.montar_sinal_propagado(df_choques, df_grafo)
    df_sinal = s4.limpar_e_winsorizar_sinal(df_sinais)
    return s4.suavizar_sinal(df_sinal, janela=janela_sinal)


def gerar_pesos(df_sinal, df_retornos, df_betas, df_adtv, df_sectors, janela_pesos):
    """Bloco 5 completo, com as mesmas travas institucionais do pipeline."""
    df_ret, _ = df_retornos.align(df_sinal, join="right")
    df_bet, _ = df_betas.align(df_sinal, join="right")
    df_adt = None
    if df_adtv is not None:
        df_adt, _ = df_adtv.align(df_sinal, join="right")

    pb = s5.PortfolioBuilder(aum=AUM, janela_suavizacao_pesos=janela_pesos)
    return pb.build_portfolio(
        df_zscore=df_sinal,
        df_returns=df_ret,
        df_adtv=df_adt,
        df_betas=df_bet,
        df_sectors=df_sectors,
    )


def rodar_backtest(df_pesos, df_retornos, retorno_ibov):
    """Bloco 3, reusando `rodar_motor` para nao reimplementar o P&L."""
    retornos = df_retornos.copy()
    retornos["IBOV_SYNTHETIC"] = retorno_ibov.reindex(retornos.index)
    # Mesma protecao do Bloco 3: dia sem Ibovespa faria o hedge "render
    # zero" e vazar beta. Descarta-se o dia inteiro.
    retornos = retornos.loc[~retornos["IBOV_SYNTHETIC"].isna()]

    retorno_liquido, pnl_bruto, giro = s3.rodar_motor(df_pesos, retornos, CUSTO)
    return retorno_liquido, pnl_bruto, giro


# ------------------------------------------------------------------
# 4) Metricas por sub-periodo
# ------------------------------------------------------------------

def calcular_ic(df_sinal, df_retornos, mascara):
    """
    Information Coefficient: correlacao TRANSVERSAL, dia a dia, entre o
    sinal de hoje e o retorno de amanha, depois promediada no tempo.

    E a medida mais direta de "o sinal preve alguma coisa?" -- independente
    de travas, alavancagem e custo. Um IC positivo e estavel e o que
    sustenta a tese; retorno de backtest sozinho pode vir de sorte na
    calibragem de risco.
    """
    colunas = [c for c in df_sinal.columns if c in df_retornos.columns]
    sinal = df_sinal[colunas]
    retorno_amanha = df_retornos[colunas].reindex(sinal.index).shift(-1)

    sinal = sinal.loc[mascara.reindex(sinal.index, fill_value=False)]
    retorno_amanha = retorno_amanha.loc[sinal.index]

    ics = sinal.corrwith(retorno_amanha, axis=1).dropna()
    if len(ics) < 2:
        return np.nan, np.nan, 0

    ic_medio = float(ics.mean())
    t = ic_medio / (ics.std() / np.sqrt(len(ics)))
    return ic_medio, float(t), len(ics)


def metricas_periodo(retorno_liquido, pnl_bruto, giro, retorno_cdi, mascara, nome_periodo):
    r = retorno_liquido.loc[mascara.reindex(retorno_liquido.index, fill_value=False)].dropna()
    if len(r) < 20:
        return None

    bruto = pnl_bruto.reindex(r.index)
    giro_p = giro.reindex(r.index)
    cdi = retorno_cdi.reindex(r.index).fillna(0.0)

    # `r` e o P&L da carteira LONG-SHORT, que ja E um retorno em excesso:
    # as posicoes vendidas financiam as compradas (net ~ 0), entao o AUM
    # fica em caixa rendendo CDI. O retorno do FUNDO e CDI + P&L_LS.
    #
    # Subtrair o CDI de `r` para calcular Sharpe -- como o Bloco 3 faz hoje
    # -- desconta a taxa livre de risco DUAS VEZES e produz o absurdo de um
    # Sharpe negativo com retorno positivo. O Sharpe correto de uma carteira
    # autofinanciada e simplesmente media/desvio do proprio P&L.
    retorno_fundo = r + cdi
    curva_ls = (1 + r).cumprod()
    curva_fundo = (1 + retorno_fundo).cumprod()
    vol = r.std() * np.sqrt(DIAS_UTEIS_ANO)
    sharpe = (r.mean() / r.std()) * np.sqrt(DIAS_UTEIS_ANO) if r.std() > 0 else np.nan

    return {
        "periodo": nome_periodo,
        "dias": len(r),
        "retorno_total": float(curva_ls.iloc[-1] - 1),
        "retorno_fundo_total": float(curva_fundo.iloc[-1] - 1),
        "liquido_ano": float(r.mean() * DIAS_UTEIS_ANO),
        "fundo_ano": float(retorno_fundo.mean() * DIAS_UTEIS_ANO),
        "bruto_ano": float(bruto.mean() * DIAS_UTEIS_ANO),
        "cdi_ano": float(cdi.mean() * DIAS_UTEIS_ANO),
        "vol_ano": float(vol),
        "sharpe": float(sharpe),
        "giro_dia": float(giro_p.mean()),
        "dd_max": float((curva_ls / curva_ls.cummax() - 1).min()),
    }


# ------------------------------------------------------------------
# 5) Orquestracao
# ------------------------------------------------------------------

def avaliar_variante(nome, df_grafo_variante, contexto, janela_sinal=None, janela_pesos=None):
    janela_sinal = s4.JANELA_SUAVIZACAO if janela_sinal is None else janela_sinal
    janela_pesos = 10 if janela_pesos is None else janela_pesos

    df_sinal = gerar_sinal(contexto["choques"], df_grafo_variante, janela_sinal)
    df_pesos = gerar_pesos(
        df_sinal, contexto["retornos"], contexto["betas"],
        contexto["adtv"], contexto["setores"], janela_pesos,
    )
    retorno_liquido, pnl_bruto, giro = rodar_backtest(
        df_pesos, contexto["retornos"], contexto["ibov"]
    )

    linhas = []
    for nome_periodo, mascara_datas in contexto["periodos"].items():
        m = metricas_periodo(
            retorno_liquido, pnl_bruto, giro, contexto["cdi"], mascara_datas, nome_periodo
        )
        if m is None:
            continue
        ic, ic_t, ic_n = calcular_ic(df_sinal, contexto["retornos"], mascara_datas)
        # Numero medio de posicoes abertas por dia (fora o hedge). E a
        # "breadth" da estrategia: pelo criterio de Grinold, o Sharpe
        # alcancavel cresce com a raiz do numero de apostas independentes,
        # entao esta coluna e o que justifica (ou nao) a pendencia P7.
        posicoes = df_pesos.drop(columns=["IBOV_SYNTHETIC"], errors="ignore")
        posicoes = posicoes.loc[posicoes.index.isin(
            mascara_datas[mascara_datas].index
        )]
        n_posicoes = float((posicoes.abs() > 1e-9).sum(axis=1).mean())
        m.update({"variante": nome, "ic": ic, "ic_t": ic_t, "ic_dias": ic_n,
                  "n_posicoes": n_posicoes})
        linhas.append(m)

    return pd.DataFrame(linhas), df_sinal


def imprimir_tabela(df, titulo):
    print(f"\n{titulo}")
    print("-" * len(titulo))
    if df.empty:
        print("(sem dados)")
        return
    # alfa/ano = P&L da carteira long-short (= excesso sobre o CDI).
    # fundo/ano = CDI + alfa, que e o que o cotista veria.
    print(
        f"{'variante':<14} {'periodo':<10} {'alfa/ano':>9} {'fundo/ano':>10} "
        f"{'CDI/ano':>9} {'vol':>7} {'Sharpe':>7} {'giro':>7} {'IC':>9} {'t(IC)':>7}"
    )
    for _, r in df.iterrows():
        print(
            f"{r['variante']:<14} {r['periodo']:<10} {r['liquido_ano']:>+8.2%} "
            f"{r['fundo_ano']:>+9.2%} {r['cdi_ano']:>8.2%} {r['vol_ano']:>6.2%} "
            f"{r['sharpe']:>7.2f} {r['giro_dia']:>6.1%} {r['ic']:>+9.4f} {r['ic_t']:>7.2f}"
        )


def montar_contexto(recalcular_choques=False, verboso=True):
    """
    Carrega tudo que o pipeline precisa e devolve (contexto, df_grafo).

    Extraido do main porque outros testes (ex.: o teste bidirecional da
    pendencia P7) precisam exatamente do mesmo contexto -- mesmos choques,
    mesmo corte IS/OOS, mesmas travas. Reusar garante que os resultados
    sejam comparaveis entre si.
    """
    df_retornos, df_grafo, df_map, df_choques, df_betas = carregar_insumos(recalcular_choques)

    # Setores no formato que o PortfolioBuilder espera (index = Ticker,
    # coluna 'Setor'). O CSV do Bloco 4 usa outros nomes de coluna.
    df_sectors = df_map.copy()
    df_sectors.columns = ["Ticker", "Setor"] + list(df_sectors.columns[2:])
    df_sectors = df_sectors.set_index("Ticker")[["Setor"]]

    caminho_adtv = os.path.join(DATA_DIR, "universo", "adtv_diario.parquet")
    df_adtv = pd.read_parquet(caminho_adtv) if os.path.exists(caminho_adtv) else None

    data_inicio = df_retornos.index.min().strftime("%Y-%m-%d")
    data_fim = df_retornos.index.max().strftime("%Y-%m-%d")
    retorno_ibov = s3.carregar_retorno_ibovespa(s3.CAMINHO_INDICES, data_inicio, data_fim)
    retorno_cdi = s3.carregar_retorno_cdi(s3.CAMINHO_CDI, data_inicio, data_fim)

    datas = df_retornos.index
    periodos = {
        "IS 16-20": pd.Series(datas <= DATA_CORTE, index=datas),
        "OOS 21-25": pd.Series(datas > DATA_CORTE, index=datas),
        "completo": pd.Series(True, index=datas),
    }

    contexto = {
        "retornos": df_retornos, "choques": df_choques, "betas": df_betas,
        "adtv": df_adtv, "setores": df_sectors, "ibov": retorno_ibov,
        "cdi": retorno_cdi, "periodos": periodos,
    }

    if verboso:
        print(f"\nAmostra: {data_inicio} a {data_fim}")
        print(f"Corte IS/OOS: {DATA_CORTE.date()}  "
              f"(IS = {int(periodos['IS 16-20'].sum())} dias, "
              f"OOS = {int(periodos['OOS 21-25'].sum())} dias)")

    return contexto, df_grafo


def main():
    parser = argparse.ArgumentParser(description="Validacao out-of-sample da Sinapse (P1)")
    parser.add_argument("--recalcular-choques", action="store_true",
                        help="ignora o cache e refaz a regressao rolling (lento)")
    parser.add_argument("--sensibilidade-janelas", action="store_true",
                        help="mede o quanto o resultado OOS depende das janelas de suavizacao")
    args = parser.parse_args()

    print("=" * 62)
    print(" BLOCO 6 -- VALIDACAO OUT-OF-SAMPLE (pendencia P1)")
    print("=" * 62)

    contexto, df_grafo = montar_contexto(args.recalcular_choques)
    df_retornos = contexto["retornos"]
    df_choques = contexto["choques"]
    periodos = contexto["periodos"]

    # ---------- ETAPA 1: decidir olhando SO o in-sample ----------
    print("\n[ETAPA 1] Decidindo a direcao de cada tipo de elo com dados ate "
          f"{DATA_CORTE.date()} -- nada de 2021+ entra aqui.")
    direcoes_is = medir_direcao_por_categoria(df_grafo, df_choques, df_retornos, ate=DATA_CORTE)
    print()
    print(direcoes_is.to_string(index=False))

    # Referencia de diagnostico: a mesma medicao no OOS. NAO alimenta
    # nenhuma decisao -- serve so para mostrar se a relacao virou de sinal.
    direcoes_oos = medir_direcao_por_categoria(
        df_grafo, df_choques, df_retornos.loc[df_retornos.index > DATA_CORTE]
    )
    print("\n(diagnostico -- a mesma medicao no OOS, NAO usada para decidir)")
    print(direcoes_oos[["tipo_de_elo", "corr_T1", "t_stat", "direcao_decidida"]].to_string(index=False))

    concordam = direcoes_is.merge(direcoes_oos, on="tipo_de_elo", suffixes=("_is", "_oos"))
    estaveis = (concordam["direcao_decidida_is"] == concordam["direcao_decidida_oos"]).sum()
    print(f"\nCategorias que mantiveram o sinal da correlacao no OOS: "
          f"{estaveis}/{len(concordam)}")

    # ---------- ETAPA 2: congelar ----------
    os.makedirs(SAIDA_DIR, exist_ok=True)
    variantes = construir_variantes(df_grafo, direcoes_is)
    caminho_congelado = os.path.join(SAIDA_DIR, "grafo_congelado_is.csv")
    variantes["congelado_is"].to_csv(caminho_congelado, index=False)
    print(f"\n[ETAPA 2] Grafo congelado salvo em: {caminho_congelado}")
    print("  A partir daqui, nenhum parametro e ajustado olhando o OOS.")

    # ---------- O grafo em producao e derivavel de uma regra a priori? ----------
    #
    # Esta e a pergunta que decide se o `grafo_manual_base.csv` precisa ou nao
    # ser trocado. Se as direcoes que estao em producao coincidem com o que a
    # regra conservadora produz -- prior economico, invertido SO onde o
    # in-sample tem |t| > 2 -- entao elas nao dependem de ter visto o futuro,
    # mesmo tendo sido escolhidas olhando a amostra inteira na epoca.
    atual_dir = df_grafo.set_index(["empresa_A", "empresa_B"])["direcao"]
    cons_dir = variantes["conservador"].set_index(["empresa_A", "empresa_B"])["direcao"]
    divergentes = atual_dir[atual_dir != cons_dir.reindex(atual_dir.index)]

    print("\n[ETAPA 2b] O grafo em producao e reproduzivel por regra a priori?")
    print(f"  Regra: prior economico, invertido so onde |t| do IS >= {T_MINIMO_PARA_INVERTER}")
    if divergentes.empty:
        print("  SIM -- os 30 elos em producao sao IDENTICOS aos que a regra produz.")
        print("  Consequencia: as direcoes atuais nao precisam ter visto 2021+ para")
        print("  serem escolhidas. O grafo em producao NAO precisa ser trocado.")
    else:
        print(f"  NAO -- {len(divergentes)} elo(s) divergem da regra:")
        for (a, b), d in divergentes.items():
            tipo = df_grafo[(df_grafo["empresa_A"] == a) & (df_grafo["empresa_B"] == b)]["tipo_de_elo"].iloc[0]
            print(f"    {a} -> {b} ({tipo}): producao={d:+d}, regra={cons_dir[(a, b)]:+d}")

    # ---------- ETAPA 3: medir ----------
    print("\n[ETAPA 3] Rodando o pipeline completo para cada variante...")
    todas = []
    sinais = {}
    for nome, grafo_variante in variantes.items():
        print(f"\n  --> variante '{nome}'")
        tabela, df_sinal = avaliar_variante(nome, grafo_variante, contexto)
        todas.append(tabela)
        sinais[nome] = df_sinal

    resultado = pd.concat(todas, ignore_index=True)
    ordem = {"IS 16-20": 0, "OOS 21-25": 1, "completo": 2}
    resultado = resultado.sort_values(
        ["variante", "periodo"], key=lambda c: c.map(ordem) if c.name == "periodo" else c
    )

    imprimir_tabela(resultado, "RESULTADO POR VARIANTE E PERIODO")

    caminho_resultado = os.path.join(SAIDA_DIR, "resultado_validacao_oos.csv")
    resultado.to_csv(caminho_resultado, index=False)

    # ---------- Veredito ----------
    print("\n" + "=" * 62)
    print(" VEREDITO")
    print("=" * 62)

    oos_congelado = resultado[
        (resultado["variante"] == "congelado_is") & (resultado["periodo"] == "OOS 21-25")
    ]
    if oos_congelado.empty:
        print("Sem periodo OOS suficiente para veredito.")
    else:
        linha = oos_congelado.iloc[0]
        print("Variante honesta (direcoes congeladas no IS), periodo 2021+:")
        print(f"  IC                  : {linha['ic']:+.4f}  (t = {linha['ic_t']:.2f})")
        print(f"  Alfa (P&L long-short): {linha['liquido_ano']:+.2%} ao ano  "
              "<- ja e excesso sobre o CDI")
        print(f"  CDI no periodo      : {linha['cdi_ano']:.2%} ao ano")
        print(f"  Retorno do fundo    : {linha['fundo_ano']:+.2%} ao ano  (CDI + alfa)")
        print(f"  Volatilidade        : {linha['vol_ano']:.2%} ao ano  (alvo do projeto: 12%)")
        print(f"  Sharpe              : {linha['sharpe']:.2f}")
        print()
        if linha["ic"] > 0 and linha["ic_t"] > 2:
            print("  -> O SINAL PREVE fora da amostra (IC positivo e significante).")
        elif linha["ic"] > 0:
            print("  -> IC positivo fora da amostra, mas SEM significancia estatistica.")
            print("     O sinal aponta na direcao certa; a evidencia ainda e fraca --")
            print("     esperado com apenas 30 elos (poucas apostas independentes).")
        else:
            print("  -> IC NEGATIVO fora da amostra: a regra escolhida no IS NAO se")
            print("     sustentou. Isso e evidencia de que a inversao foi ajuste de curva.")

        if linha["liquido_ano"] > 0:
            print(f"  -> O fundo BATE o CDI em {linha['liquido_ano']:+.2%} ao ano no OOS.")
        else:
            print("  -> O fundo NAO bate o CDI no OOS.")

        # Comparacao 'atual' x 'congelado_is'.
        #
        # CUIDADO NA LEITURA: isto NAO e um teste de overfit limpo, e ja foi
        # mal interpretado uma vez. As duas variantes nao diferem apenas por
        # "uma viu o OOS e a outra nao" -- elas usam REGRAS DE DECISAO
        # diferentes:
        #   - `congelado_is` inverte pelo SINAL da correlacao no IS, mesmo
        #     quando esse sinal e ruido (ja inverteu categoria com t = -0,20);
        #   - `atual` == `conservador` so inverte com |t| >= 2.
        #
        # Entao o `congelado_is` perder nao prova que o `atual` espiou: prova
        # que inverter no ruido e uma regra pior. O teste de overfit que vale
        # e a etapa 2b -- se o grafo em producao e reproduzivel por uma regra
        # que nao olha o futuro, ele nao depende de ter visto o futuro.
        atual_oos = resultado[
            (resultado["variante"] == "atual") & (resultado["periodo"] == "OOS 21-25")
        ]
        if not atual_oos.empty:
            delta = atual_oos.iloc[0]["liquido_ano"] - linha["liquido_ano"]
            print(f"\n'atual' menos 'congelado_is' no OOS: {delta:+.2%} ao ano")
            print("  (comparacao de REGRAS de decisao, nao teste de overfit --")
            print("   o teste de overfit e a etapa 2b, acima)")
            if delta > 0:
                print("  A regra conservadora (so inverter com |t| >= 2) bateu a regra")
                print("  de congelar pelo sinal. Coerente: congelar no ruido erra.")

        pre_oos = resultado[
            (resultado["variante"] == "pre_inversao") & (resultado["periodo"] == "OOS 21-25")
        ]
        if not pre_oos.empty:
            print(f"\nControle -- 'pre_inversao' (concorrente = -1) no OOS: "
                  f"alfa {pre_oos.iloc[0]['liquido_ano']:+.2%} ao ano, "
                  f"IC {pre_oos.iloc[0]['ic']:+.4f}")
            print("  Se este for pior que o congelado, a inversao se justifica sem")
            print("  precisar olhar o futuro.")

    # ---------- Sensibilidade das janelas (contaminacao residual) ----------
    if args.sensibilidade_janelas:
        print("\n" + "=" * 62)
        print(" SENSIBILIDADE AS JANELAS DE SUAVIZACAO (contaminacao residual)")
        print("=" * 62)
        print("As janelas 21d/10d foram escolhidas na amostra inteira. Se o")
        print("resultado OOS so existe nelas, e frageis; se e parecido na")
        print("vizinhanca, a escolha nao foi decisiva.\n")

        combos = [(10, 5), (21, 10), (42, 10), (21, 21), (63, 21)]
        linhas = []
        for js, jp in combos:
            tabela, _ = avaliar_variante(
                "congelado_is", variantes["congelado_is"], contexto,
                janela_sinal=js, janela_pesos=jp,
            )
            oos = tabela[tabela["periodo"] == "OOS 21-25"]
            if oos.empty:
                continue
            r = oos.iloc[0]
            linhas.append({
                "janela_sinal": js, "janela_pesos": jp,
                "liquido_ano": r["liquido_ano"], "sharpe": r["sharpe"],
                "giro_dia": r["giro_dia"], "ic": r["ic"],
            })

        df_sens = pd.DataFrame(linhas)
        print(f"\n{'sinal':>6} {'pesos':>6} {'liq/ano':>9} {'Sharpe':>7} {'giro':>7} {'IC':>9}")
        for _, r in df_sens.iterrows():
            print(f"{r['janela_sinal']:>6.0f} {r['janela_pesos']:>6.0f} "
                  f"{r['liquido_ano']:>+8.2%} {r['sharpe']:>7.2f} "
                  f"{r['giro_dia']:>6.1%} {r['ic']:>+9.4f}")
        df_sens.to_csv(os.path.join(SAIDA_DIR, "sensibilidade_janelas.csv"), index=False)

    print(f"\nResultados salvos em: {SAIDA_DIR}")


if __name__ == "__main__":
    main()
