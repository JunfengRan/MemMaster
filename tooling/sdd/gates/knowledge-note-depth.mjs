#!/usr/bin/env node
import { existsSync, readdirSync } from "node:fs";
import { join } from "node:path";
import {
  artifactPath,
  fail,
  pass,
  readText,
  countMermaidBlocks,
} from "../gate-utils.mjs";

const runDir = process.argv[2];
if (!runDir) fail("usage: knowledge-note-depth.mjs <run-dir>");

let notePath = artifactPath(runDir, "artifacts/knowledge-note.md");
if (!existsSync(notePath)) {
  const appsDir = join(runDir, "docs", "knowledge", "apps");
  if (existsSync(appsDir)) {
    const md = readdirSync(appsDir).find((f) => f.endsWith("-note.md"));
    if (md) notePath = join(appsDir, md);
  }
}

if (!existsSync(notePath)) fail("knowledge note markdown not found");

const text = readText(notePath);
if (!/调用链|call chain/i.test(text)) {
  fail("knowledge note must include a call chain section");
}
if (countMermaidBlocks(text) < 2) {
  fail("knowledge note must include at least 2 mermaid diagrams");
}
if (!/代码索引|code index|关键文件/i.test(text)) {
  fail("knowledge note must include a code index section");
}

pass("knowledge-note-depth: ok");
