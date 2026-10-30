import assert from "node:assert/strict";
import { execFileSync, spawn } from "node:child_process";
import { existsSync, mkdtempSync, readFileSync, rmSync } from "node:fs";
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

  await page.goto(`${server.base}proposals/new`);
  await page.locator('textarea[name="json"]').fill(
    JSON.stringify(proposal("proposal:e2e-1", "episode:e2e-note", "Browser approve flow")),
  );
  await page.getByRole("button", { name: "Save pending proposal" }).click();
  await page.waitForSelector("text=Dry-run preview");
  assert.match(page.url(), /proposal%3Ae2e-1/);
  assert.ok(existsSync(join(root, "proposals", "proposal_e2e-1.json")));

  await page.getByRole("button", { name: "Approve without commit" }).click();
  await page.waitForFunction(() => document.body.innerText.includes("merged"));
  assert.ok(existsSync(join(root, "data", "episodes", "episode_e2e-note.json")));
  assert.ok(existsSync(join(root, "data", "proposals", "proposal_e2e-1.json")));
  assert.ok(!existsSync(join(root, "proposals", "proposal_e2e-1.json")));

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

  console.log("Playwright e2e: approve and reject flows passed");
} finally {
  if (browser) await browser.close();
  if (server?.child) server.child.kill("SIGTERM");
  rmSync(root, { recursive: true, force: true });
}
