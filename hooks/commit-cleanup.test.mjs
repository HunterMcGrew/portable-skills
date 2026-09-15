// Run: node --test hooks/commit-cleanup.test.mjs
//
// Every case builds a throwaway repo under os.tmpdir() carrying a manifest,
// stages a file, pipes a payload into the hook, and asserts on stdout and
// exit code. The deny fires on a fresh tree, and the remedy — the same
// commit run again — clears it.
import assert from "node:assert/strict";
import { execFileSync, spawnSync } from "node:child_process";
import { existsSync, mkdirSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import os from "node:os";
import path from "node:path";
import { after, before, describe, test } from "node:test";
import { fileURLToPath } from "node:url";

import { describeCommitTimeStaging, findCommitSegment, tokenize } from "./commit-cleanup.mjs";

const HOOK = fileURLToPath(new URL("./commit-cleanup.mjs", import.meta.url));
const REFERENCE_RELATIVE = ".ai-spec/references/commit-cleanup.md";
const MANIFEST_RELATIVE = ".ai-spec/architect/manifest.json";
const INSTRUCTION_OPENER = "Before this commit lands, review the staged diff";

// The reference file as thrive ships it on the commit-cleanup branch; a
// THRIVE_ROOT checkout that carries the real file overrides this copy.
const REFERENCE_TEXT = `# Commit Cleanup

Before this commit lands, review the staged diff (\`git diff --cached\`) for readability, reusability, and maintainability. Stay inside the local frame from \`.ai-spec/rules/code-standards.md\` § \`Refactor scope\` — the changed lines, their containing functions, helpers you extract from them, files already in the diff. Apply \`.ai-spec/rules/code-comments.md\` § \`Review\` to every comment on a changed line. Fix what you find, re-stage, and run the same commit again. Name anything outside the frame in one line to the user and leave it there.

## Why

The paragraph above is what an agent session receives when its first commit is denied.
`;

let fixtures;
before(() => {
	fixtures = mkdtempSync(path.join(os.tmpdir(), "commit-cleanup-"));
});
after(() => {
	rmSync(fixtures, { recursive: true, force: true });
});

function git(dir, ...args) {
	return execFileSync("git", ["-C", dir, ...args], {
		encoding: "utf8",
		stdio: ["ignore", "pipe", "pipe"],
	}).trim();
}

function referenceText() {
	const live = process.env.THRIVE_ROOT && path.join(process.env.THRIVE_ROOT, REFERENCE_RELATIVE);
	return live && existsSync(live) ? readFileSync(live, "utf8") : REFERENCE_TEXT;
}

/**
 * A fresh repo carrying a manifest and a copy of the reference file, so the
 * hook's runtime read is exercised against the text it will ship with.
 */
function makeRepo(name, { withReference = true, withManifest = true } = {}) {
	const dir = path.join(fixtures, name);
	mkdirSync(dir, { recursive: true });
	git(dir, "init", "-q", "-b", "main");
	git(dir, "config", "user.email", "test@example.com");
	git(dir, "config", "user.name", "Test");
	if (withManifest) {
		const manifest = path.join(dir, MANIFEST_RELATIVE);
		mkdirSync(path.dirname(manifest), { recursive: true });
		writeFileSync(manifest, "{}\n");
		git(dir, "add", MANIFEST_RELATIVE);
	}
	if (withReference) {
		const target = path.join(dir, REFERENCE_RELATIVE);
		mkdirSync(path.dirname(target), { recursive: true });
		writeFileSync(target, referenceText());
		git(dir, "add", REFERENCE_RELATIVE);
	}
	if (withManifest || withReference) git(dir, "commit", "-q", "-m", "seed");
	return dir;
}

function stage(dir, relative, content) {
	const target = path.join(dir, relative);
	mkdirSync(path.dirname(target), { recursive: true });
	writeFileSync(target, content);
	git(dir, "add", relative);
}

function runHook(payload) {
	const result = spawnSync(process.execPath, [HOOK], {
		input: JSON.stringify(payload),
		encoding: "utf8",
	});
	return {
		status: result.status,
		stdout: result.stdout,
		stderr: result.stderr,
		body: result.stdout ? JSON.parse(result.stdout) : null,
	};
}

function claudePayload(cwd, command) {
	return { hook_event_name: "PreToolUse", tool_name: "Bash", cwd, tool_input: { command } };
}

/**
 * Builds the canonical `-m "$(cat <<'EOF' … )"` commit form, the form every
 * commit in thrive actually takes.
 */
function heredocCommand(body) {
	return `git commit -m "$(cat <<'EOF'\n${body}\nEOF\n)"`;
}

function denyReason(body) {
	return body.hookSpecificOutput.permissionDecisionReason;
}

function markerPath(repo) {
	return path.join(repo, git(repo, "rev-parse", "--git-path", "commit-cleanup"), git(repo, "write-tree"));
}

describe("gate on a staged tree", () => {
	test("(a) first commit denies with the instruction, (b) the retry passes, (c) a changed tree denies again", () => {
		const repo = makeRepo("tree-key");
		stage(repo, "src/a.ts", "export const a = 1;\n");
		const payload = claudePayload(repo, 'git commit -m "add a"');

		const first = runHook(payload);
		assert.equal(first.status, 0);
		assert.deepEqual(Object.keys(first.body), ["hookSpecificOutput"]);
		assert.equal(first.body.hookSpecificOutput.permissionDecision, "deny");
		assert.equal(first.body.hookSpecificOutput.hookEventName, "PreToolUse");
		assert.ok(denyReason(first.body).startsWith(INSTRUCTION_OPENER));
		assert.ok(denyReason(first.body).includes("§ `Refactor scope`"));

		const second = runHook(payload);
		assert.equal(second.status, 0);
		assert.equal(second.stdout, "");

		stage(repo, "src/a.ts", "export const a = 2;\n");
		const third = runHook(payload);
		assert.equal(third.body.hookSpecificOutput.permissionDecision, "deny");

		const fourth = runHook(payload);
		assert.equal(fourth.stdout, "");
	});

	test("(d) staged paths all under .ai-spec/plans/ pass on the first attempt", () => {
		const repo = makeRepo("plan-only");
		stage(repo, ".ai-spec/plans/thr-0001.md", "# Plan\n");
		const result = runHook(claudePayload(repo, 'git commit -m "plan"'));
		assert.equal(result.status, 0);
		assert.equal(result.stdout, "");
	});

	test("a plan path mixed with a code path gates the whole commit", () => {
		const repo = makeRepo("plan-mixed");
		stage(repo, ".ai-spec/plans/thr-0001.md", "# Plan\n");
		stage(repo, "src/b.ts", "export const b = 1;\n");
		const result = runHook(claudePayload(repo, 'git commit -m "both"'));
		assert.equal(result.body.hookSpecificOutput.permissionDecision, "deny");
	});

	test("nothing staged emits nothing", () => {
		const repo = makeRepo("empty-index");
		const result = runHook(claudePayload(repo, 'git commit -m "nothing"'));
		assert.equal(result.stdout, "");
	});

	test("(i) the same tree in a second worktree denies independently", () => {
		const repo = makeRepo("worktree-main");
		const worktree = path.join(fixtures, "worktree-second");
		git(repo, "worktree", "add", "-q", "-b", "second", worktree);
		const content = "export const shared = 1;\n";
		stage(repo, "src/shared.ts", content);
		stage(worktree, "src/shared.ts", content);
		const payload = 'git commit -m "shared"';

		assert.equal(runHook(claudePayload(repo, payload)).body.hookSpecificOutput.permissionDecision, "deny");
		assert.equal(runHook(claudePayload(repo, payload)).stdout, "");
		assert.equal(runHook(claudePayload(worktree, payload)).body.hookSpecificOutput.permissionDecision, "deny");
		assert.equal(runHook(claudePayload(worktree, payload)).stdout, "");
	});

	test("a missing reference file denies with the embedded instruction, writes the marker, and the retry passes", () => {
		const withFile = makeRepo("with-reference");
		stage(withFile, "src/c.ts", "export const c = 1;\n");
		const fromFile = denyReason(runHook(claudePayload(withFile, 'git commit -m "c"')).body);

		const repo = makeRepo("no-reference", { withReference: false });
		stage(repo, "src/c.ts", "export const c = 1;\n");
		const payload = claudePayload(repo, 'git commit -m "c"');

		const first = runHook(payload);
		assert.equal(first.body.hookSpecificOutput.permissionDecision, "deny");
		assert.ok(denyReason(first.body).startsWith(INSTRUCTION_OPENER));
		assert.equal(denyReason(first.body), fromFile, "embedded text drifted from the reference file");
		assert.ok(!denyReason(first.body).includes(REFERENCE_RELATIVE));
		assert.ok(existsSync(markerPath(repo)), "marker not written");

		const second = runHook(payload);
		assert.equal(second.stdout, "");
	});

	test("a commit body in the canonical HEREDOC form with quotes inside gates and clears normally", () => {
		const repo = makeRepo("heredoc-quoted-body");
		stage(repo, "src/m.ts", "export const m = 1;\n");
		const payload = claudePayload(repo, heredocCommand('T: Reword the "Tests written" bullet'));

		const first = runHook(payload);
		assert.equal(first.body.hookSpecificOutput.permissionDecision, "deny");
		assert.ok(denyReason(first.body).startsWith(INSTRUCTION_OPENER));

		const second = runHook(payload);
		assert.equal(second.stdout, "");
	});

	test("a plan-only commit body in the canonical HEREDOC form with quotes inside is not gated", () => {
		const repo = makeRepo("heredoc-quoted-plan");
		stage(repo, ".ai-spec/plans/thr-0002.md", "# Plan\n");
		const result = runHook(claudePayload(repo, heredocCommand('T: Reword the "Tests written" bullet')));
		assert.equal(result.stdout, "");
	});
});

describe("yield rules", () => {
	test("no manifest above the cwd emits nothing and writes no marker", () => {
		const repo = makeRepo("no-manifest", { withManifest: false });
		stage(repo, "src/n.ts", "export const n = 1;\n");
		const result = runHook(claudePayload(repo, 'git commit -m "n"'));
		assert.equal(result.status, 0);
		assert.equal(result.stdout, "");
		assert.ok(!existsSync(markerPath(repo)));
	});

	test("a repo whose .claude/settings.json registers commit-cleanup gates its own commits", () => {
		const repo = makeRepo("self-registered");
		mkdirSync(path.join(repo, ".claude"), { recursive: true });
		writeFileSync(
			path.join(repo, ".claude/settings.json"),
			JSON.stringify({
				hooks: {
					PreToolUse: [
						{ matcher: "Bash", hooks: [{ type: "command", command: "node scripts/hooks/commit-cleanup/hook.mjs --tool=claude" }] },
					],
				},
			})
		);
		stage(repo, "src/s.ts", "export const s = 1;\n");
		const result = runHook(claudePayload(repo, 'git commit -m "s"'));
		assert.equal(result.stdout, "");
		assert.ok(!existsSync(markerPath(repo)));
		assert.equal(runHook(claudePayload(repo, 'git commit -am "s"')).stdout, "", "the yield covers the form denies too");
	});

	test("an unparseable settings.json still yields on the raw text", () => {
		const repo = makeRepo("self-registered-raw");
		mkdirSync(path.join(repo, ".claude"), { recursive: true });
		writeFileSync(path.join(repo, ".claude/settings.json"), '{ "hooks": { "PreToolUse": [ { "hooks": [ { "command": "commit-cleanup/hook.mjs" }, ] } ] } }');
		stage(repo, "src/r.ts", "export const r = 1;\n");
		assert.equal(runHook(claudePayload(repo, 'git commit -m "r"')).stdout, "");
	});

	test("a settings.json registering other hooks does not yield", () => {
		const repo = makeRepo("other-hooks");
		mkdirSync(path.join(repo, ".claude"), { recursive: true });
		writeFileSync(
			path.join(repo, ".claude/settings.json"),
			JSON.stringify({ hooks: { PreToolUse: [{ matcher: "Bash", hooks: [{ type: "command", command: "guard-worktree-git.sh" }] }] } })
		);
		stage(repo, "src/o.ts", "export const o = 1;\n");
		assert.equal(runHook(claudePayload(repo, 'git commit -m "o"')).body.hookSpecificOutput.permissionDecision, "deny");
	});
});

describe("commit-time staging forms", () => {
	test("(e) git commit -a denies with the stage-first remedy", () => {
		const repo = makeRepo("commit-a");
		const result = runHook(claudePayload(repo, 'git commit -am "all"'));
		assert.equal(result.body.hookSpecificOutput.permissionDecision, "deny");
		const reason = denyReason(result.body);
		assert.ok(reason.includes("git add <paths>"));
		assert.ok(reason.includes("`--all`"));
	});

	test("a same-command git add before the commit denies with a separate-command remedy", () => {
		const repo = makeRepo("add-then-commit");
		stage(repo, "src/staged.ts", "export const staged = 1;\n");
		writeFileSync(path.join(repo, "src/unstaged.ts"), "export const unstaged = 1;\n");

		const combined = runHook(claudePayload(repo, 'git add src/unstaged.ts && git commit -m "both"'));
		assert.equal(combined.body.hookSpecificOutput.permissionDecision, "deny");
		assert.ok(denyReason(combined.body).includes("as its own command"));
		assert.equal(runHook(claudePayload(repo, 'git add src/unstaged.ts && git commit -m "both"')).body.hookSpecificOutput.permissionDecision, "deny", "denied every time, no marker written");

		git(repo, "add", "src/unstaged.ts");
		const separate = runHook(claudePayload(repo, 'git commit -m "both"'));
		assert.ok(denyReason(separate.body).startsWith(INSTRUCTION_OPENER));
		assert.equal(runHook(claudePayload(repo, 'git commit -m "both"')).stdout, "");
	});

	test("a redirect fd on the commit is not read as a pathspec", () => {
		const base = path.resolve("/base");
		assert.equal(describeCommitTimeStaging(findCommitSegment("git commit -q -F m.txt 2>&1", base).args), null);
		assert.equal(describeCommitTimeStaging(findCommitSegment("git commit -m x >out.log", base).args), null);
		assert.equal(describeCommitTimeStaging(findCommitSegment("git commit -m x 1>/tmp/o", base).args), null);
	});

	test("a PowerShell Set-Location moves the target like cd does", () => {
		const base = path.resolve("/base");
		assert.equal(findCommitSegment("Set-Location sub; git commit -m x", base).dir, path.normalize(path.join(base, "sub")));
		assert.equal(findCommitSegment("Push-Location sub; git commit -m x", base).dir, path.normalize(path.join(base, "sub")));
	});

	test("findCommitSegment reports which index-changing subcommand precedes the commit", () => {
		const base = path.resolve("/base");
		assert.equal(findCommitSegment("git add x && git commit -m y", base).indexChangedBy, "add");
		assert.equal(findCommitSegment("git rm x; git commit -m y", base).indexChangedBy, "rm");
		assert.equal(findCommitSegment("git restore --staged x && git commit -m y", base).indexChangedBy, "restore");
		assert.equal(findCommitSegment("git stash pop && git commit -m y", base).indexChangedBy, "stash");
		assert.equal(findCommitSegment("git restore x && git commit -m y", base).indexChangedBy, null);
		assert.equal(findCommitSegment("git status && git commit -m y", base).indexChangedBy, null);
		assert.equal(findCommitSegment("git commit -m y && git add x", base).indexChangedBy, null);
	});

	test("describeCommitTimeStaging names each form and passes a plain index commit", () => {
		assert.equal(describeCommitTimeStaging(["-m", "x"]), null);
		assert.equal(describeCommitTimeStaging(["-m", "-a"]), null);
		assert.equal(describeCommitTimeStaging(["--amend", "--no-edit"]), null);
		assert.equal(describeCommitTimeStaging(["-a", "-m", "x"]), "`--all`");
		assert.equal(describeCommitTimeStaging(["--all"]), "`--all`");
		assert.equal(describeCommitTimeStaging(["-am", "x"]), "`--all`");
		assert.equal(describeCommitTimeStaging(["--include", "f"]), "`--include`");
		assert.equal(describeCommitTimeStaging(["-o", "f"]), "`--only`");
		assert.equal(describeCommitTimeStaging(["-m", "x", "--", "f"]), "a pathspec");
		assert.equal(describeCommitTimeStaging(["-m", "x", "f"]), "a pathspec");
		assert.equal(describeCommitTimeStaging(["--pathspec-from-file", "list.txt", "-m", "x"]), "a pathspec");
		assert.equal(describeCommitTimeStaging(["--pathspec-from-file=list.txt", "-m", "x"]), "a pathspec");
	});

	test("a positional token that can't plausibly be a path degrades to a miss, not a deny", () => {
		assert.equal(describeCommitTimeStaging(["-m", "x", "line one\nline two"]), null);
		assert.equal(describeCommitTimeStaging(["-m", "x", "$(spillage)"]), null);
	});
});

describe("commands that are not an index commit", () => {
	test("(f) a non-git command and git status emit nothing", () => {
		const repo = makeRepo("not-commit");
		stage(repo, "src/d.ts", "export const d = 1;\n");
		assert.equal(runHook(claudePayload(repo, "ls -la")).stdout, "");
		assert.equal(runHook(claudePayload(repo, "git status")).stdout, "");
		assert.equal(runHook(claudePayload(repo, "git log | grep commit")).stdout, "");
	});

	test("(h) an unparseable command exits 0 with no output", () => {
		const repo = makeRepo("unparseable");
		stage(repo, "src/e.ts", "export const e = 1;\n");
		const result = runHook(claudePayload(repo, 'git commit -m "oops'));
		assert.equal(result.status, 0);
		assert.equal(result.stdout, "");
	});

	test("a nested double-quoted string inside a non-heredoc $( ) registers as unbalanced and fails open", () => {
		const repo = makeRepo("nested-quote-in-substitution");
		stage(repo, "src/l.ts", "export const l = 1;\n");
		const result = runHook(claudePayload(repo, 'git commit -m "$(printf "%s" "hi)")"'));
		assert.equal(result.status, 0);
		assert.equal(result.stdout, "");
	});

	test("a non-shell tool emits nothing", () => {
		const repo = makeRepo("fail-open");
		stage(repo, "src/f.ts", "export const f = 1;\n");
		const read = runHook({ tool_name: "Read", cwd: repo, tool_input: { file_path: "x" } });
		assert.equal(read.stdout, "");
	});

	test("malformed JSON exits 0 with one stderr line and no stdout", () => {
		const result = spawnSync(process.execPath, [HOOK], { input: "{not json", encoding: "utf8" });
		assert.equal(result.status, 0);
		assert.equal(result.stdout, "");
		assert.ok(result.stderr.startsWith("commit-cleanup hook:"));
	});

	test("an unexpanded $VAR directory fails open", () => {
		const repo = makeRepo("var-dir");
		stage(repo, "src/g.ts", "export const g = 1;\n");
		assert.equal(runHook(claudePayload(repo, 'git -C $WT commit -m "x"')).stdout, "");
	});
});

describe("target directory resolution", () => {
	test("cd and -C move the commit to the named repo", () => {
		const repo = makeRepo("target");
		stage(repo, "src/h.ts", "export const h = 1;\n");
		const elsewhere = path.join(repo, "elsewhere");
		mkdirSync(elsewhere, { recursive: true });
		const repoInShell = repo.split(path.sep).join("/");

		const viaCd = runHook(claudePayload(elsewhere, `cd ${repoInShell} && git commit -m "x"`));
		assert.equal(viaCd.body.hookSpecificOutput.permissionDecision, "deny");
		const viaC = runHook(claudePayload(elsewhere, `git -C ${repoInShell} commit -m "x"`));
		assert.equal(viaC.stdout, "", "same tree, already marked by the cd form");
	});

	test("a Git Bash drive path resolves on Windows", { skip: process.platform !== "win32" }, () => {
		const repo = makeRepo("drive-path");
		stage(repo, "src/k.ts", "export const k = 1;\n");
		const posixRepo = "/" + repo[0].toLowerCase() + repo.slice(2).split(path.sep).join("/");

		const viaCwd = runHook(claudePayload(posixRepo, 'git commit -m "x"'));
		assert.equal(viaCwd.body.hookSpecificOutput.permissionDecision, "deny");
		assert.equal(runHook(claudePayload(repo, `git -C ${posixRepo} commit -m "x"`)).stdout, "", "same tree via -C, already marked");
		stage(repo, "src/k.ts", "export const k = 2;\n");
		const viaCd = runHook(claudePayload(repo, `cd ${posixRepo} && git commit -m "x"`));
		assert.equal(viaCd.body.hookSpecificOutput.permissionDecision, "deny");
	});

	test("findCommitSegment folds relative cd and -C against the session cwd", () => {
		const base = path.resolve("/base");
		const one = findCommitSegment('cd sub && git commit -m "x"', base);
		assert.equal(one.dir, path.normalize(path.join(base, "sub")));
		const two = findCommitSegment('git -C a -C b commit -m "x"', base);
		assert.equal(two.dir, path.normalize(path.join(base, "a", "b")));
		assert.equal(findCommitSegment("git commit -m x\n", base).dir, base);
		assert.equal(findCommitSegment("git status", base), null);
	});
});

describe("harness envelope", () => {
	test("a PowerShell tool call is gated too", () => {
		const repo = makeRepo("powershell");
		stage(repo, "src/p.ts", "export const p = 1;\n");
		const result = runHook({ hook_event_name: "PreToolUse", tool_name: "PowerShell", cwd: repo, tool_input: { command: 'git commit -m "x"' } });
		assert.equal(result.body.hookSpecificOutput.permissionDecision, "deny");
	});

	test("a Cursor-shaped payload with no tool_name is declined", () => {
		const repo = makeRepo("foreign");
		stage(repo, "src/j.ts", "export const j = 1;\n");
		const result = runHook({ hook_event_name: "beforeShellExecution", cwd: repo, command: 'git commit -m "x"' });
		assert.equal(result.stdout, "");
	});
});

describe("tokenize", () => {
	test("respects quotes, surfaces separators, keeps quoted newlines literal", () => {
		assert.deepEqual(tokenize('git commit -m "merge stuff"'), ["git", "commit", "-m", "merge stuff"]);
		assert.deepEqual(tokenize("git status;git commit"), ["git", "status", ";", "git", "commit"]);
		assert.deepEqual(tokenize("git fetch\n\ngit commit"), ["git", "fetch", "\n\n", "git", "commit"]);
		assert.deepEqual(tokenize('git commit -m "a\nb"'), ["git", "commit", "-m", "a\nb"]);
		assert.deepEqual(tokenize("echo $(git commit)"), ["echo", "$", "(", "git", "commit", ")"]);
		assert.deepEqual(tokenize("FOO=bar git commit"), ["FOO=bar", "git", "commit"]);
		assert.throws(() => tokenize('git commit -m "oops'));
	});

	test("a $( ) command substitution inside double quotes tokenizes as one literal argument", () => {
		assert.deepEqual(tokenize('git commit -m "$(echo hi)"'), ["git", "commit", "-m", "$(echo hi)"]);
	});

	test("a nested double-quoted string inside a non-heredoc $( ) can throw on a well-formed command", () => {
		assert.throws(() => tokenize('git commit -m "$(printf "%s" "hi)")"'));
	});

	test("a heredoc body inside a double-quoted $( ) tokenizes to one argument regardless of quotes in the body", () => {
		for (const body of [
			"no quotes here",
			'one "quoted" pair',
			'two "quoted" and "quoted again" pairs',
			'a single stray " quote',
		]) {
			const toks = tokenize(heredocCommand(body));
			assert.equal(toks.length, 4, body);
			assert.equal(describeCommitTimeStaging(toks.slice(2)), null, body);
		}
	});

	test("an escaped quote in a --trailer value still tokenizes as one argument", () => {
		assert.deepEqual(tokenize('git commit --trailer "a \\"quoted\\" value" -m x'), [
			"git",
			"commit",
			"--trailer",
			'a "quoted" value',
			"-m",
			"x",
		]);
	});
});
