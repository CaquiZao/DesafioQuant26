# Sessão 04/08 (parte 2) — Documentação completa

> Objetivo desta sessão: **atacar as pendências abertas** (P1, P2, P4, P5, P7)
> sem expandir o grafo (P3 ficou fora do escopo por decisão).
> Resultado: **+8,5% → +27,9%** de alfa, com o viés de seleção do grafo
> eliminado e **4 bugs** corrigidos — três deles descobertos por acaso,
> ao investigar outra coisa.
>
> Ponto de partida: branch `correcoes-sinapse-04-08`, commit `a8ab81c`.
> Continuação de `SESSAO_COMPLETA_04_08.md` (sessão da madrugada).

---

# PARTE 1 — Visão geral

## 1. O que foi feito

A sessão fez **quatro coisas distintas**, nesta ordem:

**(a) Validou a estratégia com um protocolo out-of-sample honesto.** A
inversão do `concorrente` (decidida em 03/08 olhando os 10 anos inteiros)
era a fragilidade mais séria do projeto. Foi testada e **sobreviveu**.

**(b) Testou e rejeitou uma expansão.** A ideia de negociar também as
`empresa_A` (dobrar as apostas sem criar elos novos) foi medida com o mesmo
rigor e **reprovada** — o ganho estava dentro do ruído.

**(c) Eliminou o viés de seleção do grafo.** As 44 empresas tinham sido
escolhidas sabendo quem sobreviveu. Agora são 74, incluindo 30 que
morreram no meio do caminho.

**(d) Corrigiu 4 bugs**, três deles achados sem estar procurando.

**Evolução do resultado (período completo, 10 anos):**

| # | O que mudou | Alfa total | Alfa/ano | Sharpe | Vol | Excesso s/ CDI |
|---|---|---|---|---|---|---|
| 1 | ponto de partida (fim da sessão 1) | +8,7% | +1,01% | −1,40 ❌ | 5,70% | −133,2% ❌ |
| 2 | + Sharpe/benchmark corrigidos | +8,7% | +1,01% | **+0,18** | 5,70% | **+21,0%** |
| 3 | + trava de liquidez respeitada | +8,5% | +1,01% | +0,17 | 5,70% | +20,5% |
| 4 | + grafo point-in-time (P2) | +11,6% | +1,35% | +0,20 | 6,85% | +28,2% |
| 5 | + mapeamento setorial corrigido | **+27,9%** | **+2,81%** | **+0,36** | **7,84%** | **+67,5%** |

*Referências no período: CDI +141,9% · Ibovespa +279,8%.*

> ⚠️ Os passos 1→2 e 3→4→5 **melhoram** o número, o que exige explicação
> numa sessão de correção de viés. Os passos 2 e 5 corrigem **erros de
> medição** (não de estratégia): o resultado sempre foi este, estava sendo
> mal calculado. O passo 4 faz duas coisas ao mesmo tempo e está detalhado
> na dúvida 4 da Parte 3.

**Validação out-of-sample (2021–2025, direções congeladas em 2020):**

| métrica | valor |
|---|---|
| Alfa | **+3,91% ao ano** |
| Sharpe | **0,50** |
| Volatilidade | 7,86% |
| IC | +0,0091 (t = 1,72) |

## 2. Decisão técnica central — e as alternativas descartadas

**A decisão central foi: como provar que a direção dos elos não foi
escolhida olhando o futuro.**

A primeira abordagem foi a óbvia: decidir as direções usando só 2016–2020,
congelar, medir 2021–2025. Funcionou — mas revelou um defeito na própria
regra.

| Regra de decisão | Comportamento | Decisão |
|---|---|---|
| Congelar pelo **sinal** da correlação no IS | Inverte categoria mesmo com t = −0,20 (ruído puro) | ❌ ajusta curva em outro período |
| **Prior econômico + inverter só com \|t\| ≥ 2** | Só `concorrente` passa (t = 4,50) | ✅ **escolhida** |
| Manter o prior sempre (`pre_inversao`) | Alfa OOS negativo, IC negativo | ❌ refutada pelo dado |

