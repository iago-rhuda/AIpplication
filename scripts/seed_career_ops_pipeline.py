import asyncio
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from src.database.crud import create_job, get_all_jobs
from src.database.models import Application, Job, StatusEvent
from src.database.session import async_session_factory, init_db
from src.engine.career_ops_evaluator import evaluate_with_career_ops
from src.engine.career_ops_sync import (
    append_or_update_contact,
    append_status_log,
    sync_applications_markdown,
    sync_followups_markdown,
)
from src.utils.logger import logger


SAMPLE_JOBS = [
    {
        "company_name": "Mistral AI",
        "title": "Stage R&D — Modèles de Fondation & Alignement LLM",
        "location": "Paris, Île-de-France",
        "job_url": "https://jobs.lever.co/mistral/stage-rd-llm-2027",
        "source": "direct",
        "workplace_type": "hybrid",
        "start_date": "Février 2027",
        "duration_weeks": 26,
        "description": (
            "Au sein de notre équipe de recherche à Paris, vous participerez à l'entraînement, l'évaluation "
            "et l'alignement (RLHF/DPO) de modèles de fondation open-weights. Travail sur clusters GPU à grande échelle, "
            "optimisation de l'attention et distillation de connaissances."
        ),
        "raw_requirements": "PyTorch, Transformers, LLMs, Distributed Training, Python, Deep Learning, Git",
        "is_iad_compliant": True,
        "compliance_score": 0.98,
        "target_status": "applied",
        "applied_days_ago": 3,
        "history": [
            ("wishlist", "system", "Identifiée via portail carrières Mistral AI — Évaluation 4.9/5.0"),
            ("to_apply", "user", "CV 1-page compilé et adapté sur les architectures Transformer."),
            ("applied", "user", "Candidature déposée sur le portail Lever + message LinkedIn au Lead Aligner."),
        ],
    },
    {
        "company_name": "Doctolib",
        "title": "Stage Ingénieur IA — Assistant Médical & RAG",
        "location": "Paris / Levallois-Perret (Hybride)",
        "job_url": "https://careers.doctolib.fr/jobs/ai-intern-rag-2027",
        "source": "wttj",
        "workplace_type": "hybrid",
        "start_date": "1er Février 2027",
        "duration_weeks": 24,
        "description": (
            "Rejoignez l'équipe GenAI de Doctolib pour concevoir la prochaine génération d'outils d'assistance à la consultation médicale. "
            "Vous développerez des pipelines RAG hautement sécurisés intégrant re-rankers sémantiques, vérification de faits médicaux "
            "et observabilité temps réel sous FastAPI et PostgreSQL pgvector."
        ),
        "raw_requirements": "Python, RAG, LangChain, FastAPI, Vector Databases, PostgreSQL, Docker, NLP",
        "is_iad_compliant": True,
        "compliance_score": 0.96,
        "target_status": "interview",
        "applied_days_ago": 9,
        "history": [
            ("wishlist", "scraper", "Qualifiée automatiquement pour TN10 UTC P27."),
            ("to_apply", "user", "Validation dossier avec focus sur la rigueur de traçabilité médicale."),
            ("applied", "user", "Candidature soumise avec CV personnalisé et lettre de motivation en français."),
            ("interview", "user", "Entretien RH validé ! Entretien technique prévu avec le Staff AI Engineer."),
        ],
    },
    {
        "company_name": "Datadog",
        "title": "Stage Software Engineer — AI Observability & Monitoring",
        "location": "Paris, France",
        "job_url": "https://careers.datadoghq.com/detail/stage-ai-observability",
        "source": "linkedin",
        "workplace_type": "hybrid",
        "start_date": "Mars 2027",
        "duration_weeks": 26,
        "description": (
            "Développement de sondes d'observabilité et d'outils d'analyse des coûts et latences pour applications basées sur des LLMs. "
            "Conception d'APIs distribuées haute performance, traitement de flux télémétriques temps réel et dashboards analytiques."
        ),
        "raw_requirements": "Python, Go, Distributed Systems, OpenTelemetry, Observability, FastAPI, LLMOps",
        "is_iad_compliant": True,
        "compliance_score": 0.94,
        "target_status": "offer",
        "applied_days_ago": 18,
        "history": [
            ("wishlist", "scraper", "Détectée sur LinkedIn Jobs Paris."),
            ("to_apply", "user", "Mise en avant des compétences en métriques et traçabilité logicielle."),
            ("applied", "user", "Candidature envoyée."),
            ("interview", "user", "3 tours passés (RH, Coding Live, System Design & Fit)."),
            ("offer", "user", "Offre reçue ! Gratification 1 800€/mois + Navigo + Tickets Resto."),
        ],
    },
    {
        "company_name": "Hugging Face",
        "title": "Stage Machine Learning Engineer — Quantization & Edge Models",
        "location": "Paris, France (Hybride)",
        "job_url": "https://apply.workable.com/huggingface/j/stage-quantization-2027",
        "source": "direct",
        "workplace_type": "hybrid",
        "start_date": "Février 2027",
        "duration_weeks": 26,
        "description": (
            "Optimisation de modèles open-source pour l'inférence locale (quantization 4-bit/8-bit, AWQ, llama.cpp, ONNX). "
            "Contribution directe aux bibliothèques Transformers, Optimum et TGI."
        ),
        "raw_requirements": "Python, C++, PyTorch, Transformers, Quantization, CUDA, Open Source",
        "is_iad_compliant": True,
        "compliance_score": 0.95,
        "target_status": "to_apply",
        "applied_days_ago": 0,
        "history": [
            ("wishlist", "user", "Découverte via réseau alumni UTC."),
            ("to_apply", "user", "Dossier en cours de finalisation (mise en valeur des contributions open-source)."),
        ],
    },
    {
        "company_name": "BNP Paribas CIB",
        "title": "Stage Data Science & NLP — Analyse de Sentiments & Entités Financières",
        "location": "Paris (Grands Moulins)",
        "job_url": "https://group.bnpparibas/emploi-carriere/stage-data-science-nlp-2027",
        "source": "linkedin",
        "workplace_type": "on-site",
        "start_date": "1er Février 2027",
        "duration_weeks": 24,
        "description": (
            "Au sein du pôle Global Markets, conception de modèles de traitement automatique du langage naturel (NER, sentiment analysis) "
            "sur les flux d'actualités financières et rapports trimestriels pour alimenter les stratégies quantitatives."
        ),
        "raw_requirements": "Python, Scikit-Learn, PyTorch, FinBERT, SQL, Time Series, NLP",
        "is_iad_compliant": True,
        "compliance_score": 0.91,
        "target_status": "wishlist",
        "applied_days_ago": 0,
        "history": [
            ("wishlist", "scraper", "Qualifiée conforme TN10. En attente de révision personnalisée."),
        ],
    },
    {
        "company_name": "Thales",
        "title": "Stage Computer Vision — Détection d'Objets & Edge AI",
        "location": "Vélizy-Villacoublay, Île-de-France",
        "job_url": "https://thales.wd3.myworkdayjobs.com/Careers/stage-cv-edge-2027",
        "source": "wttj",
        "workplace_type": "on-site",
        "start_date": "Février 2027",
        "duration_weeks": 26,
        "description": (
            "Développement et embarquement d'algorithmes de vision par ordinateur (YOLO, segmentation sémantique) "
            "sur cartes de calcul embarquées (Nvidia Jetson). Optimisation TensorRT et robustesse face aux variations lumineuses."
        ),
        "raw_requirements": "Python, C++, PyTorch, Computer Vision, TensorRT, OpenCV, Linux",
        "is_iad_compliant": True,
        "compliance_score": 0.92,
        "target_status": "rejected",
        "applied_days_ago": 25,
        "history": [
            ("wishlist", "scraper", "Ingérée depuis WTTJ."),
            ("to_apply", "user", "CV technique généré."),
            ("applied", "user", "Candidature déposée sur le portail Workday."),
            ("rejected", "user", "Poste gelé en interne pour restructuration budgétaire. Contact conservé pour opportunités futures."),
        ],
    },
]


