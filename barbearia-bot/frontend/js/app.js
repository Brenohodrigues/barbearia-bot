/*
 * Painel administrativo - SPA simples em JS puro (sem build step), pensado
 * para ser fácil de entender e modificar por quem está começando.
 */

if (!Api.getToken()) {
  window.location.href = "/painel/login.html";
}

document.getElementById("logout-btn").addEventListener("click", () => {
  Api.clearToken();
  window.location.href = "/painel/login.html";
});

const VIEW_TITLES = {
  dashboard: "Dashboard",
  agenda: "Agenda",
  clientes: "Clientes",
  servicos: "Serviços",
  barbeiros: "Barbeiros",
};

const STATUS_LABELS = {
  pending: ["Aguardando", "pending"],
  confirmed: ["Confirmado", "confirmed"],
  completed: ["Concluído", "completed"],
  cancelled: ["Cancelado", "cancelled"],
  no_show: ["Não compareceu", "cancelled"],
};

function money(v) {
  return `R$ ${Number(v).toFixed(2).replace(".", ",")}`;
}

function badge(status) {
  const [label, cls] = STATUS_LABELS[status] || [status, ""];
  return `<span class="badge ${cls}">${label}</span>`;
}

document.querySelectorAll(".nav-item[data-view]").forEach((btn) => {
  btn.addEventListener("click", () => navigate(btn.dataset.view));
});

function navigate(view) {
  document.querySelectorAll(".nav-item[data-view]").forEach((b) => {
    b.classList.toggle("active", b.dataset.view === view);
  });
  document.getElementById("view-title").textContent = VIEW_TITLES[view];
  window.location.hash = view;
  RENDERERS[view]();
}

const content = document.getElementById("view-content");

// ---------------------------------------------------------------- Dashboard
async function renderDashboard() {
  content.innerHTML = `<p class="empty-state">Carregando...</p>`;
  const today = new Date().toISOString().slice(0, 10);
  try {
    const [todayAppts, customers, services] = await Promise.all([
      Api.get(`/appointments?date_from=${today}&date_to=${today}`),
      Api.get("/customers"),
      Api.get("/services?include_inactive=true"),
    ]);
    const confirmed = todayAppts.filter((a) => a.status === "confirmed").length;
    const cancelled = todayAppts.filter((a) => a.status === "cancelled").length;

    content.innerHTML = `
      <div class="grid grid-4">
        <div class="card stat"><div class="label">Agendamentos hoje</div><div class="value">${todayAppts.length}</div></div>
        <div class="card stat"><div class="label">Confirmados hoje</div><div class="value">${confirmed}</div></div>
        <div class="card stat"><div class="label">Cancelados hoje</div><div class="value">${cancelled}</div></div>
        <div class="card stat"><div class="label">Total de clientes</div><div class="value">${customers.length}</div></div>
      </div>
      <div class="card">
        <h3>Próximos horários de hoje</h3>
        ${renderApptTable(todayAppts)}
      </div>
    `;
  } catch (err) {
    content.innerHTML = `<p class="error-msg">${err.message}</p>`;
  }
}

function renderApptTable(appts) {
  if (!appts.length) return `<p class="empty-state">Nenhum agendamento.</p>`;
  const rows = appts
    .sort((a, b) => a.starts_at.localeCompare(b.starts_at))
    .map(
      (a) => `<tr>
        <td>${new Date(a.starts_at).toLocaleString("pt-BR")}</td>
        <td>${money(a.price_at_booking)}</td>
        <td>${badge(a.status)}</td>
      </tr>`
    )
    .join("");
  return `<table><thead><tr><th>Data/hora</th><th>Valor</th><th>Status</th></tr></thead><tbody>${rows}</tbody></table>`;
}

// -------------------------------------------------------------------- Agenda
async function renderAgenda() {
  content.innerHTML = `
    <div class="toolbar">
      <input type="date" id="agenda-date" value="${new Date().toISOString().slice(0, 10)}">
      <button class="btn secondary" id="agenda-refresh">Atualizar</button>
    </div>
    <div class="card" id="agenda-table"><p class="empty-state">Carregando...</p></div>
  `;
  document.getElementById("agenda-refresh").addEventListener("click", loadAgenda);
  document.getElementById("agenda-date").addEventListener("change", loadAgenda);
  loadAgenda();
}

