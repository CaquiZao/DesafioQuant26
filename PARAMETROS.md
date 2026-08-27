# Parâmetros da Estratégia

> **Nota:** os valores abaixo foram fixados **antes** da execução de qualquer backtest, como medida anti-overfitting (pré-registro de hipóteses). O histórico do Git (data do commit deste arquivo) comprova que a definição ocorreu antes de qualquer resultado de backtest ter sido observado. Nenhum parâmetro deve ser alterado retroativamente com base em resultados — qualquer mudança posterior deve ser feita em um novo commit, com justificativa própria, e será visível no histórico.

---

## Como ler este documento

| parte | o que é | data |
|---|---|---|
| **Parte I** (§1–7) | os 7 parâmetros **pré-registrados**, com o texto original preservado | 21/07/2026 |
| **Parte II** (§8–12) | parâmetros **acrescentados depois**, que não existiam no pré-registro | 16/08/2026 |
| **Parte III** | o que foi **testado e não adotado** | 16/08/2026 |

**Nenhum valor da Parte I foi alterado.** Onde a medição posterior contradisse a *justificativa*
escrita, o texto original ficou intacto e recebeu uma **nota de correção datada** logo abaixo —
para que a diferença entre o que se supunha e o que se mediu fique visível, em vez de ser
apagada.

---

# PARTE I — Parâmetros pré-registrados (21/07/2026)

## 1. Janela da regressão do choque limpo (em meses)

- **Valor:** 12 meses (252 dias úteis).
- **Justificativa econômica:** A regressão do choque limpo serve para isolar o que é movimento sistêmico (do mercado e do setor) do que é movimento exclusivo da empresa. Para calcular esses *betas* (a sensibilidade do ativo ao mercado) com precisão estatística, precisamos de uma amostra grande o suficiente para diluir ruídos de curto prazo, mas não tão longa a ponto de pegar uma "outra empresa" do passado. Na literatura acadêmica (ex: modelos Fama-French), 12 meses de dados diários é o padrão-ouro de equilíbrio.
- **Validação Crítica:** Uma janela de 1 a 3 meses seria ruidosa demais (a temporada de balanços distorceria o beta). Uma janela de 5 anos assumiria que a empresa não mudou seu modelo de negócios. 12 meses captura perfeitamente o risco atual do papel. É a escolha mais defensável e embasada para a banca.

## 2. Corte de winsorização (percentil dos extremos)

- **Valor:** 2% total (corte nos percentis 1% e 99%).
- **Justificativa econômica:** O mercado tem "caudas gordas" (eventos abruptos e extremos). Um vazamento de fusão pode fazer uma ação disparar 60% num dia. Modelos estatísticos lineares (como nossas regressões e z-scores) enlouquecem com isso, dando um peso absurdo a esse ruído. A winsorização impõe um limite: tudo acima do percentil 99% é achatado para o valor do percentil 99%. Isso garante que nosso lucro venha de um processo estrutural na rede da bolsa, e não de um robô enviesado por 3 ou 4 *outliers* anuais.
- **Validação Crítica:** Por que não 5%? Em um universo de apenas ~100 ações, 5% ceifaria informação preciosa de sinais fortes e válidos. Por que não 0%? Zero winsorização resulta em backtests frágeis (uma única empresa pode dominar o retorno do ano). 1% em cada cauda é exatamente o ponto onde o ruído some e a tese fica.

> **📌 Nota de correção (16/08/2026) — o valor está mantido, a justificativa estava exagerada.**
> Medido: a winsorização corta **3,8% das células** do sinal. Com a seção transversal em torno de
> 50 nomes por dia no período inicial, o percentil 1% é praticamente o mínimo — na prática ela
> achata **cerca de um nome por ponta**. É uma guarda leve contra valor absurdo, **não** a
> proteção contra caudas gordas que o texto acima descreve. O parâmetro não faz mal e fica como
> pré-registrado; o que muda é o que se pode alegar sobre ele.
>
> A proteção real contra concentração veio de outro lugar: a expansão da seção transversal. Os 5
> maiores contribuintes de P&L saíram de **79%** do total (v1) para **13,2%** (configuração
> atual).

