"""
Bloco 7: acervo visual do relatorio.

Gera graficos, tabelas e diagramas a partir dos artefatos do pipeline, em PNG
(300 dpi, proporcao 16:9) e em Markdown, prontos para colar no PPT.

PRINCIPIOS DE DESENHO (nao sao gosto, sao regras)
-------------------------------------------------
- Paleta categorica validada para daltonismo (protan/deutan/tritan). A ordem
  dos slots E o mecanismo de seguranca -- nao trocar por gosto.
- Um eixo por grafico. NUNCA eixo duplo: duas medidas de escala diferente
  viram dois graficos ou sao indexadas na mesma base.
- Marcas finas, grade recessiva, rotulo direto nas series (a cor nunca carrega
  a identidade sozinha).
- Texto em tinta neutra, nunca na cor da serie.

USO
---
    python "fase 7 - relatorio/src/r1_visuais.py"
    python "fase 7 - relatorio/src/r1_visuais.py" --apenas curva,drawdown
"""

import argparse
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
import pandas as pd
from matplotlib.ticker import FuncFormatter

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_DIR = os.path.join(BASE_DIR, "data")
SAIDA = os.path.join(BASE_DIR, "fase 7 - relatorio", "saida")
DIAS = 252
AUM = 100_000_000   # mesmo AUM do Bloco 3, exigido pelo modelo de custo

# ------------------------------------------------------------------
# Paleta (validada) e chrome
# ------------------------------------------------------------------
C = {
    "sinapse": "#2a78d6",   # slot 1 azul
    "ibov":    "#eb6834",   # slot 2 laranja
    "cdi":     "#1baf7a",   # slot 3 aqua
    "fundo":   "#4a3aa7",   # slot 7 violeta (distinto dos 3 acima)
    "neutro":  "#898781",
    "grade":   "#e1e0d9",
    "eixo":    "#c3c2b7",
    "tinta":   "#0b0b0b",
    "tinta2":  "#52514e",
    "surface": "#fcfcfb",
    "bom":     "#0ca30c",
    "ruim":    "#d03b3b",
}

plt.rcParams.update({
    "figure.facecolor": C["surface"],
    "axes.facecolor": C["surface"],
    "savefig.facecolor": C["surface"],
    "font.family": "sans-serif",
    "font.sans-serif": ["Segoe UI", "DejaVu Sans", "Arial"],
    "font.size": 11,
    "axes.edgecolor": C["eixo"],
    "axes.labelcolor": C["tinta2"],
    "axes.titlecolor": C["tinta"],
    "xtick.color": C["neutro"],
    "ytick.color": C["neutro"],
    "grid.color": C["grade"],
    "grid.linewidth": 0.8,
    "axes.grid": True,
    "axes.grid.axis": "y",
    "axes.spines.top": False,
    "axes.spines.right": False,
    "legend.frameon": False,
})

PCT = FuncFormatter(lambda v, _: f"{v:.0%}")
PCT1 = FuncFormatter(lambda v, _: f"{v:.1%}")


def fig169(w=12.8, h=7.2):
    return plt.subplots(figsize=(w, h), dpi=110)


# MODO DECK -------------------------------------------------------------
# O relatorio e o deck sao lidos de formas diferentes. No RelatorioRAW.md
# cada figura tem de se explicar sozinha, porque nao ha texto ao lado
# garantido. No deck de 5 paginas o slide JA da o contexto, e repetir o
# mesmo paragrafo dentro da imagem so gasta palavra (o edital pede ~750).
#
# `sub()` escolhe entre as duas versoes. A regra que seguimos: so encurta
# quando a informacao aparece em outro lugar do deck. Onde o subtitulo e a
# UNICA fonte de algo -- "escalas independentes" no drawdown, "2017 e
# parcial" no anual -- o texto curto continua dizendo aquilo.
DECK = False


def sub(longo, curto):
    return curto if DECK else longo


def salvar(fig, nome):
    destino = os.path.join(SAIDA, "deck") if DECK else SAIDA
    os.makedirs(destino, exist_ok=True)
    caminho = os.path.join(destino, f"{nome}.png")
    fig.savefig(caminho, dpi=300, bbox_inches="tight")
    plt.close(fig)
    print(f"  [png] {'deck/' if DECK else ''}{nome}")
    return caminho


def salvar_md(texto, nome):
    os.makedirs(SAIDA, exist_ok=True)
    caminho = os.path.join(SAIDA, f"{nome}.md")
    with open(caminho, "w", encoding="utf-8") as f:
        f.write(texto)
    print(f"  [md ] {nome}")
    return caminho


def titulo(ax, t, sub=None):
    """
    Titulo + subtitulo alinhados a esquerda, sem colisao.

    O subtitulo e ancorado em coordenadas de AXES (1.01) e o titulo recebe pad
    suficiente para caber acima dele. `n_linhas` cresce o pad quando o
    subtitulo quebra em varias linhas -- senao o titulo cai por cima.
    """
    if not sub:
        ax.set_title(t, fontsize=15, fontweight="600", loc="left", pad=10)
        return
    n_linhas = sub.count("\n") + 1
    ax.set_title(t, fontsize=15, fontweight="600", loc="left", pad=13 + 13 * n_linhas)
    ax.text(0, 1.012, sub, transform=ax.transAxes, fontsize=10,
            color=C["tinta2"], va="bottom", linespacing=1.45)


def rotulo_direto(ax, x, y, texto, cor, dx=6):
    ax.annotate(texto, xy=(x, y), xytext=(dx, 0), textcoords="offset points",
                color=cor, fontsize=11, fontweight="600", va="center")


# ==================================================================
# CARGA
# ==================================================================

def carregar():
    """
    Recalcula o P&L a partir dos pesos, com os DOIS regimes de custo.

    POR QUE NAO BASTA LER `curvas_diarias.parquet`: aquele arquivo traz apenas
    o custo linear de 5 bps. Esse numero e de LARGE CAP LIQUIDA -- 79% do giro
    deste book esta abaixo de R$150MM de ADTV. Sob o custo realista (spread por
    faixa + impacto + aluguel BTC) o excesso sobre o CDI cai para menos da
    metade, e essa diferenca e o resultado mais importante do material.

    Nenhum numero fica escrito aqui de proposito: as duas leituras sao
    recalculadas a cada execucao e o texto dos graficos e tabelas e formatado a
    partir delas. Numero em docstring vira mentira na rodada seguinte.
    """
    import sys
    sys.path.insert(0, os.path.join(BASE_DIR, "fase 3 - backtest", "src"))
    import s3b_custos

    d = {}
    d["curvas"] = pd.read_parquet(os.path.join(DATA_DIR, "backtest", "curvas_diarias.parquet"))
    d["pesos"] = pd.read_parquet(os.path.join(DATA_DIR, "df_weights_sinapse.parquet"))
    d["sinal"] = pd.read_parquet(os.path.join(DATA_DIR, "sinal_sinapse.parquet"))
    d["retornos"] = pd.read_parquet(os.path.join(DATA_DIR, "precos", "retornos_diarios_completo.parquet"))
    d["cdi"] = pd.read_parquet(os.path.join(DATA_DIR, "precos", "cdi_diario.parquet"))["CDI"]
    d["adtv"] = pd.read_parquet(os.path.join(DATA_DIR, "universo", "adtv_diario.parquet"))
    caminho_grafo = os.path.join(DATA_DIR, "grafo_regra_mensal.parquet")
    d["grafo"] = pd.read_parquet(caminho_grafo) if os.path.exists(caminho_grafo) else None

    ibov = pd.read_parquet(os.path.join(DATA_DIR, "precos", "indices_retornos.parquet"))["IBOV"]
    R = d["retornos"].copy()
    R["IBOV_SYNTHETIC"] = ibov.reindex(R.index)
    R = R.loc[~R["IBOV_SYNTHETIC"].isna()]      # mesma protecao do Bloco 3

    datas = d["pesos"].index.intersection(R.index)
    W = d["pesos"].loc[datas].sort_index()
    R = R.loc[datas].sort_index()

    d["bruto"] = (W.fillna(0) * R.fillna(0)).sum(axis=1)
    d["giro"] = W.fillna(0).diff().abs().sum(axis=1)

    custo_real, comp = s3b_custos.custo_por_dia(W, d["adtv"], R, AUM)
    d["custo_real"] = custo_real.reindex(d["bruto"].index).fillna(0.0)
    d["comp_custo"] = comp
    d["custo_flat"] = d["giro"] * 0.0005

    # As duas leituras, no MESMO indice de datas (o desalinhamento entre
    # `pesos` e `giro` era a origem do "33,6 bps" -- o correto e 32,2).
    d["r_flat"] = d["bruto"] - d["custo_flat"]
    d["r_real"] = d["bruto"] - d["custo_real"]
    # NAO recriar um alias generico tipo `r_estrategia`. Existia um, apontando
    # silenciosamente para os 5 bps, e cinco graficos o usaram achando que era "o
    # retorno da estrategia" -- enquanto as tabelas mostravam o custo realista.
    # Cada grafico agora nomeia a premissa que esta usando: `r_flat` ou `r_real`.

    d["r_ibov"] = ibov.reindex(datas).fillna(0.0)
    d["r_cdi"] = d["cdi"].reindex(datas).fillna(0.0)
    d["r_fundo"] = d["r_flat"] + d["r_cdi"]
    d["r_fundo_real"] = d["r_real"] + d["r_cdi"]

    # Periodo ATIVO: antes de mai/2017 nao ha posicao (aquecimento de 252d de
    # regressao + 231d de acumulacao). Incluir esses dias dilui a vol e o
    # Sharpe artificialmente.
    ativo = (W.abs().sum(axis=1) > 1e-9)
    d["primeiro_ativo"] = ativo.idxmax()
    d["mask_ativo"] = ativo

    # JANELA UNICA DO MATERIAL. Todo grafico e toda tabela usam ESTE indice.
    # A versao anterior deixava cada funcao escolher: as tabelas filtravam pelo
    # periodo ativo, os graficos plotavam o painel inteiro desde 2016. O mesmo
    # Ibovespa aparecia +161,6% na tabela e +282% no grafico -- material que se
    # contradiz sozinho e a primeira coisa que uma banca encontra.
    d["idx_ativo"] = ativo[ativo].index
    d["pesos_ativo"] = W.loc[d["idx_ativo"]]
    return d


