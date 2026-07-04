const clientId = new URLSearchParams(window.location.search).get("id");

const form = document.getElementById("detail-form");
const metaEl = document.getElementById("meta");
const errorEl = document.getElementById("error");
const deleteBtn = document.getElementById("delete-btn");

if (!clientId) {
  window.location.href = "/index.html";
}

async function loadClient() {
  const res = await fetch(`/api/clients/${clientId}`);
  if (!res.ok) {
    errorEl.textContent = "Client not found.";
    return;
  }
  const c = await res.json();

  document.getElementById("f-name").value = c.name;
  document.getElementById("f-email").value = c.email;
  document.getElementById("f-company").value = c.company || "";
  document.getElementById("f-phone").value = c.phone || "";
  document.getElementById("f-status").value = c.status;
  document.getElementById("f-last-contact").value = c.last_contact_date || "";
  document.getElementById("f-notes").value = c.notes || "";

  const created = new Date(c.created_at).toLocaleString();
  metaEl.textContent = `Client since ${created}`;
}

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  errorEl.textContent = "";

  const payload = {
    name: document.getElementById("f-name").value,
    email: document.getElementById("f-email").value,
    company: document.getElementById("f-company").value || null,
    phone: document.getElementById("f-phone").value || null,
    status: document.getElementById("f-status").value,
    last_contact_date: document.getElementById("f-last-contact").value || null,
    notes: document.getElementById("f-notes").value || null,
  };

  const res = await fetch(`/api/clients/${clientId}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  if (res.ok) {
    loadClient();
  } else {
    const err = await res.json();
    errorEl.textContent = err.detail || "Something went wrong.";
  }
});

deleteBtn.addEventListener("click", async () => {
  if (!confirm("Delete this client? This cannot be undone.")) return;
  const res = await fetch(`/api/clients/${clientId}`, { method: "DELETE" });
  if (res.ok) {
    window.location.href = "/index.html";
  } else {
    errorEl.textContent = "Failed to delete client.";
  }
});

loadClient();
