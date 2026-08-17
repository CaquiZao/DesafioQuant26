import pandas as pd
import numpy as np

class PortfolioBuilder:
    def __init__(self, aum=100_000_000, target_vol=0.12, max_weight_name=0.05, max_weight_sector=0.25, max_adtv_pct=0.10, vol_window=60, max_leverage=3.0, n_iteracoes_vol=3, janela_suavizacao_pesos=63):
        self.aum = aum
        self.target_vol = target_vol
        self.max_weight_name = max_weight_name
        self.max_weight_sector = max_weight_sector
        self.max_adtv_pct = max_adtv_pct
        self.vol_window = vol_window
        self.max_leverage = max_leverage
        # Quantas rodadas de (calibrar vol -> reaplicar travas). As travas cortam
        # os pesos e derrubam a vol calibrada, então uma rodada só não converge:
        # medido em 03/08, a vol caía de 31% para 6,3% depois das travas.
        self.n_iteracoes_vol = n_iteracoes_vol
        # Média móvel aplicada aos PESOS FINAIS (não ao sinal). Suavizar o
        # sinal no Bloco 4 não basta: o escalar de vol-targeting e as travas
        # mudam todo dia e reintroduzem giro. Suavizar o que é de fato
        # negociado é o que controla o giro e, portanto, a capacidade.
        #
        # 63 pregões (16/08), era 10. A justificativa mudou de natureza junto
        # com o horizonte do sinal: o Bloco 4 passou a acumular o choque em
        # 12-1 meses, então a carteira-alvo é intrinsecamente lenta e não faz
        # sentido negociá-la com uma janela de 2 semanas. A janela de pesos
        # deve ser da ordem do horizonte do sinal, não um número calibrado.
        #
        # NOTA HISTORICA: o valor antigo (10) foi escolhido por maximizar o
        # Sharpe numa varredura -- era a unica linha do repositorio que
        # documentava escolha de parametro por resultado. A justificativa
        # agora e estrutural.
        self.janela_suavizacao_pesos = janela_suavizacao_pesos
        
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
        df_weights = df_zscore.copy()

        # 2/3. Vol-Targeting e Travas Institucionais, alternados.
        # As travas cortam pesos e derrubam a volatilidade calibrada, então
        # calibrar uma vez só entrega uma carteira muito abaixo do alvo. Aqui
        # alternamos as duas etapas, SEMPRE terminando nas travas -- os limites
        # institucionais (liquidez, 5% por nome, 25% por setor) são inegociáveis
        # e têm a palavra final. Se eles impedirem chegar ao alvo de vol, a
        # carteira fica abaixo do alvo mesmo: é uma restrição real, não um bug.
        for _ in range(self.n_iteracoes_vol):
            df_weights = self._apply_vol_targeting(df_weights, df_returns)
            df_weights = self._apply_institutional_locks(df_weights, df_adtv, df_sectors)

        # 3b. Suavização dos pesos finais (controle de giro).
        df_weights = self._suavizar_pesos(df_weights)

        # 3c. Reaplicar as travas DEPOIS de suavizar.
        #
        # A versão anterior pulava esta etapa, apoiada no argumento de que a
        # média móvel é uma combinação convexa de carteiras que já respeitam
        # os limites, e |média(w)| <= média(|w|). Esse argumento é válido --
        # mas SÓ para limites CONSTANTES no tempo (5% por nome, 25% por
        # setor).
        #
        # A trava de liquidez não é constante: o limite do dia t depende do
        # ADTV do dia t. A média dos pesos dos últimos 10 pregões pode
        # perfeitamente estourar o limite de HOJE se o volume negociado caiu
        # nesse intervalo. Medido em 04/08: 60,5% dos dias tinham ao menos
        # uma posição acima do permitido, com até 74% do book em posições
        # ilegais no pior dia -- incluindo posições em ações que não
        # negociaram nada naquele pregão (limite zero).
        #
        # Isso não é um detalhe contábil: significava um backtest com
        # posições que não seriam executáveis na vida real, exatamente a
        # crítica que a trava de liquidez existe para evitar.
        df_weights = self._apply_institutional_locks(df_weights, df_adtv, df_sectors)

        # 3d. Máscara de negociabilidade.
        #
        # Uma ação que deixou de ser negociada (delistada, suspensa) não tem
        # retorno no dia. Se ela ficar com peso, a posição consome limite de
        # risco e de setor, entra no cálculo de volatilidade, mas rende
        # exatamente zero -- uma "posição fantasma".
        #
        # Isso precisa vir DEPOIS da suavização, e não antes: a média móvel
        # dos 10 pregões anteriores ressuscita o peso de uma ação que parou
        # de negociar, do mesmo jeito que ressuscitava pesos acima da trava
        # de liquidez (ver passo 3c). Zerar o sinal na entrada não basta.
        #
        # Não há look-ahead: a decisão do dia t usa a informação de que a
        # ação negociou em t, e o peso só é executado em t+1 (shift abaixo).
        # É a mesma premissa de qualquer mesa -- só se manda ordem de papel
        # que está negociando.
        df_weights = self._mascarar_nao_negociaveis(df_weights, df_returns)

        # 4. Beta-Neutro
        df_weights = self._apply_beta_hedge(df_weights, df_betas)

        # 5. Lag de Execução t+1
        df_weights_final = df_weights.shift(1)

        return df_weights_final

    def _suavizar_pesos(self, df_weights):
        """
        Média móvel dos pesos finais, para controlar o giro (turnover).

        O sinal da Sinapse é um choque de UM dia e praticamente não tem
        persistência, então a carteira-alvo muda quase por completo todo
        pregão. Negociar isso literalmente custaria mais que todo o alfa.
        A média móvel transforma a carteira-alvo em "a média das últimas
        `janela` carteiras", que é o que dá para sustentar na prática.
        """
        if not self.janela_suavizacao_pesos or self.janela_suavizacao_pesos <= 1:
            return df_weights
        return df_weights.rolling(window=self.janela_suavizacao_pesos, min_periods=1).mean()

    def _mascarar_nao_negociaveis(self, df_weights, df_returns):
        """
        Zera o peso de cada ação nos dias em que ela não tem retorno --
        isto é, não está sendo negociada.

        Sem isso, o backtest carrega posições em papéis delistados ou
        suspensos: elas ocupam espaço nas travas e na conta de risco, mas
        não podem gerar nem perda nem ganho. Medido em 04/08: ~2% do book
        em média, mesmo no grafo só de sobreviventes.
        """
        if df_returns is None or df_returns.empty:
            return df_weights

        negociavel = df_returns.reindex(
            index=df_weights.index, columns=df_weights.columns
        ).notna()

        # GUARDA DE FERIADO (16/08). A base de retornos contem linhas de dias
        # em que a bolsa NAO abriu -- 02/11 (Finados), 15/10, etc. -- com um ou
        # dois tickers preenchidos por ruido de fonte. Sem esta guarda, a
        # mascara lia isso como "130 acoes pararam de negociar de uma vez" e
        # ZERAVA a carteira inteira, com rebuild completo no dia seguinte.
        #
        # Medido: 11 liquidacoes completas, giro de ate 1,77 num unico dia
        # (duas pontas). A 5 bps era quase invisivel; com custo realista cada
        # evento custa ~0,5%.
        #
        # O criterio nao e calibrado: num pregao real ~335 tickers tem retorno;
        # nesses dias, UM. Qualquer corte entre os dois separa o feriado do
        # evento de mercado. 10% da mediana e conservador com folga -- nao ha
        # dia real de bolsa em que 90% do universo pare de negociar.
        # Referencia MOVEL, nao mediana global: o universo cresce ao longo do
        # tempo (46 nomes em 2017, 152 em 2022), entao uma mediana global
        # subestima o limiar no fim da amostra e o superestima no comeco.
        #
        # O limiar de 10% da mediana global tinha uma ZONA CEGA de 24 dias: em
        # pregoes reais contaminados por feriado fantasma do yfinance a
        # cobertura caia para ~51 nomes, acima do corte de 15,8 -- e a guarda
        # nao disparava. Com a causa raiz corrigida em `s1_precos.py` isso nao
        # deveria mais acontecer; esta camada e a defesa em profundidade.
        #
        # 60% da mediana movel: medido, o MENOR valor de cobertura/mediana
        # movel entre dias legitimos e 93,4%. O corte tem folga de 33 pontos
        # percentuais -- nao existe risco de falso positivo.
        # DUAS condicoes, e a segunda existe porque a primeira sozinha tem
        # falso positivo: num universo pequeno, UMA acao deslistando derruba a
        # cobertura tanto quanto um feriado. Foi o teste
        # `test_acao_delistada_nao_carrega_posicao_fantasma` (2 tickers) que
        # expos isso -- a guarda preservava o peso da acao morta.
        #
        # "Cobertura desabou" so distingue feriado de deslistagem quando a
        # secao transversal e grande o bastante para a estatistica significar
        # alguma coisa. Com 158 nomes, uma acao morrendo move 0,6%; com 2
        # nomes, move 50%.
        MIN_UNIVERSO_GUARDA = 20
        por_dia = negociavel.sum(axis=1)
        referencia = (por_dia.rolling(252, min_periods=20).median()
                      .fillna(por_dia.median()))
        dia_util = (por_dia >= (referencia * 0.60).clip(lower=1.0)) | \
                   (referencia < MIN_UNIVERSO_GUARDA)
        if (~dia_util).any():
            print(f"  mascara de negociabilidade: {int((~dia_util).sum())} dia(s) sem "
                  f"pregao efetivo preservados (nao se liquida a carteira em feriado)")
        negociavel = negociavel.where(dia_util, other=True, axis=0)

        return df_weights.where(negociavel, 0.0)

    def _estimar_vol_portfolio(self, df_weights, df_returns):
        """
        Volatilidade anualizada do portfólio, estimada com a matriz de
        covariância REALIZADA da janela.

        A versão anterior usava `sqrt(sum((w_i * vol_i)^2))`, que assume
        correlação ZERO entre as ações -- premissa falsa que subestimava a vol
        do book e fazia a calibração errar o alvo por um fator de ~2,6x
        (entregava 31% quando o alvo era 12%). Aqui usamos w' * Cov * w, que
        captura a correlação de verdade.

        A janela vai de t-vol_window até t-1 (exclui o próprio dia t), então
        não há look-ahead.
        """
        colunas = [c for c in df_weights.columns if c in df_returns.columns]
        matriz_pesos = df_weights[colunas].fillna(0.0).to_numpy(dtype=float)
        matriz_retornos = df_returns[colunas].reindex(df_weights.index).fillna(0.0).to_numpy(dtype=float)

        vols = np.full(len(matriz_pesos), np.nan)
        for i in range(self.vol_window, len(matriz_pesos)):
            janela = matriz_retornos[i - self.vol_window:i]
            covariancia = np.cov(janela, rowvar=False)
            pesos = matriz_pesos[i]
            variancia = float(np.atleast_2d(covariancia).dot(pesos).dot(pesos))
            vols[i] = np.sqrt(max(variancia, 0.0) * 252)

        return pd.Series(vols, index=df_weights.index)

    def _apply_vol_targeting(self, df_weights, df_returns):
        port_vol = self._estimar_vol_portfolio(df_weights, df_returns)

        scalar = self.target_vol / port_vol.replace(0, np.nan)
        scalar = scalar.replace([np.inf, -np.inf], np.nan).fillna(1.0)

        # Limitando alavancagem máxima/mínima para evitar explosões
        scalar = scalar.clip(lower=0.1, upper=self.max_leverage)

        return df_weights.multiply(scalar, axis=0)

    def _apply_institutional_locks(self, df_weights, df_adtv, df_sectors):
        # a. Trava de Liquidez (ADTV) - executada primeiro para podar ações ilíquidas logo de cara
        #
        # BUG CORRIGIDO (16/08): `clip` com limite NaN NAO CORTA -- ele devolve o
        # valor original. Verificado em pandas 3.0.1:
        #     pd.Series([10.0]).clip(lower=pd.Series([nan]), upper=pd.Series([nan])) -> 10.0
        # Como o indice do ADTV nao cobre todos os dias/tickers da matriz de pesos
        # (36 dias fora do indice, mais celulas com ADTV ausente), 353 posicoes
        # escapavam silenciosamente da trava.
        #
        # ADTV ausente significa "nao sabemos se da para negociar", e a resposta
        # conservadora para isso e limite ZERO, nao limite infinito.
        # SEGUNDA CORRECAO (16/08): `fillna(0)` sozinho era GROSSEIRO DEMAIS.
        # O ADTV vem do COTAHIST, que tem calendario proprio -- ha dias que
        # existem na matriz de pesos e nao existem no arquivo de ADTV. Nesses
        # dias o limite virava ZERO para TODOS os tickers e a carteira inteira
        # era LIQUIDADA, com rebuild no dia seguinte.
        #
        # Medido: 21 liquidacoes completas apos o aquecimento, cada uma com giro
        # de ate 1,30 (duas pontas). A 5 bps isso e invisivel; com custo realista
        # cada round trip custa ~0,8%.
        #
        # A liquidez de uma acao nao evapora porque falta uma linha no arquivo.
        # `ffill` carrega o ultimo ADTV conhecido pelo buraco de calendario; o
        # `fillna(0)` que sobra continua valendo para ticker que nunca teve ADTV
        # -- que e o caso em que "nao sabemos se da para negociar" deve mesmo
        # significar limite zero.
        if df_adtv is not None and not df_adtv.empty:
            limit_w = (df_adtv * self.max_adtv_pct) / self.aum
            limit_w, df_weights_aligned = limit_w.align(df_weights, join='right')
            limit_w = limit_w.ffill().fillna(0.0)
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
        """
        Beta da carteira = soma(peso_i * beta_i). O IBOV_SYNTHETIC recebe peso
        -beta_carteira, zerando a exposicao ao mercado.

        BUG CORRIGIDO (16/08): `.sum()` do pandas ignora NaN por padrao, entao
        beta DESCONHECIDO virava contribuicao ZERO. Na pratica: a posicao
        entrava no book e o hedge fingia que ela tinha beta nulo. Medido em
        producao: 12.629 de 93.022 posicoes-dia (13,6%), equivalentes a 9,3% da
        exposicao bruta, e um beta residual da estrategia de -0,031 (t = -4,57).

        Nao se hedgeia o que nao se mede: a posicao sem beta valido e ZERADA,
        em vez de entrar sem protecao. E a escolha conservadora -- deixar de
        ganhar num nome e melhor que carregar exposicao de mercado nao medida
        numa estrategia vendida como neutra.
        """
        if df_betas is None or df_betas.empty:
            df_weights['IBOV_SYNTHETIC'] = 0.0
            return df_weights

        df_betas_aligned, df_weights_aligned = df_betas.align(df_weights, join='right')

        # Elegibilidade: so entra quem tem beta medido.
        sem_beta = df_betas_aligned.isna() & (df_weights_aligned.abs() > 0)
        n_zeradas = int(sem_beta.sum().sum())
        if n_zeradas:
            ativas = int((df_weights_aligned.abs() > 0).sum().sum())
            print(f"  hedge de beta: {n_zeradas} posicoes-dia sem beta valido "
                  f"({n_zeradas / max(ativas, 1):.1%} das ativas) foram zeradas")
        df_weights = df_weights_aligned.where(~sem_beta, 0.0)

        port_beta = (df_weights * df_betas_aligned).sum(axis=1)

        # Safeguard: depois da mascara, nenhuma posicao ativa pode ter beta NaN.
        residual = (df_betas_aligned.isna() & (df_weights.abs() > 0)).sum().sum()
        assert residual == 0, f"{residual} posicoes ativas ainda sem beta apos a mascara"

        df_weights['IBOV_SYNTHETIC'] = -port_beta
        return df_weights

if __name__ == "__main__":
    pass
