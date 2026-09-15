// Run: node --test hooks/architect-enforce.test.mjs
// Set THRIVE_ROOT to a thrive checkout to run the live remedy leg, which
// credits a read through thrive's real architect-context hook and then
// checks that this overlay honours the credit.
import assert from "node:assert/strict";
import { randomUUID } from "node:crypto";
import { spawnSync } from "node:child_process";
import { existsSync, mkdirSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import os from "node:os";
import path from "node:path";
import { after, before, describe, test } from "node:test";
import { fileURLToPath } from "node:url";

const HOOK = fileURLToPath(new URL("./architect-enforce.mjs", import.meta.url));
const STATE_DIR = path.join(os.tmpdir(), "architect-context", "claude");
const THRIVE_ROOT = process.env.THRIVE_ROOT;

const DOCS = {
	a: ".ai-spec/architect/a.md",
	b: ".ai-spec/architect/b.md",
	c: ".ai-spec/architect/c.md",
	ghost: ".ai-spec/architect/ghost.md",
	spec: ".ai-spec/architect/spec-editing.md",
};

let fixtures;
let repo;
let outside;
const sessions = new Set();

before(() => {
	fixtures = mkdtempSync(path.join(os.tmpdir(), "architect-enforce-"));
	repo = path.join(fixtures, "repo");
	outside = path.join(fixtures, "outside");
	mkdirSync(path.join(repo, ".ai-spec/architect"), { recursive: true });
	mkdirSync(path.join(repo, "src"), { recursive: true });
	mkdirSync(path.join(repo, "docs"), { recursive: true });
	mkdirSync(outside, { recursive: true });
	writeFileSync(
		path.join(repo, ".ai-spec/architect/manifest.json"),
		JSON.stringify({
			code: {
				"src/**": [DOCS.a, DOCS.b, DOCS.ghost],
				"src/*.ts": DOCS.c,
			},
			authoring: {
				"docs/**": DOCS.spec,
			},
		})
	);
	for (const doc of [DOCS.a, DOCS.b, DOCS.c, DOCS.spec]) {
		writeFileSync(path.join(repo, doc), `# ${doc}\n`);
	}
	writeFileSync(path.join(repo, "src/x.ts"), "export const x = 1;\n");
	writeFileSync(path.join(repo, "src/three.ts"), "foo\nbar\nfoo\nbaz\nfoo\n");
	writeFileSync(path.join(outside, "x.ts"), "export const x = 1;\n");
});

after(() => {
	rmSync(fixtures, { recursive: true, force: true });
	for (const id of sessions) {
		rmSync(path.join(STATE_DIR, `${id}.json`), { force: true });
		rmSync(path.join(STATE_DIR, `${id}.enforce.json`), { force: true });
	}
});

function newSession() {
	const id = `enforce-test-${randomUUID()}`;
	sessions.add(id);
	return id;
}

function creditPath(sessionId) {
	return path.join(STATE_DIR, `${sessionId}.json`);
}

function tallyPath(sessionId) {
	return path.join(STATE_DIR, `${sessionId}.enforce.json`);
}

function seedCredit(sessionId, state) {
	mkdirSync(STATE_DIR, { recursive: true });
	writeFileSync(creditPath(sessionId), JSON.stringify(state));
}

function seedTally(sessionId, tally) {
	mkdirSync(STATE_DIR, { recursive: true });
	writeFileSync(tallyPath(sessionId), JSON.stringify(tally));
}

function runHook(payload, env = {}) {
	const result = spawnSync(process.execPath, [HOOK], {
		input: typeof payload === "string" ? payload : JSON.stringify(payload),
		encoding: "utf8",
		env: { ...process.env, ARCHITECT_CONTEXT_MODE: "", ARCHITECT_ENFORCE: "", ARCHITECT_ENFORCE_MIN_LINES: "0", ...env },
	});
	return {
		status: result.status,
		stdout: result.stdout,
		stderr: result.stderr,
		body: result.stdout ? JSON.parse(result.stdout) : null,
	};
}

function editPayload(sessionId, cwd, file, extra = {}) {
	return {
		session_id: sessionId,
		hook_event_name: "PreToolUse",
		tool_name: "Edit",
		cwd,
		tool_input: { file_path: file, old_string: "x = 1", new_string: "x = 2", ...extra },
	};
}

function denyReason(body) {
	return body.hookSpecificOutput.permissionDecisionReason;
}

describe("gate on unread code routes", () => {
	test("(1) denies an edit to a routed file, naming each unread doc, in the exact envelope", () => {
		const sessionId = newSession();
		const result = runHook(editPayload(sessionId, repo, "src/x.ts"));
		assert.equal(result.status, 0);
		assert.deepEqual(result.body, {
			hookSpecificOutput: {
				hookEventName: "PreToolUse",
				permissionDecision: "deny",
				permissionDecisionReason: `You're editing src/x.ts. This file has 1 changed lines this session (threshold 0). Architect docs routed to it that this session hasn't read in full:

- ${DOCS.a}
- ${DOCS.b}
- ${DOCS.c}

Read each in full (no offset or limit), then retry.`,
			},
		});
	});

	test("(2) credited reads clear the deny, a partial read does not, a missing doc is never named", () => {
		const sessionId = newSession();
		seedCredit(sessionId, { read: [DOCS.a, DOCS.c], partial: [DOCS.b] });
		const partial = runHook(editPayload(sessionId, repo, path.join(repo, "src/x.ts")));
		assert.equal(partial.body.hookSpecificOutput.permissionDecision, "deny");
		const reason = denyReason(partial.body);
		assert.ok(reason.includes(`- ${DOCS.b}`));
		assert.ok(!reason.includes(DOCS.a));
		assert.ok(!reason.includes(DOCS.c));
		assert.ok(!reason.includes(DOCS.ghost));

		seedCredit(sessionId, { read: [DOCS.a, DOCS.b, DOCS.c] });
		const cleared = runHook(editPayload(sessionId, repo, "src/x.ts"));
		assert.equal(cleared.status, 0);
		assert.equal(cleared.stdout, "");
	});

	test("a bare-array credit file and the legacy { instructed, read } shape both count", () => {
		const bare = newSession();
		seedCredit(bare, [DOCS.a, DOCS.b, DOCS.c]);
		assert.equal(runHook(editPayload(bare, repo, "src/x.ts")).stdout, "");

		const legacy = newSession();
		seedCredit(legacy, { instructed: { [DOCS.a]: 3 }, read: [DOCS.a, DOCS.b, DOCS.c] });
		assert.equal(runHook(editPayload(legacy, repo, "src/x.ts")).stdout, "");
	});

	test("(3) a read credited by thrive's real hook clears that doc from the deny", { skip: !THRIVE_ROOT }, () => {
		const thriveHook = path.join(THRIVE_ROOT, "scripts/hooks/architect-context/hook.mjs");
		const doc = ".ai-spec/architect/frontend-constants.md";
		const codeFile = "frontend/lib/constants/content-types.ts";
		assert.ok(existsSync(thriveHook), `missing ${thriveHook}`);
		assert.ok(existsSync(path.join(THRIVE_ROOT, doc)), `missing ${doc}`);
		assert.ok(existsSync(path.join(THRIVE_ROOT, codeFile)), `missing ${codeFile}`);
		const sessionId = newSession();

		const before = runHook(editPayload(sessionId, THRIVE_ROOT, codeFile));
		assert.equal(before.body.hookSpecificOutput.permissionDecision, "deny");
		assert.ok(denyReason(before.body).includes(`- ${doc}`));

		const credit = spawnSync(
			process.execPath,
			[thriveHook, "--tool=claude", "--event=PostToolUse"],
			{
				input: JSON.stringify({
					session_id: sessionId,
					hook_event_name: "PostToolUse",
					tool_name: "Read",
					cwd: THRIVE_ROOT,
					tool_input: { file_path: path.join(THRIVE_ROOT, doc) },
					tool_response: {},
				}),
				encoding: "utf8",
			}
		);
		assert.equal(credit.status, 0, credit.stderr);
		assert.ok(existsSync(creditPath(sessionId)), "thrive's hook wrote no credit file");

		const afterRead = runHook(editPayload(sessionId, THRIVE_ROOT, codeFile));
		assert.equal(afterRead.status, 0);
		if (afterRead.stdout) {
			assert.ok(!denyReason(afterRead.body).includes(doc), "credited doc still named");
		}
	});
});

describe("changed-line threshold", () => {
	test("a one-line edit denies under the default threshold of 0", () => {
		const sessionId = newSession();
		seedCredit(sessionId, { read: [] });
		const result = runHook(editPayload(sessionId, repo, "src/x.ts"), { ARCHITECT_ENFORCE_MIN_LINES: "" });
		assert.equal(result.body.hookSpecificOutput.permissionDecision, "deny");
		assert.ok(denyReason(result.body).includes("1 changed lines this session (threshold 0)"));
		assert.deepEqual(JSON.parse(readFileSync(tallyPath(sessionId), "utf8")), { creditSeen: true, files: { "src/x.ts": 1 } });
	});

	test("a one-line edit stays silent when the threshold is raised", () => {
		const sessionId = newSession();
		seedCredit(sessionId, { read: [] });
		const result = runHook(editPayload(sessionId, repo, "src/x.ts"), { ARCHITECT_ENFORCE_MIN_LINES: "50" });
		assert.equal(result.stdout, "");
	});

	test("two edits that together cross the threshold deny on the second", () => {
		const sessionId = newSession();
		seedCredit(sessionId, { read: [] });
		const edit = editPayload(sessionId, repo, "src/x.ts", { old_string: "a\nb\nc", new_string: "d" });
		assert.equal(runHook(edit, { ARCHITECT_ENFORCE_MIN_LINES: "5" }).stdout, "");
		const second = runHook(edit, { ARCHITECT_ENFORCE_MIN_LINES: "5" });
		assert.equal(second.body.hookSpecificOutput.permissionDecision, "deny");
		assert.ok(denyReason(second.body).includes("6 changed lines this session (threshold 5)"));
	});

	test("replace_all multiplies by the occurrences in the current file", () => {
		const single = newSession();
		seedCredit(single, { read: [] });
		const base = editPayload(single, repo, "src/three.ts", { old_string: "foo", new_string: "qux" });
		assert.equal(runHook(base, { ARCHITECT_ENFORCE_MIN_LINES: "3" }).stdout, "");

		const all = newSession();
		seedCredit(all, { read: [] });
		const result = runHook({ ...base, session_id: all, tool_input: { ...base.tool_input, replace_all: true } }, { ARCHITECT_ENFORCE_MIN_LINES: "3" });
		assert.equal(result.body.hookSpecificOutput.permissionDecision, "deny");
		assert.ok(denyReason(result.body).includes("3 changed lines"));
	});

	test("a Write to a new file counts its content lines", () => {
		const sessionId = newSession();
		seedCredit(sessionId, { read: [] });
		const write = (content) => ({
			session_id: sessionId,
			tool_name: "Write",
			cwd: repo,
			tool_input: { file_path: "src/new.ts", content },
		});
		assert.equal(runHook(write("a\nb"), { ARCHITECT_ENFORCE_MIN_LINES: "3" }).stdout, "");
		const crossed = runHook(write("a"), { ARCHITECT_ENFORCE_MIN_LINES: "3" });
		assert.equal(crossed.body.hookSpecificOutput.permissionDecision, "deny");
	});

	test("a Write over an existing file counts added plus removed lines", () => {
		const sessionId = newSession();
		seedCredit(sessionId, { read: [] });
		const result = runHook(
			{ session_id: sessionId, tool_name: "Write", cwd: repo, tool_input: { file_path: "src/three.ts", content: "foo\nbar\nNEW\nbaz\nfoo\n" } },
			{ ARCHITECT_ENFORCE_MIN_LINES: "2" }
		);
		assert.equal(result.body.hookSpecificOutput.permissionDecision, "deny");
		assert.ok(denyReason(result.body).includes("2 changed lines"));
	});

	test("ARCHITECT_ENFORCE_MIN_LINES=0 denies a one-line edit", () => {
		const sessionId = newSession();
		const result = runHook(editPayload(sessionId, repo, "src/x.ts"), { ARCHITECT_ENFORCE_MIN_LINES: "0" });
		assert.equal(result.body.hookSpecificOutput.permissionDecision, "deny");
	});

	test("a session with no credit file accumulates across calls and crosses the threshold", () => {
		const sessionId = newSession();
		const edit = editPayload(sessionId, repo, "src/x.ts");
		const env = { ARCHITECT_ENFORCE_MIN_LINES: "3" };
		assert.equal(runHook(edit, env).stdout, "");
		assert.equal(runHook(edit, env).stdout, "");
		assert.deepEqual(JSON.parse(readFileSync(tallyPath(sessionId), "utf8")), { creditSeen: false, files: { "src/x.ts": 2 } });
		const third = runHook(edit, env);
		assert.equal(third.body.hookSpecificOutput.permissionDecision, "deny");
		assert.ok(denyReason(third.body).includes("3 changed lines this session (threshold 3)"));
	});

	test("a credit file that was seen and then removed resets the tally", () => {
		const sessionId = newSession();
		const edit = editPayload(sessionId, repo, "src/x.ts");
		const env = { ARCHITECT_ENFORCE_MIN_LINES: "50" };
		seedCredit(sessionId, { read: [] });
		runHook(edit, env);
		assert.equal(JSON.parse(readFileSync(tallyPath(sessionId), "utf8")).creditSeen, true);

		rmSync(creditPath(sessionId), { force: true });
		assert.equal(runHook(edit, env).stdout, "");
		assert.deepEqual(JSON.parse(readFileSync(tallyPath(sessionId), "utf8")), { creditSeen: false, files: { "src/x.ts": 1 } });

		seedCredit(sessionId, { read: [] });
		seedTally(sessionId, { creditSeen: true, files: { "src/x.ts": 100 } });
		const denied = runHook(edit, env);
		assert.equal(denied.body.hookSpecificOutput.permissionDecision, "deny");
		assert.ok(denyReason(denied.body).includes("101 changed lines"));
	});

	test("a credit file that was never present never resets a seeded tally", () => {
		const sessionId = newSession();
		seedTally(sessionId, { creditSeen: false, files: { "src/x.ts": 100 } });
		const denied = runHook(editPayload(sessionId, repo, "src/x.ts"), { ARCHITECT_ENFORCE_MIN_LINES: "50" });
		assert.equal(denied.body.hookSpecificOutput.permissionDecision, "deny");
		assert.ok(denyReason(denied.body).includes("101 changed lines"));
	});

	test("a flat pre-marker tally file reads as never having seen the credit file", () => {
		const sessionId = newSession();
		seedTally(sessionId, { "src/x.ts": 100 });
		const denied = runHook(editPayload(sessionId, repo, "src/x.ts"), { ARCHITECT_ENFORCE_MIN_LINES: "50" });
		assert.equal(denied.body.hookSpecificOutput.permissionDecision, "deny");
		assert.deepEqual(JSON.parse(readFileSync(tallyPath(sessionId), "utf8")), { creditSeen: false, files: { "src/x.ts": 101 } });
	});
});

describe("silent paths", () => {
	test("observe and off modes emit nothing", () => {
		const sessionId = newSession();
		for (const mode of ["observe", "off"]) {
			const result = runHook(editPayload(sessionId, repo, "src/x.ts"), { ARCHITECT_CONTEXT_MODE: mode });
			assert.equal(result.status, 0, mode);
			assert.equal(result.stdout, "", mode);
		}
	});

	test("ARCHITECT_ENFORCE=false emits nothing even when the mode says enforce", () => {
		const result = runHook(editPayload(newSession(), repo, "src/x.ts"), { ARCHITECT_ENFORCE: "false", ARCHITECT_CONTEXT_MODE: "enforce" });
		assert.equal(result.status, 0);
		assert.equal(result.stdout, "");
	});

	test("ARCHITECT_ENFORCE=true denies even when the mode says off", () => {
		const result = runHook(editPayload(newSession(), repo, "src/x.ts"), { ARCHITECT_ENFORCE: "true", ARCHITECT_CONTEXT_MODE: "off" });
		assert.equal(result.status, 0);
		assert.equal(JSON.parse(result.stdout).hookSpecificOutput.permissionDecision, "deny");
	});

	test("a file matching only an authoring route is thrive's to gate", () => {
		const result = runHook(editPayload(newSession(), repo, "docs/guide.md"));
		assert.equal(result.stdout, "");
	});

	test("no manifest above the file emits nothing", () => {
		const result = runHook(editPayload(newSession(), outside, "x.ts"));
		assert.equal(result.status, 0);
		assert.equal(result.stdout, "");
	});

	test("no session_id emits nothing", () => {
		const payload = editPayload(null, repo, "src/x.ts");
		delete payload.session_id;
		assert.equal(runHook(payload).stdout, "");
	});

	test("a Read is never denied", () => {
		const result = runHook({ ...editPayload(newSession(), repo, "src/x.ts"), tool_name: "Read" });
		assert.equal(result.stdout, "");
	});

	test("malformed JSON exits 0 with one stderr line and no stdout", () => {
		const result = runHook("{not json");
		assert.equal(result.status, 0);
		assert.equal(result.stdout, "");
		assert.ok(result.stderr.startsWith("architect-enforce hook:"));
	});
});
