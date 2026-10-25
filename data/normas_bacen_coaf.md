# COMPÊNDIO NORMATIVO DE PREVENÇÃO À LAVAGEM DE DINHEIRO (PLD/FTP) E COMBATE À FRAUDE BANCÁRIA

---

## DOCUMENTO 1: Circular BACEN nº 3.978/2020 — Política, Procedimentos e Controles Internos de PLD
**Órgão Emissor:** Banco Central do Brasil (BACEN)
**Código Interno de Compliance:** `NORM-BCB-3978`
**Base Legal Relacionada:** Lei nº 9.613/1998 (Lei de Lavagem de Dinheiro)

### Art. 13 ao Art. 18 — Qualificação e Conhecimento do Cliente (KYC - Know Your Customer)
As instituições financeiras devem implementar procedimentos destinados a conhecer seus clientes, incluindo a verificação e validação da **capacidade financeira (renda declarada para Pessoa Física ou faturamento para Pessoa Jurídica)**, ocupação profissional e data de constituição societária.
- **Regra de Incompatibilidade Financeira (`REGRA-KYC-01`):** Qualquer movimentação mensal acumulada que supere em **10 (dez) vezes ou mais a renda mensal declarada** do cliente Pessoa Física, sem comprovação prévia de origem lícita (como venda de imóvel ou herança), obriga a abertura imediata de dossiê de análise de suspeição.
- **Empresas Recém-Constituídas (`REGRA-KYC-02`):** Pessoas Jurídicas com menos de **90 (noventa) dias de abertura do CNPJ** que recebam aportes ou transferências de alto valor incompatíveis com seu capital social ou porte declarado devem ser classificadas sob risco crítico de **Empresa de Fachada (Shell Company)**.

### Art. 38 e Art. 39 — Monitoramento, Seleção e Análise de Operações Suspeitas
As instituições devem monitorar continuamente as transações de PIX, TED e boletos. As operações selecionadas pelos sistemas de monitoramento devem ser analisadas no prazo máximo de **45 (quarenta e cinco) dias**, devendo o parecer técnico fundamentar a decisão de comunicar ou não ao **COAF (Conselho de Controle de Atividades Financeiras)**.
- **Art. 49 — Prazo de Comunicação ao COAF:** Decidida a existência de indícios de lavagem de dinheiro ou fraude, a comunicação ao COAF (via sistema SISCOAF) deve ser realizada até o **dia útil seguinte** ao término da análise.

---

## DOCUMENTO 2: Carta Circular BACEN nº 4.001/2020 — Relação de Operações e Situações Suspeitas (Tipologias COAF)
**Órgão Emissor:** Banco Central do Brasil (BACEN) / COAF
**Código Interno de Compliance:** `NORM-BCB-4001`

### 1. Tipologia de Estruturação ou Fracionamento de Valores (Smurfing)
- **Código de Enquadramento COAF:** `COAF-TIP-101` (Art. 1º, Inciso III, Alínea "b" da Carta Circular 4.001/2020)
- **Descrição Conceitual:** Realização de múltiplas transações financeiras (depósitos, transferências PIX ou TED) em valores individuais intencionalmente fixados logo abaixo do limite regulamentar de monitoramento automático de **R$ 10.000,00 (dez mil reais)** — por exemplo, diversas remessas de R$ 9.500,00 a R$ 9.999,00 em curto intervalo de tempo.
- **Agravantes Operacionais:** Operações executadas em horários atípicos ou período noturno/madrugada (entre **00h00 e 06h00**) destinadas a um único recebedor ou grupo econômico demonstram tentativa deliberada de burlar os controles de PLD (*evasão de limiar regulatório*).
- **Ação Recomendada:** Bloqueio preventivo de limites noturnos, retenção cautelar e comunicação obrigatória ao COAF sob o código `COAF-TIP-101`.

### 2. Tipologia de Conta de Passagem ou "Conta Laranja" (Mule Account)
- **Código de Enquadramento COAF:** `COAF-TIP-102` (Art. 1º, Inciso IV, Alínea "c" da Carta Circular 4.001/2020)
- **Descrição Conceitual:** Contas correntes ou de pagamento (frequentemente abertas recentemente ou pertencentes a titulares de baixa renda, estudantes ou desempregados) que permanecem com saldo irrisório e, subitamente, recebem créditos expressivos seguidos de **esvaziamento quase integral (acima de 95% do valor recebido) em poucos minutos ou horas** para contas de terceiros.
- **Indicador Técnico de Tempo de Retenção:** Tempo de permanência do recurso na conta (*holding time*) inferior a **30 minutos** combinado com incompatibilidade de renda configura forte indício de utilização de interposta pessoa ("laranja") para ocultar o real beneficiário final dos recursos ilícitos.
- **Ação Recomendada:** Acionamento do Mecanismo Especial de Devolução (MED) ou bloqueio cautelar da conta nos termos da Resolução BCB nº 142/2021 e comunicação sob o código `COAF-TIP-102`.