> **📌 Nota de correção (27/08/2026) — o "3,8%" da nota acima também ficou velho.**
> A saída atual do pipeline diz **2,57% das células**
> (`fase 7 - relatorio/saida/16_tabela_parametros.md`, gerado por `r1_visuais.py`), e o §7.3 do
> `RelatórioRAW.md` já lista "corta 3,8%" como corrigido para 2,57%. O **argumento** da nota de
> 16/08 não muda — é guarda leve, não proteção contra caudas gordas —, só o dígito. Este número não foi
> re-medido aqui: o valor acima foi alinhado com o artefato gerado, que é a fonte única.

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

> **📌 Nota de correção (16/08/2026) — o valor está mantido, a alegação de executabilidade era
> forte demais.**
>
> A trava limita a **POSIÇÃO** (estoque), não a **ORDEM** (fluxo). Com giro diário, a ordem de um
> dia é uma fração pequena da posição, então esta trava **não** governa o impacto de execução —
> ela governa quanto tempo levaria para montar ou desmontar a posição. Dizer que ela "prova que
> os retornos seriam executáveis" confunde as duas coisas.
>
> Quem endereça executabilidade é o **modelo de custo em camadas** (§11, e
> `fase 3 - backtest/src/s3b_custos.py`), com impacto de mercado pela lei da raiz quadrada e
> aluguel da ponta vendida. Medido: o custo realista é **33,6 bps por unidade de giro**, contra
> os 5 bps que o backtest assumia — e o alfa por unidade de giro é 33,7 bps.
> ⚠️ **Re-medido em 27/08/2026: o alfa por unidade de giro é 68,3 bps.** Ver a nota de
> correção no §11.
>
> Dois bugs relacionados foram corrigidos em 04/08 e 16/08: a trava era violada em 59,6% dos dias
> (a suavização de pesos rodava depois dela e não a reaplicava) e o `clip` com limite NaN não
> cortava. Ambos com teste de regressão.

## 6. Volatilidade-alvo do dimensionamento de posição

- **Valor:** 12% anualizada.
- **Justificativa econômica:** O Vol-Targeting substitui as tentativas (quase sempre inúteis) de prever o cenário macro. O investidor institucional quer retorno atrelado a um risco conhecido. Com o alvo de 12%, o algoritmo se autoprotege: se o mercado entrar em histeria coletiva (volatilidade sobe), o modelo reduz automaticamente o tamanho das posições financeiras para manter a carteira travada nos 12% de oscilação. Em águas calmas, ele alavanca levemente. É o mecanismo de defesa perfeito.
- **Validação Crítica:** Fundos multimercado (*macro* e *quant*) costumam rodar com mandato de volatilidade entre 8% e 15%. Cravar o meio-termo (12%) entrega oscilação suficiente para produzir prêmios interessantes na ponta do Sharpe, sem gerar *drawdowns* (quedas) que matariam um fundo precocemente.

