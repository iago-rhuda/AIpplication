# Stage AI Application Ecosystem (TN10 - UTC)

Local, autonomous, and traceable platform for internship prospecting, regulatory qualification, contextual LaTeX resume/cover letter customization, and application tracking for master's engineering graduation internships (TN10 - AI & Data Science / Université de Technologie de Compiègne).

---

## 1. Architecture & Technology Stack

The entire architecture is strictly standardized on the following stack:

- **Backend Runtime & Framework:** Python 3.12+ with FastAPI and Uvicorn (asynchronous REST API + WebSockets for real-time log and task streaming).
- **Local Persistence & ORM:** SQLite 3 via SQLAlchemy (AsyncIO with `aiosqlite`) and Alembic for schema migrations.
- **Scraping & Browser Automation:** Playwright for Python (Chromium headless/headful with stealth plugin support for LinkedIn Jobs and Welcome to the Jungle).
- **Document Compilation Engine:** TeX Live / MiKTeX invoking `latexmk` / `pdflatex` with strict single-page bounding and automated layout checking.
- **Frontend Architecture:** Vanilla JavaScript (ES2022+), Semantic HTML5, and Vanilla CSS with custom design tokens (dark mode, glassmorphism, responsive flex/grid) with zero Node.js/Tailwind build overhead.
- **Graph Knowledge Base:** Graphify integration (`graphifyy`) for mapping skills, requirements, companies, and experience clusters.
- **Logging & Audit Trail:** `loguru` with structured JSON serialization, automatic daily rotation, and a designated audit stream.

---

## 2. Directory Structure

```
.
├── .env.example
├── .gitignore
├── README.md
├── requirements.txt
├── data/
│   ├── profile.example.json
│   └── .gitkeep
├── logs/
│   └── .gitkeep
├── output/
│   └── .gitkeep
├── src/
│   ├── __init__.py
│   ├── main.py
│   ├── config.py
│   ├── api/
│   │   ├── __init__.py
│   │   ├── routes_jobs.py
│   │   ├── routes_applications.py
│   │   ├── routes_doubts.py
│   │   └── websocket_logs.py
│   ├── database/
│   │   ├── __init__.py
│   │   ├── session.py
│   │   ├── models.py
│   │   └── crud.py
│   ├── engine/
│   │   ├── __init__.py
│   │   ├── scraper.py
│   │   ├── filter_compliance.py
│   │   ├── latex_compiler.py
│   │   ├── cover_letter_generator.py
│   │   └── cold_outreach.py
│   └── utils/
│       ├── __init__.py
│       └── logger.py
├── storage/
│   ├── schema.sql
│   └── .gitkeep
├── templates/
│   ├── cv_template.tex
│   ├── cover_letter_template.tex
│   └── .gitkeep
└── web/
    ├── index.html
    ├── css/
    │   └── styles.css
    ├── js/
    │   ├── api.js
    │   ├── kanban.js
    │   ├── doubts.js
    │   └── main.js
    └── assets/
        └── .gitkeep
```

---

## 3. Privacy & Repository Rules

- Zero Personal Data Policy: All personal data, phone numbers, contact addresses, profile photos, and generated application PDFs reside exclusively in local, git-ignored directories (`.projeto/`, `CVs/`, `data/profile.json`, `output/`).
- Language Invariant: All code, documentation, scripts, variable names, commit messages, and README files in the public repository must be in English. Files inside `.projeto/` are strictly written in Portuguese.

---

## 4. Local Setup & Quickstart

1. Clone the repository:
   ```bash
   git clone https://github.com/iago-rhuda/stage-ai-applications.git
   cd stage-ai-applications
   ```

2. Create and activate a Python virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   playwright install chromium
   ```

4. Configure local environment variables:
   ```bash
   cp .env.example .env
   ```

5. Configure candidate profile:
   ```bash
   cp data/profile.example.json data/profile.json
   ```

6. Start local development server:
   ```bash
   python -m src.main
   ```
   Open your browser at `http://127.0.0.1:8080`.

---

## 5. License
Distributed under the MIT License. See `LICENSE` for details.
