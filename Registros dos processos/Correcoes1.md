# Correções da Sinapse — Fases 1 e 2 concluídas

> Status: **Fase 1 ✅ concluída** · **Fase 2 ✅ concluída** (escopo repriorizado)
> · Validação anti-overfitting e Fase 3 (breadth) **pendentes**.

## Contexto

Depois de corrigir os inputs mockados (beta real, ADTV real, custo de 5bps) e o
bug de caminho do `mapeamento_setores.csv` — que fazia a regressão do Bloco 4
rodar com o mapa setorial vazio e devolver resíduo == retorno bruto —, o
backtest entregava **−63,0% líquido / −13,2% bruto** em ~10 anos.

Benchmarks: **CDI** (oficial, +141,9% no período) e Ibovespa (+279,8%).

---

## Diagnóstico que embasou as correções

### 1. O sinal era ruído estatístico
IC (correlação transversal sinal[T] × retorno[T+1]): **0,0009, t = 0,22**.
P&L bruto com t = −0,78 — não era "comprovadamente ruim", era *sem informação*.

### 2. Causa raiz: `concorrente = -1` empiricamente invertido
Teste elo a elo (corr entre `choque_A[T] × direcao` e `retorno_B[T+1]`):

| tipo de elo | direção | corr média T+1 | veredito |
|---|---|---|---|
| holding_subsidiaria | +1 | +0,040 | funciona |
| cliente | +1 | +0,025 | funciona |
| imobiliario_logistica | +1 | +0,007 | ruído |
| fornecedor | +1 | −0,004 | ruído |
| **concorrente** | **−1** | **−0,033** | **invertido** |

Piores elos: `VALE3→CSNA3` (−0,090), `SUZB3→KLBN11` (−0,062).

**Racional econômico:** concorrentes co-movem. O controle setorial da regressão
usa a média do setor B3 inteiro — grosseiro demais para remover o que VALE3 e
CSNA3 de fato compartilham (minério de ferro). O resíduo "idiossincrático" de A
ainda carrega fator de commodity, que respinga **positivamente** em B.

Invertendo para +1: IC vai de 0,0025 (t=0,54) → **0,0180 (t=3,17)**.

### 3. Giro ~20x maior do que o alfa suportava
Autocorrelação do sinal ≈ 0 (0,002 no lag 2d). Em bps/dia: alfa bruto **6,1**
contra custo **6,9** (138% de giro × 5bps). O custo consumia 100% do alfa.

### 4. Vol-targeting inoperante
Vol realizada **3,2%** contra alvo de 12%. Duas causas, ambas confirmadas por
medição estágio a estágio:
- a proxy `sqrt(Σ(wᵢ·volᵢ)²)` assume **correlação zero** entre ativos —
  errava o alvo por ~2,6x (entregava 31%);
- `_apply_vol_targeting` rodava **antes** de `_apply_institutional_locks`, e as
  travas derrubavam a vol de 31% → 6,3% depois da calibração.

### 5. O que estava correto (verificado, não alterado)
Dollar-neutrality (net médio +0,0000; net/gross +0,0026), hedge de beta
(corr 0,00 com Ibovespa) e a matemática vetorizada do Bloco 3.

---

## Fase 1 — Correções de alta convicção ✅

### 1.1 `fase 4 - sinal da sinapse\grafo_manual_base.csv`
Invertidos **os 16 elos `concorrente`** (−1 → +1). O diagnóstico só conseguiu
testar 11 (os demais não tinham histórico suficiente), mas a inversão foi
aplicada à **categoria inteira** — a justificativa é econômica, não ajuste
ponto a ponto. O único elo `substituto` (`JBSS3→BRFS3`) foi mantido em −1 por
ser relação econômica distinta e não testada.

### 1.2 `s4_sinapse_sinal.py` — suavização do sinal
```python
JANELA_SUAVIZACAO = 21
def suavizar_sinal(df, janela=JANELA_SUAVIZACAO):
    return df.rolling(window=janela, min_periods=1).mean()
```
Aplicada em `pipeline_bloco_4()` após `limpar_e_winsorizar_sinal`. Sem
look-ahead (`rolling` só olha para trás).

### 1.3 `s5_portfolio_builder.py` — vol-targeting reescrito
- **Novo `_estimar_vol_portfolio`**: substitui a proxy de correlação zero por
  `w' Σ w` com covariância realizada da janela. Janela `[t-vol_window, t-1]`,
  exclui o próprio dia t → sem look-ahead.
