"""
Bloco 4b: preenche o mapeamento setorial (manutencao).

POR QUE ESTE SCRIPT EXISTE
--------------------------
Em 04/08 descobrimos que 201 dos 253 tickers do `mapeamento_setores.csv`
estavam com o setor literal "A DEFINIR" -- inclusive 43 das 74 empresas do
grafo. Isso nao era um detalhe de cadastro: quebrava duas coisas.

1. REGRESSAO DO CHOQUE LIMPO (Bloco 4)
   O choque limpo sai de `retorno = a + b1*IBOV + b2*SETOR + residuo`, onde
   SETOR e a media das OUTRAS acoes do mesmo setor. Com 201 acoes no mesmo
   balaio, o "indice setorial" de cada uma delas era a media de 200 acoes
   de todos os setores misturados -- ou seja, praticamente o mercado. IBOV
   e SETOR ficavam quase colineares, e o controle setorial nao controlava
   nada. O residuo chamado de "choque idiossincratico" ainda continha o
   movimento do setor inteiro.

2. TRAVA SETORIAL (Bloco 5)
   O limite de 25% por setor tratava as 43 empresas do grafo em "A DEFINIR"
   como UM setor so. Media em 04/08: a trava setorial sozinha cortava 55,9%
   da exposicao bruta -- de longe a mais restritiva das tres. Boa parte
   disso era artefato de cadastro, nao decisao de risco.

CRITERIO DE CLASSIFICACAO
-------------------------
Setores da B3 (mesma taxonomia dos 52 tickers que ja estavam preenchidos).
Onde a classificacao real da B3 e contra-intuitiva, seguimos a B3 e nao o
senso comum:
  - Shoppings e exploracao de imoveis (MULT3, IGTI11, ALOS3, BRML3, IGTA3,
    LOGG3, BRPR3, SYNE3) -> Financeiro, nao "Imobiliario".
  - Construcao civil e incorporacao (CYRE3, EZTC3, MRVE3...) -> Consumo
    Ciclico.
  - Servicos educacionais (KROT3, ESTC3, ANIM3...) -> Consumo Ciclico.
  - Holdings seguem o ativo principal: BRAP4 (Vale) -> Materiais Basicos;
    ITSA4 (Itau) -> Financeiro.

TICKERS DEIXADOS EM "A DEFINIR"
-------------------------------
Alguns poucos ficam sem classificacao de proposito: nao consegui
identificar a empresa com confianca suficiente. Chute errado e pior que
ausencia -- um ticker no setor errado contamina o indice setorial de dois
setores ao mesmo tempo. Nenhum deles esta no grafo.

USO
---
    python "fase 4 - sinal da sinapse/src/s4b_atualiza_setores.py"

O script e idempotente: so preenche o que esta em "A DEFINIR" ou ausente,
nunca sobrescreve uma classificacao existente.
"""

import os

import pandas as pd

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CAMINHO_MAPA = os.path.join(BASE_DIR, "fase 4 - sinal da sinapse", "mapeamento_setores.csv")

MARCADOR_VAZIO = "A DEFINIR"

# ------------------------------------------------------------------
# Classificacao por setor B3
# ------------------------------------------------------------------

