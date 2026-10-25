/**
 * Interactive Drag-and-Drop Kanban Board Component (VibePrompts Architecture).
 */

const Kanban = {
  columns: ["wishlist", "to_apply", "applied", "interview", "offer", "rejected"],

  init() {
    this.setupDragAndDrop();
    this.loadApplications();
  },

  setupDragAndDrop() {
    document.querySelectorAll(".kanban-col").forEach((col) => {
      col.addEventListener("dragover", (e) => {
        e.preventDefault();
        col.style.background = "rgba(28, 39, 60, 0.95)";
      });

      col.addEventListener("dragleave", () => {
        col.style.background = "";
      });

      col.addEventListener("drop", async (e) => {
        e.preventDefault();
        col.style.background = "";
        const appId = e.dataTransfer.getData("text/plain");
        const targetStatus = col.dataset.status;

        if (appId && targetStatus) {
          await API.updateApplicationStatus(appId, targetStatus);
          await this.loadApplications();
        }
      });
    });
  },

  async loadApplications() {
    const data = await API.getApplications();
    const apps = data.applications || [];

    // Clear all column containers
    this.columns.forEach((status) => {
      const container = document.getElementById(`cards-${status}`);
      const counter = document.getElementById(`count-${status}`);
      if (container) container.innerHTML = "";
      if (counter) counter.innerText = "0";
    });

    const statusCounts = {};

    apps.forEach((app) => {
      const colId = app.status;
      statusCounts[colId] = (statusCounts[colId] || 0) + 1;
      const container = document.getElementById(`cards-${colId}`);
      if (container) {
        container.appendChild(this.renderCard(app));
      }
    });

    // Update column counters
    this.columns.forEach((status) => {
      const counter = document.getElementById(`count-${status}`);
      if (counter) counter.innerText = statusCounts[status] || "0";
    });

    if (window.UI && typeof window.UI.updateKPIs === "function") {
      window.UI.updateKPIs(apps);
    }
  },

  renderCard(app) {
    const card = document.createElement("div");
    card.className = "job-card";
    card.draggable = true;
    card.dataset.id = app.id;

    card.addEventListener("dragstart", (e) => {
      e.dataTransfer.setData("text/plain", app.id);
    });

    const job = app.job || {};
    const company = job.company_name || "Company";
    const title = job.title || "Stage Ingénieur IA";
    const loc = job.location || "Paris, France";
    const score = job.compliance_score ? Math.round(job.compliance_score * 100) : 100;

    let docButtonsHtml = "";
    if (app.cv_web_url) {
      docButtonsHtml += `<a href="${app.cv_web_url}" target="_blank" class="card-btn btn-ready" title="Open compiled 1-page LaTeX CV">📄 View CV</a>`;
    }
    if (app.cover_letter_web_url) {
      docButtonsHtml += `<a href="${app.cover_letter_web_url}" target="_blank" class="card-btn btn-ready" title="Open generated Cover Letter">✉️ LM</a>`;
    }

    card.innerHTML = `
      <div class="card-company">${company}</div>
      <div class="card-title">${title}</div>
      <div class="card-meta">
        <span class="tag tag-iad">IAD ${score}%</span>
        <span class="tag">${loc}</span>
        <span class="tag">${(app.application_mode || "semi_auto").toUpperCase()}</span>
      </div>
      <div class="card-actions" id="cardActions-${app.id}">
        ${docButtonsHtml}
        <button class="card-btn btn-gen-doc">${app.cv_web_url ? "Regenerate CV" : "Generate CV"}</button>
        ${job.job_url ? `<a href="${job.job_url}" target="_blank" class="card-btn" rel="noreferrer">Job Link</a>` : ""}
      </div>
      <div class="card-progress-wrapper" style="display: none;" id="cardProgress-${app.id}">
        <div class="card-inline-progress"><div class="card-inline-fill"></div></div>
        <div style="font-size: 0.72rem; color: var(--accent-cyan); margin-top: 0.25rem;">Compiling LaTeX template with pdflatex...</div>
      </div>
    `;

    const genBtn = card.querySelector(".btn-gen-doc");
    const progressEl = card.querySelector(`#cardProgress-${app.id}`);

    genBtn.addEventListener("click", async () => {
      genBtn.disabled = true;
      genBtn.classList.add("loading");
      genBtn.innerText = "Compiling...";
      if (progressEl) progressEl.style.display = "block";

      if (window.UI) {
        window.UI.setPipelineProgress(45, `Compiling custom LaTeX CV for ${company}...`);
        window.UI.showToast(`Compiling single-page LaTeX CV for ${company}...`, "info", 4000);
      }

      try {
        const res = await API.generateDocuments(app.id);
        if (progressEl) progressEl.style.display = "none";
        genBtn.classList.remove("loading");
        genBtn.disabled = false;
        genBtn.innerText = "Regenerate CV";

        if (window.UI) {
          window.UI.setPipelineProgress(100, `CV compiled for ${company}!`);
          window.UI.showToast(
            `Resume successfully generated for ${company}!`,
            "success",
            8000,
            [{ label: "Open PDF", url: res.cv_web_url }]
          );
        }

        await Kanban.loadApplications();
      } catch (err) {
        if (progressEl) progressEl.style.display = "none";
        genBtn.classList.remove("loading");
        genBtn.disabled = false;
        genBtn.innerText = "Retry CV";

        if (window.UI) {
          window.UI.setPipelineProgress(100, `Error compiling CV: ${err.message}`, true);
          window.UI.showToast(`LaTeX compilation failed: ${err.message}`, "error", 8000);
        }
      }
    });

    return card;
  },
};
