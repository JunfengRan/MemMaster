#!/usr/bin/env node
import { mkdtempSync, mkdirSync, writeFileSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { execFileSync } from "node:child_process";

let failed = 0;
function assert(name, condition, detail = "") {
  if (!condition) {
    console.error(`FAIL ${name}${detail ? `: ${detail}` : ""}`);
    failed += 1;
  } else {
    console.log(`OK ${name}`);
  }
}

function runGate(script, runDir, expectOk) {
  try {
    execFileSync(process.execPath, [script, runDir], {
      encoding: "utf8",
      stdio: ["ignore", "pipe", "pipe"],
      env: { ...process.env, MEMMASTER_GATE_FALLBACK: "0" },
    });
    return expectOk;
  } catch (err) {
    return !expectOk;
  }
}

const runDir = mkdtempSync(join(tmpdir(), "memmaster-gates-"));
mkdirSync(join(runDir, "artifacts"), { recursive: true });
writeFileSync(
  join(runDir, "context-pack.json"),
  JSON.stringify({
    schemaVersion: 1,
    metadata: {
      pipeline_id: "delivery",
      phase_id: "environment",
      context_pack_version: 1,
      run_id: "t",
      slug: "t",
    },
    L0_constraints: { researchType: "selection_compare", scope: "x", forbiddenPaths: [] },
    L1_session_anchor: {
      currentState: "environment",
      phaseGoal: "x",
      gateLastResult: { gate: "pending", result: "pending" },
    },
  }),
);

const envScript = join("tooling", "sdd", "gates", "env-doctor.mjs");
assert("env-doctor fail without artifact", runGate(envScript, runDir, false));
writeFileSync(
  join(runDir, "artifacts", "env-doctor.json"),
  JSON.stringify({ ok: true, node: "v26", python: "3.12" }),
);
assert("env-doctor pass with artifact", runGate(envScript, runDir, true));

writeFileSync(
  join(runDir, "artifacts", "eval-lock.json"),
  JSON.stringify({ ok: true, lockedGroups: ["E0", "E1", "E2", "E3"] }),
);
assert(
  "eval-lock fail missing E4",
  runGate(join("tooling", "sdd", "gates", "eval-lock.mjs"), runDir, false),
);
writeFileSync(
  join(runDir, "artifacts", "eval-lock.json"),
  JSON.stringify({
    ok: true,
    lockedGroups: ["E0", "E1", "E2", "E3", "E4", "E5"],
  }),
);
assert(
  "eval-lock pass with core groups",
  runGate(join("tooling", "sdd", "gates", "eval-lock.mjs"), runDir, true),
);

rmSync(runDir, { recursive: true, force: true });
if (failed > 0) {
  console.error(`${failed} assertion(s) failed`);
  process.exit(1);
}
console.log("test-gates: ok");
