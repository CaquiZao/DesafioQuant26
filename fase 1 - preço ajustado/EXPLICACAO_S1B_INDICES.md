# Explicação: Script `s1b_indices.py` (A Régua de Medição)

Este documento foi criado para que todo o grupo (e a banca avaliadora, se necessário) entenda exatamente a finalidade do arquivo `src/s1b_indices.py` dentro do nosso repositório e o porquê de termos tomado o caminho mais inteligente em relação aos dados do Ibovespa.

---

## 1. Contexto: Qual o nosso objetivo?
Lembre-se da nossa tese principal: nós queremos capturar **Choques Limpos** (o que chamamos de *choque idiossincrático*). 

Se a ação da Petrobras (PETR4) cai 4% hoje, existem dois motivos possíveis:
1. **Motivo Sistêmico:** A bolsa inteira afundou no mundo todo, o Ibovespa caiu 3%, o setor de energia caiu 3.5%. A Petrobras só foi levada pela maré.
2. **Motivo Idiossincrático (O Choque Verdadeiro):** A bolsa subiu 1%, mas a Petrobras despencou 4% porque teve um acidente em uma plataforma. 

Nossa estratégia SINAPSE **só funciona com o Motivo 2**. Nós avisamos a empresa vizinha (fornecedora) apenas quando o problema é exclusivo da Petrobras. Se o mercado inteiro cair, o "sinal" não deve disparar.

Para a nossa regressão matemática separar o que é "maré" do que é "acidente", precisamos ter as cotações de quem mede a maré: **Os Índices**.

## 2. A Função do Código e o Bloco a que ele responde
O script `s1b_indices.py` é considerado o **Bloco 1.5** do nosso pipeline. 

Ele existe unicamente para **alimentar o Bloco 4.2** (o momento exato em que a matemática subtrai o Ibovespa da Ação).
Enquanto o `s1_precos.py` baixa os retornos dos "jogadores" em campo (ações individuais), o `s1b_indices.py` baixa a pontuação do "campeonato" inteiro (os índices de mercado e os índices setoriais da B3).

## 3. O que exatamente o script faz?
Ele usa o Yahoo Finance para extrair as séries históricas diárias (de 2016 até hoje) dos seguintes "termômetros" do mercado brasileiro:
*   **A Régua do Mercado Total:** O índice Ibovespa em si (`^BVSP`), que nos dá a pontuação diária.
*   **As Réguas Setoriais (ETFs):** Usamos ETFs reais negociados na B3 que acompanham os setores perfeitamente (ex: `FIND11` para Bancos/Financeiro, `MATB11` para Siderurgia/Mineração). 

Ele baixa esses números dia a dia, calcula a variação percentual diária (se o índice subiu 1% ou caiu 2%) e salva em um arquivo blindado e limpo chamado `indices_retornos.parquet`.

## 4. O Pulo do Gato: Por que NÃO precisamos da Composição Histórica do IBOV?
É muito comum em competições Quant os grupos se desesperarem tentando encontrar a planilha da B3 com **quais** as 80 ações que compunham o Ibovespa no ano de 2018. Não é possível baixar isso sem pagar ferramentas caríssimas, o que gera o famoso e letal erro de *Survivorship Bias* (viés de sobrevivência).

**A nossa grande sacada: Nós desmembramos o problema em duas metades.**

1.  **A Metade do "Universo de Ações":** Para saber quais ações podemos negociar (e não testar empresas que já faliram), nós **não** usamos a composição do Ibovespa. Nós usamos o nosso próprio proxy de liquidez no script `s2_universo.py`, lendo direto os dados brutos da B3 (COTAHIST). Ali resolvemos o risco de sobrevivência.
2.  **A Metade da "Regressão" (Choque Limpo):** Para a nossa fórmula do Bloco 4 isolar o choque, o modelo matemático não quer saber "quais ações estavam dentro do Ibovespa". O modelo só quer a seguinte variável: *"qual foi o retorno diário do mercado hoje?"*. 

A linha do gráfico do Ibovespa (`^BVSP`) é pública e gratuita em qualquer lugar. O script `s1b_indices.py` pega justamente isso: a linha histórica. 

Não precisamos saber se a *Kroton Educacional* estava dentro do índice em março de 2017 para saber que naquele exato dia a linha do Ibovespa subiu 0.5%.

## Resumo Didático
*   `s1_precos.py`: Responde "Quanto a Petrobras subiu hoje?"
*   `s1b_indices.py`: Responde "Quanto a Bolsa inteira subiu hoje?"
*   `Bloco 4`: Faz a conta "A Petrobras - A Bolsa = Choque Real da Empresa"

Com o `s1b_indices.py` salvo na nossa pasta de dados, toda a matemática estatística do Bloco 4 da SINAPSE tem o oxigênio necessário para funcionar.
