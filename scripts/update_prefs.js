#!/usr/bin/env node
// Deterministic post-generation update for preferences.json.
// Run after menu.json is written: node scripts/update_prefs.js

const fs = require('fs');
const path = require('path');

const ROOT = path.join(__dirname, '..');
const menuPath = path.join(ROOT, 'menu.json');
const prefsPath = path.join(ROOT, 'preferences.json');

const menu = JSON.parse(fs.readFileSync(menuPath, 'utf8'));
const prefs = JSON.parse(fs.readFileSync(prefsPath, 'utf8'));

const today = new Date().toISOString().slice(0, 10);

// Adopted recipes from this week's menu
const adopted = [...(menu.main || []), ...(menu.side || [])];

for (const recipe of adopted) {
  const existing = prefs.recipes.find(r => r.name === recipe.name);
  if (existing) {
    existing.priority = false;
    existing.done_count = (existing.done_count || 0) + 1;
    existing.last_adopted_at = today;
  } else {
    prefs.recipes.push({
      id: Math.random().toString(36).slice(2, 14),
      name: recipe.name,
      priority: false,
      good_count: 0,
      bad_count: 0,
      comments: [],
      added_at: today,
      done_count: 1,
      last_adopted_at: today,
    });
  }
}

// Reset weekly state
prefs.weekly_request = { moods: [], note: '', updated_at: null };
prefs.leftover_ingredients = { checked: [], extra: '', updated_at: null };

fs.writeFileSync(prefsPath, JSON.stringify(prefs, null, 2) + '\n');
console.log(`updated preferences.json — ${adopted.length} recipes, resets applied (${today})`);
