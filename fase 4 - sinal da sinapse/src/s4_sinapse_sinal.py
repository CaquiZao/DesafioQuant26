import pandas as pd
import numpy as np
import statsmodels.api as sm
from statsmodels.regression.rolling import RollingOLS
import os

"""
Bloco 4: Sinal da Sinapse
Este script processa a engenharia da estratégia, calculando os choques limpos 
das ações (extraindo resíduos da regressão com Ibov e Setor), propagando o 
sinal pelo Grafo de Ligações Econômicas e normalizando a saída final.
"""

# Constantes definidas rigorosamente no PARAMETROS.md
JANELA_REGRESSAO_DIAS = 252
WINSORIZATION_LIMIT = 0.02 # recortes de 1% nas caudas (superior e inferior)

# Janela (em pregões) da média móvel aplicada ao sinal final.
# O choque diário não tem persistência nenhuma (autocorrelação ~0), então usar
# o sinal cru significa remontar a carteira inteira todo dia: ~139% de giro
# diário, o que a 5bps custa ~8,7% ao ano e consome 100% do alfa bruto.
# Suavizar em 21 pregões derruba o giro para ~6,6%/dia preservando a maior
# parte do alfa -- foi o horizonte de melhor Sharpe numa varredura de 1 a 126
# dias (ver diagnóstico de 03/08).
JANELA_SUAVIZACAO = 21

def carregar_dados():
    """
    Passo 4.1: Carrega os dados históricos e o Grafo Manual.
    """
    print("Iniciando ingestao de dados (Retornos, Indices e Grafo)...")
    
    base_dir = os.path.dirname(__file__)
    data_dir = os.path.join(base_dir, '..', '..', 'data', 'precos')
    
    # Preferimos a base COMPLETA (Bloco 1c), que inclui as acoes ja
    # deslistadas e portanto nao tem vies de sobrevivencia. Se ela ainda
    # nao foi gerada, caimos na base so-yfinance do Bloco 1.
    caminho_retornos = os.path.join(data_dir, 'retornos_diarios_completo.parquet')
    if not os.path.exists(caminho_retornos):
        print("AVISO: base completa nao encontrada -- usando a base com vies de sobrevivencia.")
        caminho_retornos = os.path.join(data_dir, 'retornos_diarios.parquet')
    caminho_indices = os.path.join(data_dir, 'indices_retornos.parquet')
    caminho_grafo = os.path.join(base_dir, '..', 'grafo_manual_base.csv')
    # Elos com empresas que MORRERAM durante o periodo (Kroton, B2W, Cielo,
    # Hering, Gol...). Sem eles o grafo so enxerga sobreviventes: um analista
    # em 2016 teria escrito exatamente essas relacoes, e nao saberia quais
    # iriam quebrar. Ver `Registros dos processos/acomp_04_08_sessao2.md` (P2).
    caminho_grafo_hist = os.path.join(base_dir, '..', 'grafo_historico.csv')
    caminho_map = os.path.join(base_dir, '..', 'mapeamento_setores.csv')

    df_retornos = pd.read_parquet(caminho_retornos)
    df_indices = pd.read_parquet(caminho_indices)

    df_grafo = pd.DataFrame(columns=['empresa_A', 'empresa_B', 'tipo_de_elo', 'forca', 'direcao'])
    if os.path.exists(caminho_grafo):
        df_grafo = pd.read_csv(caminho_grafo)
        print(f"Grafo carregado com {len(df_grafo)} elos.")

    # Os dois arquivos sao mantidos separados de proposito: um descreve a
    # bolsa de hoje, o outro as relacoes que existiram e acabaram. Juntar
    # num arquivo so esconderia quais elos vieram da correcao do vies.
    if os.path.exists(caminho_grafo_hist):
        df_hist = pd.read_csv(caminho_grafo_hist)
        df_grafo = pd.concat([df_grafo, df_hist], ignore_index=True)
        print(f"Grafo historico (empresas mortas): +{len(df_hist)} elos "
              f"-> {len(df_grafo)} no total.")
        # Um elo cuja empresa deixou de existir para de gerar sinal sozinho:
        # `montar_sinal_propagado` trata choque ausente como zero. Nao ha
        # necessidade de coluna de vigencia.
        
    df_map = pd.DataFrame(columns=['TICKER', 'Setor B3'])
    if os.path.exists(caminho_map):
        df_map = pd.read_csv(caminho_map)
        
    return df_retornos, df_indices, df_grafo, df_map