def ativo(d, s):
    """Recorta qualquer serie/tabela para a janela ativa do material."""
    return s.loc[s.index.intersection(d["idx_ativo"])]


# ==================================================================
# METRICAS
# ==================================================================

def metricas(r, rf=None):
    r = r.dropna()
    if len(r) < 20:
        return {}
    curva = (1 + r).cumprod()
    anos = len(r) / DIAS
    ret_tot = curva.iloc[-1] - 1
    ret_ano = (1 + ret_tot) ** (1 / anos) - 1
    vol = r.std() * np.sqrt(DIAS)
    exc = r if rf is None else r - rf.reindex(r.index).fillna(0)
    sharpe = exc.mean() / exc.std() * np.sqrt(DIAS) if exc.std() > 0 else np.nan
    down = exc[exc < 0].std()
    sortino = exc.mean() / down * np.sqrt(DIAS) if down and down > 0 else np.nan
    dd = (curva / curva.cummax() - 1)
    mdd = dd.min()
    calmar = ret_ano / abs(mdd) if mdd < 0 else np.nan
    return {
        "retorno_total": ret_tot, "retorno_ano": ret_ano, "vol": vol,
        "sharpe": sharpe, "sharpe_diario": exc.mean() / exc.std() if exc.std() > 0 else np.nan,
        "sortino": sortino, "mdd": mdd, "calmar": calmar,
        "dias": len(r), "anos": anos,
    }


# ==================================================================
# 1. CURVA DE RETORNO ACUMULADO
# ==================================================================

def g_curva(d):
    """
    Dois paineis, uma premissa de custo em cada.

    BUG CORRIGIDO (16/08): a versao anterior plotava o periodo COMPLETO
    enquanto as tabelas usavam o periodo ATIVO -- o Ibovespa aparecia +282% no
    grafico e +161,6% na tabela. Toda serie aqui usa a MESMA janela das
    tabelas, senao o material se contradiz.
    """
    a = d["mask_ativo"].values
    def cum(s):
        s = s[a]
        return (1 + s).cumprod() - 1

    paineis = [
        ("01a_retorno_acumulado_5bps",
         "Retorno acumulado: premissa usual de mercado (5 bps por unidade de giro)",
         sub("Custo linear de 5 bps sobre o giro: a convenção de backtest da indústria, "
             "calibrada para large cap líquida.\nA Sinapse é market-neutral: o produto "
             "entregue ao cotista é CDI + alfa. O Ibovespa é referência de descorrelação, não meta.",
             None),
         [("Fundo (CDI + Sinapse)", cum(d["r_fundo"]), C["fundo"], 2.8),
          ("Ibovespa", cum(d["r_ibov"]), C["ibov"], 2.1),
          ("CDI", cum(d["r_cdi"]), C["cdi"], 2.1),
          ("Sinapse (alfa)", cum(d["r_flat"]), C["sinapse"], 2.8)]),
        ("01b_retorno_acumulado_realista",
         "Retorno acumulado: custo realista (o número que defendemos)",
         sub("Meio-spread por faixa de ADTV + impacto de mercado + aluguel (BTC) da ponta vendida. "
             "79% do giro deste book\nestá abaixo de R$ 150 MM de ADTV: onde os 5 bps do painel "
             "anterior deixam de valer. Mesma carteira, mesmo sinal, mesmo período.",
             None),
         [("Fundo (CDI + Sinapse)", cum(d["r_fundo_real"]), C["fundo"], 2.8),
          ("Ibovespa", cum(d["r_ibov"]), C["ibov"], 2.1),
          ("CDI", cum(d["r_cdi"]), C["cdi"], 2.1),
          ("Sinapse (alfa)", cum(d["r_real"]), C["sinapse"], 2.8)]),
    ]

    # Escala Y COMPARTILHADA entre as duas imagens. Sao dois arquivos separados,
    # mas o leitor vai compara-los lado a lado -- eixos diferentes fariam a queda
    # sob custo realista parecer menor do que e.
    topo = max(s.max() for _, _, _, ss in paineis for _, s, _, _ in ss)

    caminhos = []
    for nome_arq, tit, subt, series in paineis:      # `subt`: `sub` e a funcao do modo deck
        fig, ax = fig169(12.8, 6.6)
        for nome, s, cor, lw in series:
            ax.plot(s.index, s.values, color=cor, linewidth=lw, label=nome,
                    solid_capstyle="round")
            rotulo_direto(ax, s.index[-1], s.iloc[-1],
                          f" {nome.split(' (')[0]} {s.iloc[-1]:+.0%}", cor)
        ax.axhline(0, color=C["eixo"], linewidth=1)
        ax.yaxis.set_major_formatter(PCT)
        ax.set_ylim(-0.12, topo * 1.10)
        ax.margins(x=0.16)
        ax.legend(loc="upper left", fontsize=10.5)
        titulo(ax, tit, subt)
        caminhos.append(salvar(fig, nome_arq))
    return caminhos[-1]


# ==================================================================
# 2. DRAWDOWN
# ==================================================================

def g_drawdown(d):
    """
    Painéis separados em vez de sobrepostos.

    Sobrepor Sinapse (−18%) e Ibovespa (−47%) no mesmo eixo esmaga a primeira
    contra o zero e torna a comparação ilegível. Painéis empilhados com escalas
    próprias mostram a FORMA de cada um; a comparação de magnitude fica na
    anotação, que é onde ela pertence.
    """
    a = d["mask_ativo"]
    # O CDI nao entra: por construcao ele nunca tem drawdown, e um painel reto
    # em zero rouba um terco do grafico para nao dizer nada. Fica na legenda.
    series = [("Sinapse", d["r_real"][a], C["sinapse"]),
              ("Ibovespa", d["r_ibov"][a], C["ibov"])]

    fig, axes = plt.subplots(2, 1, figsize=(12.8, 7.0), dpi=110, sharex=True,
                             gridspec_kw={"hspace": 0.30})
    minimos = {}
    for ax, (nome, r, cor) in zip(axes, series):
        c = (1 + r).cumprod()
        dd = c / c.cummax() - 1
        minimos[nome] = dd.min()
        ax.fill_between(dd.index, dd.values, 0, color=cor, alpha=0.22)
        ax.plot(dd.index, dd.values, color=cor, linewidth=1.6)
        ax.axhline(0, color=C["eixo"], linewidth=1)
        ax.yaxis.set_major_formatter(PCT)
        ax.set_ylim(dd.min() * 1.32, dd.max() * 0.02 if dd.max() > 0 else 0.004)

        # marca o vale, com rotulo que nao colide com a curva
        ax.plot([dd.idxmin()], [dd.min()], marker="o", markersize=9, color=cor,
                markerfacecolor=C["surface"], markeredgewidth=2.4, zorder=5)
        ax.annotate(f"{dd.min():.1%}", xy=(dd.idxmin(), dd.min()), xytext=(10, 4),
                    textcoords="offset points", fontsize=12, fontweight="700", color=cor)
        ax.text(0.998, 0.08, nome, transform=ax.transAxes, ha="right", fontsize=13,
                fontweight="700", color=cor)

    razao = minimos["Ibovespa"] / minimos["Sinapse"]
    axes[0].set_title("Drawdown: quanto se perde do topo anterior",
                      fontsize=15, fontweight="600", loc="left", pad=46)
    axes[0].text(0, 1.02, sub(f"Escalas independentes, para que a FORMA de cada série seja legível. "
                              f"O pior momento do Ibovespa é {razao:.1f}× o da Sinapse.\n"
                              "O CDI não aparece porque, por construção, nunca tem drawdown.",
                              "Escalas independentes: compare a FORMA, não a altura."),
                 transform=axes[0].transAxes, fontsize=10, color=C["tinta2"],
                 va="bottom", linespacing=1.45)
    return salvar(fig, "02_drawdown")


