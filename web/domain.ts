import { z } from "zod";

export const collections = ["clients", "invoices", "projects", "messages"] as const;
export type Collection = typeof collections[number];
export const stages = ["Lead", "Contacted", "Proposal Sent", "Active", "Completed", "Upsell"];
export const currencies = ["USD", "EUR", "GBP", "AED", "MAD", "MXN"];
export const taskStatuses = ["Not Started", "In Progress", "Blocked", "In Review", "Done"];
const amount = z.number().finite().nonnegative().max(1e12);
const date = z.string().regex(/^\d{4}-\d{2}-\d{2}$/).refine((value) => {
  const parsed = new Date(`${value}T00:00:00Z`);
  return !Number.isNaN(parsed.getTime()) && parsed.toISOString().slice(0, 10) === value;
}, "Use a valid calendar date");
const optionalDate = z.union([date, z.literal(""), z.null()]).optional();
const item = z.looseObject({ desc: z.string(), qty: amount, rate: amount, unit: z.string().optional() });
const payment = z.looseObject({ date, amount: amount.positive(), method: z.string().optional(), note: z.string().optional() });
const task = z.looseObject({ id: z.string().optional(), name: z.string().optional(), status: z.string().optional(), progress: amount.max(100).optional(), weight: amount.optional(), estimated_hours: amount.optional(), logged_hours: amount.optional() });
export const recordSchema = z.looseObject({
  id: z.string().min(1).max(120), name: z.string().max(500).optional(), company: z.string().max(500).optional(),
  client_id: z.string().optional(), project_id: z.union([z.string(), z.null()]).optional(), email: z.string().optional(),
  stage: z.enum(stages as [string, ...string[]]).optional(), status: z.string().optional(), currency: z.enum(currencies as [string, ...string[]]).optional(),
  deal_value: amount.optional(), budget: amount.optional(), hourly_rate: amount.optional(), tax_rate: amount.max(1).optional(), discount: amount.optional(),
  issue_date: optionalDate, due_date: optionalDate, start: optionalDate, due: optionalDate, date: optionalDate, last_contact: optionalDate,
  notes: z.string().optional(), body: z.string().optional(), subject: z.string().optional(), channel: z.string().optional(), direction: z.string().optional(),
  items: z.array(item).max(100).optional(), payments: z.array(payment).max(1000).optional(), tasks: z.array(task).max(1000).optional(),
  deliverables: z.array(z.looseObject({ name: z.string(), approval: z.looseObject({ state: z.string(), requested: optionalDate }).optional() })).max(1000).optional(),
  time_entries: z.array(z.looseObject({ hours: amount, date: optionalDate, billed: z.boolean().optional(), invoice_id: z.union([z.string(), z.null()]).optional() })).max(1000).optional(),
  change_orders: z.array(z.looseObject({ id: z.string(), status: z.string(), amount: amount.optional(), value: amount.optional() })).max(1000).optional(),
});
export type RecordData = z.infer<typeof recordSchema>;
export const settingsSchema = z.looseObject({
  sample_data: z.boolean(),
  agency: z.looseObject({ name: z.string().min(1), owner: z.string().optional(), email: z.string().optional(), base_currency: z.enum(currencies as [string, ...string[]]) }),
  fx_rates: z.record(z.string(), amount.positive()),
  targets: z.looseObject({ monthly_revenue: amount }),
  cadence_days: z.record(z.string(), amount).optional(),
});
export type Settings = z.infer<typeof settingsSchema>;
export const bookSchema = z.object({
  settings: settingsSchema,
  clients: z.array(recordSchema).max(2000), invoices: z.array(recordSchema).max(2000),
  projects: z.array(recordSchema).max(2000), messages: z.array(recordSchema).max(2000),
}).superRefine((book, context) => {
  if (!book.settings.fx_rates[book.settings.agency.base_currency]) context.addIssue({ code: "custom", message: "Set an FX rate for the base currency" });
  for (const collection of collections) {
    const ids = book[collection].map((record) => record.id);
    if (new Set(ids).size !== ids.length) context.addIssue({ code: "custom", message: `Duplicate IDs in ${collection}` });
    for (const record of book[collection]) {
      if (record.currency && !book.settings.fx_rates[record.currency]) context.addIssue({ code: "custom", message: `Set an FX rate for ${record.currency}` });
    }
  }
  const clientIds = new Set(book.clients.map((client) => client.id));
  const projectIds = new Set(book.projects.map((project) => project.id));
  for (const collection of ["invoices", "projects", "messages"] as const) {
    for (const record of book[collection]) {
      if (record.client_id && !clientIds.has(record.client_id)) context.addIssue({ code: "custom", message: `${record.id} references a missing client` });
      if (record.project_id && !projectIds.has(record.project_id)) context.addIssue({ code: "custom", message: `${record.id} references a missing project` });
    }
  }
});
export type Book = z.infer<typeof bookSchema>;
export const saveSchema = z.object({ revision: z.number().int().nonnegative(), book: bookSchema });
export const today = () => new Date().toISOString().slice(0, 10);
export function daysBetween(from: string | null | undefined, to = today()) {
  return from ? Math.floor((Date.parse(`${to}T00:00:00Z`) - Date.parse(`${from}T00:00:00Z`)) / 86400000) : 0;
}
export function money(value: number, currency = "USD") {
  return new Intl.NumberFormat("en", { style: "currency", currency, maximumFractionDigits: 2 }).format(value);
}
export function invoiceTotals(invoice: RecordData, reference = today()) {
  const subtotal = (invoice.items ?? []).reduce((sum, item) => sum + item.qty * item.rate, 0);
  const discounted = Math.max(0, subtotal - (invoice.discount ?? 0));
  const total = Math.round(discounted * (1 + (invoice.tax_rate ?? 0)) * 100) / 100;
  const paid = (invoice.payments ?? []).reduce((sum, payment) => sum + payment.amount, 0);
  const balance = Math.max(0, Math.round((total - paid) * 100) / 100);
  const late = Math.max(0, daysBetween(invoice.due_date, reference));
  const status = invoice.status === "void" || invoice.status === "draft" ? invoice.status : balance <= 0 ? "paid" : late > 0 ? "overdue" : paid > 0 ? "partial" : "sent";
  return { total, paid, balance, late, status };
}
export function baseAmount(book: Book, value: number, currency = "USD") {
  const rates = book.settings.fx_rates;
  return value * (rates[currency] ?? 1) / (rates[book.settings.agency.base_currency] ?? 1);
}
export function projectProgress(project: RecordData) {
  const weights: Record<string, number> = { "Not Started": 0, Blocked: 0, "In Progress": 50, "In Review": 80, Done: 100 };
  const tasks = project.tasks ?? [];
  const totalWeight = tasks.reduce((sum, task) => sum + (task.weight || task.estimated_hours || 1), 0);
  return tasks.length ? Math.round(tasks.reduce((sum, task) => sum + (task.progress ?? weights[task.status ?? ""] ?? 0) * (task.weight || task.estimated_hours || 1), 0) / totalWeight) : Number(project.progress ?? 0);
}
export function projectRisk(project: RecordData, reference = today()) {
  const progress = projectProgress(project);
  if (["Completed", "Delivered"].includes(project.status ?? "") || progress >= 100) return "Delivered";
  if (!project.due) return "No Deadline";
  const left = -daysBetween(project.due, reference);
  const duration = daysBetween(project.start, project.due);
  const expected = project.start && duration > 0 ? Math.max(0, Math.min(100, daysBetween(project.start, reference) / duration * 100)) : progress;
  if (left < 0 || progress - expected <= -25) return "Critical";
  if (progress - expected <= -10 || (left <= 7 && progress < 85)) return "At Risk";
  return "On Track";
}
export interface Move { title: string; reason: string; score: number; clientId?: string; page: string }
export function nextMoves(book: Book, reference = today()): Move[] {
  const moves: Move[] = [];
  const clientName = (id?: string) => book.clients.find((client) => client.id === id)?.company ?? "Client";
  for (const invoice of book.invoices) {
    const totals = invoiceTotals(invoice, reference);
    if (totals.status === "overdue" || totals.status === "draft") moves.push({
      title: `${totals.status === "draft" ? "Send" : "Collect"} ${invoice.id}`, clientId: invoice.client_id, page: "invoices",
      reason: `${clientName(invoice.client_id)} · ${money(totals.balance, invoice.currency)} · ${totals.status === "draft" ? "draft waiting to send" : `${totals.late} days overdue`}`,
      score: baseAmount(book, totals.balance, invoice.currency) * (totals.status === "draft" ? 1.25 : totals.late > 21 ? 4 : totals.late > 7 ? 2.5 : 1.5),
    });
  }
  for (const project of book.projects) {
    const risk = projectRisk(project, reference);
    if (["Critical", "At Risk"].includes(risk)) moves.push({ title: `Unblock ${project.name}`, reason: `${risk} · ${projectProgress(project)}% complete · due ${project.due}`, score: baseAmount(book, project.budget ?? 0, project.currency) * (risk === "Critical" ? 3 : 1.5), clientId: project.client_id, page: "projects" });
    for (const order of project.change_orders ?? []) if (order.status === "Approved") moves.push({ title: `Bill ${order.id}`, reason: `${project.name} · approved change order`, score: baseAmount(book, order.amount ?? order.value ?? 0, project.currency) * 2, clientId: project.client_id, page: "projects" });
    const unbilled = (project.time_entries ?? []).filter((entry) => !entry.billed && !entry.invoice_id).reduce((sum, entry) => sum + entry.hours, 0);
    if (unbilled > 0) moves.push({ title: `Invoice ${unbilled}h on ${project.name}`, reason: "Logged time not yet billed", score: baseAmount(book, unbilled * (project.hourly_rate ?? 0), project.currency) * 1.4, clientId: project.client_id, page: "projects" });
    for (const deliverable of project.deliverables ?? []) if (deliverable.approval?.state === "pending") moves.push({ title: `Chase ${deliverable.name} approval`, reason: `${project.name} · waiting ${daysBetween(deliverable.approval.requested, reference)} days`, score: baseAmount(book, project.budget ?? 0, project.currency) * 0.5, clientId: project.client_id, page: "projects" });
  }
  const cadence: Record<string, number> = { Lead: 3, Contacted: 5, "Proposal Sent": 4, Active: 7, Completed: 21, Upsell: 14, ...book.settings.cadence_days };
  for (const client of book.clients) {
    const silence = daysBetween(client.last_contact, reference);
    if (silence > (cadence[client.stage ?? "Lead"] ?? 7)) moves.push({ title: `Reconnect with ${client.company ?? client.name}`, reason: `${silence} days of silence · ${client.stage}`, score: baseAmount(book, client.deal_value ?? 0, client.currency) * Math.min(1, silence / 30), clientId: client.id, page: "comms" });
  }
  const seen = new Set<string>();
  return moves.sort((first, second) => second.score - first.score).filter((move) => {
    if (move.clientId && seen.has(move.clientId)) return false;
    if (move.clientId) seen.add(move.clientId);
    return true;
  });
}
export function emptyBook(settings: Settings): Book {
  return { settings: { ...structuredClone(settings), sample_data: false }, clients: [], invoices: [], projects: [], messages: [] };
}