async function loadAgenda() {
  const date = document.getElementById("agenda-date").value;
  const target = document.getElementById("agenda-table");
  try {
    const appts = await Api.get(`/appointments?date_from=${date}&date_to=${date}`);
    if (!appts.length) {
      target.innerHTML = `<p class="empty-state">Nenhum agendamento nesta data.</p>`;
      return;
    }
    const rows = appts
      .sort((a, b) => a.starts_at.localeCompare(b.starts_at))
      .map(
        (a) => `<tr>
          <td>${new Date(a.starts_at).toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" })}</td>
          <td>${money(a.price_at_booking)}</td>
          <td>${badge(a.status)}</td>
          <td>
            <select data-id="${a.id}" class="status-select">
              ${Object.keys(STATUS_LABELS)
                .map((s) => `<option value="${s}" ${s === a.status ? "selected" : ""}>${STATUS_LABELS[s][0]}</option>`)
                .join("")}
            </select>
          </td>
        </tr>`
      )
      .join("");
    target.innerHTML = `<table><thead><tr><th>Hora</th><th>Valor</th><th>Status</th><th>Alterar</th></tr></thead><tbody>${rows}</tbody></table>`;

    target.querySelectorAll(".status-select").forEach((sel) => {
      sel.addEventListener("change", async () => {
        try {
          await Api.put(`/appointments/${sel.dataset.id}`, { status: sel.value });
          loadAgenda();
        } catch (err) {
          alert(err.message);
        }
      });
    });
  } catch (err) {
    target.innerHTML = `<p class="error-msg">${err.message}</p>`;
  }
}

// ----------------------------------------------------------------- Clientes
async function renderClientes() {
  content.innerHTML = `
    <div class="toolbar">
      <input type="text" id="cliente-search" placeholder="Buscar por nome ou telefone...">
    </div>
    <div class="card" id="clientes-table"><p class="empty-state">Carregando...</p></div>
  `;
  document.getElementById("cliente-search").addEventListener("input", debounce(loadClientes, 350));
  loadClientes();
}

async function loadClientes() {
  const search = document.getElementById("cliente-search").value;
  const target = document.getElementById("clientes-table");
  try {
    const customers = await Api.get(`/customers${search ? `?search=${encodeURIComponent(search)}` : ""}`);
    if (!customers.length) {
      target.innerHTML = `<p class="empty-state">Nenhum cliente encontrado.</p>`;
      return;
    }
    const rows = customers
      .map(
        (c) => `<tr>
          <td>${c.name || "(sem nome)"}</td>
          <td>${c.phone}</td>
          <td>${c.visits_count}</td>
          <td>${c.last_visit_at ? new Date(c.last_visit_at).toLocaleDateString("pt-BR") : "-"}</td>
          <td>${c.is_blocked ? "🚫 Bloqueado" : "Ativo"}</td>
        </tr>`
      )
      .join("");
    target.innerHTML = `<table><thead><tr><th>Nome</th><th>Telefone</th><th>Atendimentos</th><th>Último atendimento</th><th>Status</th></tr></thead><tbody>${rows}</tbody></table>`;
  } catch (err) {
    target.innerHTML = `<p class="error-msg">${err.message}</p>`;
  }
}

// ----------------------------------------------------------------- Serviços
async function renderServicos() {
  content.innerHTML = `
    <div class="toolbar"><button class="btn" id="new-service-btn">+ Novo serviço</button></div>
    <div class="card" id="servicos-table"><p class="empty-state">Carregando...</p></div>
  `;
  document.getElementById("new-service-btn").addEventListener("click", () => openServiceModal());
  loadServicos();
}

