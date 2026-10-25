/**
 * Human-in-the-Loop doubts queue management with rich vacancy inspector.
 */

const Doubts = {
  currentDoubts: [],

  async loadDoubts() {
    const data = await API.getDoubts();
    this.currentDoubts = data.doubts || [];

    const badge = document.getElementById("doubtsBadge");
    if (badge) badge.innerText = this.currentDoubts.length;

    const headerCount = document.getElementById("doubtsHeaderCount");
    if (headerCount) {
      headerCount.innerText = `${this.currentDoubts.length} vaga${this.currentDoubts.length === 1 ? "" : "s"} pendente${this.currentDoubts.length === 1 ? "" : "s"}`;
    }

    const kpiDoubts = document.getElementById("kpiDoubtsCount");
    if (kpiDoubts) kpiDoubts.innerText = this.currentDoubts.length;

    this.renderDoubts(this.currentDoubts);
    this.bindSearchAndActions();
  },

  renderDoubts(doubts) {
    const container = document.getElementById("doubtsList");
    if (!container) return;
    container.innerHTML = "";

    if (!doubts || doubts.length === 0) {
      container.innerHTML = `
        <div class="doubts-empty-state">
          <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" style="margin: 0 auto 1rem; color: var(--accent-green); opacity: 0.85;">
            <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/>
            <polyline points="22 4 12 14.01 9 11.01"/>
          </svg>
          <h3 style="color: var(--text-main); font-size: 1.1rem; margin-bottom: 0.5rem;">Fila de Validação Vazia</h3>
          <p style="font-size: 0.85rem; max-width: 450px; margin: 0 auto; color: var(--text-secondary);">
            Todas as oportunidades encontradas foram validadas ou promovidas ao Kanban. Quando o scraper identificar vagas com requisitos ou localização que necessitem de confirmação humana, elas aparecerão aqui para sua análise.
          </p>
        </div>
      `;
      return;
    }

    doubts.forEach((doubt) => {
      const job = doubt.job || {};
      const company = job.company_name || "Empresa Recrutadora";
      const title = job.title || "Vaga de Estágio";
      const location = job.location || "França";
      const workplace = job.workplace_type || "Híbrido";
      const source = (job.source || "web").toUpperCase();
      const jobUrl = job.job_url || "#";
      const initial = company.charAt(0).toUpperCase();

      // Requirements tags
      const rawReq = job.raw_requirements || "Python, IA, Machine Learning, Data";
      const skillTags = rawReq.split(/[,•\n]+/).map(s => s.trim()).filter(s => s.length > 1).slice(0, 6);

      const card = document.createElement("article");
      card.className = "doubt-card";
      card.setAttribute("data-doubt-id", doubt.id);
      card.setAttribute("data-search", `${company} ${title} ${location} ${rawReq}`.toLowerCase());

      card.innerHTML = `
        <div class="doubt-card-top">
          <div class="doubt-company-wrap">
            <div class="doubt-company-avatar">${initial}</div>
            <div>
              <div class="doubt-company-name">${company}</div>
              <div class="doubt-location">
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/><circle cx="12" cy="10" r="3"/></svg>
                <span>${location}</span>
              </div>
            </div>
          </div>
          <div class="doubt-badges">
            <span class="doubt-badge doubt-badge-source">${source}</span>
            <span class="doubt-badge doubt-badge-workplace">${workplace}</span>
            <span class="doubt-badge doubt-badge-timing">P27 (6 meses)</span>
          </div>
        </div>

        <div>
          <h3 class="doubt-job-title">${title}</h3>
        </div>

        <div class="doubt-diagnostic-box">
          <div class="doubt-diag-title">
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
            <span>Motivo da Dúvida / Diagnóstico</span>
          </div>
          <div class="doubt-diag-text">${doubt.question_text}</div>
          <div class="doubt-diag-suggestion">
            <strong>Sugestão:</strong> ${doubt.suggested_answer || "Analisar descrição da vaga e aprovar se relevante."}
          </div>
        </div>

        <div>
          <div style="font-size: 0.72rem; font-weight: 700; color: var(--text-muted); text-transform: uppercase; margin-bottom: 0.35rem;">
            Requisitos Detectados / Stack:
          </div>
          <div class="doubt-skills-wrap">
            ${skillTags.map(st => `<span class="doubt-skill-pill">${st}</span>`).join("")}
          </div>
        </div>

        <div class="doubt-description-box">
          <div class="doubt-desc-preview">
            ${job.description ? job.description.slice(0, 160) + (job.description.length > 160 ? "..." : "") : "Nenhuma descrição fornecida."}
          </div>
          ${job.description && job.description.length > 160 ? `
            <div class="doubt-desc-full">${job.description}</div>
            <button class="doubt-toggle-desc">Ver descrição completa ▼</button>
          ` : ""}
        </div>

        <div class="doubt-actions">
          <button class="btn-approve-doubt" title="Aprovar esta vaga, criar card no Kanban (Wishlist) e avaliar perfil">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="20 6 9 17 4 12"/></svg>
            Aprovar para Wishlist
          </button>
          <button class="btn-discard-doubt" title="Descartar vaga da fila de dúvidas">
            ✕ Descartar
          </button>
          <a href="${jobUrl}" target="_blank" rel="noopener noreferrer" class="btn-open-job-link" title="Abrir página oficial do anúncio">
            Abrir Vaga Original
            <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/><polyline points="15 3 21 3 21 9"/><line x1="10" y1="14" x2="21" y2="3"/></svg>
          </a>
        </div>
      `;

      // Expand / Collapse Description toggle
      const toggleBtn = card.querySelector(".doubt-toggle-desc");
      if (toggleBtn) {
        const fullDesc = card.querySelector(".doubt-desc-full");
        toggleBtn.addEventListener("click", () => {
          const isShown = fullDesc.style.display === "block";
          fullDesc.style.display = isShown ? "none" : "block";
          toggleBtn.innerText = isShown ? "Ver descrição completa ▼" : "Ocultar descrição ▲";
        });
      }

      // Approve action
      card.querySelector(".btn-approve-doubt").addEventListener("click", async () => {
        try {
          const res = await API.resolveDoubt(doubt.id, "Approved by candidate from web interface", "resolved");
          if (window.UI) {
            window.UI.showToast(`Vaga "${title}" na ${company} aprovada e adicionada ao Wishlist!`, "success", 4500);
          }
          await Doubts.loadDoubts();
          if (window.Kanban) await window.Kanban.loadApplications();
        } catch (err) {
          if (window.UI) window.UI.showToast(`Erro ao aprovar vaga: ${err.message}`, "error", 5000);
        }
      });

      // Discard action
      card.querySelector(".btn-discard-doubt").addEventListener("click", async () => {
        try {
          await API.resolveDoubt(doubt.id, "Discarded by candidate", "ignored");
          if (window.UI) {
            window.UI.showToast(`Vaga "${title}" descartada.`, "info", 3500);
          }
          await Doubts.loadDoubts();
        } catch (err) {
          if (window.UI) window.UI.showToast(`Erro ao descartar vaga: ${err.message}`, "error", 5000);
        }
      });

      container.appendChild(card);
    });
  },

  bindSearchAndActions() {
    const searchInput = document.getElementById("doubtsSearchInput");
    if (searchInput && !searchInput.dataset.bound) {
      searchInput.dataset.bound = "true";
      searchInput.addEventListener("input", (e) => {
        const query = e.target.value.toLowerCase().trim();
        const cards = document.querySelectorAll(".doubt-card");
        cards.forEach((card) => {
          const text = card.getAttribute("data-search") || "";
          card.style.display = text.includes(query) ? "flex" : "none";
        });
      });
    }

    const btnApproveAll = document.getElementById("btnApproveAllDoubts");
    if (btnApproveAll && !btnApproveAll.dataset.bound) {
      btnApproveAll.dataset.bound = "true";
      btnApproveAll.addEventListener("click", async () => {
        if (!this.currentDoubts || this.currentDoubts.length === 0) {
          if (window.UI) window.UI.showToast("Não há dúvidas pendentes para aprovar.", "info", 3000);
          return;
        }

        const confirmMsg = `Deseja aprovar todas as ${this.currentDoubts.length} vagas e adicioná-las ao Wishlist do Kanban?`;
        if (!confirm(confirmMsg)) return;

        try {
          const res = await API.resolveAllDoubts("Batch approved by candidate in web interface", "resolved");
          if (window.UI) {
            window.UI.showToast(`Sucesso! ${res.promoted_count || res.resolved_count} vagas promovidas para o Wishlist do Kanban!`, "success", 5000);
          }
          await Doubts.loadDoubts();
          if (window.Kanban) await window.Kanban.loadApplications();
        } catch (err) {
          if (window.UI) window.UI.showToast(`Erro ao aprovar vagas: ${err.message}`, "error", 5000);
        }
      });
    }
  },
};
