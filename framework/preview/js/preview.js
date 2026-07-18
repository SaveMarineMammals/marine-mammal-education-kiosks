const TOKENS_URL = new URL("../../branding/tokens.json", import.meta.url);
const COPY_URL = new URL("../../../exhibits/humpback-migration/copy/en.md", import.meta.url);

const statusEl = document.getElementById("status");

function setStatus(message, state = "ok") {
  if (!statusEl) return;
  statusEl.textContent = message;
  statusEl.dataset.state = state;
}

function applyTokens(tokens) {
  const root = document.documentElement;
  const colors = tokens.colors || {};
  for (const [name, value] of Object.entries(colors)) {
    root.style.setProperty(`--${name}`, value);
  }

  const typography = tokens.typography || {};
  if (typography.display) {
    const display = String(typography.display).split("—")[0].trim();
    root.style.setProperty("--font-display", `"${display}", "Georgia", serif`);
    const el = document.getElementById("font-display");
    if (el) el.textContent = display;
  }
  if (typography.body) {
    const body = String(typography.body).split("—")[0].trim();
    root.style.setProperty("--font-body", `"${body}", "Segoe UI", sans-serif`);
    const el = document.getElementById("font-body");
    if (el) el.textContent = body;
  }
  if (typography.minCaptionPx) {
    root.style.setProperty("--min-caption", String(typography.minCaptionPx));
    const el = document.getElementById("min-caption");
    if (el) el.textContent = String(typography.minCaptionPx);
  }

  if (tokens.canvas?.width) {
    root.style.setProperty("--canvas-w", String(tokens.canvas.width));
  }
  if (tokens.canvas?.height) {
    root.style.setProperty("--canvas-h", String(tokens.canvas.height));
  }

  const swatches = document.getElementById("swatches");
  if (!swatches) return;
  swatches.replaceChildren();
  Object.entries(colors).forEach(([name, value], index) => {
    const card = document.createElement("div");
    card.className = "swatch";
    card.style.animationDelay = `${0.04 * index}s`;
    card.innerHTML = `
      <div class="swatch-chip" style="background:${value}"></div>
      <div class="swatch-meta">
        <strong>${name}</strong>
        <span>${value}</span>
      </div>
    `;
    swatches.appendChild(card);
  });
}

function parseCopyMarkdown(md) {
  const sections = {};
  let current = null;
  for (const line of md.split(/\r?\n/)) {
    const heading = line.match(/^##\s+(.+)\s*$/);
    if (heading) {
      current = heading[1].trim().toLowerCase();
      sections[current] = [];
      continue;
    }
    if (!current) continue;
    if (line.startsWith("# ")) continue;
    sections[current].push(line);
  }
  const text = (key) => (sections[key] || []).join("\n").trim();
  return {
    title: text("title") || "Untitled exhibit",
    caption: text("short caption") || "",
    cta: text("call to action") || "",
  };
}

function bindCopy(copy) {
  document.querySelectorAll("[data-bind='title']").forEach((el) => {
    el.textContent = copy.title;
  });
  document.querySelectorAll("[data-bind='caption']").forEach((el) => {
    el.textContent = copy.caption;
  });
  document.querySelectorAll("[data-bind='cta']").forEach((el) => {
    el.textContent = copy.cta;
  });
}

async function main() {
  try {
    const tokensRes = await fetch(TOKENS_URL);
    if (!tokensRes.ok) {
      throw new Error(`Could not load tokens.json (${tokensRes.status})`);
    }
    const tokens = await tokensRes.json();
    applyTokens(tokens);

    let copyNote = "using built-in sample copy";
    try {
      const copyRes = await fetch(COPY_URL);
      if (copyRes.ok) {
        bindCopy(parseCopyMarkdown(await copyRes.text()));
        copyNote = "loaded humpback-migration copy";
      }
    } catch {
      // Keep HTML defaults when opened without exhibit path available.
    }

    setStatus(`Tokens loaded · ${copyNote}`, "ok");
  } catch (err) {
    const message = err instanceof Error ? err.message : String(err);
    setStatus(
      `${message}. Serve from the repo root (see framework/preview/README.md).`,
      "error",
    );
  }
}

main();