**O achado que fecha a questão:** os 30 elos que a regra conservadora
produz são **idênticos** aos que já estavam em produção. Ou seja, as
direções do `grafo_manual_base.csv` são reproduzíveis por uma regra que
qualquer analista escreveria em 2020, sem ver nada de 2021+. A acusação de
*data snooping* fica respondida **sem depender do resultado do backtest**.

**Segunda decisão importante: adotar o grafo point-in-time mesmo piorando
o Sharpe.** O grafo expandido derruba o Sharpe OOS de 0,62 para 0,45 —
essa queda **é** a medida do viés que existia. Seguimos o mesmo princípio
que o projeto já aplicou em 03/08 ao viés de preço (+19,9% → +8,7%): o
número honesto vale mais que o número bonito.

## 3. Integrações tocadas

**Criados:**
- `fase 6 - validacao/src/s6_validacao_oos.py` — protocolo IS/OOS (P1)
- `fase 6 - validacao/src/s7_teste_bidirecional.py` — teste da P7
- `fase 6 - validacao/src/s8_diagnostico_vol.py` — diagnóstico da P4 + curva de capacidade
- `fase 6 - validacao/src/s9_teste_vol_corrigida.py` — registro de resultado negativo
- `fase 6 - validacao/src/s10_vies_selecao_grafo.py` — medição do viés (P2)
- `fase 6 - validacao/src/s11_grafo_point_in_time.py` — correção da P2
- `fase 4 - sinal da sinapse/grafo_historico.csv` — 28 elos com empresas mortas
- `fase 4 - sinal da sinapse/src/s4b_atualiza_setores.py` — manutenção do cadastro setorial
- `Registros dos processos/DIAGNOSTICO_P5_RETRY_YAHOO.md`

**Alterados:**
- `fase 3 .../s3_backtest.py` — Sharpe sem dupla contagem do CDI + curva do fundo
- `fase 4 .../s4_sinapse_sinal.py` — carrega o grafo histórico
- `fase 4 .../mapeamento_setores.csv` — 200 tickers classificados, 2 acrescentados
- `fase 5 .../s5_portfolio_builder.py` — passos 3c (travas pós-suavização) e 3d (máscara de negociabilidade)
- `fase 5 .../tests/` — **8 testes passando** (6 antigos + 2 novos)
- `fase 1 .../config/tickers_sem_preco.csv` — motivos específicos no lugar de genéricos

## 4. Safeguards — bugs corrigidos e como não voltam

**Bug 1 — dupla contagem do CDI no Sharpe** 🔴
`s3_backtest.py` subtraía o CDI de um P&L long-short que **já é excesso
sobre o caixa**. A carteira é autofinanciada (as vendidas financiam as
compradas) e o AUM fica em caixa rendendo CDI — então o retorno do fundo é
`CDI + alfa`, não `alfa` competindo contra o CDI.
*Sintoma:* Sharpe **−1,40 com retorno positivo**, o que é incoerente.
→ *Safeguard:* o comentário no código explica por que o Ibovespa **continua**
medido como excesso sobre CDI (é um investimento comprado e financiado) —
para ninguém "uniformizar" os dois cálculos no futuro.

**Bug 2 — trava de liquidez violada em 60% dos dias** 🔴
A suavização dos pesos rodava **depois** das travas e não as reaplicava,
justificada por um argumento de convexidade (`|média(w)| ≤ média(|w|)`).
Esse argumento vale para limites **constantes** (5% por nome, 25% por
setor) — mas a trava de liquidez **varia no tempo**.
*Tamanho:* 59,6% dos dias com ao menos uma violação, 5,2% do book em
posição ilegal, pior dia com **74% do book**, incluindo posição em ação com
ADTV = 0 (não negociou nada naquele pregão).
→ *Safeguard:* passo 3c + `test_suavizacao_respeita_trava_de_liquidez_variavel`,
verificado que **falha** no código antigo (+0,0241) e **passa** no novo.

