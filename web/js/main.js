/**
 * Main application script initializing tabs, real-time WebSockets, progress bars, and controls.
 */

const UI = {
  activePollInterval: null,

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
      actionsHtml = `<div class="toast-actions">` +
        actions.map(a => `<a href="${a.url}" target="_blank" class="toast-action-btn">${a.label}</a>`).join("") +
        `</div>`;
    }

    toast.innerHTML = `
      <div class="toast-row">
        <span class="toast-icon">${icons[type] || "•"}</span>
        <div class="toast-content">
          <div class="toast-title">${title}</div>
          ${actionsHtml}
        </div>
        <button class="toast-close" title="Dismiss">&times;</button>
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
    const bar = document.getElementById("pipelineProgressBar");
    const percentEl = document.getElementById("pipelinePercent");
    const textEl = document.getElementById("pipelineStatusText");
    const subtextEl = document.getElementById("pipelineSubtext");
    const pulse = document.getElementById("pipelinePulse");

    const clamped = Math.max(0, Math.min(100, Math.round(percent)));

    if (bar) {
      bar.style.width = `${clamped}%`;
      if (clamped > 0 && clamped < 100) {
        bar.classList.add("active");
      } else {
        bar.classList.remove("active");
      }
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
      if (isError) textEl.innerText = "Pipeline Alert";
      else if (clamped === 100) textEl.innerText = "Operation Completed";
      else if (clamped > 0) textEl.innerText = "Task in Progress";
      else textEl.innerText = "Pipeline Idle";
    }

    if (subtextEl && message) {
      subtextEl.innerText = message;
    }
  },

  async updateKPIs(applications = null) {
    try {
      if (!applications) {
        const appRes = await API.getApplications();
        applications = appRes.applications || [];
      }

      const totalApps = applications.length;
      const readyResumes = applications.filter(a => !!a.cv_pdf_path).length;
      const activeApps = applications.filter(a => a.status !== "rejected").length;

      // Calculate average compliance score or rate
      let compliantCount = 0;
      applications.forEach(a => {
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
    UI.setPipelineProgress(30, "Syncing pipeline state with database...");
    await Promise.allSettled([
      Kanban.loadApplications(),
      Doubts.loadDoubts(),
      loadColdOutreach(),
      UI.updateKPIs(),
    ]);
    UI.setPipelineProgress(100, "Dashboard synced & up-to-date.");
    setTimeout(() => {
      UI.setPipelineProgress(0, "Pipeline ready for next task.");
    }, 2000);
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
            btnScrape.innerHTML = `<svg width="16" height="16" fill="currentColor" viewBox="0 0 16 16"><path d="M11.534 7h3.932a.25.25 0 0 1 .192.41l-1.966 2.36a.25.25 0 0 1-.384 0l-1.966-2.36a.25.25 0 0 1 .192-.41zm-11 2h3.932a.25.25 0 0 0 .192-.41L2.692 6.23a.25.25 0 0 0-.384 0L.342 8.59A.25.25 0 0 0 .534 9z"/><path fill-rule="evenodd" d="M8 3c-1.552 0-2.94.707-3.857 1.818a.5.5 0 1 1-.771-.636A6.002 6.002 0 0 1 13.917 7H12.9A5.002 5.002 0 0 0 8 3zM3.1 9a5.002 5.002 0 0 0 8.757 2.182.5.5 0 1 1 .771.636A6.002 6.002 0 0 1 2.083 9H3.1z"/></svg> Scrape Jobs`;
          }

          if (state.step === "completed") {
            this.showToast(state.message, "success", 7000);
            await Kanban.loadApplications();
            await Doubts.loadDoubts();
            await this.updateKPIs();
          } else if (state.step === "error") {
            this.showToast(`Scraping issue: ${state.error}`, "error", 8000);
          }
        }
      } catch (err) {
        console.warn("Polling error:", err);
      }
    }, 1500);
  },
};

window.UI = UI;

document.addEventListener("DOMContentLoaded", () => {
  // 1. Initialize Tabs
  const tabButtons = document.querySelectorAll(".tab-btn");
  const tabPanes = document.querySelectorAll(".tab-pane");

  tabButtons.forEach((btn) => {
    btn.addEventListener("click", () => {
      tabButtons.forEach((b) => b.classList.remove("active"));
      tabPanes.forEach((p) => p.classList.remove("active"));

      btn.classList.add("active");
      const targetPane = document.getElementById(btn.dataset.tab);
      if (targetPane) targetPane.classList.add("active");

      if (btn.dataset.tab === "doubtsTab") Doubts.loadDoubts();
      if (btn.dataset.tab === "coldTab") loadColdOutreach();
    });
  });

  // 2. Initialize Mode Toggle
  const semiAutoBtn = document.getElementById("modeSemiAuto");
  const autoBtn = document.getElementById("modeAuto");

  semiAutoBtn.addEventListener("click", () => {
    semiAutoBtn.classList.add("active");
    autoBtn.classList.remove("active");
    UI.showToast("Switched to Semi-Auto mode: AI prepares resumes and waits for your confirmation.", "info", 3500);
  });

  autoBtn.addEventListener("click", () => {
    autoBtn.classList.add("active");
    semiAutoBtn.classList.remove("active");
    UI.showToast("Switched to Autonomous mode: End-to-end auto-compilation enabled.", "warning", 3500);
  });

  // 3. Global Sync Button
  const btnRefresh = document.getElementById("btnRefreshAll");
  if (btnRefresh) {
    btnRefresh.addEventListener("click", async () => {
      btnRefresh.disabled = true;
      await UI.refreshAll();
      btnRefresh.disabled = false;
      UI.showToast("Dashboard synchronized with database.", "success", 3000);
    });
  }

  // 4. Trigger Scraping Action
  const btnScrape = document.getElementById("btnScrape");
  btnScrape.addEventListener("click", async () => {
    btnScrape.disabled = true;
    btnScrape.innerHTML = `<span style="display:inline-block; animation: spin 1s infinite linear;">⟳</span> Scraping...`;
    UI.setPipelineProgress(10, "Initiating stealth browser scraper (LinkedIn & WTTJ)...");
    UI.showToast("Job prospecting launched in background. Streaming updates...", "info", 4000);

    try {
      const res = await API.triggerScrape();
      if (res.status === "already_running") {
        UI.showToast("Scraping is already in progress. Following current task...", "warning", 4000);
      }
      UI.startScrapingMonitor();
    } catch (err) {
      btnScrape.disabled = false;
      btnScrape.innerHTML = `<svg width="16" height="16" fill="currentColor" viewBox="0 0 16 16"><path d="M11.534 7h3.932a.25.25 0 0 1 .192.41l-1.966 2.36a.25.25 0 0 1-.384 0l-1.966-2.36a.25.25 0 0 1 .192-.41zm-11 2h3.932a.25.25 0 0 0 .192-.41L2.692 6.23a.25.25 0 0 0-.384 0L.342 8.59A.25.25 0 0 0 .534 9z"/><path fill-rule="evenodd" d="M8 3c-1.552 0-2.94.707-3.857 1.818a.5.5 0 1 1-.771-.636A6.002 6.002 0 0 1 13.917 7H12.9A5.002 5.002 0 0 0 8 3zM3.1 9a5.002 5.002 0 0 0 8.757 2.182.5.5 0 1 1 .771.636A6.002 6.002 0 0 1 2.083 9H3.1z"/></svg> Scrape Jobs`;
      UI.setPipelineProgress(100, `Failed to launch: ${err.message}`, true);
      UI.showToast(`Scraping launch failed: ${err.message}`, "error", 6000);
    }
  });

  // 5. Generate Cold Outreach Report
  const btnCold = document.getElementById("btnGenColdReport");
  btnCold.addEventListener("click", async () => {
    btnCold.disabled = true;
    UI.setPipelineProgress(50, "Synthesizing speculative outreach dossier...");
    UI.showToast("Generating cold outreach dossier...", "info", 3000);

    try {
      const res = await API.generateColdReport();
      UI.setPipelineProgress(100, "Cold Outreach Dossier generated!");
      UI.showToast(
        `Cold Outreach Dossier compiled!`,
        "success",
        6000
      );
      await loadColdOutreach();
    } catch (err) {
      UI.setPipelineProgress(100, `Report generation failed: ${err.message}`, true);
      UI.showToast(`Failed to generate report: ${err.message}`, "error", 6000);
    } finally {
      btnCold.disabled = false;
    }
  });

  // 6. Terminal Clear Action
  const btnClearLogs = document.getElementById("btnClearLogs");
  if (btnClearLogs) {
    btnClearLogs.addEventListener("click", () => {
      const terminal = document.getElementById("logTerminal");
      if (terminal) terminal.innerText = "=== Terminal cleared by user ===\n";
    });
  }

  // 7. Initialize Live WebSocket Terminal Logs
  connectLogsWebSocket();

  // 8. Initialize Components and KPIs
  Kanban.init();
  Doubts.loadDoubts();
  UI.updateKPIs();
});

async function loadColdOutreach() {
  const container = document.getElementById("coldList");
  if (!container) return;
  const data = await API.getColdTargets();
  const targets = data.targets || [];

  container.innerHTML = "";
  targets.forEach((target) => {
    const card = document.createElement("div");
    card.className = "card-box";
    card.innerHTML = `
      <div style="font-size: 0.75rem; color: var(--accent-cyan); font-weight: 700; text-transform: uppercase; margin-bottom: 0.25rem;">
        ${target.ai_domain}
      </div>
      <h3 style="font-size: 1.1rem; margin-bottom: 0.5rem;">${target.company_name}</h3>
      <p style="font-size: 0.85rem; color: var(--text-muted); margin-bottom: 0.75rem;">
        <strong>Stack:</strong> <code>${target.tech_stack || "Python, IA"}</code>
      </p>
      <div style="background: rgba(0,0,0,0.25); padding: 0.6rem; border-radius: var(--radius-sm); font-size: 0.8rem; margin-bottom: 0.75rem;">
        <strong>Recommended Pitch:</strong> ${target.recommended_approach}
      </div>
      <a href="${target.website}" target="_blank" class="card-btn" style="display: inline-block;">Visit Website</a>
    `;
    container.appendChild(card);
  });
}

function connectLogsWebSocket() {
  const terminal = document.getElementById("logTerminal");
  if (!terminal) return;

  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  const wsUrl = `${protocol}//${window.location.host}/ws/logs`;

  const ws = new WebSocket(wsUrl);

  ws.onopen = () => {
    terminal.innerText = "=== Connected to Live Audit Logs Stream ===\n";
  };

  ws.onmessage = (event) => {
    terminal.innerText += event.data;
    terminal.scrollTop = terminal.scrollHeight;
  };

  ws.onclose = () => {
    terminal.innerText += "\n[Connection closed. Reconnecting in 3s...]";
    setTimeout(connectLogsWebSocket, 3000);
  };
}

