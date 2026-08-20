#!/usr/bin/env node
import { existsSync } from "node:fs";
import { artifactPath, fail, pass, readJson } from "../gate-utils.mjs";

const runDir = process.argv[2];
if (!runDir) fail("usage: brief-complete.mjs <run-dir>");

const briefPath = artifactPath(runDir, "artifacts/research-brief.json");
if (!existsSync(briefPath)) fail(`missing ${briefPath}`);

const brief = readJson(briefPath);
if (!brief.reader || typeof brief.reader !== "string") {
  fail("research-brief.json must include reader string");
}
if (!brief.scope || typeof brief.scope !== "string") {
  fail("research-brief.json must include scope string");
}
if (!Array.isArray(brief.evidenceTargets) || brief.evidenceTargets.length === 0) {
  fail("research-brief.json must include non-empty evidenceTargets[]");
}
const targetIds = [];
for (const target of brief.evidenceTargets) {
  if (!target.targetId || !target.repoPath) {
    fail("each evidenceTarget requires targetId and repoPath");
  }
  if (!/^[A-Za-z0-9][A-Za-z0-9._-]*$/.test(target.targetId)) {
    fail("each evidenceTarget targetId must be a safe identifier");
  }
  targetIds.push(target.targetId);
}
if (new Set(targetIds).size !== targetIds.length) {
  fail("evidenceTarget targetIds must be unique");
}

pass("brief-complete: ok");