**Bug 3 — posições fantasma em ações mortas** 🔴
Ação que para de negociar continuava com peso: consumia limite de risco e
de setor, entrava no cálculo de volatilidade, e rendia exatamente zero.
*Mesmo padrão do Bug 2:* zerar o sinal na entrada não bastava, porque a
suavização **ressuscita** o peso dos 10 pregões anteriores.
*Tamanho:* 2,07% do book em média — **já existia no grafo só de
sobreviventes**, não foi criado pela P2.
→ *Safeguard:* passo 3d + `test_acao_delistada_nao_carrega_posicao_fantasma`,
verificado que falha no código antigo (5,0% de peso fantasma) e passa no
novo (0,0%).

**Bug 4 — mapeamento setorial 79% vazio** 🔴 *(o mais grave)*
**201 dos 253 tickers** estavam com o setor literal `"A DEFINIR"`, incluindo
**43 das 74 empresas do grafo**. Consequências:
1. A regressão do choque limpo usava, como "índice setorial", a média de
   200 ações de todos os setores misturados — **praticamente o mercado**.
   `IBOV` e `SETOR` ficavam quase colineares, e o resíduo chamado de
   "choque idiossincrático" ainda continha o movimento setorial inteiro.
2. A trava de 25% tratava 43 empresas do grafo como **um setor só**.

> É uma variante do Bug 1 da sessão de 03/08 (mapa de setores nunca lido).
> Lá o arquivo não era encontrado; aqui ele é lido mas está quase vazio — e
> **falha silenciosamente do mesmo jeito**, porque `"A DEFINIR"` é uma
> string válida que agrupa em vez de dar erro.

→ *Safeguard:* `s4b_atualiza_setores.py` é idempotente e termina imprimindo
**"empresas do grafo sem setor: X de 74"** — um número diferente de zero
fica visível na hora.

## 5. Como validar

Rode nesta ordem, a partir da raiz do projeto:

```bash
python "fase 2 - universo liquidez/s2_universo.py"              # ~30s (lê 3,7 GB)
python "fase 1 - preço ajustado/src/s1c_retornos_completo.py"
python "fase 4 - sinal da sinapse/src/s4b_atualiza_setores.py"  # cadastro setorial
python "fase 4 - sinal da sinapse/src/s4_sinapse_sinal.py"
python "fase 5 - construcao da carteira/src/exec_s5.py"
python "fase 3 - backtest/src/s3_backtest.py"
```

**Validação (Bloco 6, opcional mas é o que sustenta a tese):**

```bash
python "fase 6 - validacao/src/s6_validacao_oos.py"    # P1: protocolo IS/OOS
python "fase 6 - validacao/src/s10_vies_selecao_grafo.py"  # P2: viés de seleção
python "fase 6 - validacao/src/s8_diagnostico_vol.py"  # P4 + curva de capacidade
```

**O que deve aparecer no final:**

| Verificação | Valor esperado |
|---|---|
| Correlação com Ibovespa | entre −0,3 e +0,3 (hedge OK) |
| Alfa líquido | positivo (~+2,8%/ano) |
| Excesso sobre o CDI | positivo (~+67%) |
| Empresas do grafo sem setor | **0 de 74** |
| Grafo reproduzível por regra a priori (etapa 2b) | **SIM** |
| Cobertura do grafo (s10) | "parecida nos dois extremos" |

**Testes:** `cd "fase 5 - construcao da carteira" && python -m pytest tests/ -q`
→ **8 passando**.

## 6. Lacunas e pendências

