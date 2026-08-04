# Sessão 03–04/08 — Documentação completa

> Objetivo desta sessão: sair de um backtest com **−63%** e descobrir se a
> Sinapse é viável. Resultado final: **+8,7%**, mas ainda abaixo do CDI.
> Este documento existe para que o funcionamento da estratégia continue
> claro depois de tantas iterações.

---

# PARTE 1 — Visão geral

## 1. O que foi feito

A sessão fez **três coisas distintas**, nesta ordem:

**(a) Trocou dados falsos por dados reais.** O pipeline rodava com beta
inventado (1,0 para todas as ações), sem trava de liquidez e sem custo de
transação. Agora usa beta calculado, volume real da B3 e custo de 0,05% por
giro.

**(b) Consertou a estratégia.** Três problemas: metade do grafo apostava na
direção errada, a carteira girava 20x mais do que o lucro suportava, e o
controle de risco não funcionava.

**(c) Eliminou o viés de sobrevivência dos preços.** 34% das empresas do
universo real não existiam no backtest — justamente as que quebraram.

**Evolução do resultado:**

| # | O que mudou | Retorno total | Líquido/ano | Giro/dia | Vol | Corr IBOV |
|---|---|---|---|---|---|---|
| 1 | ponto de partida (dados falsos + bug) | −20,7% | — | — | — | 0,02 |
| 2 | beta real + ADTV real + custo + bug corrigido | **−63,0%** | −9,97% | 69% | — | 0,00 |
| 3 | grafo corrigido + vol-targeting | −1,3% | +0,09% | 18,0% | 6,59% | −0,04 |
| 4 | + suavização dos pesos | **+19,9%** | +2,00% | 5,3% | 5,67% | 0,01 |
| 5 | + sem viés de sobrevivência | **+8,7%** | +1,01% | 5,8% | 5,70% | −0,01 |

*Referências no período: CDI +141,9% · Ibovespa +279,8%.*

> ⚠️ A piora de 1→2 e de 4→5 é **boa**: significa que removemos vantagens
> que não existiriam na vida real. Um número que piora quando você tira uma
> trapaça é sinal de honestidade, não de fracasso.

## 2. Decisão técnica central — e as alternativas descartadas

**A decisão central foi: onde suavizar a carteira para controlar o giro.**

O sinal da Sinapse é um choque de **um dia** e não tem memória
(autocorrelação ≈ 0). Seguir ele literalmente refazia a carteira inteira todo
pregão: ganhava 6,1 centavos/dia e gastava 6,9 em corretagem.

| Alternativa | Resultado | Decisão |
|---|---|---|
| Suavizar o **sinal** (Bloco 4) | giro caiu só para 13,4%/dia | ❌ insuficiente |
| Suavizar o **escalar de risco** | giro 13,3%/dia | ❌ quase nulo |
| **Suavizar os pesos finais** (Bloco 5) | giro **3,9%/dia**, Sharpe 0,22→0,51 | ✅ **escolhida** |
| Banda de não-negociação | não testada | ⏳ pendência P4 |

**Por que suavizar o sinal não bastou:** mesmo com o sinal estável, o
*escalar de risco* variava 14% ao dia e as travas mudavam de posição — os dois
reintroduziam giro depois. Só suavizando **o que é de fato negociado** o
problema morre.

**Por que é seguro suavizar depois das travas de segurança:** a média móvel é
uma média de carteiras que já respeitam os limites. Como a média de valores
menores que um teto também é menor que o teto, os limites continuam válidos
automaticamente. (Provado no teste `test_suavizacao_nao_viola_travas`.)

**Segunda decisão importante: base de preços híbrida.**
Yahoo Finance manda nas 166 ações que ele cobre (já vem ajustado por
dividendos); o arquivo COTAHIST da B3 preenche **só** as ausentes. Descartamos
reconstruir tudo do COTAHIST — perderíamos o ajuste de proventos em 166 ações
para ganhar consistência que não precisamos.

