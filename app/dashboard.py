import os
import sys
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
from pyvis.network import Network

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from graph.queries import (
    detectar_grupos_economicos,
    listar_documentos_com_grafo,
    obter_grafo_de_documento,
    obter_subgrafo_visualizacao,
    partes_contrarias_recorrentes,
)
from graph.extractor import extrair_e_gravar_grafo_de_documento
from rag.ingest import extrair_chunks_de_bytes, indexar_chunks_no_qdrant, status_colecao_qdrant
from agent.investigator import responder_consulta_juridica

st.set_page_config(
    page_title="Ecossistema de IA Jurídico",
    page_icon="⚖️",
    layout="wide",
)


def renderizar_grafo_juridico(subgrafo: dict, mostrar_processos: bool = True) -> str:
    net = Network(height="550px", width="100%", bgcolor="#0e1117", font_color="#f1f5f9", directed=True)
    net.barnes_hut(gravity=-3500, central_gravity=0.3, spring_length=150)

    nos = set()
    arestas = set()

    def add_no(node_id: str, label: str, title: str, color: str, shape: str = "dot", size: int = 22):
        if node_id not in nos:
            net.add_node(node_id, label=label, title=title, color=color, shape=shape, size=size)
            nos.add(node_id)

    def add_aresta(orig: str, dest: str, label: str, color: str, dashes: bool = False):
        chave = (orig, dest, label)
        if chave not in arestas:
            net.add_edge(orig, dest, label=label, color=color, dashes=dashes, width=2)
            arestas.add(chave)

    for row in subgrafo.get("socios", []):
        c1_id = f"CLI:{row['c1_nome']}"
        s_id = f"SOC:{row['s_nome']}"

        add_no(c1_id, row["c1_nome"], f"Cliente/Empresa: {row['c1_nome']} ({row.get('c1_seg', '')})", "#3b82f6", "dot", 26)
        add_no(s_id, row["s_nome"], f"Sócio / Holding: {row['s_nome']} ({row.get('s_doc', '')})", "#f59e0b", "diamond", 22)
        add_aresta(c1_id, s_id, f"{row['v1_tipo']} ({float(row['v1_part'] or 0):.0f}%)", "#f59e0b")

        if row.get("c2_nome"):
            c2_id = f"CLI:{row['c2_nome']}"
            add_no(c2_id, row["c2_nome"], f"Cliente Vinculado: {row['c2_nome']}", "#3b82f6", "dot", 26)
            add_aresta(c2_id, s_id, f"{row['v2_tipo']} ({float(row['v2_part'] or 0):.0f}%)", "#f59e0b")

    if mostrar_processos:
        for row in subgrafo.get("processos", []):
            c_id = f"CLI:{row['c_nome']}"
            p_id = f"PROC:{row['cnj']}"
            pc_id = f"PC:{row['parte_contraria']}"
            adv_id = f"ADV:{row['adv_nome']}"

            cor_proc = "#ef4444" if row["risco"] == "PROVAVEL" else "#a855f7"
            add_no(c_id, row["c_nome"], f"Cliente: {row['c_nome']}", "#3b82f6", "dot", 26)
            add_no(
                p_id,
                f"{row['area']}\n{row['cnj'][:15]}...",
                f"CNJ: {row['cnj']} | Valor: R$ {float(row['valor'] or 0):,.2f} | Risco: {row['risco']}",
                cor_proc,
                "box",
                18,
            )
            add_no(pc_id, row["parte_contraria"][:30], f"Parte Contrária: {row['parte_contraria']}", "#ec4899", "triangle", 18)
            add_no(adv_id, row["adv_nome"], f"Advogado: {row['adv_nome']} ({row.get('adv_esp', '')})", "#10b981", "star", 20)

            add_aresta(c_id, p_id, "PARTE_EM", "#94a3b8")
            add_aresta(p_id, pc_id, "CONTRA", "#ec4899", dashes=True)
            add_aresta(adv_id, p_id, "PATROCINA", "#10b981", dashes=True)

    return net.generate_html()