# ==================================================================
# 3. PERFORMANCE ANUAL
# ==================================================================

def g_anual(d):
    """Barras agrupadas com valor em TODAS as barras, e só anos com posição."""
    a = d["mask_ativo"]
    anos = [y for y in sorted(set(d["r_real"].index.year))
            if a[a.index.year == y].sum() > 20]
    # Janela ativa nas TRES series. Sem isso, 2017 comparava 7,5 meses de
    # Sinapse contra 12 meses de CDI e de Ibovespa -- e a barra do CDI de 2017
    # no grafico (+9,8%) nao batia com a da tabela (+5,2%).
    fontes = [("Sinapse", ativo(d, d["r_real"]), C["sinapse"]),
              ("Ibovespa", ativo(d, d["r_ibov"]), C["ibov"]),
              ("CDI", ativo(d, d["r_cdi"]), C["cdi"])]
    dados = {n: [(1 + r[r.index.year == y]).prod() - 1 for y in anos] for n, r, _ in fontes}

    fig, ax = fig169(13.4, 6.8)
    x = np.arange(len(anos)); w = 0.27
    for i, (nome, _, cor) in enumerate(fontes):
        pos = x + (i - 1) * w
        ax.bar(pos, dados[nome], w * 0.88, label=nome, color=cor,
               edgecolor=C["surface"], linewidth=1.6, zorder=3)
        # valor em TODAS as barras, com fonte menor nas de referencia
        for xi, v in zip(pos, dados[nome]):
            ax.annotate(f"{v:+.0%}" if abs(v) >= 0.10 else f"{v:+.1%}",
                        (xi, v), textcoords="offset points",
                        xytext=(0, 5 if v >= 0 else -14), ha="center",
                        fontsize=9.5 if nome == "Sinapse" else 8,
                        fontweight="700" if nome == "Sinapse" else "500",
                        color=cor if nome == "Sinapse" else C["neutro"], zorder=4)

    # Faixa de destaque nos anos que DE FATO carregam o resultado -- medido, nao
    # escolhido. A versao anterior marcava 2019-2021 fixo, mas 2019 rendeu so
    # +2,9%: os dois melhores anos sozinhos ja somam mais que o total do periodo.
    ordem = sorted(range(len(anos)), key=lambda j: dados["Sinapse"][j], reverse=True)
    top = sorted(ordem[:2])
    soma_top = sum(dados["Sinapse"][j] for j in top)
    total = np.prod([1 + v for v in dados["Sinapse"]]) - 1
    for j in top:
        ax.axvspan(j - 0.5, j + 0.5, color=C["sinapse"], alpha=0.06, zorder=0)
    rotulo = ("–".join(str(anos[j]) for j in top) if top[1] - top[0] == 1
              else " e ".join(str(anos[j]) for j in top))
    ax.annotate(f"{rotulo} sozinhos somam {soma_top:+.0%}, mais que os {total:+.0%} "
                "de todo o período",
                xy=((top[0] + top[1]) / 2, max(dados["Sinapse"]) * 1.30),
                ha="center", fontsize=10, color=C["sinapse"], fontweight="700")

    ax.set_xticks(x); ax.set_xticklabels(anos, fontsize=11.5)
    ax.axhline(0, color=C["tinta"], linewidth=1.4, zorder=2)
    ax.yaxis.set_major_formatter(PCT)
    ax.set_ylim(min(min(v) for v in dados.values()) * 1.35,
                max(max(v) for v in dados.values()) * 1.30)
    ax.set_axisbelow(True)
    # Contagem MEDIDA. A versao anterior afirmava "5 dos 9 anos" -- sobra de
    # antes da correcao de calendario, e o proprio relatorio ja dizia 3.
    neg = sum(1 for v in dados["Sinapse"] if v < 0)
    pior = anos[int(np.argmin(dados["Sinapse"]))]
    melhor = anos[int(np.argmax(dados["Sinapse"]))]
    titulo(ax, "Retorno por ano: alfa da Sinapse com custo realista",
           sub(f"O melhor ano da Sinapse ({melhor}) foi um dos piores do Ibovespa; o pior dela ({pior}) "
               "foi um dos melhores dele.\n"
               f"Isso é descorrelação. Mas {neg} dos {len(anos)} anos são negativos com custo real, "
               f"e {anos[0]} é parcial (a estratégia só tem posição a partir de {d['primeiro_ativo']:%d/%m}).",
               f"{anos[0]} é parcial: há posição só a partir de {d['primeiro_ativo']:%d/%m}."))
    ax.legend(loc="upper left", ncol=3, fontsize=10.5)
    return salvar(fig, "03_performance_anual")


# ==================================================================
# 4. GIRO E NUMERO DE POSICOES
# ==================================================================

def g_giro(d):
    w = ativo(d, d["pesos"])          # janela unica: media de giro tem que bater com a tabela
    acoes = [c for c in w.columns if c != "IBOV_SYNTHETIC"]
    n_pos = (w[acoes].abs() > 1e-6).sum(axis=1)
    giro = ativo(d, d["giro"])

    fig, (a1, a2) = plt.subplots(2, 1, figsize=(12.8, 7.2), dpi=110, sharex=True,
                                 gridspec_kw={"hspace": 0.28})
    m = n_pos.resample("ME").mean()
    a1.fill_between(m.index, m.values, color=C["sinapse"], alpha=0.16)
    a1.plot(m.index, m.values, color=C["sinapse"], linewidth=2)
    a1.set_ylabel("ações na carteira")
    titulo(a1, "Número de ações na carteira, por mês",
           f"Mediana de {n_pos.median():.0f} nomes por pregão (média {n_pos.mean():.0f}). "
           "A carteira cresce com o universo elegível: mais ações passam no filtro de liquidez\n"
           "ao longo do período. Atenção: 134 posições NÃO são 134 apostas — a breadth "
           "efetiva medida é 16,1 (ver inferência).")

    g = giro.resample("ME").mean()
    a2.fill_between(g.index, g.values, color=C["ibov"], alpha=0.16)
    a2.plot(g.index, g.values, color=C["ibov"], linewidth=2)
    a2.axhline(giro.mean(), color=C["neutro"], linestyle="--", linewidth=1.2)
    a2.annotate(f"média {giro.mean():.2%}/dia", (g.index[3], giro.mean()),
                xytext=(0, 8), textcoords="offset points", color=C["tinta2"], fontsize=10,
                fontweight="600")
    a2.yaxis.set_major_formatter(PCT1)
    a2.set_ylabel("giro diário")
    titulo(a2, "Giro diário (soma das mudanças absolutas de peso)")
    return salvar(fig, "04_giro_e_posicoes")


# ==================================================================
# 5. IC POR HORIZONTE -- a evidencia central da tese
# ==================================================================

