#!/usr/bin/env node
/**
 * Denies a Write or Edit to a code-routed file until every architect doc the
 * manifest routes it to has been read in full this session, once the file's
 * cumulative changed-line tally for the session reaches a threshold.
 *
 * Runs as a Claude Code PreToolUse hook for Write|Edit and reads the credit
 * file thrive's own architect-context hook writes at
 * `<os.tmpdir()>/architect-context/claude/<session_id>.json`, so crediting a
 * read stays thrive's job and this overlay only adds the deny. Only the
 * manifest's `code` section is consulted; authoring routes are gated by
 * thrive already.
 *
 * Yields silently when: the mode is `observe` or `off` — `ARCHITECT_ENFORCE`
 * (`true` → enforce, `false` → off) wins when set, else `ARCHITECT_CONTEXT_MODE`; no
 * `.ai-spec/architect/manifest.json` sits above the edited file; the payload
 * carries no `session_id` (a deny with no way to clear it is worse than none);
 * the tool is a Read (the remedy must stay performable); the file matches no
 * code route; every routed doc that exists on disk is already credited; or
 * the file's tally is still below `ARCHITECT_ENFORCE_MIN_LINES` (default 0,
 * which denies on the first changed line; raise it to let small edits through).
 *
 * The tally lives beside the credit file as `<session_id>.enforce.json`,
 * shaped `{ "creditSeen": boolean, "files": { "<repo-relative path>": n } }`,
 * and is updated before the decision so a denied call still counts. Thrive's
 * compact-checkpoint removes only the credit file, so a credit file that was
 * seen and is now absent is the post-compact signal and the tally starts
 * over too. Thrive creates the credit file only on the first full doc read,
 * so a session that has read nothing has none; `creditSeen` is what keeps
 * that session's tally accumulating instead of resetting on every call.
 *
 * Fails open on every error: one stderr line, exit 0, never `process.exit()`.
 */
import { existsSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import os from "node:os";
import path from "node:path";

const DEDUP_DIR = path.join(os.tmpdir(), "architect-context", "claude");
const ARCHITECT_DIR = ".ai-spec/architect";
const MANIFEST_RELATIVE = `${ARCHITECT_DIR}/manifest.json`;
const DEFAULT_MIN_LINES = 0;

// ARCHITECT_ENFORCE is the plain boolean switch; ARCHITECT_CONTEXT_MODE is the
// three-way knob shared with thrive's own hook. The boolean wins when set so a
// one-off `ARCHITECT_ENFORCE=false` needs no knowledge of the mode names.
function resolveMode() {
	const flag = (process.env.ARCHITECT_ENFORCE || "").trim().toLowerCase();
	if (flag === "false") return "off";
	if (flag === "true") return "enforce";
	return process.env.ARCHITECT_CONTEXT_MODE || "enforce";
}

function main(stdin) {
	if (resolveMode() !== "enforce") return;

	const payload = JSON.parse(stdin);
	if (payload.tool_name === "Read") return;

	const filePath = payload.tool_input?.file_path;
	if (typeof filePath !== "string" || !filePath) return;
	const cwd = payload.cwd || process.cwd();
	const absolute = path.isAbsolute(filePath) ? filePath : path.resolve(cwd, filePath);

	const manifestRoot = findManifestRoot(path.dirname(absolute));
	if (!manifestRoot) return;

	const sessionId = payload.session_id;
	if (!sessionId) return;

	const relativePath = toRelative(manifestRoot, absolute);
	if (!relativePath) return;

	const creditPath = path.join(DEDUP_DIR, `${sessionId}.json`);
	const tallyPath = path.join(DEDUP_DIR, `${sessionId}.enforce.json`);
	const tally = loadTally(tallyPath, creditPath);
	tally.files[relativePath] =
		(tally.files[relativePath] || 0) +
		countChangedLines(payload.tool_name, payload.tool_input, absolute);
	writeTally(tallyPath, tally);

	const minLines = readMinLines();
	if (tally.files[relativePath] < minLines) return;

	const matched = computeCodeMatched(manifestRoot, relativePath);
	const { existing } = computeExistingMissing(manifestRoot, matched);
	const credited = readCreditedSet(creditPath);
	const unread = existing.filter((d) => !credited.has(d));
	if (unread.length === 0) return;

	writeStdout(emitDeny(buildDenyReason(relativePath, unread, tally.files[relativePath], minLines)));
}

function emitDeny(text) {
	return {
		hookSpecificOutput: {
			hookEventName: "PreToolUse",
			permissionDecision: "deny",
			permissionDecisionReason: text,
		},
	};
}

function buildDenyReason(relativePath, unread, changedLines, minLines) {
	const listed = unread.map((d) => `- ${d}`).join("\n");
	return `You're editing ${relativePath}. This file has ${changedLines} changed lines this session (threshold ${minLines}). Architect docs routed to it that this session hasn't read in full:

${listed}

Read each in full (no offset or limit), then retry.`;
}

// --- Credit and tally state ---

/**
 * Returns the set of repo-relative paths thrive has credited as read in full.
 * Accepts every shape thrive's `loadDedupState` accepts — a bare array, the
 * current `{ read, partial }`, and the legacy `{ instructed, read }` — and
 * counts only `read`; a partial read never clears a deny.
 */
function readCreditedSet(creditPath) {
	if (!existsSync(creditPath)) return new Set();
	try {
		const parsed = JSON.parse(readFileSync(creditPath, "utf8"));
		if (Array.isArray(parsed)) return new Set(parsed);
		return new Set(Array.isArray(parsed?.read) ? parsed.read : []);
	} catch {
		return new Set();
	}
}

/**
 * Loads the tally, resetting it when the credit file was seen on an earlier
 * call and is gone now. A flat `{ "<path>": n }` file from before the marker
 * existed reads as never having seen the credit file.
 */
function loadTally(tallyPath, creditPath) {
	const creditExists = existsSync(creditPath);
	const stored = readTally(tallyPath);
	if (stored.creditSeen && !creditExists) return { creditSeen: false, files: {} };
	return { creditSeen: stored.creditSeen || creditExists, files: stored.files };
}

function readTally(tallyPath) {
	const empty = { creditSeen: false, files: {} };
	if (!existsSync(tallyPath)) return empty;
	try {
		const parsed = JSON.parse(readFileSync(tallyPath, "utf8"));
		if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) return empty;
		if (parsed.files && typeof parsed.files === "object") {
			return { creditSeen: parsed.creditSeen === true, files: parsed.files };
		}
		return { creditSeen: false, files: parsed };
	} catch {
		return empty;
	}
}

