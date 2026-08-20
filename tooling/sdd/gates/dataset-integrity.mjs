#!/usr/bin/env node
import { requireOk, pass, fail } from "./delivery-utils.mjs";

const runDir = process.argv[2];
if (!runDir) fail("usage: dataset-integrity.mjs <run-dir>");
const data = requireOk(runDir, "dataset-integrity");
if (data.questionCount !== 20) fail("dataset must contain 20 questions");
const per = data.perSource || {};
for (const src of ["mail", "meeting", "im", "web"]) {
  if (per[src] !== 5) fail(`source ${src} must have 5 questions`);
}
if (data.oraclePass !== true) fail("oracle gate must pass");
pass("dataset-integrity: ok");
