import re
from typing import Dict, List

CODIGOS_OFICIAIS_VALIDOS = {
    "COAF-TIP-101",
    "COAF-TIP-102",
    "COAF-TIP-103",
    "COAF-TIP-104",
    "COAF-TIP-105",
    "REGRA-KYC-01",
    "REGRA-KYC-02",
    "NORM-BCB-3978",
    "NORM-BCB-4001",
    "MANUAL-MED-142",
    "GOV-ALCADA-01",
    "GOV-LGPD-02",
}

PADROES_BLOQUEADOS = [
    r"ignore\s+(todas\s+as\s+)?instru[cç][oõ]es",
    r"esque[cç]a\s+as\s+regras",
    r"drop\s+table",
    r"delete\s+from",
]


def mascarar_dados_sensiveis(texto: str) -> str:
    # CPF: 111.222.333-44 -> ***.222.333-**
    texto = re.sub(r"\b(\d{3})\.(\d{3}\.\d{3})-(\d{2})\b", r"***. \2-**".replace(" ", ""), texto)
    # CNPJ: 12.345.678/0001-90 -> **.345.678/0001-**
    texto = re.sub(r"\b(\d{2})\.(\d{3}\.\d{3}/\d{4})-(\d{2})\b", r"**. \2-**".replace(" ", ""), texto)
    return texto


def validar_entrada(pergunta: str) -> Dict:
    texto_lower = pergunta.lower()
    for padrao in PADROES_BLOQUEADOS:
        if re.search(padrao, texto_lower):
            return {
                "aprovado": False,
                "motivo": "Entrada bloqueada pelo Guardrail de Segurança (tentativa de violação de instrução ou comando destrutivo)."
            }
    return {"aprovado": True, "motivo": "OK"}


def auditar_resposta_ia(texto_resposta: str, trechos_rag_recuperados: List[str] = None) -> Dict:
    texto_mascarado = mascarar_dados_sensiveis(texto_resposta)

    codigos_citados = set(re.findall(r"\b(?:COAF-TIP|REGRA-KYC|NORM-BCB|MANUAL-MED|GOV-ALCADA|GOV-LGPD)-\d+\b", texto_mascarado))
    codigos_alucinados = [c for c in codigos_citados if c not in CODIGOS_OFICIAIS_VALIDOS]

    # Confere também se o código citado estava presente nos chunks retornados pelo Qdrant
    nao_presentes_no_rag = []
    if trechos_rag_recuperados:
        contexto_unificado = "\n".join(trechos_rag_recuperados)
        for c in codigos_citados:
            if c in CODIGOS_OFICIAIS_VALIDOS and c not in contexto_unificado:
                nao_presentes_no_rag.append(c)

    cpfs_expostos = re.findall(r"\b\d{3}\.\d{3}\.\d{3}-\d{2}\b", texto_resposta)

    aprovado = len(codigos_alucinados) == 0
    return {
        "aprovado": aprovado,
        "texto_seguro": texto_mascarado,
        "lgpd_mascarado": len(cpfs_expostos) > 0,
        "codigos_validados": sorted(list(codigos_citados - set(codigos_alucinados))),
        "codigos_alucinados": codigos_alucinados,
        "codigos_fora_do_contexto_rag": nao_presentes_no_rag,
    }
