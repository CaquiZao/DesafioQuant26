# O que mudou na estratégia e no código — da versão original até hoje

> Documento de atualização para quem esteve fora do loop.
> Cobre as sessões de 03/08, 04/08, 11/08 e 16/08.
> **Leia a §1 e a §7 se tiver pouco tempo.**

---

# 1. Resumo em uma página

A estratégia original (chamada aqui de **"vanilla"**) rendia **−63,0%** em 10 anos quando medida
pela primeira vez com dados reais. Hoje rende **+2,83%/ano** sobre o CDI na premissa de custo
original — mas descobrimos que essa premissa de custo é irrealista, e com custo realista o número
volta a ser negativo.

O que aconteceu no meio: **6 bugs silenciosos encontrados, 2 vieses corrigidos e medidos, 4
hipóteses testadas e rejeitadas.**

| momento | retorno no período | o que mudou |
|---|---|---|
| baseline (mocks + bug do setor) | **−63,0%** | ponto de partida real |
| + grafo corrigido + vol-targeting | −1,3% | direção dos elos, estimativa de vol |
| + suavização dos pesos | +19,9% | controle de giro |
| **+ sem viés de sobrevivência** | **+8,7%** | **o número PIOROU e foi adotado** |
| + Sharpe corrigido + trava de liquidez | +8,5% | dupla contagem do CDI, posições ilegais |
| + grafo point-in-time | +11,6% | empresas mortas no grafo |
| **+ mapa setorial corrigido** | **+27,9%** | 201 de 253 tickers estavam sem setor |

**A mensagem principal para quem está chegando:** quase todo o trabalho foi encontrar erros e
medir vieses, não otimizar retorno. Duas vezes o número **piorou** por uma correção e foi adotado
assim mesmo.

---

# 2. Como era a estratégia vanilla

## 2.1 A tese original

> Existe um grafo de ligações econômicas entre empresas (cliente, fornecedor, concorrente,
> holding). Quando uma empresa **gatilho** tem um choque idiossincrático, esse choque se **propaga**
> para a empresa **satélite** ligada a ela, com atraso de um dia.
>
> Direção do elo: `+1` se o choque se propaga no mesmo sentido; `−1` se em sentido oposto.
> **Concorrente foi definido como `−1`** — "a desgraça de um é a sorte do outro".

## 2.2 O pipeline vanilla

```
Bloco 1  preços ajustados (yfinance)
Bloco 2  universo líquido (COTAHIST)
Bloco 4  choque limpo → propaga pelo grafo → z-score
Bloco 5  z-score vira peso → vol-target 12% → travas → hedge de beta → lag T+1
Bloco 3  P&L = pesos × retornos − custo
```

## 2.3 O que estava errado nele (descoberto depois)

| problema | consequência |
|---|---|
| `mapeamento_setores.csv` nunca era encontrado (caminho errado) | a regressão do choque limpo devolvia **o retorno bruto disfarçado**. O sinal nunca fez o que dizia fazer |
| beta fixo em 1,0 para todas as ações | o hedge de mercado era fictício |
| trava de liquidez desligada | posições impossíveis de executar |
| custo de transação zerado | resultado sem desconto de corretagem |
| `concorrente = −1` | **metade do grafo apostava ao contrário** |
| preços só do yfinance | **viés de sobrevivência**: só empresas que existem hoje |

---

# 3. Bugs corrigidos

Todos foram encontrados por medição, não por leitura de código. Todos têm teste de regressão que
**falha no código antigo e passa no novo**.

## 3.1 Mapa de setores nunca carregado · 03/08

**O que era:** o caminho do arquivo subia uma pasta a mais. O script seguia em frente como se
nenhuma ação tivesse setor.

**Por que foi grave:** criava uma regressão matematicamente degenerada (duas colunas idênticas e
constantes). A biblioteca, em vez de dar erro, devolvia **silenciosamente** um resultado sem
sentido — que acabava virando o retorno bruto da ação, sem nenhum ajuste.