function writeTally(tallyPath, tally) {
	mkdirSync(path.dirname(tallyPath), { recursive: true });
	writeFileSync(tallyPath, JSON.stringify(tally));
}

function readMinLines() {
	const raw = process.env.ARCHITECT_ENFORCE_MIN_LINES;
	if (raw === undefined || raw === "") return DEFAULT_MIN_LINES;
	const parsed = Number(raw);
	return Number.isFinite(parsed) && parsed >= 0 ? parsed : DEFAULT_MIN_LINES;
}

/**
 * Lines this call changes. An Edit counts the larger side of the
 * replacement, times the occurrences it hits when `replace_all` is set. A
 * Write counts every line of a new file, or the lines added plus removed
 * against the file's current content. Any other tool shape counts nothing.
 */
function countChangedLines(toolName, toolInput, absolute) {
	if (toolName === "Edit") {
		const oldString = typeof toolInput?.old_string === "string" ? toolInput.old_string : "";
		const newString = typeof toolInput?.new_string === "string" ? toolInput.new_string : "";
		const perOccurrence = Math.max(lineCount(oldString), lineCount(newString));
		const occurrences = toolInput?.replace_all ? countOccurrences(absolute, oldString) : 1;
		return perOccurrence * Math.max(occurrences, 1);
	}
	if (toolName === "Write") {
		const content = typeof toolInput?.content === "string" ? toolInput.content : "";
		if (!existsSync(absolute)) return lineCount(content);
		return countLineDiff(readFileSafely(absolute), content);
	}
	return 0;
}

function lineCount(text) {
	return text ? text.split("\n").length : 0;
}

function countOccurrences(absolute, needle) {
	if (!needle) return 1;
	const haystack = readFileSafely(absolute);
	let count = 0;
	let from = haystack.indexOf(needle);
	while (from !== -1) {
		count += 1;
		from = haystack.indexOf(needle, from + needle.length);
	}
	return count;
}

function countLineDiff(before, after) {
	const counts = new Map();
	for (const line of before.split("\n")) counts.set(line, (counts.get(line) || 0) + 1);
	for (const line of after.split("\n")) counts.set(line, (counts.get(line) || 0) - 1);
	let changed = 0;
	for (const n of counts.values()) changed += Math.abs(n);
	return changed;
}

function readFileSafely(absolute) {
	try {
		return readFileSync(absolute, "utf8");
	} catch {
		return "";
	}
}

// --- Manifest routing, copied from thrive's architect-context hook ---

function computeCodeMatched(manifestRoot, relativePath) {
	const manifest = loadManifest(manifestRoot);
	return [...resolveMatchedValues(matchManifest(relativePath, manifest.code))].sort();
}