async def seed():
    logger.info("Initializing database and seeding Career-Ops pipeline...")
    await init_db()

    now_utc = datetime.now(timezone.utc)
    all_serialized = []

    async with async_session_factory() as db:
        for idx, job_info in enumerate(SAMPLE_JOBS, start=1):
            history = job_info.pop("history")
            target_status = job_info.pop("target_status")
            days_ago = job_info.pop("applied_days_ago")

            # Check if job already exists
            created_job = await create_job(db, job_info)

            # Run Career-Ops A-H evaluation
            eval_res = evaluate_with_career_ops(job_info, report_num=idx)

            # Record contact in contacts.tsv
            append_or_update_contact(
                name=eval_res["key_contact_name"],
                company=created_job.company_name,
                contact_type="recruiter",
                title=eval_res["key_contact_role"],
                tracker_num=idx,
                notes=f"Contact pour {created_job.title}",
            )

            # Create application in initial state
            first_state = history[0][0]
            created_dt = now_utc - timedelta(days=max(days_ago + 2, 2))
            applied_dt = (now_utc - timedelta(days=days_ago)) if target_status in ("applied", "interview", "offer", "rejected") else None

            app = Application(
                job_id=created_job.id,
                status=target_status,
                application_mode="semi_auto",
                requires_cover_letter=True,
                applied_at=applied_dt,
                notes=history[-1][2] if history else None,
                created_at=created_dt,
                evaluation_score=eval_res["evaluation_score"],
                match_grade=eval_res["match_grade"],
                salary_range=eval_res["salary_range"],
                star_stories=json.dumps(eval_res["star_stories"], ensure_ascii=False),
                form_answers=json.dumps(eval_res["form_answers"], ensure_ascii=False),
                key_contact_name=eval_res["key_contact_name"],
                key_contact_role=eval_res["key_contact_role"],
                outreach_message=eval_res["outreach_message"],
                evaluation_report_path=eval_res["report_rel_path"],
                followup_due_at=(applied_dt + timedelta(days=7)) if applied_dt else None,
            )
            db.add(app)
            await db.commit()
            await db.refresh(app)

            # Generate status transition events history
            prev_status = None
            for step_idx, (st, source, note) in enumerate(history):
                step_time = created_dt + timedelta(days=step_idx * 2)
                ev = StatusEvent(
                    application_id=app.id,
                    from_status=prev_status,
                    to_status=st,
                    source=source,
                    notes=note,
                    created_at=step_time,
                )
                db.add(ev)
                append_status_log(
                    tracker_num=app.id,
                    from_status=prev_status,
                    to_status=st,
                    source=source,
                    note=note,
                    event_time=step_time,
                )
                prev_status = st

            await db.commit()
            logger.info(f"Seeded application #{app.id}: {created_job.company_name} — {target_status.upper()} (Score: {eval_res['evaluation_score']})")

            all_serialized.append({
                "id": app.id,
                "status": target_status,
                "evaluation_score": eval_res["evaluation_score"],
                "created_at": created_dt.isoformat(),
                "applied_at": applied_dt.isoformat() if applied_dt else None,
                "notes": app.notes,
                "cv_web_url": None,
                "report_web_url": f"/reports/{Path(eval_res['report_rel_path']).name}",
                "key_contact_name": eval_res["key_contact_name"],
                "job": {
                    "company_name": created_job.company_name,
                    "title": created_job.title,
                    "job_url": created_job.job_url,
                },
            })

    # Synchronize Career-Ops canonical files
    sync_applications_markdown(all_serialized)
    sync_followups_markdown(all_serialized)
    logger.info("Pipeline seeded successfully with 6 realistic applications and full Career-Ops traceability!")


if __name__ == "__main__":
    asyncio.run(seed())
