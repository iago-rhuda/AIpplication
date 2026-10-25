"""Curated target finder and report generator for speculative applications (cold outreach)."""

import json
from pathlib import Path
from src.config import settings
from src.utils.logger import log_audit_event, logger


CURATED_FRENCH_AI_TARGETS = [
    {
        "company_name": "Mistral AI",
        "website": "https://mistral.ai",
        "ai_domain": "Frontier LLM Foundations & Open Models",
        "tech_stack": "PyTorch, CUDA, Distributed Training, Transformers, C++",
        "key_contacts": json.dumps([
            {"name": "Arthur Mensch", "role": "CEO & Co-founder", "linkedin": "https://www.linkedin.com/in/arthur-mensch/"},
            {"name": "Guillaume Lample", "role": "Chief Scientist", "linkedin": "https://www.linkedin.com/in/guillaume-lample-b7470624/"}
        ]),
        "recommended_approach": "Candidature spontanée axée sur l'optimisation RAG et l'expérimentation de modèles compacts.",
    },
    {
        "company_name": "Dust",
        "website": "https://dust.tt",
        "ai_domain": "Enterprise AI Knowledge Assistants & Multi-Agent Workflows",
        "tech_stack": "TypeScript, Python, Rust, Vector Databases, Qdrant, OpenAI/Anthropic APIs",
        "key_contacts": json.dumps([
            {"name": "Gabriel Hubert", "role": "CEO", "linkedin": "https://www.linkedin.com/in/gabrielhubert/"},
            {"name": "Stanislas Polu", "role": "Co-founder & CTO", "linkedin": "https://www.linkedin.com/in/spolu/"}
        ]),
        "recommended_approach": "Mettre en avant l'expérience en graphes de connaissances, ontologies et systèmes RAG hybrides.",
    },
    {
        "company_name": "LightOn",
        "website": "https://www.lighton.ai",
        "ai_domain": "Generative AI Platforms & Enterprise LLMs",
        "tech_stack": "Python, PyTorch, vLLM, Triton, Docker, Linux",
        "key_contacts": json.dumps([
            {"name": "Laurent Daudet", "role": "Co-CEO", "linkedin": "https://www.linkedin.com/in/laurent-daudet-3b02b54/"}
        ]),
        "recommended_approach": "Envoi direct au lead de recherche en valorisant le double diplôme UTC/PUCPR et les publications.",
    },
    {
        "company_name": "Doctolib (Data & AI Lab)",
        "website": "https://about.doctolib.fr",
        "ai_domain": "Healthcare AI, Clinical NLP, Secure RAG & Predictive Systems",
        "tech_stack": "Python, PyTorch, Fastify, PostgreSQL, GCP, Kubernetes",
        "key_contacts": json.dumps([
            {"name": "Équipe Data & IA", "role": "Engineering Leads", "linkedin": "https://www.linkedin.com/company/doctolib/"}
        ]),
        "recommended_approach": "Candidature ciblée sur l'éthique des données de santé et l'extraction d'information clinique.",
    },
    {
        "company_name": "Allphins",
        "website": "https://www.allphins.com",
        "ai_domain": "Risk Modeling, Knowledge Graphs, Insurance Analytics",
        "tech_stack": "Python, Neo4j, Scikit-Learn, FastAPI, React",
        "key_contacts": json.dumps([
            {"name": "Laurent de la Porte", "role": "CEO", "linkedin": "https://www.linkedin.com/in/laurentdelaporte/"}
        ]),
        "recommended_approach": "Présentation des travaux de modélisation ontologique et automatisation de processus complexes.",
    },
    {
        "company_name": "Qantav",
        "website": "https://qantav.com",
        "ai_domain": "Quantitative Analytics & Industrial Automation",
        "tech_stack": "Python, PyTorch, Time-Series Forecasting, BPMN, Docker",
        "key_contacts": json.dumps([
            {"name": "Direction Technique", "role": "Tech Lead", "linkedin": "https://www.linkedin.com/company/qantav/"}
        ]),
        "recommended_approach": "Valorisation de la publication COBEM 2025 sur TabPFN et les signaux vibratoires.",
    }
]


def generate_cold_outreach_report() -> Path:
    """Generate a clean markdown dossier detailing speculative application targets."""
    report_path = settings.BASE_DIR / "output" / "relatorio_cold_application.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)

    lines = [
        "# Dossier Stratégique de Candidatures Spontanées (Cold Outreach)",
        "",
        "> **Cible :** Écosystème IA & Science des Données en France (Paris, Île-de-France)",
        f"> **Génération :** Registre de veille technologique",
        "",
        "---",
        "",
    ]

    for idx, target in enumerate(CURATED_FRENCH_AI_TARGETS, 1):
        contacts = json.loads(target["key_contacts"])
        contacts_formatted = ", ".join(f"[{c['name']} ({c['role']})]({c['linkedin']})" for c in contacts)

        lines.extend([
            f"### {idx}. {target['company_name']}",
            f"- **Site Web :** {target['website']}",
            f"- **Domaine IA :** {target['ai_domain']}",
            f"- **Stack Technique :** `{target['tech_stack']}`",
            f"- **Contacts Clés :** {contacts_formatted}",
            f"- **Approche Recommandée :** {target['recommended_approach']}",
            "",
        ])

    report_path.write_text("\n".join(lines), encoding="utf-8")
    logger.info(f"Generated cold outreach report at {report_path}")

    log_audit_event(
        event_type="COLD_REPORT_GENERATED",
        entity_type="REPORT",
        entity_id="COLD_OUTREACH",
        action="GENERATE_DOSSIER",
        details={"company_count": len(CURATED_FRENCH_AI_TARGETS), "path": str(report_path)},
    )
    return report_path