def calcular_choque_limpo(df_retornos, df_indices, df_map, tickers_alvo=None):
    """
    Passo 4.2: Isola o Choque Limpo extraindo a maré sistêmica.
    Regressão: Retorno_A = alpha + beta1 * Retorno_Ibovespa + beta2 * Retorno_Setor + resíduo(ε)

    `tickers_alvo` limita a regressão às ações de que realmente precisamos
    (as do grafo). Os índices setoriais continuam sendo calculados com o
    universo INTEIRO -- só a regressão, que é a parte cara, é restrita.
    Sem isso, rodaríamos 543 regressões rolling para usar ~44.
    """
    print(f"Calculando Índices Sintéticos e Choques Limpos (Regressão Rolling {JANELA_REGRESSAO_DIAS} dias)...")
    
    # 1. Calcula Retornos Setoriais Sintéticos
    # O CSV mapeamento_setores foi acordado ter 2 colunas, Ticker e Setor B3
    # Vamos adaptar pros nomes das colunas
    col_ticker = df_map.columns[0]
    col_setor = df_map.columns[1]
    ticker_to_sector = dict(zip(df_map[col_ticker], df_map[col_setor]))
    
    # Prepara dataframe de resíduos e de betas (beta contra o IBOV, mesma
    # regressão rolling -- guardado pra servir de hedge no Bloco 5)
    df_choques = pd.DataFrame(index=df_retornos.index, columns=df_retornos.columns)
    df_betas = pd.DataFrame(index=df_retornos.index, columns=df_retornos.columns)

    # Ibovespa
    if 'IBOV' not in df_indices.columns:
        print("Erro: Índice IBOV não encontrado em indices_retornos.parquet")
        return df_choques, df_betas
        
    ibov = df_indices['IBOV']

    if tickers_alvo is None:
        tickers_para_regredir = list(df_retornos.columns)
    else:
        tickers_para_regredir = [t for t in df_retornos.columns if t in set(tickers_alvo)]
    print(f"  regredindo {len(tickers_para_regredir)} tickers (universo total: {len(df_retornos.columns)})")

    for ticker in tickers_para_regredir:
        setor = ticker_to_sector.get(ticker, "Desconhecido")
        
        # Cria índice setorial sintético (média dos retornos de todas ações do mesmo setor, excluindo a própria ação)
        tickers_setor = [t for t, s in ticker_to_sector.items() if s == setor and t in df_retornos.columns and t != ticker]
        
        if len(tickers_setor) > 0:
            retorno_setor = df_retornos[tickers_setor].mean(axis=1)
        else:
            # Se não há pares no setor, usa 0 (o beta setorial será ignorado)
            retorno_setor = pd.Series(0, index=df_retornos.index)
            
        y = df_retornos[ticker].dropna()
        if len(y) < JANELA_REGRESSAO_DIAS + 10:
            continue
            
        # Alinha as variáveis
        X = pd.DataFrame({'const': 1, 'IBOV': ibov, 'SETOR': retorno_setor}).loc[y.index]
        X = X.fillna(0) # Trata possíveis NAs
        
        try:
            model = RollingOLS(endog=y, exog=X, window=JANELA_REGRESSAO_DIAS, min_nobs=JANELA_REGRESSAO_DIAS)
            res = model.fit(params_only=True)
            # O resíduo diário é y[t] - (X[t] * params[t]).
            y_pred = (X * res.params).sum(axis=1)
            residuo = y - y_pred
            df_choques[ticker] = residuo
            df_betas[ticker] = res.params['IBOV']
        except Exception as e:
            print(f"Aviso: Erro na regressão de {ticker}. Ignorando.")

    return df_choques, df_betas

def montar_sinal_propagado(df_choques, df_grafo):
    """
    Passo 4.3: Propaga o choque limpo através dos elos mapeados.
    sinal_bruto_B = Choque_limpo_A * força_do_elo * direcao_prevista
    """
    print("Propagando choques pelo grafo para gerar sinais nas empresas satélites...")
    
    empresas_alvo = df_grafo['empresa_B'].unique()
    df_sinais_brutos = pd.DataFrame(0.0, index=df_choques.index, columns=empresas_alvo)
    
    for _, row in df_grafo.iterrows():
        empresa_a = row['empresa_A']
        empresa_b = row['empresa_B']
        forca = row['forca']
        direcao = row['direcao']
        
        if empresa_a in df_choques.columns:
            # Multiplica o choque idossincrático de A pela força e direção do elo
            choque_a = df_choques[empresa_a].fillna(0)
            sinal = choque_a * forca * direcao
            
            if empresa_b in df_sinais_brutos.columns:
                df_sinais_brutos[empresa_b] += sinal
                
    return df_sinais_brutos