## 3. Integrações tocadas

**Criados:**
- `fase 1 - preço ajustado/src/s1c_retornos_completo.py` — une as duas fontes
  de preço e limpa desdobramentos
- `data/precos/precos_cotahist.parquet` — preços de 1.088 ações da B3
- `data/precos/retornos_diarios_completo.parquet` — **base oficial nova** (543 ações)
- `data/precos/cdi_diario.parquet` — CDI do Banco Central (cache)
- `data/betas_sinapse.parquet` — betas reais
- `data/universo/adtv_diario.parquet` — volume médio diário real

**Alterados:**
- `fase 2 .../s2_universo.py` — passa a extrair preço e volume diário do COTAHIST
- `fase 4 .../s4_sinapse_sinal.py` — salva betas, suaviza sinal, corrige caminho do setor
- `fase 4 .../grafo_manual_base.csv` — 16 elos `concorrente` invertidos
- `fase 5 .../s5_portfolio_builder.py` — vol-targeting reescrito + suavização de pesos
- `fase 5 .../exec_s5.py` — usa beta e ADTV reais em vez de valores fictícios
- `fase 3 .../s3_backtest.py` — benchmark CDI + painel de diagnóstico
- `fase 5 .../tests/` — 6 testes passando (1 ajustado, 1 novo)

## 4. Safeguards — bugs corrigidos e como não voltam

**Bug 1 — o mais grave: mapa de setores nunca era lido**
`s4_sinapse_sinal.py` procurava `mapeamento_setores.csv` uma pasta acima do
lugar certo. O arquivo nunca era encontrado, o script seguia como se nenhuma
ação tivesse setor, e isso tornava a regressão matematicamente degenerada. A
biblioteca **não deu erro** — devolveu resultado vazio, que virou, disfarçado,
o retorno bruto da ação. **Na prática, o sinal da Sinapse nunca fez o que
deveria fazer.**
→ *Safeguard:* o Bloco 4 agora salva `betas_sinapse.parquet`, e beta vazio ou
absurdo é imediatamente visível. Detectamos exatamente assim.

**Bug 2 — vazamento no hedge**
Em dias em que o calendário das ações e o do Ibovespa divergiam (feriados), o
retorno do hedge era tratado como zero — o peso existia mas "não rendia nada".
→ *Safeguard:* esses dias agora são **descartados** e o script imprime quantos
foram (36 em 10 anos).

**Bug 3 — arquivos salvos no lugar errado**
Scripts usavam caminhos relativos à pasta de execução, criando pastas `data/`
duplicadas.
→ *Safeguard:* todos resolvem a raiz do projeto a partir do próprio arquivo.

**Bug 4 — controle de risco anulado**
O ajuste de risco rodava **antes** das travas de segurança, que depois cortavam
os pesos e desmontavam o ajuste (12% viravam 3%).
→ *Safeguard:* as duas etapas agora se alternam 3 vezes, **sempre terminando
nas travas**, e o backtest alerta se a vol ficar abaixo de metade do alvo.

## 5. Como validar

Rode nesta ordem, a partir da raiz do projeto:

```bash
python "fase 2 - universo liquidez/s2_universo.py"              # ~30s (lê 3,7 GB)
python "fase 1 - preço ajustado/src/s1c_retornos_completo.py"
python "fase 4 - sinal da sinapse/src/s4_sinapse_sinal.py"
python "fase 5 - construcao da carteira/src/exec_s5.py"
python "fase 3 - backtest/src/s3_backtest.py"
```

**O que deve aparecer no final:**

| Verificação | Valor esperado |
|---|---|
| Correlação com Ibovespa | entre −0,3 e +0,3 (hedge OK) |
| Giro médio diário | < 10% |
| Retorno líquido | positivo |
| Cobertura do universo (passo 2) | 249/253 (98%) |

**Testes:** `cd "fase 5 - construcao da carteira" && python -m pytest tests/ -q`
→ 6 passando.

## 6. Lacunas e pendências

