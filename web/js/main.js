/**
 * Main application script initializing tabs, real-time WebSockets, progress bars, theme toggle, and controls.
 */

const UI = {
  activePollInterval: null,
  progressHideTimeout: null,

  showToast(title, type = "info", duration = 5000, actions = []) {
    const container = document.getElementById("toastContainer");
    if (!container) return;

    const toast = document.createElement("div");
    toast.className = `toast toast-${type}`;

    const icons = {
      success: "✓",
      info: "ℹ",
      warning: "⚠",
      error: "✕",
    };

    let actionsHtml = "";
    if (actions && actions.length > 0) {
      actionsHtml =
        `<div class="toast-actions">` +
        actions.map((a) => `<a href="${a.url}" target="_blank" class="toast-action-btn">${a.label}</a>`).join("") +
        `</div>`;
    }

    toast.innerHTML = `
      <div class="toast-row">
        <span class="toast-icon">${icons[type] || "•"}</span>
        <div class="toast-content">
          <div class="toast-title">${title}</div>
          ${actionsHtml}
        </div>
        <button class="toast-close" title="Fechar">&times;</button>
      </div>
      <div class="toast-bar"></div>
    `;

    container.appendChild(toast);

    const closeBtn = toast.querySelector(".toast-close");
    const dismiss = () => {
      toast.classList.add("toast-hiding");
      setTimeout(() => toast.remove(), 250);
    };

    closeBtn.addEventListener("click", dismiss);

    if (duration > 0) {
      const bar = toast.querySelector(".toast-bar");
      if (bar) {
        bar.style.transition = `width ${duration}ms linear`;
        requestAnimationFrame(() => {
          bar.style.width = "0%";
        });
      }
      setTimeout(dismiss, duration);
    }
  },

  setPipelineProgress(percent, message, isError = false) {
    const banner = document.getElementById("pipelineBanner");
    const bar = document.getElementById("pipelineProgressBar");
    const percentEl = document.getElementById("pipelinePercent");
    const textEl = document.getElementById("pipelineStatusText");
    const subtextEl = document.getElementById("pipelineSubtext");
    const pulse = document.getElementById("pipelinePulse");

    if (this.progressHideTimeout) {
      clearTimeout(this.progressHideTimeout);
      this.progressHideTimeout = null;
    }

    const clamped = Math.max(0, Math.min(100, Math.round(percent)));

    // Visibility rule: Visible ONLY when something is running or alert; hidden when idle (0)
    if (banner) {
      if (clamped > 0 || isError) {
        banner.style.display = "block";
      } else {
        banner.style.display = "none";
      }
    }

    if (bar) {
      bar.style.width = `${clamped}%`;
    }

    if (percentEl) percentEl.innerText = `${clamped}%`;

    if (pulse) {
      pulse.classList.remove("running", "error");
      if (isError) {
        pulse.classList.add("error");
      } else if (clamped > 0 && clamped < 100) {
        pulse.classList.add("running");
      }
    }

    if (textEl) {
      if (isError) textEl.innerText = "Alerta na Pipeline";
      else if (clamped === 100) textEl.innerText = "Operação Concluída";
      else if (clamped > 0) textEl.innerText = "Buscando & Avaliando Oportunidades";
      else textEl.innerText = "Pipeline Pronta";
    }

    if (subtextEl && message) {
      subtextEl.innerText = message;
    }

    // Auto-hide when reaching 100% after 2 seconds
    if (clamped === 100 && banner && !isError) {
      this.progressHideTimeout = setTimeout(() => {
        banner.style.display = "none";
        if (bar) bar.style.width = "0%";
        if (percentEl) percentEl.innerText = "0%";
      }, 2000);
    }
  },

  async updateKPIs(applications = null) {
    try {
      if (!applications) {
        const appRes = await API.getApplications();
        applications = appRes.applications || [];
      }

      const totalApps = applications.length;
      const readyResumes = applications.filter((a) => !!a.cv_pdf_path).length;
      const activeApps = applications.filter((a) => a.status !== "rejected").length;

      let compliantCount = 0;
      applications.forEach((a) => {
        if (a.job && a.job.is_iad_compliant) compliantCount++;
      });
      const complianceRate = totalApps > 0 ? Math.round((compliantCount / totalApps) * 100) : 100;

      const jobsRes = await API.getJobs();
      const totalJobs = jobsRes.total || totalApps;

      const elTotal = document.getElementById("kpiTotalJobs");
      const elRate = document.getElementById("kpiComplianceRate");
      const elActive = document.getElementById("kpiActiveApps");
      const elResumes = document.getElementById("kpiResumesReady");

      if (elTotal) elTotal.innerText = totalJobs;
      if (elRate) elRate.innerText = `${complianceRate}%`;
      if (elActive) elActive.innerText = activeApps;
      if (elResumes) elResumes.innerText = readyResumes;
    } catch (err) {
      console.warn("Failed to update KPIs:", err);
    }
  },

  async refreshAll() {
    UI.setPipelineProgress(30, "Sincronizando estado com o ledger canônico...");
    await Promise.allSettled([
      Kanban.loadApplications(),
      Doubts.loadDoubts(),
      loadColdOutreach(),
      UI.updateKPIs(),
    ]);
    UI.setPipelineProgress(100, "Dashboard sincronizado com data/status-log.tsv.");
  },

  startScrapingMonitor() {
    if (this.activePollInterval) clearInterval(this.activePollInterval);

    this.activePollInterval = setInterval(async () => {
      try {
        const state = await API.getScrapeStatus();
        if (!state) return;

        this.setPipelineProgress(state.progress, state.message, state.step === "error");

        if (!state.is_running) {
          clearInterval(this.activePollInterval);
          this.activePollInterval = null;

          const btnScrape = document.getElementById("btnScrape");
          if (btnScrape) {
            btnScrape.disabled = false;
            btnScrape.innerHTML = `
              <svg width="15" height="15" viewBox="0 0 24 24" fill="currentColor"><polygon points="5 3 19 12 5 21 5 3"></polygon></svg>
              <span>Iniciar Busca Automática</span>
            `;
          }

          if (state.step === "completed") {
            this.showToast(state.message, "success", 7000);
            await Kanban.loadApplications();
            await Doubts.loadDoubts();
            await this.updateKPIs();
          } else if (state.step === "error") {
            this.showToast(`Problema na busca: ${state.error}`, "error", 8000);
          }
        }
      } catch (err) {
        console.error("Monitor poll error:", err);
      }
    }, 2000);
  },
};

