import fs from "fs";
import http from "http";
import path from "path";
import { fileURLToPath } from "url";

const dir = path.dirname(fileURLToPath(import.meta.url));
const file = path.join(dir, "Hamzaban_roadmap_v1.html");
const port = 47321;
const phases = ["now", "next", "later"];
const enName = { now: "Now", next: "Next", later: "Later" };
const faName = { now: "اکنون", next: "بعدی", later: "بعدتر" };

function boardRange(html, board) {
  const attr = `data-board="${board}"`;
  const attrAt = html.indexOf(attr);
  if (attrAt < 0) throw new Error("Missing the " + board + " board");
  const start = html.lastIndexOf("<div", attrAt);
  let depth = 0;
  const tags = /<\/?div\b[^>]*>/g;
  tags.lastIndex = start;
  let match;
  while ((match = tags.exec(html))) {
    depth += match[0].startsWith("</") ? -1 : 1;
    if (depth === 0) return { start, end: tags.lastIndex };
  }
  throw new Error("The " + board + " board is not closed");
}

function reorderBoard(html, board, order) {
  for (const phase of phases) {
    if (!Array.isArray(order[phase]) || !order[phase].every((id) => typeof id === "string")) {
      throw new Error("Bad order for " + board);
    }
  }
  const incoming = phases.flatMap((phase) => order[phase]);
  if (new Set(incoming).size !== incoming.length) throw new Error("A card was repeated");

  const range = boardRange(html, board);
  const region = html.slice(range.start, range.end);
  const buttons = [];
  const buttonRe = /\n[ \t]*<button class="epic"[\s\S]*?<\/button>/g;
  let match;
  while ((match = buttonRe.exec(region))) {
    const card = (match[0].match(/data-card="([^"]+)"/) || [])[1];
    const epic = (match[0].match(/data-epic="([^"]+)"/) || [])[1];
    if (!card || !epic) throw new Error("A card is missing its id");
    buttons.push({ card, epic, html: match[0] });
  }
  const known = new Set(buttons.map((button) => button.card));
  if (incoming.length !== buttons.length || incoming.some((id) => !known.has(id))) {
    throw new Error("The cards on the " + board + " board do not match the file");
  }

  const byCard = Object.fromEntries(buttons.map((button) => [button.card, button.html]));
  const stacks = [];
  const stackRe = /<div class="stack">[\s\S]*?<\/div>/g;
  while ((match = stackRe.exec(region))) {
    const before = region.slice(0, match.index);
    const marks = [...before.matchAll(/class="col (now|next|later)"/g)];
    stacks.push({ phase: marks[marks.length - 1][1], index: match.index, length: match[0].length });
  }
  if (stacks.length !== 3) throw new Error("Expected three columns on the " + board + " board");

  let nextRegion = region;
  stacks.sort((a, b) => b.index - a.index).forEach((stack) => {
    const lineStart = nextRegion.lastIndexOf("\n", stack.index) + 1;
    const stackIndent = nextRegion.slice(lineStart, stack.index);
    const ids = order[stack.phase];
    const inner = ids.map((id) => byCard[id]).join("") + "\n" + stackIndent;
    const replacement = `<div class="stack">${inner}</div>`;
    nextRegion = nextRegion.slice(0, stack.index) + replacement + nextRegion.slice(stack.index + stack.length);
  });

  const epicPhases = new Map();
  const epicOf = Object.fromEntries(buttons.map((button) => [button.card, button.epic]));
  for (const phase of phases) {
    for (const card of order[phase]) {
      const epic = epicOf[card];
      const previous = epicPhases.get(epic);
      epicPhases.set(epic, previous && previous !== phase ? "mixed" : phase);
    }
  }
  return {
    html: html.slice(0, range.start) + nextRegion + html.slice(range.end),
    epicPhases,
  };
}

function updateArticle(html, epic, phase) {
  const articleRe = new RegExp(`<article id="${epic}"[\\s\\S]*?</article>`);
  const article = html.match(articleRe);
  if (!article) return html;
  const labelRe = /<div class="label(?: next| later)?">[\s\S]*?<\/div>/;
  const label = article[0].match(labelRe);
  if (!label || !/Now|Next|Later/.test(label[0]) || !/اکنون|بعدی|بعدتر/.test(label[0])) return html;
  const className = phase === "now" ? "label" : `label ${phase}`;
  let updated = label[0].replace(/class="label(?: next| later)?"/, `class="${className}"`);
  updated = updated.replace(/Now|Next|Later/, enName[phase]);
  updated = updated.replace(/اکنون|بعدی|بعدتر/, faName[phase]);
  return html.replace(article[0], article[0].replace(label[0], updated));
}