> **O sinal da Sinapse, desde sempre, nunca tinha isolado choque nenhum.**

## 3.2 Dupla contagem do CDI no Sharpe · 04/08

**O que era:** o Sharpe subtraía o CDI do P&L. Mas a carteira é long-short autofinanciada — as
vendidas financiam as compradas, e o AUM fica em caixa rendendo CDI. **O P&L já é excesso sobre a
taxa livre.**

**Como se manifestava:** Sharpe negativo com retorno positivo — matematicamente incoerente.

| | antes | depois |
|---|---|---|
| Sharpe | −1,40 | **+0,18** |

**Safeguard:** o Ibovespa **continua** medido como excesso sobre o CDI, que é o correto para ele.
O comentário no código explica a assimetria para ninguém "uniformizar" no futuro.

## 3.3 Trava de liquidez violada · 04/08

**O que era:** os pesos eram suavizados **depois** das travas e as travas não eram reaplicadas. A
justificativa era um argumento de convexidade — correto para limites **constantes**, mas a trava
de liquidez **varia no tempo** (`limite[t] = ADTV[t] × 10% / AUM`).

| medida | antes | depois |
|---|---|---|
| dias com ao menos uma violação | **59,6%** | **0,0%** |
| pior dia | 74% do book ilegal | — |

**Por que importava:** backtest com posições **não executáveis na vida real**.

## 3.4 Posição fantasma em ação delistada · 04/08

Ação que para de negociar continuava com peso: consumia limite de risco e de setor, e rendia
zero. Zerar o sinal na entrada não bastava — a suavização de 10 dias **ressuscitava** o peso.

| | antes | depois |
|---|---|---|
| fantasma por construção | 2,07% do book | **0,00%** |

## 3.5 Mapa setorial 79% vazio · 04/08

**201 de 253 tickers** estavam com o setor literal `"A DEFINIR"` — incluindo **43 das 74 empresas
do grafo**. É a mesma falha do 3.1 com outra roupa: o arquivo era lido, mas quase vazio, e
`"A DEFINIR"` é uma string válida que **agrupa em vez de dar erro**.

| | antes | depois |
|---|---|---|
| tickers sem setor | 201 de 253 | **1 de 255** |
| alfa acumulado | +11,6% | **+27,9%** |

## 3.6 Bugs identificados e **ainda não corrigidos** · 16/08

Estes são os que faltam. Estão listados aqui porque mudam números oficiais.

| # | bug | onde | impacto |
|---|---|---|---|
| a | Resíduo vira **retorno bruto** enquanto não há 252 observações | `s4:233` | **13,4% das células**, 100% de 2016. Faz o `t = 2,14` in-sample virar **1,39** |
| b | Beta do hedge é **parcial**, não de mercado | `s4:226-236` | mediana 0,28, **24% negativos**. Hedge com ~1/3 do beta correto |
| c | Beta NaN vira zero no hedge | `s5:209` | **12,8% das posições** sem hedge |
| d | `clip` com limite NaN não corta | `s5:176-178` | 353 posições escapam da trava |
| e | `s11` duplica os 28 elos históricos | `s11:189-192` | os "86 elos" são 58 com 28 dobrados |

> **O (a) é o mais grave conceitualmente:** o `t = 2,14` que sustenta o protocolo de validação
> das direções é artefato de bug. Corrigido, o in-sample não é significante.

---

# 4. Vieses corrigidos

## 4.1 Viés de sobrevivência nos preços · 03/08

**O problema:** das 253 ações do universo, só 166 tinham preço — o yfinance não serve ticker
deslistado. Das 87 ausentes, **65 já tinham saído do mercado**: Kroton, Cielo, B2W, Hering,
Linx, NotreDame, Gol, Estácio, Americanas...

Testar só com quem sobreviveu é trapaça involuntária: em 2016 ninguém sabia quem ia quebrar.

**A solução:** o COTAHIST da B3 tem o preço de **todas** as empresas. O Bloco 2 passou a extrair
preço além de volume, e um script novo (`s1c`) limpa e une as duas fontes.