| # | Pendência | Status | Por que importa |
|---|---|---|---|
| **P1** | Validação anti-overfitting | ✅ **fechada** | Direções reproduzíveis por regra a priori. Ressalva: IC ainda sem significância (t = 1,72). |
| **P2** | Grafo 100% sobrevivente | ✅ **fechada** | 74 empresas, 30 mortas incluídas. Custo honesto medido: −0,58 p.p./ano no OOS. |
| **P3** | Expandir grafo (58 → 100+ elos) | 🔴 **aberta** | **O gargalo único.** P1, P4 e P7 convergiram todas para cá. |
| **P4** | Vol abaixo da meta de 12% | 🟡 **parcial** | Subiu de 5,70% para 7,84% sem tocar em parâmetro de risco. Resto depende de P3. |
| **P5** | Retry no Yahoo Finance | ✅ **fechada** | Não era rate-limiting (404 permanente). Impacto medido: −0,005%/ano. |
| **P6** | Dividendos das deslistadas | ✅ fechada em 03/08 | Viés 0,00%/ano. |
| **P7** | Negociar as `empresa_A` | ✅ **rejeitada** | Ganho de Sharpe +0,06 (ruído). Sentido reverso é fraco em todas as categorias. |
| — | Testes no `s3_backtest.py` | 🔴 **aberta** | O Bug 1 não tem teste de regressão. O bloco não tem suíte. |
| — | Revisão da classificação setorial | 🟡 **aberta** | 200 tickers classificados por julgamento. Erros propagam para o choque limpo. |

---

# PARTE 2 — Cronologia técnica

### Etapa 1 — Levantamento das pendências
Mapeamento de P1–P7 a partir de `SESSAO_COMPLETA_04_08.md` §6 e
`duvidas.md`. Decisão: **P1 primeiro e sozinha**, porque todas as outras
mudam de sentido conforme o resultado dela (não faz sentido subir a
volatilidade ou dobrar as posições de uma estratégia sem edge comprovado).

### Etapa 2 — P1: protocolo out-of-sample
`s6_validacao_oos.py` reusa as funções dos Blocos 3, 4 e 5 por importação
direta (não reimplementa nada — senão validaria outra coisa).

Direções decididas **só** com 2016–2020 (1.273 pregões):

| tipo de elo | corr T+1 (IS) | t | decisão |
|---|---|---|---|
| **concorrente** | **+0,0375** | **4,50** | +1 |
| holding_subsidiaria | +0,0557 | 2,73 | +1 |
| cliente | +0,0194 | 1,39 | +1 |
| fornecedor | −0,0856 | −0,92 | ruído |
| imobiliario_logistica | −0,0038 | −0,20 | ruído |

**O ponto central:** um analista em 31/12/2020, sem ver nada de 2021+,
escolheria `concorrente = +1` do mesmo jeito, com t = 4,50. A inversão
**não precisou** do futuro.

Controle `pre_inversao` (`concorrente = −1`): alfa OOS negativo e IC
negativo — a hipótese econômica original estava mesmo errada.

**Sensibilidade das janelas:** nas 5 combinações testadas o OOS é positivo
(Sharpe 0,30 a 0,96), e o par escolhido (21/10) **nem é o melhor** — 42/10
seria. Overfit de janela colocaria a escolha no pico.

### Etapa 3 — 🔴 Descoberta do bug do Sharpe
Ao montar a tabela de métricas, apareceu **Sharpe −0,86 com alfa +5,03%** —
matematicamente incoerente. Investigação levou à dupla contagem do CDI
(Bug 1). Correção aplicada ao `s3_backtest.py`.
**Resultado:** Sharpe do período completo −1,40 → **+0,18**; excesso sobre
CDI −133,2% → **+21,0%**.

### Etapa 4 — P7: teste bidirecional (rejeitada)
Hipótese: se o choque da VALE informa a CSN, o choque da CSN informa a
VALE? Mesmo protocolo, direções do lado reverso congeladas no IS.

**A tese original se confirmou no dado** — o sentido reverso é
sistematicamente mais fraco em **todas** as 6 categorias (melhor |t| do
A→B = 4,50; do B→A = 1,21). A informação flui do grande e líquido para o
pequeno e lento.

Ganho de Sharpe no OOS: **+0,06** — ruído. Giro subia de 6,2% para 10,2%.

> **A armadilha que o protocolo pegou:** o lado reverso *sozinho* tem IC
> out-of-sample de **+0,0201 (t = 2,24)** — mais alto que o do lado
> original. Olhando só isso, pareceria uma descoberta. Mas no in-sample ele
> era fraco (t = 0,45). **Sinal que só aparece fora da amostra é mais
> provável ser sorte que edge.** Sem o protocolo, teríamos "descoberto" um
> alfa inexistente.