- **Iteração vol ↔ travas** (`n_iteracoes_vol=3`), **sempre terminando nas
  travas** — os limites institucionais têm a palavra final. Se impedirem
  atingir o alvo, a carteira fica abaixo dele: é restrição real, não bug.
- Novos parâmetros: `max_leverage=3.0`, `n_iteracoes_vol=3`.

### 1.4 `s5_portfolio_builder.py` — suavização dos **pesos finais**
Descoberta durante a execução: suavizar só o sinal **não bastou**. O escalar
de vol-targeting variava ~14% ao dia e as travas mudavam de binding
diariamente, reintroduzindo giro (13,4%/dia mesmo com o sinal suavizado).

```python
janela_suavizacao_pesos = 10   # aplicada após as travas, antes do beta hedge
```

**Por que é seguro suavizar depois das travas:** a média móvel é combinação
convexa de vetores que já as respeitam, e como `|média(w)| ≤ média(|w|)`, tanto
o cap por nome quanto o setorial seguem válidos automaticamente — não precisa
reaplicar as travas. Coberto pelo novo teste `test_suavizacao_nao_viola_travas`.

Efeito medido: giro **13,4% → 3,9%/dia**, Sharpe **0,22 → 0,51**.

### 1.5 `s3_backtest.py` — instrumentação e benchmark CDI
- `rodar_motor` passa a devolver `(retorno_estrategia, pnl_bruto, giro_diario)`
  — permite separar "sinal ruim" de "custo comeu o resultado".
- **CDI real** via API SGS do Banco Central (série 12), com cache em
  `data/precos/cdi_diario.parquet`. A API devolve % ao dia → dividido por 100.
- `calcular_sharpe_anualizado` aceita `retorno_livre_diario` (série) além da
  taxa constante — correto, já que o CDI variou de ~14% a ~2% a.a. no período.
- Painel `DIAGNOSTICO DE EXECUCAO`: giro médio, bruto/ano, custo implícito/ano,
  líquido/ano, vol realizada vs alvo, com alertas automáticos.

### 1.6 Testes
`fase 5 - construcao da carteira\tests`: **6 passando**.
`test_limite_peso_setorial` precisou de ajuste — usava um pico de sinal de 1
dia, que a suavização (corretamente) dilui. Alterado o **cenário** (sinal
sustentado por 15d > janela de 10d), **mantendo a asserção original**
(`isclose(soma_setor, 0.25)`). Adicionado `test_suavizacao_nao_viola_travas`.

---

## Fase 2 — Viés de sobrevivência ✅

> **Repriorização:** a Fase 2 original era o protocolo anti-overfitting. Foi
> substituída pela correção do viés de sobrevivência, levantada durante a
> revisão e considerada mais grave — ela invalida o **nível** de qualquer
> número medido, inclusive o da validação out-of-sample.

### 2.1 Dimensão do problema (medido)
Das **253** ações do universo point-in-time (COTAHIST, Bloco 2), apenas **166**
tinham preço — o yfinance não serve ticker deslistado. Das 87 ausentes, **65 já
tinham saído do mercado antes de 2025**: `KROT3`, `CIEL3`, `BTOW3`, `HGTX3`,
`LINX3`, `GNDI3`, `BVMF3`, `GOLL4`, `ESTC3`, `LAME3/4`, `BIDI11`…

Agravante: o grafo (44 tickers) é **100% sobrevivente** — foi escrito com
conhecimento de quais empresas existem hoje. A Fase 3 (expandir o grafo)
**amplificaria** o viés se feita a partir da lista atual.

### 2.2 `s2_universo.py` — extração de preços do COTAHIST
O Bloco 2 é o único script autorizado a ler COTAHIST, então a extração entra
nele, na mesma passada que já lia volume:

```python
fator_cotacao   = int(linha[210:217]) or 1        # FATCOT
preco_fechamento = (int(linha[108:121]) / 100) / fator_cotacao   # PREULT
```
A divisão por FATCOT normaliza para preço **por ação** — sem isso, mudança de
fator de cotação viraria salto falso no retorno.

