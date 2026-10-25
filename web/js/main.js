/**
 * Main application script initializing tabs, real-time WebSockets, and controls.
 */

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
  });

  autoBtn.addEventListener("click", () => {
    autoBtn.classList.add("active");
    semiAutoBtn.classList.remove("active");
  });

  // 3. Trigger Scraping Action
  const btnScrape = document.getElementById("btnScrape");
  btnScrape.addEventListener("click", async () => {
    btnScrape.disabled = true;
    btnScrape.innerText = "Scraping...";
    try {
      await API.triggerScrape();
      alert("Scraping initiated in background! Check the Live Audit Logs tab for progress.");
    } catch (err) {
      alert(`Scraping failed to launch: ${err.message}`);
    } finally {
      btnScrape.disabled = false;
      btnScrape.innerHTML = `<svg width="16" height="16" fill="currentColor" viewBox="0 0 16 16"><path d="M11.534 7h3.932a.25.25 0 0 1 .192.41l-1.966 2.36a.25.25 0 0 1-.384 0l-1.966-2.36a.25.25 0 0 1 .192-.41zm-11 2h3.932a.25.25 0 0 0 .192-.41L2.692 6.23a.25.25 0 0 0-.384 0L.342 8.59A.25.25 0 0 0 .534 9z"/><path fill-rule="evenodd" d="M8 3c-1.552 0-2.94.707-3.857 1.818a.5.5 0 1 1-.771-.636A6.002 6.002 0 0 1 13.917 7H12.9A5.002 5.002 0 0 0 8 3zM3.1 9a5.002 5.002 0 0 0 8.757 2.182.5.5 0 1 1 .771.636A6.002 6.002 0 0 1 2.083 9H3.1z"/></svg> Scrape Jobs`;
    }
  });

  // 4. Generate Cold Outreach Report
  const btnCold = document.getElementById("btnGenColdReport");
  btnCold.addEventListener("click", async () => {
    btnCold.disabled = true;
    try {
      const res = await API.generateColdReport();
      alert(`Cold Outreach Dossier generated at:\n${res.report_path}`);
      loadColdOutreach();
    } catch (err) {
      alert(`Failed to generate report: ${err.message}`);
    } finally {
      btnCold.disabled = false;
    }
  });

  // 5. Initialize Live WebSocket Terminal Logs
  connectLogsWebSocket();

  // 6. Initialize Components
  Kanban.init();
  Doubts.loadDoubts();
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
