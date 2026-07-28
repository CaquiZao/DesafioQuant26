"""
Bloco 2b do projeto SINAPSE: validar o universo de liquidez (proxy) contra
a carteira OFICIAL do indice Ibovespa.

O Bloco 2 (s2_universo.py) cria um "proxy" do Ibovespa: as 100 acoes mais
negociadas (por volume financeiro) de cada mes. Mas o Ibovespa DE VERDADE
nao e escolhido so por volume -- a B3 usa um criterio proprio (indice de
negociabilidade em 12 meses + governanca), e a carteira oficial tem menos
de 100 acoes (normalmente 80-90).

Este script confere quao perto o nosso proxy chega da carteira real, pra
um periodo em que temos a composicao oficial em maos: o 1o quadrimestre
de 2021 (jan-abr/2021), baixada do site da B3.

O que o script faz, passo a passo:
1. Le a carteira oficial do Ibovespa (arquivo extraido do site da B3,
   fora do repo -- ver CAMINHO_CARTEIRA_IBOV).
2. Le o universo de liquidez do Bloco 2 (nosso proxy) para os mesmos meses.
3. Compara mes a mes: quantas acoes batem, quantas sobram no proxy (estao
   no proxy mas nao no Ibovespa real) e quantas faltam (estao no Ibovespa
   real mas nao aparecem no proxy naquele mes).
4. Faz tambem uma comparacao CONSOLIDADA: junta os 4 meses do proxy (a
   carteira oficial e fixa no quadrimestre inteiro) pra ver se, ao longo
   do periodo todo, alguma acao do Ibovespa real fica de fora o tempo
   inteiro (isso sim seria um problema serio do proxy).
5. Salva um CSV com o detalhamento e imprime um relatorio de conferencia.
"""

import os

import pandas as pd

# ------------------------------------------------------------------
# 1) CONFIGURACOES GERAIS
# ------------------------------------------------------------------

# Arquivo com a carteira OFICIAL do Ibovespa (extraido do site da B3 --
# a pagina de "carteira teorica" do 1o quadrimestre de 2021). Fica FORA
# do repo, por isso o caminho e absoluto e especifico desta maquina --
# mesma logica do PASTA_COTAHIST no s2_universo.py.
CAMINHO_CARTEIRA_IBOV = (
    r"C:\Users\Jvssv\Desktop\desafio_itau_quant_pessoal\carteira_ibov_extraida_2021.csv"
)

# Arquivo gerado pelo Bloco 2 (nosso proxy de liquidez).
CAMINHO_UNIVERSO = os.path.join("data", "universo", "universo_mensal.parquet")

# Meses cobertos pela carteira oficial que baixamos (1o quadrimestre 2021).
# A carteira e FIXA nesses 4 meses -- a B3 so reajusta a cada quadrimestre.
MESES_QUADRIMESTRE = ["2021-01", "2021-02", "2021-03", "2021-04"]

# Pasta de saida (fora do repo -- ja esta no .gitignore).
PASTA_SAIDA = os.path.join("data", "validacao")
NOME_ARQUIVO_SAIDA = "comparacao_proxy_vs_ibov.csv"


# ------------------------------------------------------------------
# 2) CARREGAR OS DOIS LADOS DA COMPARACAO
# ------------------------------------------------------------------

def carregar_carteira_ibov(caminho):
    """
    Le a carteira oficial do Ibovespa (CSV ja extraido do site da B3) e
    devolve o conjunto de tickers que compoem o indice. A ultima linha
    do arquivo original e sempre o total geral (nao e um ticker de
    verdade), entao removemos ela por posicao.
    """
    if not os.path.exists(caminho):
        print("ERRO: nao encontrei o arquivo da carteira oficial do Ibovespa.")
        print(f"Caminho procurado: {os.path.abspath(caminho)}")
        return None

    carteira = pd.read_csv(caminho, encoding="utf-8")
    carteira = carteira.iloc[:-1].copy()  # remove a linha de total geral
    return set(carteira["codigo"])


def carregar_universo(caminho):
    """Le o parquet do Bloco 2 (universo de liquidez, mes a mes)."""
    if not os.path.exists(caminho):
        print("ERRO: nao encontrei o universo do Bloco 2.")
        print(f"Caminho procurado: {os.path.abspath(caminho)}")
        print("Rode primeiro o s2_universo.py para gerar esse arquivo.")
        return None

    return pd.read_parquet(caminho, engine="pyarrow")


# ------------------------------------------------------------------
# 3) COMPARAR PROXY x CARTEIRA OFICIAL
# ------------------------------------------------------------------

