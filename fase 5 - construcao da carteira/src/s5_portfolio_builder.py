import pandas as pd
import numpy as np

class PortfolioBuilder:
    def __init__(self, aum=100_000_000, target_vol=0.12, max_weight_name=0.05, max_weight_sector=0.25, max_adtv_pct=0.10, vol_window=60):
        self.aum = aum
        self.target_vol = target_vol
        self.max_weight_name = max_weight_name
        self.max_weight_sector = max_weight_sector
        self.max_adtv_pct = max_adtv_pct
        self.vol_window = vol_window
        
    def build_portfolio(self, df_zscore, df_returns, df_adtv, df_betas, df_sectors):
        """
        Constrói a matriz de pesos da carteira aplicando as regras institucionais.
        
        Args:
            df_zscore (pd.DataFrame): Sinal final do bloco 4 (Z-scores).
            df_returns (pd.DataFrame): Retornos diários das ações.
            df_adtv (pd.DataFrame): Volume médio diário negociado (21 dias).
            df_betas (pd.DataFrame): Betas diários de 252 dias contra o IBOV.
            df_sectors (pd.DataFrame): Mapeamento de Ticker -> Setor. Index deve ser 'Ticker'.
            
        Returns:
            pd.DataFrame: df_weights final com lag t+1 aplicado.
        """
        # 1. Rankeamento e Lado (Z-score cru já serve como direção de força)
        df_raw_weights = df_zscore.copy()
        
        # 2. Vol-Targeting
        df_weights = self._apply_vol_targeting(df_raw_weights, df_returns)

        # 3. Travas Institucionais
        df_weights = self._apply_institutional_locks(df_weights, df_adtv, df_sectors)
        
        # 4. Beta-Neutro
        df_weights = self._apply_beta_hedge(df_weights, df_betas)
        
        # 5. Lag de Execução t+1
        df_weights_final = df_weights.shift(1)
        
        return df_weights_final

    def _apply_vol_targeting(self, df_weights, df_returns):
        # Para evitar endogeneidade (pesos do target dependendo da vol do portfolio iterativo), 
        # utilizamos uma estimativa de variância baseada no rolling std das ações individuais.
        df_vol = df_returns.rolling(self.vol_window).std() * np.sqrt(252)
        
        # Variância proxy: assume correlação nula por simplicidade, ou o escalar limitará.
        # Vol do portfólio = sqrt( sum( (w_i * vol_i)^2 ) )
        port_vol_proxy = np.sqrt((df_weights**2 * df_vol**2).sum(axis=1))
        port_vol_proxy = port_vol_proxy.replace(0, np.nan)
        
        scalar = self.target_vol / port_vol_proxy
        scalar = scalar.fillna(1.0)
        
        # Limitando alavancagem máxima/mínima para evitar explosões 
        scalar = scalar.clip(lower=0.1, upper=3.0)
        
        return df_weights.multiply(scalar, axis=0)

    def _apply_institutional_locks(self, df_weights, df_adtv, df_sectors):
        # a. Trava de Liquidez (ADTV) - executada primeiro para podar ações ilíquidas logo de cara
        if df_adtv is not None and not df_adtv.empty:
            limit_w = (df_adtv * self.max_adtv_pct) / self.aum
            limit_w, df_weights_aligned = limit_w.align(df_weights, join='right')
            df_weights = df_weights_aligned.clip(lower=-limit_w, upper=limit_w)

        # b. Trava de % Max por nome
        df_weights = df_weights.clip(lower=-self.max_weight_name, upper=self.max_weight_name)
        
        # c. Trava de Setor
        if df_sectors is not None and not df_sectors.empty:
            sectors = df_sectors['Setor'].to_dict() if 'Setor' in df_sectors.columns else {}
            
            for date, row in df_weights.iterrows():
                sector_sums = {}
                for ticker, w in row.items():
                    if pd.isna(w) or w == 0: continue
                    sec = sectors.get(ticker, 'Outros')
                    sector_sums[sec] = sector_sums.get(sec, 0) + abs(w)
                
                # Scale down proporções
                for ticker, w in row.items():
                    if pd.isna(w) or w == 0: continue
                    sec = sectors.get(ticker, 'Outros')
                    if sector_sums[sec] > self.max_weight_sector:
                        scale = self.max_weight_sector / sector_sums[sec]
                        df_weights.at[date, ticker] = w * scale
                        
        return df_weights

    def _apply_beta_hedge(self, df_weights, df_betas):
        # Portfolio Beta = sum(weight_i * beta_i)
        # O ativo IBOV_SYNTHETIC vai ter peso de -Portfolio Beta
        if df_betas is not None and not df_betas.empty:
            df_betas_aligned, df_weights_aligned = df_betas.align(df_weights, join='right')
            port_beta = (df_weights_aligned * df_betas_aligned).sum(axis=1)
            df_weights['IBOV_SYNTHETIC'] = -port_beta
        else:
            df_weights['IBOV_SYNTHETIC'] = 0.0
            
        return df_weights

if __name__ == "__main__":
    pass
