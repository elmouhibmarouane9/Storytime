import { saveSchema, type Book } from "./domain.js";

export class RevisionConflict extends Error {}
export interface Snapshot { book: Book; revision: number }
export interface BookApi {
  authenticate: () => Promise<{ id: string; confirmedAt?: string } | null>;
  read: (ownerId: string) => Promise<Snapshot>;
  write: (ownerId: string, snapshot: Snapshot) => Promise<number>;
}
export function makeBookHandler(api: BookApi) {
  return async (request: Request): Promise<Response> => {
    const respond = (body: unknown, status = 200) => Response.json(body, { status, headers: { "Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff" } });
    try {
      if (!["GET", "PUT"].includes(request.method)) return new Response("Method not allowed", { status: 405, headers: { Allow: "GET, PUT" } });
      const user = await api.authenticate();
      if (!user?.confirmedAt) return respond({ error: "Sign in with a confirmed account to open your book." }, 401);
      if (request.method === "GET") return respond(await api.read(user.id));
      if (request.headers.get("Origin") !== new URL(request.url).origin) return respond({ error: "Cross-site updates are not allowed." }, 403);
      if (!request.headers.get("Content-Type")?.startsWith("application/json")) return respond({ error: "Send a JSON book." }, 415);
      const text = await request.text();
      if (new TextEncoder().encode(text).length > 2_000_000) return respond({ error: "The book exceeds the 2 MB upload limit." }, 413);
      let input: unknown;
      try { input = JSON.parse(text); } catch { return respond({ error: "The book is not valid JSON." }, 400); }
      const parsed = saveSchema.safeParse(input);
      if (!parsed.success) return respond({ error: "The book contains invalid records, dates, or amounts. Check the imported data." }, 422);
      const revision = await api.write(user.id, parsed.data);
      return respond({ revision });
    } catch (error) {
      if (error instanceof RevisionConflict) return respond({ error: "This book changed in another tab. Reload before editing again; your latest change was not saved." }, 409);
      return respond({ error: "The book is temporarily unavailable. Retry in a moment; no successful save has been reported." }, 503);
    }
  };
}