| # | Pendência | Por que importa |
|---|---|---|
| **P1** | **Validação anti-overfitting** | A inversão do grafo foi decidida olhando os dados. Enquanto não houver validação limpa, **o +8,7% não é confiável**. Ver dúvida 1. |
| **P2** | **Grafo ainda é 100% sobrevivente** | As 44 empresas foram escolhidas sabendo quais existem hoje. Viés **não resolvido**. |
| **P3** | Expandir grafo (23 → 100+ elos) | Gargalo estrutural: com 23 apostas o teto de retorno é baixo. **É o item que decide a viabilidade.** |
| **P4** | Vol em 5,7% contra meta de 12% | As travas de liquidez limitam. Sozinho, levaria a ~2%/ano. |
| **P5** | Retry no Yahoo Finance | 5 ações vivas caíram no COTAHIST (sem ajuste de dividendo) por falha de download. |
| **P6** | Dividendos não ajustados nas deslistadas | Aceito e medido (viés 0,00%/ano). |
| **P7** | Negociar também as `empresa_A` | Metade da informação do grafo é descartada. |

---

# PARTE 2 — Cronologia técnica

### Etapa 1 — Refatoração do motor (Bloco 3)
Motor deixou de gerar sinal próprio (equal-weight mensal) e passou a consumir
`df_weights_sinapse.parquet` do Bloco 5: multiplicação matricial diária
`(pesos × retornos).sum(axis=1)`, sem loop, sem lag próprio (o lag T+1 já vem
do Bloco 5 via `.shift(1)`).
**Resultado:** −20,7% · Sharpe −0,40 · corr 0,02.

### Etapa 2 — Substituição dos dados fictícios
- **Beta:** `calcular_choque_limpo` já calculava `res.params['IBOV']` na
  regressão rolling de 252 dias e **descartava**. Passou a salvar.
- **ADTV:** `s2_universo.py` estendido para acumular volume por **dia** (antes
  só por mês) → média móvel de 21 pregões.
- **Custo:** `CUSTO = 0.0005` (5 bps sobre giro de duas pontas).

### Etapa 3 — 🔴 Descoberta do bug do mapa setorial
Ao salvar o beta, ele veio **100% vazio**. Investigação: caminho do
`mapeamento_setores.csv` errado (`'..','..'` em vez de `'..'`) → mapa vazio →
coluna `SETOR` constante zero → regressão degenerada → `RollingOLS` devolveu
NaN silenciosamente → `y_pred` virou 0 → **resíduo = retorno bruto**.
**Resultado após corrigir:** −63,0% · Sharpe −1,89.

### Etapa 4 — Diagnóstico quantitativo (antes de qualquer correção)
Três scripts de diagnóstico mediram:

1. **IC** (correlação transversal sinal[T] × retorno[T+1]): **0,0009, t=0,22**
   → ruído. Mesmo dia: −0,033 (t=−7,87) → suspeito.
2. **Teste elo a elo** — a descoberta central:

| tipo de elo | direção | corr T+1 | veredito |
|---|---|---|---|
| holding_subsidiaria | +1 | +0,040 | funciona |
| cliente | +1 | +0,025 | funciona |
| **concorrente** | **−1** | **−0,033** | **invertido** |

3. **Decomposição do P&L:** alfa 6,1 bps/dia vs custo 6,9 bps/dia.
4. **Neutralidade:** net/gross +0,0026 → book correto, não mexer.

### Etapa 5 — Fase 1: correções
- Grafo: 16 elos `concorrente` → +1. IC salta para **0,0180 (t=3,17)**.
- `JANELA_SUAVIZACAO = 21` no sinal.
- Vol-targeting reescrito: `_estimar_vol_portfolio` usa `w'Σw` (covariância
  real) no lugar da proxy de correlação zero, que errava o alvo por 2,6x.
  Iteração vol↔travas 3x, terminando nas travas.
- CDI via API SGS/BCB (série 12) + painel de diagnóstico no Bloco 3.

