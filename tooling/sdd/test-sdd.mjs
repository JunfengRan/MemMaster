#!/usr/bin/env node
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { loadWorkflowSpec, createInitialRunState, reduce } from "./research-reducer.mjs";

let failed = 0;
function assert(name, condition, detail = "") {
  if (!condition) {
    console.error(`FAIL ${name}${detail ? `: ${detail}` : ""}`);
    failed += 1;
  } else {
    console.log(`OK ${name}`);
  }
}

const ROOT = join(dirname(fileURLToPath(import.meta.url)), "..", "..");
const research = loadWorkflowSpec(
  join(ROOT, "spec", "workflows", "deep-research.yaml"),
);
let runState = createInitialRunState(research, "test-run");
assert("research initial is brief", runState.currentState === "brief");

let result = reduce(
  runState,
  { type: "GATE_PASSED", gate: "brief-complete" },
  research,
);
runState = result.runState;
assert("brief pass -> explore", runState.currentState === "explore");

result = reduce(
  runState,
  { type: "GATE_FAILED", gate: "explore-min-depth", reason: "short" },
  research,
);
assert("explore fail stays explore", result.runState.currentState === "explore");

const delivery = loadWorkflowSpec(join(ROOT, "spec", "workflows", "delivery.yaml"));
let d = createInitialRunState(delivery, "delivery-run");
assert("delivery initial is environment", d.currentState === "environment");
d = reduce(d, { type: "GATE_PASSED", gate: "env-doctor" }, delivery).runState;
assert("env-doctor pass -> dataset", d.currentState === "dataset");
d = reduce(d, { type: "GATE_PASSED", gate: "dataset-integrity" }, delivery).runState;
assert("dataset pass -> adapters", d.currentState === "adapters");
d = reduce(d, { type: "USER_ABORT" }, delivery).runState;
assert("abort terminal", d.currentState === "aborted" && d.aborted === true);

result = reduce(
  createInitialRunState(delivery, "bad"),
  { type: "GATE_PASSED", gate: "brief-complete" },
  delivery,
);
assert("wrong gate rejected", Boolean(result.error));

if (failed > 0) {
  console.error(`${failed} assertion(s) failed`);
  process.exit(1);
}
console.log("test-sdd: ok");
