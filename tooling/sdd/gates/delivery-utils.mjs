import { existsSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { artifactPath, fail, pass, readJson } from "../gate-utils.mjs";

const ROOT = join(dirname(fileURLToPath(import.meta.url)), "..", "..", "..");

export function repoRoot() {
  return ROOT;
}

export function loadNamedArtifact(runDir, name) {
  const path = artifactPath(runDir, `artifacts/${name}.json`);
  if (existsSync(path)) return { path, data: readJson(path) };
  fail(`missing artifacts/${name}.json`);
}

export function requireOk(runDir, name) {
  const { path, data } = loadNamedArtifact(runDir, name);
  if (data.ok !== true) fail(`${path}: ok must be true`);
  return data;
}

export function requireFile(rel, label = rel) {
  const path = join(ROOT, rel);
  if (!existsSync(path)) fail(`missing ${label}: ${path}`);
  return path;
}

export { fail, pass, readJson, existsSync, join };