def g_horizonte(d):
    sig, r = d["sinal"], d["retornos"]
    cols = [c for c in sig.columns if c in r.columns]
    hs = [1, 5, 10, 21, 42, 63, 126]
    ics, ts = [], []
    for h in hs:
        fwd = r[cols].reindex(sig.index).rolling(h).sum().shift(-h)
        v = sig[cols].corrwith(fwd, axis=1).dropna()
        ics.append(v.mean())
        ts.append(v.mean() / (v.std() / np.sqrt(len(v) / h)))

    fig, (a1, a2) = plt.subplots(1, 2, figsize=(12.8, 5.6), dpi=110,
                                 gridspec_kw={"wspace": 0.26})
    a1.plot(hs, ics, color=C["sinapse"], linewidth=2.4, marker="o", markersize=8,
            markerfacecolor=C["surface"], markeredgewidth=2)
    a1.set_xlabel("horizonte de previsão (pregões)")
    a1.set_ylabel("IC")
    a1.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:.3f}"))
    titulo(a1, "O IC cresce com o horizonte", "Se o efeito fosse de 1 dia, alongar o horizonte o diluiria.")

    # Duas referencias tornam o grafico interpretavel, em vez de exigir fe:
    #   - efeito de 1 DIA que nao acumula: IC fica constante, IC/sqrt(h) cai como 1/sqrt(h)
    #   - difusao PERFEITA: IC cresce com sqrt(h), IC/sqrt(h) fica horizontal
    # O medido fica muito mais perto da segunda que da primeira -- e e isso, e
    # so isso, que o grafico afirma.
    norm = [i / np.sqrt(h) for i, h in zip(ics, hs)]
    um_dia = [norm[0] / np.sqrt(h) for h in hs]

    a2.plot(hs, norm, color=C["fundo"], linewidth=2.4, marker="o", markersize=8,
            markerfacecolor=C["surface"], markeredgewidth=2, label="medido", zorder=3)
    a2.axhline(norm[0], color=C["bom"], linestyle="--", linewidth=1.6,
               label="difusão perfeita (horizontal)")
    a2.plot(hs, um_dia, color=C["ruim"], linestyle=":", linewidth=1.8,
            label="efeito de 1 dia (não acumula)")
    a2.set_xlabel("horizonte de previsão (pregões)")
    a2.set_ylabel("IC / √h")
    a2.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:.4f}"))
    a2.set_ylim(0, norm[0] * 1.42)      # espaco para a legenda nao colidir com a referencia
    a2.legend(fontsize=9.5, loc="upper right")
    queda_med = 1 - norm[-1] / norm[0]
    queda_1d = 1 - um_dia[-1] / um_dia[0]
    titulo(a2, "O sinal acumula — quase como difusão pura",
           f"De T+1 a T+126, IC/√h cai {queda_med:.0%}. Um efeito de um dia só cairia {queda_1d:.0%}.\n"
           "O sinal está muito mais perto de difusão que de choque instantâneo — mas não é perfeito.")

    salvar(fig, "05_ic_por_horizonte")
    linhas = ["| horizonte | IC | t | IC/√h |", "|---|---|---|---|"]
    for h, i, t in zip(hs, ics, ts):
        linhas.append(f"| T+{h} | {i:+.4f} | {t:.2f} | {i/np.sqrt(h):.4f} |")
    return salvar_md("\n".join(linhas), "05_ic_por_horizonte")


# ==================================================================
# 6. EXPOSICOES
# ==================================================================

def g_exposicao(d):
    w = ativo(d, d["pesos"])
    acoes = [c for c in w.columns if c != "IBOV_SYNTHETIC"]
    W = w[acoes].fillna(0)
    lg = W.clip(lower=0).sum(axis=1).resample("ME").mean()
    sh = W.clip(upper=0).sum(axis=1).resample("ME").mean()
    net = (lg + sh)
    hedge = w["IBOV_SYNTHETIC"].fillna(0).resample("ME").mean()

    # A linha que realmente importa -- e que faltava. A perna de acoes sozinha
    # NAO e dollar-neutral: ela oscila dezenas de pontos. E o hedge de indice
    # que traz o book de volta ao zero. Afirmar "dollar-neutral por construcao"
    # ao lado de uma linha que vai de +40% a -45% e uma contradicao visivel.
    total = net + hedge

    fig, ax = fig169(12.8, 6.6)
    ax.fill_between(lg.index, lg.values, 0, color=C["sinapse"], alpha=0.30, label="comprado (long)")
    ax.fill_between(sh.index, sh.values, 0, color=C["ibov"], alpha=0.30, label="vendido (short)")
    ax.plot(net.index, net.values, color=C["neutro"], linewidth=1.5, linestyle="-",
            label="líquida — só ações")
    ax.plot(hedge.index, hedge.values, color=C["cdi"], linewidth=1.6, linestyle="--",
            label="hedge de Ibovespa")
    ax.plot(total.index, total.values, color=C["tinta"], linewidth=2.6,
            label="líquida TOTAL (ações + hedge)", zorder=4)
    ax.axhline(0, color=C["eixo"], linewidth=1.2)
    ax.yaxis.set_major_formatter(PCT)
    titulo(ax, "Exposição da carteira — e por que a neutralidade não é automática",
           f"A perna de ações sozinha NÃO é dollar-neutral: ela oscila entre {net.quantile(.05):+.0%} "
           f"e {net.quantile(.95):+.0%} (faixa de 90%).\n"
           f"É o hedge de índice que fecha a conta: a líquida TOTAL fica entre "
           f"{total.quantile(.05):+.0%} e {total.quantile(.95):+.0%}, média {total.mean():+.1%}. "
           f"Exposição bruta média {(lg - sh).mean():.0%}.")
    ax.legend(loc="upper left", ncol=2, fontsize=9.5)
    return salvar(fig, "06_exposicoes")


# ==================================================================
# 7. HEATMAP DE RETORNOS MENSAIS
# ==================================================================

def g_heatmap(d):
    # Custo REALISTA: e o numero que o relatorio defende como o correto. Mostrar
    # o mes a mes na premissa otimista de 5 bps e escolher a vitrine.
    r = ativo(d, d["r_real"])
    m = (1 + r).resample("ME").prod() - 1
    tab = m.groupby([m.index.year, m.index.month]).first().unstack()
    tab = tab.reindex(columns=range(1, 13))

    fig, ax = plt.subplots(figsize=(12.8, 5.2), dpi=110)
    lim = np.nanmax(np.abs(tab.to_numpy()))
    im = ax.imshow(tab.to_numpy(), cmap="RdBu", vmin=-lim, vmax=lim, aspect="auto")
    ax.set_xticks(range(12))
    ax.set_xticklabels(["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"])
    ax.set_yticks(range(len(tab.index)))
    ax.set_yticklabels(tab.index)
    ax.grid(False)
    for i in range(tab.shape[0]):
        for j in range(12):
            v = tab.iloc[i, j]
            if pd.notna(v):
                ax.text(j, i, f"{v*100:+.1f}", ha="center", va="center", fontsize=8,
                        color=C["tinta"] if abs(v) < lim * 0.55 else "white")
    titulo(ax, "Retorno mensal do alfa, com custo realista (%)",
           "Vermelho = mês negativo · Azul = mês positivo")
    fig.colorbar(im, ax=ax, shrink=0.7, format=FuncFormatter(lambda v, _: f"{v:.0%}"))
    return salvar(fig, "07_heatmap_mensal")


# ==================================================================
# 8. ROLLING SHARPE E VOL
# ==================================================================

def g_rolling(d):
    r = ativo(d, d["r_real"])
    sh = r.rolling(DIAS).mean() / r.rolling(DIAS).std() * np.sqrt(DIAS)
    vol = r.rolling(63).std() * np.sqrt(DIAS)

    fig, (a1, a2) = plt.subplots(2, 1, figsize=(12.8, 7.8), dpi=110, sharex=True,
                                 gridspec_kw={"hspace": 0.46})
    a1.plot(sh.index, sh.values, color=C["sinapse"], linewidth=1.8)
    a1.fill_between(sh.index, sh.values, 0, where=sh.values >= 0, color=C["sinapse"], alpha=0.14)
    a1.fill_between(sh.index, sh.values, 0, where=sh.values < 0, color=C["ibov"], alpha=0.14)
    a1.axhline(0, color=C["eixo"], linewidth=1.2)
    a1.set_ylabel("Sharpe 252d")
    titulo(a1, "Sharpe móvel de 252 pregões (custo realista)",
           "Mostra que o resultado não é estável — e onde ele veio de fato.")

    a2.plot(vol.index, vol.values, color=C["fundo"], linewidth=1.8)
    a2.axhline(0.12, color=C["ruim"], linestyle="--", linewidth=1.4)
    a2.annotate("teto do mandato: 12%", (vol.index[10], 0.12), xytext=(0, 6),
                textcoords="offset points", color=C["ruim"], fontsize=10, fontweight="600")
    a2.axhline(vol.median(), color=C["neutro"], linestyle=":", linewidth=1.2)
    # A direita: a esquerda a curva sobe do zero e passa por cima do rotulo.
    a2.annotate(f"mediana {vol.median():.1%}", (1.0, vol.median()),
                xycoords=("axes fraction", "data"), xytext=(-4, 7),
                textcoords="offset points", ha="right", color=C["tinta2"],
                fontsize=10, fontweight="600")
    a2.yaxis.set_major_formatter(PCT)
    a2.set_ylabel("vol 63d")
    titulo(a2, "Volatilidade móvel contra o teto de mandato",
           f"Utilização do orçamento de risco ≈ {vol.median()/0.12:.0%} (mediana {vol.median():.2%} "
           f"contra teto de 12%). O pico de {vol.idxmax():%Y} chega a {vol.max():.2%}:\n"
           "é limitação do estimador de covariância em regime de stress, e está declarado — "
           f"{(vol.dropna() > 0.12).mean():.1%} dos pregões passam do teto.")
    return salvar(fig, "08_rolling_sharpe_vol")