O preço bruto da B3 não é ajustado por proventos nem desdobramentos — a PDGR3 fez grupamento
1:50, que no preço cru vira "+4.900% num dia". Três limpezas:

| | preço bruto | depois da limpeza |
|---|---|---|
| correlação média com yfinance | 0,840 | **0,972** |
| erro (desvio da diferença) | 0,4486 | **0,0096** |

Erro reduzido **46x**. Cobertura do universo: **66% → 98%**.

| | resultado |
|---|---|
| Fase 1 (só sobreviventes) | +19,9% |
| **Fase 2 (universo real)** | **+8,7%** |

> **O viés estava inflando o resultado em mais da metade.** O +8,7% é o número honesto.

## 4.2 Viés de seleção do grafo · 04/08

Corrigir o preço não bastava: **as 44 empresas do grafo foram escolhidas em 2025 por alguém que
já sabia quem sobreviveu.** O viés estava na escolha das *relações*.

| medida | valor |
|---|---|
| empresas do grafo que não eram líquidas em 2016 | **20 de 44 (45%)** |
| cobertura do universo 2016–2018 | 21,9% |
| cobertura 2023–2025 | 29,7% (**1,4× maior**) |

**A correção:** `grafo_historico.csv` — 28 elos novos com 30 empresas que morreram (Kroton/Estácio,
B2W/Magazine Luiza, Cielo/Bradesco, Gol/Azul, Linx/Totvs...).

**Regra imposta na escrita:** só relações **estruturais verificáveis na época**. Nenhum elo foi
escrito a partir de desfecho conhecido. Exemplo do que isso *excluiu*: não foi criado
`GNDI3 → RDOR3` (aquisição posterior) nem `LINX3 → STNE`.

| | antes | depois |
|---|---|---|
| empresas no grafo | 44 | **74** |
| cobertura 2016–2018 | 21,9% | **43,8%** |
| custo honesto no OOS | — | **−0,58 p.p./ano de alfa** |

> ⚠️ **Ressalva descoberta depois:** as 10 empresas mortas escolhidas são exatamente as quebras
> famosas do período. Um analista em 2016 teria escrito elos para essas **e para cem outras que
> não quebraram**. A correção pode ter introduzido viés de retrovisão na *seleção*, mesmo com
> cada elo sendo honesto. Evidência: AZUL4 sozinha responde por **19% do P&L bruto**, e entra no
> universo só por esse arquivo.

---

# 5. Validações e testes — o que foi rejeitado

Registro para não retestar. Cada um tem script no repositório.

| hipótese | veredito | como foi testado |
|---|---|---|
| Inversão de `concorrente` foi data snooping? | **não** — um analista em 2020, sem ver 2021+, escolheria `+1` do mesmo jeito | protocolo IS/OOS (`s6`) |
| Negociar também as empresas gatilho (bidirecional) | **rejeitado** — ganho de Sharpe dentro do ruído | `s7`, mesmo protocolo |
| A vol baixa é erro de código? | **não** — as 3 correções testadas pioraram | `s8`, `s9` |
| Retry no Yahoo resolveria os 5 tickers sem preço? | **não** — é 404 permanente, não rate-limiting | investigação isolada |
| Controle setorial mais fino (subsetor) | **rejeitado** — baseline vence os 7 limiares no IS | `s4c`, `s13` |
| Grafo mecânico substituindo o manual (1 dia) | melhor em todos os eixos, mas ainda sem edge | protótipo |
| Suavização maior / banda de não-negociação | breakeven não se move | varredura completa |

> **Todos os resultados negativos foram mantidos no repositório**, com os números medidos nos
> comentários. Sem isso, a próxima pessoa tenta as mesmas coisas.

---

# 6. Descobertas metodológicas

## 6.1 Breadth efetiva — 58 elos entregam 11,3 apostas

O número de apostas **independentes** não é o número de elos. Medido pela razão de participação
dos autovalores da matriz de correlação dos sinais:

| | |
|---|---|
| elos | 58 |
| gatilhos distintos | 28 |
| **apostas independentes** | **11,3** |

