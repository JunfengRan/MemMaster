#!/usr/bin/env node
/**
 * Copy workspace artifacts/gates/*.json into a delivery run and advance all passing gates.
 */
import { cpSync, existsSync, mkdirSync, readdirSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { spawnSync } from "node:child_process";

const ROOT = join(dirname(fileURLToPath(import.meta.url)), "..", "..");
const runDir = process.argv[2];
if (!runDir) {
  console.error("usage: seed-run-artifacts.mjs <run-dir>");
  process.exit(1);
}
const src = join(ROOT, "artifacts", "gates");
const dest = join(runDir, "artifacts");
mkdirSync(dest, { recursive: true });
for (const name of readdirSync(src)) {
  if (name.endsWith(".json")) cpSync(join(src, name), join(dest, name));
}
console.log("seeded", dest);
