import { foreignKey, integer, jsonb, pgTable, primaryKey, text, timestamp } from "drizzle-orm/pg-core";
import type { Settings, RecordData } from "../web/domain.js";

export const books = pgTable("mim_books", {
  ownerId: text("owner_id").primaryKey(),
  settings: jsonb("settings").$type<Settings>().notNull(),
  revision: integer("revision").notNull().default(0),
  updatedAt: timestamp("updated_at", { withTimezone: true }).notNull().defaultNow(),
});

export const records = pgTable("mim_records", {
  ownerId: text("owner_id").notNull(),
  collection: text("collection").notNull(),
  recordId: text("record_id").notNull(),
  data: jsonb("data").$type<RecordData>().notNull(),
}, (table) => [
  primaryKey({ columns: [table.ownerId, table.collection, table.recordId] }),
  foreignKey({ columns: [table.ownerId], foreignColumns: [books.ownerId] }).onDelete("cascade"),
]);
