import pandas as pd
import numpy as np
import os
import sys

# Ensure src is in the python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.s5_portfolio_builder import PortfolioBuilder

def main():
    print("Iniciando a execução do Bloco 5: Construção da Carteira...")
    
    # Paths (adjusting for execution from the root or inside the folder)
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    data_dir = os.path.join(base_dir, 'data')
    
    sinal_path = os.path.join(data_dir, 'sinal_sinapse.parquet')
    retornos_path = os.path.join(data_dir, 'precos', 'retornos_diarios.parquet')
    setores_path = os.path.join(base_dir, 'fase 4 - sinal da sinapse', 'mapeamento_setores.csv')
    
    # 1. Carregar dados
    print("Carregando sinal_sinapse.parquet...")
    df_zscore = pd.read_parquet(sinal_path)
    
    print("Carregando retornos_diarios.parquet...")
    df_returns = pd.read_parquet(retornos_path)
    
    # Aligning returns to the Z-scores (z-scores might have a subset of tickers/dates)
    df_returns, _ = df_returns.align(df_zscore, join='right')
    
    print("Carregando mapeamento_setores.csv...")
    if os.path.exists(setores_path):
        df_sectors = pd.read_csv(setores_path)
        df_sectors = df_sectors.set_index('Ticker') if 'Ticker' in df_sectors.columns else None
    else:
        df_sectors = None
        print("AVISO: mapeamento_setores.csv não encontrado. Trava setorial não será aplicada.")
        
    # TODO: No futuro, carregar ADTV e Betas salvos nos blocos anteriores.
    # Por enquanto, rodaremos sem as travas de liquidez (ou com mock) e sem o hedge (ou com mock).
    # Vamos gerar mock betas (ex: beta = 1.0 para todas as ações) para testar o IBOV_SYNTHETIC.
    df_betas = pd.DataFrame(1.0, index=df_zscore.index, columns=df_zscore.columns)
    
    # Construir a carteira com o construtor padrão (100M AUM)
    print("Instanciando PortfolioBuilder (AUM = 100M)...")
    pb = PortfolioBuilder(aum=100_000_000)
    
    print("Calculando pesos da carteira...")
    df_weights_final = pb.build_portfolio(
        df_zscore=df_zscore, 
        df_returns=df_returns, 
        df_adtv=None,  # Passando None para pular trava de liquidez caso ADTV não esteja disponível
        df_betas=df_betas, 
        df_sectors=df_sectors
    )
    
    output_path = os.path.join(data_dir, 'df_weights_sinapse.parquet')
    print(f"Salvando df_weights_final em {output_path}...")
    df_weights_final.to_parquet(output_path)
    
    print("Concluído!")
    print(f"Dimensões do output: {df_weights_final.shape}")
    
if __name__ == "__main__":
    main()
