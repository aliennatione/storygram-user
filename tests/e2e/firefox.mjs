import assert from "node:assert/strict";
import { execFileSync, spawn } from "node:child_process";
import { existsSync, mkdtempSync, readdirSync, readFileSync, rmSync } from "node:fs";
import net from "node:net";
import { tmpdir } from "node:os";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const repo = join(dirname(fileURLToPath(import.meta.url)), "..", "..");

function freePort() {
  return new Promise((resolve, reject) => {
    const server = net.createServer();
    server.on("error", reject);
    server.listen(0, "127.0.0.1", () => {
      const address = server.address();
      const port = typeof address === "object" && address ? address.port : 0;
      server.close(() => resolve(port));
    });
  });
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

async function startGeckodriver(port) {
  const child = spawn("geckodriver", ["--port", String(port), "--binary", "/usr/bin/firefox"], {
    stdio: ["ignore", "pipe", "pipe"],
  });
  let stderr = "";
  child.stderr.on("data", (chunk) => {
    stderr += chunk.toString();
  });
  for (let attempt = 0; attempt < 50; attempt += 1) {
    try {
      const response = await fetch(`http://127.0.0.1:${port}/status`);
      if (response.ok) return child;
    } catch {
      // geckodriver is still starting
    }
    await new Promise((resolve) => setTimeout(resolve, 200));
  }
  child.kill("SIGTERM");
  throw new Error(`geckodriver did not start: ${stderr}`);
}

async function webdriver(port, method, path, body) {
  const response = await fetch(`http://127.0.0.1:${port}${path}`, {
    method,
    headers: body === undefined ? {} : { "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  const payload = await response.json();
  if (!response.ok || payload.value?.error) {
    throw new Error(`WebDriver ${method} ${path} failed: ${JSON.stringify(payload)}`);
  }
  return payload.value;
}

async function main() {
  const root = mkdtempSync(join(tmpdir(), "storygram-firefox-"));
  let server;
  let gecko;
  let sessionId;
  const port = await freePort();
  try {
    execFileSync("python", ["-m", "storygram", "init", root], {
      cwd: repo,
      env: { ...process.env, PYTHONPATH: join(repo, "src") },
      stdio: "pipe",
    });
    server = await startServer(root);
    gecko = await startGeckodriver(port);
    const session = await webdriver(port, "POST", "/session", {
      capabilities: {
        alwaysMatch: {
          browserName: "firefox",
          "moz:firefoxOptions": { args: ["-headless"] },
        },
      },
    });
    sessionId = session.sessionId;

    const sessionPath = `/session/${sessionId}`;
    const elementKey = "element-6066-11e4-a52e-4f735466cecf";

    const navigate = (url) => webdriver(port, "POST", `${sessionPath}/url`, { url });
    const find = (using, value) =>
      webdriver(port, "POST", `${sessionPath}/element`, { using, value });
    const css = (value) => find("css selector", value);
    const xpath = (value) => find("xpath", value);
    const click = async (element) =>
      webdriver(port, "POST", `${sessionPath}/element/${element[elementKey]}/click`, {});
    const sendKeys = async (element, text) =>
      webdriver(port, "POST", `${sessionPath}/element/${element[elementKey]}/value`, { text });
    const text = async (element) =>
      webdriver(port, "GET", `${sessionPath}/element/${element[elementKey]}/text`);
    const bodyText = async () => text(await css("body"));
    const waitForText = async (needle) => {
      for (let attempt = 0; attempt < 100; attempt += 1) {
        if ((await bodyText()).includes(needle)) return;
        await new Promise((resolve) => setTimeout(resolve, 100));
      }
      throw new Error(`timed out waiting for text: ${needle}`);
    };

    await navigate(server.base);
    await waitForText("Storygram");

    await navigate(`${server.base}?lang=it`);
    const italian = await bodyText();
    assert.match(italian, /Aggiungi memoria/);
    assert.match(italian, /Coda di revisione/);
    assert.match(italian, /Cronologia/);

    await navigate(`${server.base}memories/new`);
    await waitForText("Add memory");
    await sendKeys(await css('input[name="title"]'), "Firefox memory input");
    await sendKeys(await css('input[name="captured_at"]'), "1987");
    await sendKeys(
      await css('textarea[name="text"]'),
      "A memory entered through Firefox WebDriver.",
    );
    await sendKeys(await css('input[name="tags"]'), "firefox, memory");
    await click(await xpath("//button[normalize-space()='Save pending proposal']"));
    await waitForText("Dry-run preview");

    const pendingFiles = readdirSync(join(root, "proposals")).filter((name) =>
      name.endsWith(".json"),
    );
    assert.equal(pendingFiles.length, 1);
    const proposal = JSON.parse(readFileSync(join(root, "proposals", pendingFiles[0]), "utf8"));
    const record = proposal.operations[0].record;
    assert.equal(record.type, "Episode");
    assert.equal(record.content.text, "A memory entered through Firefox WebDriver.");

    await click(await xpath("//button[normalize-space()='Approve without commit']"));
    await waitForText("merged");
    const episodePath = join(
      root,
      "data",
      "episodes",
      `${record.id.replace(":", "_")}.json`,
    );
    assert.ok(existsSync(episodePath));

    await navigate(`${server.base}records?q=firefox`);
    await waitForText("Episode");
    assert.match(await bodyText(), new RegExp(record.id));

    for (const name of ["Firefox Nonna", "Firefox Nonno"]) {
      await navigate(`${server.base}people/new`);
      await waitForText("Add person");
      await sendKeys(await css('input[name="name"]'), name);
      await click(await css(`input[name="evidence"][value="${record.id}"]`));
      await click(await xpath("//button[normalize-space()='Save pending proposal']"));
      await waitForText("Dry-run preview");
      await click(await xpath("//button[normalize-space()='Approve without commit']"));
      await waitForText("merged");
    }
    const formPeople = readdirSync(join(root, "data", "people"))
      .map((file) => JSON.parse(readFileSync(join(root, "data", "people", file), "utf8")))
      .map((person) => person.id)
      .sort();
    assert.equal(formPeople.length, 2);

    await navigate(`${server.base}relationships/new`);
    await waitForText("Add relationship");
    await click(await xpath(`//select[@name='subject']/option[@value='${formPeople[0]}']`));
    await click(
      await xpath("//select[@name='predicate']/option[@value='relation:parent']"),
    );
    await click(await xpath(`//select[@name='object']/option[@value='${formPeople[1]}']`));
    await click(await css(`input[name="evidence"][value="${record.id}"]`));
    await click(await xpath("//button[normalize-space()='Save pending proposal']"));
    await waitForText("Dry-run preview");
    await click(await xpath("//button[normalize-space()='Approve without commit']"));
    await waitForText("merged");
    assert.equal(readdirSync(join(root, "data", "relationships")).length, 1);

    await navigate(`${server.base}sources/new`);
    await waitForText("Add source");
    await sendKeys(await css('input[name="title"]'), "Firefox register");
    await click(await xpath("//select[@name='source_type']/option[@value='registry']"));
    await click(await xpath("//button[normalize-space()='Save pending proposal']"));
    await waitForText("Dry-run preview");
    await click(await xpath("//button[normalize-space()='Approve without commit']"));
    await waitForText("merged");
    assert.equal(readdirSync(join(root, "data", "sources")).length, 1);

    await navigate(`${server.base}assertions/new`);
    await waitForText("Add assertion");
    await click(await xpath(`//select[@name='subject']/option[@value='${formPeople[0]}']`));
    await sendKeys(await css('input[name="predicate"]'), "relation:lived_in");
    await sendKeys(await css('input[name="value"]'), "Firefox family home");
    await click(await css(`input[name="evidence"][value="${record.id}"]`));
    await click(await xpath("//button[normalize-space()='Save pending proposal']"));
    await waitForText("Dry-run preview");
    await click(await xpath("//button[normalize-space()='Approve without commit']"));
    await waitForText("merged");
    assert.equal(readdirSync(join(root, "data", "assertions")).length, 1);

    console.log(
      "Firefox WebDriver e2e: bilingual home, add memory, source/person/relationship/assertion forms and approval passed",
    );
  } finally {
    if (sessionId) {
      await webdriver(port, "DELETE", `/session/${sessionId}`).catch(() => {});
    }
    if (gecko) gecko.kill("SIGTERM");
    if (server?.child) server.child.kill("SIGTERM");
    rmSync(root, { recursive: true, force: true });
  }
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