### Etapa 5 — P4: diagnóstico da volatilidade
`s8_diagnostico_vol.py` mediu a vol estágio a estágio. **A explicação de
03/08 estava errada** — não era a trava de liquidez:

- **Não é alavancagem:** escalar mediano 0,27 (a estratégia *desalavanca*),
  bate no teto de 3,0 em **0% dos dias**.
- **Não é capacidade:** a curva 20M/100M/300M (prevista no `PARAMETROS.md`
  §7 e nunca executada até hoje) mostra que reduzir o fundo 5× move a vol
  de 6,29% para apenas 6,51%. As travas são **substitutas** — relaxa uma,
  outra morde.
- **O loop não converge:** cada rodada o vol-targeting acerta 12% e as
  travas derrubam; em 3 iterações chegou a 7,12%, ainda subindo.
- **A suavização custa mais 16,4%** (7,12% → 5,95%) sem recalibração.

Três correções testadas (`s9`), **todas falharam**: a vol mal se move e o
Sharpe cai de 0,80 para 0,38, porque suavizar dentro do loop aplica a média
3× e destrói o sinal. Arquivo mantido como **registro de resultado
negativo**.

### Etapa 6 — 🔴 Bug da trava de liquidez
A verificação numérica de travas embutida no `s9` (que não confia no
argumento teórico) flagrou o Bug 2. Correção: passo 3c.
**Impacto no resultado: quase nulo** (alfa OOS +5,03% → +5,05%) — o melhor
desfecho possível, porque significa que a estratégia **não estava vivendo**
de posições inexequíveis.

> Detalhe que o teste revelou: o critério de verificação precisa comparar o
> peso contra o limite do dia da **decisão**, não da execução. Violação que
> só aparece por causa do lag `shift(1)` é inerente à execução real.

### Etapa 7 — P5: diagnóstico do Yahoo (fechada sem correção)
Os 5 tickers (AXIA6, CPLE5, GUAR3, NEOE3, PETZ3) falham com **HTTP 404
"Quote not found"** — imediato, consistente em 2 janelas de data e 2
endpoints. Controle: **8 de 8** tickers líquidos funcionam no mesmo
instante. **Retry não resolveria.**

Duas hipóteses minhas foram refutadas pelos próprios dados: (a) *"CPLE5
sumiu na unificação da Copel"* — o COTAHIST mostra ele negociando até
2025-12-19; (b) *"são ilíquidos demais"* — todos têm ADTV de R$20M a
R$124M.

> ⚠️ Armadilha de medição em que caí: calcular mediana de ADTV sobre a série
> inteira dá ~0 para ticker recente, porque os anos anteriores à existência
> do papel entram como **zero**, não NaN.

**Impacto medido:** dos 5, só GUAR3 está no grafo. O viés de dividendo não
ajustado nele é **−0,005%/ano** no pior caso (dy 6%), contra alfa de
+1,0%/ano — porque a carteira fica long 47,2% dos dias e short 52,8%, e o
viés se cancela entre as pontas.

### Etapa 8 — P2: grafo point-in-time
`s10_vies_selecao_grafo.py` mediu o viés antes de corrigir:

| medida | valor |
|---|---|
| Empresas do grafo não líquidas em 2016 | **20 de 44 (45%)** |
| Top-60 de 2016 que morreram | 39 — só **4** no grafo |
| Cobertura 2016–18 vs 2023–25 | 21,9% vs 29,7% (**1,4× mais nítido no presente**) |

`grafo_historico.csv`: 28 elos, 30 empresas mortas — Kroton/Estácio,
B2W/Magalu, Lojas Americanas/B2W, Hering/Renner, Cielo/Bradesco+BB,
Gol/Azul, BR Malls/Multiplan, Fibria/Klabin, Linx/Totvs, NotreDame/Hapvida,
Localiza/Locamerica, Eletrobras/CESP+EDP+Tietê.

