const TARGET_FIELDS = [
  { key: "email", label: "Email *" },
  { key: "name", label: "Name" },
  { key: "company", label: "Company" },
  { key: "phone", label: "Phone" },
];

let uploadId = null;
let uploadColumns = [];

const fileInput = document.getElementById("file-input");
const uploadBtn = document.getElementById("upload-btn");
const uploadError = document.getElementById("upload-error");
const uploadSummary = document.getElementById("upload-summary");

const mappingStep = document.getElementById("mapping-step");
const mappingGrid = document.getElementById("mapping-grid");
const mappingError = document.getElementById("mapping-error");

const templateStep = document.getElementById("template-step");
const tplSubject = document.getElementById("tpl-subject");
const tplBody = document.getElementById("tpl-body");
const saveTemplateBtn = document.getElementById("save-template-btn");
const previewBtn = document.getElementById("preview-btn");
const templateError = document.getElementById("template-error");

const previewStep = document.getElementById("preview-step");
const unknownFieldsEl = document.getElementById("unknown-fields");
const samplesEl = document.getElementById("samples");

const sendStep = document.getElementById("send-step");
const sendBtn = document.getElementById("send-btn");
const sendError = document.getElementById("send-error");
const sendProgress = document.getElementById("send-progress");
const progressFill = document.getElementById("progress-fill");
const gmailBadge = document.getElementById("gmail-badge");

function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str;
  return div.innerHTML;
}

async function checkGmailStatus() {
  const res = await fetch("/api/gmail/status");
  const { connected } = await res.json();
  gmailBadge.textContent = connected ? "Gmail connected" : "Gmail not connected";
  gmailBadge.className = `badge ${connected ? "badge-connected" : "badge-disconnected"}`;
}

async function loadTemplate() {
  const res = await fetch("/api/template");
  const tpl = await res.json();
  tplSubject.value = tpl.subject || "";
  tplBody.value = tpl.body || "";
}

function guessColumn(fieldKey, columns) {
  const match = columns.find((c) => c.trim().toLowerCase() === fieldKey);
  return match || "";
}

function renderMappingGrid() {
  mappingGrid.innerHTML = "";
  for (const field of TARGET_FIELDS) {
    const label = document.createElement("label");
    label.textContent = field.label;

    const select = document.createElement("select");
    select.id = `map-${field.key}`;
    select.innerHTML = `<option value="">-- none --</option>` +
      uploadColumns.map((c) => `<option value="${escapeHtml(c)}">${escapeHtml(c)}</option>`).join("");
    select.value = guessColumn(field.key, uploadColumns);

    mappingGrid.appendChild(label);
    mappingGrid.appendChild(select);
  }
}

function getMapping() {
  const mapping = {};
  for (const field of TARGET_FIELDS) {
    const value = document.getElementById(`map-${field.key}`).value;
    if (value) mapping[field.key] = value;
  }
  return mapping;
}

uploadBtn.addEventListener("click", async () => {
  uploadError.textContent = "";
  if (!fileInput.files.length) {
    uploadError.textContent = "Choose a .csv or .xlsx file first.";
    return;
  }

  const formData = new FormData();
  formData.append("file", fileInput.files[0]);

  const res = await fetch("/api/upload", { method: "POST", body: formData });
  if (!res.ok) {
    const err = await res.json();
    uploadError.textContent = err.detail || "Upload failed.";
    return;
  }

  const data = await res.json();
  uploadId = data.upload_id;
  uploadColumns = data.columns;
  uploadSummary.textContent = `${data.row_count} rows, columns: ${data.columns.join(", ")}`;

  renderMappingGrid();
  mappingStep.style.display = "block";
  templateStep.style.display = "block";
  previewStep.style.display = "none";
  sendStep.style.display = "none";
});

saveTemplateBtn.addEventListener("click", async () => {
  templateError.textContent = "";
  const res = await fetch("/api/template", {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ subject: tplSubject.value, body: tplBody.value }),
  });
  if (!res.ok) {
    templateError.textContent = "Failed to save template.";
  }
});

previewBtn.addEventListener("click", async () => {
  templateError.textContent = "";
  mappingError.textContent = "";
  const mapping = getMapping();
  if (!mapping.email) {
    mappingError.textContent = "Map a column to Email before previewing.";
    return;
  }

  const res = await fetch(`/api/upload/${uploadId}/preview`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      mapping,
      subject: tplSubject.value,
      body: tplBody.value,
      sample_size: 3,
    }),
  });

  if (!res.ok) {
    const err = await res.json();
    templateError.textContent = err.detail || "Preview failed.";
    return;
  }

  const data = await res.json();
  unknownFieldsEl.textContent = data.unknown_fields.length
    ? `Unknown merge fields (will render blank): ${data.unknown_fields.join(", ")}`
    : "";

  samplesEl.innerHTML = data.items.map((item) => `
    <div class="sample">
      <div class="subject">To: ${escapeHtml(item.recipient_email)}${item.is_suppressed ? ' <span class="status-pill status-closed">suppressed — will be skipped</span>' : ""}</div>
      <div class="subject">Subject: ${escapeHtml(item.subject)}</div>
      <div class="body">${escapeHtml(item.body)}</div>
    </div>
  `).join("") || '<p class="meta">No rows to preview.</p>';

  previewStep.style.display = "block";
  sendStep.style.display = "block";
});

let pollTimer = null;

function renderJobStatus(job) {
  sendProgress.style.display = "block";
  const donePortion = job.sent + job.failed + job.skipped_suppressed + job.skipped_invalid;
  const pct = job.total ? Math.round((donePortion / job.total) * 100) : 0;
  progressFill.style.width = `${pct}%`;

  document.getElementById("stat-status").textContent = `Status: ${job.status}`;
  document.getElementById("stat-sent").textContent = `Sent: ${job.sent}`;
  document.getElementById("stat-failed").textContent = `Failed: ${job.failed}`;
  document.getElementById("stat-skipped-suppressed").textContent = `Skipped (suppressed): ${job.skipped_suppressed}`;
  document.getElementById("stat-skipped-invalid").textContent = `Skipped (invalid): ${job.skipped_invalid}`;

  if (job.status !== "running") {
    clearInterval(pollTimer);
    sendBtn.disabled = false;
    if (job.error) sendError.textContent = job.error;
  }
}

sendBtn.addEventListener("click", async () => {
  sendError.textContent = "";
  const mapping = getMapping();
  if (!mapping.email) {
    sendError.textContent = "Map a column to Email before sending.";
    return;
  }
  if (!confirm("Start sending? This will email every row in the uploaded sheet (minus suppressed addresses).")) {
    return;
  }

  sendBtn.disabled = true;
  const res = await fetch("/api/send/start", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      upload_id: uploadId,
      mapping,
      subject: tplSubject.value,
      body: tplBody.value,
    }),
  });

  if (!res.ok) {
    const err = await res.json();
    sendError.textContent = err.detail || "Failed to start send.";
    sendBtn.disabled = false;
    return;
  }

  let job = await res.json();
  renderJobStatus(job);

  pollTimer = setInterval(async () => {
    const jobRes = await fetch(`/api/send/jobs/${job.job_id}`);
    if (jobRes.ok) {
      job = await jobRes.json();
      renderJobStatus(job);
    }
  }, 1500);
});

checkGmailStatus();
loadTemplate();
