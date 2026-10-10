import assert from "node:assert/strict";
import { test } from "node:test";
import { makeBookHandler, RevisionConflict, type BookApi } from "../../web/book-api.js";
import { sampleBook } from "../../web/sample.js";

function fixture(overrides: Partial<BookApi> = {}) {
  const owners: string[] = [];
  const book = sampleBook("2026-10-05");
  const handler = makeBookHandler({
    authenticate: async () => ({ id: "owner-a", confirmedAt: "2026-10-01" }),
    read: async (owner) => { owners.push(owner); return { book, revision: 3 }; },
    write: async (owner) => { owners.push(owner); return 4; },
    ...overrides,
  });
  const request = (body: unknown = { book, revision: 3 }, origin = "https://console.example") => new Request("https://console.example/api/book", { method: "PUT", headers: { "Content-Type": "application/json", Origin: origin }, body: JSON.stringify(body) });
  return { handler, owners, book, request };
}

test("anonymous and unconfirmed users cannot read or write any book", async () => {
  for (const user of [null, { id: "unconfirmed" }]) {
    const { handler, owners, request } = fixture({ authenticate: async () => user });
    assert.equal((await handler(new Request("https://console.example/api/book"))).status, 401);
    assert.equal((await handler(request())).status, 401);
    assert.deepEqual(owners, []);
  }
});

test("reads use the authenticated owner and private no-store responses", async () => {
  const { handler, owners } = fixture();
  const response = await handler(new Request("https://console.example/api/book?ownerId=someone-else"));
  assert.equal(response.status, 200);
  assert.deepEqual(owners, ["owner-a"]);
  assert.equal(response.headers.get("Cache-Control"), "private, no-store");
});

test("writes cannot override ownership in the request body", async () => {
  const { handler, request, owners, book } = fixture();
  const response = await handler(request({ book, revision: 3, ownerId: "someone-else" }));
  assert.equal(response.status, 200);
  assert.deepEqual(owners, ["owner-a"]);
  assert.deepEqual(await response.json(), { revision: 4 });
});

test("cross-origin writes fail without touching storage", async () => {
  const { handler, request, owners } = fixture();
  assert.equal((await handler(request(undefined, "https://attacker.example"))).status, 403);
  assert.deepEqual(owners, []);
});

test("missing Origin is rejected", async () => {
  const { handler, request } = fixture();
  const incoming = request(); incoming.headers.delete("Origin");
  assert.equal((await handler(incoming)).status, 403);
});

test("invalid data and malformed JSON fail before writing", async () => {
  const { handler, request, owners } = fixture();
  assert.equal((await handler(request({ revision: -1, book: {} }))).status, 422);
  const malformed = new Request("https://console.example/api/book", { method: "PUT", headers: { Origin: "https://console.example", "Content-Type": "application/json" }, body: "{" });
  assert.equal((await handler(malformed)).status, 400);
  assert.deepEqual(owners, []);
});

test("non-JSON writes and unsupported methods are rejected", async () => {
  const { handler, request } = fixture();
  const incoming = request(); incoming.headers.set("Content-Type", "text/plain");
  assert.equal((await handler(incoming)).status, 415);
  const response = await handler(new Request("https://console.example/api/book", { method: "DELETE" }));
  assert.equal(response.status, 405);
  assert.equal(response.headers.get("Allow"), "GET, PUT");
});

test("large uploads are rejected", async () => {
  const { handler, request, owners } = fixture();
  assert.equal((await handler(request({ extra: "x".repeat(2_000_001) }))).status, 413);
  assert.deepEqual(owners, []);
});

test("stale revisions return a conflict rather than overwriting newer data", async () => {
  const { handler, request } = fixture({ write: async () => { throw new RevisionConflict(); } });
  const response = await handler(request());
  assert.equal(response.status, 409);
  assert.match((await response.json()).error, /another tab/);
});

test("storage failures never expose internal exception details", async () => {
  const { handler } = fixture({ read: async () => { throw new Error("internal connection details"); } });
  const response = await handler(new Request("https://console.example/api/book"));
  assert.equal(response.status, 503);
  assert.doesNotMatch(await response.text(), /internal connection/);
});