Sete elos pendurados na LREN3 são **uma** aposta replicada sete vezes.

**O teste que valida:** a Lei Fundamental (IR ≈ IC × √breadth) prevê IR = **0,49** com a breadth
efetiva. O Sharpe realizado OOS foi **0,50**. Sem nenhum fator livre — o relatório anterior
fechava a mesma lacuna com um fator de 50% ad hoc.

## 6.2 O gap de volatilidade é aritmética, não bug

A carteira roda a 7,84% contra meta de 12%. Isso foi diagnosticado como "estrutural" sem se saber
qual era a estrutura. Agora se sabe:

```
vol ≈ peso × σ × √(apostas independentes)

com 11,3 apostas e σ = 42,9%:
   peso necessário para 12% de vol = 8,3%
   teto por nome                   = 5,0%   ← bloqueia
   vol máxima alcançável           = 7,2%   (medido: 7,84%)
```

A trava de 5% está encostada em **84% dos dias**. **Com ~31 apostas independentes, a vol atinge
os 12% sozinha**, sem tocar em parâmetro de risco.

> **P4 não é um problema separado de P3 — P4 é P3.**

## 6.3 Os t-stats estavam inflados

O erro-padrão tratava observações empilhadas como independentes, mas o mesmo pregão aparece uma
vez por elo. Com erro-padrão **clusterizado por data**:

| categoria | t ingênuo | t clusterizado | inflação |
|---|---|---|---|
| concorrente | 4,91 | **3,13** | 1,57x |
| cliente | 3,61 | **2,20** | 1,64x |
| holding_subsidiaria | 2,96 | **1,79** | **perde o limiar** |

`concorrente` sobrevive — a conclusão central se mantém. Mas `holding_subsidiaria` passava o
limiar |t| ≥ 2 com o erro-padrão errado.

**Uma hipótese foi refutada:** suspeitávamos que a média móvel de 21 dias inflasse o t do IC por
autocorrelação. Medido com Newey-West: ρ(1) ≈ 0,00. **Os t do IC estavam corretos.** O teste
ficou no repositório como verificação.

## 6.4 O custo está 4x otimista

O modelo usa 5 bps flat. Medido para este book: **20,3 bps**, porque **73% do giro está abaixo de
R$150MM de ADTV** — 5 bps é número de large cap.

| cenário | alfa/ano | Sharpe |
|---|---|---|
| 5 bps (premissa atual) | +2,83% | 0,36 |
| custo realista + aluguel | **−2,28%** | **−0,29** |

**E o fato estrutural:** o alfa por unidade de giro é **~15 bps e constante** — testado em
suavização de 1 a 34 dias e banda de 0,25% a 2,0%. **Não existe ponto de operação em que a
estratégia sobreviva a 20 bps.**

## 6.5 O Sharpe não é estatisticamente significante

```
Sharpe 0,361 × √9,8 anos  =  t = 1,13        (precisa de > 2)
IC 95%: [−0,27 ; +0,99]                       (inclui zero)
Deflated Sharpe (N=50 configurações): 0,05
```

E **100% do P&L está em 3 anos**: 2016–2022 acumula −4,23%; 2023–2025, +33,84%.

---

# 7. Onde estamos e para onde vamos

## 7.1 Estado atual

| | 10 anos | OOS 21–25 |
|---|---|---|
| Alfa (a 5 bps) | +2,83%/ano | +3,91%/ano |
| Alfa (custo realista) | **−2,28%/ano** | — |
| Sharpe | 0,36 (**t = 1,13**) | 0,50 |
| Volatilidade | 7,84% (meta 12%) | 7,86% |
| Drawdown máximo | −19,6% | |
| Breadth efetiva | 11,3 apostas | |

**O que é sólido:** o pipeline é honesto, os vieses foram medidos e corrigidos, o protocolo de
validação é rigoroso, e o grafo **bate placebo** de reembaralhamento (p ≤ 0,015).

**O que não é:** não há edge estatisticamente demonstrável na configuração atual.

