"""
Bloco 6: bateria de evidencia da CONFIGURACAO EM PRODUCAO.

POR QUE ESTE SCRIPT EXISTE
--------------------------
Uma auditoria de 16/08 encontrou o pior tipo de problema possivel: os numeros
mais importantes do relatorio -- walk-forward, placebo do gatilho, Deflated
Sharpe, atribuicao de fator -- tinham sido calculados em prototipos e NAO
existiam no repositorio. Nao podiam ser regerados nem auditados.

Pior: os p-valores do placebo que estavam documentados haviam sido medidos
numa configuracao que foi REJEITADA (com neutralizacao de beta), nao na que
esta em producao.

Este script recalcula tudo, do zero, a partir do pipeline em producao.
Todo numero que for para o relatorio sai daqui.

Os scripts s6 a s13 continuam no repositorio como registro historico, mas
rodam a estrategia SUPERADA (choque bivariado, media movel de 21d, grafo
manual). Nao usar os artefatos deles.

USO
---
    python "fase 6 - validacao/src/s14_evidencia.py"
    python "fase 6 - validacao/src/s14_evidencia.py" --sorteios 300
"""

import argparse
import importlib.util
import json
import os
import sys

import numpy as np
import pandas as pd

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_DIR = os.path.join(BASE_DIR, "data")
SAIDA = os.path.join(DATA_DIR, "evidencia")
DIAS = 252
AUM = 100_000_000

# N ACUMULADO de configuracoes testadas no projeto inteiro, para o Deflated
# Sharpe. Declarar este numero e o que separa pesquisa de garimpo -- e ele
# so cresce.
N_CONFIGS_PROJETO = 294


def _carregar(nome, rel):
    spec = importlib.util.spec_from_file_location(nome, os.path.join(BASE_DIR, rel))
    m = importlib.util.module_from_spec(spec)
    sys.modules[nome] = m
    spec.loader.exec_module(m)
    return m


s4 = _carregar("s4", os.path.join("fase 4 - sinal da sinapse", "src", "s4_sinapse_sinal.py"))
s5 = _carregar("s5", os.path.join("fase 5 - construcao da carteira", "src", "s5_portfolio_builder.py"))
sys.path.insert(0, os.path.join(BASE_DIR, "fase 3 - backtest", "src"))
import s3b_custos


# ==================================================================
# INSUMOS
# ==================================================================

def contexto():
    print("Carregando insumos e recalculando o choque (config de producao)...")
    ret, idx, _, mapa = s4.carregar_dados()
    choques, betas = s4.calcular_choque_mercado(ret, idx, tickers_alvo=None)
    acum = s4.acumular_choque(choques)
    grafo = pd.read_parquet(os.path.join(DATA_DIR, "grafo_regra_mensal.parquet"))

    setores = mapa.copy()
    setores.columns = ["Ticker", "Setor"] + list(setores.columns[2:])
    setores = setores.set_index("Ticker")[["Setor"]]

    adtv = pd.read_parquet(os.path.join(DATA_DIR, "universo", "adtv_diario.parquet"))
    ibov = idx["IBOV"]
    cdi = pd.read_parquet(os.path.join(DATA_DIR, "precos", "cdi_diario.parquet"))["CDI"]
    return dict(ret=ret, choques=choques, acum=acum, betas=betas, grafo=grafo,
                setores=setores, adtv=adtv, ibov=ibov, cdi=cdi, mapa=mapa)


def sinal_de(grafo, ctx):
    bruto = s4.propagar_ensemble(ctx["acum"], grafo)
    return s4.limpar_e_winsorizar_sinal(bruto)


def carteira_de(sinal, ctx, janela_pesos=63):
    ret, _ = ctx["ret"].align(sinal, join="right")
    bet, _ = ctx["betas"].align(sinal, join="right")
    adt, _ = ctx["adtv"].align(sinal, join="right")
    pb = s5.PortfolioBuilder(aum=AUM, janela_suavizacao_pesos=janela_pesos)
    return pb.build_portfolio(df_zscore=sinal, df_returns=ret, df_adtv=adt,
                              df_betas=bet, df_sectors=ctx["setores"])