**Resultado intermediário:** −1,3% · giro ainda 18%/dia.

### Etapa 6 — Investigação do giro residual
Medição estágio a estágio revelou que o **escalar de vol** variava 14%/dia,
remontando o book. Testes comparativos levaram a suavizar **os pesos finais**
(`janela_suavizacao_pesos = 10`), aplicada após as travas.
**Resultado:** **+19,9%** · giro 5,3%/dia · custo 8,67% → 0,66%/ano.

**Testes:** `test_limite_peso_setorial` falhou — usava pico de sinal de 1 dia,
que a suavização dilui. Ajustado o **cenário** (sinal sustentado por 15d),
mantendo a asserção original. Novo `test_suavizacao_nao_viola_travas`.

### Etapa 7 — Fase 2: viés de sobrevivência
Medição: **87 de 253** ações do universo sem preço; **65 já mortas**
(KROT3, CIEL3, BTOW3, HGTX3, LINX3, GNDI3, GOLL4...).

- `s2_universo.py`: extrai `PREULT [108:121]/100 ÷ FATCOT [210:217]` →
  `precos_cotahist.parquet` (1.088 tickers).
- **Problema:** preço bruto não é ajustado. PDGR3 fez grupamento 1:50 →
  "+4.900%" num dia. Correlação com yfinance: apenas **0,84**.
- `s1c_retornos_completo.py`: detecção de split (variação > 35% **E** razão
  perto de fator simples ±12%), filtro de ações < R$1, teto de 50%.

| | bruto | + split | + preço≥R$1 |
|---|---|---|---|
| corr mediana | 0,976 | 0,993 | **0,993** |
| desvio da diferença | 0,4486 | 0,3918 | **0,0096** |

Erro reduzido **46x**. União híbrida → 543 tickers, cobertura **66% → 98%**.

**Otimização:** com 543 ações, `calcular_choque_limpo` ganhou `tickers_alvo`
para regredir só as ~44 do grafo (índices setoriais seguem usando tudo).

**Resultado final:** **+8,7%** · líquido +1,01%/ano · vol 5,70% · corr −0,01.

---

# PARTE 3 — Dúvidas respondidas

### 1. Inverter o sinal com base em testes não é viés?

**Sim, é um risco real — e é a fragilidade mais séria do que fizemos.**

Não é viés de *sobrevivência* (esse é sobre empresas que sumiram). O nome
correto é **viés de "espiar os dados"** (*data snooping*): eu olhei 10 anos de
resultado, vi que `concorrente = −1` perdia dinheiro, e inverti. Qualquer
regra escolhida assim parece boa **no período em que foi escolhida**.

O que **atenua**:
- A inversão foi aplicada à **categoria inteira** (16 elos), não elo a elo. Se
  eu tivesse invertido só os 11 que testaram mal, seria puro ajuste de curva.
- Existe justificativa econômica *a priori* (ver dúvida 2).
- O teste 2016-2020 → 2021-2025 não degradou (Sharpe 0,58 → 0,87).

O que **não** atenua:
- Esse teste está **contaminado**: a decisão de inverter usou a amostra
  inteira, incluindo 2021-2025. Não é out-of-sample de verdade.

**Conclusão honesta: enquanto a pendência P1 não for feita, o +8,7% não deve
ser tratado como resultado confiável.** O protocolo correto é definir as
direções usando **só** 2016-2020, congelar, e medir 2021-2025 sem tocar em
mais nada.

### 2. Se a VALE cai, a CSN não deveria subir? A relação não é inversa?

**Sua lógica econômica está certa** — o problema é que existem **dois canais
agindo ao mesmo tempo**, e o mais forte não é o da competição:

| Canal | Direção | Velocidade | Força |
|---|---|---|---|
| **Fator compartilhado** (minério, demanda da China) | mesma direção | imediata | **forte** |
| **Competição** (VALE ganha share, CSN perde) | direção oposta | lenta (trimestres) | fraca |

