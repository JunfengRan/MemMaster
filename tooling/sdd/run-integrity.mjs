import { createHash } from "node:crypto";
import { existsSync, readFileSync, realpathSync } from "node:fs";
import { dirname, join, resolve, sep } from "node:path";
import { fileURLToPath } from "node:url";
import Ajv2020 from "ajv/dist/2020.js";
import addFormats from "ajv-formats";

const SCRIPT_DIR = dirname(fileURLToPath(import.meta.url));
const ROOT = join(SCRIPT_DIR, "..", "..");
const SPEC_DIR = join(ROOT, "spec", "schemas");

const schemaFiles = {
  "run-meta.json": "run-meta.schema.json",
  "state.json": "run-state.schema.json",
  "context-pack.json": "context-pack.schema.json",
  "replay-chain.json": "replay-chain.schema.json",
};

function readJson(path) {
  return JSON.parse(readFileSync(path, "utf8"));
}

function normalizeForComparison(path) {
  return process.platform === "win32" ? path.toLowerCase() : path;
}

export function resolveInside(base, relativePath) {
  if (typeof relativePath !== "string" || relativePath.length === 0) {
    throw new Error("run-relative path must be a non-empty string");
  }
  const root = resolve(base);
  const target = resolve(root, relativePath);
  const normalizedRoot = normalizeForComparison(root);
  const normalizedTarget = normalizeForComparison(target);
  if (
    normalizedTarget !== normalizedRoot &&
    !normalizedTarget.startsWith(`${normalizedRoot}${sep}`)
  ) {
    throw new Error(`path escapes run directory: ${relativePath}`);
  }
  if (existsSync(target)) {
    const realRoot = normalizeForComparison(realpathSync(root));
    const realTarget = normalizeForComparison(realpathSync(target));
    if (
      realTarget !== realRoot &&
      !realTarget.startsWith(`${realRoot}${sep}`)
    ) {
      throw new Error(`path escapes run directory: ${relativePath}`);
    }
  }
  return target;
}

export function sha256File(path) {
  const digest = createHash("sha256").update(readFileSync(path)).digest("hex");
  return `sha256:${digest}`;
}

export function createReplayEntry({
  runDir,
  phase,
  nextPhase,
  workflowId,
  schemaVersion,
  contextPackSnapshot,
  artifacts = [],
  gate,
  gateResult,
}) {
  const snapshotPath = resolveInside(runDir, contextPackSnapshot);
  if (!existsSync(snapshotPath)) {
    throw new Error(`replay snapshot not found: ${contextPackSnapshot}`);
  }
  return {
    recordedAt: new Date().toISOString(),
    phase,
    nextPhase,
    workflowId,
    schemaVersion,
    nodeVersion: process.version,
    contextPackSnapshot,
    contextPackSha256: sha256File(snapshotPath),
    artifacts: artifacts.map((relativePath) => {
      const artifactPath = resolveInside(runDir, relativePath);
      if (!existsSync(artifactPath)) {
        throw new Error(`replay artifact not found: ${relativePath}`);
      }
      return { path: relativePath, sha256: sha256File(artifactPath) };
    }),
    gate,
    gateResult,
  };
}

function createValidators() {
  const ajv = new Ajv2020({ allErrors: true, strict: false });
  addFormats(ajv);
  const validators = {};
  for (const [fileName, schemaName] of Object.entries(schemaFiles)) {
    validators[fileName] = ajv.compile(readJson(join(SPEC_DIR, schemaName)));
  }
  validators.observation = ajv.compile(
    readJson(join(SPEC_DIR, "observation.schema.json")),
  );
  return validators;
}

function formatValidationErrors(label, errors = []) {
  return errors.map(
    (error) => `${label}${error.instancePath || "/"} ${error.message}`,
  );
}

export function verifyRun(runDir, spec) {
  const errors = [];
  const documents = {};
  const validators = createValidators();

  for (const fileName of Object.keys(schemaFiles)) {
    const path = join(runDir, fileName);
    if (!existsSync(path)) {
      errors.push(`missing ${fileName}`);
      continue;
    }
    try {
      const document = readJson(path);
      documents[fileName] = document;
      const validate = validators[fileName];
      if (!validate(document)) {
        errors.push(...formatValidationErrors(fileName, validate.errors));
      }
    } catch (error) {
      errors.push(`${fileName} is not valid JSON: ${error.message}`);
    }
  }

  const observationsPath = join(runDir, "observations.jsonl");
  if (!existsSync(observationsPath)) {
    errors.push("missing observations.jsonl");
  } else {
    const lines = readFileSync(observationsPath, "utf8").split(/\r?\n/);
    lines.forEach((line, index) => {
      if (!line.trim()) return;
      try {
        const observation = JSON.parse(line);
        if (!validators.observation(observation)) {
          errors.push(
            ...formatValidationErrors(
              `observations.jsonl:${index + 1}`,
              validators.observation.errors,
            ),
          );
        }
      } catch (error) {
        errors.push(`observations.jsonl:${index + 1} invalid JSON: ${error.message}`);
      }
    });
  }

  const state = documents["state.json"];
  if (state && !spec.states?.[state.currentState]) {
    errors.push(`state.json currentState "${state.currentState}" is not in workflow spec`);
  }

  const replay = documents["replay-chain.json"];
  for (const [index, entry] of (replay?.entries ?? []).entries()) {
    if (entry.seq !== index + 1) {
      errors.push(
        `replay sequence must be contiguous: expected ${index + 1}, got ${entry.seq}`,
      );
    }
    const phaseDefinition = spec.states?.[entry.phase];
    if (!phaseDefinition) {
      errors.push(`replay phase "${entry.phase}" is not in workflow spec`);
    } else if (phaseDefinition.gate !== entry.gate) {
      errors.push(
        `replay gate "${entry.gate}" does not match phase "${entry.phase}" gate "${phaseDefinition.gate}"`,
      );
    }
    if (!spec.states?.[entry.nextPhase]) {
      errors.push(`replay nextPhase "${entry.nextPhase}" is not in workflow spec`);
    }
    if (entry.workflowId !== spec.workflowId) {
      errors.push(
        `replay workflowId "${entry.workflowId}" does not match "${spec.workflowId}"`,
      );
    }
    if (entry.schemaVersion !== spec.schemaVersion) {
      errors.push(
        `replay schemaVersion ${entry.schemaVersion} does not match ${spec.schemaVersion}`,
      );
    }
    try {
      const snapshotPath = resolveInside(runDir, entry.contextPackSnapshot);
      if (!existsSync(snapshotPath)) {
        errors.push(`replay snapshot not found: ${entry.contextPackSnapshot}`);
      } else if (sha256File(snapshotPath) !== entry.contextPackSha256) {
        errors.push(`sha256 mismatch: ${entry.contextPackSnapshot}`);
      }
      for (const artifact of entry.artifacts ?? []) {
        const artifactPath = resolveInside(runDir, artifact.path);
        if (!existsSync(artifactPath)) {
          errors.push(`replay artifact not found: ${artifact.path}`);
        } else if (sha256File(artifactPath) !== artifact.sha256) {
          errors.push(`sha256 mismatch: ${artifact.path}`);
        }
      }
    } catch (error) {
      errors.push(error.message);
    }
  }

  return {
    ok: errors.length === 0,
    errors,
    entries: replay?.entries?.length ?? 0,
  };
}