def pnl_de(W, ctx, custo="real"):
    R = ctx["ret"].copy()
    R["IBOV_SYNTHETIC"] = ctx["ibov"].reindex(R.index)
    R = R.loc[~R["IBOV_SYNTHETIC"].isna()]
    datas = W.index.intersection(R.index)
    W, R = W.loc[datas].sort_index(), R.loc[datas].sort_index()
    bruto = (W.fillna(0) * R.fillna(0)).sum(axis=1)
    giro = W.fillna(0).diff().abs().sum(axis=1)
    if custo == "real":
        c, _ = s3b_custos.custo_por_dia(W, ctx["adtv"], R, AUM)
        c = c.reindex(bruto.index).fillna(0.0)
    else:
        c = giro * 0.0005
    return bruto - c, bruto, giro, W


def sharpe(r):
    r = r.dropna()
    return r.mean() / r.std() * np.sqrt(DIAS) if len(r) > 20 and r.std() > 0 else np.nan


def ic_serie(sinal, ret, h=21):
    cols = [c for c in sinal.columns if c in ret.columns]
    fwd = ret[cols].reindex(sinal.index).rolling(h).sum().shift(-h)
    return sinal[cols].corrwith(fwd, axis=1).dropna()


def t_ic(v, h=21):
    return v.mean() / (v.std() / np.sqrt(len(v) / h)) if len(v) > h else np.nan


# ==================================================================
# 1. PLACEBO DO GATILHO -- na configuracao de PRODUCAO
# ==================================================================

def placebo(ctx, n=300, semente=42):
    """
    Sorteia QUAL nome do subsetor e a cabeca, mantendo subsetor, K e satelites.

    E o teste do MECANISMO: se ordenar por liquidez nao carrega informacao, um
    gatilho sorteado deveria funcionar igual. A hipotese nula e "qualquer par
    do mesmo ramo serve".
    """
    print(f"\n[1] Placebo do gatilho ({n} sorteios)...")
    rng = np.random.default_rng(semente)
    g = ctx["grafo"]
    sub = {t: s for t, s in zip(ctx["mapa"]["Ticker"], ctx["mapa"].get("Subsetor", []))
           if isinstance(s, str) and s != "A DEFINIR"}

    real_ic = ic_serie(sinal_de(g, ctx), ctx["ret"])
    corte = pd.Timestamp("2020-12-31")
    alvo = {"IS": real_ic[real_ic.index <= corte], "OOS": real_ic[real_ic.index > corte],
            "total": real_ic}

    membros = {}
    for (mes, var), bloco in g.groupby(["mes_vigencia", "variante"]):
        for s in set(sub.get(t) for t in bloco["empresa_B"]):
            if s is None:
                continue
        membros[(mes, var)] = bloco

    dist = {k: [] for k in alvo}
    for i in range(n):
        gp = g.copy()
        # dentro de cada (mes, variante, subsetor), permuta quem e cabeca
        chave = gp["empresa_B"].map(sub)
        novo_a = gp["empresa_A"].copy()
        for (mes, var, s), bloco in gp.groupby(["mes_vigencia", "variante", chave]):
            elegiveis = sorted(set(bloco["empresa_B"]) | set(bloco["empresa_A"]))
            cabecas = sorted(set(bloco["empresa_A"]))
            sorteadas = list(rng.choice(elegiveis, size=len(cabecas), replace=False))
            mapa_c = dict(zip(cabecas, sorteadas))
            novo_a.loc[bloco.index] = bloco["empresa_A"].map(mapa_c)
        gp["empresa_A"] = novo_a
        gp = gp[gp["empresa_A"] != gp["empresa_B"]]
        v = ic_serie(sinal_de(gp, ctx), ctx["ret"])
        dist["IS"].append(v[v.index <= corte].mean())
        dist["OOS"].append(v[v.index > corte].mean())
        dist["total"].append(v.mean())
        if (i + 1) % 50 == 0:
            print(f"    {i+1}/{n}")

    linhas = []
    for k in ["IS", "OOS", "total"]:
        arr = np.array([x for x in dist[k] if np.isfinite(x)])
        real = alvo[k].mean()
        p = float((arr >= real).mean())
        linhas.append({"janela": k, "ic_real": real, "placebo_media": arr.mean(),
                       "placebo_dp": arr.std(), "p_unilateral": p,
                       "percentil": float((arr < real).mean()), "n_sorteios": len(arr)})
    return pd.DataFrame(linhas)