> **📌 Nota de correção (16/08/2026) — o valor está mantido, mas 12% é um TETO, não um alvo
> atingido.**
>
> A carteira **nunca rodou a 12%**. Realizado: 7,84% (v1) e 7,64–8,94% (configuração atual).
> Utilização do orçamento de risco: **~65%**.
>
> **Por que, com número.** A volatilidade de um book long-short obedece
> `vol ≈ peso × σ × √(apostas independentes)`. Com a breadth efetiva medida e vol individual
> mediana de 42,9% a.a., atingir 12% exigiria peso de **8,3% por nome** — acima da trava de 5%
> do §3. O teto aritmético alcançável era **7,2%**; o medido foi 7,84%. Não é erro de
> calibragem, é aritmética.
>
> A configuração atual elevou a breadth e a trava de 5% deixou de morder (**77,0% dos dias no
> teto → 3,3%**), o que levou a exposição bruta de 85% para ~119%. Ainda assim a vol fica abaixo
> de 12%.
>
> **O argumento que encerra a pergunta:** o vol-targeting é homogêneo de grau 1 — multiplicar o
> book por uma constante multiplica retorno e volatilidade pelo mesmo fator e **deixa o Sharpe
> inalterado**. Rodar a 7,6% em vez de 12% custou *retorno absoluto*, não *qualidade*. **O gap de
> volatilidade não explica o resultado da estratégia.**
>
> **A exceção que precisa ser reportada, e é a que machuca:** a vol de 63 dias atingiu **18,12%
> em 25/05/2020** — acima do teto — e ficou acima de 12% em 2,62% dos dias. Causa: a janela de
> covariância de 60 pregões com peso igual demora até um trimestre para reagir a mudança de
> regime. É um defeito do *estimador*, não do parâmetro.
>
> **Decisão: manter os 12% e reclassificar como teto de mandato**, reportando a utilização.
> Baixar a meta para 7,5% depois de medir 7,64% seria exatamente o ajuste retroativo que o
> cabeçalho deste documento proíbe.

> **📌 Nota de correção (27/08/2026) — os números de vol acima são pré-correção de calendário.**
> Depois da correção dos 36 feriados-fantasma (`1deffe1`), a vol de 63 dias tem **máximo de 13,63%
> (abr/2020)** e mediana de 7,54% — não 18,12% em 25/05/2020 (`RelatórioRAW.md` §4.5; o §7.3 lista
> "atingiu 18,12%" como corrigido). O percentual de dias acima do teto aparece como **7,0%** num
> trecho do RAW e **7,2%** em outro; nenhum dos dois foi re-medido, então o valor não é fixado aqui.
> **A decisão da nota de 16/08 não muda, e fica mais fácil de defender:** o estouro do teto era
> menor do que se pensava.

## 7. Assets Under Management (AUM)

- **Valor Padrão:** R$ 100.000.000 (100 milhões).
- **Justificativa econômica:** O tamanho do fundo (AUM) dita o quão agressivamente a trava de liquidez (10% do ADTV) irá "tesourar" as posições em empresas menores e desatendidas. Testar a estratégia com 100 milhões reflete um fundo de tamanho médio viável no Brasil.
- **Validação Crítica:** É imperativo gerar a curva de capacidade do fundo. A estratégia será testada em três cenários de AUM: R$ 20 milhões (onde a trava raramente atua, maximizando o prêmio teórico), R$ 100 milhões (cenário base) e R$ 300 milhões (onde a restrição de liquidez reduz a alocação em small caps, testando a resiliência do modelo).

> **📌 Nota (16/08/2026) — curva de capacidade executada, e um quarto ponto acrescentado.**
>
> | AUM | Sharpe líquido | líquido a.a. | custo/ano |
> |---|---|---|---|
> | R$ 20 MM | +0,008 | +0,07% | 4,42% |
> | R$ 100 MM | −0,034 | −0,27% | 3,83% |
> | R$ 300 MM | −0,049 | −0,36% | 3,12% |
> | R$ 1 bi | −0,085 | −0,40% | 1,69% |
>
> (com custo realista; com o custo flat de 5 bps os quatro pontos são positivos)
>
> A curva é rasa: reduzir o fundo 5x quase não melhora o resultado. O motivo é o §11 — no
> período recente **60%+ do custo é aluguel da ponta vendida**, que é carrego proporcional ao
> book, **não à ordem**. Diminuir o AUM reduz impacto de mercado, mas não reduz aluguel.

---

# PARTE II — Parâmetros acrescentados após o pré-registro (16/08/2026)

