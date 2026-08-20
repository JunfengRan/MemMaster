#!/usr/bin/env node
import { requireOk, pass, fail } from "./delivery-utils.mjs";

const runDir = process.argv[2];
if (!runDir) fail("usage: eval-lock.mjs <run-dir>");
const data = requireOk(runDir, "eval-lock");
if (!Array.isArray(data.lockedGroups) || data.lockedGroups.length === 0) {
  fail("lockedGroups must be non-empty");
}
if (data.lockedGroups.length > 10) fail("locked group count exceeds 10");
for (const id of ["E0", "E1", "E2", "E3", "E4"]) {
  if (!data.lockedGroups.includes(id)) fail(`core group ${id} must remain locked`);
}
pass("eval-lock: ok");