# ==================================================================
# 2. CONTROLE DE PERSISTENCIA
# ==================================================================

def persistencia(ctx):
    """
    O choque acumulado do PROPRIO nome, no mesmo universo. E a hipotese nula
    da tese: se a propagacao entre nomes nao adiciona sobre a persistencia no
    proprio nome, a tese de difusao nao se separa de momento residual.
    """
    print("\n[2] Controle de persistencia (momento residual proprio)...")
    sinal = sinal_de(ctx["grafo"], ctx)
    cols = [c for c in sinal.columns if c in ctx["acum"].columns]
    proprio = s4.limpar_e_winsorizar_sinal(ctx["acum"][cols])

    r_prop, _, _, _ = pnl_de(carteira_de(proprio, ctx), ctx)
    r_grafo, _, _, _ = pnl_de(carteira_de(sinal, ctx), ctx)

    idx = r_prop.index.intersection(r_grafo.index)
    x, y = r_prop.loc[idx], r_grafo.loc[idx]
    beta = np.polyfit(x, y, 1)[0]
    alfa_dia = (y - beta * x).mean()
    res = y - beta * x
    t = alfa_dia / (res.std() / np.sqrt(len(res)))
    return {"sharpe_propagacao": sharpe(y), "sharpe_persistencia": sharpe(x),
            "correlacao": float(x.corr(y)), "beta": float(beta),
            "alfa_ano": float(alfa_dia * DIAS), "t_alfa": float(t)}


# ==================================================================
# 3. ATRIBUICAO DE FATOR
# ==================================================================

def fatores(ctx, r_estrategia):
    """Constroi fatores no MESMO universo e regride o P&L contra eles."""
    print("\n[3] Atribuicao de fator...")
    ret = ctx["ret"]
    cols = [c for c in ctx["acum"].columns if c in ret.columns]
    R = ret[cols]

    def z(x):
        return x.sub(x.mean(axis=1), axis=0).div(x.std(axis=1).replace(0, 1), axis=0)

    fat = {
        "mom21": z(R.rolling(21).mean()),
        "mom12_1": z(R.rolling(231).sum().shift(22)),
        "rev5": z(-R.rolling(5).mean()),
        "lowvol": z(-R.rolling(60).std()),
    }
    curvas = {}
    for nome, s in fat.items():
        w = s.div(s.abs().sum(axis=1), axis=0).fillna(0)
        curvas[nome] = (w.shift(1) * R).sum(axis=1)

    X = pd.DataFrame(curvas).dropna()
    idx = X.index.intersection(r_estrategia.index)
    X, y = X.loc[idx], r_estrategia.loc[idx]
    A = np.column_stack([np.ones(len(X))] + [X[c].to_numpy() for c in X.columns])
    coef, *_ = np.linalg.lstsq(A, y.to_numpy(), rcond=None)
    resid = y.to_numpy() - A @ coef
    # Newey-West simples (21 lags)
    n, k = A.shape
    S = (resid[:, None] * A).T @ (resid[:, None] * A)
    for L in range(1, 22):
        u = (resid[:, None] * A)
        G = u[L:].T @ u[:-L]
        S += (1 - L / 22) * (G + G.T)
    XtX_inv = np.linalg.inv(A.T @ A)
    se = np.sqrt(np.diag(XtX_inv @ S @ XtX_inv))
    return {"alfa_ano": float(coef[0] * DIAS), "t_alfa": float(coef[0] / se[0]),
            **{f"beta_{c}": float(coef[i + 1]) for i, c in enumerate(X.columns)},
            **{f"t_{c}": float(coef[i + 1] / se[i + 1]) for i, c in enumerate(X.columns)}}