def renderizar_grafo_documentos(relacoes: list) -> str:
    net = Network(height="550px", width="100%", bgcolor="#0e1117", font_color="#f1f5f9", directed=True)
    net.barnes_hut(gravity=-3200, central_gravity=0.3, spring_length=160)

    cores_por_tipo = {
        "EMPRESA": ("#3b82f6", "dot", 25),
        "PESSOA": ("#f59e0b", "diamond", 22),
        "LEI_ARTIGO": ("#10b981", "box", 20),
        "CLAUSULA": ("#a855f7", "box", 20),
        "PROCESSO": ("#ef4444", "triangle", 22),
        "ORGAO": ("#06b6d4", "star", 22),
        "CONCEITO": ("#ec4899", "dot", 20),
    }

    nos = set()
    arestas = set()

    for r in relacoes:
        orig_id = f"{r['documento']}::{r['origem']}"
        dest_id = f"{r['documento']}::{r['destino']}"

        cor_o, shape_o, size_o = cores_por_tipo.get(r.get("tipo_origem", "CONCEITO"), ("#ec4899", "dot", 20))
        cor_d, shape_d, size_d = cores_por_tipo.get(r.get("tipo_destino", "CONCEITO"), ("#ec4899", "dot", 20))

        if orig_id not in nos:
            net.add_node(
                orig_id,
                label=r["origem"],
                title=f"[{r.get('tipo_origem', 'CONCEITO')}] {r['origem']} (Doc: {r['documento']})",
                color=cor_o,
                shape=shape_o,
                size=size_o,
            )
            nos.add(orig_id)

        if dest_id not in nos:
            net.add_node(
                dest_id,
                label=r["destino"],
                title=f"[{r.get('tipo_destino', 'CONCEITO')}] {r['destino']} (Doc: {r['documento']})",
                color=cor_d,
                shape=shape_d,
                size=size_d,
            )
            nos.add(dest_id)

        chave = (orig_id, dest_id, r["relacao"])
        if chave not in arestas:
            net.add_edge(orig_id, dest_id, label=r["relacao"], color="#94a3b8", width=2)
            arestas.add(chave)

    return net.generate_html()


# =========================================================
# BARRA LATERAL: INGESTÃO DE DOCUMENTOS (QDRANT + FALKORDB)
# =========================================================
with st.sidebar:
    st.header("📄 Documentos da IA")
    st.caption("Suba contratos, petições ou leis. A IA indexa no **Qdrant Cloud** (RAG Híbrido) e gera o **Grafo do Documento no FalkorDB**.")

    arquivos_upload = st.file_uploader(
        "Enviar PDF, MD ou TXT:",
        type=["pdf", "md", "txt"],
        accept_multiple_files=True,
    )

    if arquivos_upload and st.button("🚀 Processar Documento com IA", type="primary", use_container_width=True):
        with st.spinner("1/2 Vetorizando no Qdrant Cloud (Denso + BM25)..."):
            novos_chunks = []
            textos_por_arquivo = []
            for arq in arquivos_upload:
                raw_bytes = arq.getvalue()
                chunks_arq = extrair_chunks_de_bytes(arq.name, raw_bytes)
                novos_chunks.extend(chunks_arq)
                texto_unificado = "\n".join(c["texto"] for c in chunks_arq)
                textos_por_arquivo.append((arq.name, texto_unificado))
            qtd_chunks = indexar_chunks_no_qdrant(novos_chunks, recriar_colecao=False)

        with st.spinner("2/2 IA extraindo entidades e criando Grafo do Documento no FalkorDB..."):
            total_relacoes = 0
            for nome_arq, txt_doc in textos_por_arquivo:
                res_grafo = extrair_e_gravar_grafo_de_documento(nome_arq, txt_doc)
                total_relacoes += res_grafo["relacoes_criadas"]

        st.success(
            f"✅ **{qtd_chunks} trechos** salvos no Qdrant Cloud!\n\n"
            f"🕸️ **{total_relacoes} conexões de grafo** extraídas do documento pela IA no FalkorDB!"
        )
        st.rerun()

    st.divider()
    status_qd = status_colecao_qdrant()
    st.subheader(f"📚 Base Ativa ({status_qd['total_chunks']} trechos)")
    if status_qd.get("documentos"):
        for doc_nome in status_qd["documentos"]:
            st.markdown(f"- `{doc_nome}`")
    else:
        st.caption("Nenhum documento indexado.")

