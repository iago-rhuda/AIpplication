/**
 * Human-in-the-Loop doubts queue management.
 */

const Doubts = {
  async loadDoubts() {
    const data = await API.getDoubts();
    const doubts = data.doubts || [];

    const badge = document.getElementById("doubtsBadge");
    if (badge) badge.innerText = doubts.length;

    const container = document.getElementById("doubtsList");
    if (!container) return;
    container.innerHTML = "";

    if (doubts.length === 0) {
      container.innerHTML = `
        <div style="grid-column: 1/-1; padding: 2rem; text-align: center; color: var(--text-muted);">
          No pending doubts or human approval items. System is operating autonomously.
        </div>
      `;
      return;
    }

    doubts.forEach((doubt) => {
      const box = document.createElement("div");
      box.className = "card-box";
      box.innerHTML = `
        <div style="font-size: 0.75rem; color: var(--accent-amber); font-weight: 700; text-transform: uppercase; margin-bottom: 0.5rem;">
          ${doubt.doubt_type.replace("_", " ")}
        </div>
        <p style="font-size: 0.95rem; font-weight: 600; margin-bottom: 0.75rem;">
          ${doubt.question_text}
        </p>
        <div style="background: rgba(0,0,0,0.3); padding: 0.75rem; border-radius: var(--radius-sm); margin-bottom: 1rem; font-size: 0.85rem; color: var(--text-muted);">
          <strong>Suggested Decision:</strong> ${doubt.suggested_answer || "None provided"}
        </div>
        <div style="display: flex; gap: 0.5rem;">
          <button class="btn btn-resolve" style="background: var(--accent-green); font-size: 0.75rem; padding: 0.4rem 0.8rem;">
            Approve & Proceed
          </button>
          <button class="btn btn-secondary btn-reject" style="font-size: 0.75rem; padding: 0.4rem 0.8rem;">
            Dismiss / Reject
          </button>
        </div>
      `;

      box.querySelector(".btn-resolve").addEventListener("click", async () => {
        try {
          await API.resolveDoubt(doubt.id, "Approved by user in web interface");
          if (window.UI) window.UI.showToast("Doubt approved! Candidate application unlocked.", "success", 4000);
          await Doubts.loadDoubts();
          if (window.Kanban) await window.Kanban.loadApplications();
        } catch (err) {
          if (window.UI) window.UI.showToast(`Error resolving doubt: ${err.message}`, "error", 5000);
        }
      });

      box.querySelector(".btn-reject").addEventListener("click", async () => {
        try {
          await API.resolveDoubt(doubt.id, "Rejected by user", "ignored");
          if (window.UI) window.UI.showToast("Doubt dismissed/ignored.", "info", 4000);
          await Doubts.loadDoubts();
        } catch (err) {
          if (window.UI) window.UI.showToast(`Error rejecting doubt: ${err.message}`, "error", 5000);
        }
      });

      container.appendChild(box);
    });

    const kpiDoubts = document.getElementById("kpiDoubtsCount");
    if (kpiDoubts) kpiDoubts.innerText = doubts.length;
  },
};
