#!/usr/bin/env node
/**
 * Pure reducer for deep-research workflow state machine.
 * (runState, event, spec) => { runState, error? }
 */
import { readFileSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import YAML from "yaml";

const SCRIPT_DIR = dirname(fileURLToPath(import.meta.url));
const DEFAULT_SPEC_PATH = join(
  SCRIPT_DIR,
  "..",
  "..",
  "spec",
  "workflows",
  "deep-research.yaml",
);

export function loadWorkflowSpec(specPath = DEFAULT_SPEC_PATH) {
  return YAML.parse(readFileSync(specPath, "utf8"));
}

export function createInitialRunState(spec, runId = "local-run") {
  return {
    runId,
    workflowId: spec.workflowId,
    currentState: spec.initialState,
    barrier: {
      expected: 0,
      completed: 0,
      pendingSubagents: [],
    },
    history: [],
    aborted: false,
  };
}

function getStateDef(spec, stateName) {
  return spec.states[stateName] ?? null;
}

function pushHistory(runState, event, from, to) {
  return {
    ...runState,
    history: [
      ...runState.history,
      {
        at: new Date().toISOString(),
        event: event.type,
        from,
        to,
        detail: event,
      },
    ],
  };
}

function transitionTo(runState, spec, from, to, event) {
  if (!spec.states[to]) {
    return { runState, error: `Unknown target state: ${to}` };
  }
  const next = pushHistory(
    {
      ...runState,
      currentState: to,
      barrier: { expected: 0, completed: 0, pendingSubagents: [] },
    },
    event,
    from,
    to,
  );
  return { runState: next };
}

function handleGateResult(runState, spec, event) {
  const stateName = runState.currentState;
  const stateDef = getStateDef(spec, stateName);
  if (!stateDef || stateDef.kind === "terminal") {
    return { runState, error: `Cannot gate-transition from terminal state ${stateName}` };
  }
  if (event.gate !== stateDef.gate) {
    return {
      runState,
      error: `Gate "${event.gate}" does not match state "${stateName}" gate "${stateDef.gate}"`,
    };
  }
  if (
    event.type === "GATE_PASSED" &&
    stateDef.kind === "parallel_subagents" &&
    !isBarrierComplete(runState)
  ) {
    return { runState, error: `Cannot pass state "${stateName}": barrier incomplete` };
  }

  if (event.type === "GATE_PASSED") {
    return transitionTo(runState, spec, stateName, stateDef.onPass, event);
  }

  if (event.type === "GATE_FAILED") {
    return transitionTo(runState, spec, stateName, stateDef.onFail, event);
  }

  return { runState, error: `Unhandled gate event ${event.type}` };
}

function handleSubagentCompleted(runState, spec, event) {
  const stateName = runState.currentState;
  const stateDef = getStateDef(spec, stateName);
  if (!stateDef || stateDef.kind !== "parallel_subagents") {
    return { runState, error: `SUBAGENT_COMPLETED invalid in state ${stateName}` };
  }
  if (!runState.barrier.pendingSubagents.includes(event.subagentId)) {
    return {
      runState,
      error: `Subagent "${event.subagentId}" is not pending in state "${stateName}"`,
    };
  }

  const pending = runState.barrier.pendingSubagents.filter((id) => id !== event.subagentId);
  const completed = runState.barrier.completed + 1;
  const next = {
    ...runState,
    barrier: {
      ...runState.barrier,
      completed,
      pendingSubagents: pending,
    },
  };

  return { runState: pushHistory(next, event, stateName, stateName) };
}

function handleSubagentFailed(runState, spec, event) {
  const stateName = runState.currentState;
  const stateDef = getStateDef(spec, stateName);
  if (!stateDef || stateDef.kind !== "parallel_subagents") {
    return { runState, error: `SUBAGENT_FAILED invalid in state ${stateName}` };
  }
  return transitionTo(runState, spec, stateName, stateDef.onFail, event);
}

function handleEnterVerify(runState, spec, evidenceTargets = []) {
  const stateName = runState.currentState;
  const stateDef = getStateDef(spec, stateName);
  if (!stateDef || stateDef.kind !== "parallel_subagents") {
    return { runState };
  }

  const ids = evidenceTargets.map((t) => t.targetId ?? t);
  if (ids.some((id) => typeof id !== "string" || id.trim() === "")) {
    return { runState, error: "Evidence target ids must be non-empty strings" };
  }
  if (ids.some((id) => !/^[A-Za-z0-9][A-Za-z0-9._-]*$/.test(id))) {
    return {
      runState,
      error: "Evidence target ids must be safe identifiers",
    };
  }
  if (new Set(ids).size !== ids.length) {
    return { runState, error: "Evidence target ids must be unique" };
  }
  return {
    runState: {
      ...runState,
      barrier: {
        expected: ids.length,
        completed: 0,
        pendingSubagents: ids,
      },
    },
  };
}

function isBarrierComplete(runState) {
  return (
    runState.barrier.expected > 0 &&
    runState.barrier.completed >= runState.barrier.expected &&
    runState.barrier.pendingSubagents.length === 0
  );
}

export function reduce(runState, event, spec) {
  switch (event.type) {
    case "USER_ABORT": {
      const abortTransition = spec.transitions?.find((t) => t.event === "USER_ABORT");
      const to = abortTransition?.to ?? "aborted";
      const next = transitionTo({ ...runState, aborted: true }, spec, runState.currentState, to, event);
      return next;
    }

    case "PHASE_ENTER": {
      if (event.state !== runState.currentState) {
        return {
          runState,
          error: `PHASE_ENTER state "${event.state}" does not match current state "${runState.currentState}"`,
        };
      }
      if (event.state === "verify" && Array.isArray(event.evidenceTargets)) {
        const withBarrier = handleEnterVerify(runState, spec, event.evidenceTargets);
        return withBarrier;
      }
      return { runState };
    }

    case "PHASE_ARTIFACT_WRITTEN":
      return { runState: pushHistory(runState, event, runState.currentState, runState.currentState) };

    case "GATE_PASSED":
    case "GATE_FAILED":
      return handleGateResult(runState, spec, event);

    case "SUBAGENT_COMPLETED":
      return handleSubagentCompleted(runState, spec, event);

    case "SUBAGENT_FAILED":
      return handleSubagentFailed(runState, spec, event);

    case "BARRIER_CHECK": {
      if (isBarrierComplete(runState)) {
        return { runState, barrierComplete: true };
      }
      return { runState, barrierComplete: false };
    }

    default:
      return { runState, error: `Unknown event type: ${event.type}` };
  }
}

export function canTransition(runState, spec, gateResult) {
  const stateDef = getStateDef(spec, runState.currentState);
  if (!stateDef || stateDef.kind === "terminal") {
    return false;
  }

  if (stateDef.kind === "parallel_subagents" && gateResult === "pass") {
    return isBarrierComplete(runState);
  }

  return true;
}