# =========================================================
# ÁREA PRINCIPAL: 2 ABAS (CHAT JURÍDICO E GRAFO VISUAL)
# =========================================================
st.title("⚖️ Ecossistema de IA Jurídico")
st.caption("Assistente Jurídico conectado ao **PostgreSQL (MCP)** + **Qdrant Cloud (RAG Híbrido)** + **FalkorDB (Grafos)**")

aba_chat, aba_grafo = st.tabs([
    "💬 Chat Jurídico (MCP + RAG + Grafos)",
    "🕸️ Mapa de Conexões (FalkorDB)",
])

with aba_chat:
    if "mensagens_chat" not in st.session_state:
        st.session_state["mensagens_chat"] = [
            {
                "role": "assistant",
                "content": (
                    "Olá! Sou o assistente jurídico do escritório. Posso consultar **processos, prazos e honorários no PostgreSQL**, "
                    "**grupos econômicos e vínculos societários no FalkorDB**, e **leis, contratos e PDFs que você subir no Qdrant Cloud**.\n\n"
                    "O que você gostaria de analisar?"
                ),
            }
        ]

    col_s1, col_s2, col_s3 = st.columns(3)
    pergunta_sugerida = None

    if col_s1.button("🔗 Grupo Econômico Horizonte Logística", use_container_width=True):
        pergunta_sugerida = (
            "Quais empresas fazem parte do grupo econômico da Horizonte Logística, quais processos elas enfrentam "
            "e qual o risco de responsabilidade solidária segundo a CLT e o Código Civil?"
        )
    if col_s2.button("🏗️ Processos e Risco da Construtora Vanguarda", use_container_width=True):
        pergunta_sugerida = (
            "Analise os processos da Construtora Vanguarda S.A. e de sua subsidiária Vanguarda SPE, "
            "os valores envolvidos e o que a Lei 4.591/64 diz sobre atraso de obra e retenção em distrato."
        )
    if col_s3.button("💰 Contratos de Honorários em Atraso", use_container_width=True):
        pergunta_sugerida = (
            "Quais clientes estão com contratos de honorários em atraso no banco e qual a multa prevista "
            "na nossa política interna de contratos?"
        )

    for msg in st.session_state["mensagens_chat"]:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if msg.get("auditoria"):
                aud = msg["auditoria"]
                st.caption(
                    f"🛡️ **Guardrails:** LGPD ativo (`CPF/CNPJ mascarado: {aud['lgpd_mascarado']}`) | "
                    f"Referências validadas no Qdrant: `{', '.join(aud['codigos_validados']) or 'OK'}`"
                )
            if msg.get("rastro"):
                with st.expander(f"🛠️ Ver ferramentas MCP acionadas pela IA ({len(msg['rastro'])})"):
                    st.json(msg["rastro"])

    entrada_usuario = st.chat_input("Pergunte sobre processos, clientes, vínculos societários ou sobre os PDFs enviados...")
    pergunta_final = pergunta_sugerida or entrada_usuario

    if pergunta_final:
        st.session_state["mensagens_chat"].append({"role": "user", "content": pergunta_final})
        with st.chat_message("user"):
            st.markdown(pergunta_final)

        with st.chat_message("assistant"):
            with st.spinner("Consultando PostgreSQL (MCP), FalkorDB e Qdrant Cloud..."):
                resultado = responder_consulta_juridica(pergunta_final)

            if "erro" in resultado:
                st.error(resultado["erro"])
            else:
                st.markdown(resultado["resposta_markdown"])
                aud = resultado["auditoria_guardrails"]
                st.caption(
                    f"🛡️ **Guardrails:** LGPD ativo (`CPF/CNPJ mascarado: {aud['lgpd_mascarado']}`) | "
                    f"Referências validadas no Qdrant: `{', '.join(aud['codigos_validados']) or 'OK'}`"
                )
                with st.expander(f"🛠️ Ver ferramentas MCP acionadas pela IA ({len(resultado['rastro_ferramentas'])})"):
                    st.json(resultado["rastro_ferramentas"])

                st.session_state["mensagens_chat"].append({
                    "role": "assistant",
                    "content": resultado["resposta_markdown"],
                    "auditoria": aud,
                    "rastro": resultado["rastro_ferramentas"],
                })