SETORES = {
    "Petróleo Gás e Biocombustíveis": [
        "BRAV3", "BRDT3", "DMMO3", "ENAT3", "QGEP3", "RAIZ4", "RECV3",
        "RRRP3", "VBBR3",
    ],
    "Materiais Básicos": [
        "AXIA3", "AXIA6", "AXIA7", "BRAP4", "BRKM5", "CBAV3", "CMIN3",
        "DTEX3", "DXCO3", "ETER3", "FHER3", "FIBR3", "GGBR3", "GOAU4",
        "MAGG3", "PTBL3", "SUZB5", "UNIP6", "VALE5",
    ],
    "Bens Industriais": [
        "AERI3", "ARTR3", "ECOR3", "EMBJ3", "FJTA4", "GGPS3", "HBSA3",
        "INTB3", "KEPL3", "LEVE3", "LOGN3", "MILS3", "MOTV3", "MYPK3",
        "POMO4", "PORT3", "RAPT4", "ROMI3", "RUMO3", "SEQL3", "SIMH3",
        "STBP3", "TASA4", "TGMA3", "TPIS3", "TUPY3", "VAMO3", "AMBP3",
    ],
    "Consumo Não Cíclico": [
        "BEEF3", "CAML3", "GMAT3", "MBRF3", "MDIA3", "MRFG3", "NATU3",
        "PCAR3", "PCAR4", "SLCE3", "SMTO3", "TTEN3",
    ],
    "Consumo Cíclico": [
        "ALPA4", "AMAR3", "AMER3", "ANIM3", "ARZZ3", "AZZA3", "BHIA3",
        "BKBR3", "BTOW3", "CEAB3", "CNTO3", "CURY3", "CYRE3", "DIRR3",
        "ESPA3", "ESTC3", "EVEN3", "EZTC3", "GFSA3", "GRND3", "GUAR3",
        "HBOR3", "HGTX3", "JHSF3", "KROT3", "LAME3", "LAME4", "LCAM3",
        "LJQQ3", "LLIS3", "MEAL3", "MOSI3", "MOVI3", "MPLU3", "MRVE3",
        "PDGR3", "PETZ3", "RSID3", "SBFG3", "SEDU3", "SEER3", "SMFT3",
        "SMLE3", "SMLS3", "SOMA3", "TCSA3", "TEND3", "VIIA3", "VIVA3",
        "VIVR3", "VULC3", "VVAR11", "VVAR3",
    ],
    "Saúde": [
        "AALR3", "BPHA3", "GNDI3", "HYPE3", "ODPV3", "ONCO3", "PARD3",
        "PGMN3", "QUAL3",
    ],
    "Tecnologia da Informação": [
        "BMOB3", "CARD3", "CASH3", "CLSA3", "LINX3", "LWSA3", "NGRD3",
        "POSI3", "SQIA3", "VLID3",
    ],
    "Comunicações": [
        "FIQE3", "OIBR3", "OIBR4", "TIMP3", "VIVT4",
    ],
    "Utilidade Pública": [
        "AESB3", "ALUP11", "AURE3", "CESP6", "CGAS5", "CMIG3", "CPFE3",
        "CPLE3", "CPLE5", "CPRE3", "CSMG3", "EGIE3", "ELPL3", "ELPL4",
        "ENBR3", "ENGI11", "ISAE4", "LIGT3", "MEGA3", "NEOE3", "OMGE3",
        "ORVR3", "SAPR11", "SAPR4", "SRNA3", "TAEE11", "TBLE3", "TIET11",
        "TRPL4",
    ],
    "Financeiro": [
        "ABCB4", "ALOS3", "ALSC3", "ALSO3", "BBTG11", "BIDI11", "BIDI4",
        "BMGB11", "BPAC11", "BPAN4", "BRML3", "BRPR3", "BRSR6", "BVMF3",
        "CIEL3", "CTIP3", "CXSE3", "IGTA3", "IRBR3", "ITSA3", "ITSA4",
        "ITUB3", "LOGG3", "PARC3", "PRBC4", "PSSA3", "SULA11", "SYNE3", "WIZS3",
    ],
}
# PARC3 -> WIZS3 -> WIZC3: Wiz Co, ticker renomeado em 2017. Financeiro,
# subsetor Previdencia e Seguros, segmento Corretoras de Seguros (confirmado
# pelo usuario em 04/08). PARC3 ja esta em tickers_sem_preco.csv como
# "empresa_extinta" -- nunca tem preco, entao esta classificacao nao afeta
# nenhum resultado; e so por completude do cadastro.

