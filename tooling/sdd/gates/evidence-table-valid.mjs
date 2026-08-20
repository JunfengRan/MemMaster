#!/usr/bin/env node
import { existsSync } from "node:fs";
import { basename, join } from "node:path";
import { fail, pass, readJson, listEvidenceFiles } from "../gate-utils.mjs";

const runDir = process.argv[2];
if (!runDir) fail("usage: evidence-table-valid.mjs <run-dir>");

const files = listEvidenceFiles(runDir);
if (files.length === 0) {
  fail("no artifacts/evidence/*.json files found");
}

const validVerdicts = new Set(["true", "partial", "false"]);
const contextPackPath = join(runDir, "context-pack.json");
if (!existsSync(contextPackPath)) {
  fail("missing context-pack.json");
}
const contextPack = readJson(contextPackPath);
const targets = contextPack.L3_evidence_layer?.evidenceTargets;
if (!Array.isArray(targets) || targets.length === 0) {
  fail("context-pack.json must include non-empty L3 evidenceTargets");
}
const expectedTargetIds = targets.map((target) => target.targetId);
if (
  expectedTargetIds.some((targetId) => typeof targetId !== "string" || !targetId) ||
  new Set(expectedTargetIds).size !== expectedTargetIds.length
) {
  fail("context-pack.json evidence targetIds must be non-empty and unique");
}

const actualTargetIds = [];
for (const file of files) {
  const data = readJson(file);
  if (!data.targetId || typeof data.targetId !== "string") {
    fail(`${file}: missing targetId`);
  }
  if (basename(file, ".json") !== data.targetId) {
    fail(`${file}: filename must match targetId "${data.targetId}"`);
  }
  actualTargetIds.push(data.targetId);
  const rows = Array.isArray(data.rows) ? data.rows : [data];
  if (rows.length === 0) fail(`${file}: rows must not be empty`);
  for (const row of rows) {
    if (!row.claim) fail(`${file}: missing claim`);
    if (!validVerdicts.has(row.verdict)) {
      fail(`${file}: verdict must be true|partial|false`);
    }
    if (!row.filePath) fail(`${file}: missing filePath`);
  }
}

if (new Set(actualTargetIds).size !== actualTargetIds.length) {
  fail("evidence targetIds must be unique across files");
}
const expected = new Set(expectedTargetIds);
const actual = new Set(actualTargetIds);
const missing = expectedTargetIds.filter((targetId) => !actual.has(targetId));
const extra = actualTargetIds.filter((targetId) => !expected.has(targetId));
if (missing.length > 0 || extra.length > 0) {
  fail(
    `evidence targets do not match context pack; missing=[${missing.join(",")}], extra=[${extra.join(",")}]`,
  );
}

pass(`evidence-table-valid: ok (${files.length} file(s))`);