> **Regra imposta ao escrever, e que importa para a defesa:** só relações
> **estruturais verificáveis na época** — mesmo setor com disputa direta,
> ou controle acionário declarado em balanço. Nenhum elo foi escrito a
> partir de desfecho conhecido. Isso **exclui** `GNDI3 → RDOR3` (Rede D'Or
> comprou a SulAmérica) e `LINX3 → STNE` (aquisição pela Stone).
> `LINX3 → TOTS3` entra porque disputavam software de gestão em 2016 —
> fato independente do que veio depois.

**Vigência temporal não precisou de coluna de data:** o elo morre sozinho
quando a empresa deixa de ter choque calculado.

Correção expôs o Bug 3 (posições fantasma), que **já existia** no grafo só
de sobreviventes.

**Resultado:** alfa OOS +3,71% → +3,13%, Sharpe 0,62 → 0,45. **Essa queda
é a resposta de P2** — a medida direta de quanto o resultado dependia de
olhar só para sobreviventes.

**Viés depois da correção:** dependência de empresas pós-2016 45% → 34%;
mortas cobertas 4 → 23; cobertura 2016–18 21,9% → **43,8%**; veredito do
script: *"olha para o presente"* → **"cobertura parecida nos dois
extremos"**.

### Etapa 9 — 🔴 O bug do mapeamento setorial
A pergunta *"o `mapeamento_setores.csv` não precisa ser atualizado?"*
destravou o achado mais grave da sessão (Bug 4). As 30 empresas novas
tinham setor — mas **201 dos 253 tickers** estavam em `"A DEFINIR"`,
incluindo 43 das 74 do grafo.

`s4b_atualiza_setores.py` classificou 200 tickers na taxonomia B3 e
acrescentou 2 ausentes (FIQE3, LOGG3). Segui a B3 mesmo onde é
contra-intuitiva: shoppings → **Financeiro**; construção civil → **Consumo
Cíclico**; serviços educacionais → **Consumo Cíclico**; holdings seguem o
ativo principal (BRAP4 → Materiais Básicos, ITSA4 → Financeiro).

**Impacto — incluindo revisão do meu próprio diagnóstico de P4:** a trava
setorial caiu de **−55,9% para −32,9%**. Boa parte do que eu havia
diagnosticado como "limite estrutural da trava setorial" era artefato do
cadastro quebrado. A ordem das travas mudou:

| trava | antes | depois |
|---|---|---|
| liquidez | −53,0% | **−44,4%** (agora a maior) |
| setor | **−55,9%** | −32,9% |
| nome | −32,1% | −25,1% |

**Resultado final:** alfa **+27,9%** · +2,81%/ano · Sharpe **0,36** · vol
**7,84%** · excesso sobre CDI **+67,5%**.

> **Resolveu a assimetria que incomodava na P1:** o in-sample tinha alfa
> **negativo** (−1,99%) e o OOS positivo — o inverso do padrão de overfit,
> e eu não sabia explicar. Era em boa parte artefato do mapeamento
> quebrado. Agora IS = **+1,69%** e OOS = **+3,91%**: os dois positivos, na
> mesma direção.

---

# PARTE 3 — Dúvidas respondidas

### 1. Por que o excesso sobre o CDI é +67,5% e não +27,9% (o alfa)?

**É matemática de composição, não outro número.** O alfa e o CDI são cada
um um retorno composto ao longo de 10 anos. Quando você junta os dois num
fundo só (CDI + alfa todo dia, composto dia após dia), o efeito é um
**produto**, não uma soma:

```
retorno do fundo ≈ (1 + CDI_total) × (1 + alfa_total) − 1
                  = 2,419 × 1,279 − 1
                  = 2,094  →  +209,4%
```

E portanto:

```
excesso = retorno_fundo − CDI_total = (1 + CDI_total) × alfa_total
        = 2,419 × 0,279 = 0,675  →  +67,5%
```

**A intuição:** o alfa não é aplicado sobre o capital inicial parado — ele
é aplicado, dia após dia, sobre o patrimônio que **já cresceu** por causa
do CDI acumulado. Em 2025, quando o CDI já multiplicou o patrimônio por
~2,4×, um dia de alfa positivo vale mais em reais do que valeria em 2016.