# ==================================================================
# 4. DEFLATED SHARPE
# ==================================================================

def deflated_sharpe(r, n_configs=N_CONFIGS_PROJETO, dp_sharpes=0.42):
    """
    Bailey & Lopez de Prado. Corrige o Sharpe pelo numero de configuracoes
    testadas -- e por isso `n_configs` DEVE ser declarado honestamente.
    """
    from math import log, sqrt, erf, exp, pi
    r = r.dropna()
    T, sr = len(r), sharpe(r)
    g1, g2 = float(r.skew()), float(r.kurtosis()) + 3.0
    gamma = 0.5772156649
    e = 2.718281828459045
    z = ((1 - gamma) * (2 * log(max(n_configs, 2))) ** 0.5
         + gamma * (2 * log(max(n_configs, 2))) ** -0.5)
    sr0 = dp_sharpes * z / sqrt(DIAS)          # limiar em base diaria
    sr_d = sr / sqrt(DIAS)
    den = sqrt(max(1 - g1 * sr_d + (g2 - 1) / 4 * sr_d ** 2, 1e-9))
    stat = (sr_d - sr0) * sqrt(T - 1) / den
    dsr = 0.5 * (1 + erf(stat / sqrt(2)))
    return {"sharpe": sr, "n_configs": n_configs, "sharpe_limiar": sr0 * sqrt(DIAS),
            "DSR": dsr, "skew": g1, "curtose": g2}


# ==================================================================
# 5. WALK-FORWARD
# ==================================================================

def walk_forward(ctx, primeiro=2019):
    """
    Janela expansiva. Para o ano Y, a janela de suavizacao de pesos e
    re-escolhida usando SO 2016..Y-1, e o ano Y e medido uma vez.

    E o unico numero que nao gasta periodo: cada ano foi medido com parametro
    que nao tinha visto aquele ano.
    """
    print("\n[5] Walk-forward...")
    sinal = sinal_de(ctx["grafo"], ctx)
    grade = [21, 42, 63, 126]
    cache = {}
    for j in grade:
        r, _, _, _ = pnl_de(carteira_de(sinal, ctx, janela_pesos=j), ctx)
        cache[j] = r

    linhas, pedacos = [], []
    anos = sorted(set(cache[grade[0]].index.year))
    for ano in [a for a in anos if a >= primeiro]:
        treino = {j: s[s.index.year < ano] for j, s in cache.items()}
        escolha = max(grade, key=lambda j: sharpe(treino[j]) if len(treino[j]) > 60 else -9)
        teste = cache[escolha][cache[escolha].index.year == ano]
        if len(teste) < 20:
            continue
        pedacos.append(teste)
        linhas.append({"ano": ano, "janela_escolhida": escolha,
                       "sharpe": sharpe(teste), "retorno": (1 + teste).prod() - 1})
    curva = pd.concat(pedacos).sort_index()
    return pd.DataFrame(linhas), curva