async function loadServicos() {
  const target = document.getElementById("servicos-table");
  try {
    const services = await Api.get("/services?include_inactive=true");
    if (!services.length) {
      target.innerHTML = `<p class="empty-state">Nenhum serviço cadastrado ainda.</p>`;
      return;
    }
    const rows = services
      .map(
        (s) => `<tr>
          <td>${s.name}</td>
          <td>${money(s.price)}</td>
          <td>${s.duration_minutes} min</td>
          <td>${s.is_active ? "Ativo" : "Inativo"}</td>
          <td>
            <button class="btn secondary" data-edit="${s.id}">Editar</button>
            ${s.is_active ? `<button class="btn danger" data-deactivate="${s.id}">Desativar</button>` : ""}
          </td>
        </tr>`
      )
      .join("");
    target.innerHTML = `<table><thead><tr><th>Nome</th><th>Preço</th><th>Duração</th><th>Status</th><th></th></tr></thead><tbody>${rows}</tbody></table>`;

    target.querySelectorAll("[data-edit]").forEach((btn) =>
      btn.addEventListener("click", async () => {
        const service = services.find((s) => s.id === btn.dataset.edit);
        openServiceModal(service);
      })
    );
    target.querySelectorAll("[data-deactivate]").forEach((btn) =>
      btn.addEventListener("click", async () => {
        if (!confirm("Desativar este serviço?")) return;
        await Api.del(`/services/${btn.dataset.deactivate}`);
        loadServicos();
      })
    );
  } catch (err) {
    target.innerHTML = `<p class="error-msg">${err.message}</p>`;
  }
}

function openServiceModal(service) {
  const isEdit = !!service;
  const modal = createModal(`
    <h3>${isEdit ? "Editar" : "Novo"} serviço</h3>
    <form id="service-form">
      <label>Nome</label>
      <input name="name" required value="${service?.name || ""}">
      <label>Descrição</label>
      <textarea name="description">${service?.description || ""}</textarea>
      <label>Preço (R$)</label>
      <input name="price" type="number" step="0.01" min="0.01" required value="${service?.price || ""}">
      <label>Duração (minutos)</label>
      <input name="duration_minutes" type="number" min="1" required value="${service?.duration_minutes || ""}">
      <div class="error-msg hidden" id="service-error"></div>
      <div style="display:flex; gap:8px; justify-content:flex-end">
        <button type="button" class="btn secondary" id="cancel-modal">Cancelar</button>
        <button type="submit" class="btn">Salvar</button>
      </div>
    </form>
  `);

  modal.querySelector("#cancel-modal").addEventListener("click", () => modal.remove());
  modal.querySelector("#service-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const form = new FormData(e.target);
    const payload = {
      name: form.get("name"),
      description: form.get("description") || null,
      price: parseFloat(form.get("price")),
      duration_minutes: parseInt(form.get("duration_minutes"), 10),
      is_active: true,
    };
    try {
      if (isEdit) {
        await Api.put(`/services/${service.id}`, payload);
      } else {
        await Api.post("/services", payload);
      }
      modal.remove();
      loadServicos();
    } catch (err) {
      const errEl = modal.querySelector("#service-error");
      errEl.textContent = err.message;
      errEl.classList.remove("hidden");
    }
  });
}

// ---------------------------------------------------------------- Barbeiros
async function renderBarbeiros() {
  content.innerHTML = `
    <div class="toolbar"><button class="btn" id="new-barber-btn">+ Novo barbeiro</button></div>
    <div class="card" id="barbeiros-table"><p class="empty-state">Carregando...</p></div>
  `;
  document.getElementById("new-barber-btn").addEventListener("click", () => openBarberModal());
  loadBarbeiros();
}