> Estes parâmetros **não existiam** no pré-registro de 21/07. Estão aqui separados de propósito:
> a alegação de pré-registro da Parte I permanece verificável no `git log` porque não foi
> diluída com valores decididos depois.

## 8. Horizonte do sinal — acumulação 12-1

- **Valor:** soma do choque nos 231 pregões que terminam 22 pregões antes de hoje.
- **Substitui:** a média móvel de 21 pregões sobre o choque de um dia.
- **Justificativa — e ela é medida, não escolhida.** A tese original supunha propagação em T+1.
  Medindo o IC do sinal contra o retorno futuro em vários horizontes:

  | h | T+1 | T+5 | T+21 | T+63 | T+126 |
  |---|---|---|---|---|---|
  | IC | +0,0076 | +0,0129 | +0,0225 | +0,0359 | +0,0389 |
  | **t** | **2,99** | **2,20** | 1,79 | 1,59 | 1,05 |
  | **IC/√h** | **0,0076** | **0,0058** | **0,0049** | **0,0045** | **0,0035** |

  `IC/√h` **cai 54%** de T+1 a T+126 — não é constante. Mas está muito longe dos **91%** que um
  efeito de um único dia produziria, e é isso que a tabela sustenta: **difusão lenta** — informação
  que se espalha por meses, não por um dia. **A janela não foi calibrada para maximizar nada — ela é
  consequência de um fenômeno medido.** A defasagem de 22 pregões (o "−1") é a convenção da
  literatura para evitar contaminação por reversão de curto prazo.

  Ressalva honesta: **só T+1 e T+5 têm t > 2.** Nos horizontes longos as janelas se sobrepõem e o
  n efetivo cai, então cada horizonte isolado não cruza a significância. A evidência está no
  **padrão monotônico** e no **placebo do gatilho** (§4.7 do `RelatórioRAW.md`), não no t de um
  horizonte só.

  > **Fonte única do IC por horizonte:** `fase 7 - relatorio/saida/05_ic_por_horizonte.md`, gerado
  > por `r1_visuais.py`. Não repetir os dígitos em outro lugar sem apontar para esse arquivo.
  >
  > **Correção de 27/08/2026 — transcrição, não resultado.** A tabela que estava aqui
  > (0,0073 / 0,0146 / 0,0315 / 0,0505, com `IC/√h` descrito como "praticamente constante") vinha do
  > protótipo de 16/08, **anterior** à correção dos 36 feriados-fantasma do calendário (`1deffe1`), e
  > nunca foi produzida pelo pipeline — não há código no repositório que gere aqueles valores. A
  > alegação de constância já constava como **refutada** no §7.3 do `RelatórioRAW.md`; este parágrafo
  > ainda a repetia. Nenhum código, dado ou resultado mudou nesta correção.
- **Efeito colateral:** o giro cai de 9,7% para **3,08% ao dia**, e o alfa por unidade de giro sobe
  de 19 para **68,3 bps**. No horizonte de um dia a estratégia **pagava para operar**.
  *(Giro e alfa por unidade de giro re-medidos em 27/08/2026 na janela ativa de 2.140 pregões,
  direto de `df_weights_sinapse.parquet`: **3,0791%/dia** e **68,3 bps**. Os valores anteriores —
  ~4,8% e 33,7 bps — eram pré-correção de calendário.)*

## 9. Modelo do choque — só-mercado

- **Valor:** `retorno = α + β·IBOV + ε`, rolling de 252 pregões (a janela do §1, inalterada).
- **Substitui:** `retorno = α + β₁·IBOV + β₂·SETOR + ε`.
- **Justificativa:** a tese é difusão de informação **intra-indústria**. O termo `β₂·SETOR`
  removia exatamente a informação que se quer propagar — limpava o sinal do próprio conteúdo.
  Medido (IC em T+21, rodada de 16/08): grafo manual +0,0506 → **+0,0621**; regra mecânica
  +0,0130 → **+0,0315**.
  ⚠️ Números do **protótipo**, anteriores à correção do calendário e não re-medidos: refazer o
  teste exige rodar o pipeline com o termo setorial de volta. Eles sustentam o **sinal e a ordem
  de grandeza** da diferença, não os valores absolutos. O IC em T+21 da configuração final é
  **+0,0225** (§8).