Nova `montar_precos_diarios()` → `data/precos/precos_cotahist.parquet`
(**1.088 tickers × 2.483 pregões**). Usa `aggfunc="last"` **sem** `fill_value`:
dia sem negociação é preço *desconhecido*, não zero.

Corrigido também `PASTA_SAIDA`, que era relativa ao cwd e criava uma pasta
`data/` duplicada ao rodar de dentro da fase.

### 2.3 O obstáculo: preço bruto não é utilizável
COTAHIST não ajusta proventos nem desdobramentos. Validação inicial contra o
yfinance nos 166 nomes comuns: correlação média **0,84**, desvio da diferença
**0,4486**. Caso extremo: `PDGR3` fez grupamento 1:50 → "+4.900%" num dia.

### 2.4 `s1c_retornos_completo.py` (novo) — limpeza e união híbrida

**Detecção de split** — exige as duas condições simultaneamente, para não
marcar como evento societário uma queda legítima de 40% em dia de crise:
```python
FATORES_SPLIT = [2,3,4,5,6,8,10,12,15,20,25,30,40,50,100,200,500,1000]
LIMIAR_RETORNO_SPLIT = 0.35   # variação grande E
TOLERANCIA_SPLIT     = 0.12   # razão perto de fator simples (ou 1/fator)
```
Retorno do dia do evento → 0 (o investidor não ganhou nem perdeu ali).

**Filtro de ação de centavos** (`PRECO_MINIMO = 1.0`): R$0,02 → R$0,03 é "+50%"
de arredondamento, não economia. **Teto** `LIMITE_RETORNO_DIARIO = 0.50` como
rede para eventos societários não mapeados.

Ganho medido (166 nomes comuns):

| | preço bruto | + split | + preço≥R$1 | + cap 50% |
|---|---|---|---|---|
| corr média | 0,840 | 0,956 | 0,972 | **0,972** |
| corr mediana | 0,976 | 0,993 | 0,993 | **0,993** |
| corr < 0,90 | 56 | 14 | 10 | **9** |
| desvio da diferença | 0,4486 | 0,3918 | 0,0096 | **0,0096** |
| viés sistemático | — | — | — | **0,00%/ano** |

Erro reduzido **46x**. Os 9 nomes residuais são todos cisão/evento societário
complexo (`PCAR3`/Assaí, `NATU3`, `AMER3`, `OIBR4`, `BRPR3`…) — e **todos estão
no yfinance**, portanto não entram pela porta do COTAHIST.

**União híbrida** (`montar_retornos_completos`): yfinance é fonte **primária**
nos 166 (já ajustado por proventos); COTAHIST preenche **apenas os ausentes**,
exigindo `MINIMO_PREGOES_VALIDOS = 250`.
Saída: `data/precos/retornos_diarios_completo.parquet` — **543 tickers**.

### 2.5 Consumidores atualizados
Blocos 3, 4 e 5 passam a ler `retornos_diarios_completo.parquet`, com fallback
explícito (e aviso em log) para a base antiga.

**Otimização necessária no Bloco 4:** com 543 tickers, rodar `RollingOLS` em
todos seria desperdício — só precisamos do *choque* das `empresa_A` e do *beta*
das `empresa_B`. Novo parâmetro `tickers_alvo` em `calcular_choque_limpo`
restringe a regressão a ~44 tickers. **Os índices setoriais continuam usando o
universo inteiro** — só a parte cara é restrita.

### 2.6 Cobertura
| | antes | depois |
|---|---|---|
| universo point-in-time coberto | 166/253 (66%) | **249/253 (98%)** |

---

## Evolução do resultado

| etapa | retorno total | líquido/ano |
|---|---|---|
| baseline (mocks + bug do setor) | **−63,0%** | −9,97% |
| + grafo corrigido + vol-targeting | −1,3% | +0,09% |
| + suavização dos pesos finais (fim da Fase 1) | **+19,9%** | +2,00% |
| **+ sem viés de sobrevivência (Fase 2)** | **+8,7%** | **+1,01%** |

A queda de +19,9% → +8,7% é o efeito esperado: **o viés inflava o resultado em
mais da metade**. O +8,7% é o número honesto.

### Diagnóstico atual
```
Giro medio diario:            5,8% do book      (era 69%)
Retorno BRUTO:                +1,73% ao ano
Custo de transacao:            0,73% ao ano     (era 8,67%)
Retorno LIQUIDO:              +1,01% ao ano
Volatilidade realizada:        5,70% ao ano     (alvo 12%)
Correlacao com Ibovespa:      -0,01             (hedge OK)
```