## 7.2 A DESCOBERTA DE 16/08 — o horizonte estava errado

Esta é a mudança mais importante do projeto inteiro, e ela reabre a estratégia.

**O que era:** o sinal é o choque de **um dia**, suavizado por média móvel de 21 pregões. A tese
dizia que a propagação acontece em T+1.

**O que se descobriu:** a difusão é **lenta — meses, não um dia.** Acumulando o choque em 12
meses (janela 12-1, padrão da literatura) em vez de usar o choque diário:

| sinal | IC(T+21) | t |
|---|---|---|
| produção (choque 1d, suavizado 21d) | +0,0255 | 1,32 |
| **choque acumulado 12-1** | **+0,0547** | **2,42** |

*(t ajustado para observações sobrepostas — n dividido pelo horizonte. Sem esse ajuste os t saem
inflados.)*

**Verificado de forma independente**, fora do prototipador. Mais que dobra o IC e cruza a
significância.

### O IC cresce com a raiz do horizonte — assinatura de difusão real

| horizonte | IC | IC/√h |
|---|---|---|
| T+1 | +0,0073 | 0,0073 |
| T+5 | +0,0146 | 0,0065 |
| T+21 | +0,0315 | 0,0069 |
| T+63 | +0,0505 | 0,0064 |

`IC/√h` praticamente constante é exatamente o que um processo de difusão prevê. **Isso não é um
parâmetro ajustado — é um fenômeno medido**, e é o argumento mais forte da tese.

### O problema de custo evaporou junto

O horizonte longo derruba o giro, e o custo era o que matava a estratégia:

| | antes (1 dia) | depois (12-1) |
|---|---|---|
| giro | 9,7%/dia | **1,3%/dia** |
| **alfa por unidade de giro** | 19 bps | **235 bps** |
| custo | ~20 bps (breakeven era 15) | ~73 bps/ano contra 235 de alfa |
| concentração (top 5 nomes) | 79% do P&L | **34%** |
| drawdown máximo | −50% | **−26%** |

> Toda a análise anterior que concluía "não há edge" foi feita no horizonte de 1 dia. **A
> conclusão mudou porque o horizonte mudou** — não porque calibramos alguma coisa.

### O placebo decisivo: não é momentum de indústria

A crítica óbvia seria *"vocês só descobriram momentum de indústria"*. Testado — o movimento do
**líder específico** contra a **média do setor inteiro**:

| horizonte | líder sozinho | média do setor | juntos: líder | juntos: setor |
|---|---|---|---|---|
| T+21 | **+29,0 bp (t 2,15)** | +14,9 bp (t 0,89) | **+50,1 bp (t 2,69)** | −25,2 bp (t −1,06) |
| T+63 | **+103,5 bp (t 2,66)** | +51,5 bp (t 1,00) | **+156,4 bp (t 2,59)** | −65,7 bp (t −0,84) |

O líder ganha sozinho e sobrevive ao controle; a média do setor não sobrevive e vira negativa.
Momentum de indústria puro entrega Sharpe **−0,06**.

**É a informação do nome líder específico, não do setor.**

### E o grafo manual passa o placebo de reembaralhamento

Sorteando quem é gatilho, 300 vezes, dentro do mesmo setor:

```
IC real     +0,0621   vs média dos sorteios +0,0145   →  p = 0,013
Sharpe real +0,648    vs máximo de 100 sorteios 0,583 →  p = 0,000
```

## 7.3 O que vai ser feito — vereditos medidos