- **Reconcilia três resultados** que estavam soltos: por que `concorrente = +1` funciona, por que
  o controle por subsetor **piorou** o resultado, e por que o placebo do mecanismo falhava no
  in-sample.
- **Bônus:** o β desta regressão **é** o beta de mercado, e não um coeficiente parcial.
  **Mediana medida: 0,82** (re-medida em 27/08/2026 em `betas_sinapse.parquet`, 1.348.269
  observações: 0,8178). A versão anterior deste parágrafo dizia "~1,0" — alegação que o §7.3 do
  `RelatórioRAW.md` já listava como corrigida. Na versão bivariada era
  um coeficiente *parcial* (mediana 0,335), porque o índice setorial tem ele mesmo beta ~1 —
  e usar coeficiente parcial como razão de hedge sub-hedgeava o book.

## 10. Grafo mecânico — ensemble A3

- **Valores:** K ∈ {2, 3, 5} × peso da cabeça ∈ {igual, ADTV} = **6 variantes**; mínimo de 4
  membros por subsetor; ADTV mínimo de R$ 100 mil; dedup por raiz de ticker.
- **Substitui:** os 58 elos escritos à mão (mantidos no repositório para comparação e placebo).
- **A regra:** mensalmente, por subsetor, ordena por ADTV dos 21 pregões anteriores
  (point-in-time); os K mais líquidos formam a cabeça; cada nome da cabeça manda sinal para
  todos os membros do ramo, ex-self e ex-mesma-empresa.
- **Por que ensemble e não a melhor variante:** as 6 entram **todas**. Nenhuma é escolhida por
  desempenho — e é isso que torna a configuração defensável. Ver a Parte III para a evidência de
  que escolher, neste problema, é perigoso.
- **Validação:** a regra reproduz **38 dos 40** elos same-subsetor do grafo manual (95%), todos
  também na direção inversa. E o gatilho tem conteúdo: sortear qual nome é a cabeça, 300 vezes,
  perde para a escolha por ADTV com **p ≤ 0,010** em todas as janelas de IC.

## 11. Custo de transação — modelo em camadas

- **Substitui:** o custo único de 5 bps por unidade de giro, que **nunca foi pré-registrado**.
- **Por que:** 5 bps é um número de large cap líquida, e 73% do giro deste book está abaixo de
  R$ 150 MM de ADTV. Faltavam dois componentes inteiros: impacto de mercado e aluguel (BTC).

| camada | valor | natureza |
|---|---|---|
| emolumentos + liquidação B3 | 2,3 bps | **observável** (tabela pública) |
| corretagem institucional | 3,0–4,0 bps | **contratual** |
| meio-spread por faixa de ADTV | 2 / 5 / 11 / 24 bps | **estimado** |
| impacto de mercado | `0,4 × σ₆₀ × √(participação)` | **estimado** (η) |
| aluguel BTC por faixa | 1,0 / 2,0 / 3,5 / 6,0 % a.a. | **estimado** |

- **Nenhum destes foi calibrado para melhorar o resultado.** São números de mercado, e a tabela
  de sensibilidade em η (0,0 a 1,0) está no painel do Bloco 3 — é o que separa "modelamos custo"
  de "escolhemos um custo".
- **Resultado:** custo total 4,02% a.a. = **33,6 bps por unidade de giro**, contra **33,7 bps de
  alfa por unidade de giro**. Este par é o resultado mais defensável do projeto: mostra que a
  conclusão não depende da calibragem de custo, e sim de uma propriedade medida do sinal.

