import {
  closeSync,
  existsSync,
  fsyncSync,
  mkdirSync,
  openSync,
  readFileSync,
  renameSync,
  rmSync,
  statSync,
  writeFileSync,
} from "node:fs";
import { basename, dirname, join } from "node:path";
import { randomUUID } from "node:crypto";

const DEFAULT_TIMEOUT_MS = 5_000;
const DEFAULT_RETRY_MS = 20;
const DEFAULT_STALE_MS = 30_000;

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function isProcessAlive(pid) {
  if (!Number.isInteger(pid) || pid <= 0) return false;
  try {
    process.kill(pid, 0);
    return true;
  } catch (error) {
    return error.code === "EPERM";
  }
}

function readLockOwner(lockDir) {
  try {
    return JSON.parse(readFileSync(join(lockDir, "owner.json"), "utf8"));
  } catch {
    return null;
  }
}

function removeStaleLock(lockDir, staleMs) {
  const owner = readLockOwner(lockDir);
  const createdAtMs = Date.parse(owner?.createdAt ?? "");
  let lockAgeMs = 0;
  try {
    lockAgeMs = Date.now() - statSync(lockDir).mtimeMs;
  } catch (error) {
    return error.code === "ENOENT";
  }
  const ageMs = Number.isFinite(createdAtMs)
    ? Date.now() - createdAtMs
    : lockAgeMs;
  const isStale = ageMs >= staleMs;
  if (isStale && !isProcessAlive(owner?.pid)) {
    rmSync(lockDir, { recursive: true, force: true });
    return true;
  }
  return false;
}

async function acquireRunLock(runDir, options = {}) {
  const timeoutMs = options.timeoutMs ?? DEFAULT_TIMEOUT_MS;
  const retryMs = options.retryMs ?? DEFAULT_RETRY_MS;
  const staleMs = options.staleMs ?? DEFAULT_STALE_MS;
  const lockDir = join(runDir, ".write-lock");
  const startedAt = Date.now();

  while (true) {
    try {
      mkdirSync(lockDir);
      writeFileSync(
        join(lockDir, "owner.json"),
        `${JSON.stringify({
          pid: process.pid,
          createdAt: new Date().toISOString(),
        })}\n`,
        "utf8",
      );
      return () => rmSync(lockDir, { recursive: true, force: true });
    } catch (error) {
      if (error.code !== "EEXIST") throw error;
      if (removeStaleLock(lockDir, staleMs)) continue;
      if (Date.now() - startedAt >= timeoutMs) {
        const owner = readLockOwner(lockDir);
        throw new Error(
          `Timed out acquiring run lock ${lockDir}` +
            (owner?.pid ? ` held by pid ${owner.pid}` : ""),
        );
      }
      await sleep(retryMs);
    }
  }
}

export async function withRunLock(runDir, operation, options = {}) {
  const release = await acquireRunLock(runDir, options);
  try {
    return await operation();
  } finally {
    release();
  }
}

export function atomicWriteText(path, content) {
  const tempPath = join(
    dirname(path),
    `.${basename(path)}.tmp-${process.pid}-${randomUUID()}`,
  );
  let fd;
  try {
    fd = openSync(tempPath, "wx");
    writeFileSync(fd, content, "utf8");
    fsyncSync(fd);
    closeSync(fd);
    fd = undefined;
    renameSync(tempPath, path);
  } finally {
    if (fd !== undefined) closeSync(fd);
    if (existsSync(tempPath)) rmSync(tempPath, { force: true });
  }
}

export function atomicWriteJson(path, value) {
  atomicWriteText(path, `${JSON.stringify(value, null, 2)}\n`);
}

export function appendJsonLine(path, value) {
  writeFileSync(path, `${JSON.stringify(value)}\n`, {
    encoding: "utf8",
    flag: "a",
  });
}