def comparar_mes_a_mes(universo, tickers_ibov_real, meses):
    """
    Para cada mes da lista, compara o universo (proxy) daquele mes com
    a carteira oficial do Ibovespa. Devolve uma tabela com uma linha por
    mes: quantos tickers batem, quantos sobram no proxy, quantos faltam.
    """
    linhas = []
    for mes in meses:
        tickers_proxy_mes = set(universo[universo["mes"] == mes]["ticker"])

        bateram = tickers_proxy_mes & tickers_ibov_real
        sobra_no_proxy = tickers_proxy_mes - tickers_ibov_real
        falta_no_proxy = tickers_ibov_real - tickers_proxy_mes

        linhas.append(
            {
                "mes": mes,
                "tickers_no_proxy": len(tickers_proxy_mes),
                "tickers_no_ibov_real": len(tickers_ibov_real),
                "bateram": len(bateram),
                "sobra_no_proxy": len(sobra_no_proxy),
                "falta_no_proxy": len(falta_no_proxy),
                "tickers_que_faltaram": sorted(falta_no_proxy),
            }
        )

    return pd.DataFrame(linhas)


def comparar_consolidado(universo, tickers_ibov_real, meses):
    """
    Junta (uniao) o proxy de TODOS os meses do quadrimestre num unico
    conjunto -- ja que a carteira oficial e fixa no periodo inteiro --
    e compara com o Ibovespa real. Isso responde a pergunta mais
    importante: ao longo do quadrimestre todo, alguma acao do Ibovespa
    real NUNCA apareceu no proxy?
    """
    tickers_proxy_uniao = set(universo[universo["mes"].isin(meses)]["ticker"])

    bateram = tickers_proxy_uniao & tickers_ibov_real
    sobra_no_proxy = sorted(tickers_proxy_uniao - tickers_ibov_real)
    falta_no_proxy = sorted(tickers_ibov_real - tickers_proxy_uniao)

    return {
        "tickers_proxy_uniao": len(tickers_proxy_uniao),
        "tickers_ibov_real": len(tickers_ibov_real),
        "bateram": len(bateram),
        "sobra_no_proxy": sobra_no_proxy,
        "falta_no_proxy": falta_no_proxy,
    }


# ------------------------------------------------------------------
# 4) RELATORIO DE SANIDADE
# ------------------------------------------------------------------

def imprimir_relatorio(tabela_mes_a_mes, resultado_consolidado):
    print("\n===== VALIDACAO DO PROXY x CARTEIRA OFICIAL DO IBOVESPA =====")
    print(f"Periodo comparado: {MESES_QUADRIMESTRE[0]} a {MESES_QUADRIMESTRE[-1]}")
    print(f"Tickers na carteira oficial do Ibovespa: {resultado_consolidado['tickers_ibov_real']}")

    print("\n--- Comparacao mes a mes ---")
    for _, linha in tabela_mes_a_mes.iterrows():
        print(
            f"  {linha['mes']}: {linha['bateram']} bateram, "
            f"{linha['sobra_no_proxy']} sobrando no proxy, "
            f"{linha['falta_no_proxy']} faltando no proxy "
            f"({linha['tickers_que_faltaram']})"
        )

    print("\n--- Comparacao consolidada (uniao do proxy nos 4 meses) ---")
    print(
        f"Tickers unicos no proxy (uniao): {resultado_consolidado['tickers_proxy_uniao']}"
    )
    print(f"Bateram com o Ibovespa real: {resultado_consolidado['bateram']}")
    print(
        f"Sobraram no proxy, nao estao no Ibovespa real "
        f"({len(resultado_consolidado['sobra_no_proxy'])}): "
        f"{resultado_consolidado['sobra_no_proxy']}"
    )
    print(
        f"Faltaram no proxy (estao no Ibovespa real mas nunca apareceram "
        f"no proxy no quadrimestre inteiro) "
        f"({len(resultado_consolidado['falta_no_proxy'])}): "
        f"{resultado_consolidado['falta_no_proxy']}"
    )

    if not resultado_consolidado["falta_no_proxy"]:
        print(
            "\n=> Nenhuma acao do Ibovespa real ficou de fora do proxy no "
            "quadrimestre inteiro -- cobertura de 100% (a sobra de tickers "
            "e esperada, ja que o proxy tem 100 acoes e o Ibovespa real tem menos)."
        )


# ------------------------------------------------------------------
# 5) FUNCAO PRINCIPAL
# ------------------------------------------------------------------

def main():
    tickers_ibov_real = carregar_carteira_ibov(CAMINHO_CARTEIRA_IBOV)
    if tickers_ibov_real is None:
        return

    universo = carregar_universo(CAMINHO_UNIVERSO)
    if universo is None:
        return

    tabela_mes_a_mes = comparar_mes_a_mes(universo, tickers_ibov_real, MESES_QUADRIMESTRE)
    resultado_consolidado = comparar_consolidado(universo, tickers_ibov_real, MESES_QUADRIMESTRE)

    os.makedirs(PASTA_SAIDA, exist_ok=True)
    caminho_saida = os.path.join(PASTA_SAIDA, NOME_ARQUIVO_SAIDA)
    tabela_mes_a_mes.to_csv(caminho_saida, index=False)
    print(f"\nDetalhamento mes a mes salvo em: {caminho_saida}")

    imprimir_relatorio(tabela_mes_a_mes, resultado_consolidado)


if __name__ == "__main__":
    main()
