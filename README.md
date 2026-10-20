# 🛡️ Sentinel AI — Plataforma de Investigação de Fraudes e PLD/AML

> **Plataforma Corporativa de Investigação de Fraudes Bancárias e Prevenção à Lavagem de Dinheiro (PLD/AML)** combinando **Banco Relacional (PostgreSQL via MCP)**, **Banco de Grafos (FalkorDB com Cypher)**, **RAG Híbrido (Qdrant Cloud + BM25)** e **Orquestração com Google Vertex AI**.

---

## 🏛️ Arquitetura da Solução

```text
                               ┌────────────────────────────────────────────────────────┐
                               │               Google Cloud Vertex AI                   │
                               │  • Gemini 2.5 Flash (Agente Orquestrador & Relatórios) │
                               │  • text-embedding-004 (Vetor Semântico)               │
                               └──────────────────────────┬─────────────────────────────┘
                                                          │
                                                [MCP / Tool Calling]
                                                          │
                   ┌──────────────────────────────────────┼──────────────────────────────────────┐
                   │                                      │                                      │
                   ▼                                      ▼                                      ▼
    ┌─────────────────────────────┐        ┌─────────────────────────────┐        ┌─────────────────────────────┐
    │     🗄️ PostgreSQL (Docker)   │        │     🕸️ FalkorDB (Docker)    │        │   🌐 Qdrant Cloud + BM25    │
    │  • Clientes e Contas        │        │  • Rede de Laranjas         │        │  • Circular BACEN 3.978/20  │
    │  • Histórico de PIX / TED   │        │  • Triangulação de Valores  │        │  • Carta Circular 4.001     │
    │  • Fila de Alertas de Risco │        │  • Dispositivos & IPs       │        │  • Tipologias COAF de Crime │
    └─────────────────────────────┘        └─────────────────────────────┘        └─────────────────────────────┘
                   │                                      │                                      │
                   └──────────────────────────────────────┼──────────────────────────────────────┘
                                                          ▼
                                           ┌─────────────────────────────┐
                                           │   🛡️ Camada de Guardrails   │
                                           │  • Mascaramento LGPD (CPF)  │
                                           │  • Verificação de Citação   │
                                           │  • Alçada Humana Obrigatória│
                                           └──────────────┬──────────────┘
                                                          ▼
                                           ┌─────────────────────────────┐
                                           │  💻 Painel Streamlit (UI)   │
                                           │  • Mesa de Investigação     │
                                           │  • Grafo Interativo PyVis   │
                                           │  • Raio-X da Engenharia     │
                                           └─────────────────────────────┘
```

---

## 🗺️ Roteiro de Construção (Etapas)

- [x] **Etapa 1:** Estrutura base, Docker Compose (Postgres + FalkorDB) e variáveis de ambiente.
- [ ] **Etapa 2:** Modelagem do Banco Relacional (PostgreSQL) com carga de dados sintéticos de fraudes PIX/TED.
- [ ] **Etapa 3:** Modelagem do Grafo (FalkorDB) e consultas Cypher para detecção de laranjas e triangulações.
- [ ] **Etapa 4:** Ingestão de normas BACEN/COAF no Qdrant Cloud com Busca Híbrida (Dense + Sparse/BM25).
- [ ] **Etapa 5:** Criação do Servidor de Ferramentas (MCP Tools) para o Agente.
- [ ] **Etapa 6:** Orquestrador Gemini (Vertex AI) + Camada de Guardrails (LGPD e Anti-alucinação).
- [ ] **Etapa 7:** Interface Visual Streamlit (Dashboard de Investigação de Fraudes).

---

## 🚀 Como Subir a Infraestrutura (Bancos Locais)

```bash
# 1. Iniciar PostgreSQL e FalkorDB via Docker
docker compose up -d

# 2. Verificar se os containers estão saudáveis
docker compose ps
```
