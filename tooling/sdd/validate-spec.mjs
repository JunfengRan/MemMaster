#!/usr/bin/env node
import { readFileSync, existsSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import Ajv2020 from "ajv/dist/2020.js";
import addFormats from "ajv-formats";
import YAML from "yaml";
import { createInitialRunState, loadWorkflowSpec, reduce } from "./research-reducer.mjs";

const ROOT = join(dirname(fileURLToPath(import.meta.url)), "..", "..");

function readJson(path) {
  return JSON.parse(readFileSync(path, "utf8"));
}

function validateSchema(instance, schemaPath, label) {
  const ajv = new Ajv2020({ allErrors: true, strict: false });
  addFormats(ajv);
  const validate = ajv.compile(readJson(schemaPath));
  if (!validate(instance)) {
    console.error(`${label} schema validation failed:`);
    for (const err of validate.errors ?? []) {
      console.error(`  - ${err.instancePath || "/"} ${err.message}`);
    }
    process.exit(1);
  }
}

function checkWorkflow(rel) {
  const specPath = join(ROOT, rel);
  const spec = YAML.parse(readFileSync(specPath, "utf8"));
  validateSchema(
    spec,
    join(ROOT, "spec", "schemas", "research-workflow.schema.json"),
    rel,
  );
  if (!spec.states[spec.initialState]) {
    console.error(`${rel}: initialState missing`);
    process.exit(1);
  }
  for (const [name, state] of Object.entries(spec.states)) {
    if (state.kind === "terminal") continue;
    if (!state.gate || !spec.gates[state.gate]) {
      console.error(`${rel}: state ${name} missing/unknown gate`);
      process.exit(1);
    }
    const scriptPath = join(ROOT, spec.gates[state.gate].script);
    if (!existsSync(scriptPath)) {
      console.error(`${rel}: missing gate script ${scriptPath}`);
      process.exit(1);
    }
    if (state.onPass && !spec.states[state.onPass]) {
      console.error(`${rel}: onPass unknown for ${name}`);
      process.exit(1);
    }
    if (state.onFail && !spec.states[state.onFail]) {
      console.error(`${rel}: onFail unknown for ${name}`);
      process.exit(1);
    }
  }
  const initial = createInitialRunState(spec, "validate-run");
  const abort = reduce(initial, { type: "USER_ABORT" }, spec);
  if (abort.error || abort.runState.currentState !== "aborted") {
    console.error(`${rel}: USER_ABORT failed`);
    process.exit(1);
  }
  console.log(`ok ${rel}`);
}

checkWorkflow("spec/workflows/deep-research.yaml");
checkWorkflow("spec/workflows/delivery.yaml");
console.log("validate-spec: ok");
