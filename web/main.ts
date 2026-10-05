import { acceptInvite, getSettings, getUser, handleAuthCallback, login, logout, onAuthChange, requestPasswordRecovery, signup, updateUser } from "@netlify/identity";
import { baseAmount, bookSchema, collections, currencies, daysBetween, emptyBook, invoiceTotals, money, nextMoves, projectProgress, projectRisk, stages, taskStatuses, today, type Book, type Collection, type RecordData } from "./domain.js";
import { sampleBook, templates } from "./sample.js";

const root = document.querySelector<HTMLDivElement>("#app")!;
const pages: Record<string, [string, string]> = {
  dashboard: ["Ops pulse", "The whole operation. One clear next move."],
  clients: ["Client relationships", "From first conversation to the next opportunity."],
  invoices: ["Invoice ledger", "The work is done. Make the money move."],
  finance: ["Financial position", "Cash collected, cash waiting, and the gap ahead."],
  projects: ["Project control", "Protect the deadline. Keep the scope honest."],
  comms: ["Client communications", "Confident. Cinematic. Direct. Nothing sends itself."],
  settings: ["Your operations book", "Your agency, your defaults, your data."],
};
let book: Book | null = null;
let revision = 0;
let page = "dashboard";
let demo = false;
let saving = false;
let search = "";
let account = "";
let authMode = "login";
let allowSignup = false;
let inviteToken = "";
let draft = "";
let draftClient = "";
let templateName = "lead_followup";
let templateLanguage = "en";

