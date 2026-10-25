"""Automated contextual LaTeX resume compiler guaranteeing a strict 1-page visual standard with photo."""

import json
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any
from pypdf import PdfReader

from src.config import settings
from src.utils.logger import log_audit_event, logger


class LatexCompilerError(Exception):
    """Custom exception raised when LaTeX compilation or bounding fails."""

    pass


def load_candidate_profile() -> dict[str, Any]:
    """Load the candidate profile from data/profile.json (fallback to profile.example.json)."""
    target_path = settings.PROFILE_DATA_PATH
    if not target_path.exists():
        logger.warning(
            f"Active profile at {target_path} not found. Falling back to example profile."
        )
        target_path = settings.PROFILE_EXAMPLE_PATH

    with open(target_path, encoding="utf-8") as f:
        return json.load(f)


def sanitize_latex_text(text: str) -> str:
    """Escape special LaTeX characters in dynamic text inputs."""
    replacements = {
        "\\": r"\textbackslash{}",
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_",
        "{": r"\{",
        "}": r"\}",
        "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
    }
    for char, escaped in replacements.items():
        text = text.replace(char, escaped)
    return text


def build_cv_context(
    job_data: dict[str, Any], profile: dict[str, Any]
) -> dict[str, str]:
    """Assemble dynamic context values tailored to the job requirements."""
    candidate = profile.get("candidate", {})
    identity = candidate.get("identity", {})
    links = identity.get("links", {})

    # Resolve profile picture path
    rel_pic = identity.get(
        "profile_picture_relpath", "CVs/foto_perfil_iago.jpg"
    )
    pic_path = settings.BASE_DIR / rel_pic
    if not pic_path.exists():
        # Fallback to local CVs directory if available
        cv_pic = settings.BASE_DIR / "CVs" / "foto_perfil_iago.jpg"
        pic_path = cv_pic if cv_pic.exists() else pic_path

    # In LaTeX on Windows, paths must use forward slashes
    pic_posix = pic_path.as_posix()

    # Dynamic accroche tailored to company and position
    raw_company = job_data.get("company_name", "votre entreprise")
    clean_company = sanitize_latex_text(raw_company)
    title = job_data.get("title", "Stagiaire Ingénieur en IA")
    accroche = (
        r"\textit{Étudiant en Génie Informatique} à l'UTC dans la filière d'\textbf{IA \& Science des Données} "
        r"avec un parcours international, je recherche un \textbf{stage de 6 mois à partir de février 2027}. "
        r"Particulièrement motivé par les projets de \textbf{"
        + clean_company
        + r"}, je conçois des \textbf{systèmes intelligents}, "
        r"du \textbf{RAG} aux \textbf{graphes de connaissances}, et j'\textbf{automatise} les flux pour allier recherche et performance concrète."
    )

    formation_block = (
        r"\textbf{Université de Technologie de Compiègne (UTC), France}" "\n"
        r"\hfill 2025 -- 2027" "\n"
        r"\vspace{-3pt}" "\n"
        r"\begin{itemize}" "\n"
        r"    \item Cursus d'\textbf{Ingénieur Informatique}, filière \textbf{IA \& Science des Données} (IAD) | Double Diplôme avec PUCPR." "\n"
        r"    \item Cours pertinents : \textbf{Indexation et Recherche d'Information; Techniques de Modélisation, Capitalisation et Gestion des Connaissances.}" "\n"
        r"\end{itemize}" "\n"
        r"\vspace{2pt}" "\n"
        r"\textbf{Pontifícia Universidade Católica do Paraná (PUCPR), Brésil}" "\n"
        r"\hfill 2022 -- 2025" "\n"
        r"\vspace{-3pt}" "\n"
        r"\begin{itemize}" "\n"
        r"    \item Cursus d'\textbf{Ingénieur Informatique} | Double Diplôme avec UTC." "\n"
        r"    \item \textit{Bases solides en algorithmique, structures de données et programmation (Python, C/C++)}." "\n"
        r"\end{itemize}"
    )

    experiences_block = (
        r"\textbf{Stagiaire Ingénieur en Automatisation}" "\n"
        r"chez Packform | \textit{CDI (Brésil)}" "\n"
        r"\hfill 06/2024 -- 07/2025" "\n"
        r"\vspace{-3pt}" "\n"
        r"\begin{itemize}" "\n"
        r"    \item Développement de scripts \textbf{Python} et d'intégrations \textbf{API} pour automatiser les workflows." "\n"
        r"    \item \textbf{+500\,h économisées par mois} grâce aux automatisations." "\n"
        r"    \item Modélisation des processus métier en \textbf{BPMN} pour traduire les besoins en spécifications techniques." "\n"
        r"    \item Gestion du code source avec \textbf{Git} (contrôle de version, travail collaboratif)." "\n"
        r"\end{itemize}" "\n"
        r"\vspace{2pt}" "\n"
        r"\textbf{Publication COBEM 2025} | 28\textsuperscript{e} Congrès International d'Ingénierie Mécanique (ABCM) | \textit{CDD Étudiant}" "\n"
        r"\hfill 2025" "\n"
        r"\vspace{-3pt}" "\n"
        r"\begin{itemize}" "\n"
        r"    \item Conception d'un système de \textbf{maintenance prédictive} via \textbf{TabPFN (Transformer)} sur signaux vibratoires." "\n"
        r"    \item \textbf{99,18\,\%} de précision en détection de dommages structurels, sans réglage d'hyperparamètres." "\n"
        r"\end{itemize}" "\n"
        r"\vspace{2pt}" "\n"
        r"\textbf{Assistant d'Enseignement} chez PUCPR | \textit{CDD Étudiant}" "\n"
        r"\hfill 06/2023 -- 06/2024" "\n"
        r"\vspace{-3pt}" "\n"
        r"\begin{itemize}" "\n"
        r"    \item Soutien technique et pédagogique à +200 étudiants en \textbf{Python} et C (+360\,h d'assistance directe)." "\n"
        r"\end{itemize}"
    )

    projects_block = (
        r"\textbf{Système de recommandation hybride de collaborateurs} | Projet encadré, UTC" "\n"
        r"\hfill 2026 -- courant" "\n"
        r"\vspace{-3pt}" "\n"
        r"\begin{itemize}" "\n"
        r"    \item Conception d'un système de recommandation reposant sur un \textbf{graphe de connaissances / ontologie}." "\n"
        r"    \item Pipeline \textbf{Python} intégrant un module \textbf{RAG} pour expliquer chaque recommandation." "\n"
        r"\end{itemize}" "\n"
        r"\vspace{2pt}" "\n"
        r"\textbf{Application RAG -- Indexation et Recherche d'Information} | Cours, UTC" "\n"
        r"\hfill 2026" "\n"
        r"\vspace{-3pt}" "\n"
        r"\begin{itemize}" "\n"
        r"    \item Implémentation complète d'un système \textbf{RAG} (indexation vectorielle, recherche, génération) en \textbf{Python}." "\n"
        r"\end{itemize}"
    )

    skills_block = (
        r"\textbf{IA \& Données :} \textit{PyTorch, Scikit-Learn, TabPFN, Pandas, NumPy, Graphe RAG, LangChain, ontologies.}" "\n\n"
        r"\textbf{Automatisation \& Systèmes :} \textbf{automatisation de workflows} (scripts Python \& \textbf{API REST}), \textit{BPMN}, Linux, Docker, Git." "\n\n"
        r"\textbf{Langages :} \textbf{Python (avancé)}, \textit{SQL, C/C++, Go, Lisp.}" "\n\n"
        r"\textbf{Langues :} Portugais (natif) \enspace\textbar\enspace \textbf{Anglais (C1, courant)} \enspace\textbar\enspace \textit{Français (C1, courant)}"
    )

    interests_block = (
        r"\textbf{Épicerie Innovante (EPI), UTC} (bénévole, 2026) : gestion et optimisation des stocks.\\" "\n"
        r"\textbf{1\textsuperscript{re} place}, championnat de calcul différentiel, PUCPR (2023).\\" "\n"
        r"\textit{Marchés financiers} \enspace\textbar\enspace Aérospatiale et exploration spatiale \enspace\textbar\enspace Course à pied."
    )

    raw_title = identity.get("professional_title", "Stagiaire Ingénieur en IA & Science de Données")
    clean_title = sanitize_latex_text(raw_title)

    raw_name = identity.get("full_name", "IAGO RHUDÁ RAMOS")
    clean_name = sanitize_latex_text(raw_name)

    return {
        "<<<CANDIDATE_NAME>>>": clean_name,
        "<<<CANDIDATE_TITLE>>>": clean_title,
        "<<<CANDIDATE_EMAIL>>>": identity.get("academic_email", "iago.rhuda-ramos@etu.utc.fr"),
        "<<<CANDIDATE_PHONE>>>": identity.get("phone", "07 82 96 77 21"),
        "<<<CANDIDATE_LOCATION>>>": identity.get("city", "Paris, France"),
        "<<<LINKEDIN_URL>>>": links.get("linkedin", "https://www.linkedin.com/in/iago-rhuda-ramos/"),
        "<<<LINKEDIN_DISPLAY>>>": "linkedin.com/in/iago-rhuda-ramos",
        "<<<PORTFOLIO_URL>>>": links.get("portfolio", "https://iagoramos.com"),
        "<<<PORTFOLIO_DISPLAY>>>": "iagoramos.com",
        "<<<GITHUB_URL>>>": links.get("github", "https://github.com/iago-rhuda"),
        "<<<GITHUB_DISPLAY>>>": "github.com/iago-rhuda",
        "<<<PROFILE_PICTURE_PATH>>>": pic_posix,
        "<<<ACCROCHE_TEXT>>>": accroche,
        "<<<FORMATION_BLOCK>>>": formation_block,
        "<<<EXPERIENCES_BLOCK>>>": experiences_block,
        "<<<PROJECTS_BLOCK>>>": projects_block,
        "<<<SKILLS_BLOCK>>>": skills_block,
        "<<<INTERESTS_BLOCK>>>": interests_block,
    }


