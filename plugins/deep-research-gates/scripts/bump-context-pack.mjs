#!/usr/bin/env node
/**
 * Bump context-pack version and write snapshot
 * Usage: node bump-context-pack.mjs <run-dir> [phaseId]
 */
import { readFileSync, mkdirSync, existsSync } from "node:fs";
import { join, resolve } from "node:path";
import { pathToFileURL } from "node:url";

const [runDir, phaseId] = process.argv.slice(2);
if (!runDir) {
  console.error("usage: bump-context-pack.mjs <run-dir> [phaseId]");
  process.exit(1);
}

const persistenceUrl = pathToFileURL(
  resolve(process.cwd(), "tooling", "sdd", "run-persistence.mjs"),
).href;
const { appendJsonLine, atomicWriteJson, withRunLock } = await import(persistenceUrl);

const bump = async () => {
  const packPath = join(runDir, "context-pack.json");
  if (!existsSync(packPath)) {
    throw new Error("context-pack.json not found");
  }

  const pack = JSON.parse(readFileSync(packPath, "utf8"));
  pack.metadata = pack.metadata ?? {};
  pack.metadata.context_pack_version =
    (pack.metadata.context_pack_version ?? 0) + 1;
  if (phaseId) {
    pack.metadata.phase_id = phaseId;
    pack.L1_session_anchor = pack.L1_session_anchor ?? {};
    pack.L1_session_anchor.currentState = phaseId;
  }

  const version = pack.metadata.context_pack_version;
  const snapDir = join(runDir, "snapshots");
  mkdirSync(snapDir, { recursive: true });
  const snapPath = join(snapDir, `context-pack@v${version}.json`);
  atomicWriteJson(packPath, pack);
  atomicWriteJson(snapPath, pack);

  appendJsonLine(join(runDir, "observations.jsonl"), {
    ts: new Date().toISOString(),
    actor: { type: "system", id: "context-pack-bump" },
    phase: phaseId ?? pack.L1_session_anchor?.currentState ?? "unknown",
    kind: "context_pack_bump",
    payload: { version, snapshot: snapPath },
    contextPackVersion: version,
  });

  console.log(`context-pack bumped to v${version}`);
};

if (process.env.RESEARCH_LOCK_HELD === "1") {
  await bump();
} else {
  await withRunLock(runDir, bump);
}