function escape(value: unknown): string {
  return String(value ?? "").replace(/[&<>"']/g, (character) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[character]!);
}
function button(label: string, action: string, data = "", style = "") {
  return `<button class="${style}" data-action="${action}" data-id="${escape(data)}">${escape(label)}</button>`;
}
function badge(label: string) {
  const tone = /overdue|Critical|Blocked/.test(label) ? "danger" : /paid|Done|Delivered|On Track|Approved/.test(label) ? "good" : "neutral";
  return `<span class="badge ${tone}">${escape(label)}</span>`;
}
function notify(message: string, error = false) {
  document.querySelector(".toast")?.remove();
  const toast = document.createElement("div");
  toast.className = `toast ${error ? "error" : ""}`;
  toast.setAttribute("role", error ? "alert" : "status");
  toast.textContent = message;
  document.body.append(toast);
  setTimeout(() => toast.remove(), error ? 15000 : 6000);
}
function filtered(records: RecordData[]) {
  return records.filter((record) => JSON.stringify(record).toLowerCase().includes(search.toLowerCase()));
}
function clientName(id?: string) {
  const client = book?.clients.find((record) => record.id === id);
  return client?.company ?? client?.name ?? "Unassigned";
}
function blank(message: string, detail = "Use the add button to get started.") {
  return `<div class="empty"><span class="eyebrow">A clear desk</span><h3>${escape(message)}</h3><p>${escape(detail)}</p></div>`;
}
function table(headers: string[], rows: string[][]) {
  if (!rows.length) return blank("Nothing here yet", search ? "No records match your search." : "Add a record to start your book.");
  return `<div class="table-wrap"><table><thead><tr>${headers.map((header) => `<th>${escape(header)}</th>`).join("")}</tr></thead><tbody>${rows.map((row) => `<tr>${row.map((cell) => `<td>${cell}</td>`).join("")}</tr>`).join("")}</tbody></table></div>`;
}
function stats() {
  const current = book!;
  const base = current.settings.agency.base_currency;
  const invoices = current.invoices.filter((invoice) => invoice.status !== "void");
  const collected = invoices.reduce((sum, invoice) => sum + (invoice.payments ?? []).filter((payment) => payment.date.startsWith(today().slice(0, 7))).reduce((paid, payment) => paid + baseAmount(current, payment.amount, invoice.currency), 0), 0);
  const overdue = invoices.reduce((sum, invoice) => sum + (invoiceTotals(invoice).status === "overdue" ? baseAmount(current, invoiceTotals(invoice).balance, invoice.currency) : 0), 0);
  const outstanding = invoices.filter((invoice) => invoice.status !== "draft").reduce((sum, invoice) => sum + baseAmount(current, invoiceTotals(invoice).balance, invoice.currency), 0);
  const risk = current.projects.filter((project) => ["At Risk", "Critical"].includes(projectRisk(project))).length;
  return { base, collected, overdue, outstanding, risk };
}
function metrics() {
  const pulse = stats();
  return `<section class="metrics"><article><span>Collected this month</span><strong>${money(pulse.collected, pulse.base)}</strong><small>Target ${money(book!.settings.targets.monthly_revenue, pulse.base)}</small></article><article><span>Overdue balance</span><strong class="red">${money(pulse.overdue, pulse.base)}</strong><small>Cash waiting on a decision</small></article><article><span>Active relationships</span><strong>${book!.clients.filter((client) => ["Active", "Upsell"].includes(client.stage ?? "")).length}<em> / ${book!.clients.length}</em></strong><small>Clients in your book</small></article><article><span>Projects at risk</span><strong>${String(pulse.risk).padStart(2, "0")}</strong><small>Of ${book!.projects.length} tracked projects</small></article></section>`;
}
function movesPanel() {
  const moves = nextMoves(book!).slice(0, 2);
  return `<section class="moves"><div><span class="eyebrow">Priority engine</span><h2>Next move <span>↗</span></h2><p>Money at stake × urgency.<br>One relationship. One move.</p></div><div class="move-list">${moves.length ? moves.map((move, index) => `<button class="move" data-action="navigate" data-id="${move.page}"><span class="move-number">0${index + 1}</span><span><strong>${escape(move.title)}</strong><small>${escape(move.reason)}</small></span><span class="arrow">↗</span></button>`).join("") : "<p>No urgent signals. Your next move is to build the pipeline.</p>"}</div></section>`;
}
function dashboard() {
  const pulse = stats();
  const target = book!.settings.targets.monthly_revenue;
  const progress = target > 0 ? Math.min(100, pulse.collected / target * 100) : 0;
  return `${metrics()}${movesPanel()}<div class="dashboard-grid"><section class="panel"><div class="section-heading"><h2>Delivery radar</h2>${button("All projects ↗", "navigate", "projects", "text-button")}</div>${book!.projects.length ? book!.projects.slice(0, 5).map((project) => `<div class="radar"><div><strong>${escape(project.name)}</strong><small>${escape(clientName(project.client_id))} · ${project.due ? `due ${escape(project.due)}` : "no deadline"}</small></div>${badge(projectRisk(project))}<meter min="0" max="100" value="${projectProgress(project)}">${projectProgress(project)}%</meter><span>${projectProgress(project)}%</span></div>`).join("") : blank("No projects in flight")}</section><section class="panel target"><span class="eyebrow">Monthly revenue</span><h2>Close the gap.</h2><strong>${money(Math.max(0, target - pulse.collected), pulse.base)}</strong><p>Remaining to your ${money(target, pulse.base)} target.</p><meter min="0" max="100" value="${progress}">${progress}%</meter><small>${Math.round(progress)}% collected · ${today().slice(0, 7)}</small>${button("Open finance ↗", "navigate", "finance", "text-button")}</section></div>`;
}
function clients() {
  return `<div class="pipeline">${stages.map((stage) => `<div><span>${escape(stage)}</span><strong>${book!.clients.filter((client) => client.stage === stage).length}</strong></div>`).join("")}</div>${table(["Client / company", "Stage", "Deal value", "Last touch", "Next action", ""], filtered(book!.clients).map((client) => {
    const action = client.next_action as { note?: string; due?: string } | undefined;
    return [`<strong>${escape(client.company ?? client.name)}</strong><small>${escape(client.name)} · ${escape(client.email)}</small>`, badge(client.stage ?? "Lead"), money(client.deal_value ?? 0, client.currency), client.last_contact ? `${daysBetween(client.last_contact)}d ago` : "Not logged", `${escape(action?.note ?? "—")}<small>${escape(action?.due)}</small>`, `<div class="row-actions">${button("Edit", "edit:clients", client.id)}${button("Delete", "delete:clients", client.id)}</div>`];
  }))}`;
}
function invoices() {
  return `${table(["Invoice / client", "Status", "Due", "Total", "Balance", "Actions"], filtered(book!.invoices).map((invoice) => {
    const totals = invoiceTotals(invoice);
    return [`<strong>${escape(invoice.id)}</strong><small>${escape(clientName(invoice.client_id))}</small>`, badge(totals.status), escape(invoice.due_date ?? "—"), money(totals.total, invoice.currency), money(totals.balance, invoice.currency), `<div class="row-actions">${button("Edit", "edit:invoices", invoice.id)}${totals.balance > 0 && !["draft", "void"].includes(totals.status) ? button("Payment", "payment", invoice.id) : ""}${button("Download", "invoice-download", invoice.id)}${button("Delete", "delete:invoices", invoice.id)}</div>`];
  }))}<p class="footnote">Invoice status is calculated from due dates and logged payments. Downloads are printable HTML; nothing is emailed automatically.</p>`;
}
function financePage() {
  const current = book!;
  const pulse = stats();
  const aging = ["Current", "1–30", "31–60", "61–90", "90+"];
  const buckets = aging.map((label, index) => {
    const amount = current.invoices.reduce((sum, invoice) => {
      const totals = invoiceTotals(invoice);
      const bucket = totals.late === 0 ? 0 : totals.late <= 30 ? 1 : totals.late <= 60 ? 2 : totals.late <= 90 ? 3 : 4;
      return sum + (bucket === index && !["draft", "void"].includes(totals.status) ? baseAmount(current, totals.balance, invoice.currency) : 0);
    }, 0);
    return `<div class="aging-item"><span>${label} days</span><strong>${money(amount, pulse.base)}</strong></div>`;
  }).join("");
  const probabilities: Record<string, number> = { Lead: .1, Contacted: .25, "Proposal Sent": .5, Upsell: .35 };
  const pipeline = current.clients.reduce((sum, client) => sum + baseAmount(current, client.deal_value ?? 0, client.currency) * (probabilities[client.stage ?? ""] ?? 0), 0);
  return `${metrics()}<section class="panel"><div class="section-heading"><h2>Receivables aging</h2><small>All balances in ${pulse.base}</small></div><div class="aging">${buckets}</div></section><div class="dashboard-grid"><section class="panel"><h2>Collection queue</h2>${table(["Invoice", "Client", "Days late", "Balance"], current.invoices.filter((invoice) => invoiceTotals(invoice).status === "overdue").sort((first, second) => baseAmount(current, invoiceTotals(second).balance * invoiceTotals(second).late, second.currency) - baseAmount(current, invoiceTotals(first).balance * invoiceTotals(first).late, first.currency)).map((invoice) => [escape(invoice.id), escape(clientName(invoice.client_id)), String(invoiceTotals(invoice).late), money(baseAmount(current, invoiceTotals(invoice).balance, invoice.currency), pulse.base)]))}</section><section class="panel target"><span class="eyebrow">Forecast indicators</span><h2>Cash ahead.</h2><strong>${money(pulse.outstanding, pulse.base)}</strong><p>Outstanding issued invoices, not a guarantee of collection.</p><hr><strong>${money(pipeline, pulse.base)}</strong><p>Probability-weighted pipeline. Excludes active and completed deals to avoid counting invoiced revenue twice.</p></section></div>`;
}
function projects() {
  return `<div class="project-list">${filtered(book!.projects).map((project) => `<section class="panel project"><div class="section-heading"><div><span class="eyebrow">${escape(clientName(project.client_id))}</span><h2>${escape(project.name)}</h2></div>${badge(projectRisk(project))}</div><div class="project-meta"><span>Due <b>${escape(project.due ?? "Not set")}</b></span><span>Budget <b>${money(project.budget ?? 0, project.currency)}</b></span><span>Complete <b>${projectProgress(project)}%</b></span></div><meter min="0" max="100" value="${projectProgress(project)}">${projectProgress(project)}%</meter><div class="task-list">${(project.tasks ?? []).map((task, index) => `<label><span>${escape(task.name ?? task.title ?? "Task")}</span><select data-task="${escape(project.id)}" data-index="${index}" ${demo ? "disabled" : ""}>${taskStatuses.map((status) => `<option ${task.status === status ? "selected" : ""}>${status}</option>`).join("")}</select></label>`).join("")}</div>${(project.deliverables ?? []).filter((deliverable) => deliverable.approval?.state === "pending").map((deliverable) => `<p class="approval">Approval pending · ${escape(deliverable.name)} · ${daysBetween(deliverable.approval?.requested)}d waiting</p>`).join("")}<div class="row-actions">${button("Edit project", "edit:projects", project.id)}${button("Log time", "log-time", project.id)}${button("Bill unbilled time", "bill-time", project.id)}${(project.change_orders ?? []).filter((order) => order.status === "Approved").map((order) => button(`Bill ${order.id}`, "bill-change", `${project.id}|${order.id}`)).join("")}</div></section>`).join("") || blank("No projects in flight")}</div>`;
}
function comms() {
  return `<div class="comms-grid"><section class="panel"><span class="eyebrow">Drafting desk</span><h2>Make the next conversation count.</h2><label>Client<select id="draft-client"><option value="">Choose a client</option>${book!.clients.map((client) => `<option value="${escape(client.id)}" ${client.id === draftClient ? "selected" : ""}>${escape(client.company ?? client.name)}</option>`).join("")}</select></label><div class="form-grid"><label>Template<select id="draft-template">${Object.keys(templates).map((name) => `<option value="${name}" ${name === templateName ? "selected" : ""}>${name.replaceAll("_", " ")}</option>`).join("")}</select></label><label>Language<select id="draft-language"><option value="en" ${templateLanguage === "en" ? "selected" : ""}>English</option><option value="es" ${templateLanguage === "es" ? "selected" : ""}>Español</option></select></label></div>${button("Create draft", "generate-draft", "", "primary")}<label>Your editable draft<textarea id="draft-body" rows="16" placeholder="Choose a client and a template. Fill any remaining [placeholders] before sending.">${escape(draft)}</textarea></label><div class="row-actions">${button("Download .txt", "draft-download")}${button("Log as sent", "log-draft")}</div><p class="footnote">You send it from your own inbox. Logging records the conversation; it does not send email.</p></section><section class="panel"><div class="section-heading"><h2>Communication log</h2>${button("Log a touch", "new:messages")}</div>${filtered(book!.messages).sort((first, second) => String(second.date).localeCompare(String(first.date))).slice(0, 30).map((message) => `<article class="message"><span class="eyebrow">${escape(message.date)} · ${escape(message.channel ?? "email")} · ${escape(message.direction ?? "out")}</span><h3>${escape(clientName(message.client_id))}</h3><p>${escape(message.subject ?? message.body ?? "Touch logged").slice(0, 240)}</p>${button("Edit", "edit:messages", message.id)}</article>`).join("") || blank("No conversations logged")}</section></div>`;
}
function settingsPage() {
  const settings = book!.settings;
  return `<div class="dashboard-grid"><section class="panel"><span class="eyebrow">Agency details</span><h2>Built around your operation.</h2><form id="settings-form"><label>Agency name<input name="agency-name" required value="${escape(settings.agency.name)}"></label><label>Owner<input name="owner" value="${escape(settings.agency.owner)}"></label><label>Email<input name="email" type="email" value="${escape(settings.agency.email)}"></label><div class="form-grid"><label>Base currency<select name="currency">${currencies.map((currency) => `<option ${settings.agency.base_currency === currency ? "selected" : ""}>${currency}</option>`).join("")}</select></label><label>Monthly revenue target<input name="target" type="number" min="0" step="0.01" required value="${settings.targets.monthly_revenue}"></label></div><label>FX rates (currency → USD)<textarea name="fx" rows="5" required>${escape(JSON.stringify(settings.fx_rates, null, 2))}</textarea></label><button class="primary" ${demo ? "disabled" : ""}>Save settings</button></form></section><section class="panel"><span class="eyebrow">Your book</span><h2>Take it with you.</h2><p>Each account has a private book stored in Netlify Database. Saves survive deploys and do not depend on a laptop or a tunnel.</p><div class="setting-actions">${button("Export complete book", "export")}${button("Restore a JSON book", "import")}${button("Start a clean book", "reset", "", "danger-button")}${button("Load sample book", "seed")}</div><input type="file" id="import-file" accept="application/json,.json" hidden><hr><p class="footnote">${demo ? "Sample preview · no edits are saved." : `Signed in as ${escape(account)} · revision ${revision}. Existing Streamlit exports can be restored here. Keep backups private; they may contain client information.`}</p><p class="footnote">No access code required. Identity accounts replace the shared Streamlit password; books are not shared between accounts.</p></section></div>`;
}
function render() {
  if (!book) return renderAuth();
  const content: Record<string, () => string> = { dashboard, clients, invoices, finance: financePage, projects, comms, settings: settingsPage };
  const add: Record<string, string> = { clients: "Add client", invoices: "Create invoice", projects: "Add project" };
  root.innerHTML = `<div class="shell"><aside class="sidebar"><a class="brand" href="#dashboard" data-action="navigate" data-id="dashboard">MIM<span>MEM DIGITAL</span></a><p class="sidebar-caption">THE OPERATIONS CONSOLE</p><nav aria-label="Main navigation">${Object.entries(pages).map(([key, value], index) => `<button class="nav-link ${page === key ? "active" : ""}" data-action="navigate" data-id="${key}"><span class="nav-index">0${index + 1}</span>${escape(value[0])}<span class="nav-arrow">↗</span></button>`).join("")}</nav><div class="sidebar-bottom"><span class="status-dot"></span>${demo ? "Sample preview" : "Private operations book"}<small>CRM · Finance · Delivery · Comms</small>${button(demo ? "Sign in to save" : "Sign out", demo ? "exit-demo" : "logout", "", "text-button")}</div></aside><main><header class="topbar"><span>${escape(book.settings.agency.name)} / OPERATIONS</span><div>${saving ? "Saving…" : demo ? "READ-ONLY SAMPLE" : "NETLIFY DATABASE"} <span class="date">${today()}</span>${button("Reload", "reload", "", "text-button")}</div></header>${demo || book.settings.sample_data ? `<div class="sample-banner">SAMPLE BOOK · These records demonstrate the console; they are not real client data.${demo ? " Sign in to create your private book." : " Start a clean book in Settings when you are ready."}</div>` : ""}<div class="page"><div class="page-heading"><div><span class="eyebrow">MEM Digital / ${String(Object.keys(pages).indexOf(page) + 1).padStart(2, "0")}</span><h1>${pages[page][0]}</h1><p>${pages[page][1]}</p></div>${add[page] ? button(add[page], `new:${page}`, "", "primary") : ""}</div>${["clients", "invoices", "projects"].includes(page) ? `<label class="search-label">Search ${page}<input id="search" type="search" value="${escape(search)}" placeholder="Search the book…"></label>` : ""}<div id="page-content">${content[page]()}</div>${page !== "dashboard" && page !== "settings" ? movesPanel() : ""}<footer>MIM — MEM Digital <span>Decisions, not just dashboards.</span></footer></div></main></div>`;
}
function renderAuth(message = "") {
  const reset = authMode === "recovery" || authMode === "invite";
  root.innerHTML = `<main class="auth-shell"><section class="auth-story"><div class="brand">MIM<span>MEM DIGITAL</span></div><span class="eyebrow">Your agency. Under control.</span><h1>One screen.<br>Every next<br><i>move.</i></h1><p>CRM, finance, delivery, and client communications.<br>A private operations console that turns signals into decisions.</p><div class="auth-pillars"><span>01 / RELATIONSHIPS</span><span>02 / CASH FLOW</span><span>03 / DELIVERY</span><span>04 / CONVERSATIONS</span></div></section><section class="auth-card"><span class="eyebrow">Private workspace</span><h2>${reset ? "Set your password" : authMode === "signup" ? "Start your book" : "Welcome back."}</h2><p>${reset ? "Choose a strong password for your account." : "Your book stays private and survives every deployment."}</p><form id="auth-form">${reset ? "" : `<label>Email<input name="email" type="email" required autocomplete="email"></label>`}<label>Password<input name="password" type="password" required minlength="8" autocomplete="${authMode === "login" ? "current-password" : "new-password"}"></label><button class="primary">${reset ? "Save password" : authMode === "signup" ? "Create account" : "Sign in"} <span>↗</span></button><p id="auth-message" role="status">${escape(message)}</p></form>${reset ? "" : `<div class="auth-links">${allowSignup ? button(authMode === "signup" ? "Already have an account? Sign in" : "Create an account", "auth-mode", "", "text-button") : "<p>Use your invited account to sign in.</p>"}${button("Forgot password", "forgot-password", "", "text-button")}</div>`}<hr>${button("Explore the sample console ↗", "demo", "", "text-button")}<small class="auth-note">No tunnel. No shared access code. Hosted on Netlify.</small></section></main>`;
}
async function loadBook() {
  root.innerHTML = `<div class="loading"><div class="brand">MIM<span>MEM DIGITAL</span></div><h1>Opening your book.</h1><div class="skeleton"></div><div class="skeleton"></div><p>Connecting to your private operations workspace…</p></div>`;
  try {
    const response = await fetch("/api/book", { credentials: "same-origin", cache: "no-store" });
    const result = await response.json();
    if (!response.ok) throw new Error(result.error ?? "Could not open your book.");
    book = bookSchema.parse(result.book);
    revision = result.revision;
    render();
  } catch (error) {
    book = null;
    renderAuth("Your book could not be opened. Sign in again to retry. Saved data is not cleared.");
    notify(error instanceof Error ? error.message : "Could not open your book.", true);
  }
}
async function save(next: Book) {
  if (demo) throw new Error("This is a read-only sample. Sign in to keep your own book.");
  if (saving) throw new Error("A save is in progress. Try again when it finishes.");
  const validated = bookSchema.parse(next);
  saving = true;
  document.body.classList.add("saving");
  try {
    const response = await fetch("/api/book", { method: "PUT", credentials: "same-origin", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ book: validated, revision }) });
    const result = await response.json();
    if (!response.ok) throw new Error(result.error ?? "Could not save. Try again.");
    revision = result.revision;
    book = validated;
    notify("Saved to your private book.");
  } finally { saving = false; document.body.classList.remove("saving"); }
}
function field(label: string, name: string, value: unknown, type = "text", required = false) {
  return `<label>${escape(label)}<input name="${name}" type="${type}" value="${escape(value)}" ${required ? "required" : ""} ${type === "number" ? 'min="0" step="0.01"' : ""}></label>`;
}
function selectField(label: string, name: string, value: unknown, options: [string, string][]) {
  return `<label>${escape(label)}<select name="${name}">${options.map(([key, title]) => `<option value="${escape(key)}" ${key === value ? "selected" : ""}>${escape(title)}</option>`).join("")}</select></label>`;
}
function dialog(title: string, body: string, submit: (form: FormData) => Promise<void>, label = "Save record") {
  const element = document.createElement("dialog");
  element.innerHTML = `<form class="dialog-form"><div class="section-heading"><h2>${escape(title)}</h2><button type="button" data-close aria-label="Close dialog">×</button></div>${body}<p class="form-error" role="alert"></p><div class="dialog-actions"><button type="button" data-close>Cancel</button><button class="primary">${escape(label)}</button></div></form>`;
  document.body.append(element);
  element.querySelectorAll("[data-close]").forEach((control) => control.addEventListener("click", () => element.close()));
  element.addEventListener("close", () => element.remove());
  element.querySelector("form")!.addEventListener("submit", async (event) => {
    event.preventDefault();
    const submitButton = element.querySelector<HTMLButtonElement>('button.primary')!;
    submitButton.disabled = true;
    try { await submit(new FormData(event.target as HTMLFormElement)); element.close(); render(); }
    catch (error) { element.querySelector(".form-error")!.textContent = error instanceof Error ? error.message : "Could not save."; }
    finally { submitButton.disabled = false; }
  });
  element.showModal();
}
function editable() {
  if (demo) { notify("The sample is read-only. Sign in to create your private book."); return false; }
  return Boolean(book);
}
function editRecord(collection: Collection, id?: string) {
  if (!editable()) return;
  const record = book![collection].find((entry) => entry.id === id);
  const defaults: Record<Collection, RecordData> = {
    clients: { id: `C-${crypto.randomUUID().slice(0, 8)}`, name: "", company: "", email: "", stage: "Lead", currency: "USD", deal_value: 0, last_contact: today(), notes: "" },
    invoices: { id: `MEM-${new Date().getFullYear()}-${crypto.randomUUID().slice(0, 8)}`, client_id: book!.clients[0]?.id ?? "", status: "draft", currency: "USD", issue_date: today(), due_date: today(), tax_rate: 0, discount: 0, items: [{ desc: "", qty: 1, rate: 0 }], payments: [] },
    projects: { id: `P-${crypto.randomUUID().slice(0, 8)}`, name: "", client_id: book!.clients[0]?.id ?? "", status: "Active", currency: "USD", budget: 0, hourly_rate: 0, start: today(), due: today(), tasks: [], deliverables: [], time_entries: [], change_orders: [] },
    messages: { id: `M-${crypto.randomUUID().slice(0, 8)}`, client_id: book!.clients[0]?.id ?? "", date: today(), channel: "email", direction: "out", subject: "", body: "" },
  };
  if (collection !== "clients" && !book!.clients.length) { notify("Add a client first."); return; }
  const initial = record ?? defaults[collection];
  const clientOptions = book!.clients.map((client): [string, string] => [client.id, client.company ?? client.name ?? client.id]);
  const options = (values: string[]) => values.map((value): [string, string] => [value, value]);
  let fields = "";
  if (collection === "clients") fields = `${field("Contact name", "name", initial.name, "text", true)}${field("Company", "company", initial.company)}${field("Email", "email", initial.email, "email")}${selectField("Pipeline stage", "stage", initial.stage, options(stages))}${field("Deal value", "deal_value", initial.deal_value, "number")}${field("Last contact", "last_contact", initial.last_contact, "date")}`;
  if (collection !== "clients") fields += selectField("Client", "client_id", initial.client_id, clientOptions);
  if (collection === "invoices") fields += `${selectField("Status", "status", initial.status, options(["draft", "sent", "void"]))}${field("Issue date", "issue_date", initial.issue_date, "date", true)}${field("Due date", "due_date", initial.due_date, "date", true)}${field("Tax rate (0.20 = 20%)", "tax_rate", initial.tax_rate ?? 0, "number")}${field("Discount amount", "discount", initial.discount ?? 0, "number")}<label>Line items (JSON)<textarea name="items" rows="6" required>${escape(JSON.stringify(initial.items, null, 2))}</textarea></label>`;
  if (collection === "projects") fields += `${field("Project name", "name", initial.name, "text", true)}${selectField("Status", "status", initial.status, options(["Active", "On Hold", "Completed", "Delivered"]))}${field("Start", "start", initial.start, "date")}${field("Deadline", "due", initial.due, "date")}${field("Budget", "budget", initial.budget ?? 0, "number")}${field("Hourly rate", "hourly_rate", initial.hourly_rate ?? 0, "number")}`;
  if (collection === "messages") fields += `${field("Date", "date", initial.date, "date", true)}${selectField("Channel", "channel", initial.channel, options(["email", "phone", "Slack", "meeting", "WhatsApp"]))}${selectField("Direction", "direction", initial.direction, [["out", "Outbound"], ["in", "Inbound"]])}${field("Subject", "subject", initial.subject)}<label>Message<textarea name="body" rows="6">${escape(initial.body)}</textarea></label>`;
  if (collection !== "messages") fields += `${selectField("Currency", "currency", initial.currency ?? "USD", options(currencies))}<label>Notes<textarea name="notes" rows="3">${escape(initial.notes)}</textarea></label>`;
  fields += `<details><summary>Advanced record details</summary><p class="footnote">Edit tasks, deliverables, approvals, time entries, change orders, preferences, and other existing fields here. The form fields above override the same keys.</p><textarea name="advanced" rows="12" required>${escape(JSON.stringify(initial, null, 2))}</textarea></details>`;
  dialog(`${record ? "Edit" : "Add"} ${collection.slice(0, -1)}`, fields, async (form) => {
    const updated = JSON.parse(String(form.get("advanced"))) as RecordData;
    updated.id = initial.id;
    for (const [key, value] of form.entries()) {
      if (key === "advanced") continue;
      updated[key] = ["deal_value", "budget", "hourly_rate", "tax_rate", "discount"].includes(key) ? Number(value) : key === "items" ? JSON.parse(String(value)) : String(value);
    }
    const next = structuredClone(book!);
    const index = next[collection].findIndex((entry) => entry.id === initial.id);
    if (index < 0) next[collection].push(updated); else next[collection][index] = updated;
    if (collection === "messages") {
      const client = next.clients.find((entry) => entry.id === updated.client_id);
      if (client && String(updated.date) > String(client.last_contact ?? "")) client.last_contact = updated.date;
    }
    await save(next);
  });
}
function download(filename: string, content: string, type = "application/json") {
  const url = URL.createObjectURL(new Blob([content], { type }));
  const link = document.createElement("a");
  link.href = url;
  link.download = filename.replace(/[^a-zA-Z0-9_.-]/g, "_");
  link.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
function confirmBook(title: string, description: string, next: Book) {
  if (!editable()) return;
  dialog(title, `<p>${escape(description)} Export your current book first if you need a backup.</p>${field('Type "REPLACE" to confirm', "confirm", "", "text", true)}`, async (form) => {
    if (form.get("confirm") !== "REPLACE") throw new Error('Type "REPLACE" exactly to confirm.');
    await save(next);
  }, "Replace book");
}
function paymentDialog(id: string) {
  if (!editable()) return;
  const invoice = book!.invoices.find((record) => record.id === id)!;
  const balance = invoiceTotals(invoice).balance;
  dialog(`Record payment · ${id}`, `${field("Amount", "amount", balance, "number", true)}${field("Date", "date", today(), "date", true)}${field("Method", "method", "wire")}${field("Note", "note", "")}`, async (form) => {
    const amount = Number(form.get("amount"));
    if (amount <= 0 || amount > balance) throw new Error("Enter a positive payment no greater than the outstanding balance.");
    const next = structuredClone(book!);
    const target = next.invoices.find((record) => record.id === id)!;
    target.payments = [...(target.payments ?? []), { amount, date: String(form.get("date")), method: String(form.get("method")), note: String(form.get("note")) }];
    await save(next);
  });
}
async function action(name: string, id: string) {
  if (name === "navigate") { page = pages[id] ? id : "dashboard"; search = ""; history.replaceState(null, "", `#${page}`); render(); return; }
  if (name === "demo") { demo = true; book = sampleBook(); render(); return; }
  if (name === "exit-demo") { demo = false; book = null; renderAuth(); return; }
  if (name === "auth-mode") { authMode = authMode === "login" ? "signup" : "login"; renderAuth(); return; }
  if (name === "forgot-password") {
    const email = root.querySelector<HTMLInputElement>('[name="email"]')?.value;
    if (!email) throw new Error("Enter your email address first.");
    await requestPasswordRecovery(email); notify("Check your email for a password reset link."); return;
  }
  if (name === "logout") { await logout(); book = null; demo = false; renderAuth(); return; }
  if (name === "reload") { if (demo) render(); else await loadBook(); return; }
  if (!book) return;
  if (name.startsWith("edit:")) { editRecord(name.split(":")[1] as Collection, id); return; }
  if (name.startsWith("new:")) { editRecord(name.split(":")[1] as Collection); return; }
  if (name.startsWith("delete:")) {
    if (!editable()) return;
    const collection = name.split(":")[1] as Collection;
    if (collection === "clients" && [book.invoices, book.projects, book.messages].some((records) => records.some((record) => record.client_id === id))) throw new Error("This client has linked invoices, projects, or messages. Remove or reassign those records first.");
    dialog("Delete record", `<p>Delete ${escape(id)} from your private book? This cannot be undone without restoring a backup.</p>`, async () => {
      const next = structuredClone(book!);
      next[collection] = next[collection].filter((record) => record.id !== id);
      await save(next);
    }, "Delete record"); return;
  }
  if (name === "payment") { paymentDialog(id); return; }
  if (name === "export") { download(`mim-book-${today()}.json`, JSON.stringify(book, null, 2)); return; }
  if (name === "import") { if (editable()) document.querySelector<HTMLInputElement>("#import-file")!.click(); return; }
  if (name === "reset") { confirmBook("Start a clean book", "This removes all clients, invoices, projects, and messages from your account.", emptyBook(book.settings)); return; }
  if (name === "seed") { confirmBook("Load sample book", "This replaces your records with fictional sample data.", sampleBook()); return; }
  if (name === "invoice-download") {
    const invoice = book.invoices.find((entry) => entry.id === id)!;
    const totals = invoiceTotals(invoice);
    const client = book.clients.find((entry) => entry.id === invoice.client_id);
    download(`${invoice.id}.html`, `<!doctype html><html lang="en"><meta charset="utf-8"><title>${escape(invoice.id)}</title><body><h1>${escape(book.settings.agency.name)}</h1><h2>Invoice ${escape(invoice.id)}</h2><p>Bill to: ${escape(client?.company ?? client?.name)} · ${escape(client?.email)}</p><p>Issued ${escape(invoice.issue_date)} · Due ${escape(invoice.due_date)}</p><table><thead><tr><th>Description</th><th>Quantity</th><th>Rate</th><th>Amount</th></tr></thead><tbody>${(invoice.items ?? []).map((item) => `<tr><td>${escape(item.desc)}</td><td>${item.qty}</td><td>${money(item.rate, invoice.currency)}</td><td>${money(item.rate * item.qty, invoice.currency)}</td></tr>`).join("")}</tbody></table><p>Discount ${money(invoice.discount ?? 0, invoice.currency)} · Tax ${((invoice.tax_rate ?? 0) * 100).toFixed(2)}%</p><h3>Total ${money(totals.total, invoice.currency)}</h3><p>Paid ${money(totals.paid, invoice.currency)} · Balance ${money(totals.balance, invoice.currency)}</p><p>${escape(invoice.notes)}</p></body></html>`, "text/html"); return;
  }
  if (name === "generate-draft") {
    draftClient = root.querySelector<HTMLSelectElement>("#draft-client")!.value;
    templateName = root.querySelector<HTMLSelectElement>("#draft-template")!.value;
    templateLanguage = root.querySelector<HTMLSelectElement>("#draft-language")!.value;
    const client = book.clients.find((entry) => entry.id === draftClient);
    if (!client) throw new Error("Choose a client first.");
    const context: Record<string, string> = { name: client.name ?? "", company: client.company ?? "", sender: book.settings.agency.name };
    draft = templates[templateName][templateLanguage].replace(/\{([^{}]+)\}/g, (_, key: string) => context[key] ?? `[${key}]`);
    render(); return;
  }
  if (name === "draft-download") { draft = root.querySelector<HTMLTextAreaElement>("#draft-body")!.value; if (!draft.trim()) throw new Error("Create a draft first."); download(`mim-${templateName}.txt`, draft, "text/plain"); return; }
  if (name === "log-draft") {
    if (!editable()) return;
    draft = root.querySelector<HTMLTextAreaElement>("#draft-body")!.value;
    draftClient = root.querySelector<HTMLSelectElement>("#draft-client")!.value;
    if (!draft.trim() || !draftClient) throw new Error("Choose a client and write the message first.");
    if (/\[[a-z_0-9]+\]/i.test(draft)) throw new Error("Replace the remaining template placeholders before logging as sent.");
    dialog("Log this message as sent", "<p>Confirm that you already sent this message from your own inbox. MIM does not send it.</p>", async () => {
      const next = structuredClone(book!);
      next.messages.push({ id: `M-${crypto.randomUUID()}`, client_id: draftClient, date: today(), subject: draft.split("\n")[0], body: draft, direction: "out", channel: "email" });
      next.clients.find((entry) => entry.id === draftClient)!.last_contact = today();
      await save(next);
    }, "Already sent · log it"); return;
  }
  if (name === "log-time") {
    if (!editable()) return;
    dialog("Log project time", `${field("Hours", "hours", "", "number", true)}${field("Date", "date", today(), "date", true)}${field("Work description", "note", "")}`, async (form) => {
      const hours = Number(form.get("hours"));
      if (hours <= 0) throw new Error("Hours must be greater than zero.");
      const next = structuredClone(book!);
      const project = next.projects.find((entry) => entry.id === id)!;
      project.time_entries = [...(project.time_entries ?? []), { hours, date: String(form.get("date")), note: String(form.get("note")), billed: false }];
      await save(next);
    }); return;
  }
  if (name === "bill-time" || name === "bill-change") {
    if (!editable()) return;
    const [projectId, orderId] = id.split("|");
    const next = structuredClone(book);
    const project = next.projects.find((entry) => entry.id === projectId)!;
    const invoiceId = `MEM-${new Date().getFullYear()}-${crypto.randomUUID().slice(0, 8)}`;
    let items: NonNullable<RecordData["items"]>;
    if (name === "bill-time") {
      const entries = (project.time_entries ?? []).filter((entry) => !entry.billed && !entry.invoice_id);
      const hours = entries.reduce((sum, entry) => sum + entry.hours, 0);
      if (!hours || !project.hourly_rate) throw new Error("Log unbilled time and set a positive hourly rate first.");
      items = [{ desc: `${project.name} — logged time`, qty: hours, rate: project.hourly_rate }];
      for (const entry of entries) { entry.billed = true; entry.invoice_id = invoiceId; }
    } else {
      const order = project.change_orders?.find((entry) => entry.id === orderId);
      if (!order || order.status !== "Approved") throw new Error("The change order must be approved before billing.");
      const value = order.amount ?? order.value ?? 0;
      if (value <= 0) throw new Error("Set a positive change-order value first.");
      items = [{ desc: `${project.name} — ${order.id}`, qty: 1, rate: value }];
      order.status = "Billed";
      order.invoice_id = invoiceId;
    }
    next.invoices.push({ id: invoiceId, client_id: project.client_id, project_id: project.id, currency: project.currency ?? "USD", issue_date: today(), due_date: new Date(Date.now() + 14 * 86400000).toISOString().slice(0, 10), status: "draft", items, payments: [], tax_rate: 0, discount: 0 });
    await save(next); page = "invoices"; render();
  }
}
root.addEventListener("click", (event) => {
  const target = (event.target as Element).closest<HTMLElement>("[data-action]");
  if (!target) return;
  event.preventDefault();
  void action(target.dataset.action!, target.dataset.id ?? "").catch((error) => notify(error instanceof Error ? error.message : "Something went wrong. Try again.", true));
});
root.addEventListener("input", (event) => {
  const target = event.target as HTMLInputElement;
  if (target.id === "draft-body") draft = target.value;
  if (target.id === "search") {
    search = target.value;
    const content: Record<string, () => string> = { clients, invoices, projects };
    root.querySelector("#page-content")!.innerHTML = content[page]();
  }
});
root.addEventListener("change", async (event) => {
  const target = event.target as HTMLInputElement;
  try {
    if (target.dataset.task && editable()) {
      const next = structuredClone(book!);
      const task = next.projects.find((entry) => entry.id === target.dataset.task)!.tasks![Number(target.dataset.index)];
      task.status = target.value;
      delete task.progress;
      await save(next); render();
    }
    if (target.id === "import-file" && target.files?.[0]) {
      const file = target.files[0];
      target.value = "";
      if (file.size > 2_000_000) throw new Error("Choose a JSON book smaller than 2 MB.");
      const parsed = bookSchema.safeParse(JSON.parse(await file.text()));
      if (!parsed.success) throw new Error("This export contains invalid dates, amounts, or references. Restore a complete MIM book.");
      confirmBook("Restore your book", "This replaces all current records with the uploaded book.", parsed.data);
    }
  } catch (error) { if (target.dataset.task) render(); notify(error instanceof Error ? error.message : "Could not update the book.", true); }
});
root.addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = event.target as HTMLFormElement;
  const data = new FormData(form);
  const submit = form.querySelector<HTMLButtonElement>('button[type="submit"], button.primary')!;
  submit.disabled = true;
  try {
    if (form.id === "auth-form") {
      const password = String(data.get("password"));
      if (authMode === "invite") await acceptInvite(inviteToken, password);
      else if (authMode === "recovery") await updateUser({ password });
      else if (authMode === "signup") {
        const user = await signup(String(data.get("email")), password);
        if (!user.confirmedAt) { renderAuth("Check your email to confirm your account, then sign in."); return; }
      } else await login(String(data.get("email")), password);
      const user = await getUser();
      account = user?.email ?? "";
      authMode = "login"; demo = false;
      await loadBook();
    }
    if (form.id === "settings-form") {
      const next = structuredClone(book!);
      next.settings.agency = { ...next.settings.agency, name: String(data.get("agency-name")), owner: String(data.get("owner")), email: String(data.get("email")), base_currency: String(data.get("currency")) };
      next.settings.targets.monthly_revenue = Number(data.get("target"));
      next.settings.fx_rates = JSON.parse(String(data.get("fx")));
      await save(next); render();
    }
  } catch (error) { notify(error instanceof Error ? error.message : "Could not complete this request.", true); }
  finally { submit.disabled = false; }
});
async function start() {
  try {
    const callback = await handleAuthCallback();
    if (callback?.type === "invite" && callback.token) { inviteToken = callback.token; authMode = "invite"; renderAuth(); return; }
    if (callback?.type === "recovery") { authMode = "recovery"; renderAuth(); return; }
    const user = await getUser();
    if (user) {
      account = user.email ?? "";
      const requested = location.hash.slice(1);
      page = pages[requested] ? requested : "dashboard";
      await loadBook();
    } else {
      try { allowSignup = !(await getSettings()).disableSignup; } catch { allowSignup = false; }
      renderAuth();
    }
  } catch { renderAuth("Could not process this sign-in link. Request a new link or sign in again."); }
}
onAuthChange((event) => {
  if (event === "logout") {
    document.querySelectorAll("dialog").forEach((element) => element.close());
    book = null; draft = ""; account = ""; demo = false; renderAuth();
  }
});
void start();
