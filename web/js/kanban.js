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

    card.innerHTML = `
      <div class="card-company">${company}</div>
      <div class="card-title">${title}</div>
      <div class="card-meta">
        <span class="tag tag-iad">IAD Compliant</span>
        <span class="tag">${loc}</span>
        <span class="tag">${app.application_mode.toUpperCase()}</span>
      </div>
      <div class="card-actions">
        <button class="card-btn btn-gen-doc">Generate CV</button>
        ${job.job_url ? `<a href="${job.job_url}" target="_blank" class="card-btn">Job Link</a>` : ""}
      </div>
    `;

    const genBtn = card.querySelector(".btn-gen-doc");
    genBtn.addEventListener("click", async () => {
      genBtn.innerText = "Generating...";
      genBtn.disabled = true;
      try {
        const res = await API.generateDocuments(app.id);
        genBtn.innerText = "PDF Ready";
        alert(`Documents compiled successfully!\nCV: ${res.cv_pdf_path}`);
      } catch (err) {
        genBtn.innerText = "Error";
        alert(`Generation failed: ${err.message}`);
      }
    });

    return card;
  },
};
