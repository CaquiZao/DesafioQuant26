# Diagnóstico da pendência P5 — retry no Yahoo Finance

**Data:** 04/08. **Status: fechada.** Não é um problema de retry, e o impacto
no resultado foi medido em **−0,005% ao ano** (desprezível).

## A premissa original

O relatório de 03/08 registrava: *"5 ações vivas caíram no COTAHIST (sem
ajuste de dividendo) por falha de download"*, e supunha que a causa fosse
*rate-limiting* — o Yahoo bloqueando temporariamente por excesso de
requisições, como já acontece e é tratado para outros tickers (ver o
comentário sobre `JBSS3` em `s1_precos.py`).

Os 5 tickers: **AXIA6, CPLE5, GUAR3, NEOE3, PETZ3**. Todos estavam no
universo de liquidez em 2025-12, e todos estão marcados em
`tickers_sem_preco.csv` — o que faz o pipeline **nunca tentar** baixá-los,
caindo direto no COTAHIST (sem ajuste de proventos).

## Achado 1 — não é rate-limiting

Testado com `yfinance==1.5.2`, isolado do pipeline:

- Os 5 falham com **HTTP 404 "Quote not found for symbol"** — não timeout,
  não erro genérico de rede.
- Falha **imediata e consistente**: mesmo resultado em janelas de data
  diferentes (2016–2025 e 2023–2024) e em dois endpoints distintos
  (`yf.download` e `Ticker().history()`).
- **Controle:** 8 de 8 tickers líquidos aleatórios (MGLU3, LREN3, RADL3,
  PRIO3, RENT3, VIVT3, SUZB3, B3SA3) funcionam normalmente no mesmo
  instante.

**Retry com qualquer backoff não resolveria** — 404 "quote not found" não é
o tipo de erro que retry conserta. A implementação sugerida na pendência
teria sido trabalho perdido.

## Achado 2 — a causa raiz continua desconhecida (e duas hipóteses foram refutadas)

**Hipótese A (refutada): unificação societária.** `CPLE3.SA` existe no
Yahoo com histórico completo, o que sugeria que `CPLE5` (preferencial)
tivesse deixado de existir na privatização da Copel em 2023. **O COTAHIST
refuta:** CPLE5 continua negociando até 2025-12-19. Os dois coexistem.

**Hipótese B (refutada): são ilíquidos demais para o Yahoo cobrir.** Medindo
o ADTV real de dezembro/2025, os 5 são líquidos:

| ticker | ADTV dez/2025 | pregões no COTAHIST |
|---|---|---|
| AXIA6 | R$ 124,6M | 34 (ticker novo, desde 2025-11) |
| CPLE5 | R$ 117,5M | 478 (negociação esporádica) |
| GUAR3 | R$ 20,0M | 2.482 (série completa) |
| NEOE3 | ~R$ 24M | 1.621 |
| PETZ3 | R$ 28,8M | 1.321 |

> ⚠️ **Armadilha de medição que caí e corrigi:** calcular a mediana do ADTV
> sobre a série inteira dá ~0 para tickers recentes, porque os anos
> anteriores à existência do papel entram como **zero**, não como NaN. Isso
> me levou a concluir (erradamente) que AXIA6 e CPLE5 "quase não negociam".
> Para julgar liquidez de ticker novo, use a janela em que ele existe.

Sem hipótese verificada, a causa fica em aberto. O que **está** estabelecido
é que não é retry, não é bloqueio, e não é liquidez.

## Achado 3 — o impacto real é desprezível, e foi medido

Dos 5 tickers, **apenas GUAR3 está no grafo** — os outros 4 não entram na
carteira em nenhum momento, então o preço deles não afeta resultado nenhum.

Para GUAR3, o efeito do dividendo não ajustado no alfa da carteira:

| dividend yield assumido | viés no alfa |
|---|---|
| 2% ao ano | −0,0015% ao ano |
| 4% ao ano | −0,0030% ao ano |
| 6% ao ano | −0,0046% ao ano |

Contra um alfa de +1,0% ao ano, isso é **meio por cento do alfa** no cenário
mais pessimista.

**Por que é tão pequeno:** a carteira fica *long* GUAR3 em 47,2% dos dias e
*short* em 52,8%. O peso médio **com sinal** é −0,076%, contra 0,59% em
módulo. Num book long-short equilibrado, um viés constante de retorno
(que é o que dividendo não ajustado produz) se cancela quase inteiramente
entre as duas pontas.

Isso é consistente com a medição independente feita em 03/08 para o
conjunto das ações do COTAHIST (viés sistemático de 0,00%/ano — pendência
P6).

## Decisão: fechar sem alterar o pipeline

Nenhuma mudança no código de preços. As razões:

1. **O retry proposto não funcionaria** (achado 1).
2. **O impacto é 0,5% do alfa no pior caso** (achado 3) — abaixo do ruído de
   qualquer decisão de modelagem já tomada.
3. Buscar fonte alternativa (Alpha Vantage, Investing.com) para 1 ticker
   relevante adicionaria uma dependência externa e um caminho de dados novo
   para corrigir um erro de quinta casa decimal.

O que **foi** feito: os motivos genéricos `sem_fonte_confiavel` em
`tickers_sem_preco.csv` foram substituídos por diagnósticos específicos,
para que ninguém reabra esta investigação do zero.

## Se alguém quiser retomar

O ponto de partida é descobrir por que o Yahoo retorna 404 para códigos de
ações ativas e líquidas. Testar a API do Yahoo diretamente (fora do
yfinance) separaria "o Yahoo não tem" de "o yfinance não consegue pedir".
Mas, dado o impacto medido, isso é otimização, não correção.
