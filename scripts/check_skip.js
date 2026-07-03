#!/usr/bin/env node
// Deterministic skip gate for the weekly meal-prep routine.
//
// The routine (scheduled Saturday run) must call this FIRST and obey the result.
// Gmail access needs the agent, so the routine fetches the latest Green Beans
// order's delivery date and passes it here; this script owns the decision so it
// is machine-made, not a fuzzy natural-language judgement.
//
// Usage:
//   node scripts/check_skip.js <latest_order_delivery_date:YYYY-MM-DD>
//
// Output (first stdout line is the decision token):
//   SKIP      -> menu.json already generated for this delivery; do NOT generate,
//                do NOT run any script, do NOT push. End the run.
//   GENERATE  -> proceed with the normal generation flow.
//
// Exit codes:
//   0 -> a decision was printed (SKIP or GENERATE)
//   2 -> bad usage / unparseable date (routine should stop and report)

const fs = require('fs');
const path = require('path');

const orderDate = (process.argv[2] || '').trim();
if (!/^\d{4}-\d{2}-\d{2}$/.test(orderDate)) {
  console.error('ERROR: pass the latest order delivery date as YYYY-MM-DD');
  console.error('usage: node scripts/check_skip.js 2026-07-09');
  process.exit(2);
}

const menuPath = path.join(__dirname, '..', 'menu.json');

let currentDelivery = '';
try {
  currentDelivery = (JSON.parse(fs.readFileSync(menuPath, 'utf8')).delivery_date || '').trim();
} catch (e) {
  // No readable menu.json -> nothing generated yet -> must generate.
  console.log('GENERATE');
  console.log(`reason: menu.json not readable (${e.message})`);
  process.exit(0);
}

if (currentDelivery && currentDelivery === orderDate) {
  console.log('SKIP');
  console.log(`reason: menu.json already generated for delivery ${orderDate}`);
} else {
  console.log('GENERATE');
  console.log(`reason: menu.json delivery=${currentDelivery || '(none)'} != order delivery=${orderDate}`);
}
process.exit(0);
