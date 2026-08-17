"""
Bloco 4c: camada de SUBSETOR no mapeamento setorial.

POR QUE ESTE SCRIPT EXISTE
--------------------------
O choque limpo do Bloco 4 sai de

    retorno = a + b1*IBOV + b2*SETOR + residuo

e chama o residuo de "choque idiossincratico". Ele so merece esse nome se
`SETOR` remover de fato o que a acao compartilha com as suas pares. Os 10
setores da B3 sao grosseiros demais para isso:

  - "Materiais Basicos" (25 tickers) junta minerio de ferro (VALE3), celulose
    (SUZB3), siderurgia (CSNA3) e quimica (BRKM5). Sao negocios que respondem
    a fatores globais diferentes -- minerio, preco de celulose em dolar,
    demanda de aco, nafta. A media dos 25 nao representa nenhum deles.
  - "Consumo Ciclico" (60 tickers) junta varejo de vestuario, construcao
    civil, educacao e aluguel de carros.

Consequencia medida em 04/08 (`s12_inferencia_e_breadth.py`, Etapa 2): as 49
posicoes ativas da carteira entregam apenas 11,3 APOSTAS INDEPENDENTES --
razao de 23%. O grafo e estruturalmente muito fragmentado (modularidade
0,922, 20 componentes), entao essa redundancia NAO vem da topologia: vem dos
choques co-movendo, porque o controle setorial deixou fator comum no residuo.

Breadth baixa custa duas coisas ao mesmo tempo:
  - teto de retorno ajustado a risco (IR ~ IC * raiz(breadth) = 0,49)
  - teto de VOLATILIDADE: com 11,3 apostas e trava de 5% por nome, a vol
    maxima alcancavel e 7,2% -- contra alvo de 12%. A vol medida e 7,84%.
    Ou seja, o gap de P4 e consequencia aritmetica da breadth, nao um
    problema separado.

Subsetor mais fino remove mais fator comum, os choques ficam mais
independentes, e a breadth sobe SEM ESCREVER UM UNICO ELO NOVO.

O QUE ESTE SCRIPT FAZ
---------------------
Acrescenta a coluna `Subsetor` ao `mapeamento_setores.csv`. Nao altera a
coluna `Setor` -- a trava setorial do Bloco 5 continua operando na
granularidade grossa, que e a correta para limite de concentracao (um limite
de risco por "Materiais Basicos" e mais conservador que um por "Mineracao").
So a REGRESSAO passa a usar o subsetor.

CRITERIO DE CLASSIFICACAO
-------------------------
Natureza economica do negocio: o que faz o preco da acao se mexer junto com
o das pares. Onde a B3 tem subsetor proprio, seguimos a B3; onde a divisao
util e mais fina que a da B3, dividimos (ex.: transmissao de energia separada
de geracao/distribuicao -- transmissao e receita regulada, parecida com
titulo de renda fixa; geracao depende de hidrologia e preco spot. Junta-las
e o mesmo erro, um nivel abaixo).

ISTO NAO E LOOK-AHEAD. A classificacao usa o que a empresa FAZ, informacao
estavel e disponivel na epoca: uma mineradora era mineradora em 2016. E a
mesma natureza da coluna `Setor` que ja existe.

TICKERS SEM SUBSETOR
--------------------
Ficam em "A DEFINIR" de proposito quando nao identifiquei a empresa com
confianca -- mesma regra que o `s4b` adotou para o setor: chute errado e
PIOR que ausencia, porque contamina o indice de dois subsetores ao mesmo
tempo. Quem fica sem subsetor cai automaticamente no setor, no Bloco 4.

DISCIPLINA ANTI-OVERFITTING
---------------------------
A taxonomia abaixo foi escrita UMA VEZ, antes de medir qualquer resultado, e
por natureza do negocio -- nao por tentativa e erro ate a breadth melhorar.
Iterar a classificacao olhando o resultado seria ajustar 255 parametros
categoricos no ruido, exatamente o erro que o protocolo IS/OOS da pendencia
P1 existe para bloquear. Se a breadth nao melhorar, o resultado negativo fica
registrado e o script permanece no repositorio como registro.

USO
---
    python "fase 4 - sinal da sinapse/src/s4c_subsetores.py"

Idempotente: so preenche o que esta ausente ou em "A DEFINIR".
"""

import importlib.util
import os

import pandas as pd

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CAMINHO_MAPA = os.path.join(BASE_DIR, "fase 4 - sinal da sinapse", "mapeamento_setores.csv")

MARCADOR_VAZIO = "A DEFINIR"


