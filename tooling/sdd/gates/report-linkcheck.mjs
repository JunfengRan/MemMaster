#!/usr/bin/env node
import { requireOk, pass, fail } from "./delivery-utils.mjs";

const runDir = process.argv[2];
if (!runDir) fail("usage: report-linkcheck.mjs <run-dir>");
const data = requireOk(runDir, "report-linkcheck");
if (data.brokenLinks !== 0) fail("report has broken links");
if (data.offline !== true) fail("report must be fully offline");
pass("report-linkcheck: ok");
