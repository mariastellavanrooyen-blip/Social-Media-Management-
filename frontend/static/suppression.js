const rowsEl = document.getElementById("rows");
const emptyEl = document.getElementById("empty");
const addBtn = document.getElementById("add-btn");
const newEmail = document.getElementById("new-email");
const newReason = document.getElementById("new-reason");
const addError = document.getElementById("add-error");

function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str;
  return div.innerHTML;
}

async function loadEntries() {
  const res = await fetch("/api/suppression");
  const entries = await res.json();

  rowsEl.innerHTML = "";
  emptyEl.style.display = entries.length ? "none" : "block";

  for (const e of entries) {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${escapeHtml(e.email)}</td>
      <td>${escapeHtml(e.reason || "")}</td>
      <td>${new Date(e.created_at).toLocaleDateString()}</td>
      <td><button class="secondary" data-id="${e.id}">Remove</button></td>
    `;
    tr.querySelector("button").addEventListener("click", () => removeEntry(e.id));
    rowsEl.appendChild(tr);
  }
}

async function removeEntry(id) {
  await fetch(`/api/suppression/${id}`, { method: "DELETE" });
  loadEntries();
}

addBtn.addEventListener("click", async () => {
  addError.textContent = "";
  if (!newEmail.value) {
    addError.textContent = "Enter an email address.";
    return;
  }

  const res = await fetch("/api/suppression", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email: newEmail.value, reason: newReason.value || null }),
  });

  if (res.ok) {
    newEmail.value = "";
    newReason.value = "";
    loadEntries();
  } else {
    const err = await res.json();
    addError.textContent = err.detail || "Failed to add.";
  }
});

loadEntries();
