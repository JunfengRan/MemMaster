#!/usr/bin/env node
import { existsSync } from "node:fs";
import { artifactPath, fail, pass, readJson } from "../gate-utils.mjs";

const runDir = process.argv[2];
if (!runDir) fail("usage: catalog-numbered.mjs <run-dir>");

const catalogPath = artifactPath(runDir, "artifacts/comparative-catalog.json");
if (!existsSync(catalogPath)) fail(`missing ${catalogPath}`);

const catalog = readJson(catalogPath);
const entries = Array.isArray(catalog.entries) ? catalog.entries : [];
if (entries.length === 0) fail("comparative-catalog.json entries[] must be non-empty");

const idPattern = /^[A-Z]{2,}-\d+$/;
for (const entry of entries) {
  if (!entry.id || !idPattern.test(entry.id)) {
    fail(`entry id must match XX-NN pattern, got: ${entry.id}`);
  }
  if (!entry.claim) fail(`entry ${entry.id} missing claim`);
}

pass("catalog-numbered: ok");
