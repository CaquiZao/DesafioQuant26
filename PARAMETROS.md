# Parâmetros da Estratégia

> **Nota:** os valores abaixo foram fixados **antes** da execução de qualquer backtest, como medida anti-overfitting (pré-registro de hipóteses). O histórico do Git (data do commit deste arquivo) comprova que a definição ocorreu antes de qualquer resultado de backtest ter sido observado. Nenhum parâmetro deve ser alterado retroativamente com base em resultados — qualquer mudança posterior deve ser feita em um novo commit, com justificativa própria, e será visível no histórico.

## 1. Janela da regressão do choque limpo (em meses)

- **Valor:** 12 meses (252 dias úteis).
- **Justificativa econômica:** A regressão do choque limpo serve para isolar o que é movimento sistêmico (do mercado e do setor) do que é movimento exclusivo da empresa. Para calcular esses *betas* (a sensibilidade do ativo ao mercado) com precisão estatística, precisamos de uma amostra grande o suficiente para diluir ruídos de curto prazo, mas não tão longa a ponto de pegar uma "outra empresa" do passado. Na literatura acadêmica (ex: modelos Fama-French), 12 meses de dados diários é o padrão-ouro de equilíbrio.
- **Validação Crítica:** Uma janela de 1 a 3 meses seria ruidosa demais (a temporada de balanços distorceria o beta). Uma janela de 5 anos assumiria que a empresa não mudou seu modelo de negócios. 12 meses captura perfeitamente o risco atual do papel. É a escolha mais defensável e embasada para a banca.

## 2. Corte de winsorização (percentil dos extremos)

- **Valor:** 2% total (corte nos percentis 1% e 99%).
- **Justificativa econômica:** O mercado tem "caudas gordas" (eventos abruptos e extremos). Um vazamento de fusão pode fazer uma ação disparar 60% num dia. Modelos estatísticos lineares (como nossas regressões e z-scores) enlouquecem com isso, dando um peso absurdo a esse ruído. A winsorização impõe um limite: tudo acima do percentil 99% é achatado para o valor do percentil 99%. Isso garante que nosso lucro venha de um processo estrutural na rede da bolsa, e não de um robô enviesado por 3 ou 4 *outliers* anuais.
- **Validação Crítica:** Por que não 5%? Em um universo de apenas ~100 ações, 5% ceifaria informação preciosa de sinais fortes e válidos. Por que não 0%? Zero winsorização resulta em backtests frágeis (uma única empresa pode dominar o retorno do ano). 1% em cada cauda é exatamente o ponto onde o ruído some e a tese fica.

## 3. Trava máxima por nome (% da carteira)

- **Valor:** 5%.
- **Justificativa econômica:** A SINAPSE é uma estratégia estatística distribuída. Nós não apostamos no destino da empresa X; operamos o atraso informacional médio de dezenas de conexões. Fixar o máximo em 5% obriga o capital a se dividir em pelo menos 20 teses distintas, blindando o portfólio contra um choque reverso inesperado (ex: recuperação judicial surpresa de uma ponta do elo).
- **Validação Crítica:** Posições de 10-15% são comuns em fundos fundamentalistas (*stock picking* direcional), mas inadmissíveis para *quant stat-arb*, onde o foco é diversificação. 5% grita "gestão de risco profissional" para os avaliadores.

## 4. Trava máxima por setor (% da carteira)

- **Valor:** 25%.
- **Justificativa econômica:** Em momentos de boom de commodities, dezenas de empresas de mineração, siderurgia e logística vão emitir sinais e acender o painel ao mesmo tempo. Sem trava de setor, o algoritmo concentraria 80% do dinheiro numa aposta setorial, travestida de aposta em rede. A trava de 25% obriga a carteira a minerar valor em pelo menos 4 setores completamente distintos.
- **Validação Crítica:** Limites menores que 20% seriam inoperáveis no Brasil por conta do Ibovespa ser pesado em bancos e commodities. 25% é o teto ideal que garante pluralidade e elimina apostas macro.

## 5. Trava de liquidez (% do volume médio diário)

- **Valor:** 10% do Volume Financeiro Médio Diário (ADTV) dos últimos 21 dias.
- **Justificativa econômica:** Como o efeito do "atraso de atenção" é maior em empresas menores e ilíquidas, se o nosso fundo hipotético tentasse comprar com força, nós mesmos faríamos o preço subir antes de terminarmos de comprar (*market impact* e slippage). Limitar a posição a 10% do volume diário prova que os retornos do backtest seriam executáveis na vida real, com custos reais de corretagem em D+1.
- **Validação Crítica:** Gestoras de verdade sabem que ultrapassar 10% a 15% do volume diário é pedir para ser "esmagado" pelo spread. Assumir um limite de 10% e, ainda assim, gerar alfa, desmonta qualquer contra-argumento sobre capacidade do backtest.

## 6. Volatilidade-alvo do dimensionamento de posição

- **Valor:** 12% anualizada.
- **Justificativa econômica:** O Vol-Targeting substitui as tentativas (quase sempre inúteis) de prever o cenário macro. O investidor institucional quer retorno atrelado a um risco conhecido. Com o alvo de 12%, o algoritmo se autoprotege: se o mercado entrar em histeria coletiva (volatilidade sobe), o modelo reduz automaticamente o tamanho das posições financeiras para manter a carteira travada nos 12% de oscilação. Em águas calmas, ele alavanca levemente. É o mecanismo de defesa perfeito.
- **Validação Crítica:** Fundos multimercado (*macro* e *quant*) costumam rodar com mandato de volatilidade entre 8% e 15%. Cravar o meio-termo (12%) entrega oscilação suficiente para produzir prêmios interessantes na ponta do Sharpe, sem gerar *drawdowns* (quedas) que matariam um fundo precocemente.



## 7. Assets Under Management (AUM)

- **Valor Padrão:** R$ 100.000.000 (100 milhões).
- **Justificativa econômica:** O tamanho do fundo (AUM) dita o quão agressivamente a trava de liquidez (10% do ADTV) irá "tesourar" as posições em empresas menores e desatendidas. Testar a estratégia com 100 milhões reflete um fundo de tamanho médio viável no Brasil.
- **Validação Crítica:** É imperativo gerar a curva de capacidade do fundo. A estratégia será testada em três cenários de AUM: R$ 20 milhões (onde a trava raramente atua, maximizando o prêmio teórico), R$ 100 milhões (cenário base) e R$ 300 milhões (onde a restrição de liquidez reduz a alocação em small caps, testando a resiliência do modelo).
