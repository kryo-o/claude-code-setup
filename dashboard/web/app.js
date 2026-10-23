// Builds every node with textContent: the data includes text from third-party plugins.
// Styles go through element.style (CSSOM), which the page's CSP allows; style="" attributes it blocks.
"use strict";

const token = new URLSearchParams(location.search).get("t") || "";
const SVGNS = "http://www.w3.org/2000/svg";
// Colours live in app.css; SVG attributes cannot use var(), so read them once.
const css = (name) => getComputedStyle(document.documentElement).getPropertyValue(name).trim();
let inv = null;
let tab = "Home";

function build(n, attrs, kids) {
  for (const [k, v] of Object.entries(attrs || {})) {
    if (k === "onclick") n.addEventListener("click", v);
    else if (k === "style") Object.assign(n.style, v);
    else n.setAttribute(k, v);
  }
  for (const k of kids.flat(Infinity)) {
    if (k === null || k === undefined || k === false) continue;
    n.append(k instanceof Node ? k : document.createTextNode(String(k)));
  }
  return n;
}
const el = (tag, attrs, ...kids) => build(document.createElement(tag), attrs, kids);
const svg = (tag, attrs, ...kids) => build(document.createElementNS(SVGNS, tag), attrs, kids);

const usd = (v) => (v === null || v === undefined ? "?" : "$" + v.toFixed(2));
const num = (v) => (v || 0).toLocaleString();
const kTok = (v) => (v >= 1000 ? (v / 1000).toFixed(1) + "k" : String(v));
const initials = (s) => s.replace(/@.*/, "").split(/[-_\s]+/).map((w) => w[0] || "").join("").slice(0, 2).toUpperCase();

const ICONS = {
  hex: "M12 2 21 7v10l-9 5-9-5V7z M12 7l4.5 2.5v5L12 17l-4.5-2.5v-5z",
  grid: "M3 3h7v7H3z M14 3h7v7h-7z M3 14h7v7H3z M14 14h7v7h-7z",
  coin: "M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18z M9 9.5c0-1.4 1.3-2 3-2s3 .7 3 2-1.3 1.7-3 2-3 .8-3 2.2 1.3 2 3 2 3-.7 3-2 M12 6v1.5 M12 16.5V18",
  bolt: "M13 2 4 14h7l-1 8 9-12h-7z",
  brain: "M9 4a3 3 0 0 0-3 3 3 3 0 0 0-2 5 3 3 0 0 0 2 5 3 3 0 0 0 6 1V5a3 3 0 0 0-3-1z M15 4a3 3 0 0 1 3 3 3 3 0 0 1 2 5 3 3 0 0 1-2 5 3 3 0 0 1-6 1",
  alert: "M12 3 2 20h20z M12 10v4 M12 17v.5",
  clock: "M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18z M12 7v5l3 2",
  slash: "M15 3 9 21",
  pin: "M12 2v6 M8 8h8l-1 6H9z M12 14v8",
  info: "M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18z M12 11v6 M12 7.5v.5",
};
const icon = (name) => svg("svg", { viewBox: "0 0 24 24", fill: "none", stroke: "currentColor", "stroke-width": "1.6",
  "stroke-linecap": "round", "stroke-linejoin": "round", "aria-hidden": "true" }, svg("path", { d: ICONS[name] }));

let panelNo = 0;
const seq = () => String(++panelNo).padStart(2, "0");
const panel = (ic, title, meta, ...body) =>
  el("section", { class: "panel" }, el("header", {}, icon(ic), el("h2", {}, el("i", {}, seq()), title), meta || null), body);

// --- dialog: proposals and details ---
function openDialog(title, ...body) {
  document.getElementById("dlg-title").textContent = title;
  document.getElementById("dlg-body").replaceChildren(...body.flat(Infinity).filter(Boolean));
  document.getElementById("dlg").showModal();
}