const mvpRole = {
  now: ["Client", "مراجع"],
  next: ["Therapist", "درمانگر"],
  later: ["Admin", "مدیر"],
};

function updateMvpArticle(html, epic, phase) {
  const articleRe = new RegExp(`<article id="${epic}"[\\s\\S]*?</article>`);
  const article = html.match(articleRe);
  if (!article) return html;
  const labelRe = /<div class="label(?: next| later)?">[\s\S]*?<\/div>/;
  const label = article[0].match(labelRe);
  if (!label) return html;
  const className = phase === "now" ? "label" : `label ${phase}`;
  let updated = label[0].replace(/class="label(?: next| later)?"/, `class="${className}"`);
  updated = updated.replace(/MVP · (?:Client|Therapist|Admin)/, "MVP · " + mvpRole[phase][0]);
  updated = updated.replace(/نسخهٔ اول · (?:مراجع|درمانگر|مدیر)/, "نسخهٔ اول · " + mvpRole[phase][1]);
  return html.replace(article[0], article[0].replace(label[0], updated));
}

function applyOrder(html, boards) {
  if (!boards || typeof boards !== "object") throw new Error("Bad order");
  const epicPhases = new Map();
  for (const board of ["client", "therapist"]) {
    if (!boards[board]) throw new Error("Missing the " + board + " board");
    const result = reorderBoard(html, board, boards[board]);
    html = result.html;
    for (const [epic, phase] of result.epicPhases) {
      const previous = epicPhases.get(epic);
      epicPhases.set(epic, previous && previous !== phase ? "mixed" : phase);
    }
  }
  for (const [epic, phase] of epicPhases) {
    if (phase === "mixed") continue;
    html = epic.startsWith("mvp-") ? updateMvpArticle(html, epic, phase) : updateArticle(html, epic, phase);
  }
  return html;
}

let writing = Promise.resolve();

function stampHtml(html) {
  const tag = `<meta name="hamzaban-saved" content="${Date.now()}" />`;
  if (/<meta name="hamzaban-saved" content="\d+" \/>/.test(html)) {
    return html.replace(/<meta name="hamzaban-saved" content="\d+" \/>/, tag);
  }
  return html.replace("<head>", "<head>\n  " + tag);
}

function writeOrder(boards) {
  writing = writing.catch(() => {}).then(() => {
    const html = fs.readFileSync(file, "utf8");
    const next = stampHtml(applyOrder(html, boards));
    const temp = file + ".tmp";
    fs.writeFileSync(temp, next);
    fs.renameSync(temp, file);
  });
  return writing;
}

function send(res, status, body) {
  res.writeHead(status, {
    "Content-Type": "application/json; charset=utf-8",
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Private-Network": "true",
    "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type",
    "Cache-Control": "no-store",
  });
  res.end(body);
}

const server = http.createServer((req, res) => {
  if (req.method === "OPTIONS") {
    send(res, 204, "");
    return;
  }
  if (req.method === "GET" && (req.url === "/health" || req.url.startsWith("/health?"))) {
    send(res, 200, JSON.stringify({ ok: true }));
    return;
  }
  if (req.method === "GET") {
    const url = new URL(req.url, "http://127.0.0.1");
    const name = decodeURIComponent(url.pathname === "/" ? "/Hamzaban_roadmap_v1.html" : url.pathname);
    const target = path.resolve(dir, "." + name);
    if (!target.startsWith(dir + path.sep) && target !== path.join(dir, "Hamzaban_roadmap_v1.html")) {
      send(res, 404, JSON.stringify({ ok: false }));
      return;
    }
    if (!fs.existsSync(target) || !fs.statSync(target).isFile()) {
      send(res, 404, JSON.stringify({ ok: false }));
      return;
    }
    const type = target.endsWith(".svg") ? "image/svg+xml" : "text/html; charset=utf-8";
    res.writeHead(200, {
      "Content-Type": type,
      "Cache-Control": "no-store, no-cache, must-revalidate",
      "Pragma": "no-cache",
    });
    res.end(fs.readFileSync(target));
    return;
  }
  if (req.method === "POST" && req.url === "/order") {
    let body = "";
    req.on("data", (chunk) => {
      body += chunk;
      if (body.length > 100000) req.destroy();
    });
    req.on("end", () => {
      let boards;
      try {
        boards = JSON.parse(body);
      } catch {
        send(res, 400, JSON.stringify({ ok: false, error: "Bad order" }));
        return;
      }
      writeOrder(boards)
        .then(() => send(res, 200, JSON.stringify({ ok: true })))
        .catch((error) => send(res, 400, JSON.stringify({ ok: false, error: error.message })));
    });
    return;
  }
  send(res, 404, JSON.stringify({ ok: false }));
});

server.listen(port, "127.0.0.1");
