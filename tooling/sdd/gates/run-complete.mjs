#!/usr/bin/env node
import { requireOk, pass, fail } from "./delivery-utils.mjs";

const runDir = process.argv[2];
if (!runDir) fail("usage: run-complete.mjs <run-dir>");
const data = requireOk(runDir, "run-complete");
const g = data.lockedGroupCount;
const expected = 20 * g;
if (data.acceptedSessions !== expected) {
  fail(`acceptedSessions must equal 20G=${expected}, got ${data.acceptedSessions}`);
}
pass("run-complete: ok");
