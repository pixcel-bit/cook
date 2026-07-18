#!/usr/bin/env node
// Deterministic post-generation update for preferences.json.
// Run after menu.json is written: node scripts/update_prefs.js

const fs = require('fs');
const path = require('path');

const ROOT = path.join(__dirname, '..');
const prefsPath = path.join(ROOT, 'preferences.json');
const menuPath = path.join(ROOT, 'menu.json');

let prefs;
try {
  prefs = JSON.parse(fs.readFileSync(prefsPath, 'utf8'));
} catch (e) {
  console.error(`ERROR: could not read ${prefsPath}: ${e.message}`);
  process.exit(1);
}

const today = new Date().toISOString().slice(0, 10);

// Reset weekly_request and all priority flags.
// leftover_ingredients.checked is preserved so carried-over items remain visible next week.
// prefs.recipes is user-curated (liked or manually added) — not auto-populated.
prefs.weekly_request = { moods: [], note: '', updated_at: null };
(prefs.recipes || []).forEach(r => { r.priority = false; });
// 「あとから追加」した料理は前週分なのでクリア（新しい献立には引き継がない）
prefs.menu_extra = [];

// 採用メタデータの記録：新しい献立に登場したリストレシピに last_adopted_at /
// done_count を刻む（殿堂入りの14日クールダウン判定の根拠になる）。
// 同じ delivery_date への再実行では二重カウントしない（冪等）。
try {
  const menu = JSON.parse(fs.readFileSync(menuPath, 'utf8'));
  const delivery = menu.delivery_date || today;
  const menuNames = new Set([...(menu.main || []), ...(menu.side || [])].map(r => r.name));
  let adopted = 0;
  (prefs.recipes || []).forEach(r => {
    if (menuNames.has(r.name) && r.last_adopted_at !== delivery) {
      r.last_adopted_at = delivery;
      r.done_count = (r.done_count || 0) + 1;
      adopted += 1;
    }
  });
  if (adopted) console.log(`adoption recorded for ${adopted} recipe(s) (delivery ${delivery})`);
} catch (e) {
  console.error(`WARN: could not record adoptions: ${e.message}`);
}

try {
  fs.writeFileSync(prefsPath, JSON.stringify(prefs, null, 2) + '\n');
} catch (e) {
  console.error(`ERROR: could not write ${prefsPath}: ${e.message}`);
  process.exit(1);
}
console.log(`updated preferences.json — resets applied (${today})`);