def compile_latex_to_pdf(tex_content: str, output_pdf_path: Path) -> Path:
    """Compile LaTeX source in an isolated temporary directory and enforce a strict 1-page boundary."""
    template_path = settings.LATEX_TEMPLATE_PATH
    if not template_path.exists():
        raise LatexCompilerError(f"LaTeX template not found at {template_path}")

    with tempfile.TemporaryDirectory() as temp_dir_str:
        temp_dir = Path(temp_dir_str)
        tex_file = temp_dir / "document.tex"
        tex_file.write_text(tex_content, encoding="utf-8")

        # Copy graphic assets or photos if located relatively
        photo_src = settings.BASE_DIR / "CVs" / "foto_perfil_iago.jpg"
        if photo_src.exists():
            shutil.copy2(photo_src, temp_dir / "foto_perfil_iago.jpg")

        cmd = [
            settings.LATEX_CMD,
            "-interaction=nonstopmode",
            "-halt-on-error",
            "document.tex",
        ]

        # First compilation pass
        result = subprocess.run(
            cmd,
            cwd=temp_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        pdf_temp = temp_dir / "document.pdf"
        if result.returncode != 0 or not pdf_temp.exists():
            log_output = (temp_dir / "document.log").read_text(
                encoding="utf-8", errors="replace"
            ) if (temp_dir / "document.log").exists() else result.stdout
            logger.error(f"LaTeX compilation failed: {log_output[-1000:]}")
            raise LatexCompilerError(f"pdflatex compilation failed with code {result.returncode}")

        # Run second pass for hyperref and TikZ geometry consistency
        subprocess.run(cmd, cwd=temp_dir, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        # Validate strict 1-page constraint
        reader = PdfReader(str(pdf_temp))
        page_count = len(reader.pages)
        if page_count != 1:
            logger.warning(f"Resume generated {page_count} pages instead of 1! Enforcing single-page compression.")
            # Automatically apply compact spacing
            compact_content = tex_content.replace(
                r"\titlespacing*{\section}{0pt}{8pt}{4pt}",
                r"\titlespacing*{\section}{0pt}{5pt}{2pt}"
            ).replace(
                r"itemsep=1.5pt",
                r"itemsep=0.5pt"
            )
            tex_file.write_text(compact_content, encoding="utf-8")
            subprocess.run(cmd, cwd=temp_dir, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            reader = PdfReader(str(pdf_temp))
            page_count = len(reader.pages)

        if page_count > 1:
            logger.error(f"Failed to constrain PDF to 1 page (actual: {page_count} pages).")
            raise LatexCompilerError(f"Single page constraint violated: generated {page_count} pages.")

        output_pdf_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(pdf_temp, output_pdf_path)

    return output_pdf_path


def compile_custom_cv(job_data: dict[str, Any]) -> Path:
    """End-to-end contextual CV compiler for a given job posting."""
    profile = load_candidate_profile()
    context = build_cv_context(job_data, profile)

    template_text = settings.LATEX_TEMPLATE_PATH.read_text(encoding="utf-8")
    rendered_tex = template_text
    for placeholder, value in context.items():
        rendered_tex = rendered_tex.replace(placeholder, value)

    # Sanitize company name for folder naming
    safe_company = re.sub(r"[^\w\-]", "_", job_data.get("company_name", "Company"))
    dest_pdf = settings.APPLICATIONS_OUTPUT_DIR / safe_company / f"CV_{safe_company}.pdf"

    compile_latex_to_pdf(rendered_tex, dest_pdf)

    log_audit_event(
        event_type="CV_COMPILED",
        entity_type="APPLICATION",
        entity_id=job_data.get("id"),
        action="COMPILE_LATEX_CV",
        details={
            "company_name": job_data.get("company_name"),
            "pdf_path": str(dest_pdf),
            "page_count": 1,
        },
    )
    return dest_pdf
