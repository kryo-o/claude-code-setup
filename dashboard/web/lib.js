// Pure helpers for app.js, kept apart so node can test them (tests/test_web.py).
"use strict";

// "-Users-kryo-projects-claude-code-setup" -> "claude-code-setup"
function prettyProject(dir) {
  const s = dir.replace(/^-Users-[^-]+/, "").replace(/^-projects-/, "").replace(/^-/, "");
  return s || "~";
}

// Cuts text longer than n characters, ending it with an ellipsis.
const clip = (s, n) => (s.length > n ? s.slice(0, n - 1) + "…" : s);

const dayOf =(iso) => (iso || "").slice(0, 10);

// Cost per UTC day for the last n days, oldest first; a session counts on the day it last ran.
function dailyCost(sessions, n, now) {
  const days = [];
  for (let i = n - 1; i >= 0; i--) days.push({ day: dayOf(new Date(now - i * 864e5).toISOString()), usd: 0 });
  const at = Object.fromEntries(days.map((d) => [d.day, d]));
  for (const s of sessions) if (at[dayOf(s.last)]) at[dayOf(s.last)].usd += s.cost_usd || 0;
  return days;
}

// Cost by project over the last n days: the top ones, then the rest as "other".
function projectMix(sessions, top, n, now) {
  const cut = new Date(now - n * 864e5).toISOString();
  const by = {};
  for (const s of sessions) {
    if ((s.last || "") < cut) continue;
    const p = prettyProject(s.project);
    by[p] = (by[p] || 0) + (s.cost_usd || 0);
  }
  const all = Object.entries(by).map(([name, usd]) => ({ name, usd })).sort((a, b) => b.usd - a.usd);
  const rest = all.slice(top).reduce((a, p) => a + p.usd, 0);
  return rest > 0 ? [...all.slice(0, top), { name: "other", usd: rest }] : all.slice(0, top);
}

// n points spread evenly over the unit sphere (Fibonacci lattice).
function sphere(n) {
  const pts = [];
  const golden = Math.PI * (3 - Math.sqrt(5));
  for (let i = 0; i < n; i++) {
    const y = 1 - (2 * (i + 0.5)) / n;
    const r = Math.sqrt(1 - y * y);
    pts.push([Math.cos(golden * i) * r, y, Math.sin(golden * i) * r]);
  }
  return pts;
}

// Seeded random numbers, so the picture is the same on every load.
function rng(seed) {
  return () => ((seed = (seed * 1664525 + 1013904223) >>> 0) / 4294967296);
}
