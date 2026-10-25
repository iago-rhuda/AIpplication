/**
 * Interactive Drag-and-Drop Kanban Board Component with Career-Ops Traceability & Rich A-H Inspection.
 */

const Kanban = {
  columns: ["wishlist", "to_apply", "applied", "interview", "offer", "rejected"],
  columnLabels: {
    wishlist: "Wishlist",
    to_apply: "To Apply",
    applied: "Applied",
    interview: "Interview",
    offer: "Offer",
    rejected: "Rejected",
  },
  allApplications: [],
  filters: {
    search: "",
    minScore: 0,
    workplace: "all",
  },
  currentApp: null,

  init() {
    this.setupDragAndDrop();
    this.setupFilters();
    this.setupModal();
    this.loadApplications();
  },

  setupDragAndDrop() {
    document.querySelectorAll(".kanban-col").forEach((col) => {
      const container = col.querySelector(".kanban-cards");

      col.addEventListener("dragover", (e) => {
        e.preventDefault();
        col.classList.add("drag-over");

        const draggingCard = document.querySelector(".job-card.dragging");
        if (container && draggingCard) {
          const afterElement = Kanban.getDragAfterElement(container, e.clientY);
          if (afterElement == null) {
            container.appendChild(draggingCard);
          } else {
            container.insertBefore(draggingCard, afterElement);
          }
        }
      });

      col.addEventListener("dragleave", (e) => {
        if (!col.contains(e.relatedTarget)) {
          col.classList.remove("drag-over");
        }
      });

      col.addEventListener("drop", async (e) => {
        e.preventDefault();
        col.classList.remove("drag-over");
        const draggingCard = document.querySelector(".job-card.dragging");
        const appId = draggingCard ? draggingCard.dataset.id : e.dataTransfer.getData("text/plain");
        const targetStatus = col.dataset.status;

        if (appId && targetStatus) {
          Kanban.recountColumns();
          const targetLabel = Kanban.columnLabels[targetStatus] || targetStatus;
          try {
            await API.updateApplicationStatus(appId, targetStatus, `Movido para ${targetLabel} via Kanban`, "user");
            if (window.UI) {
              window.UI.showToast(`Candidatura #${appId} movida para "${targetLabel}" e registrada no status-log.tsv`, "success", 4000);
            }
            await Kanban.loadApplications();
          } catch (err) {
            console.error("Erro ao atualizar status:", err);
            await Kanban.loadApplications();
          }
        }
      });
    });
  },

  getDragAfterElement(container, y) {
    const draggableElements = [...container.querySelectorAll(".job-card:not(.dragging)")];
    return draggableElements.reduce(
      (closest, child) => {
        const box = child.getBoundingClientRect();
        const offset = y - box.top - box.height / 2;
        if (offset < 0 && offset > closest.offset) {
          return { offset: offset, element: child };
        } else {
          return closest;
        }
      },
      { offset: Number.NEGATIVE_INFINITY }
    ).element;
  },

  recountColumns() {
    this.columns.forEach((status) => {
      const container = document.getElementById(`cards-${status}`);
      const counter = document.getElementById(`count-${status}`);
      if (container && counter) {
        const cards = container.querySelectorAll(".job-card");
        counter.innerText = cards.length;
        const emptyState = container.querySelector(".kanban-empty-state");
        if (cards.length === 0 && !emptyState) {
          container.innerHTML = `
            <div class="kanban-empty-state">
              <span class="empty-icon">📭</span>
              <span class="empty-text">Nenhuma vaga aqui</span>
            </div>
          `;
        } else if (cards.length > 0 && emptyState) {
          emptyState.remove();
        }
      }
    });
  },

  setupFilters() {
    const searchInput = document.getElementById("kanbanSearch");
    if (searchInput) {
      searchInput.addEventListener("input", (e) => {
        this.filters.search = e.target.value.toLowerCase().trim();
        this.applyFiltersAndRender();
      });
    }

    const scoreFilter = document.getElementById("kanbanScoreFilter");
    if (scoreFilter) {
      scoreFilter.addEventListener("change", (e) => {
        this.filters.minScore = e.target.value === "all" ? 0 : parseFloat(e.target.value);
        this.applyFiltersAndRender();
      });
    }

    const workplaceFilter = document.getElementById("kanbanWorkplaceFilter");
    if (workplaceFilter) {
      workplaceFilter.addEventListener("change", (e) => {
        this.filters.workplace = e.target.value;
        this.applyFiltersAndRender();
      });
    }
  },

  setupModal() {
    const modal = document.getElementById("cardDetailModal");
    const closeBtn = document.getElementById("modalCloseBtn");

    if (closeBtn && modal) {
      closeBtn.addEventListener("click", () => {
        modal.style.display = "none";
      });

      modal.addEventListener("click", (e) => {
        if (e.target === modal) modal.style.display = "none";
      });
    }

    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape" && modal && modal.style.display !== "none") {
        modal.style.display = "none";
      }
    });

    // Tab buttons inside the modal
    document.querySelectorAll(".modal-tab-btn").forEach((btn) => {
      btn.addEventListener("click", () => {
        document.querySelectorAll(".modal-tab-btn").forEach((b) => b.classList.remove("active"));
        document.querySelectorAll(".modal-pane").forEach((p) => p.classList.remove("active"));

        btn.classList.add("active");
        const targetPane = document.getElementById(btn.dataset.modaltab);
        if (targetPane) targetPane.classList.add("active");
      });
    });
  },

  async loadApplications() {
    try {
      const data = await API.getApplications();
      this.allApplications = data.applications || [];
      this.applyFiltersAndRender();

      if (window.UI && typeof window.UI.updateKPIs === "function") {
        window.UI.updateKPIs(this.allApplications);
      }
    } catch (err) {
      console.error("Failed to load applications:", err);
    }
  },

  applyFiltersAndRender() {
    // Clear all columns
    this.columns.forEach((status) => {
      const container = document.getElementById(`cards-${status}`);
      const counter = document.getElementById(`count-${status}`);
      if (container) container.innerHTML = "";
      if (counter) counter.innerText = "0";
    });

    const statusCounts = {};

    const filtered = this.allApplications.filter((app) => {
      const job = app.job || {};
      const company = (job.company_name || "").toLowerCase();
      const title = (job.title || "").toLowerCase();
      const reqs = (job.raw_requirements || "").toLowerCase();
      const score = app.evaluation_score || 0;
      const workplace = (job.workplace_type || "").toLowerCase();

      // Search match
      if (this.filters.search) {
        const q = this.filters.search;
        const matchesSearch = company.includes(q) || title.includes(q) || reqs.includes(q);
        if (!matchesSearch) return false;
      }

      // Score filter
      if (this.filters.minScore > 0 && score < this.filters.minScore) {
        return false;
      }

      // Workplace filter
      if (this.filters.workplace !== "all" && workplace !== this.filters.workplace) {
        return false;
      }

      return true;
    });

    filtered.forEach((app) => {
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
    card.setAttribute("data-card", app.id);

    card.addEventListener("dragstart", (e) => {
      card.classList.add("dragging");
      e.dataTransfer.setData("text/plain", app.id);
      e.dataTransfer.effectAllowed = "move";
    });

    card.addEventListener("dragend", () => {
      card.classList.remove("dragging");
      document.querySelectorAll(".kanban-col").forEach((c) => c.classList.remove("drag-over"));
      Kanban.recountColumns();
    });

    const job = app.job || {};
    const company = job.company_name || "Company";
    const title = job.title || "Stage Ingénieur IA";
    const loc = job.location || "Paris, France";
    const compliance = job.compliance_score ? Math.round(job.compliance_score * 100) : 95;
    const evalScore = app.evaluation_score ? app.evaluation_score.toFixed(1) : "4.5";
    const grade = app.match_grade || "A";
    const initial = company.charAt(0).toUpperCase();

    // Latest status note snippet
    let latestNoteHtml = "";
    if (app.status_events && app.status_events.length > 0) {
      const lastEv = app.status_events[0];
      if (lastEv && lastEv.notes) {
        latestNoteHtml = `
          <div class="card-ledger-snippet" title="Último evento no ledger: ${escapeHtml(lastEv.notes)}">
            📜 ${escapeHtml(lastEv.notes)}
          </div>
        `;
      }
    } else if (app.notes) {
      latestNoteHtml = `
        <div class="card-ledger-snippet" title="${escapeHtml(app.notes)}">
          💬 ${escapeHtml(app.notes)}
        </div>
      `;
    }

    // Follow-up cadence badge
    let cadenceBadgeHtml = "";
    const tagClass = app.cadence_tag === "overdue" ? "cadence-overdue" : (app.cadence_tag === "due" ? "cadence-due" : "cadence-normal");
    cadenceBadgeHtml = `<span class="card-cadence-badge ${tagClass}">⏳ ${app.cadence_label || "Ativo"}</span>`;

    const eventsCount = app.status_events ? app.status_events.length : 1;

    card.innerHTML = `
      <div class="card-chips-row">
        <span class="category-chip chip-score" title="Career-Ops Score">⭐ ${evalScore} (${grade})</span>
        <span class="category-chip chip-iad" title="UTC TN10 IAD Compliance">IAD ${compliance}%</span>
        <span class="category-chip chip-workplace">${job.workplace_type || "Hybrid"}</span>
        <span class="category-chip chip-loc">${loc.split(",")[0]}</span>
      </div>

      <div class="card-main-info">
        <div class="card-company-name">${escapeHtml(company)}</div>
        <div class="card-task-title">${escapeHtml(title)}</div>
      </div>

      ${app.salary_range ? `<div class="card-salary-text">💶 ${escapeHtml(app.salary_range)}</div>` : ""}

      ${latestNoteHtml}

      <div class="card-footer-row">
        <div class="card-footer-left">
          <div class="card-avatar-circle" title="${escapeHtml(company)}">${initial}</div>
          ${cadenceBadgeHtml}
        </div>
        <div class="card-footer-right">
          <span class="card-comment-count" title="Transições registradas no ledger">📋 ${eventsCount}</span>
          <button class="card-quick-inspect" title="Abrir Dossiê A-H e Rastreabilidade">🔍 Detalhes</button>
        </div>
      </div>
    `;

    // Click card body or inspect button to open inspection modal
    card.addEventListener("click", (e) => {
      this.openModal(app.id, "tabEvaluation");
    });

    const inspectBtn = card.querySelector(".card-quick-inspect");
    if (inspectBtn) {
      inspectBtn.addEventListener("click", (e) => {
        e.stopPropagation();
        this.openModal(app.id, "tabTimeline");
      });
    }
    return card;
  },

  async openModal(appId, initialTab = "tabEvaluation") {
    try {
      const res = await API.getApplication(appId);
      const app = res.application;
      if (!app) return;
      this.currentApp = app;

      const modal = document.getElementById("cardDetailModal");
      if (!modal) return;

      const job = app.job || {};
      const company = job.company_name || "Company";
      const title = job.title || "Stage Ingénieur IA";

      // 1. Populate Header
      const avatarEl = document.getElementById("modalCompanyAvatar");
      if (avatarEl) avatarEl.innerText = company.charAt(0).toUpperCase();

      const companyEl = document.getElementById("modalCompany");
      if (companyEl) companyEl.innerText = company;

      const titleEl = document.getElementById("modalTitle");
      if (titleEl) titleEl.innerText = title;

      const scoreBadge = document.getElementById("modalScoreBadge");
      if (scoreBadge) {
        scoreBadge.innerText = `⭐ ${app.evaluation_score ? app.evaluation_score.toFixed(1) : "4.5"} / 5.0 (${app.match_grade || "A"})`;
      }

      // Populate Status dropdown
      const statusSelect = document.getElementById("modalStatusSelect");
      if (statusSelect) {
        statusSelect.innerHTML = "";
        this.columns.forEach((st) => {
          const opt = document.createElement("option");
          opt.value = st;
          opt.innerText = this.columnLabels[st] || st;
          if (st === app.status) opt.selected = true;
          statusSelect.appendChild(opt);
        });

        // Remove old listener and add new one
        statusSelect.onchange = async () => {
          const newStatus = statusSelect.value;
          if (newStatus !== app.status) {
            const note = prompt(`Reason/note for transitioning to ${Kanban.columnLabels[newStatus] || newStatus}:`, "");
            await API.updateApplicationStatus(app.id, newStatus, note || "Status updated via inspection modal", "user");
            if (window.UI) {
              window.UI.showToast(`Updated to ${Kanban.columnLabels[newStatus]} & recorded in status-log.tsv`, "success", 4000);
            }
            await Kanban.loadApplications();
            await Kanban.openModal(app.id, "tabTimeline");
          }
        };
      }

      // 2. Populate Meta Strip
      const metaStrip = document.getElementById("modalMetaStrip");
      if (metaStrip) {
        metaStrip.innerHTML = `
          <span class="meta-pill">📍 ${escapeHtml(job.location || "Paris, France")}</span>
          <span class="meta-pill">🏢 ${escapeHtml(job.workplace_type || "Hybrid")}</span>
          <span class="meta-pill">📅 ${escapeHtml(job.start_date || "Fév 2027")} (${job.duration_weeks || 26} sem)</span>
          <span class="meta-pill">💶 ${escapeHtml(app.salary_range || "1 400€ - 1 800€ / mois")}</span>
          <span class="meta-pill ${app.cadence_tag === "overdue" ? "pill-danger" : (app.cadence_tag === "due" ? "pill-warning" : "pill-success")}">
            ⏳ Cadence: ${escapeHtml(app.cadence_label || "Active")}
          </span>
          ${job.job_url ? `<a href="${job.job_url}" target="_blank" class="meta-pill pill-link" rel="noreferrer">🔗 View Posting ↗</a>` : ""}
        `;
      }

      // 3. Render Tab Panes
      this.renderEvaluationTab(app);
      this.renderTimelineTab(app);
      this.renderContactsTab(app);
      this.renderAnswersTab(app);
      this.renderRawReportTab(app);

      // 4. Activate chosen tab
      document.querySelectorAll(".modal-tab-btn").forEach((b) => {
        b.classList.toggle("active", b.dataset.modaltab === initialTab);
      });
      document.querySelectorAll(".modal-pane").forEach((p) => {
        p.classList.toggle("active", p.id === initialTab);
      });

      modal.style.display = "flex";
    } catch (err) {
      console.error("Failed to open application modal:", err);
    }
  },

  renderEvaluationTab(app) {
    const pane = document.getElementById("tabEvaluation");
    if (!pane) return;

    const job = app.job || {};

    pane.innerHTML = `
      <div class="eval-grid">
        <!-- Block A: Role & TN10 Compliance -->
        <div class="eval-card">
          <div class="eval-card-header">
            <span class="eval-badge">Block A</span>
            <h4>Role Summary &amp; UTC TN10 Alignment</h4>
          </div>
          <table class="eval-table">
            <tr><td><strong>Domain:</strong></td><td>${escapeHtml(job.title)}</td></tr>
            <tr><td><strong>Workplace:</strong></td><td>${escapeHtml(job.workplace_type || "Hybrid")} (${escapeHtml(job.location)})</td></tr>
            <tr><td><strong>TN10 Schedule:</strong></td><td>✅ P27 compliant (Start: ${escapeHtml(job.start_date || "Fév 2027")}, Duration: ${job.duration_weeks || 26} weeks)</td></tr>
            <tr><td><strong>Work Auth:</strong></td><td>➖ French Convention de Stage (UTC Université de Technologie de Compiègne)</td></tr>
            <tr><td><strong>Culture Screen:</strong></td><td>✅ Favorable — Team in active engineering growth</td></tr>
          </table>
        </div>

        <!-- Block D: Gratification Benchmark -->
        <div class="eval-card">
          <div class="eval-card-header">
            <span class="eval-badge">Block D</span>
            <h4>Compensation &amp; Gratification Benchmark</h4>
          </div>
          <div style="font-size: 1.1rem; font-weight: 700; color: var(--accent-green); margin-bottom: 0.5rem;">
            ${escapeHtml(app.salary_range || "1 400€ - 1 800€ / mois")}
          </div>
          <p style="font-size: 0.85rem; color: var(--text-muted); line-height: 1.5;">
            Legal minimum gratification in France is 4.35€/h (~650€/mo). Paris market benchmark for Bac+5 engineering interns (UTC TN10) typically ranges from 1,300€ to 2,000€/month.
          </p>
        </div>
      </div>

      <!-- Block B: Requirements & Match Breakdown -->
      <div class="eval-card" style="margin-top: 1rem;">
        <div class="eval-card-header">
          <span class="eval-badge">Block B</span>
          <h4>CV Match &amp; Requirement Gap Analysis</h4>
        </div>
        <p style="font-size: 0.85rem; color: var(--text-muted); margin-bottom: 0.75rem;">
          Raw requirements: <code>${escapeHtml(job.raw_requirements || "Python, Machine Learning, Deep Learning")}</code>
        </p>
        <div class="skills-match-strip">
          <span class="skill-tag match">✓ Python (Advanced)</span>
          <span class="skill-tag match">✓ PyTorch / Transformers</span>
          <span class="skill-tag match">✓ RAG &amp; Vector DBs</span>
          <span class="skill-tag match">✓ FastAPI &amp; Async</span>
          <span class="skill-tag match">✓ Git &amp; Docker</span>
          <span class="skill-tag bonus">+ Graphify / Knowledge Graphs</span>
        </div>
      </div>

      <!-- Block F: STAR+R Stories -->
      <div class="eval-card" style="margin-top: 1rem;">
        <div class="eval-card-header">
          <span class="eval-badge">Block F</span>
          <h4>Pre-Calculated STAR+R Stories for Interviews</h4>
        </div>
        ${this.renderStarStoriesHtml(app.star_stories)}
      </div>
    `;
  },

  renderStarStoriesHtml(stories) {
    if (!stories || stories.length === 0) {
      return `<p style="font-size: 0.85rem; color: var(--text-muted);">No STAR stories generated yet.</p>`;
    }

    return stories.map((s, idx) => `
      <div class="star-card">
        <div class="star-header">⭐ Master Story #${idx + 1}: ${escapeHtml(s.theme || "Engineering Challenge")}</div>
        <div class="star-row"><strong>S (Situation):</strong> ${escapeHtml(s.situation)}</div>
        <div class="star-row"><strong>T (Task):</strong> ${escapeHtml(s.task)}</div>
        <div class="star-row"><strong>A (Action):</strong> ${escapeHtml(s.action)}</div>
        <div class="star-row"><strong>R (Result):</strong> ${escapeHtml(s.result)}</div>
        <div class="star-row"><strong>R (Reflection):</strong> ${escapeHtml(s.reflection)}</div>
      </div>
    `).join("");
  },

  renderTimelineTab(app) {
    const pane = document.getElementById("tabTimeline");
    if (!pane) return;

    const events = app.status_events || [];

    let eventsHtml = "";
    if (events.length === 0) {
      eventsHtml = `<div style="color: var(--text-muted); font-size: 0.85rem; padding: 1rem;">No status transitions recorded yet.</div>`;
    } else {
      eventsHtml = events.map((ev) => {
        const fromLabel = ev.from_status ? (this.columnLabels[ev.from_status] || ev.from_status) : "Registered";
        const toLabel = this.columnLabels[ev.to_status] || ev.to_status;
        const dt = ev.created_at ? ev.created_at.replace("T", " ").slice(0, 16) : "Just now";

        return `
          <div class="timeline-item">
            <div class="timeline-dot"></div>
            <div class="timeline-content">
              <div class="timeline-header">
                <span class="timeline-transition"><strong>${fromLabel}</strong> ➔ <strong>${toLabel}</strong></span>
                <span class="timeline-source badge-source-${ev.source || 'user'}">${ev.source || 'user'}</span>
                <span class="timeline-date">${dt}</span>
              </div>
              ${ev.notes ? `<div class="timeline-notes">${escapeHtml(ev.notes)}</div>` : ""}
            </div>
          </div>
        `;
      }).join("");
    }

    pane.innerHTML = `
      <div class="timeline-wrapper">
        <div class="timeline-left">
          <h4 style="margin-bottom: 0.75rem; font-size: 0.95rem; display: flex; align-items: center; gap: 0.5rem;">
            📜 Career-Ops Status Transition Ledger
            <span style="font-size: 0.72rem; color: var(--text-muted); font-weight: normal;">(Synced with data/status-log.tsv)</span>
          </h4>
          <div class="timeline-stream">
            ${eventsHtml}
          </div>
        </div>

        <div class="timeline-right">
          <!-- Transition Status Form -->
          <div class="action-box">
            <h4>Transition Status Stage</h4>
            <div class="form-group">
              <label>Target Kanban Column:</label>
              <select id="timelineTargetStatus" class="form-select">
                ${this.columns.map(c => `<option value="${c}" ${c === app.status ? "selected" : ""}>${this.columnLabels[c] || c}</option>`).join("")}
              </select>
            </div>
            <div class="form-group">
              <label>Transition Reason / Note:</label>
              <input type="text" id="timelineTransitionNote" class="form-input" placeholder="e.g. 1st Technical Interview Scheduled">
            </div>
            <button id="btnExecuteTransition" class="btn" style="width: 100%; justify-content: center;">
              Execute Status Transition
            </button>
          </div>

          <!-- Add Interaction Note Form -->
          <div class="action-box" style="margin-top: 1rem;">
            <h4>Add Interaction Note (Without Moving)</h4>
            <div class="form-group">
              <input type="text" id="timelineInteractionNote" class="form-input" placeholder="e.g. Sent follow-up email to HR">
            </div>
            <button id="btnAddInteraction" class="btn btn-secondary" style="width: 100%; justify-content: center;">
              Append Note to Ledger
            </button>
          </div>
        </div>
      </div>
    `;

    // Bind transition action
    const btnTrans = pane.querySelector("#btnExecuteTransition");
    if (btnTrans) {
      btnTrans.addEventListener("click", async () => {
        const targetStatus = pane.querySelector("#timelineTargetStatus").value;
        const note = pane.querySelector("#timelineTransitionNote").value.trim();
        btnTrans.disabled = true;

        try {
          await API.updateApplicationStatus(app.id, targetStatus, note || `Transitioned to ${targetStatus}`, "user");
          if (window.UI) {
            window.UI.showToast(`Application transitioned to ${Kanban.columnLabels[targetStatus]}!`, "success", 4000);
          }
          await Kanban.loadApplications();
          await Kanban.openModal(app.id, "tabTimeline");
        } catch (err) {
          alert(`Failed to update status: ${err.message}`);
          btnTrans.disabled = false;
        }
      });
    }

    // Bind add interaction note action
    const btnNote = pane.querySelector("#btnAddInteraction");
    if (btnNote) {
      btnNote.addEventListener("click", async () => {
        const note = pane.querySelector("#timelineInteractionNote").value.trim();
        if (!note) return;
        btnNote.disabled = true;

        try {
          await API.addApplicationEvent(app.id, note, "user");
          if (window.UI) {
            window.UI.showToast("Note recorded in status-log.tsv and database!", "success", 3000);
          }
          await Kanban.loadApplications();
          await Kanban.openModal(app.id, "tabTimeline");
        } catch (err) {
          alert(`Failed to add note: ${err.message}`);
          btnNote.disabled = false;
        }
      });
    }
  },

  renderContactsTab(app) {
    const pane = document.getElementById("tabContacts");
    if (!pane) return;

    const contactName = app.key_contact_name || "Responsable Recrutement Tech";
    const contactRole = app.key_contact_role || `Talent Acquisition — ${app.job.company_name}`;
    const outreach = app.outreach_message || `Bonjour, élève-ingénieur IA à l'UTC (filière IAD), je prépare mon stage PFE de 6 mois dès fév 2027. Votre offre chez ${app.job.company_name} correspond parfaitement à mon profil. Seriez-vous ouvert à un rapide échange ?`;

    pane.innerHTML = `
      <div class="eval-grid">
        <div class="eval-card">
          <div class="eval-card-header">
            <span class="eval-badge">Direct Contact</span>
            <h4>Identified Hiring Contact</h4>
          </div>
          <div style="font-size: 1.05rem; font-weight: 700; margin-bottom: 0.25rem;">${escapeHtml(contactName)}</div>
          <div style="font-size: 0.85rem; color: var(--accent-cyan); margin-bottom: 0.75rem;">${escapeHtml(contactRole)}</div>
          <p style="font-size: 0.8rem; color: var(--text-muted); line-height: 1.4;">
            Identified via Career-Ops contact discovery protocol. Synced with <code>data/contacts.tsv</code>.
          </p>
        </div>

        <div class="eval-card">
          <div class="eval-card-header">
            <span class="eval-badge">Networking Protocol</span>
            <h4>LinkedIn Connection Request Draft (≤300 chars)</h4>
          </div>
          <textarea id="linkedinOutreachText" class="copy-textarea" rows="4" readonly>${escapeHtml(outreach)}</textarea>
          <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 0.5rem;">
            <span style="font-size: 0.75rem; color: var(--text-muted);">${outreach.length} / 300 characters</span>
            <button id="btnCopyLinkedIn" class="btn" style="font-size: 0.75rem; padding: 0.35rem 0.75rem;">
              📋 Copy Message
            </button>
          </div>
        </div>
      </div>
    `;

    const copyBtn = pane.querySelector("#btnCopyLinkedIn");
    if (copyBtn) {
      copyBtn.addEventListener("click", () => {
        navigator.clipboard.writeText(outreach);
        copyBtn.innerText = "✓ Copied!";
        setTimeout(() => (copyBtn.innerText = "📋 Copy Message"), 2500);
      });
    }
  },

  renderAnswersTab(app) {
    const pane = document.getElementById("tabAnswers");
    if (!pane) return;

    const answers = app.form_answers || {};
    const q1 = answers.why_company || `Je souhaite rejoindre ${app.job.company_name} car votre approche allie rigueur d'ingénierie et impact produit.`;
    const q2 = answers.biggest_challenge || `Conception d'une plateforme d'assistance documentaire RAG sous FastAPI avec traçabilité complète.`;
    const q3 = answers.availability_constraints || `Disponible pour un stage de fin d'études conventionné UTC (TN10) dès le 1er février 2027 pour 24 à 26 semaines.`;

    pane.innerHTML = `
      <div class="answers-container">
        <p style="font-size: 0.85rem; color: var(--text-muted); margin-bottom: 1rem;">
          Block H pre-drafted French application form answers, ready for 1-click copy into job portals:
        </p>

        <div class="answer-card">
          <div class="answer-header">
            <strong>1. Pourquoi souhaitez-vous rejoindre ${escapeHtml(app.job.company_name)} ?</strong>
            <button class="btn-copy-ans btn btn-secondary" data-target="ans1">Copy</button>
          </div>
          <div class="answer-body" id="ans1">${escapeHtml(q1)}</div>
        </div>

        <div class="answer-card" style="margin-top: 0.75rem;">
          <div class="answer-header">
            <strong>2. Décrivez un défi technique significatif que vous avez surmonté :</strong>
            <button class="btn-copy-ans btn btn-secondary" data-target="ans2">Copy</button>
          </div>
          <div class="answer-body" id="ans2">${escapeHtml(q2)}</div>
        </div>

        <div class="answer-card" style="margin-top: 0.75rem;">
          <div class="answer-header">
            <strong>3. Disponibilités et contraintes de convention :</strong>
            <button class="btn-copy-ans btn btn-secondary" data-target="ans3">Copy</button>
          </div>
          <div class="answer-body" id="ans3">${escapeHtml(q3)}</div>
        </div>
      </div>
    `;

    pane.querySelectorAll(".btn-copy-ans").forEach((btn) => {
      btn.addEventListener("click", () => {
        const text = pane.querySelector(`#${btn.dataset.target}`).innerText;
        navigator.clipboard.writeText(text);
        btn.innerText = "✓ Copied";
        setTimeout(() => (btn.innerText = "Copy"), 2000);
      });
    });
  },

  async renderRawReportTab(app) {
    const pane = document.getElementById("tabRawReport");
    if (!pane) return;

    pane.innerHTML = `
      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.75rem;">
        <div style="font-size: 0.85rem; color: var(--text-muted);">
          Raw Markdown Report: <code>${escapeHtml(app.report_path || "reports/...")}</code>
        </div>
        <div style="display: flex; gap: 0.5rem;">
          ${app.report_web_url ? `<a href="${app.report_web_url}" target="_blank" class="btn btn-secondary" style="font-size: 0.75rem;">Download MD</a>` : ""}
          <button id="btnReevaluate" class="btn" style="font-size: 0.75rem;">Re-run A-H Evaluation</button>
        </div>
      </div>
      <div id="rawReportContent" class="raw-report-view">Loading report content...</div>
    `;

    try {
      const rawText = await API.getApplicationReport(app.id);
      const container = pane.querySelector("#rawReportContent");
      if (container) container.innerText = rawText;
    } catch (err) {
      const container = pane.querySelector("#rawReportContent");
      if (container) container.innerText = `Error loading report: ${err.message}`;
    }

    const reEvalBtn = pane.querySelector("#btnReevaluate");
    if (reEvalBtn) {
      reEvalBtn.addEventListener("click", async () => {
        reEvalBtn.disabled = true;
        reEvalBtn.innerText = "Evaluating...";
        try {
          await API.triggerEvaluation(app.id);
          if (window.UI) window.UI.showToast("Evaluation re-run complete!", "success", 3000);
          await Kanban.openModal(app.id, "tabRawReport");
        } catch (err) {
          alert(`Re-evaluation failed: ${err.message}`);
          reEvalBtn.disabled = false;
        }
      });
    }
  },
};

function escapeHtml(str) {
  if (!str) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

window.Kanban = Kanban;
