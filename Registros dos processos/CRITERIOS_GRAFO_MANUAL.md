# Critérios para o Grafo Manual (Bloco 4)

Para garantir que nosso teste da SINAPSE seja estatisticamente válido, não podemos preencher os elos com base em "achismos". Cada linha do `grafo_manual_base.csv` obedece aos critérios fixos e lógicos descritos abaixo, validados com fatos do mercado brasileiro.

## A Premissa da Assimetria
Sempre lemos o elo da **Empresa A (Âncora/Gigante)** para a **Empresa B (Satélite/Afetada)**. O choque limpo que nos importa é o que acontece na Empresa A. O robô vai operar a Empresa B.

## 1. Tipo de Elo (`tipo_de_elo`)
Representa a natureza econômica do encanamento que liga as duas empresas.

*   `fornecedor`: B vende produtos/serviços vitais para A. Se A entra em crise, B perde faturamento instantaneamente.
*   `cliente`: B compra insumos essenciais de A. Se A interrompe a produção, B sofre choque de oferta.
*   `imobiliario_logistica`: B aluga infraestrutura para A (Shoppings, Galpões). Se A vai mal, B sofre vacância e quebra de contrato.
*   `concorrente`: B disputa o mesmo mercado/clientes que A. Concorrência pura de soma-zero.
*   `holding_subsidiaria`: B é holding de A (ou vice-versa). O choque se transmite por equivalência patrimonial ou risco sistêmico do grupo.
*   `substituto`: B vende um produto que substitui o de A em caso de crise (Ex: Frango vs Carne Bovina). Não é concorrência direta na mesma gôndola, mas substituição de consumo.
*   `credor_devedor`: B está altamente alavancada ou tem dívidas vitais providas por A.

## 2. Direção do Choque (`direcao`)
Representa o vetor matemático do choque. 

*   `1` **(Correlação Positiva):** Destinos alinhados. Se A sangra, B sangra junto. (Aplicável a: `fornecedor`, `cliente`, `imobiliario_logistica`, `holding_subsidiaria`, `credor_devedor`).
*   `-1` **(Correlação Negativa / Soma-Zero):** A desgraça de um é a sorte do outro. O capital e os clientes migram de A para B. (Aplicável a: `concorrente`, `substituto`).

## 3. Força do Elo (`forca`)
Multiplicador (0.0 a 1.0) que amortece ou amplifica o sinal. Para o grafo manual, usamos elos muito óbvios (Força alta).
*   `0.8 a 1.0` **(Dependência Severa):** Sobrevivência/Balanço atrelados.
*   `0.5 a 0.7` **(Dependência Média / Concorrência Forte):** Divisão direta de espaço com impacto relevante, mas B não morre se A falir.
*   `0.2 a 0.4` **(Impacto Leve):** Concorrência pulverizada ou elo muito fraco.

---

## 4. Base Verificável dos 30 Elos Iniciais

O arquivo base do grafo `grafo_manual_base.csv` possui 30 ligações reais da B3, estruturadas a partir de relatórios da CVM e fatos do mercado, conforme justificativas abaixo:

### Cadeia Vale (Mineração)
1.  **VALE3 $\rightarrow$ USIM5** (`cliente`, 0.7, 1): Usiminas depende do minério da Vale para altos-fornos.
2.  **VALE3 $\rightarrow$ CSNA3** (`concorrente`, 0.6, -1): CSN Mineração se beneficia do prêmio do minério se a Vale paralisa.
3.  **VALE3 $\rightarrow$ BRAP4** (`holding_subsidiaria`, 0.9, 1): Bradespar tem a Vale como seu ativo principal (dependência letal).

### Cadeia Petrobras (Petróleo e Combustíveis)
4.  **PETR4 $\rightarrow$ VBBR3** (`cliente`, 0.8, 1): Vibra (ex-BR Distribuidora) compra derivados da Petrobras.
5.  **PETR4 $\rightarrow$ UGPA3** (`cliente`, 0.7, 1): Ipiranga compra derivados da Petrobras.
6.  **PETR4 $\rightarrow$ PRIO3** (`concorrente`, 0.6, -1): Petroleiras independentes ganham fluxo se a estatal sofrer intervenção.
7.  **PETR4 $\rightarrow$ BRAV3** (`concorrente`, 0.5, -1): Brava Energia. Mesma lógica da PRIO.

### Cadeia Bens de Capital
8.  **WEGE3 $\rightarrow$ AERI3** (`fornecedor`, 0.9, 1): Aeris fabrica pás eólicas. WEG é cliente gigante. Aeris sofre se WEG para.
9.  **WEGE3 $\rightarrow$ ROMI3** (`cliente`, 0.5, 1): Romi utiliza motores WEG em suas máquinas industriais.

### Cadeia Varejo de Moda e Shoppings
10. **LREN3 $\rightarrow$ MULT3** (`imobiliario_logistica`, 0.6, 1): Lojas Renner é âncora histórica da Multiplan.
11. **LREN3 $\rightarrow$ IGTI11** (`imobiliario_logistica`, 0.6, 1): Iguatemi. Mesma lógica de vacância.
12. **LREN3 $\rightarrow$ ALOS3** (`imobiliario_logistica`, 0.6, 1): Allos (ex-Aliansce). Mesma lógica.
13. **LREN3 $\rightarrow$ CEAB3** (`concorrente`, 0.7, -1): C&A captura market share da Renner no vestuário.
14. **LREN3 $\rightarrow$ GUAR3** (`concorrente`, 0.7, -1): Riachuelo (Guararapes). Soma-zero.