> **📌 Nota de correção (27/08/2026) — este par de números é pré-correção de calendário.**
> Re-medido hoje direto de `df_weights_sinapse.parquet`, na janela ativa de 2.140 pregões: o giro
> é **3,0791%/dia** (era ~4,8%) e o alfa por unidade de giro é **68,3 bps**, não 33,7 bps. O custo
> total anual oficial é **2,84% a.a.** (`RelatórioRAW.md`), não 4,02%, e o custo por unidade de
> giro no material de entrega é **36,6 bps**, não 33,6 — **esses dois não foram re-medidos**, porque
> exigem rodar `s3b_custos.py`.
> **O argumento fica mais forte, não mais fraco:** a folga entre alfa e custo por unidade de giro
> passa de ~1,0× (33,7 contra 33,6) para **1,87×** (68,3 contra 36,6). A frase "a conclusão não
> depende da calibragem de custo" continua verdadeira — e agora com margem.
- **Achado:** no período pós-2019, **60%+ do custo é aluguel da ponta vendida** — carrego
  proporcional ao short, **imune a qualquer redução de giro**.

## 12. Suavização dos pesos finais

- **Valor:** 63 pregões (era 10).
- **Justificativa:** a janela de suavização dos pesos deve ser da ordem do horizonte do sinal.
  Com o §8, a carteira-alvo é intrinsecamente lenta e não faz sentido negociá-la com uma janela
  de duas semanas. **É uma consequência estrutural do §8, não uma calibragem.**
- **Nota histórica, e ela importa:** o valor antigo (10) foi escolhido por **maximizar o Sharpe**
  numa varredura — era a única linha do repositório que documentava escolha de parâmetro por
  resultado. Está corrigido, e a menção fica aqui para que a mudança seja rastreável.

---

# PARTE III — Testado e não adotado

Registro para não retestar, e para que a banca veja o que foi considerado.

| # | ideia | veredito | número |
|---|---|---|---|
| D1 | teto de satélites por subsetor {3,5,8,12} | **não adotado** | vence no IS (SR +0,263 com teto 3, monotônico) e **inverte no OOS** (−0,150 contra −0,051 sem teto) |
| D2 | neutralizar o sinal contra beta | **não adotado** | vence pelo critério declarado (IC IS +0,0464 vs +0,0428) e **piora o OOS** |
| — | controle por subsetor no choque | **rejeitado** | o baseline vence os 7 limiares no in-sample (`s13`) |
| — | empilhar momentum de preço | **rejeitado por princípio** | melhoraria o número, mas é fator alheio validado há 30 anos; entra só como controle de atribuição |
| — | propagação de 2 saltos | **não adotado** | ganho de breadth = zero nomes/dia; o coeficiente colapsa (t −0,10) ao controlar pelo 1º salto |
| — | força do elo pelo gap de liquidez | **não adotado** | IC OOS 0,0041 / 0,0022 / 0,0029 nas três funções — ruído |
| — | elos cross-setor (MIP do IBGE, CVM) | **não perseguido** | cross-setor é **imaterial** no horizonte 12-1 (+0,0373 contra +0,0595 dos internos) |

> **A razão de fundo para D1 e D2 não terem sido adotados, e ela vale mais que os dois:**
> a grade OOS completa (5 tetos × 3 neutralizações) **não tem nenhuma célula com Sharpe líquido
> positivo — exceto exatamente a que os dois critérios in-sample rejeitaram por larga margem**
> (SR IS −0,87 → SR OOS +0,48).
>
> Terceira vez que o in-sample deste projeto escolhe errado. **A leitura não é "o teto de 3 é
> ruim" — é que o in-sample deste problema não tem poder de seleção.** E se o critério não
> seleciona, adicionar parâmetros escolhidos por ele destrói a propriedade mais valiosa da
> configuração: ter zero parâmetros escolhidos por desempenho.
