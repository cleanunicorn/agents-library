// Manager pre-grant for a pi worker, loaded with `pi -e <this file>`.
//
// pi asks before no tool call on its own (its docs/security.md), so without
// this extension every escalation command runs unasked. The manager sets the
// role through the tab's environment (references/herdr.md § Pre-grants per
// kind):
//
//   PI_MANAGER_ROLE     coordinator | planner | reviewer
//   PI_MANAGER_RUN_DIR  absolute run directory, the only place a reader writes
//   PI_MANAGER_MAIN     main branch name, so a push to it asks
//   PI_MANAGER_GATE     optional: the reviewer's exact gate command
//   PI_MANAGER_DENY     optional: other items' worktrees, ':'-separated
//
// Missing or invalid settings block every tool call: failing open would
// launch an unrestricted worker. Command matching is not an OS sandbox; the
// manager's after-the-fact audit (references/console.md § Approvals) stays.

import { realpathSync } from "node:fs";
import { dirname, isAbsolute, resolve, sep } from "node:path";

const READERS = new Set(["planner", "reviewer"]);
const READ_TOOLS = new Set(["read", "grep", "find", "ls"]);
const WRITE_TOOLS = new Set(["write", "edit"]);

// Commands a reader may run unasked: each segment of a pipeline or chain must
// start with one of these.
const READ_COMMANDS = [
  /^git (log|diff|show|status|rev-parse|blame|branch --show-current)\b/,
  /^(ls|cat|head|tail|grep|rg|wc|pwd)\b/,
  /^sed -n\b/,
  /^find\b(?!.*\s-(exec|execdir|delete|ok)\b)/,
];

// Shell features that can write or run hidden commands. `2>&1` is harmless.
const SHELL_WRITES = /(?<![0-9])>|\$\(|`|<\(|>\(/;

function escalations(main) {
  const branch = main.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  return [
    /\bgit\s+push\b.*\s(--force(-with-lease|-if-includes)?\b|-[a-zA-Z]*f\b|\+\S)/,
    new RegExp(`\\bgit\\s+push\\b.*\\s(\\S*:)?(refs/heads/)?${branch}(\\s|$)`),
    /\bgh\s+pr\s+(merge|ready)\b/,
    /\bgit\s+branch\b.*\s(-[a-zA-Z]*D[a-zA-Z]*|--delete\s+--force|--force\s+--delete)(\s|$)/,
    /\bgit\s+worktree\s+remove\b/,
    recursiveForceRm,
  ].map((shape) => (typeof shape === "function" ? { test: shape } : shape));
}

// `rm -rf`, `rm -fr`, `rm -r -f`, `rm --recursive --force`, in any order.
function recursiveForceRm(command) {
  return segments(command).some((part) => {
    const tokens = part.split(/\s+/);
    const at = tokens.findIndex((token) => token === "rm" || token.endsWith("/rm"));
    if (at < 0) return false;
    const flags = tokens.slice(at + 1).filter((token) => token.startsWith("-"));
    const recursive = flags.some((flag) => flag === "--recursive" || /^-[a-zA-Z]*[rR]/.test(flag));
    const force = flags.some((flag) => flag === "--force" || /^-[a-zA-Z]*f/.test(flag));
    return recursive && force;
  });
}

export function settings(env) {
  const role = env.PI_MANAGER_ROLE ?? "";
  const runDir = env.PI_MANAGER_RUN_DIR ?? "";
  const main = env.PI_MANAGER_MAIN ?? "";
  if (role !== "coordinator" && !READERS.has(role)) return { error: `PI_MANAGER_ROLE is "${role}"` };
  if (!isAbsolute(runDir)) return { error: "PI_MANAGER_RUN_DIR is not an absolute path" };
  if (!main) return { error: "PI_MANAGER_MAIN is empty" };
  return {
    role,
    runDir: canonical(runDir),
    gate: env.PI_MANAGER_GATE ?? "",
    deny: (env.PI_MANAGER_DENY ?? "").split(":").filter(Boolean).map(canonical),
    escalations: escalations(main),
  };
}

// Resolve symlinks through the deepest existing ancestor, so a path that does
// not exist yet is judged by where it would land.
function canonical(path) {
  const absolute = resolve(path);
  try {
    return realpathSync(absolute);
  } catch {
    const parent = dirname(absolute);
    if (parent === absolute) return absolute;
    return resolve(canonical(parent), absolute.slice(parent.length + 1));
  }
}

function inside(path, dir) {
  return path === dir || path.startsWith(dir + sep);
}

function segments(command) {
  return command.split(/\|\||&&|[|;\n]/).map((part) => part.trim()).filter(Boolean);
}

function readOnlyCommand(command, config) {
  if (config.gate && command.trim() === config.gate) return true;
  if (SHELL_WRITES.test(command)) return false;
  return segments(command).every((part) => READ_COMMANDS.some((allowed) => allowed.test(part)));
}

// One verdict per tool call: "allow", "ask", or "block: <reason>".
export function decide(config, toolName, input, cwd) {
  if (config.error) return `block: pi-permissions misconfigured — ${config.error}`;
  if (READ_TOOLS.has(toolName)) return "allow";

  if (WRITE_TOOLS.has(toolName)) {
    const target = canonical(resolve(cwd, String(input?.path ?? "")));
    if (config.deny.some((dir) => inside(target, dir))) return `block: ${target} is another item's worktree`;
    if (config.role === "coordinator" || inside(target, config.runDir)) return "allow";
    return `block: a ${config.role} writes only to the run directory`;
  }

  if (toolName === "bash") {
    const command = String(input?.command ?? "");
    if (config.escalations.some((shape) => shape.test(command))) return "ask";
    if (config.role === "coordinator") return "allow";
    return readOnlyCommand(command, config) ? "allow" : "ask";
  }

  return "ask";
}

export default function (pi) {
  const config = settings(process.env);

  pi.on("tool_call", async (event, ctx) => {
    const verdict = decide(config, event.toolName, event.input, ctx.cwd ?? process.cwd());
    if (verdict === "allow") return undefined;
    if (verdict.startsWith("block: ")) return { block: true, reason: verdict.slice(7) };

    if (!ctx.hasUI) return { block: true, reason: "approval needed and no UI to ask" };
    const shown = event.toolName === "bash" ? event.input.command : JSON.stringify(event.input);
    const choice = await ctx.ui.select(`Manager approval needed — ${event.toolName}:\n\n  ${shown}\n\nAllow?`, [
      "Allow once",
      "Deny",
    ]);
    if (choice === "Allow once") return undefined;
    return { block: true, reason: "denied by the manager" };
  });
}
