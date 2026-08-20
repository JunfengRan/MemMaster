#!/usr/bin/env node
import { readFileSync, existsSync, readdirSync } from "node:fs";
import { join, dirname, basename } from "node:path";

export function readJson(path) {
  return JSON.parse(readFileSync(path, "utf8"));
}

export function readText(path) {
  return readFileSync(path, "utf8");
}

export function fail(reason) {
  console.error(reason);
  process.exit(1);
}

export function pass(message) {
  console.log(message ?? "gate passed");
  process.exit(0);
}

export function artifactPath(runDir, relativePath) {
  return join(runDir, relativePath);
}

export function countMermaidBlocks(content) {
  return (content.match(/```mermaid/g) ?? []).length;
}

export function listEvidenceFiles(runDir) {
  const dir = join(runDir, "artifacts", "evidence");
  if (!existsSync(dir)) return [];
  return readdirSync(dir)
    .filter((f) => f.endsWith(".json"))
    .map((f) => join(dir, f));
}

export function countWords(text) {
  return measureContent(text).latinWords;
}

export function measureContent(text) {
  const cjkPattern =
    /[\p{Script=Han}\p{Script=Hiragana}\p{Script=Katakana}\p{Script=Hangul}]/u;
  const tokens = text.match(/[\p{L}\p{N}]+/gu) ?? [];
  return {
    latinWords: tokens.filter((token) => !cjkPattern.test(token)).length,
    cjkChars: (text.match(
      /[\p{Script=Han}\p{Script=Hiragana}\p{Script=Katakana}\p{Script=Hangul}]/gu,
    ) ?? []).length,
  };
}

export function countSections(text) {
  return (text.match(/^##\s+/gm) ?? []).length;
}