# ==================================================================
# 9. DISTRIBUICAO E NEUTRALIDADE
# ==================================================================

def g_distribuicao(d):
    r, ib = ativo(d, d["r_real"]), ativo(d, d["r_ibov"])
    idx = r.index.intersection(ib.index)

    fig, (a1, a2) = plt.subplots(1, 2, figsize=(12.8, 5.6), dpi=110,
                                 gridspec_kw={"wspace": 0.24})
    a1.hist(r * 100, bins=70, color=C["sinapse"], alpha=0.75, edgecolor=C["surface"])
    a1.axvline(0, color=C["eixo"], linewidth=1.2)
    a1.axvline(r.mean() * 100, color=C["ruim"], linewidth=1.6)
    a1.set_xlabel("retorno diário (%)")
    a1.grid(axis="x")
    titulo(a1, "Distribuição dos retornos diários",
           f"assimetria {r.skew():+.2f} · curtose {r.kurtosis():+.2f}")

    a2.scatter(ib.loc[idx] * 100, r.loc[idx] * 100, s=7, alpha=0.28,
               color=C["sinapse"], edgecolors="none")
    z = np.polyfit(ib.loc[idx], r.loc[idx], 1)
    xs = np.linspace(ib.loc[idx].min(), ib.loc[idx].max(), 50)
    a2.plot(xs * 100, np.polyval(z, xs) * 100, color=C["ruim"], linewidth=2)
    a2.axhline(0, color=C["eixo"], linewidth=1); a2.axvline(0, color=C["eixo"], linewidth=1)
    a2.set_xlabel("retorno diário do Ibovespa (%)")
    a2.set_ylabel("retorno diário da Sinapse (%)")
    a2.grid(True)
    titulo(a2, "Neutralidade de mercado",
           f"beta {z[0]:+.3f} · correlação {ib.loc[idx].corr(r.loc[idx]):+.2f}: a nuvem não tem inclinação")
    return salvar(fig, "09_distribuicao_neutralidade")


# ==================================================================
# 10. FLUXOGRAMA DO PIPELINE
# ==================================================================

def g_fluxograma(_):
    """
    Três colunas, fluxo de cima para baixo dentro de cada uma e da esquerda
    para a direita entre elas. Setas nunca cruzam caixa nem texto.
    """
    fig, ax = plt.subplots(figsize=(13.4, 7.4), dpi=110)
    ax.set_xlim(0, 100); ax.set_ylim(0, 100); ax.axis("off"); ax.grid(False)

    LARG, ALT = 27.0, 17.5
    COL = {"A": 3.0, "B": 36.5, "C": 70.0}
    LIN = {1: 66.0, 2: 43.0, 3: 20.0}

    caixas = [
        (COL["A"], LIN[1], "1 · DADOS", C["neutro"],
         ["COTAHIST (B3) + yfinance", "543 tickers · 2016–2025", "sem viés de sobrevivência"]),
        (COL["A"], LIN[2], "2 · CHOQUE LIMPO", C["sinapse"],
         ["retorno = α + β·IBOV + ε", "regressão móvel de 252d", "ε = o que é da empresa"]),
        (COL["A"], LIN[3], "3 · HORIZONTE", C["sinapse"],
         ["acumula ε em 12–1 meses", "231 pregões, defasados 22", "difusão, não choque de 1 dia"]),
        (COL["B"], LIN[1], "4 · GRAFO MECÂNICO", C["fundo"],
         ["mensal, por subsetor", "cabeça = mais líquidos (ADTV)", "cabeça → todos, ex-self"]),
        (COL["B"], LIN[2], "5 · PROPAGAÇÃO", C["fundo"],
         ["sinal_B = Σ ε_A × força", "ensemble de 6 variantes", "winsoriza + z-score"]),
        (COL["B"], LIN[3], "6 · CARTEIRA", C["cdi"],
         ["vol-target 12% e travas", "suaviza pesos 63d", "hedge de beta · lag T+1"]),
        (COL["C"], LIN[2], "7 · BACKTEST", C["ibov"],
         ["P&L = Σ(peso × retorno)", "− custo em 3 camadas", "spread, impacto, aluguel"]),
        (COL["C"], LIN[3], "8 · VALIDAÇÃO", C["ibov"],
         ["walk-forward · placebo", "Deflated Sharpe", "atribuição de fator"]),
    ]
    for x, y, t, cor, itens in caixas:
        ax.add_patch(mpatches.FancyBboxPatch(
            (x, y), LARG, ALT, boxstyle="round,pad=0.5,rounding_size=1.4",
            linewidth=2.2, edgecolor=cor, facecolor=cor + "12", zorder=2))
        ax.text(x + 1.8, y + ALT - 4.4, t, fontsize=11.5, fontweight="700", color=cor, zorder=3)
        for k, linha in enumerate(itens):
            ax.text(x + 1.8, y + ALT - 8.6 - k * 3.9, linha, fontsize=9.3,
                    color=C["tinta2"], zorder=3)

    seta = dict(arrowstyle="-|>", color=C["neutro"], linewidth=2.0,
                mutation_scale=17, shrinkA=0, shrinkB=0)
    mx = {c: COL[c] + LARG / 2 for c in COL}
    caminhos = [
        ((mx["A"], LIN[1]), (mx["A"], LIN[2] + ALT)),          # 1 -> 2
        ((mx["A"], LIN[2]), (mx["A"], LIN[3] + ALT)),          # 2 -> 3
        ((COL["A"] + LARG, LIN[3] + ALT / 2), (COL["B"], LIN[2] + ALT / 2)),   # 3 -> 5
        ((mx["B"], LIN[1]), (mx["B"], LIN[2] + ALT)),          # 4 -> 5
        ((mx["B"], LIN[2]), (mx["B"], LIN[3] + ALT)),          # 5 -> 6
        ((COL["B"] + LARG, LIN[3] + ALT / 2), (COL["C"], LIN[2] + ALT / 2)),   # 6 -> 7
        ((mx["C"], LIN[2]), (mx["C"], LIN[3] + ALT)),          # 7 -> 8
    ]
    for a, b in caminhos:
        ax.annotate("", xy=b, xytext=a, arrowprops=seta, zorder=1)

    ax.text(0, 93, "Fluxo da estratégia — do dado bruto à posição executada",
            fontsize=16.5, fontweight="700", color=C["tinta"])
    ax.text(0, 87.5, "Cada bloco é um script independente e reexecutável. "
                     "O motor de backtest não decide nada: recebe a matriz de pesos pronta e multiplica por retornos.",
            fontsize=10.5, color=C["tinta2"])

    ax.add_patch(mpatches.FancyBboxPatch((3, 4), 95, 9.5,
                                         boxstyle="round,pad=0.5,rounding_size=1.2",
                                         linewidth=1.6, edgecolor=C["eixo"],
                                         facecolor=C["grade"] + "55", zorder=2))
    ax.text(5, 9.6, "Sem look-ahead em nenhum ponto (auditado):", fontsize=10.5,
            fontweight="700", color=C["tinta"], zorder=3)
    ax.text(5, 5.6, "o grafo do mês M usa ADTV até o fim de M−1  ·  o choque do dia t usa só dados ≤ t  ·  "
                    "a covariância exclui o próprio dia  ·  a decisão de t é executada em t+1",
            fontsize=9.6, color=C["tinta2"], zorder=3)
    return salvar(fig, "10_fluxograma_pipeline")


# ==================================================================
# 11. DIAGRAMA DA REGRA DO GRAFO
# ==================================================================

