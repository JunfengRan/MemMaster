#!/usr/bin/env node
import { existsSync, readdirSync } from "node:fs";
import { join } from "node:path";
import { artifactPath, fail, pass, readText } from "../gate-utils.mjs";

const runDir = process.argv[2];
if (!runDir) fail("usage: decision-doc-complete.mjs <run-dir>");

let docPath = artifactPath(runDir, "artifacts/decision-doc.md");
if (!existsSync(docPath)) {
  const designDir = join(runDir, "docs", "design");
  if (existsSync(designDir)) {
    const md = readdirSync(designDir).find((f) => f.endsWith("-selection.md"));
    if (md) docPath = join(designDir, md);
  }
}

if (!existsSync(docPath)) fail("decision selection markdown not found");

const text = readText(docPath);
if (!/选型前提|selection premise|前提/i.test(text)) {
  fail("decision doc must include selection premise section");
}
if (!/\|.+\|.+\|/s.test(text)) {
  fail("decision doc must include a comparison table");
}
if (!/P[0-3]|优先级|priority/i.test(text)) {
  fail("decision doc must include priority section");
}

pass("decision-doc-complete: ok");