### 3. Tipologia de Compartilhamento de Dispositivo Físico e Rede (Device Farming / Múltiplos Titulares)
- **Código de Enquadramento COAF:** `COAF-TIP-103` (Art. 1º, Inciso VI, Alínea "h" da Carta Circular 4.001/2020 e Manual de Cibersegurança Bancária)
- **Descrição Conceitual:** Identificação de múltiplas contas bancárias registradas em nome de diferentes titulares (CPFs distintos sem vínculo familiar comprovado) que são acessadas e operadas a partir do **mesmo identificador físico de hardware (`Device ID` / IMEI / Fingerprint)** e/ou do **mesmo endereço IP (especialmente IPs de VPN, proxies anônimos ou datacenters)**, ou em aparelhos com modificação de sistema operacional (*Root / Jailbreak*).
- **Significado na Investigação:** Evidencia que um único operador criminoso ("central de laranjas" ou *fraud ring*) detém o controle efetivo de diversas contas alugadas ou abertas com documentos falsos.
- **Ação Recomendada:** Bloqueio imediato de todas as contas vinculadas ao `Device ID` comprometido, revogação de chaves PIX e reporte sob o código `COAF-TIP-103`.

### 4. Tipologia de Triangulação Circular de Capital (Layering / Lavagem em Ciclo)
- **Código de Enquadramento COAF:** `COAF-TIP-104` (Art. 1º, Inciso VIII, Alínea "e" da Carta Circular 4.001/2020)
- **Descrição Conceitual:** Movimentação de recursos em circuito fechado (ex: `Conta A ➔ Conta B ➔ Conta C ➔ Conta A`) onde o capital sai de uma conta de origem, percorre duas ou mais contas intermediárias (frequentemente PJs de serviços digitais ou consultorias) e retorna parcial ou integralmente à conta de origem em curto espaço de tempo, muitas vezes com um pequeno deságio correspondente à comissão da lavagem.
- **Significado na Investigação:** Fase clássica de **Ocultação/Dissimulação (*Layering*)** da lavagem de dinheiro, utilizada para simular faturamento comercial ou prestação de serviços inexistentes a fim de dar aparência lícita a recursos de origem criminosa.
- **Ação Recomendada:** Congelamento do elo societário envolvido no ciclo, auditoria dos contratos de prestação de serviço das PJs participantes e comunicação ao COAF sob o código `COAF-TIP-104`.

### 5. Tipologia de Empresa de Fachada ou Fantasma (Shell Company / Conta Coletora)
- **Código de Enquadramento COAF:** `COAF-TIP-105` (Art. 1º, Inciso V, Alínea "a" da Carta Circular 4.001/2020)
- **Descrição Conceitual:** Pessoa Jurídica recém-constituída (frequentemente com menos de 30 dias de abertura do CNPJ), com objeto social genérico (como "consultoria empresarial" ou "intermediação de negócios"), capital social baixo e sem histórico operacional, que passa a atuar como **conta concentradora/coletora**, recebendo transferências de alto valor de múltiplas origens distintas em janela de 24 a 72 horas.
- **Ação Recomendada:** Diligência reforçada de PJ (*Enhanced Due Diligence*), exigência de notas fiscais e contratos que lastreiem os créditos recebidos, bloqueio cautelar e comunicação ao COAF sob o código `COAF-TIP-105`.

---

## DOCUMENTO 3: Resolução BCB nº 142/2021 e Manual Interno de Bloqueio Cautelar (MED)
**Órgão Emissor:** Banco Central do Brasil / Diretoria de Risco e Compliance Interno
**Código Interno de Compliance:** `MANUAL-MED-142`

### 1. Bloqueio Cautelar Preventivo (Art. 39-B da Resolução BCB nº 1/2020 alterado pela Resolução BCB nº 142/2021)
As instituições participantes do arranjo PIX devem realizar o **bloqueio cautelar** dos recursos creditados em conta transacional de usuário recebedor sempre que houver fundada suspeita de fraude. O bloqueio cautelar pode durar até **72 (setenta e duas) horas** para realização da análise de fraude.

### 2. Regras de Alçada e Governança Interna (Guardrails de Compliance e LGPD)
- **Política de Alçada Humana (`GOV-ALCADA-01`):** Nenhum sistema automatizado ou agente de Inteligência Artificial possui autorização para efetivar o **encerramento definitivo de conta** ou o **envio automático de comunicação ao SISCOAF** sem a validação e assinatura digital de um Analista de Compliance humano certificado. A IA deve emitir exclusivamente um **Parecer Técnico Recomendatório (Dossiê SAR)**.
- **Política de Privacidade e LGPD (`GOV-LGPD-02`):** Em conformidade com a Lei nº 13.709/2018 (LGPD), todos os relatórios e prompts processados por modelos de linguagem externos devem preservar o mascaramento de documentos pessoais (CPF/CNPJ) e manter rastreabilidade integral das fontes normativas citadas. É estritamente proibida a citação de artigos ou códigos regulatórios que não constem expressamente na base normativa oficial recuperada.
