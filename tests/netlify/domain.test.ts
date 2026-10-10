import assert from "node:assert/strict";
import { test } from "node:test";
import { baseAmount, bookSchema, daysBetween, emptyBook, invoiceTotals, nextMoves, projectProgress, projectRisk } from "../../web/domain.js";
import { sampleBook, templates } from "../../web/sample.js";

const reference = "2026-10-05";

test("the original sample book and bilingual templates survive the port", () => {
  const book = sampleBook(reference);
  assert.equal(book.clients.length, 5);
  assert.equal(book.invoices.length, 8);
  assert.equal(book.projects.length, 4);
  assert.equal(book.settings.sample_data, true);
  assert.ok(Object.keys(templates).length >= 15);
  assert.ok(Object.values(templates).every((template) => template.en && template.es));
});

test("sample dates stay relative to the first visit", () => {
  const first = sampleBook(reference);
  const later = sampleBook("2026-11-04");
  assert.equal(daysBetween(first.invoices[0].due_date, later.invoices[0].due_date!), 30);
});

test("invoice totals use quantity, absolute discount, fractional tax and payments", () => {
  const result = invoiceTotals({ id: "invoice", status: "sent", due_date: "2026-10-01", items: [{ desc: "Film", qty: 2, rate: 150 }], discount: 50, tax_rate: .2, payments: [{ date: reference, amount: 100 }] }, reference);
  assert.deepEqual(result, { total: 300, paid: 100, balance: 200, late: 4, status: "overdue" });
});

test("drafts and void invoices do not become overdue", () => {
  for (const status of ["draft", "void"]) assert.equal(invoiceTotals({ id: status, status, due_date: "2026-01-01", items: [{ desc: "", qty: 1, rate: 100 }] }, reference).status, status);
});

test("fully paid invoices are paid and partial future invoices are partial", () => {
  const invoice = { id: "invoice", status: "sent", due_date: "2026-11-01", items: [{ desc: "", qty: 1, rate: 100 }], payments: [{ date: reference, amount: 100 }] };
  assert.equal(invoiceTotals(invoice, reference).status, "paid");
  invoice.payments[0].amount = 40;
  assert.equal(invoiceTotals(invoice, reference).status, "partial");
});

test("FX conversion respects the selected base currency", () => {
  const book = sampleBook(reference);
  book.settings.agency.base_currency = "EUR";
  assert.ok(Math.abs(baseAmount(book, 108, "USD") - 100) < .000001);
});

test("weighted project progress and deadline risk reflect the existing engine", () => {
  const project = { id: "project", start: "2026-09-05", due: "2026-10-10", tasks: [{ name: "Strategy", status: "Done", weight: 1 }, { name: "Production", status: "In Progress", weight: 3 }] };
  assert.equal(projectProgress(project), 63);
  assert.equal(projectRisk(project, reference), "At Risk");
  project.tasks[1].status = "Done";
  assert.equal(projectRisk(project, reference), "Delivered");
});

test("next moves rank urgency and select one signal per client", () => {
  const moves = nextMoves(sampleBook(reference), reference);
  assert.ok(moves.length > 0);
  assert.equal(new Set(moves.map((move) => move.clientId)).size, moves.length);
  assert.ok(moves.every((move, index) => index === 0 || moves[index - 1].score >= move.score));
});

test("clean books keep settings without changing the source", () => {
  const sample = sampleBook(reference);
  const clean = emptyBook(sample.settings);
  assert.equal(clean.settings.sample_data, false);
  assert.equal(clean.clients.length, 0);
  assert.equal(sample.settings.sample_data, true);
});

test("validation rejects duplicate IDs, missing clients and non-existent dates", () => {
  const duplicate = sampleBook(reference);
  duplicate.clients.push(duplicate.clients[0]);
  assert.equal(bookSchema.safeParse(duplicate).success, false);
  const missing = sampleBook(reference);
  missing.invoices[0].client_id = "missing";
  assert.equal(bookSchema.safeParse(missing).success, false);
  const date = sampleBook(reference);
  date.invoices[0].due_date = "2026-02-30";
  assert.equal(bookSchema.safeParse(date).success, false);
});

test("validation rejects negative money and absent FX rates", () => {
  const book = sampleBook(reference);
  book.invoices[0].items![0].rate = -1;
  assert.equal(bookSchema.safeParse(book).success, false);
  book.invoices[0].items![0].rate = 100;
  delete book.settings.fx_rates.USD;
  assert.equal(bookSchema.safeParse(book).success, false);
});

test("existing advanced record fields are retained on export and import", () => {
  const sample = sampleBook(reference);
  assert.deepEqual(bookSchema.parse(JSON.parse(JSON.stringify(sample))), sample);
});