def g_regra(_):
    fig, ax = plt.subplots(figsize=(12.8, 7.2), dpi=110)
    ax.set_xlim(0, 100); ax.set_ylim(0, 100); ax.axis("off"); ax.grid(False)

    ax.text(0, 95, "Como o grafo é construído — sem nenhum julgamento humano",
            fontsize=16, fontweight="700", color=C["tinta"])
    ax.text(0, 90.5, "Exemplo: subsetor Siderurgia, um mês qualquer de 2018. O ranking usa apenas o volume dos 21 pregões ANTERIORES.",
            fontsize=10.5, color=C["tinta2"])

    nomes = [("GGBR4", 180, True), ("CSNA3", 120, True), ("USIM5", 95, False),
             ("GOAU4", 40, False), ("GGBR3", 8, False)]
    y0 = 74
    for i, (n, adtv, cabeca) in enumerate(nomes):
        y = y0 - i * 11
        cor = C["sinapse"] if cabeca else C["neutro"]
        ax.add_patch(mpatches.FancyBboxPatch((4, y), 15, 8, boxstyle="round,pad=0.4,rounding_size=1.2",
                                             linewidth=2.2 if cabeca else 1.4,
                                             edgecolor=cor, facecolor=cor + ("22" if cabeca else "0d")))
        ax.text(11.5, y + 4, n, fontsize=11.5, fontweight="700" if cabeca else "500",
                color=cor, ha="center", va="center")
        ax.barh(y + 4, adtv / 180 * 22, height=3.4, left=21, color=cor, alpha=0.55)
        ax.text(21 + adtv / 180 * 22 + 1.2, y + 4, f"R$ {adtv} M", fontsize=9.5,
                color=C["tinta2"], va="center")
        if cabeca:
            ax.text(1.5, y + 4, ">", fontsize=13, color=C["sinapse"], va="center")

    ax.text(4, 79, "ordenado por ADTV (21d)", fontsize=10, color=C["tinta2"], fontweight="600")
    ax.text(56, 79, "elos gerados", fontsize=10, color=C["tinta2"], fontweight="600")

    elos = ["GGBR4 → CSNA3", "GGBR4 → USIM5", "GGBR4 → GOAU4", "GGBR4 → GGBR3",
            "CSNA3 → GGBR4", "CSNA3 → USIM5", "CSNA3 → GOAU4", "CSNA3 → GGBR3"]
    for i, e in enumerate(elos):
        y = 74 - i * 6.2
        mutuo = e in ("GGBR4 → CSNA3", "CSNA3 → GGBR4")
        cor = C["fundo"] if mutuo else C["cdi"]
        ax.text(56, y + 2, e, fontsize=11, color=cor, fontweight="700" if mutuo else "500")
        if mutuo:
            ax.text(74, y + 2, "elo mútuo entre as cabeças", fontsize=9, color=C["fundo"], style="italic")

    ax.add_patch(mpatches.FancyBboxPatch((4, 6), 92, 13, boxstyle="round,pad=0.6,rounding_size=1.6",
                                         linewidth=2, edgecolor=C["fundo"], facecolor=C["fundo"] + "10"))
    ax.text(6, 15.5, "A peça central: a cabeça também RECEBE sinal (alvo = todos ex-self).",
            fontsize=11.5, fontweight="700", color=C["fundo"])
    ax.text(6, 8.5, "É isso que cria elos mútuos entre os nomes líquidos de cada ramo — VALE3↔CSNA3, PETR3↔PETR4, SUZB3↔KLBN11 —\n"
                    "exatamente a topologia que a equipe havia escrito à mão. A regra reproduz 38 dos 40 elos manuais (95%), todos mútuos.",
            fontsize=10, color=C["tinta2"], va="bottom", linespacing=1.6)
    return salvar(fig, "11_diagrama_regra_grafo")


# ==================================================================
# 12. DECOMPOSICAO DE CUSTO E BREAKEVEN
# ==================================================================

def g_custo(d):
    # Janela ativa: incluir o aquecimento (carteira zerada, custo zero) diluiria
    # o custo anualizado para baixo -- justamente o numero que o material usa
    # como sua evidencia mais desconfortavel.
    ano = ativo(d, d["comp_custo"]).mean() * DIAS * 100
    comp = {"spread + taxas": ano["spread_taxas"], "impacto de mercado": ano["impacto"],
            "aluguel (BTC)": ano["aluguel"], "hedge": ano["hedge"]}
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(12.8, 5.6), dpi=110,
                                 gridspec_kw={"wspace": 0.3, "width_ratios": [1.1, 1]})

    nomes = list(comp); vals = list(comp.values())
    cores = [C["sinapse"], C["ibov"], C["ruim"], C["neutro"]]
    a1.barh(nomes[::-1], vals[::-1], color=cores[::-1], height=0.6, edgecolor=C["surface"], linewidth=1.5)
    for i, v in enumerate(vals[::-1]):
        a1.text(v + 0.04, i, f"{v:.2f}%", va="center", fontsize=10.5, color=C["tinta2"], fontweight="600")
    a1.set_xlabel("% ao ano")
    a1.grid(axis="x"); a1.set_axisbelow(True)
    titulo(a1, "Custo real, decomposto",
           f"Total {sum(vals):.2f}% ao ano · aluguel da ponta vendida é "
           f"{comp['aluguel (BTC)']/sum(vals):.0%} do custo")   # mantido: o total só aparece aqui

    g = ativo(d, d["giro"]).mean()
    alfa = ativo(d, d["bruto"]).mean() / g * 1e4
    custo = ativo(d, d["custo_real"]).mean() / g * 1e4
    a2.bar(["alfa gerado", "custo pago"], [alfa, custo], color=[C["bom"], C["ruim"]],
           width=0.5, edgecolor=C["surface"], linewidth=2)
    for i, v in enumerate([alfa, custo]):
        a2.text(i, v + 0.7, f"{v:.1f} bps", ha="center", fontsize=13, fontweight="700", color=C["tinta"])
    a2.set_ylabel("bps por unidade de giro")
    a2.set_ylim(0, alfa * 1.28)
    titulo(a2, "O número que não depende da nossa calibragem",
           sub(f"Cada unidade de giro gera {alfa:.1f} bps de alfa bruto e paga {custo:.1f} bps de custo, "
               f"margem de {alfa-custo:.1f} bps.\nSe a banca achar nosso modelo de custo otimista ou "
               "pessimista, é esta margem que decide, e ela está na mesa.",
               None))
    return salvar(fig, "12_custo_e_breakeven")


# ==================================================================
# 13. TABELAS
# ==================================================================

