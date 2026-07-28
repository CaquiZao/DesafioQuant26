# Aqui está o resumo do que foi inserido no PARAMETROS.md (você pode usar exatamente essa didática na banca):

## Janela da Regressão (12 meses / 252 dias úteis):

- **Por que esse valor:** A regressão isola o choque idiossincrático (o tombo que é culpa só da empresa) do choque de mercado/setor. Se a janela for muito curta (1 mês), uma temporada de balanços distorce tudo. Se for muito longa (5 anos), estamos usando a empresa de 2021 para tentar explicar a de 2026. A literatura acadêmica de finanças convergiu para 12 meses diários como o padrão-ouro de estabilidade para cálculo de betas. Não tínhamos motivo real para reinventar isso.

## Corte de Winsorização (2% no total: percentis 1% e 99%):

- **Por que esse valor:** O mercado tem "caudas gordas" (eventos insanos). Um boato de fusão faz a ação subir 60% num dia. Modelos de regressão enlouquecem com isso, dando peso excessivo ao ruído. A winsorização apenas coloca um teto nesses 1% mais loucos. Se não cortássemos (0%), nosso backtest dependeria da sorte de meia dúzia de dias bizarros. Se cortássemos muito (5%), jogaríamos fora o próprio sinal real da SINAPSE num universo pequeno de 100 ações. 1% de cada lado é a medida exata.

## Trava Máxima por Nome (5%):

- **Por que esse valor:** A estratégia da SINAPSE depende do volume estatístico da rede (muitos elos com um atrasinho sistemático), e não de acertar na mosca o destino de uma única empresa. 5% de teto força o robô a alocar o dinheiro em pelo menos 20 posições simultâneas (já que a inteligência extrairá ~300 elos). É a prova para a banca de que gerimos risco e de que o resultado vem da estrutura, não de uma "aposta direcional".

## Trava Máxima por Setor (25%):

- **Por que esse valor:** O Brasil é muito concentrado em commodities. Num superciclo de minério, todas as siderúrgicas, mineradoras e logísticas disparam. Se não travarmos em 25%, o robô colocaria 80% do dinheiro num único fator (China) e o modelo pararia de ser um stat-arb sofisticado para virar um fundo de commodities disfarçado. 25% obriga o capital a caçar atrasos em pelo menos 4 setores diferentes (Bancos, Varejo, Saúde, Energia).

## Trava de Liquidez (10% do ADTV - Volume Médio Diário):

- **Por que esse valor:** Essa é a principal defesa contra "backtest irrealista". Os maiores atrasos da SINAPSE acontecem em empresas pequenas e ilíquidas. Se nosso fundo comprasse R$ 5 milhões numa empresa que negocia apenas R$ 10 milhões por dia, nossa própria compra faria o preço disparar e destruiria o lucro na vida real (slippage / impacto de mercado). Gestoras limitam as ordens entre 10% e 15% do volume. Assumir o rigoroso teto de 10% cala qualquer avaliador que duvide da viabilidade de execução do fundo.

## Vol-Targeting (Alvo de 12% Anualizado):

- **Por que esse valor:** Usar alvo de volatilidade mata a necessidade de tentarmos prever a curva de juros ou a macroeconomia. Ao fixar o risco em 12% (sweet-spot de fundos Quant e Long-Short institucionais), o robô se blinda automaticamente. Em pânicos globais, a volatilidade sobe; o algoritmo reage cortando drasticamente o tamanho das posições, e você se protege sem usar previsão subjetiva.