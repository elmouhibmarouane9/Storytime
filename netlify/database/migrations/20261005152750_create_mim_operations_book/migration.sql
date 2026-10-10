CREATE TABLE "mim_books" (
	"owner_id" text PRIMARY KEY,
	"settings" jsonb NOT NULL,
	"revision" integer DEFAULT 0 NOT NULL,
	"updated_at" timestamp with time zone DEFAULT now() NOT NULL
);
--> statement-breakpoint
CREATE TABLE "mim_records" (
	"owner_id" text,
	"collection" text,
	"record_id" text,
	"data" jsonb NOT NULL,
	CONSTRAINT "mim_records_pkey" PRIMARY KEY("owner_id","collection","record_id")
);
--> statement-breakpoint
ALTER TABLE "mim_records" ADD CONSTRAINT "mim_records_owner_id_mim_books_owner_id_fkey" FOREIGN KEY ("owner_id") REFERENCES "mim_books"("owner_id") ON DELETE CASCADE;