def t_metricas(d):
    """
    A tabela principal do relatorio -- e ela precisa das DUAS leituras de custo.

    Publicar so a coluna de 5 bps seria o erro mais grave possivel: sob o custo
    que o proprio projeto argumenta ser o correto o excesso sobre o CDI cai para
    menos da metade. Os dois numeros vao lado a lado, sempre, e o veredito e
    formatado a partir do valor medido -- nunca escrito a mao.
    """
    a = d["mask_ativo"]
    # DUAS convencoes, rotuladas: `retorno/vol` (sem taxa livre) e SHARPE de
    # verdade (excesso sobre o CDI). Publicar retorno/vol sob o nome "Sharpe"
    # inflava a comparacao com o Ibovespa -- 0,551 em vez de 0,244 -- e era o
    # unico numero do material que mudava de definicao entre dois scripts.
    rf = d["r_cdi"]
    m = {
        "flat": metricas(d["r_flat"][a]),
        "real": metricas(d["r_real"][a]),
        "f_flat": metricas(d["r_fundo"][a]),
        "f_real": metricas(d["r_fundo_real"][a]),
        "ibo": metricas(d["r_ibov"][a]),
        "cdi": metricas(d["r_cdi"][a]),
    }
    sh_cdi = {
        "f_flat": metricas(d["r_fundo"][a], rf)["sharpe"],
        "f_real": metricas(d["r_fundo_real"][a], rf)["sharpe"],
        "ibo": metricas(d["r_ibov"][a], rf)["sharpe"],
    }
    cdi_tot = m["cdi"]["retorno_total"]

    linhas = [
        "| métrica | Sinapse<br>*(custo 5 bps)* | **Sinapse<br>*(custo realista)*** | Fundo<br>*(5 bps)* | **Fundo<br>*(realista)*** | Ibovespa | CDI |",
        "|---|---|---|---|---|---|---|"]
    campos = [("Retorno acumulado", "retorno_total", "{:+.1%}"),
              ("Retorno anualizado", "retorno_ano", "{:+.2%}"),
              ("Volatilidade anualizada", "vol", "{:.2%}"),
              ("Retorno / volatilidade", "sharpe", "{:.3f}"),
              ("Sortino", "sortino", "{:.2f}"),
              ("Drawdown máximo", "mdd", "{:.1%}"),
              ("Calmar", "calmar", "{:.2f}")]
    for rot, k, f in campos:
        vs = []
        for c in ["flat", "real", "f_flat", "f_real", "ibo", "cdi"]:
            v = m[c].get(k, np.nan)
            # Sharpe do proprio CDI nao significa nada -- fica em branco.
            if c == "cdi" and k in ("sharpe", "sortino", "calmar"):
                vs.append("—")
            else:
                vs.append(f.format(v) if pd.notna(v) else "—")
        linhas.append(f"| {rot} | " + " | ".join(vs) + " |")

    linhas.append(f"| **SHARPE** *(excesso sobre o CDI)* | — | — | "
                  f"**{sh_cdi['f_flat']:.3f}** | **{sh_cdi['f_real']:.3f}** | "
                  f"**{sh_cdi['ibo']:.3f}** | — |")

    exc_flat = m["f_flat"]["retorno_total"] - cdi_tot
    exc_real = m["f_real"]["retorno_total"] - cdi_tot
    linhas.append(f"| **Excesso sobre o CDI** | — | — | **{exc_flat:+.1%}** | "
                  f"**{exc_real:+.1%}** | {m['ibo']['retorno_total']-cdi_tot:+.1%} | — |")

    # O texto NAO pode ser escrito a mao. Na versao anterior a nota afirmava "a
    # estrategia nao bate o benchmark" logo ao lado do numero que ela mesma
    # imprimia (+40,0% sobre o CDI) -- sobra de uma rodada em que o excesso era
    # negativo. Conclusao codificada e conclusao que envelhece errado.
    veredito = (
        f"sob custo realista o fundo entrega **{exc_real:+.1%}** contra o CDI, com Sharpe "
        f"**{sh_cdi['f_real']:.3f}**. A estratégia **bate o benchmark**, mas por uma margem "
        "modesta: o Sharpe é da ordem do que um índice de ações entrega, com a diferença de "
        "que este resultado não depende da direção do mercado."
        if exc_real > 0 else
        f"sob custo realista o fundo entrega **{exc_real:+.1%}** contra o CDI. A estratégia "
        "**não bate o benchmark**. O que sobrevive é o mecanismo (ver placebo), não o "
        "retorno líquido."
    )
    nota = (f"\n\n> **Período:** {d['primeiro_ativo']:%d/%m/%Y} a "
            f"{d['idx_ativo'][-1]:%d/%m/%Y} ({len(d['idx_ativo'])} pregões) — antes disso não há "
            "posição (252 pregões de regressão + 231 de acumulação de aquecimento). "
            "**Todos os gráficos deste material usam exatamente esta janela.**\n\n"
            "> **As duas colunas de custo são obrigatórias.** `5 bps` é a premissa usual de "
            "backtest, calibrada para large cap líquida. `realista` aplica meio-spread por faixa "
            "de ADTV, impacto de mercado e aluguel (BTC) da ponta vendida — e **79% do giro deste "
            "book está abaixo de R$ 150 MM de ADTV**.\n\n"
            f"> **A leitura honesta:** {veredito}")
    return salvar_md("\n".join(linhas) + nota, "13_tabela_metricas_periodo")


def t_anual(d):
    # Janela ativa em TUDO. Com o painel completo, 2017 misturava 4,5 meses de
    # carteira vazia com 7,5 meses de operacao: aparecia com 69 acoes (metade da
    # media real), vol 4,7% e um Sharpe inflado por dias de retorno zero.
    w = ativo(d, d["pesos"])
    acoes = [c for c in w.columns if c != "IBOV_SYNTHETIC"]
    n_pos = (w[acoes].abs() > 1e-6).sum(axis=1)
    giro = ativo(d, d["giro"])
    r_flat, r_real = ativo(d, d["r_flat"]), ativo(d, d["r_real"])
    r_cdi, r_ibov = ativo(d, d["r_cdi"]), ativo(d, d["r_ibov"])

    linhas = ["| ano | alfa<br>*(5 bps)* | **alfa<br>*(realista)*** | fundo<br>*(realista)* | CDI | Ibovespa | Sharpe<br>*(5bps)* | MDD | vol | ações | giro/dia |",
              "|---|---|---|---|---|---|---|---|---|---|---|"]
    for a in sorted(set(r_flat.index.year)):
        r = r_flat[r_flat.index.year == a]
        c = r_cdi[r_cdi.index.year == a]
        ib = r_ibov[r_ibov.index.year == a]
        # Aquecimento: o sinal so existe depois de 252d de beta + 231d de
        # acumulacao. Anos sem posicao nao entram na tabela.
        if len(r) < 20 or (n_pos[n_pos.index.year == a].mean() or 0) < 1:
            continue
        mm = metricas(r)
        rr = r_real[r_real.index.year == a]
        linhas.append(
            f"| {a} | {(1+r).prod()-1:+.2%} | **{(1+rr).prod()-1:+.2%}** | "
            f"{(1+rr.add(c, fill_value=0)).prod()-1:+.2%} | {(1+c).prod()-1:+.2%} | "
            f"{(1+ib).prod()-1:+.2%} | {mm['sharpe']:.2f} | {mm['mdd']:.1%} | {mm['vol']:.1%} | "
            f"{n_pos[n_pos.index.year == a].mean():.0f} | "
            f"{giro[giro.index.year == a].mean():.1%} |")
    nota = ("\n\n> **Por que 2016 não aparece:** o sinal exige 252 pregões de regressão mais 231 de "
            "acumulação — cerca de dois anos de aquecimento. A estratégia só tem posição a partir de "
            f"{d['primeiro_ativo']:%d/%m/%Y}, então **{d['primeiro_ativo']:%Y} é um ano parcial** "
            "(nem o retorno nem o giro dele são comparáveis aos anos cheios).\n\n"
            "> **Por que o alfa não é comparado ao CDI:** o P&L da Sinapse **já é** excesso sobre a taxa "
            "livre. A carteira é long-short autofinanciada — as vendidas financiam as compradas e o AUM "
            "fica em caixa rendendo CDI. Descontar o CDI de novo contaria a taxa livre duas vezes. "
            "O que o cotista recebe é a coluna *fundo*.")
    return salvar_md("\n".join(linhas) + nota, "14_tabela_desempenho_anual")


def t_sinais(d):
    """Exemplo concreto: a vida de algumas posicoes ao longo do tempo."""
    w = d["pesos"]
    acoes = [c for c in w.columns if c != "IBOV_SYNTHETIC"]
    W = w[acoes]

    # Uma acao por SUBSETOR: ON e PN da mesma empresa recebem sinal identico
    # (sao a mesma exposicao economica), entao mostrar as duas desperdicaria
    # coluna sem acrescentar informacao.
    mapa = pd.read_csv(os.path.join(BASE_DIR, "fase 4 - sinal da sinapse", "mapeamento_setores.csv"))
    sub = {t: s for t, s in zip(mapa["Ticker"], mapa["Subsetor"])
           if isinstance(s, str) and s != "A DEFINIR"}
    ranking = W.abs().sum().sort_values(ascending=False)
    escolhidas, vistos = [], set()
    for t in ranking.index:
        s = sub.get(t)
        if s is None or s in vistos:
            continue
        vistos.add(s)
        escolhidas.append(t)
        if len(escolhidas) == 6:
            break

    amostra = W.loc[W.index >= "2023-01-01", escolhidas].resample("ME").mean().head(14)
    linhas = ["| mês | " + " | ".join(escolhidas) + " |",
              "|---" * (len(escolhidas) + 1) + "|"]
    for dt, row in amostra.iterrows():
        cel = []
        for t in escolhidas:
            v = row[t]
            if pd.isna(v) or abs(v) < 1e-4:
                cel.append("· HOLD")
            elif v > 0:
                cel.append(f"**BUY** {v:+.2%}")
            else:
                cel.append(f"**SELL** {v:+.2%}")
        linhas.append(f"| {dt:%Y-%m} | " + " | ".join(cel) + " |")

    nota = ("\n\n**Como ler:** cada célula é o peso médio da posição no mês. "
            "`BUY` = comprado, `SELL` = vendido, `HOLD` = fora da carteira.\n\n"
            "A carteira **não** entra e sai de posições — ela ajusta o *tamanho* continuamente. "
            "É consequência do desenho: o sinal é acumulado em 12 meses e os pesos são suavizados em 63 pregões, "
            "então a convicção muda devagar. Uma ação típica permanece meses na carteira mudando de peso, "
            "e troca de lado quando o choque acumulado do seu ramo inverte.")
    return salvar_md("\n".join(linhas) + nota, "15_tabela_sinais_exemplo")