def limpar_e_winsorizar_sinal(df_sinais_brutos):
    """
    Passo 4.4: Limpa extremos irreais e padroniza a intensidade do sinal (z-score transversal diário).
    """
    print(f"Aplicando winsorização rigorosa de {WINSORIZATION_LIMIT*100}% e gerando Z-Score transversal...")
    
    df_sinal_limpo = df_sinais_brutos.copy()
    
    # 0.0 significa ausência de sinal, ignoramos no Z-score para não puxar a média
    df_sinal_limpo = df_sinal_limpo.replace(0.0, np.nan)
    
    # Winsorize cross-sectionally (cada dia corta os 1% piores outliers de cima e baixo)
    lower_limit = WINSORIZATION_LIMIT / 2
    upper_limit = 1 - lower_limit
    
    for idx, row in df_sinal_limpo.iterrows():
        if row.isna().all():
            continue
        p_low = row.quantile(lower_limit)
        p_high = row.quantile(upper_limit)
        df_sinal_limpo.loc[idx] = row.clip(lower=p_low, upper=p_high)
        
    # Z-score transversal
    mean = df_sinal_limpo.mean(axis=1)
    std = df_sinal_limpo.std(axis=1).replace(0, 1) # Evita div por zero
    
    df_sinal_final = df_sinal_limpo.sub(mean, axis=0).div(std, axis=0)
    
    # Preenche NaN de volta com 0
    df_sinal_final = df_sinal_final.fillna(0)

    return df_sinal_final

def suavizar_sinal(df_sinal_final, janela=JANELA_SUAVIZACAO):
    """
    Passo 4.5: Suaviza o sinal com média móvel de `janela` pregões.

    O choque limpo é uma informação de UM dia; usado cru, ele faz a carteira
    se reinventar diariamente e o custo de transação engole todo o alfa. A
    média móvel transforma "o choque de hoje" em "a convicção acumulada das
    últimas `janela` sessões", que é o que de fato se sustenta no tempo.

    Não há look-ahead: `rolling` só olha para trás.
    """
    if janela <= 1:
        return df_sinal_final

    print(f"Suavizando o sinal com média móvel de {janela} pregões (controle de giro)...")
    return df_sinal_final.rolling(window=janela, min_periods=1).mean()

def pipeline_bloco_4():
    print("="*50)
    print(" INICIANDO MOTOR: SINAL DA SINAPSE (BLOCO 4)")
    print("="*50)
    
    df_retornos, df_indices, df_grafo, df_map = carregar_dados()

    # Precisamos do choque das empresas GATILHO (empresa_A, que originam o
    # sinal) e do beta das SATELITES (empresa_B, que entram na carteira e
    # precisam de hedge no Bloco 5).
    tickers_do_grafo = set(df_grafo['empresa_A']) | set(df_grafo['empresa_B'])
    df_choques, df_betas = calcular_choque_limpo(
        df_retornos, df_indices, df_map, tickers_alvo=tickers_do_grafo
    )

    df_sinais_brutos = montar_sinal_propagado(df_choques, df_grafo)

    df_sinal_final = limpar_e_winsorizar_sinal(df_sinais_brutos)

    df_sinal_final = suavizar_sinal(df_sinal_final)

    # Exportação do Output
    data_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'data')
    os.makedirs(data_dir, exist_ok=True)
    caminho_output = os.path.join(data_dir, 'sinal_sinapse.parquet')
    caminho_betas = os.path.join(data_dir, 'betas_sinapse.parquet')

    df_sinal_final.to_parquet(caminho_output, engine="pyarrow")
    df_betas.to_parquet(caminho_betas, engine="pyarrow")

    print(f"\n[SUCESSO] Bloco 4 Concluído. Matriz de sinais salva em:\n{caminho_output}")
    print(f"Matriz de betas (IBOV) salva em:\n{caminho_betas}")

if __name__ == "__main__":
    pipeline_bloco_4()
