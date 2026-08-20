#!/usr/bin/env node
import { requireOk, pass, fail } from "./delivery-utils.mjs";

const runDir = process.argv[2];
if (!runDir) fail("usage: pilot-budget.mjs <run-dir>");
const data = requireOk(runDir, "pilot-budget");
if (typeof data.hardBudgetUsd !== "number") fail("hardBudgetUsd required");
if (data.withinBudget !== true) fail("pilot projection exceeds budget");
pass("pilot-budget: ok");
