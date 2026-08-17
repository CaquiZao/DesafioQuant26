"""
Bloco 1c do projeto SINAPSE: retornos diarios SEM VIES DE SOBREVIVENCIA.

O PROBLEMA QUE ESTE SCRIPT RESOLVE
----------------------------------
O `retornos_diarios.parquet` do Bloco 1 vem do yfinance, que so entrega
preco de empresa que AINDA existe. Das 253 acoes que o Bloco 2 identificou
como liquidas entre 2016 e 2025, so 166 tinham preco -- faltavam 87, e 65
delas eram justamente as que MORRERAM (Kroton, Cielo, B2W, Hering, Linx,
NotreDame, Gol, Estacio, Lojas Americanas...).

Testar a estrategia so nas sobreviventes e trapacear sem querer: em 2016
ninguem sabia quais empresas iriam quebrar. O backtest fica otimista.

A SOLUCAO
---------
O COTAHIST da B3 tem preco de TODA acao que ja negociou, inclusive as
deslistadas. O Bloco 2 (unico autorizado a ler COTAHIST) ja exporta esses
precos em `precos_cotahist.parquet`. Aqui nos:

1. Mantemos o yfinance como fonte PRIMARIA nas 166 acoes que ele cobre --
   os precos dele ja vem ajustados por proventos e desdobramentos, o que
   o COTAHIST nao oferece.
2. Preenchemos SO as acoes ausentes com o COTAHIST, depois de limpar os
   defeitos conhecidos do preco bruto (ver `construir_retornos_cotahist`).

QUALIDADE DA FONTE COTAHIST (medido em 04/08 contra o yfinance nas 166
acoes cobertas pelas duas fontes, ja com a limpeza aplicada):
  - correlacao diaria mediana: 0,993
  - desvio da diferenca:       0,0096  (era 0,4486 sem a limpeza)
  - vies sistematico:          0,00% ao ano
Sobram ~9 acoes com correlacao baixa, todas casos de cisao/evento
societario complexo (PCAR3/Assai, NATU3, AMER3, OIBR4...) que o preco
bruto nao tem como capturar -- mas essas 9 estao no yfinance, entao nao
entram por esta porta.
"""

import os

import pandas as pd

# ------------------------------------------------------------------
# 1) CONFIGURACOES
# ------------------------------------------------------------------

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_DIR = os.path.join(BASE_DIR, "data")

CAMINHO_RETORNOS_YF = os.path.join(DATA_DIR, "precos", "retornos_diarios.parquet")
CAMINHO_PRECOS_COTAHIST = os.path.join(DATA_DIR, "precos", "precos_cotahist.parquet")
CAMINHO_SAIDA = os.path.join(DATA_DIR, "precos", "retornos_diarios_completo.parquet")

# Razoes de preco tipicas de desdobramento/grupamento. Um grupamento de
# 1:50 (ex: PDGR3) faz o preco bruto pular 50x num dia -- sem tratar,
# isso vira um "retorno" de +4900% que contamina tudo.
FATORES_SPLIT = [2, 3, 4, 5, 6, 8, 10, 12, 15, 20, 25, 30, 40, 50, 100, 200, 500, 1000]
LIMIAR_RETORNO_SPLIT = 0.35   # so investiga variacoes acima disso
TOLERANCIA_SPLIT = 0.12       # a razao nao bate exata: a acao tambem se mexe no dia

# Acao de centavos tem ruido de arredondamento brutal: de R$0,02 pra
# R$0,03 e "+50%" que nao significa nada economicamente.
PRECO_MINIMO = 1.0

# Teto de retorno diario, so como rede de seguranca pra eventos societarios
# nao mapeados (cisao, incorporacao) que escapam da deteccao de split.
LIMITE_RETORNO_DIARIO = 0.50

MINIMO_PREGOES_VALIDOS = 250


