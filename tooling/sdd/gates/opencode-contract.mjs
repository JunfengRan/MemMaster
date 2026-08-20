#!/usr/bin/env node
import { requireOk, pass, fail } from "./delivery-utils.mjs";

const runDir = process.argv[2];
if (!runDir) fail("usage: opencode-contract.mjs <run-dir>");
const data = requireOk(runDir, "opencode-contract");
if (!data.pluginEntry) fail("opencode-contract.json missing pluginEntry");
if (data.silentDowngrade === true) fail("silent hook downgrade is forbidden");
pass("opencode-contract: ok");