async function loadBarbeiros() {
  const target = document.getElementById("barbeiros-table");
  try {
    const [barbers, services] = await Promise.all([
      Api.get("/barbers?include_inactive=true"),
      Api.get("/services?include_inactive=true"),
    ]);
    if (!barbers.length) {
      target.innerHTML = `<p class="empty-state">Nenhum barbeiro cadastrado ainda.</p>`;
      return;
    }
    const rows = barbers
      .map(
        (b) => `<tr>
          <td>${b.name}</td>
          <td>${b.services.map((s) => s.name).join(", ") || "-"}</td>
          <td>${b.is_active ? "Ativo" : "Inativo"}</td>
          <td>
            <button class="btn secondary" data-edit="${b.id}">Editar</button>
            ${b.is_active ? `<button class="btn danger" data-deactivate="${b.id}">Desativar</button>` : ""}
          </td>
        </tr>`
      )
      .join("");
    target.innerHTML = `<table><thead><tr><th>Nome</th><th>Serviços</th><th>Status</th><th></th></tr></thead><tbody>${rows}</tbody></table>`;

    target.querySelectorAll("[data-edit]").forEach((btn) =>
      btn.addEventListener("click", () => {
        const barber = barbers.find((b) => b.id === btn.dataset.edit);
        openBarberModal(barber, services);
      })
    );
    target.querySelectorAll("[data-deactivate]").forEach((btn) =>
      btn.addEventListener("click", async () => {
        if (!confirm("Desativar este barbeiro?")) return;
        await Api.del(`/barbers/${btn.dataset.deactivate}`);
        loadBarbeiros();
      })
    );
  } catch (err) {
    target.innerHTML = `<p class="error-msg">${err.message}</p>`;
  }
}

function openBarberModal(barber, allServices) {
  const isEdit = !!barber;
  const selectedIds = new Set((barber?.services || []).map((s) => s.id));

  Api.get("/services?include_inactive=true").then((services) => {
    const modal = createModal(`
      <h3>${isEdit ? "Editar" : "Novo"} barbeiro</h3>
      <form id="barber-form">
        <label>Nome</label>
        <input name="name" required value="${barber?.name || ""}">
        <label>Bio (opcional)</label>
        <textarea name="bio">${barber?.bio || ""}</textarea>
        <label>Serviços que realiza</label>
        <div style="margin-bottom:12px">
          ${services
            .map(
              (s) => `<label style="display:flex;align-items:center;gap:8px;font-size:14px;color:var(--text)">
                <input type="checkbox" name="service_ids" value="${s.id}" style="width:auto;margin:0"
                  ${selectedIds.has(s.id) ? "checked" : ""}> ${s.name}
              </label>`
            )
            .join("")}
        </div>
        <div class="error-msg hidden" id="barber-error"></div>
        <div style="display:flex; gap:8px; justify-content:flex-end">
          <button type="button" class="btn secondary" id="cancel-modal">Cancelar</button>
          <button type="submit" class="btn">Salvar</button>
        </div>
      </form>
    `);

    modal.querySelector("#cancel-modal").addEventListener("click", () => modal.remove());
    modal.querySelector("#barber-form").addEventListener("submit", async (e) => {
      e.preventDefault();
      const form = new FormData(e.target);
      const payload = {
        name: form.get("name"),
        bio: form.get("bio") || null,
        is_active: true,
        service_ids: form.getAll("service_ids"),
        working_hours: [],
      };
      try {
        if (isEdit) {
          await Api.put(`/barbers/${barber.id}`, payload);
        } else {
          await Api.post("/barbers", payload);
        }
        modal.remove();
        loadBarbeiros();
      } catch (err) {
        const errEl = modal.querySelector("#barber-error");
        errEl.textContent = err.message;
        errEl.classList.remove("hidden");
      }
    });
  });
}

// ------------------------------------------------------------------- Utils
function createModal(innerHtml) {
  const backdrop = document.createElement("div");
  backdrop.className = "modal-backdrop";
  backdrop.innerHTML = `<div class="modal">${innerHtml}</div>`;
  document.body.appendChild(backdrop);
  return backdrop;
}

function debounce(fn, delay) {
  let timer;
  return (...args) => {
    clearTimeout(timer);
    timer = setTimeout(() => fn(...args), delay);
  };
}

const RENDERERS = {
  dashboard: renderDashboard,
  agenda: renderAgenda,
  clientes: renderClientes,
  servicos: renderServicos,
  barbeiros: renderBarbeiros,
};

const initialView = window.location.hash.replace("#", "") || "dashboard";
navigate(RENDERERS[initialView] ? initialView : "dashboard");