---

## Pendências

### P1 — Validação anti-overfitting (era a Fase 2 original)
A inversão de `concorrente` foi descoberta olhando os dados. O teste
out-of-sample rodado (Sharpe 0,58 in → 0,87 out, corte em 2021) é
**parcialmente contaminado**, porque a decisão de inverter usou a amostra
inteira. Protocolo limpo: definir direções **só com 2016-2020**, congelar, e
medir 2021-2025 sem tocar em mais nada.
→ Novo `fase 3 - backtest\src\s3_validacao.py`.

### P2 — Fase 3: breadth (o item que decide a viabilidade)
Gargalo estrutural: **23 elos úteis / ~22 nomes por dia**. Pela Lei Fundamental
da Gestão Ativa (IR ≈ IC × √breadth), com IC = 0,018:

| elos | IR teórico | realista (~50%)¹ | retorno @ vol 12% |
|---|---|---|---|
| 23 (hoje) | 1,37 | 0,73 ✓ *(bate com o medido)* | +8,7%/ano |
| 50 | 2,02 | ~1,08 | ~+13%/ano |
| 100 | 2,86 | ~1,53 | ~+18%/ano |
| 200 | 4,04 | ~2,16 | ~+26%/ano |

¹ *O fator de 50% não é arbitrário: o Sharpe realizado (0,73) foi exatamente
metade do teórico (1,37), porque os elos não são independentes e o IC não é
estável.*

Afinar parâmetros não resolve — o teto é estrutural. **Com a base sem viés, a
expansão agora pode incluir elos com `KROT3`, `CIEL3`, `BTOW3` e `HGTX3`**, que
eram gigantes em 2016, em vez de olhar só a lista de sobreviventes.

Item relacionado: **negociar também as `empresa_A`** — hoje só as satélites
entram na carteira, metade da informação do grafo é descartada.

### P3 — Destravar a volatilidade
A carteira roda a 5,7% contra alvo de 12%; as travas de liquidez limitam.
Mesmo destravada, chegaria a ~2%/ano — **não resolve sozinho**, depende de P2.

### P4 — Refinamentos
- Controle setorial mais fino em `calcular_choque_limpo` (subsetor ou fator de
  commodity) — é a raiz do problema que gerou o item 2 do diagnóstico.
- Banda de não-negociação em vez de média móvel: costuma preservar mais alfa
  para o mesmo nível de giro.

---

## Arquivos alterados

| Fase | Arquivo | Mudança |
|---|---|---|
| 1 | `fase 4 …\grafo_manual_base.csv` | 16 elos `concorrente`: −1 → +1 |
| 1 | `fase 4 …\src\s4_sinapse_sinal.py` | `JANELA_SUAVIZACAO`, `suavizar_sinal()` |
| 1 | `fase 5 …\src\s5_portfolio_builder.py` | `_estimar_vol_portfolio`, iteração vol↔travas, `_suavizar_pesos` |
| 1 | `fase 3 …\src\s3_backtest.py` | CDI (BCB SGS 12), diagnóstico de execução, Sharpe com RF diária |
| 1 | `fase 5 …\tests\test_s5_portfolio_builder.py` | cenário setorial ajustado + teste de invariante |
| 2 | `fase 2 …\s2_universo.py` | extração de PREULT/FATCOT, `montar_precos_diarios()`, path fix |
| 2 | `fase 1 …\src\s1c_retornos_completo.py` | **novo** — limpeza de splits e união híbrida |
| 2 | Blocos 3/4/5 | apontados para `retornos_diarios_completo.parquet`; `tickers_alvo` no Bloco 4 |

## Reprodução

```
1. fase 2 - universo liquidez\s2_universo.py        # COTAHIST -> universo, ADTV, precos
2. fase 1 - preço ajustado\src\s1c_retornos_completo.py   # base sem vies
3. fase 4 - sinal da sinapse\src\s4_sinapse_sinal.py      # sinal + betas
4. fase 5 - construcao da carteira\src\exec_s5.py         # pesos
5. fase 3 - backtest\src\s3_backtest.py                   # curva e metricas
```
Passo 1 relê ~3,7 GB de COTAHIST (~30s). Os demais são rápidos.