def _min_pares_do_bloco4():
    """
    Le `MIN_PARES_SUBSETOR` do proprio Bloco 4, que e quem de fato aplica a
    regra na regressao.

    Duplicar a constante aqui seria criar duas fontes de verdade que podem
    divergir em silencio -- o mesmo tipo de falha que ja mordeu este projeto
    duas vezes (caminho do mapa de setores em 03/08, "A DEFINIR" em 04/08).
    Melhor importar e quebrar alto se o Bloco 4 mudar de forma.
    """
    caminho = os.path.join(os.path.dirname(os.path.abspath(__file__)), "s4_sinapse_sinal.py")
    spec = importlib.util.spec_from_file_location("_s4_para_constante", caminho)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo.MIN_PARES_SUBSETOR


MIN_PARES_SUBSETOR = _min_pares_do_bloco4()


# ------------------------------------------------------------------
# Taxonomia de subsetores
# ------------------------------------------------------------------
# Cada chave e um subsetor; o valor e a lista de tickers. Tickers de uma
# mesma empresa em classes diferentes (PETR3/PETR4, ITUB3/ITUB4) ficam no
# mesmo subsetor, como e obvio -- e como ja estavam no setor.

SUBSETORES = {
    # ---------------- Materiais Basicos ----------------
    # A separacao que mais importa para o grafo: VALE3, CSNA3, SUZB3 e
    # KLBN11 estavam todos no mesmo "setor", e sao tres cadeias distintas.
    "Mineracao": [
        "VALE3", "VALE5", "BRAP4", "CMIN3", "MAGG3", "CBAV3",
    ],
    "Siderurgia": [
        "CSNA3", "GGBR3", "GGBR4", "GOAU4", "USIM5", "USIM3",
    ],
    "Papel e Celulose": [
        "SUZB3", "SUZB5", "FIBR3", "KLBN11", "KLBN4", "DTEX3", "DXCO3",
    ],
    "Quimicos": [
        "BRKM5", "UNIP6", "FHER3",
    ],
    "Materiais de Construcao": [
        "ETER3", "PTBL3",
    ],

    # ---------------- Petroleo, Gas e Biocombustiveis ----------------
    # PETR4 -> VBBR3 e PETR4 -> UGPA3 sao elos E&P -> distribuicao. Separar
    # os dois subsetores e o que impede o indice de "explicar" o elo antes
    # de ele existir.
    "Petroleo e Gas E&P": [
        "PETR3", "PETR4", "PRIO3", "RECV3", "RRRP3", "BRAV3", "ENAT3",
        "QGEP3", "DMMO3",
    ],
    "Distribuicao de Combustiveis": [
        "VBBR3", "BRDT3", "UGPA3",
    ],
    "Acucar e Etanol": [
        "CSAN3", "RAIZ4", "SMTO3",
    ],

    # ---------------- Utilidade Publica ----------------
    # Transmissao separada de geracao/distribuicao: receita regulada e
    # indexada (comporta-se como renda fixa longa) contra exposicao a
    # hidrologia e preco spot. Economicamente sao negocios diferentes.
    "Energia - Transmissao": [
        "TAEE11", "TAEE4", "TRPL4", "ISAE4", "ALUP11",
    ],
    "Energia - Geracao e Distribuicao": [
        "ELET3", "ELET6", "CMIG3", "CMIG4", "CPLE3", "CPLE5", "CPLE6",
        "CPFE3", "EGIE3", "ENBR3", "ENGI11", "EQTL3", "AESB3", "AURE3",
        "CESP6", "ELPL3", "ELPL4", "LIGT3", "NEOE3", "TIET11", "TBLE3",
        "ENEV3", "OMGE3", "SRNA3", "MEGA3", "CPRE3",
    ],
    "Saneamento e Ambiental": [
        "SBSP3", "SAPR4", "SAPR11", "CSMG3", "ORVR3", "AMBP3",
    ],
    "Gas": [
        "CGAS5",
    ],

    # ---------------- Financeiro ----------------
    "Bancos": [
        "ITUB3", "ITUB4", "BBDC3", "BBDC4", "BBAS3", "SANB11", "BPAC11",
        "ABCB4", "BRSR6", "BPAN4", "BMGB11", "BIDI4", "BIDI11", "PRBC4",
        "BBTG11",
    ],
    # Shoppings sao "Financeiro" na B3 (exploracao de imoveis), mas nao se
    # movem como banco. Aqui e onde a granularidade grossa mais distorcia.
    "Shoppings e Imoveis": [
        "MULT3", "IGTA3", "IGTI11", "BRML3", "ALSC3", "ALSO3", "ALOS3",
        "SYNE3", "BRPR3", "LOGG3",
    ],
    "Seguros e Previdencia": [
        "BBSE3", "PSSA3", "SULA11", "IRBR3", "CXSE3", "WIZS3",
    ],
    "Servicos Financeiros": [
        "B3SA3", "BVMF3", "CIEL3", "CTIP3",
    ],
    "Holdings": [
        "ITSA3", "ITSA4",
    ],

    # ---------------- Consumo Ciclico ----------------
    "Varejo de Vestuario": [
        "LREN3", "HGTX3", "CEAB3", "GUAR3", "AMAR3", "ARZZ3", "AZZA3",
        "SOMA3", "VULC3", "ALPA4", "GRND3", "LLIS3", "VIVA3", "LJQQ3",
    ],
    "Varejo Eletro e Ecommerce": [
        "MGLU3", "BHIA3", "VVAR3", "VVAR11", "VIIA3", "BTOW3", "LAME3",
        "LAME4", "AMER3", "MOSI3",
    ],
    "Construcao Civil": [
        "CYRE3", "EZTC3", "MRVE3", "DIRR3", "EVEN3", "GFSA3", "HBOR3",
        "JHSF3", "PDGR3", "RSID3", "TCSA3", "TEND3", "CURY3", "VIVR3",
        "ESPA3",
    ],
    "Educacao": [
        "KROT3", "ESTC3", "COGN3", "YDUQ3", "ANIM3", "SEER3", "SEDU3",
    ],
    "Aluguel de Veiculos": [
        "RENT3", "MOVI3", "LCAM3", "VAMO3",
    ],
    "Turismo, Lazer e Restaurantes": [
        "CVCB3", "SMFT3", "MEAL3", "BKBR3", "MPLU3", "CNTO3", "SBFG3",
    ],
    # NATU3 e o ticker antigo da Natura, antes da reorganizacao societaria
    # que criou a Natura &Co (NTCO3). Mesma empresa, mesmo negocio -- entram
    # juntas, como PETR3/PETR4.
    "Higiene e Varejo Especializado": [
        "NTCO3", "NATU3", "PETZ3",
    ],

    # ---------------- Consumo Nao Ciclico ----------------
    "Alimentos Processados": [
        "JBSS3", "MRFG3", "BEEF3", "BRFS3", "MBRF3", "MDIA3", "CAML3",
    ],
    "Bebidas": [
        "ABEV3",
    ],
    "Agricultura": [
        "SLCE3", "TTEN3",
    ],
    "Varejo Alimentar": [
        "PCAR3", "PCAR4", "CRFB3", "ASAI3", "GMAT3",
    ],

    # ---------------- Saude ----------------
    "Planos de Saude": [
        "GNDI3", "HAPV3", "QUAL3", "ODPV3",
    ],
    "Hospitais e Diagnostico": [
        "RDOR3", "ONCO3", "AALR3", "FLRY3", "PARD3", "BPHA3",
    ],
    "Farmacias e Medicamentos": [
        "RADL3", "PGMN3", "HYPE3",
    ],

    # ---------------- Bens Industriais ----------------
    "Maquinas e Equipamentos": [
        "WEGE3", "ROMI3", "KEPL3", "TASA4", "MILS3", "FJTA4", "INTB3",
        "AERI3",
    ],
    "Material de Transporte": [
        "EMBR3", "EMBJ3", "POMO4", "RAPT4", "TUPY3", "MYPK3", "LEVE3",
    ],
    "Transporte e Logistica": [
        "RAIL3", "RUMO3", "CCRO3", "ECOR3", "ARTR3", "STBP3", "PORT3",
        "TGMA3", "LOGN3", "HBSA3", "SIMH3", "TPIS3", "SEQL3", "MOTV3",
        "GGPS3",
    ],
    "Transporte Aereo": [
        "AZUL4", "GOLL4",
    ],

    # ---------------- Comunicacoes ----------------
    "Telecomunicacoes": [
        "VIVT3", "VIVT4", "TIMS3", "TIMP3", "OIBR3", "OIBR4", "FIQE3",
    ],

    # ---------------- Tecnologia ----------------
    "Software e Servicos de TI": [
        "TOTS3", "LINX3", "SQIA3", "CASH3", "BMOB3", "NGRD3", "CLSA3",
        "LWSA3", "CARD3",
    ],
    "Hardware e Equipamentos": [
        "POSI3", "VLID3",
    ],
}