function proposalBlocks(item) {
  const list = item.proposals || [];
  if (!list.length) return [el("p", { class: "note" }, "Nothing to propose for this one.")];
  return list.map((p) => el("div", { class: "prop" },
    el("h3", {}, p.title), el("p", {}, p.how), el("pre", {}, p.text),
    el("button", { type: "button", class: "chip", onclick: (e) => {
      navigator.clipboard.writeText(p.text).then(() => { e.target.textContent = "Copied"; });
    } }, "Copy")));
}

function showPlugin(p) {
  openDialog(p.id,
    el("p", { class: "note" }, [p.enabled ? "On" : "Off", p.version && "v" + p.version,
      p.frozen ? "frozen copy" : p.installed ? "updates from its author" : "built in", p.hooks && "hooks: " + p.hooks]
      .filter(Boolean).join(" · ")),
    p.path && el("p", {}, el("code", {}, p.path)),
    proposalBlocks(p));
}

function showItem(i) {
  openDialog("/" + i.name,
    el("p", { class: "note" }, `${i.source} · ${i.model || "inherits model"} · ${num(i.tokens)} tokens`),
    el("p", {}, i.description || "No description."),
    el("p", {}, el("code", {}, i.path)),
    proposalBlocks(i));
}

// --- the orbit: a dot sphere with your plugins on a ring around it ---
function orbit() {
  const W = 640, C = W / 2, R = 168;
  const pts = sphere(620);
  const rand = rng(7);
  const core = Array.from({ length: 240 }, () => {
    const g = () => (rand() + rand() + rand() - 1.5) / 1.5;
    return [g() * 0.32, g() * 0.32, g() * 0.32, rand()];
  });
  const ringPts = Array.from({ length: 110 }, (_, i) => [(i / 110) * Math.PI * 2, 0.55 + rand() * 0.1, rand()]);

  const shell = pts.map(() => svg("circle", { fill: css("--sphere") }));
  const coreDots = core.map(([, , , t]) => svg("circle", { fill: t > 0.7 ? css("--core-1") : t > 0.35 ? css("--core-2") : css("--core-3") }));
  const ringDots = ringPts.map(([, , t]) => svg("circle", { fill: t > 0.5 ? css("--core-3") : css("--core-2") }));
  const blue = Array.from({ length: 26 }, () => [rand() * Math.PI * 2, 0.5 + rand() * 0.45, (rand() - 0.5) * 0.5]);
  const blueDots = blue.map(() => svg("circle", { fill: css("--alt") }));

  const plugins = inv.plugins;
  const RING = 270;
  const nodes = plugins.map((p, i) => {
    const a = -Math.PI / 2 + (i / plugins.length) * Math.PI * 2;
    const x = C + Math.cos(a) * RING, y = C + Math.sin(a) * RING;
    const g = svg("g", { class: "node" + (p.enabled ? "" : " off"), tabindex: "0", role: "button",
      "aria-label": p.id, onclick: () => showPlugin(p) },
      svg("title", {}, `${p.id}${p.version ? " v" + p.version : ""}`),
      svg("rect", { x: x - 21, y: y - 15, width: 42, height: 30 }),
      svg("text", { x, y }, initials(p.id)),
      svg("text", { x, y: y + 34, class: "cap" }, p.frozen ? "FROZEN" : p.installed ? clip(p.version || "", 8) : "BUILT-IN"));
    g.addEventListener("keydown", (e) => { if (e.key === "Enter") showPlugin(p); });
    return g;
  });

  // HUD: degree ticks, crosshair, a radar sweep and corner readouts.
  const ticks = Array.from({ length: 72 }, (_, i) => {
    const a = (i / 72) * Math.PI * 2, long = i % 6 === 0, r1 = RING + 36, r2 = r1 + (long ? 9 : 4);
    return svg("line", { x1: C + Math.cos(a) * r1, y1: C + Math.sin(a) * r1, x2: C + Math.cos(a) * r2, y2: C + Math.sin(a) * r2,
      stroke: long ? css("--accent") : css("--hud"), "stroke-width": 1, opacity: long ? 0.7 : 1 });
  });
  const hud = svg("g", { "aria-hidden": "true" },
    svg("circle", { cx: C, cy: C, r: RING, fill: "none", stroke: css("--panel-2"), "stroke-width": 52 }),
    svg("circle", { cx: C, cy: C, r: RING + 26, fill: "none", stroke: css("--hud"), "stroke-dasharray": "2 4" }),
    svg("circle", { cx: C, cy: C, r: RING - 26, fill: "none", stroke: css("--hud-2") }),
    svg("circle", { cx: C, cy: C, r: R + 18, fill: "none", stroke: css("--hud-2"), "stroke-dasharray": "1 6" }),
    svg("line", { x1: C - R - 30, y1: C, x2: C + R + 30, y2: C, stroke: css("--hud-2"), "stroke-dasharray": "4 6" }),
    svg("line", { x1: C, y1: C - R - 30, x2: C, y2: C + R + 30, stroke: css("--hud-2"), "stroke-dasharray": "4 6" }),
    svg("g", { class: "sweep" },
      svg("line", { x1: C, y1: C, x2: C, y2: C - R - 18, stroke: css("--accent"), "stroke-width": 1, opacity: 0.55 }),
      svg("path", { d: `M${C} ${C} L${C} ${C - R - 18} A${R + 18} ${R + 18} 0 0 1 ${C + (R + 18) * Math.sin(0.5)} ${C - (R + 18) * Math.cos(0.5)} Z`,
        fill: css("--accent"), opacity: 0.08 })),
    ticks,
    svg("text", { x: 8, y: 16, class: "hud" }, "SYS.CORE // ONLINE"),
    svg("text", { x: 8, y: 30, class: "hud" }, `NODES ${plugins.filter((p) => p.enabled).length}/${plugins.length}`),
    svg("text", { x: W - 8, y: 16, class: "hud", "text-anchor": "end" }, `SKILLS ${inv.skills.length}`),
    svg("text", { x: W - 8, y: 30, class: "hud", "text-anchor": "end" }, `MCP ${inv.mcp.length}`),
    svg("text", { x: 8, y: W - 10, class: "hud" }, "READ-ONLY"),
    svg("text", { x: W - 8, y: W - 10, class: "hud", "text-anchor": "end" }, inv.settings.sandbox.enabled ? "SANDBOX ARMED" : "SANDBOX OFF"));
  const root = svg("svg", { class: "orbit", viewBox: `0 0 ${W} ${W}`, role: "img", "aria-label": `${plugins.length} plugins around your setup` },
    hud,
    svg("g", { "aria-hidden": "true" }, shell, blueDots, ringDots, coreDots),
    nodes);

  let angle = 0;
  const still = matchMedia("(prefers-reduced-motion: reduce)").matches;
  function frame() {
    const ca = Math.cos(angle), sa = Math.sin(angle);
    pts.forEach(([x, y, z], i) => {
      const rx = x * ca + z * sa, rz = -x * sa + z * ca;
      const d = (rz + 1) / 2;
      const c = shell[i];
      c.setAttribute("cx", (C + rx * R).toFixed(1));
      c.setAttribute("cy", (C + y * R).toFixed(1));
      c.setAttribute("r", (0.7 + d * 1.1).toFixed(2));
      c.setAttribute("opacity", (0.08 + d * 0.55).toFixed(2));
    });
    const cb = Math.cos(-angle * 1.6), sb = Math.sin(-angle * 1.6);
    core.forEach(([x, y, z], i) => {
      const rx = x * cb + z * sb, rz = -x * sb + z * cb;
      const c = coreDots[i];
      c.setAttribute("cx", (C + rx * R).toFixed(1));
      c.setAttribute("cy", (C + y * R * 0.9).toFixed(1));
      c.setAttribute("r", (0.9 + (rz + 0.5) * 1.2).toFixed(2));
      c.setAttribute("opacity", (0.55 + rz).toFixed(2));
    });
    // A tilted ring around the core.
    const tilt = -0.28;
    ringPts.forEach(([a, rr], i) => {
      const t = a + angle * 2.2;
      const x = Math.cos(t) * rr, z = Math.sin(t) * rr, y = z * 0.22;
      const px = x * Math.cos(tilt) - y * Math.sin(tilt), py = x * Math.sin(tilt) + y * Math.cos(tilt);
      const c = ringDots[i];
      c.setAttribute("cx", (C + px * R).toFixed(1));
      c.setAttribute("cy", (C + py * R).toFixed(1));
      c.setAttribute("r", (0.8 + (z + 0.6) * 0.9).toFixed(2));
      c.setAttribute("opacity", (0.35 + (z + 0.6) * 0.5).toFixed(2));
    });
    blue.forEach(([a, rr, y], i) => {
      const t = a + angle * 0.9;
      const c = blueDots[i];
      c.setAttribute("cx", (C + Math.cos(t) * rr * R).toFixed(1));
      c.setAttribute("cy", (C + (y + Math.sin(t) * rr * 0.2) * R).toFixed(1));
      c.setAttribute("r", "1.6");
      c.setAttribute("opacity", (0.35 + (Math.sin(t) + 1) * 0.25).toFixed(2));
    });
    angle += 0.0022;
    if (!still && root.isConnected) requestAnimationFrame(frame);
  }
  frame();
  requestAnimationFrame(() => { if (!still) frame(); });
  return root;
}