# Nao classificados de proposito -- empresa nao identificada com confianca.
# Nenhum esta no grafo, entao nao afeta sinal nem carteira; ficam de fora
# dos indices setoriais em vez de contamina-los com um chute.
DEIXAR_INDEFINIDO = set()


def construir_mapa_novo():
    mapa = {}
    for setor, tickers in SETORES.items():
        for t in tickers:
            if t in mapa:
                raise ValueError(f"{t} classificado em dois setores: {mapa[t]} e {setor}")
            mapa[t] = setor
    return mapa


def main():
    print("=" * 66)
    print(" BLOCO 4b -- ATUALIZACAO DO MAPEAMENTO SETORIAL")
    print("=" * 66)

    df = pd.read_csv(CAMINHO_MAPA)
    novo = construir_mapa_novo()

    antes_indefinidos = int((df["Setor"] == MARCADOR_VAZIO).sum())
    print(f"\nAntes: {len(df)} tickers, {antes_indefinidos} em '{MARCADOR_VAZIO}'")

    # 1. Preenche os que estao em "A DEFINIR" (nunca sobrescreve o que ja
    #    tem classificacao -- o script precisa ser seguro de rodar de novo).
    preenchidos = 0
    for i, linha in df.iterrows():
        if linha["Setor"] != MARCADOR_VAZIO:
            continue
        setor = novo.get(linha["Ticker"])
        if setor:
            df.at[i, "Setor"] = setor
            preenchidos += 1

    # 2. Acrescenta tickers do grafo que nem estavam no arquivo.
    existentes = set(df["Ticker"])
    novas_linhas = [
        {"Ticker": t, "Setor": s} for t, s in novo.items() if t not in existentes
    ]
    if novas_linhas:
        df = pd.concat([df, pd.DataFrame(novas_linhas)], ignore_index=True)

    df = df.sort_values("Ticker").reset_index(drop=True)
    df.to_csv(CAMINHO_MAPA, index=False)

    depois_indefinidos = int((df["Setor"] == MARCADOR_VAZIO).sum())
    print(f"Preenchidos: {preenchidos}")
    print(f"Acrescentados: {len(novas_linhas)} -> {[l['Ticker'] for l in novas_linhas]}")
    print(f"Depois: {len(df)} tickers, {depois_indefinidos} em '{MARCADOR_VAZIO}'")

    if depois_indefinidos:
        restantes = sorted(df[df["Setor"] == MARCADOR_VAZIO]["Ticker"])
        print(f"  ainda indefinidos (nao identificados com confianca): {restantes}")

    print("\nDistribuicao final:")
    print(df["Setor"].value_counts().to_string())

    # Verificacao que importa: o grafo inteiro tem setor?
    caminho_g = os.path.join(BASE_DIR, "fase 4 - sinal da sinapse", "grafo_manual_base.csv")
    caminho_h = os.path.join(BASE_DIR, "fase 4 - sinal da sinapse", "grafo_historico.csv")
    grafo = pd.read_csv(caminho_g)
    if os.path.exists(caminho_h):
        grafo = pd.concat([grafo, pd.read_csv(caminho_h)], ignore_index=True)
    empresas = set(grafo["empresa_A"]) | set(grafo["empresa_B"])

    mapa_final = dict(zip(df["Ticker"], df["Setor"]))
    sem_setor = sorted(
        t for t in empresas
        if mapa_final.get(t, MARCADOR_VAZIO) == MARCADOR_VAZIO
    )

    print(f"\nEmpresas do grafo sem setor: {len(sem_setor)} de {len(empresas)}")
    if sem_setor:
        print(f"  ATENCAO -- {sem_setor}")
        print("  Cada uma delas tem o choque limpo mal estimado e cai no")
        print("  balaio 'Outros' da trava setorial.")
    else:
        print("  OK -- todas as empresas do grafo tem setor definido.")


if __name__ == "__main__":
    main()