### Cadeia E-commerce e Galpões
15. **MGLU3 $\rightarrow$ BHIA3** (`concorrente`, 0.8, -1): Grupo Casas Bahia (ex-Via). Soma-zero clássico de linha branca/e-commerce.
16. **MGLU3 $\rightarrow$ LOGG3** (`imobiliario_logistica`, 0.6, 1): LOG CP loca infraestrutura logística para e-commerce.

### Cadeia Celulose e Gestão de Resíduos
17. **SUZB3 $\rightarrow$ KLBN11** (`concorrente`, 0.7, -1): Suzano e Klabin competem globalmente pelo prêmio da celulose.
18. **SUZB3 $\rightarrow$ AMBP3** (`fornecedor`, 0.5, 1): Ambipar provê resposta a emergências e resíduos ambientais.

### Cadeia Proteínas
19. **JBSS3 $\rightarrow$ MRFG3** (`concorrente`, 0.7, -1): Marfrig. Concorrente global em abate bovino.
20. **JBSS3 $\rightarrow$ BEEF3** (`concorrente`, 0.6, -1): Minerva. Concorrente bovino regional.
21. **JBSS3 $\rightarrow$ BRFS3** (`substituto`, 0.7, -1): BRF (Sadia/Perdigão) atua em aves/suínos. Um choque restritivo em bovinos migra o consumo nacional para o frango.

### Cadeia Financeira e Mercado de Capitais
22. **ITUB4 $\rightarrow$ BBDC4** (`concorrente`, 0.8, -1): Itaú vs Bradesco. Disputa severa por spread e crédito.
23. **ITUB4 $\rightarrow$ ITSA4** (`holding_subsidiaria`, 0.9, 1): Itaúsa (Holding) espelha os dividendos e riscos do Itaú.
24. **B3SA3 $\rightarrow$ BPAC11** (`cliente`, 0.5, 1): BTG usa a tesouraria e plataforma monopolista da B3 intensamente.

### Domésticas, Saúde e Construção
25. **RENT3 $\rightarrow$ MOVI3** (`concorrente`, 0.8, -1): Localiza vs Movida (Aluguel de frotas/seminovos).
26. **RADL3 $\rightarrow$ PGMN3** (`concorrente`, 0.7, -1): Raia Drogasil e Pague Menos (Varejo farmacêutico).
27. **CYRE3 $\rightarrow$ EZTC3** (`concorrente`, 0.6, -1): Concorrência em incorporação de média/alta renda (foco SP).

### Utilities e Telecom
28. **ELET3 $\rightarrow$ EGIE3** (`concorrente`, 0.6, -1): Eletrobras e Engie disputam o setor de geração e mercado livre de energia.
29. **VIVT3 $\rightarrow$ TIMS3** (`concorrente`, 0.8, -1): Vivo e TIM.
30. **VIVT3 $\rightarrow$ FIQE3** (`concorrente`, 0.4, -1): Unifique atua como provedora regional que pode capturar clientes da Vivo.

---

## 5. Nuances e Pontos de Atenção (Gatekeeper do ECO)

Embora os elos listados acima sejam reais e defendíveis, a classificação de direção (`direcao`) e força (`forca`) podem se comportar de maneira não linear, exigindo que o algoritmo (especialmente o módulo de notícias/eventos - ECO) filtre os alarmes falsos.

*   **A dualidade JBSS3 $\rightarrow$ BRFS3:** A relação de substituição na gôndola (carne bovina vs. frango/suíno) faz sentido macroeconômico (vetor `-1`). Porém, a JBS é dona da Seara, que é a maior concorrente direta da BRF. Logo, um choque de custo nos grãos (milho e soja) ou proibições sanitárias de exportação atingem ambas de forma correlacionada (vetor `1`). O robô precisa saber qual é o tipo de choque que a JBS sofreu antes de acionar a BRF.
*   **Celulose não é soma-zero perfeita:** SUZB3 e KLBN11 competem, mas a Suzano é focada em celulose de fibra curta (commodity dura), enquanto a Klabin tem forte integração vertical em papéis para embalagens (kraftliner e papelão). Um choque na Suzano nem sempre significa que os clientes e os prêmios migram para a Klabin de forma simétrica.
*   **Petrobras e as "Juniores" (PRIO3, BRAV3):** A direção de soma-zero (`-1`) está correta estritamente do ponto de vista de fluxo de capital institucional — se o governo intervir na estatal, os fundos vendem PETR4 e compram as privadas. No entanto, no lado operacional, o vetor vira `1`, pois todas dependem da mesma variável primária: o preço do barril de Brent.

---

## 6. Metodologia de Auditoria e Validação

Para blindar matematicamente as premissas deste grafo contra questionamentos (evitando "achismos"), as seguintes fontes de dados e métodos quantitativos podem ser acionados para atestar as relações:

1.  **Formulário de Referência (CVM):** Na seção "Fatores de Risco" e "Principais Clientes/Fornecedores", empresas listadas são obrigadas a reportar dependências extremas. Isso atesta legalmente elos de fornecimento como WEG/Aeris e Vale/Usiminas.
2.  **Matriz de Covariância (Filtrando o Beta):** Para validar a força dos elos de soma-zero (concorrentes), extrai-se o histórico de retornos diários dos últimos 5 anos e isola-se o beta (para remover o ruído de mercado geral do Ibovespa). Isso comprovará se o fluxo de capital realmente migra da Empresa A para a Empresa B durante eventos de estresse.
3.  **Rubrica de Equivalência Patrimonial:** Para validar os elos de `holding_subsidiaria`, os balanços patrimoniais trimestrais (ITRs) mostram exatamente a porcentagem do lucro de BRAP4 ou ITSA4 que advém puramente de VALE3 e ITUB4.
