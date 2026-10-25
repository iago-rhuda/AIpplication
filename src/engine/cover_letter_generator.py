"""Conditional French cover letter generator tailored to specific job mission requirements."""

import re
import shutil
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.config import settings
from src.engine.latex_compiler import LatexCompilerError, load_candidate_profile, sanitize_latex_text
from src.utils.logger import log_audit_event, logger


def generate_cover_letter_content(job_data: dict[str, Any], profile: dict[str, Any]) -> str:
    """Generate professional French cover letter LaTeX content."""
    candidate = profile.get("candidate", {})
    identity = candidate.get("identity", {})

    company_name = sanitize_latex_text(job_data.get("company_name", "l'Entreprise"))
    job_title = sanitize_latex_text(job_data.get("title", "Stagiaire Ingénieur en Intelligence Artificielle"))
    location = sanitize_latex_text(job_data.get("location", "Paris, France"))

    now = datetime.now(timezone.utc)
    french_months = [
        "janvier", "février", "mars", "avril", "mai", "juin",
        "juillet", "août", "septembre", "octobre", "novembre", "décembre"
    ]
    letter_date = f"{now.day} {french_months[now.month - 1]} {now.year}"

    template_path = settings.TEMPLATES_DIR / "cover_letter_template.tex"
    if not template_path.exists():
        raise FileNotFoundError(f"Cover letter template not found at {template_path}")

    template_text = template_path.read_text(encoding="utf-8")

    replacements = {
        "<<<CANDIDATE_NAME>>>": sanitize_latex_text(identity.get("full_name", "Iago Rhudá Ramos")),
        "<<<CANDIDATE_TITLE>>>": sanitize_latex_text(identity.get("professional_title", "Étudiant Ingénieur en Génie Informatique (IAD) - UTC")),
        "<<<CANDIDATE_EMAIL>>>": identity.get("academic_email", "iago.rhuda-ramos@etu.utc.fr"),
        "<<<CANDIDATE_PHONE>>>": identity.get("phone", "07 82 96 77 21"),
        "<<<CANDIDATE_LOCATION>>>": identity.get("city", "Paris / Compiègne, France"),
        "<<<COMPANY_NAME>>>": company_name,
        "<<<COMPANY_RECIPIENT>>>": r"À l'attention de l'équipe Recrutement \& Ingénierie",
        "<<<COMPANY_LOCATION>>>": location,
        "<<<LETTER_DATE>>>": letter_date,
        "<<<JOB_TITLE>>>": job_title,
        "<<<SALUTATION>>>": "Madame, Monsieur",
        "<<<PARAGRAPH_INTRO>>>": (
            f"Actuellement en dernière année de cursus d'ingénieur en Génie Informatique à "
            f"l'Université de Technologie de Compiègne (UTC), au sein de la filière Intelligence "
            f"Artificielle et Données (IAD), je vous adresse ma candidature pour le stage de fin d'études "
            f"en tant que \\textbf{{{job_title}}} au sein de \\textbf{{{company_name}}}, pour une durée de 6 mois "
            f"à compter de février 2027 (semestre de sortie P27)."
        ),
        "<<<PARAGRAPH_BACKGROUND>>>": (
            "Mon cursus binational d'ingénieur (UTC et PUCPR au Brésil) m'a permis d'acquérir une "
            "double expertise robuste : d'une part, la maîtrise rigoureuse des fondements algorithmiques "
            "et du développement logiciel en Python et C/C++, et d'autre part, la conception avancée "
            "de pipelines d'IA appliquée, de systèmes RAG et de graphes de connaissances."
        ),
        "<<<PARAGRAPH_PROJECTS_FIT>>>": (
            f"Au cours de mes expériences en entreprise et projets de recherche, j'ai notamment conçu "
            f"des modèles prédictifs innovants (publication COBEM 2025 via TabPFN) et automatisé des "
            f"workflows industriels permettant d'économiser plus de 500 heures par mois. "
            f"Cette capacité à transformer des concepts de recherche en solutions concrètes et performantes "
            f"est en parfaite adéquation avec les défis technologiques portés par \\textbf{{{company_name}}}."
        ),
        "<<<PARAGRAPH_MOTIVATION_COMPANY>>>": (
            f"Rejoindre \\textbf{{{company_name}}} représente pour moi l'opportunité de mettre mon autonomie, "
            f"ma rigueur analytique et mon goût prononcé pour l'expérimentation au service de vos projets "
            f"stratégiques, tout en évoluant aux côtés d'ingénieurs talentueux."
        ),
        "<<<PARAGRAPH_CLOSING>>>": (
            "Je me tiens à votre entière disposition pour un entretien afin de vous exposer plus en détail "
            "mes réalisations et ma motivation. En vous remerciant par avance pour l'attention portée à "
            "ma candidature, je vous prie d'agréer, Madame, Monsieur, l'expression de mes salutations distinguées."
        ),
    }

    rendered = template_text
    for placeholder, val in replacements.items():
        rendered = rendered.replace(placeholder, val)
    return rendered


def generate_cover_letter(job_data: dict[str, Any]) -> Path | None:
    """Conditionally generate and compile a formal French cover letter if required by the job."""
    if not job_data.get("requires_cover_letter", False):
        logger.info(f"Cover letter not required for {job_data.get('company_name')} - skipping.")
        return None

    profile = load_candidate_profile()
    tex_content = generate_cover_letter_content(job_data, profile)

    raw_company = job_data.get("company_name", "Company")
    safe_company = re.sub(r"[^\w\-]", "_", raw_company)
    dest_pdf = settings.APPLICATIONS_OUTPUT_DIR / safe_company / f"Lettre_Motivation_{safe_company}.pdf"

    with tempfile.TemporaryDirectory() as temp_dir_str:
        temp_dir = Path(temp_dir_str)
        tex_file = temp_dir / "cover_letter.tex"
        tex_file.write_text(tex_content, encoding="utf-8")

        cmd = [
            settings.LATEX_CMD,
            "-interaction=nonstopmode",
            "-halt-on-error",
            "cover_letter.tex",
        ]
        result = subprocess.run(cmd, cwd=temp_dir, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        pdf_temp = temp_dir / "cover_letter.pdf"
        if result.returncode != 0 or not pdf_temp.exists():
            log_output = (temp_dir / "cover_letter.log").read_text(
                encoding="utf-8", errors="replace"
            ) if (temp_dir / "cover_letter.log").exists() else result.stdout
            logger.error(f"Cover letter compilation failed: {log_output[-1000:]}")
            raise LatexCompilerError(f"Cover letter compilation failed with code {result.returncode}")

        dest_pdf.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(pdf_temp, dest_pdf)

    log_audit_event(
        event_type="COVER_LETTER_COMPILED",
        entity_type="APPLICATION",
        entity_id=job_data.get("id"),
        action="COMPILE_COVER_LETTER",
        details={
            "company_name": job_data.get("company_name"),
            "pdf_path": str(dest_pdf),
        },
    )
    return dest_pdf
