import { getUser } from "@netlify/identity";
import type { Config } from "@netlify/functions";
import { and, eq } from "drizzle-orm";
import { getDb } from "../../db/index.js";
import { books, records } from "../../db/schema.js";
import { collections, type Book, type RecordData } from "../../web/domain.js";
import { makeBookHandler, RevisionConflict } from "../../web/book-api.js";
import { sampleBook } from "../../web/sample.js";

function rows(ownerId: string, book: Book) {
  return collections.flatMap((collection) => book[collection].map((data) => ({ ownerId, collection, recordId: data.id, data })));
}

export default makeBookHandler({
  authenticate: getUser,
  read: async (ownerId) => getDb().transaction(async (transaction) => {
    const seed = sampleBook();
    const created = await transaction.insert(books).values({ ownerId, settings: seed.settings }).onConflictDoNothing().returning();
    if (created.length) await transaction.insert(records).values(rows(ownerId, seed));
    const [bookRow] = await transaction.select().from(books).where(eq(books.ownerId, ownerId)).for("share");
    const recordRows = await transaction.select().from(records).where(eq(records.ownerId, ownerId));
    const book: Book = { settings: bookRow.settings, clients: [], invoices: [], projects: [], messages: [] };
    for (const row of recordRows) if (collections.includes(row.collection as typeof collections[number])) book[row.collection as typeof collections[number]].push(row.data as RecordData);
    return { book, revision: bookRow.revision };
  }),
  write: async (ownerId, snapshot) => getDb().transaction(async (transaction) => {
    const updated = await transaction.update(books).set({ settings: snapshot.book.settings, revision: snapshot.revision + 1, updatedAt: new Date() }).where(and(eq(books.ownerId, ownerId), eq(books.revision, snapshot.revision))).returning();
    if (!updated.length) throw new RevisionConflict();
    await transaction.delete(records).where(eq(records.ownerId, ownerId));
    const entries = rows(ownerId, snapshot.book);
    for (let offset = 0; offset < entries.length; offset += 200) await transaction.insert(records).values(entries.slice(offset, offset + 200));
    return updated[0].revision;
  }),
});

export const config: Config = { path: "/api/book" };
