import assert from "node:assert/strict";
import { execFileSync, spawn } from "node:child_process";
import { existsSync, mkdtempSync, readdirSync, readFileSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { chromium } from "playwright";

const repo = join(dirname(fileURLToPath(import.meta.url)), "..", "..");
const now = "2026-10-30T12:00:00+00:00";

function proposal(id, episodeId, title) {
  return {
    id,
    type: "Proposal",
    status: "proposed",
    created_at: now,
    updated_at: now,
    title,
    operations: [
      {
        op: "create",
        record_type: "Episode",
        record: {
          id: episodeId,
          type: "Episode",
          episode_type: "other",
          status: "reported",
          visibility: "family",
          created_at: now,
          updated_at: now,
        },
      },
    ],
  };
}

function startServer(root) {
  const child = spawn(
    "python",
    ["-u", "-m", "storygram", "web", "--archive", root, "--host", "127.0.0.1", "--port", "0"],
    {
      cwd: repo,
      env: { ...process.env, PYTHONPATH: join(repo, "src") },
      stdio: ["ignore", "pipe", "pipe"],
    },
  );
  return new Promise((resolve, reject) => {
    const timer = setTimeout(() => reject(new Error("web server did not start")), 15000);
    let stderr = "";
    let buffer = "";
    child.stderr.on("data", (chunk) => {
      stderr += chunk.toString();
    });
    child.stdout.on("data", (chunk) => {
      buffer += chunk.toString();
      const match = buffer.match(/http:\/\/127\.0\.0\.1:\d+\//);
      if (match) {
        clearTimeout(timer);
        resolve({ child, base: match[0] });
      }
    });
    child.on("exit", (code) => {
      clearTimeout(timer);
      reject(new Error(`web server exited early (${code}): ${stderr}`));
    });
  });
}

const root = mkdtempSync(join(tmpdir(), "storygram-e2e-"));
let server;
let browser;
try {
  execFileSync("python", ["-m", "storygram", "init", root], {
    cwd: repo,
    env: { ...process.env, PYTHONPATH: join(repo, "src") },
    stdio: "pipe",
  });
  server = await startServer(root);
  const executablePath = [
    process.env.CHROMIUM_PATH,
    "/usr/bin/chromium",
    "/usr/bin/chromium-browser",
  ].find((candidate) => candidate && existsSync(candidate));
  browser = await chromium.launch({
    headless: true,
    ...(executablePath ? { executablePath } : {}),
    args: ["--no-sandbox", "--disable-dev-shm-usage"],
  });
  const page = await browser.newPage();
  await page.goto(server.base);
  assert.match(await page.locator("h1").innerText(), /Storygram/);
  await page.getByRole("link", { name: "Generate", exact: true }).click();
  await page.waitForSelector('textarea[name="source"]');
  assert.match(await page.locator("h1").innerText(), /Generate proposal/);

  await page.goto(`${server.base}proposals/new`);
  await page.locator('textarea[name="json"]').fill(
    JSON.stringify(proposal("proposal:e2e-1", "episode:e2e-note", "Browser approve flow")),
  );
  await page.getByRole("button", { name: "Save pending proposal" }).click();
  await page.waitForSelector("text=Dry-run preview");
  assert.match(page.url(), /proposal%3Ae2e-1/);
  assert.ok(existsSync(join(root, "proposals", "proposal_e2e-1.json")));

  await page.getByRole("link", { name: "Edit pending proposal" }).click();
  const draft = JSON.parse(await page.locator('textarea[name="json"]').inputValue());
  draft.title = "Edited browser proposal";
  await page.locator('textarea[name="json"]').fill(JSON.stringify(draft, null, 2));
  await page.getByRole("button", { name: "Save pending proposal" }).click();
  await page.waitForFunction(() => document.body.innerText.includes("Edited browser proposal"));
  const edited = JSON.parse(
    readFileSync(join(root, "proposals", "proposal_e2e-1.json"), "utf8"),
  );
  assert.equal(edited.title, "Edited browser proposal");

  await page.getByRole("button", { name: "Approve without commit" }).click();
  await page.waitForFunction(() => document.body.innerText.includes("merged"));
  assert.ok(existsSync(join(root, "data", "episodes", "episode_e2e-note.json")));
  assert.ok(existsSync(join(root, "data", "proposals", "proposal_e2e-1.json")));
  assert.ok(!existsSync(join(root, "proposals", "proposal_e2e-1.json")));

  await page.goto(`${server.base}records`);
  await page.locator('input[name="q"]').fill("e2e-note");
  await page.getByRole("button", { name: "Filter" }).click();
  await page.getByRole("link", { name: "episode:e2e-note", exact: true }).click();
  await page.waitForFunction(() => document.body.innerText.includes("Record JSON"));
  assert.match(page.url(), /records\/episode%3Ae2e-note/);
  assert.match(await page.locator("h1").innerText(), /episode:e2e-note/);

  await page.goto(`${server.base}records?visibility=family`);
  assert.match(await page.locator("body").innerText(), /episode:e2e-note/);
  const exported = await page.request.get(`${server.base}export?format=json&visibility=family`);
  assert.equal(exported.status(), 200);
  assert.match(exported.headers()["content-disposition"], /attachment/);
  const exportedRecords = await exported.json();
  assert.ok(exportedRecords.some((record) => record.id === "episode:e2e-note"));

  const relations = {
    id: "proposal:e2e-relations",
    type: "Proposal",
    status: "proposed",
    created_at: now,
    updated_at: now,
    title: "Browser timeline and genogram flow",
    operations: [
      {
        op: "create",
        record_type: "Person",
        evidence: ["episode:e2e-note"],
        record: {
          id: "person:e2e-anna",
          type: "Person",
          name: "Anna E2E",
          status: "confirmed",
          created_at: now,
          updated_at: now,
        },
      },
      {
        op: "create",
        record_type: "Person",
        evidence: ["episode:e2e-note"],
        record: {
          id: "person:e2e-bruno",
          type: "Person",
          name: "Bruno E2E",
          status: "confirmed",
          created_at: now,
          updated_at: now,
        },
      },
      {
        op: "create",
        record_type: "Relationship",
        evidence: ["episode:e2e-note"],
        record: {
          id: "relationship:e2e-parent",
          type: "Relationship",
          subject: "person:e2e-anna",
          predicate: "relation:parent",
          object: "person:e2e-bruno",
          status: "reported",
          valid_time: { start: "1987", end: "1995", precision: "year" },
          transaction_time: { recorded_at: now, recorded_until: null },
          created_at: now,
          updated_at: now,
        },
      },
      {
        op: "create",
        record_type: "Assertion",
        evidence: ["episode:e2e-note"],
        record: {
          id: "assertion:e2e-parent",
          type: "Assertion",
          subject: "person:e2e-anna",
          predicate: "relation:parent",
          object: "person:e2e-bruno",
          status: "reported",
          valid_time: { start: "2000", end: "2010", precision: "year" },
          transaction_time: {
            recorded_at: "2026-02-01T00:00:00+00:00",
            recorded_until: null,
          },
          produced_by: ["episode:e2e-note"],
          created_at: now,
          updated_at: now,
        },
      },
    ],
  };
  await page.goto(`${server.base}proposals/new`);
  await page.locator('textarea[name="json"]').fill(JSON.stringify(relations));
  await page.getByRole("button", { name: "Save pending proposal" }).click();
  await page.waitForSelector("text=Dry-run preview");
  await page.getByRole("button", { name: "Approve without commit" }).click();
  await page.waitForFunction(() => document.body.innerText.includes("merged"));

  await page.getByRole("link", { name: "Timeline", exact: true }).click();
  await page.waitForSelector('input[name="id"]');
  assert.match(await page.locator("h1").innerText(), /Timeline/);
  assert.match(await page.locator("body").innerText(), /assertion:e2e-parent/);
  await page.locator('input[name="id"]').fill("person:e2e-anna");
  await page.getByRole("button", { name: "Show timeline" }).click();
  await page.waitForURL(/id=person%3Ae2e-anna/);
  assert.match(await page.locator("body").innerText(), /assertion:e2e-parent/);
  await page.getByRole("link", { name: "assertion:e2e-parent", exact: true }).click();
  await page.waitForFunction(() => document.body.innerText.includes("Record JSON"));
  assert.match(page.url(), /records\/assertion%3Ae2e-parent/);

  await page.getByRole("link", { name: "Genogram", exact: true }).click();
  await page.waitForSelector('input[name="id"]');
  await page.locator('input[name="id"]').fill("person:e2e-anna");
  await page.getByRole("button", { name: "Show genogram" }).click();
  await page.waitForURL(/id=person%3Ae2e-anna/);
  const genogramText = await page.locator("body").innerText();
  assert.match(genogramText, /relation:parent/);
  assert.match(genogramText, /Experimental/);
  assert.match(genogramText, /1987/);
  assert.match(genogramText, /2000/);
  assert.match(genogramText, /relationship:e2e-parent/);
  assert.match(genogramText, /assertion:e2e-parent/);

  await page.goto(`${server.base}?lang=it`);
  const italianHome = await page.locator("body").innerText();
  assert.match(italianHome, /Aggiungi memoria/);
  assert.match(italianHome, /Coda di revisione/);
  assert.match(italianHome, /Cronologia/);
  await page.goto(server.base);

  await page
    .getByRole("banner")
    .getByRole("link", { name: "Add memory", exact: true })
    .click();
  await page.waitForSelector('textarea[name="text"]');
  assert.match(await page.locator("h1").innerText(), /Add memory/);
  await page.locator('input[name="title"]').fill("Browser memory input");
  await page.locator('input[name="captured_at"]').fill("1987");
  await page
    .locator('textarea[name="text"]')
    .fill("A memory entered through the browser form.");
  await page.locator('input[name="tags"]').fill("e2e, memory");
  await page.getByRole("button", { name: "Save pending proposal" }).click();
  await page.waitForSelector("text=Dry-run preview");
  const pendingFiles = readdirSync(join(root, "proposals")).filter((name) =>
    name.endsWith(".json"),
  );
  assert.equal(pendingFiles.length, 1);
  const memoryProposal = JSON.parse(
    readFileSync(join(root, "proposals", pendingFiles[0]), "utf8"),
  );
  assert.equal(memoryProposal.status, "proposed");
  const memoryRecord = memoryProposal.operations[0].record;
  assert.equal(memoryRecord.type, "Episode");
  assert.equal(memoryRecord.content.text, "A memory entered through the browser form.");
  await page.getByRole("button", { name: "Approve without commit" }).click();
  await page.waitForFunction(() => document.body.innerText.includes("merged"));
  assert.ok(
    existsSync(join(root, "data", "episodes", `${memoryRecord.id.replace(":", "_")}.json`)),
  );

  await page.goto(`${server.base}proposals/new`);
  await page.locator('textarea[name="json"]').fill(
    JSON.stringify(proposal("proposal:e2e-2", "episode:e2e-note-2", "Browser reject flow")),
  );
  await page.getByRole("button", { name: "Save pending proposal" }).click();
  await page.getByPlaceholder("Rejection reason (optional)").fill("duplicate");
  await page.getByRole("button", { name: "Reject" }).click();
  await page.waitForFunction(() => document.body.innerText.includes("rejected"));
  const rejected = JSON.parse(
    readFileSync(join(root, "proposals", "proposal_e2e-2.json"), "utf8"),
  );
  assert.equal(rejected.status, "rejected");
  assert.equal(rejected.notes, "duplicate");

  console.log(
    "Playwright e2e: edit, approve, reject, browse, visibility export, timeline, genogram, add memory and Italian UI flows passed",
  );
} finally {
  if (browser) await browser.close();
  if (server?.child) server.child.kill("SIGTERM");
  rmSync(root, { recursive: true, force: true });
}