No dia a dia, o fator compartilhado domina. Por isso o dado mostra
`corr(choque_VALE3, retorno_CSNA3[T+1]) = +0,09`.

**"Mas a regressão não removia o efeito do setor?"** Deveria — e essa é a raiz
do problema. O controle usa a média do **setor B3 inteiro**, que é grosseiro
demais: ele não remove o que VALE3 e CSNA3 realmente compartilham
(especificamente minério de ferro). Sobra fator de commodity dentro do
"choque idiossincrático", e é isso que respinga positivamente.

> **Importante:** o `+1` é um **remendo que reflete o que o dado contém hoje**,
> não a afirmação de que concorrentes se ajudam. Se o controle setorial ficar
> mais fino (pendência P4 — subsetor ou fator de commodity), o choque isolado
> passa a ser competição de verdade e **o −1 pode voltar a ser o correto**.

### 3. O que mudou no giro? As negociações continuam diárias?

**Sim, continuam diárias.** O que mudou foi **o tamanho** de cada ajuste.

- **Antes:** todo dia o sistema calculava a carteira ideal do dia e a montava
  do zero. ~69% da carteira trocava de mãos diariamente.
- **Agora:** a carteira-alvo do dia é a **média das 10 carteiras-alvo
  anteriores** (e o próprio sinal já é a média de 21 dias). Como a média de
  hoje e a de ontem são quase iguais, sobra pouco a negociar: **5,8%/dia**.

Analogia: o navio continua sendo corrigido todo dia, mas gira o leme devagar
em vez de virar bruscamente a cada notícia.

**Não é semanal nem mensal** — é diário, com passos pequenos. Efeito no custo:
**8,67% → 0,66% ao ano**.

### 4. Volatilidade em 3% não é melhor? Não significa mais estabilidade?

**Significa mais estabilidade, sim — mas não é bom aqui.** Em fundos, risco e
retorno são a mesma alavanca: `retorno ≈ qualidade × risco assumido`.

Rodar a 3% quando o mandato permite 12% é deixar **4x o retorno na mesa** sem
ganhar nada em troca — porque quem quer segurança tem o CDI, que paga ~9% ao
ano com **zero** risco. Uma estratégia com 3% de volatilidade rendendo 1% ao
ano é **estritamente pior que não fazer nada**.

A meta de 12% não é "quanto de risco toleramos", é **quanto de risco
precisamos assumir para o retorno fazer sentido**. Se você quer menos risco,
o certo é investir menos dinheiro na estratégia (e o resto no CDI) — não
espremer a estratégia.

> ⚠️ **Ressalva:** alavancar só faz sentido se a qualidade (Sharpe) for
> positiva e **real**. Alavancar uma estratégia ruim só perde dinheiro mais
> rápido. Por isso a ordem correta é: **primeiro P1 (provar o edge), depois
> destravar a volatilidade.**

### 5. Como você garante que o grafo não tem viés de sobrevivência?

**Não garanto. Ele tem.** Esta é a pendência **P2**, e continua aberta.

As 44 empresas do grafo foram escolhidas em 2025/2026 por alguém que já sabe
quais existem. Um analista em 2016 teria escrito elos com Kroton, Cielo, B2W e
Hering — que eram gigantes e hoje não existem.

O que a sessão fez foi **remover o obstáculo**: agora temos preço das empresas
mortas, então a expansão do grafo (P3) **pode** ser feita sem viés. Mas os 30
elos atuais continuam selecionados entre sobreviventes.

### 6. Como garantir que as correções desde os −63% não têm viés, se você já conhecia os dados?

Separando por tipo. **A maioria não depende dos dados:**

| Correção | Depende do resultado? |
|---|---|
| Bug do mapa setorial | ❌ erro objetivo de caminho |
| Beta / ADTV / custo reais | ❌ trocar fictício por real |
| Covariância no lugar de correlação zero | ❌ correção matemática |
| Ordem vol-targeting × travas | ❌ erro lógico de ordem |
| Vazamento do hedge em feriados | ❌ bug |
| Base sem viés de sobrevivência | ❌ **piorou** o resultado |