Para comparar ano a ano sem esse efeito, use o **alfa anualizado
(+2,81%/ano)**, que é limpo da composição de longo prazo.

### 2. 🔑 Estamos "muito longe" do Ibovespa. Isso é ruim?

**Não. É exatamente o que a estratégia promete fazer.** Esta é a dúvida
mais importante desta seção, porque é o erro de leitura que a banca (ou o
grupo) mais provavelmente vai cometer.

#### O erro de comparação mais comum em finanças

Quando alguém vê "minha estratégia rendeu 27,9%" e "o Ibovespa rendeu
279,8%" no mesmo período, o instinto é pensar: *"nossa, ficamos muito
atrás, isso é ruim"*. Esse instinto está certo **só se as duas coisas
estivessem competindo pela mesma coisa**. E não estão.

#### Duas apostas completamente diferentes

**Comprar o Ibovespa** é apostar que "a bolsa brasileira vai subir". Você
compra um pouco de tudo e reza para o país ir bem. Nos últimos 10 anos, o
Brasil foi bem (apesar de todos os problemas) e a bolsa subiu 279,8%. Quem
fez essa aposta ganhou muito.

**A Sinapse não faz essa aposta.** Ela é *neutra ao mercado* de propósito:
para cada real comprado numa ação, ela vende (a descoberto) um real em
outra, de forma calculada para que **não importe** se a bolsa sobe ou desce
no geral. Ela está apostando em outra coisa: que consegue identificar quais
ações específicas vão se sair melhor ou pior que as outras, **independente**
do humor geral do mercado.

#### Por que comparar os dois é como comparar maçã com laranja

Imagina dois apostadores num cassino:

- **Apostador A** aposta que "vai chover amanhã" — uma aposta sobre o clima
  geral.
- **Apostador B** aposta que "vai chover mais em São Paulo do que no Rio
  amanhã" — uma aposta sobre a *diferença* entre dois lugares, não sobre o
  clima geral.

Se amanhã chover torrencialmente em todo o Brasil, o Apostador A ganha uma
fortuna. O Apostador B pode ganhar um pouco, perder um pouco, ou empatar —
porque a aposta dele nunca foi sobre "vai chover muito", foi sobre a
diferença relativa entre dois lugares. **Não faz sentido reclamar que o
Apostador B "ficou muito atrás" do Apostador A.** Eles fizeram apostas
diferentes.

A Sinapse é o Apostador B. O Ibovespa é o resultado do Apostador A.

#### O que prova que a Sinapse está fazendo o que diz que faz

Se a Sinapse *tivesse* subido e descido junto com o Ibovespa (alta
correlação), isso seria prova de que ela **não é** neutra ao mercado de
verdade — que na prática ela também está só "apostando que a bolsa sobe",
como qualquer fundo comum, e o hedge (a proteção vendida) não está
funcionando. Isso seria motivo de alarme.

O teste do Bloco 3 mede exatamente essa correlação todo dia, e ela deu
**próxima de zero** (entre −0,3 e +0,3, dentro do esperado). Isso é a prova
técnica de que a carteira realmente se descolou do movimento geral da bolsa
— que era o objetivo.

#### Contra quem ela deveria ser comparada, então

Contra o **CDI** — o rendimento "livre de risco" no Brasil (Tesouro/poupança
de banco, essencialmente). É contra isso que qualquer estratégia neutra ao
mercado precisa ser julgada, porque um investidor que não quer correr risco
nenhum já ganha o CDI sem fazer nada. A Sinapse rendeu **CDI + 67,5%
acumulado** no período — ou seja, **bateu** a alternativa sem risco, que é a
régua certa para ela.

> **Resumindo em uma frase:** a Sinapse ficar longe do Ibovespa não é ela
> "perdendo" — é ela fazendo exatamente o que prometeu fazer (não depender
> da bolsa subir), e o jeito certo de julgar se valeu a pena é comparando
> com o CDI, não com o índice.

### 3. Os resultados estão corretos? Dá para garantir?