# ------------------------------------------------------------------
# 2) LIMPEZA DO PRECO BRUTO DO COTAHIST
# ------------------------------------------------------------------

def detectar_splits(precos):
    """
    Marca (data, ticker) onde a variacao de preco parece desdobramento ou
    grupamento, e nao movimento economico de verdade.

    O criterio tem que valer nas DUAS pontas ao mesmo tempo: a variacao
    tem que ser grande E a razao entre os precos tem que cair perto de um
    fator simples (2x, 10x, 1/50...). Exigir as duas coisas evita marcar
    como split uma acao que simplesmente caiu 40% num dia de crise.
    """
    razao = precos / precos.shift(1)
    variacao_grande = (razao - 1).abs() > LIMIAR_RETORNO_SPLIT

    perto_de_fator = pd.DataFrame(False, index=precos.index, columns=precos.columns)
    for fator in FATORES_SPLIT:
        for alvo in (float(fator), 1.0 / fator):
            perto_de_fator |= (razao - alvo).abs() <= TOLERANCIA_SPLIT * alvo

    return variacao_grande & perto_de_fator


def construir_retornos_cotahist(precos):
    """
    Converte o preco bruto do COTAHIST em retorno diario utilizavel:
      1. neutraliza os desdobramentos/grupamentos detectados (retorno 0 no
         dia do evento -- o investidor nao ganhou nem perdeu nada ali);
      2. descarta dias de acao de centavos (ruido de arredondamento);
      3. corta caudas extremas que sobraram (evento societario nao mapeado).
    """
    retornos = precos.pct_change().mask(detectar_splits(precos), 0.0)

    negociavel = (precos >= PRECO_MINIMO) & (precos.shift(1) >= PRECO_MINIMO)
    retornos = retornos.where(negociavel)

    return retornos.clip(-LIMITE_RETORNO_DIARIO, LIMITE_RETORNO_DIARIO)


# ------------------------------------------------------------------
# 3) UNIAO DAS DUAS FONTES
# ------------------------------------------------------------------

def montar_retornos_completos(retornos_yf, precos_cotahist):
    """
    Junta as duas fontes. O yfinance MANDA nas acoes que ele cobre (ja vem
    ajustado por proventos); o COTAHIST entra so nas que faltam.

    Devolve (tabela_final, tickers_recuperados).
    """
    retornos_cotahist = construir_retornos_cotahist(precos_cotahist)

    # So aproveita ticker com historico util -- serie de 3 pregoes nao
    # ajuda em nada e ainda suja o calculo de setor/correlacao.
    suficientes = retornos_cotahist.notna().sum() >= MINIMO_PREGOES_VALIDOS
    retornos_cotahist = retornos_cotahist.loc[:, suficientes[suficientes].index]

    faltantes = [t for t in retornos_cotahist.columns if t not in retornos_yf.columns]

    completos = retornos_yf.join(retornos_cotahist[faltantes], how="outer")
    completos = completos.sort_index()

    # CALENDARIO OFICIAL DA B3 -- causa raiz de tres bugs anteriores.
    #
    # O painel do yfinance traz 36 datas que NAO sao pregao na B3 (Carnaval,
    # Corpus Christi, Finados, Consciencia Negra, 25/01...). Elas nao existem
    # no COTAHIST, que e o arquivo oficial da bolsa.
    #
    # O dano nao esta no dia fantasma em si -- esta no dia SEGUINTE: 27 dessas
    # linhas vem com preco NaN, e o `pct_change` do Bloco 1 propaga o NaN para
    # o primeiro pregao REAL seguinte. Resultado medido: em 25 pregoes
    # legitimos, so ~50 dos 214 tickers da carteira tinham retorno (mediana
    # 158). O Bloco 5 lia isso como "110 acoes pararam de negociar" e ZERAVA a
    # carteira, com rebuild completo no dia seguinte.
    #
    # Isso explica por que tres correcoes anteriores (clip com NaN, ffill do
    # ADTV, guarda de feriado) quase nao mexeram no resultado: os tres
    # disparavam nas MESMAS datas e eram redundantes. Enquanto o retorno do dia
    # seguinte continuasse NaN, a carteira zerava de qualquer jeito.
    #
    # Filtramos aqui alem do Bloco 1 porque ESTE e o arquivo que os Blocos 3, 4
    # e 5 consomem -- e o Bloco 1 depende de rede, entao pode nao ter rodado.
    calendario = precos_cotahist.index
    antes = len(completos)
    completos = completos.loc[completos.index.isin(calendario)]
    if antes != len(completos):
        print(f"  calendario da B3: {antes - len(completos)} data(s) fantasma removida(s) "
              f"({antes} -> {len(completos)} pregoes)")

    return completos, faltantes


