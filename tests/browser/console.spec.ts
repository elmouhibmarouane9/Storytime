import { expect, test } from "@playwright/test";

test("all seven sample pages render without browser exceptions", async ({ page }) => {
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  await page.goto("/");
  await page.getByRole("button", { name: "Explore the sample console" }).click();
  await expect(page.locator("html")).toHaveCSS("background-color", "rgb(10, 13, 17)");
  await page.screenshot({ path: test.info().outputPath("console.png"), fullPage: true });
  for (const title of ["Ops pulse", "Client relationships", "Invoice ledger", "Financial position", "Project control", "Client communications", "Your operations book"]) {
    await page.getByRole("navigation").getByRole("button", { name: title }).click();
    await expect(page.getByRole("heading", { level: 1, name: title })).toBeVisible();
  }
  expect(errors).toEqual([]);
});

test("sample data is searchable and cannot be edited", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: "Explore the sample console" }).click();
  await page.getByRole("navigation").getByRole("button", { name: "Client relationships" }).click();
  await page.getByRole("searchbox").fill("Nordwind");
  await expect(page.locator("tbody tr")).toHaveCount(1);
  await page.getByRole("button", { name: "Add client", exact: true }).click();
  await expect(page.getByRole("status").filter({ hasText: "read-only" })).toBeVisible();
  await expect(page.locator("dialog")).toHaveCount(0);
});

test("original Spanish templates generate editable downloadable drafts", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: "Explore the sample console" }).click();
  await page.getByRole("navigation").getByRole("button", { name: "Client communications" }).click();
  await page.locator("#draft-client").selectOption("C-002");
  await page.locator("#draft-language").selectOption("es");
  await page.getByRole("button", { name: "Create draft", exact: true }).click();
  await expect(page.locator("#draft-body")).toContainText("Casa Ferrer");
  await expect(page.locator("#draft-body")).toContainText("Asunto:");
  await page.locator("#draft-body").fill("A revised message, ready for your own inbox.");
  const download = page.waitForEvent("download");
  await page.getByRole("button", { name: "Download .txt" }).click();
  expect((await download).suggestedFilename()).toBe("mim-lead_followup.txt");
});

test("mobile navigation fits without horizontal page overflow", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/");
  await page.getByRole("button", { name: "Explore the sample console" }).click();
  await expect(page.getByRole("heading", { name: "Ops pulse", exact: true })).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  await page.getByRole("navigation").getByRole("button", { name: "Project control" }).click();
  await expect(page.getByRole("heading", { name: "Project control", exact: true })).toBeVisible();
});

test("anonymous API access is denied by the deployed function runtime", async ({ request }) => {
  const response = await request.get("/api/book");
  expect(response.status()).toBe(401);
  expect(response.headers()["cache-control"]).toContain("no-store");
});