| # | mudança | veredito | número que sustenta |
|---|---|---|---|
| **M6/M7** | **horizonte 12-1** | ✅ **implementar — é a mudança principal** | IC(T+21) +0,0255 → +0,0547; giro 9,7% → 1,3%/dia |
| M1 | corrigir os 5 bugs da §3.6 | ✅ obrigatório | `s4:233` derruba o t do IS de 2,14 para 1,39 — o t que sustentava P1 era artefato |
| M9 | **`forca = 1,0`** | ✅ implementar | Sharpe 0,521 → **0,648**; deleta 116 parâmetros subjetivos |
| M10 | **walk-forward** | ✅ implementar como protocolo | Sharpe 0,603 (t 1,59), 1.743 pregões 100% OOS, 5/7 anos positivos |
| M2+M3 | universo 249 + regra mecânica | ✅ como **camada base**, em análise | breadth 9,9 → 29,0; DD −26% → −14% |
| M0 | choque sem limpeza setorial | ⚠️ **em aberto** — duas medições em sentidos opostos | ver §7.4 |
| M4 | neutralizar beta | ⚠️ inconclusivo | o sinal do efeito **inverte** com a suavização |
| M5 | long-short casado por setor | ❌ não implementar | Sharpe 0,167 contra 0,363 do M4-setor |
| M8 | força pelo gap de liquidez | ❌ não implementar | IC OOS 0,0041 / 0,0022 / 0,0029 — ruído nas três funções |
| M11 | propagação de 2 saltos | ❌ não implementar | **ganho de breadth = zero nomes/dia**; coeficiente colapsa para t −0,10 ao controlar pelo 1º salto |

**Rejeitado por princípio:** empilhar momentum de preço (`mom252`). Melhoraria o número, mas
seria adicionar um fator validado há 30 anos a uma estratégia própria só para inflar o
resultado — desincentivado pelas diretrizes, e a banca leria como "vocês construíram um fundo de
momentum". **Momentum só aparece como controle em regressão de atribuição, nunca como
componente.**

## 7.4 Duas questões em aberto

### (a) M0 — o choque deveria ser limpo de setor?

A hipótese do time: a tese de lead-lag intra-indústria diz que o que se propaga **é** a
informação de setor; o choque limpo (`retorno − β₁·IBOV − β₂·SETOR`) removeria exatamente o
sinal.

Isso reconciliaria três resultados soltos: por que `concorrente = +1` funciona, por que o
controle por subsetor piorou, e por que o placebo do mecanismo falhou no in-sample.

**Mas as medições divergem:**

| medição | resultado |
|---|---|
| prototipador (regra mecânica, universo expandido) | choque só-mercado **melhor**: IC(T+21) +0,0130 → +0,0315 |
| verificação independente (grafo manual de produção) | choque só-mercado **pior**: IC(T+21) +0,0547 → +0,0297 |

Hipótese mais provável: **M0 ajuda a regra mecânica e atrapalha o grafo manual.** Em apuração.

> Nota: não há conflito entre M0 e neutralizar a carteira contra setor. São estágios diferentes —
> **manter** setor no choque que entra (é a informação que difunde), **neutralizar** setor na
> carteira que sai (não queremos apostar no ramo).

### (b) A regra mecânica pode alcançar o grafo manual?

No horizonte 12-1, o grafo manual **bate** a regra mecânica no mesmo universo:

| | IC(T+21) | t | Sharpe | alfa líq/ano |
|---|---|---|---|---|
| grafo manual | +0,0621 | 2,86 | **+0,648** | +6,01% |
| regra mecânica K=1 | +0,0242 | 0,78 | +0,050 | +0,62% |

**Hipótese principal em teste:** a regra só gera elos **dentro** do mesmo subsetor, e os elos do
grafo manual que cruzam subsetor carregam **2,2x mais sinal** (+0,0279 contra +0,0126). Os elos
manuais mais fortes são todos cross-setor — `VALE3→USIM5` (mineração→siderurgia),
`PETR4→VBBR3` (E&P→distribuição), `ITUB4→ITSA4` (banco→holding).

Se isso se confirmar, a regra não está com bug: está **estruturalmente cega** para a metade forte
do espaço de relações. A saída seria uma fonte mecânica e externa de elos cross-setor —
candidatas: **Matriz de Insumo-Produto do IBGE** (oficial, por ano, mapeia quem compra de quem) e
**composição acionária da CVM**.

## 7.5 O que continua frágil

