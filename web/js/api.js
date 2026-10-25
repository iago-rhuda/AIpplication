/**
 * API communication helper module for Stage AI Ecosystem with Career-Ops integrations.
 */

const API = {
  async getJobs(compliantOnly = false) {
    const res = await fetch(`/api/jobs?compliant_only=${compliantOnly}`);
    return res.json();
  },

  async triggerScrape(keywords = ["Stage", "Data Scientist", "Machine Learning", "IA"], location = "Paris, Île-de-France, France") {
    const res = await fetch("/api/jobs/scrape", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ keywords, location, limit_per_source: 15 }),
    });
    return res.json();
  },

  async getScrapeStatus() {
    const res = await fetch("/api/jobs/scrape/status");
    return res.json();
  },

  async getApplications(status = null) {
    const url = status ? `/api/applications?status=${status}` : "/api/applications";
    const res = await fetch(url);
    return res.json();
  },

  async getApplication(appId) {
    const res = await fetch(`/api/applications/${appId}`);
    return res.json();
  },

  async updateApplicationStatus(appId, newStatus, notes = null, source = "user") {
    const res = await fetch(`/api/applications/${appId}/status`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ status: newStatus, notes, source }),
    });
    return res.json();
  },

  async addApplicationEvent(appId, notes, source = "user") {
    const res = await fetch(`/api/applications/${appId}/events`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ notes, source }),
    });
    return res.json();
  },

  async triggerEvaluation(appId) {
    const res = await fetch(`/api/applications/${appId}/evaluate`, {
      method: "POST",
    });
    return res.json();
  },

  async getApplicationReport(appId) {
    const res = await fetch(`/api/applications/${appId}/report`);
    return res.text();
  },

  async generateDocuments(appId) {
    const res = await fetch(`/api/applications/${appId}/generate-documents`, {
      method: "POST",
    });
    return res.json();
  },

  async getDoubts() {
    const res = await fetch("/api/doubts");
    return res.json();
  },

  async resolveDoubt(doubtId, userDecision, status = "resolved") {
    const res = await fetch(`/api/doubts/${doubtId}/resolve`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ user_decision: userDecision, status }),
    });
    return res.json();
  },

  async resolveAllDoubts(userDecision = "Approved all by user", status = "resolved") {
    const res = await fetch("/api/doubts/resolve-all", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ user_decision: userDecision, status }),
    });
    return res.json();
  },

  async getColdTargets() {
    const res = await fetch("/api/cold-outreach");
    return res.json();
  },

  async generateColdReport() {
    const res = await fetch("/api/cold-outreach/generate-report", {
      method: "POST",
    });
    return res.json();
  },
};