with aba_grafo:
    modo_grafo = st.radio(
        "Escolha a Fonte do Grafo no FalkorDB:",
        [
            "🏢 Rede Societária e Processos (Banco de Dados)",
            "📄 Grafo Extraído pela IA dos Documentos Enviados",
        ],
        horizontal=True,
    )

    if modo_grafo.startswith("🏢"):
        col_f1, col_f2 = st.columns([2.2, 1])
        termo_rede = col_f1.text_input(
            "🔎 O que você quer buscar no Grafo? (Empresa, Sócio, Holding, Tribunal, Área, Advogado ou deixe vazio para ver tudo):",
            placeholder="Ex: Horizonte, Eduardo, Atlas, TRT-2, TRABALHISTA, Sindicato...",
        )
        exibir_proc = col_f2.checkbox("Incluir Processos, Advogados e Partes Contrárias", value=True)

        subgrafo = obter_subgrafo_visualizacao(termo_rede)

        st.caption(
            "🔵 **Azul:** Clientes / Empresas | 🟡 **Losango Amarelo:** Sócios / Holdings Controladoras | "
            "🔴 **Caixa Vermelha:** Processo Risco Provável | 🟣 **Caixa Roxa:** Processo Risco Possível/Remoto | "
            "🟢 **Estrela Verde:** Advogado | 🩷 **Triângulo Rosa:** Parte Contrária"
        )
        html_grafo = renderizar_grafo_juridico(subgrafo, mostrar_processos=exibir_proc)
        components.html(html_grafo, height=560, scrolling=False)

        col_g1, col_g2 = st.columns(2)
        with col_g1:
            st.subheader("🔗 Grupos Econômicos (Sócios/Holdings em Comum)")
            grupos = detectar_grupos_economicos()
            if grupos:
                st.dataframe(pd.DataFrame(grupos), use_container_width=True, hide_index=True)
        with col_g2:
            st.subheader("⚔️ Partes Contrárias e Valor em Disputa")
            partes = partes_contrarias_recorrentes()
            if partes:
                st.dataframe(pd.DataFrame(partes), use_container_width=True, hide_index=True)

    else:
        docs_grafo = listar_documentos_com_grafo()
        if not docs_grafo:
            st.info(
                "Ainda não há grafos de documentos extraídos. Faça upload de um PDF/MD/TXT na barra lateral esquerda "
                "e clique em **'🚀 Processar Documento com IA'**, ou clique no botão abaixo para gerar o grafo do acervo inicial!"
            )
            if st.button("🧠 Gerar Grafo com IA do Acervo Jurídico Inicial (`acervo_juridico.md`)", type="primary"):
                caminho_acervo = os.path.join(os.path.dirname(__file__), "..", "data", "acervo_juridico.md")
                with open(caminho_acervo, "r", encoding="utf-8") as f:
                    texto_acervo = f.read()
                with st.spinner("IA lendo documento e construindo o Grafo de Conhecimento no FalkorDB..."):
                    res_ext = extrair_e_gravar_grafo_de_documento("acervo_juridico.md", texto_acervo)
                st.success(f"✅ {res_ext['relacoes_criadas']} conexões extraídas para o FalkorDB!")
                st.rerun()
        else:
            col_d1, col_d2 = st.columns([1, 1.5])
            opcoes_doc = ["Todos os Documentos Processados"] + docs_grafo
            doc_escolhido = col_d1.selectbox("Documento:", opcoes_doc)
            termo_doc = col_d2.text_input(
                "🔎 Filtrar conexão específica no documento (Artigo, Conceito, Parte, etc.):",
                placeholder="Ex: Art. 50, Grupo Econômico, Multa, CLT...",
            )
            relacoes_doc = obter_grafo_de_documento(doc_escolhido, termo_doc)

            st.caption(
                "🔵 **Azul:** Empresa | 🟡 **Losango Amarelo:** Pessoa/Sócio | 🟢 **Caixa Verde:** Lei / Artigo | "
                "🟣 **Caixa Roxa:** Cláusula | 🔴 **Triângulo Vermelho:** Processo | ⭐ **Estrela Ciano:** Órgão/Tribunal | 🩷 **Rosa:** Conceito Jurídico"
            )
            html_doc = renderizar_grafo_documentos(relacoes_doc)
            components.html(html_doc, height=560, scrolling=False)

            st.subheader(f"📋 Conexões Extraídas pela IA ({len(relacoes_doc)} relações)")
            st.dataframe(pd.DataFrame(relacoes_doc), use_container_width=True, hide_index=True)
