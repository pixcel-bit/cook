#!/usr/bin/env node
// Deterministic reuse of saved favorite recipes.
//
// Run AFTER menu.json is generated and BEFORE fetch_pexels.py:
//   node scripts/apply_saved_recipes.js
//
// When a user taps 👍 in the app, the exact cooking method of that dish is
// saved into preferences.json recipes[].recipe (with lock: true = 固定).
// This script overwrites any menu.json dish whose name matches a saved,
// LOCKED favorite so the favorite is reproduced verbatim instead of being
// regenerated. Recipes marked おまかせ (lock: false) are left as generated.
//
// Only menu.json is written; preferences.json is read-only here.

const fs = require('fs');
const path = require('path');

const ROOT = path.join(__dirname, '..');
const menuPath = path.join(ROOT, 'menu.json');
const prefsPath = path.join(ROOT, 'preferences.json');

let menu, prefs;
try {
  menu = JSON.parse(fs.readFileSync(menuPath, 'utf8'));
} catch (e) {
  console.error(`ERROR: could not read menu.json: ${e.message}`);
  process.exit(1);
}
try {
  prefs = JSON.parse(fs.readFileSync(prefsPath, 'utf8'));
} catch (e) {
  console.error(`ERROR: could not read preferences.json: ${e.message}`);
  process.exit(1);
}

// name -> saved detail, only for LOCKED favorites with real steps
const saved = {};
for (const r of prefs.recipes || []) {
  const d = r.recipe;
  if (d && d.lock !== false && Array.isArray(d.steps) && d.steps.length) {
    saved[r.name] = d;
  }
}

// Fields copied from the saved favorite (image is handled by fetch_pexels).
const FIELDS = ["genre", "tool", "freeze", "ingredients", "steps",
                "time_minutes", "storage_note", "search_keyword"];

let n = 0;
for (const rec of [...(menu.main || []), ...(menu.side || [])]) {
  const d = saved[rec.name];
  if (!d) continue;
  for (const f of FIELDS) {
    if (d[f] !== undefined) rec[f] = d[f];
  }
  n += 1;
  console.log(`reused saved recipe (固定): ${rec.name}`);
}

fs.writeFileSync(menuPath, JSON.stringify(menu, null, 2));
console.log(`apply_saved_recipes: reused ${n} locked favorite(s)`);