1. **O Deflated Sharpe não passa.** N acumulado declarado = **156** configurações testadas ao
   longo do projeto; DSR ≈ 0,07 contra o 0,95 necessário. **O que sustenta o resultado é o
   placebo do grafo (p = 0,013 / p = 0,000), não o Sharpe.** Isso precisa estar no deck sem
   maquiagem.
2. **O ano a ano é violento:** +19%, +17%, +23%, −6%, +35%, **−25% em 2025**. Não é perfil de
   fundo neutro.
3. **O alfa está nos satélites LÍQUIDOS, não nos ilíquidos.** IC(T+21) por faixa de ADTV do
   satélite: <R$20MM +0,0320 (t 0,62); ≥R$100MM **+0,1405 (t 4,58)**. Isso **contradiz a tese de
   lead-lag**, que prevê difusão para os ilíquidos. Ou a explicação econômica está incompleta, ou
   é ruído de subamostra. Não foi adotado como corte (seria data snooping) — é a primeira coisa a
   investigar com protocolo pré-declarado.
4. **O grafo manual não é point-in-time.** O `grafo_historico.csv` cobre os nomes mortos, mas a
   *escolha* dos elos carrega retrovisão potencial. O placebo é a defesa, e é boa — mas não é a
   mesma coisa que uma regra mecânica.

---

# 7.6 IMPLEMENTADO em 16/08 — a configuração A3 em produção

Tag do estado anterior: **`v1-pre-A3`** (commit `9efbb7b`). Backup em `data_v1_backup/`.

## O que foi implementado

| # | mudança | arquivo |
|---|---|---|
| M0 | **choque só-mercado** (`ret = α + β·IBOV + ε`) — sai o regressor SETOR | `s4:calcular_choque_mercado` (novo) |
| M2 | **universo 73 → 543 tickers** regredidos (297/dia de cobertura) | idem, regressão vetorizada |
| M6/M7 | **horizonte 12-1** (231 pregões, defasados 22) no lugar da média móvel de 21d | `s4:acumular_choque` (novo) |
| M3→A3 | **grafo mecânico**, reconstruído mensalmente, ensemble de 6 variantes | `s4d_grafo_regra.py` (novo) |
| M9 | **força = 1, direção = +1** — implícito na regra | idem |
| M1.1 | resíduo NaN em vez de retorno bruto (`min_count=1`) | `s4:233` |
| M1.2 | posição sem beta válido é **zerada**, não hedgeada com beta 0 | `s5:_apply_beta_hedge` |
| M1.3 | `clip` com limite NaN passa a cortar (`limit_w.fillna(0)`) | `s5:_apply_institutional_locks` |
| M1.4 | `s11` não duplica mais os 28 elos históricos (+ assert) | `s11:189` |
| M1.5 | winsorização vetorizada — idêntica, 14x mais rápida | `s4:limpar_e_winsorizar_sinal` |
| — | suavização de pesos **10 → 63 pregões** | `s5:__init__` |

## Verificação do critério de aceite

```
elos same-subsetor no grafo manual : 40
reproduzidos pela regra mecânica   : 38/40  (95%)
também na direção inversa (mútuos) : 38/40  (95%)
```

Os dois não reproduzidos (`GOLL4→AZUL4`, `RADL3→PGMN3`) caem no filtro de subsetor com
menos de 4 membros — restrição a priori, não ajuste.

> **O grafo escrito à mão está 95% contido no que uma regra mecânica gera.** O time não
> descobriu pares; descobriu uma topologia.

## Resultado medido — antes vs depois

| | v1 (baseline) | **v2 (A3)** |
|---|---|---|
| Retorno bruto | +4,19%/ano | +4,04%/ano |
| Custo (a 5 bps) | −1,36%/ano | **−0,60%/ano** |
| **Alfa líquido** | +2,83%/ano | **+3,44%/ano** |
| **Sharpe** | 0,36 | **0,45** |
| Volatilidade | 7,84% | 7,64% |
| **Drawdown máximo** | −19,6% | **−15,8%** |
| **Giro diário** | 10,8% | **4,8%** |
| Correlação com Ibovespa | −0,01 | **−0,01** |
| nomes/dia | 35 | **141** |
| breadth efetiva | 11,3 | **14,2** |
| **dias com posição no teto de 5%** | **77,0%** | **3,3%** |
| Retorno do fundo (CDI + alfa) | +210,1% | **+229,9%** |
| **Excesso sobre o CDI** | +68,1% | **+88,0%** |