// --- home ---
function home() {
  const now = Date.now();
  const month = inv.sessions.filter((s) => (s.last || "") >= new Date(now - 30 * 864e5).toISOString());
  const spend = month.reduce((a, s) => a + (s.cost_usd || 0), 0);
  const cold = month.reduce((a, s) => ({ n: a.n + s.cold_reloads.count, usd: a.usd + s.cold_reloads.usd }), { n: 0, usd: 0 });
  const days = dailyCost(inv.sessions, 30, now);
  const peak = Math.max(...days.map((d) => d.usd), 0.01);
  const mix = projectMix(inv.sessions, 3, 30, now);
  const mixColors = ["--accent", "--alt", "--muted", "--dim"].map(css);
  const always = inv.memory.filter((m) => m.kind !== "memory").reduce((a, m) => a + m.tokens, 0);
  const on = inv.plugins.filter((p) => p.enabled).length;

  const own = (s) => ["user", "project", "claude.ai"].includes(s.source);
  const deck = [...inv.skills.filter(own), ...inv.skills.filter((s) => !own(s))].slice(0, 8);

  const left = el("div", { class: "col" },
    panel("grid", "Plugins & mods", el("button", { type: "button", class: "chip", onclick: () => go("Plugins") }, "All"),
      el("div", { class: "rows" }, inv.plugins.map((p) => el("button", { type: "button", class: "row", onclick: () => showPlugin(p) },
        el("span", { class: "tile" + (p.enabled ? "" : " off") }, initials(p.id)),
        el("span", {}, el("b", {}, p.id.replace(/@.*/, "")),
          el("small", {}, [p.marketplace, p.version && "v" + p.version].filter(Boolean).join(" · "))),
        el("span", { class: "end" + (!p.enabled ? "" : p.installed && !p.frozen && !/official|builtin|claude-for-legal/.test(p.marketplace) ? " warn" : " ok") },
          !p.enabled ? "off" : p.frozen ? "frozen" : p.installed ? "auto" : "built-in"))))),
    panel("brain", "Memory", el("span", { class: "meta" }, `${inv.memory.length} files`),
      el("div", { class: "big" }, el("b", {}, kTok(always)), el("span", {}, "tokens in CLAUDE.md", el("br"), "and MEMORY.md, all projects")),
      el("p", { class: "note" }, "A chat loads CLAUDE.md and its own project's MEMORY.md."),
      el("div", { class: "rows" }, inv.memory.map((m) => el("div", { class: "row" },
        el("span", { class: "tile" }, m.kind === "memory" ? "M" : m.kind === "MEMORY.md" ? "IX" : "C"),
        el("span", {}, el("b", {}, m.path.split("/").slice(-1)[0]), el("small", {}, m.path)),
        el("span", { class: "end" }, kTok(m.tokens)))))),
    panel("alert", "Warnings", el("span", { class: "meta" }, String(inv.warnings.length)),
      inv.warnings.length ? inv.warnings.map((w) => el("div", { class: "warn-line" }, w)) : el("p", { class: "note" }, "All clear.")));

  const center = el("div", { class: "center" }, orbit(),
    el("div", { class: "stats" }, [[inv.skills.length, "skills"], [inv.agents.length, "agents"], [inv.mcp.length, "mcp"],
      [on + "/" + inv.plugins.length, "plugins"], [inv.settings.rules.length, "rules"]]
      .map(([v, l]) => el("div", { class: "stat" }, el("b", {}, v), el("span", {}, l)))));

  const right = el("div", { class: "col" },
    panel("coin", "Spend", el("span", { class: "meta" }, "last 30 days"),
      el("div", { class: "big" }, el("b", {}, usd(spend)), el("span", {}, `${month.length} sessions`, el("br"), "API-price equivalent")),
      el("div", { class: "label" }, "Daily"),
      el("div", { class: "dots" }, days.map((d) => {
        const size = d.usd ? 6 + (d.usd / peak) * 10 : 5;
        return el("i", { class: d.usd ? "on" : "", title: `${d.day}: ${usd(d.usd)}`,
          style: { width: size + "px", height: size + "px", opacity: d.usd ? String(0.45 + (d.usd / peak) * 0.55) : "1" } });
      })),
      el("div", { class: "label" }, "Project mix"),
      el("div", { class: "mix" }, mix.map((p, i) => el("i", { title: `${p.name}: ${usd(p.usd)}`,
        style: { flex: String(Math.max(p.usd, 0.01)), background: mixColors[i] } }))),
      el("div", { class: "legend" }, mix.map((p) => el("span", {}, el("b", {}, usd(p.usd)), p.name)))),
    panel("clock", "Prompt cache", el("span", { class: "meta" }, "cold reloads"),
      el("div", { class: "big" }, el("b", {}, usd(cold.usd)), el("span", {}, `${cold.n} reloads`, el("br"), "after idle chats")),
      el("p", { class: "note" }, cold.n ? "Each one paid to write the whole chat back to cache. /keepwarm from cache-tax prevents this." : "No cold reloads in 30 days.")),
    panel("bolt", "Skills deck", el("button", { type: "button", class: "chip", onclick: () => go("Skills") }, "All " + inv.skills.length),
      el("div", { class: "deck" }, deck.map((s) => el("div", { class: "card" },
        el("button", { type: "button", class: "name", onclick: () => showItem(s) }, "/" + s.name),
        el("div", { class: "m" }, el("b", {}, s.model || "inherits"), " · " + kTok(s.tokens) + " tok"),
        el("div", { class: "acts" },
          el("button", { type: "button", title: "Details", onclick: () => showItem(s) }, "Info"),
          (s.proposals || []).map((p) => el("button", { type: "button", title: p.title,
            onclick: () => openDialog("/" + s.name, proposalBlocks({ proposals: [p] })) },
            p.title.replace("Pin to ", "")))))))));

  return el("div", { class: "home" }, left, center, right);
}