// ==========================================================================
// Theme Management (Light by Default, Dark togglable)
// ==========================================================================

function initTheme() {
  const savedTheme = localStorage.getItem("stage_theme") || "light";
  document.documentElement.setAttribute("data-theme", savedTheme);
  updateThemeButton(savedTheme);

  const btnTheme = document.getElementById("btnThemeToggle");
  if (btnTheme) {
    btnTheme.addEventListener("click", () => {
      const current = document.documentElement.getAttribute("data-theme") || "light";
      const nextTheme = current === "light" ? "dark" : "light";
      document.documentElement.setAttribute("data-theme", nextTheme);
      localStorage.setItem("stage_theme", nextTheme);
      updateThemeButton(nextTheme);
      if (window.UI) {
        window.UI.showToast(`Modo ${nextTheme === "light" ? "Claro" : "Escuro"} ativado`, "info", 2000);
      }
    });
  }
}

function updateThemeButton(theme) {
  const icon = document.getElementById("themeIcon");
  const label = document.getElementById("themeLabel");
  if (icon && label) {
    if (theme === "light") {
      icon.innerText = "☀️";
      label.innerText = "Claro";
    } else {
      icon.innerText = "🌙";
      label.innerText = "Escuro";
    }
  }
}

// ==========================================================================
// Document Ready & Event Bindings
// ==========================================================================

