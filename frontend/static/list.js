const rowsEl = document.getElementById("client-rows");
const emptyEl = document.getElementById("empty");
const searchEl = document.getElementById("search");
const statusEl = document.getElementById("status-filter");
const addBtn = document.getElementById("add-btn");
const addModal = document.getElementById("add-modal");
const addForm = document.getElementById("add-form");
const addError = document.getElementById("add-error");
const cancelAdd = document.getElementById("cancel-add");

let debounceTimer;

async function loadClients() {
  const params = new URLSearchParams();
  if (searchEl.value.trim()) params.set("search", searchEl.value.trim());
  if (statusEl.value) params.set("status", statusEl.value);

  const res = await fetch(`/api/clients?${params.toString()}`);
  const clients = await res.json();

  rowsEl.innerHTML = "";
  emptyEl.style.display = clients.length ? "none" : "block";

  for (const c of clients) {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${escapeHtml(c.name)}</td>
      <td>${escapeHtml(c.email)}</td>
      <td>${escapeHtml(c.company || "")}</td>
      <td><span class="status-pill status-${c.status}">${c.status}</span></td>
      <td>${c.last_contact_date || "—"}</td>
    `;
    tr.addEventListener("click", () => {
      window.location.href = `/client.html?id=${c.id}`;
    });
    rowsEl.appendChild(tr);
  }
}

function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str;
  return div.innerHTML;
}

searchEl.addEventListener("input", () => {
  clearTimeout(debounceTimer);
  debounceTimer = setTimeout(loadClients, 250);
});
statusEl.addEventListener("change", loadClients);

addBtn.addEventListener("click", () => {
  addForm.reset();
  addError.textContent = "";
  addModal.classList.remove("hidden");
});
cancelAdd.addEventListener("click", () => addModal.classList.add("hidden"));
addModal.addEventListener("click", (e) => {
  if (e.target === addModal) addModal.classList.add("hidden");
});

addForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  addError.textContent = "";

  const payload = {
    name: document.getElementById("f-name").value,
    email: document.getElementById("f-email").value,
    company: document.getElementById("f-company").value || null,
    phone: document.getElementById("f-phone").value || null,
    status: document.getElementById("f-status").value,
    notes: document.getElementById("f-notes").value || null,
  };

  const res = await fetch("/api/clients", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  if (res.ok) {
    addModal.classList.add("hidden");
    loadClients();
  } else {
    const err = await res.json();
    addError.textContent = err.detail || "Something went wrong.";
  }
});

loadClients();