// --- detail tabs ---
function table(cols, rows) {
  return el("div", { class: "wrap" }, el("table", {},
    el("thead", {}, el("tr", {}, cols.map((c) => el("th", {}, c.label)))),
    el("tbody", {}, rows.map((r) => el("tr", {}, cols.map((c) => el("td", c.num ? { class: "num" } : {}, c.get(r))))))));
}

function filtered(items, render) {
  const out = el("div", {});
  const input = el("input", { type: "search", placeholder: "Filter…", "aria-label": "Filter" });
  const draw = () => {
    const q = input.value.toLowerCase();
    out.replaceChildren(render(items.filter((i) => JSON.stringify(i).toLowerCase().includes(q))));
  };
  input.addEventListener("input", draw);
  draw();
  return el("div", {}, input, out);
}

const sheet = (title, ...body) => el("section", { class: "sheet" }, el("h2", {}, el("i", {}, seq()), title), body);
const propose = (i) => ((i.proposals || []).length
  ? el("button", { type: "button", class: "chip hot", onclick: () => openDialog("Proposal", proposalBlocks(i)) }, "Propose") : "");

const views = {
  Home: home,
  Settings() {
    const s = inv.settings;
    return [
      sheet("Layers", table([{ label: "Source", get: (l) => l.source }, { label: "File", get: (l) => el("code", {}, l.path) },
        { label: "Exists", get: (l) => (l.exists ? "yes" : "no") }, { label: "Keys", get: (l) => l.keys.join(", ") }], s.layers)),
      sheet("Sandbox", el("pre", {}, JSON.stringify(s.sandbox, null, 2))),
      sheet("Permission rules", filtered(s.rules, (rows) => table([{ label: "Kind", get: (r) => r.kind },
        { label: "Rule", get: (r) => el("code", {}, r.rule) }, { label: "From", get: (r) => r.source }, { label: "", get: propose }], rows))),
      sheet("Hooks", table([{ label: "Event", get: (h) => h.event }, { label: "Matcher", get: (h) => h.matcher || "*" },
        { label: "Command", get: (h) => el("code", {}, h.command || "") }, { label: "From", get: (h) => h.source }], s.hooks)),
    ];
  },
  Plugins() {
    return sheet("Plugins & mods", filtered(inv.plugins, (rows) => table([
      { label: "Plugin", get: (p) => p.id }, { label: "On", get: (p) => (p.enabled ? "yes" : "no") },
      { label: "Version", get: (p) => p.version || (p.installed ? "?" : "built in") },
      { label: "Updates", get: (p) => (p.frozen ? "frozen copy" : p.installed ? "from author" : "") },
      { label: "Hooks", get: (p) => p.hooks || "" }, { label: "", get: propose }], rows)));
  },
  Skills() {
    return sheet("Skills · ranked by size", filtered(inv.skills, (rows) => table([
      { label: "Skill", get: (s) => s.name }, { label: "Source", get: (s) => s.source },
      { label: "Model", get: (s) => s.model || "inherits" }, { label: "Tokens", num: true, get: (s) => num(s.tokens) },
      { label: "Description", get: (s) => el("div", { class: "desc" }, s.description) }, { label: "", get: propose }], rows)));
  },
  Agents() {
    const cols = [{ label: "Name", get: (a) => a.name }, { label: "Source", get: (a) => a.source },
      { label: "Model", get: (a) => a.model || "inherits" }, { label: "Tokens", num: true, get: (a) => num(a.tokens) },
      { label: "Description", get: (a) => el("div", { class: "desc" }, a.description) }, { label: "", get: propose }];
    return [sheet("Agents", filtered(inv.agents, (r) => table(cols, r))),
      sheet("Commands", filtered(inv.commands, (r) => table(cols.slice(0, 5), r)))];
  },
  MCP() {
    return sheet("MCP servers", el("p", { class: "note" }, "Each server's tool list loads into every chat. Run /context in Claude Code to see what it costs."),
      table([{ label: "Server", get: (m) => m.name }, { label: "Type", get: (m) => m.type }, { label: "From", get: (m) => m.source }], inv.mcp));
  },
  Memory() {
    return sheet("Memory & CLAUDE.md", table([{ label: "File", get: (m) => el("code", {}, m.path) }, { label: "Kind", get: (m) => m.kind },
      { label: "Lines", num: true, get: (m) => num(m.lines) }, { label: "Tokens", num: true, get: (m) => num(m.tokens) }], inv.memory));
  },
  Sessions() {
    return sheet("Sessions", el("p", { class: "note" }, "Cost comes from Claude Code's own record; ~ marks an estimate from list prices."),
      filtered(inv.sessions, (rows) => table([
        { label: "Last", get: (s) => (s.last || "").slice(0, 16).replace("T", " ") },
        { label: "Project", get: (s) => prettyProject(s.project) },
        { label: "Models", get: (s) => s.models.join(", ") },
        { label: "Msgs", num: true, get: (s) => s.messages },
        { label: "Cost", num: true, get: (s) => (s.estimated ? "~" : "") + usd(s.cost_usd) },
        { label: "Cold reloads", num: true, get: (s) => (s.cold_reloads.count
          ? `${s.cold_reloads.count} (${usd(s.cold_reloads.usd)}, idle ${s.cold_reloads.max_idle_min} min)` : "0") }],
        rows.slice(0, 200))));
  },
  Routines() {
    const r = inv.routines;
    return sheet("Routines", r.exists ? el("pre", {}, JSON.stringify(r.items, null, 2))
      : el("p", { class: "note" }, "No local scheduled tasks. Cloud routines live in claude.ai and are not visible here."),
      inv.unavailable.map((u) => el("p", { class: "note" }, u)));
  },
};