def t_parametros(_):
    p = [
        ("Janela da regressão", "252 pregões", "12 meses de dados diários é o padrão para estimar beta com precisão sem pegar 'outra empresa' do passado.", "pré-registrado"),
        ("Winsorização", "2% (1% por cauda)", "Impede que um outlier domine o z-score transversal. Medido: corta 2,57% das células — é guarda leve, não proteção contra caudas gordas.", "pré-registrado"),
        ("Trava por nome", "5% do AUM", "Obriga o capital a se dividir em ≥20 teses. Hoje morde em apenas 2,3% dos dias — a expansão do universo a soltou.", "pré-registrado"),
        ("Trava por setor", "25% do gross", "Impede que um boom setorial vire aposta macro disfarçada de aposta em rede.", "pré-registrado"),
        ("Trava de liquidez", "10% do ADTV (21d)", "Limita a POSIÇÃO ao que seria montável. Não governa impacto de execução — quem faz isso é o modelo de custo.", "pré-registrado"),
        ("Volatilidade-alvo", "12% a.a.", "TETO de orçamento de risco, não alvo atingido. Utilização medida 63% (mediana da vol de 63d: 7,54%). Atingir 12% exigiria 8,3% por nome, acima da trava.", "pré-registrado"),
        ("AUM", "R$ 100 milhões", "Fundo de tamanho médio viável no Brasil. Curva de capacidade testada em 20 / 100 / 300 / 1000 MM.", "pré-registrado"),
        ("Horizonte do sinal", "12-1 (231d, defasado 22)", "IC cresce com o horizonte (+0,0076 em T+1 → +0,0389 em T+126). IC/√h cai 45%, contra 91% de um efeito de 1 dia: difusão lenta, medida.", "acrescentado 08/2026"),
        ("Modelo do choque", "só-mercado (α + β·IBOV)", "A tese é difusão intra-indústria: o termo setorial removia justamente a informação que se propaga.", "acrescentado 08/2026"),
        ("Grafo", "ensemble de 6 variantes", "K ∈ {2,3,5} × peso ∈ {igual, ADTV}. TODAS entram — nenhuma escolhida por desempenho.", "acrescentado 08/2026"),
        ("Suavização dos pesos", "63 pregões", "Deve ser da ordem do horizonte do sinal. Consequência estrutural, não calibragem.", "acrescentado 08/2026"),
        ("Custo de transação", "3 camadas", "spread por faixa de ADTV + impacto √(participação) + aluguel BTC. Medido: 36,6 bps por unidade de giro, contra 68,3 bps de alfa gerado.", "acrescentado 08/2026"),
    ]
    linhas = ["| parâmetro | valor | justificativa | origem |", "|---|---|---|---|"]
    for a, b, c, e in p:
        linhas.append(f"| **{a}** | `{b}` | {c} | {e} |")
    return salvar_md("\n".join(linhas), "16_tabela_parametros")


# ==================================================================
# 14. EVOLUCAO DO RESULTADO (as correcoes)
# ==================================================================

def g_evolucao(d):
    # As duas ultimas barras sao MEDIDAS a cada execucao. A ultima estava
    # congelada em "+36,4%", de uma rodada anterior a correcao de calendario --
    # justo num grafico cujo argumento e "publicamos o numero pior".
    a = d["mask_ativo"]
    final_flat = ((1 + d["r_flat"][a]).prod() - 1) * 100
    final_real = ((1 + d["r_real"][a]).prod() - 1) * 100
    etapas = [
        ("baseline\n(mocks + bug)", -63.0, C["ruim"]),
        ("+ grafo e vol\ncorrigidos", -1.3, C["ruim"]),
        ("+ giro\ncontrolado", 19.9, C["bom"]),
        ("− viés de\nsobrevivência", 8.7, C["ibov"]),
        ("+ Sharpe e trava\ncorrigidos", 8.5, C["ibov"]),
        ("+ grafo\npoint-in-time", 11.6, C["ibov"]),
        ("+ mapa setorial\ncorrigido", 27.9, C["bom"]),
        ("+ horizonte 12-1\ne grafo mecânico", 36.4, C["neutro"]),
        ("+ calendário da B3\ncorrigido  (5 bps)", final_flat, C["sinapse"]),
        ("= com custo\nREALISTA", final_real, C["ibov"]),
    ]
    fig, ax = fig169(12.8, 6.4)
    x = np.arange(len(etapas))
    vals = [e[1] for e in etapas]
    ax.bar(x, vals, color=[e[2] for e in etapas], width=0.62, edgecolor=C["surface"], linewidth=2)
    for i, v in enumerate(vals):
        ax.annotate(f"{v:+.1f}%", (i, v), xytext=(0, 6 if v >= 0 else -16),
                    textcoords="offset points", ha="center", fontsize=11,
                    fontweight="700", color=C["tinta"])
    ax.set_xticks(x); ax.set_xticklabels([e[0] for e in etapas], fontsize=9)
    ax.axhline(0, color=C["eixo"], linewidth=1.4)
    ax.set_ylabel("retorno acumulado do alfa")
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:.0f}%"))
    ax.set_ylim(min(vals) * 1.18, max(vals) * 1.30)
    titulo(ax, "A evolução do resultado — e as três vezes em que o número PIOROU",
           "Remover o viés de sobrevivência custou metade do resultado (+19,9% → +8,7%) e foi adotado assim mesmo.\n"
           "Corrigir o grafo para point-in-time custou mais 0,58 p.p./ano. Aplicar o custo REALISTA custa outra metade "
           f"({final_flat:+.1f}% → {final_real:+.1f}%).\nPublicar o número pior é o que torna o resto crível.")
    ax.annotate("", xy=(3, 12), xytext=(2, 23), arrowprops=dict(arrowstyle="-|>", color=C["ruim"], linewidth=2.2))
    ax.text(2.55, 25, "viés removido", fontsize=10, color=C["ruim"], fontweight="700", ha="center")
    ax.annotate("", xy=(9, final_real + 4), xytext=(8, final_flat + 6),
                arrowprops=dict(arrowstyle="-|>", color=C["ruim"], linewidth=2.2))
    ax.text(8.5, final_flat + 8, "custo realista", fontsize=10, color=C["ruim"],
            fontweight="700", ha="center")
    return salvar(fig, "17_evolucao_correcoes")


# ==================================================================
# MAIN
# ==================================================================

GRAFICOS = {
    "curva": g_curva, "drawdown": g_drawdown, "anual": g_anual, "giro": g_giro,
    "horizonte": g_horizonte, "exposicao": g_exposicao, "heatmap": g_heatmap,
    "rolling": g_rolling, "distribuicao": g_distribuicao, "fluxograma": g_fluxograma,
    "regra": g_regra, "custo": g_custo, "evolucao": g_evolucao,
    "t_metricas": t_metricas, "t_anual": t_anual, "t_sinais": t_sinais,
    "t_parametros": t_parametros,
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apenas", default=None, help="lista separada por virgula")
    ap.add_argument("--deck", action="store_true",
                    help="versoes para o deck: subtitulo curto onde o slide ja "
                         "diz a mesma coisa. Salva em saida/deck/.")
    args = ap.parse_args()

    global DECK
    DECK = args.deck

    print("=" * 70)
    print(" BLOCO 7 -- ACERVO VISUAL")
    print("=" * 70)
    d = carregar()
    print(f"\ndados:  {d['curvas'].index.min():%Y-%m-%d} a {d['curvas'].index.max():%Y-%m-%d}")
    print(f"janela do material (carteira com posicao): {d['idx_ativo'][0]:%Y-%m-%d} a "
          f"{d['idx_ativo'][-1]:%Y-%m-%d}  ({len(d['idx_ativo'])} pregoes)")
    print("todo grafico e toda tabela usam a segunda linha.\n")

    alvos = args.apenas.split(",") if args.apenas else list(GRAFICOS)
    for nome in alvos:
        fn = GRAFICOS.get(nome.strip())
        if fn is None:
            print(f"  [!] desconhecido: {nome}")
            continue
        try:
            fn(d)
        except Exception as erro:
            print(f"  [ERRO] {nome}: {erro}")

    print(f"\nSaida em: {SAIDA}")


if __name__ == "__main__":
    main()
