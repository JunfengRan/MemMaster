#!/usr/bin/env node
import { existsSync } from "node:fs";
import {
  artifactPath,
  fail,
  pass,
  readText,
  countSections,
  measureContent,
} from "../gate-utils.mjs";

const runDir = process.argv[2];
if (!runDir) fail("usage: explore-min-depth.mjs <run-dir>");

const notesPath = artifactPath(runDir, "artifacts/explore-notes.md");
if (!existsSync(notesPath)) fail(`missing ${notesPath}`);

const text = readText(notesPath);
if (countSections(text) < 3) {
  fail("explore-notes.md must have at least 3 ## sections");
}
const content = measureContent(text);
if (content.latinWords < 200 && content.cjkChars < 400) {
  fail(
    "explore-notes.md must have at least 200 Latin words or 400 CJK characters",
  );
}

pass("explore-min-depth: ok");