**Não dá para garantir, e ninguém deveria garantir isso de um backtest.**
O que dá para separar é o que foi *verificado* do que continua incerto.

**Verificado:**

| verificação | status |
|---|---|
| Mecânica de P&L | ✅ 8 testes passando |
| Direções não dependem de ter visto 2021+ | ✅ regra a priori reproduz o grafo |
| Grafo não é 100% sobrevivente | ✅ corrigido e medido |
| Travas institucionais respeitadas | ✅ (era violada 60% dos dias) |
| Posições fantasma | ✅ zeradas |
| Sharpe/benchmark | ✅ dupla contagem corrigida |
| Cadastro setorial | ✅ 0 de 74 sem setor |

**Não resolvido — e é o que decide a confiabilidade:**

1. **Significância estatística fraca.** IC out-of-sample com t entre 1,4 e
   1,7, **abaixo do corte convencional de 2,0**. Não dá para descartar
   ruído com confiança estatística padrão.
2. **É uma única realização histórica.** 10 anos, uma trajetória só.
   Inerente a qualquer backtest.
3. **P3 não foi feito.** 74 empresas / 58 elos ainda é pouco para as
   apostas serem independentes o suficiente.
4. **Sensibilidade a bugs de dado.** O alfa saltou de +11,6% para +27,9% só
   por corrigir um cadastro. Um resultado que se move tanto com a correção
   de um bug é, por definição, sensível — motivo de cautela.

**Posição honesta para a banca:** *"o sinal aponta na direção certa e
sobreviveu a um protocolo out-of-sample honesto, mas a evidência estatística
ainda não é forte o suficiente para ser conclusiva — o próximo passo natural
é expandir a base de apostas."*

### 4. Corrigir viés não deveria PIORAR o resultado? Por que melhorou?

**Sim, deveria — e piorou, na parte que é de fato correção de viés.** O que
confunde é que a sessão fez duas coisas ao mesmo tempo.

| mudança | tipo | efeito |
|---|---|---|
| Grafo point-in-time (P2) | remove viés | **piora** o Sharpe OOS: 0,62 → 0,45 |
| Grafo point-in-time (P2) | dobra as apostas | **melhora** o retorno absoluto |
| Sharpe/CDI (Bug 1) | corrige **medição** | melhora (o número sempre foi este) |
| Mapeamento setorial (Bug 4) | corrige **dado** | melhora (o sinal estava degradado) |

**A distinção que importa:** a **qualidade por unidade de risco caiu**
(Sharpe OOS 0,62 → 0,45 na correção de P2); o **retorno absoluto subiu**
porque a carteira ficou maior (27 → 36 posições, vol 5,70% → 7,84%).

Os Bugs 1 e 4 não são correção de viés — são **erros de cálculo e de
cadastro**. Corrigir um termômetro quebrado não é trapaça: o resultado
sempre foi aquele, só estava sendo mal medido.

> Quem quisesse "fazer o número bonito" não implementaria o grafo
> point-in-time, que custa 0,58 p.p./ano de alfa no OOS de propósito.

### 5. Por que P3 virou "o gargalo único"?

Porque as três pendências atacadas nesta sessão **convergiram para a mesma
conclusão**, por caminhos independentes:

- **P1** disse: o sinal está na direção certa, mas **faltam apostas** para
  provar significância (IC com t = 1,72, abaixo de 2).
- **P7** disse: **não dá para arranjar mais apostas** reciclando os elos
  existentes — o sentido reverso é fraco demais.
- **P4** disse: a volatilidade não sobe porque as travas por nome e setor
  mordem um book **concentrado demais**; mais elos diluem isso.

Antes da sessão, expandir o grafo era "uma boa ideia". Agora é **o único
caminho** para as três coisas ao mesmo tempo — e com três argumentos
quantitativos por trás, não uma intuição.

A infraestrutura para fazer isso **sem** reintroduzir viés já está pronta:
`grafo_historico.csv` mostra o padrão de como escrever elos point-in-time, e
`s10`/`s11` medem o viés de qualquer grafo novo automaticamente.