function go(name) { tab = name; draw(); scrollTo(0, 0); }

function bar() {
  const on = inv.plugins.filter((p) => p.enabled).length;
  const i = Object.keys(views).indexOf(tab);
  document.getElementById("bar").replaceChildren(
    el("span", { class: "seg on" }, "claude-os"),
    el("span", { class: "seg" }, `${i + 1}:${tab.toLowerCase()}*`),
    el("span", { class: "seg" }, "plugins ", el("b", {}, `${on}/${inv.plugins.length}`)),
    el("span", { class: "seg" }, "sandbox ", el("b", {}, inv.settings.sandbox.enabled ? "on" : "OFF")),
    el("span", { class: "seg" }, "warn ", el("b", {}, String(inv.warnings.length))),
    el("span", { class: "seg" }, "mode ", el("b", {}, "read-only")),
    el("span", { class: "fill" }),
    el("span", { class: "seg" }, new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })),
    el("button", { type: "button", onclick: load }, "↻ rescan"));
}

function draw() {
  panelNo = 0;
  document.getElementById("tabs").replaceChildren(...Object.keys(views).map((name) =>
    el("button", { type: "button", role: "tab", "aria-selected": String(name === tab), onclick: () => go(name) },
      el("i", {}, String(Object.keys(views).indexOf(name) + 1)), name)));
  bar();
  document.getElementById("view").replaceChildren(...[views[tab]()].flat(Infinity));
}

async function load() {
  const status = document.getElementById("status");
  status.textContent = "Scanning…";
  try {
    const r = await fetch("/api/inventory?t=" + encodeURIComponent(token), { cache: "no-store" });
    if (!r.ok) throw new Error(r.status === 403 ? "Open the full link the server printed (it carries the token)." : "HTTP " + r.status);
    inv = await r.json();
    const user = inv.home.split("/").pop();
    status.replaceChildren("usr ", el("b", {}, user), " · proj ", el("b", {}, inv.project || "none"),
      " · scan ", el("b", {}, new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" })));
    draw();
  } catch (e) {
    status.textContent = e.message;
  }
}

document.getElementById("logo").append(icon("hex"));
// Number keys switch tabs, like a terminal multiplexer.
document.addEventListener("keydown", (e) => {
  if (!inv || e.metaKey || e.ctrlKey || e.altKey || /INPUT|TEXTAREA/.test(document.activeElement.tagName)) return;
  const name = Object.keys(views)[Number(e.key) - 1];
  if (name) go(name);
});
setInterval(() => { if (inv) bar(); }, 30000);
document.getElementById("dlg-close").addEventListener("click", () => document.getElementById("dlg").close());
load();