# Tickers deliberadamente SEM subsetor (caem no setor no Bloco 4):
#   AXIA3/AXIA6/AXIA7 -- nao identifiquei a empresa com confianca. Estao em
#     "Materiais Basicos" pelo s4b; classificar errado contaminaria dois
#     subsetores. Nenhum esta no grafo.
#   PARC3 -- ja estava em "A DEFINIR" no setor pelo mesmo motivo.
#   SMLE3, SMLS3 -- Smiles (fidelidade aerea); negocio hibrido entre aereo e
#     servicos financeiros, nao ha subsetor obvio. Nao estao no grafo.


def montar_indice_ticker_subsetor():
    """Inverte o dicionario e falha alto se um ticker aparecer em dois."""
    indice = {}
    for subsetor, tickers in SUBSETORES.items():
        for ticker in tickers:
            if ticker in indice:
                raise ValueError(
                    f"{ticker} classificado em dois subsetores: "
                    f"'{indice[ticker]}' e '{subsetor}'. Corrija a taxonomia."
                )
            indice[ticker] = subsetor
    return indice


def main():
    print("=" * 70)
    print(" BLOCO 4c -- camada de SUBSETOR no mapeamento setorial")
    print("=" * 70)

    indice = montar_indice_ticker_subsetor()
    print(f"\nTaxonomia: {len(SUBSETORES)} subsetores, {len(indice)} tickers classificados.")

    df = pd.read_csv(CAMINHO_MAPA, encoding="utf-8")
    if "Subsetor" not in df.columns:
        df["Subsetor"] = MARCADOR_VAZIO
    df["Subsetor"] = df["Subsetor"].fillna(MARCADOR_VAZIO)

    antes = int((df["Subsetor"] != MARCADOR_VAZIO).sum())

    # Idempotente: so preenche o que esta vazio, nunca sobrescreve.
    vazio = df["Subsetor"] == MARCADOR_VAZIO
    df.loc[vazio, "Subsetor"] = df.loc[vazio, "Ticker"].map(indice).fillna(MARCADOR_VAZIO)

    depois = int((df["Subsetor"] != MARCADOR_VAZIO).sum())
    total = len(df)

    df.to_csv(CAMINHO_MAPA, index=False, encoding="utf-8")

    print(f"\nTickers com subsetor: {antes} -> {depois} (de {total})")
    sem = df.loc[df["Subsetor"] == MARCADOR_VAZIO, "Ticker"].tolist()
    if sem:
        print(f"Sem subsetor de proposito ({len(sem)}): {', '.join(sorted(sem))}")

    # Tickers da taxonomia que nao existem no mapa -- so aviso, nao erro: o
    # universo muda entre execucoes e a taxonomia pode estar a frente.
    ausentes = sorted(set(indice) - set(df["Ticker"]))
    if ausentes:
        print(f"\nNa taxonomia mas fora do mapa ({len(ausentes)}): {', '.join(ausentes)}")

    # Contagem por SUBSETOR, nao por (Setor, Subsetor). Alguns subsetores
    # cruzam a fronteira de setor de proposito -- VAMO3 e "Bens Industriais"
    # na B3 mas aluga veiculo igual a RENT3, e AMBP3 e industrial mas opera
    # saneamento. Para a REGRESSAO o que vale e o negocio, entao eles entram
    # no mesmo indice. A trava setorial do Bloco 5 continua usando `Setor` e
    # nao e afetada por isso.
    print("\nTamanho de cada subsetor (o que vira indice na regressao):\n")
    validos = df.loc[df["Subsetor"] != MARCADOR_VAZIO]
    contagem = validos.groupby("Subsetor").size().sort_values(ascending=False)
    for subsetor, n in contagem.items():
        setores = sorted(validos.loc[validos["Subsetor"] == subsetor, "Setor"].unique())
        origem = setores[0] if len(setores) == 1 else f"{len(setores)} setores"
        alerta = "  <- poucos pares, cai no setor" if n < MIN_PARES_SUBSETOR else ""
        print(f"  {n:>3}  {subsetor:<34} ({origem}){alerta}")

    n_uteis = int((contagem >= MIN_PARES_SUBSETOR).sum())
    tickers_uteis = int(contagem[contagem >= MIN_PARES_SUBSETOR].sum())
    print(f"\nSubsetores com pelo menos {MIN_PARES_SUBSETOR} membros: "
          f"{n_uteis} de {len(contagem)}, cobrindo {tickers_uteis} tickers.")
    print("Os demais caem no setor no Bloco 4 -- indice de 2 ou 3 acoes seria")
    print("ruidoso demais para servir de controle.")

    print(f"\nMapa salvo em: {CAMINHO_MAPA}")
    print("\nProximo passo: rodar o Bloco 4, que passa a usar `Subsetor` na")
    print("regressao do choque limpo (com fallback para `Setor` onde houver")
    print("poucos pares).")


if __name__ == "__main__":
    main()