function globToRegExp(pattern) {
	let p = pattern;
	if (p.endsWith("/")) p += "**";

	let out = "";
	let i = 0;
	while (i < p.length) {
		const c = p[i];
		if (c === "{") {
			const close = p.indexOf("}", i);
			if (close === -1) {
				out += c.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
				i += 1;
				continue;
			}
			const alts = p.slice(i + 1, close).split(",");
			out +=
				"(?:" +
				alts.map((a) => a.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")).join("|") +
				")";
			i = close + 1;
			continue;
		}
		if (c === "*") {
			if (p[i + 1] === "*") {
				if (p[i + 2] === "/") {
					out += "(?:.*/)?";
					i += 3;
				} else {
					out += ".*";
					i += 2;
				}
			} else {
				out += "[^/]*";
				i += 1;
			}
			continue;
		}
		out += c.replace(/[.+?^${}()|[\]\\]/g, "\\$&");
		i += 1;
	}
	return new RegExp("^" + out + "$");
}

/**
 * Matches a repo-root-relative path against a parsed glob-to-doc(s) map and
 * returns the raw matched values, in manifest key order.
 *
 * Map-agnostic: takes any flat glob→string|string[] object, so the same
 * function serves the manifest's "code" and "authoring" sections alike —
 * every value in both is already a repo-root-relative path, so there's
 * nothing left for the caller to resolve beyond flattening the arrays.
 */
export function matchManifest(relativePath, manifest) {
	const matched = [];
	for (const [pattern, value] of Object.entries(manifest)) {
		if (globToRegExp(pattern).test(relativePath)) {
			matched.push(value);
		}
	}
	return matched;
}

/**
 * Walks up from startDir looking for `.ai-spec/architect/manifest.json`,
 * returning the directory that carries it or null if the filesystem root is
 * reached with no match.
 */
export function findManifestRoot(startDir) {
	let dir = startDir;
	while (true) {
		if (existsSync(path.join(dir, MANIFEST_RELATIVE))) {
			return dir;
		}
		const parent = path.dirname(dir);
		if (parent === dir) return null;
		dir = parent;
	}
}

function toRelative(manifestRoot, absolutePath) {
	const rel = path
		.relative(manifestRoot, absolutePath)
		.split(path.sep)
		.join("/");
	if (!rel || rel.startsWith("..")) return null;
	return rel;
}

function resolveMatchedValues(rawMatches) {
	const resolved = new Set();
	for (const value of rawMatches) {
		for (const v of Array.isArray(value) ? value : [value]) {
			resolved.add(v);
		}
	}
	return resolved;
}

/**
 * Loads and shapes the manifest into `{ code, authoring }`. A manifest
 * carrying either key at its top level is the current two-section shape,
 * each section defaulting to `{}` if the other key is absent. A manifest
 * carrying neither is the pre-merge flat shape — a branch that hasn't
 * picked up the merged manifest yet — treated as `{ code: <the whole
 * object>, authoring: {} }` so its routes still match on every verb
 * instead of matching nothing.
 */
function loadManifest(manifestRoot) {
	const raw = JSON.parse(
		readFileSync(path.join(manifestRoot, MANIFEST_RELATIVE), "utf8")
	);
	const isSectioned =
		Object.prototype.hasOwnProperty.call(raw, "code") ||
		Object.prototype.hasOwnProperty.call(raw, "authoring");

	if (isSectioned) {
		return {
			code: raw.code && typeof raw.code === "object" ? raw.code : {},
			authoring:
				raw.authoring && typeof raw.authoring === "object" ? raw.authoring : {},
		};
	}
	return { code: raw, authoring: {} };
}

function computeExistingMissing(manifestRoot, matched) {
	const missing = matched.filter(
		(d) => !existsSync(path.join(manifestRoot, d))
	);
	const existing = matched.filter((d) =>
		existsSync(path.join(manifestRoot, d))
	);
	return { missing, existing };
}

function writeStdout(body) {
	// A downstream reader that stops early (a size cap, a timeout, a
	// cancelled tool call) closes the pipe before this write completes. The
	// resulting EPIPE fires asynchronously as an 'error' event on the stdout
	// stream, not as an exception the surrounding try/catch can see, so it
	// has to be swallowed here to keep the fail-open guarantee real.
	process.stdout.on("error", () => {});
	process.stdout.write(JSON.stringify(body));
}

try {
	main(readFileSync(0, "utf8"));
} catch (err) {
	try {
		process.stderr.write(`architect-enforce hook: ${err && err.message ? err.message : err}\n`);
	} catch {
		// stderr itself failing leaves nothing more to do
	}
}
// Deliberately no process.exit(): exit() doesn't wait for a pending stdout
// write to flush, and every throwing path above is already caught, so
// falling off the end exits 0 with the payload drained.