document.addEventListener("DOMContentLoaded", () => {
  // 1. Initialize Theme (Light by default)
  initTheme();

  // 2. Navigation Tabs
  const tabBtns = document.querySelectorAll(".tabs-nav .tab-btn");
  tabBtns.forEach((btn) => {
    btn.addEventListener("click", () => {
      tabBtns.forEach((b) => b.classList.remove("active"));
      document.querySelectorAll(".workspace .tab-pane").forEach((p) => p.classList.remove("active"));

      btn.classList.add("active");
      const targetPane = document.getElementById(btn.dataset.tab);
      if (targetPane) targetPane.classList.add("active");

      if (btn.dataset.tab === "doubtsTab") Doubts.loadDoubts();
      if (btn.dataset.tab === "coldTab") loadColdOutreach();
    });
  });

  // 3. Mode Toggle
  const semiAutoBtn = document.getElementById("modeSemiAuto");
  const autoBtn = document.getElementById("modeAuto");

  if (semiAutoBtn && autoBtn) {
    semiAutoBtn.addEventListener("click", () => {
      semiAutoBtn.classList.add("active");
      autoBtn.classList.remove("active");
      UI.showToast("Modo Semi-Auto: O robô prepara candidaturas e solicita sua aprovação.", "info", 3500);
    });

    autoBtn.addEventListener("click", () => {
      autoBtn.classList.add("active");
      semiAutoBtn.classList.remove("active");
      UI.showToast("Modo Autônomo: Processamento e compilação de ponta a ponta.", "warning", 3500);
    });
  }

  // 4. Global Sync Button
  const btnRefresh = document.getElementById("btnRefreshAll");
  if (btnRefresh) {
    btnRefresh.addEventListener("click", async () => {
      btnRefresh.disabled = true;
      await UI.refreshAll();
      btnRefresh.disabled = false;
      UI.showToast("Dashboard sincronizado com os arquivos canônicos.", "success", 3000);
    });
  }

  // 5. Trigger Scraping Action (Play Button)
  const btnScrape = document.getElementById("btnScrape");
  if (btnScrape) {
    btnScrape.addEventListener("click", async () => {
      btnScrape.disabled = true;
      btnScrape.innerHTML = `
        <span style="display:inline-block; animation: spin 1s infinite linear;">⟳</span>
        <span>Buscando Vagas...</span>
      `;
      UI.setPipelineProgress(10, "Iniciando raspagem no LinkedIn e Welcome to the Jungle...");
      UI.showToast("Busca de vagas iniciada em segundo plano. Acompanhe a pipeline...", "info", 4000);

      try {
        const res = await API.triggerScrape();
        if (res.status === "already_running") {
          UI.showToast("Uma busca já está em andamento. Monitorando progresso...", "warning", 4000);
        }
        UI.startScrapingMonitor();
      } catch (err) {
        btnScrape.disabled = false;
        btnScrape.innerHTML = `
          <svg width="15" height="15" viewBox="0 0 24 24" fill="currentColor"><polygon points="5 3 19 12 5 21 5 3"></polygon></svg>
          <span>Iniciar Busca Automática</span>
        `;
        UI.setPipelineProgress(100, `Falha ao iniciar: ${err.message}`, true);
        UI.showToast(`Falha ao iniciar busca: ${err.message}`, "error", 6000);
      }
    });
  }

  // 6. Generate Cold Outreach Report
  const btnCold = document.getElementById("btnGenColdReport");
  if (btnCold) {
    btnCold.addEventListener("click", async () => {
      btnCold.disabled = true;
      UI.setPipelineProgress(50, "Sintetizando dossiê de prospecção fria...");
      UI.showToast("Gerando dossiê de prospecção fria...", "info", 3000);

      try {
        await API.generateColdReport();
        UI.setPipelineProgress(100, "Dossiê de Cold Outreach gerado!");
        UI.showToast("Dossiê compilado com sucesso!", "success", 6000);
        await loadColdOutreach();
      } catch (err) {
        UI.setPipelineProgress(100, `Falha na geração: ${err.message}`, true);
        UI.showToast(`Falha: ${err.message}`, "error", 6000);
      } finally {
        btnCold.disabled = false;
      }
    });
  }

  // 7. Clear Logs Terminal
  const btnClearLogs = document.getElementById("btnClearLogs");
  if (btnClearLogs) {
    btnClearLogs.addEventListener("click", () => {
      const terminal = document.getElementById("logTerminal");
      if (terminal) terminal.innerText = "=== Terminal limpo pelo usuário ===\n";
    });
  }

  // 8. Connect WebSocket Terminal Logs
  connectLogsWebSocket();

  // 9. Initialize Components and KPIs
  Kanban.init();
  Doubts.loadDoubts();
  UI.updateKPIs();
});

async function loadColdOutreach() {
  const container = document.getElementById("coldList");
  if (!container) return;
  try {
    const data = await API.getColdTargets();
    const targets = data.targets || [];

    container.innerHTML = "";
    if (targets.length === 0) {
      container.innerHTML = `
        <div style="grid-column: 1/-1; padding: 2rem; text-align: center; color: var(--text-muted);">
          Nenhum alvo de cold outreach configurado no momento.
        </div>
      `;
      return;
    }

    targets.forEach((target) => {
      const card = document.createElement("div");
      card.className = "card-box";
      card.innerHTML = `
        <div style="font-size: 0.72rem; color: var(--accent-cyan); font-weight: 700; text-transform: uppercase; margin-bottom: 0.25rem;">
          ${target.ai_domain}
        </div>
        <h3 style="font-size: 1rem; font-weight: 700; margin-bottom: 0.4rem; color: var(--text-main);">${target.company_name}</h3>
        <p style="font-size: 0.8rem; color: var(--text-muted); margin-bottom: 0.6rem;">
          <strong>Stack:</strong> <code>${target.tech_stack || "Python, IA"}</code>
        </p>
        <div style="background: var(--bg-column); padding: 0.6rem; border-radius: 6px; font-size: 0.78rem; margin-bottom: 0.6rem; color: var(--text-secondary);">
          <strong>Abordagem Recomendada:</strong> ${target.recommended_approach}
        </div>
        <a href="${target.website}" target="_blank" class="btn btn-secondary" style="font-size: 0.75rem; padding: 0.3rem 0.6rem;">Visitar Website</a>
      `;
      container.appendChild(card);
    });
  } catch (err) {
    console.warn("Failed to load cold targets:", err);
  }
}

function connectLogsWebSocket() {
  const terminal = document.getElementById("logTerminal");
  if (!terminal) return;

  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  const wsUrl = `${protocol}//${window.location.host}/ws/logs`;

  try {
    const ws = new WebSocket(wsUrl);

    ws.onopen = () => {
      terminal.innerText = "=== Conectado ao Fluxo de Auditoria em Tempo Real ===\n";
    };

    ws.onmessage = (event) => {
      terminal.innerText += event.data;
      terminal.scrollTop = terminal.scrollHeight;
    };

    ws.onclose = () => {
      terminal.innerText += "\n[Conexão encerrada. Reconectando em 4s...]";
      setTimeout(connectLogsWebSocket, 4000);
    };

    ws.onerror = () => {
      terminal.innerText += "\n[Aguardando servidor de logs...]";
    };
  } catch (e) {
    console.warn("WebSocket not supported or failed to connect:", e);
  }
}