# ==================================================================
# MAIN
# ==================================================================

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sorteios", type=int, default=300)
    args = ap.parse_args()

    os.makedirs(SAIDA, exist_ok=True)
    print("=" * 78)
    print(" BLOCO 6 -- BATERIA DE EVIDENCIA (configuracao em producao)")
    print("=" * 78)

    ctx = contexto()
    sinal = sinal_de(ctx["grafo"], ctx)
    W = carteira_de(sinal, ctx)
    r_real, bruto, giro, W = pnl_de(W, ctx, custo="real")
    r_flat, _, _, _ = pnl_de(W, ctx, custo="flat")
    ativo = W.abs().sum(axis=1) > 1e-9
    r_real_a, r_flat_a = r_real[ativo], r_flat[ativo]

    resumo = {"primeiro_pregao_ativo": str(r_real_a.index.min().date()),
              "pregoes_ativos": int(ativo.sum()),
              "sharpe_flat": sharpe(r_flat_a), "sharpe_real": sharpe(r_real_a),
              "alfa_giro_bps": float(bruto.mean() / giro.mean() * 1e4),
              "custo_giro_bps": float((bruto - r_real).mean() / giro.mean() * 1e4)}

    df_pla = placebo(ctx, n=args.sorteios)
    df_pla.to_csv(os.path.join(SAIDA, "placebo_gatilho.csv"), index=False)
    print(f"\n{'janela':<8}{'IC real':>10}{'placebo':>10}{'dp':>9}{'p':>9}")
    print("-" * 46)
    for _, x in df_pla.iterrows():
        print(f"{x['janela']:<8}{x['ic_real']:>+10.4f}{x['placebo_media']:>+10.4f}"
              f"{x['placebo_dp']:>9.4f}{x['p_unilateral']:>9.3f}")

    per = persistencia(ctx)
    print(f"  Sharpe propagacao {per['sharpe_propagacao']:+.3f} | "
          f"persistencia {per['sharpe_persistencia']:+.3f} | corr {per['correlacao']:.3f}")
    print(f"  alfa da propagacao SOBRE a persistencia: {per['alfa_ano']:+.2%}/ano (t {per['t_alfa']:.2f})")

    atr = fatores(ctx, r_real_a)
    print(f"  alfa apos os 4 fatores: {atr['alfa_ano']:+.2%}/ano (t {atr['t_alfa']:.2f})")

    df_wf, curva_wf = walk_forward(ctx)
    df_wf.to_csv(os.path.join(SAIDA, "walk_forward.csv"), index=False)
    print(f"\n{'ano':<7}{'janela':>8}{'Sharpe':>9}{'retorno':>10}")
    print("-" * 34)
    for _, x in df_wf.iterrows():
        print(f"{int(x['ano']):<7}{int(x['janela_escolhida']):>8}{x['sharpe']:>9.2f}{x['retorno']:>10.2%}")
    print(f"\n  WALK-FORWARD AGREGADO: Sharpe {sharpe(curva_wf):+.3f} | "
          f"{(1+curva_wf).prod()-1:+.1%} acumulado | {len(curva_wf)} pregoes")

    dsr_wf = deflated_sharpe(curva_wf)
    dsr_pr = deflated_sharpe(r_real_a)
    print(f"\n[4] Deflated Sharpe (N={N_CONFIGS_PROJETO} declarado)")
    print(f"  walk-forward : SR {dsr_wf['sharpe']:+.3f} | limiar {dsr_wf['sharpe_limiar']:.3f} | DSR {dsr_wf['DSR']:.3f}")
    print(f"  producao     : SR {dsr_pr['sharpe']:+.3f} | limiar {dsr_pr['sharpe_limiar']:.3f} | DSR {dsr_pr['DSR']:.3f}")

    tudo = {"resumo": resumo, "persistencia": per, "atribuicao": atr,
            "dsr_walk_forward": dsr_wf, "dsr_producao": dsr_pr,
            "walk_forward_sharpe": sharpe(curva_wf),
            "walk_forward_acumulado": float((1 + curva_wf).prod() - 1),
            "walk_forward_pregoes": int(len(curva_wf))}
    with open(os.path.join(SAIDA, "evidencia.json"), "w", encoding="utf-8") as f:
        json.dump(tudo, f, indent=2, ensure_ascii=False, default=float)
    curva_wf.to_frame("retorno").to_parquet(os.path.join(SAIDA, "curva_walk_forward.parquet"))

    print(f"\nArtefatos em: {SAIDA}")


if __name__ == "__main__":
    main()
