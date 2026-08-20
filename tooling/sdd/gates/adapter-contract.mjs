#!/usr/bin/env node
import { requireOk, pass, fail } from "./delivery-utils.mjs";

const runDir = process.argv[2];
if (!runDir) fail("usage: adapter-contract.mjs <run-dir>");
const data = requireOk(runDir, "adapter-contract");
const ids = data.adapterIds || [];
for (const id of ["mail", "meeting", "im", "web"]) {
  if (!ids.includes(id)) fail(`adapter ${id} missing`);
}
pass("adapter-contract: ok");