**A trava de 5% deixou de morder** (77,0% → 3,3% dos dias). Era o gargalo aritmético
identificado em P4: com 11,3 apostas e teto de 5%, a vol máxima era 7,2%. Com breadth maior
o teto some — e a exposição bruta pôde subir de 85% para 149% sem violar nada.

**A neutralidade de mercado se mantém** (correlação −0,01 com o Ibovespa), que é requisito
da tese: o benchmark é o CDI, não o Ibovespa.

## Ressalvas honestas sobre esta implementação

1. **Os números ficaram abaixo do protótipo** (Sharpe 0,45 contra 0,496 previsto). A causa
   provável é a construção de carteira: o protótipo usava peso ∝ z com neutralização, e a
   produção mantém o laço vol-targeting ↔ travas. Ver o item em aberto abaixo.
2. **A breadth subiu menos que o previsto** (14,2 contra 24,9). Com 217 satélites possíveis e
   K até 5, muitos nomes do mesmo ramo recebem sinal quase idêntico — a razão
   efetiva/nominal caiu de 23% para 7,4%. Mais posições não é mais breadth.
3. **O giro ficou em 4,8%/dia**, não nos 1,3% do protótipo, porque o grafo mensal introduz
   rotação própria a cada reconstrução.

## O que falta

| fase | o quê |
|---|---|
| §7.1 | decidir neutralização do sinal contra beta — **só no IS**, congelado |
| 4 | modelo de custo realista (tiered + impacto + aluguel BTC) |
| 5 | evidência: placebo do gatilho, controle de persistência, atribuição de fator, Deflated Sharpe, stress, painel de risco |
| 6 | `CRITERIOS_GRAFO_MANUAL.md` (direção documentada ≠ CSV), `PARAMETROS.md` §6, deck |

O número oficial ainda deve sair do **walk-forward**, não desta rodada.

---

# 8. Para quem for revisar o código

**Arquivos que mudaram desde a versão original:**

| arquivo | mudança principal |
|---|---|
| `fase 1/src/s1c_retornos_completo.py` | **novo** — limpeza de splits e união híbrida yfinance + COTAHIST |
| `fase 2/s2_universo.py` | extração de preço além de volume; ADTV diário |
| `fase 4/src/s4_sinapse_sinal.py` | caminho do mapa de setores; suavização de 21d; `tickers_alvo` |
| `fase 4/grafo_manual_base.csv` | 16 elos `concorrente` invertidos de −1 para +1 |
| `fase 4/grafo_historico.csv` | **novo** — 28 elos com empresas mortas |
| `fase 4/src/s4b_atualiza_setores.py` | **novo** — preenche 200 tickers em "A DEFINIR" |
| `fase 5/src/s5_portfolio_builder.py` | covariância cheia; iteração vol↔travas; suavização de pesos; reaplicar travas; máscara de negociabilidade |
| `fase 3/src/s3_backtest.py` | CDI real (API do BCB); Sharpe corrigido; painel de diagnóstico |
| `fase 6/src/s6` a `s13` | **novos** — validação OOS, bidirecional, diagnóstico de vol, viés de seleção, inferência e breadth, protocolo de subsetor |

**Onde estão os registros detalhados:**

- `acomp_03_08.md` — bugs de dados, viés de sobrevivência
- `acomp_04_08_sessao2.md` — P1, P2, P5, P7; bugs de carteira
- `acomp_11_08.md` — inferência, breadth, o caminho do subsetor rejeitado
- `SITUACAO_E_OPCOES.md` — o consolidado da situação e das opções
- `PLANO_IMPLEMENTACAO.md` — o plano (a ser revisado com as decisões de 16/08)