# ------------------------------------------------------------------
# 4) MAIN
# ------------------------------------------------------------------

def main():
    print("Passo 1: carregando as duas fontes de preco...")
    retornos_yf = pd.read_parquet(CAMINHO_RETORNOS_YF)
    print(f"  yfinance (ajustado):  {retornos_yf.shape[1]} tickers, {retornos_yf.shape[0]} pregoes")

    if not os.path.exists(CAMINHO_PRECOS_COTAHIST):
        raise FileNotFoundError(
            f"{CAMINHO_PRECOS_COTAHIST} nao existe. Rode o Bloco 2 "
            "(s2_universo.py) primeiro -- e ele que extrai os precos do COTAHIST."
        )
    precos_cotahist = pd.read_parquet(CAMINHO_PRECOS_COTAHIST)
    print(f"  COTAHIST (bruto):     {precos_cotahist.shape[1]} tickers, {precos_cotahist.shape[0]} pregoes")

    print("\nPasso 2: limpando o preco bruto e unindo as fontes...")
    eventos_split = detectar_splits(precos_cotahist)
    print(
        f"  desdobramentos/grupamentos neutralizados: {int(eventos_split.sum().sum())} "
        f"em {int((eventos_split.sum() > 0).sum())} tickers"
    )

    completos, recuperados = montar_retornos_completos(retornos_yf, precos_cotahist)
    print(f"  tickers recuperados do COTAHIST: {len(recuperados)}")
    print(f"  exemplos: {sorted(recuperados)[:12]}")

    print("\nPasso 3: salvando...")
    completos.to_parquet(CAMINHO_SAIDA, engine="pyarrow")
    print(f"  {completos.shape[1]} tickers, {completos.shape[0]} pregoes")
    print(f"  salvo em: {CAMINHO_SAIDA}")

    # ------------------------------------------------------------------
    # Teste de sanidade: o vies de sobrevivencia diminuiu mesmo?
    # ------------------------------------------------------------------
    print("\n===== TESTE DE SANIDADE (VIES DE SOBREVIVENCIA) =====")
    caminho_universo = os.path.join(DATA_DIR, "universo", "universo_mensal.parquet")
    if os.path.exists(caminho_universo):
        universo = set(pd.read_parquet(caminho_universo)["ticker"].unique())
        antes = len(universo & set(retornos_yf.columns))
        depois = len(universo & set(completos.columns))
        print(f"Cobertura do universo point-in-time ({len(universo)} acoes):")
        print(f"  antes (so yfinance): {antes} ({antes/len(universo):.0%})")
        print(f"  agora:               {depois} ({depois/len(universo):.0%})")
        print(
            "\nAs acoes que aparecem agora sao as que QUEBRARAM ou sairam da "
            "bolsa. Incluir elas faz o backtest ficar mais REALISTA (e "
            "provavelmente mais modesto) -- e esse e exatamente o objetivo: "
            "medir o que a estrategia teria feito de verdade, sem a vantagem "
            "impossivel de saber de antemao quem ia sobreviver."
        )


if __name__ == "__main__":
    main()
