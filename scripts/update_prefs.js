#!/usr/bin/env node
// Deterministic post-generation update for preferences.json.
// Run after menu.json is written: node scripts/update_prefs.js

const fs = require('fs');
const path = require('path');

const ROOT = path.join(__dirname, '..');
const prefsPath = path.join(ROOT, 'preferences.json');

const prefs = JSON.parse(fs.readFileSync(prefsPath, 'utf8'));

const today = new Date().toISOString().slice(0, 10);

// Reset weekly_request and all priority flags.
// leftover_ingredients.checked is preserved so carried-over items remain visible next week.
// prefs.recipes is user-curated (liked or manually added) — not auto-populated.
prefs.weekly_request = { moods: [], note: '', updated_at: null };
(prefs.recipes || []).forEach(r => { r.priority = false; });

fs.writeFileSync(prefsPath, JSON.stringify(prefs, null, 2) + '\n');
console.log(`updated preferences.json — resets applied (${today})`);