**Duas dependem, e são as que exigem cautela:**

| Correção | Risco |
|---|---|
| 🔴 Inversão do `concorrente` | escolhida olhando o resultado |
| 🟡 Janelas de suavização (21d e 10d) | escolhidas varrendo valores e pegando o melhor Sharpe |

**O melhor argumento de que não houve ajuste de curva sistemático:** quem está
"fazendo o número bonito" não implementa uma correção que derruba o resultado
de +19,9% para +8,7%. Fizemos isso de propósito.

Ainda assim, a resposta honesta é: **duas mudanças precisam de validação
limpa (P1) antes de confiar no número.**

### 7. E as três "descobertas", têm viés?

| Descoberta | Depende dos dados? | Avaliação |
|---|---|---|
| **1. Metade do grafo invertida** | **Sim** | 🔴 Risco real. É a mesma questão da dúvida 1. |
| **2. Negociava demais** | **Não** | ✅ É aritmética: 138% de giro × 5bps = 8,7%/ano de custo. Vale para qualquer estratégia, boa ou ruim. Só a *escolha da janela* (21d/10d) tem risco leve. |
| **3. Freio de mão puxado** | **Não** | ✅ É comparação contra a meta de 12%, definida no `PARAMETROS.md` **antes** desta sessão. Medir 3,2% contra 12% é só medição. |

Ou seja: **das três descobertas, só a primeira precisa de validação.**

### 8. Todo o escopo do viés de sobrevivência foi implementado?

Comparando com a arquitetura que você planejou:

| Item planejado | Status |
|---|---|
| Yahoo como fonte primária (~166 ações) | ✅ implementado |
| **Retry com delay no Yahoo** | ❌ **não implementado** (pendência P5) |
| COTAHIST para deslistadas | ✅ implementado |
| Heurística de detecção de splits | ✅ implementado, **método diferente** ⬇️ |
| Dividendos não ajustados nas deslistadas | ✅ decisão mantida — **e medida** |
| Cobertura do universo | ⚠️ 98% (249/253), não 100% |

**Diferença no método de split:** você planejou detectar o split e
*multiplicar retroativamente a série anterior* pelo fator. Eu **zerei o retorno
do dia do evento**. Para backtest baseado em retornos, os dois são
equivalentes na prática — a diferença é que o meu descarta o movimento real
daquele único dia. Também usei um discriminador diferente: em vez de checar se
o Ibovespa caiu junto, exijo que a **razão de preços caia perto de um fator
simples** (2x, 10x, 1/50). É mais preciso para grupamentos.

> ⚠️ **Atenção:** `precos_cotahist.parquet` continua com preços **brutos, não
> ajustados**. Só o arquivo de **retornos** (`retornos_diarios_completo.parquet`)
> está limpo. Não use o de preços para calcular retorno diretamente.

**Sobre dividendos:** sua premissa ("o ruído é absorvido pela regressão") foi
**confirmada com número**: o viés sistemático medido é **0,00% ao ano** e o
desvio caiu para 0,0096. Não é suposição, é medição.

**Além do planejado**, foram adicionados dois filtros que a arquitetura
original não previa e que se mostraram necessários:
- **ações de centavos** — PDGR3 a R$0,02 gera "retorno" de +50% por
  arredondamento de 1 centavo (correlação era **negativa**, −0,12);
- **teto de 50%** para eventos societários não mapeados (cisões: PCAR3/Assaí,
  NATU3, AMER3, OIBR4).

**O que falta para fechar 100%:** P5 (retry no Yahoo — 5 ações vivas caíram no
COTAHIST sem ajuste de dividendo) e, principalmente, **P2: o grafo ainda é
selecionado entre sobreviventes.** Corrigir o preço foi metade do problema; a
outra metade é *quais relações você escolhe escrever*.
