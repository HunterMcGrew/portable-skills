#!/usr/bin/env node
/**
 * Commit-cleanup gate. Denies the first `git commit` of each distinct staged
 * tree and hands the agent the cleanup instruction from
 * `.ai-spec/references/commit-cleanup.md` — or the same paragraph embedded
 * below when the checkout lacks that file; the same tree passes on the next
 * attempt. Runs as a Claude Code PreToolUse hook for Bash.
 *
 * Yields silently when: no `.ai-spec/architect/manifest.json` sits above the
 * payload cwd; the target repo's `.claude/settings.json` registers a hook
 * whose command names `commit-cleanup`, since the repo then gates its own
 * commits; the command holds no `git commit`; or the staged tree's marker
 * already exists.
 *
 * The re-try key is the staged tree hash from `git write-tree`, so a retry
 * with the same index passes and a cleanup that changes the index gates once
 * more. Markers live at `<git rev-parse --git-path commit-cleanup>/<hash>`,
 * which is per-worktree, so two worktrees of one repo key independently and
 * nothing outside git has to clean the markers up.
 *
 * Only index commits are gated. `-a`, `--all`, `-i`/`--include`,
 * `-o`/`--only`, and any pathspec stage at commit time, so the index hash does
 * not describe what would land; those forms are denied with a stage-first
 * remedy. So is a commit preceded in the same command by an index-changing
 * segment (`git add x && git commit`): the hook runs before the `add`, so the
 * tree it hashes is not the tree that lands. A commit whose staged paths all
 * sit under `.ai-spec/plans/` is a record rather than code and passes
 * untouched.
 *
 * Commands are tokenized with a shlex-style walk (quotes respected,
 * separators surfaced as their own tokens, a newline inside quotes stays
 * literal). Inside a double-quoted region, a `$( … )` command substitution is
 * walked to its matching close (nested parens depth-counted) and any heredoc
 * body inside it is consumed as literal text through its terminator line, so
 * the canonical `-m "$(cat <<'EOF' … EOF )"` commit form always yields one
 * argument regardless of quotes in the body. The target directory is the
 * payload cwd (Windows-native, `D:\...`, on a Windows host) moved by any
 * same-command `cd`, with each `-C` folded on top the way git itself folds
 * repeated `-C`. A `-C` or `cd` argument written as a Git Bash drive path
 * (`/d/...`) is mapped to `D:/...` on win32 before any git call, since
 * git.exe cannot open the former.
 *
 * Fail open, always: every path exits 0, and a deny travels in the harness
 * envelope rather than an exit code. Known gaps: a `$VAR` in a `-C` or `cd`
 * path can't be resolved statically and fails open; a commit inside a
 * `docker exec` string is invisible; `--amend` is gated like any other commit
 * (its tree is whatever `write-tree` reports); a nested double-quoted string
 * inside a non-heredoc `$( … )` substitution can make a well-formed commit
 * register as unbalanced and fail open — the canonical heredoc form is
 * unaffected; a PowerShell command is tokenized with the same POSIX rules,
 * which hold for a `git commit` line and are not a PowerShell parser. An
 * index change by a git subcommand outside the set `changesIndex` counts —
 * `git checkout HEAD --`, `git apply --cached`, `git update-index`,
 * `git cherry-pick -n`, `git merge --no-commit` — is not seen, so a commit
 * after one in the same command is keyed on the pre-command tree.
 *
 * Wire shape (Claude Code, https://code.claude.com/docs/en/hooks):
 *   PreToolUse; tool_name "Bash"; tool_input.command; cwd; deny via
 *   hookSpecificOutput { hookEventName, permissionDecision, permissionDecisionReason }
 */
import { execFileSync } from "node:child_process";
import { existsSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const REFERENCE_RELATIVE = ".ai-spec/references/commit-cleanup.md";
const PLANS_PREFIX = ".ai-spec/plans/";
const MANIFEST_RELATIVE = ".ai-spec/architect/manifest.json";
const SETTINGS_RELATIVE = ".claude/settings.json";

/**
 * The instruction paragraph from `.ai-spec/references/commit-cleanup.md`,
 * handed back when the checkout has no copy of that file.
 */
const EMBEDDED_INSTRUCTION =
	"Before this commit lands, review the staged diff (`git diff --cached`) for readability, reusability, and maintainability. Stay inside the local frame from `.ai-spec/rules/code-standards.md` § `Refactor scope` — the changed lines, their containing functions, helpers you extract from them, files already in the diff. Apply `.ai-spec/rules/code-comments.md` § `Review` to every comment on a changed line. Fix what you find, re-stage, and run the same commit again. Name anything outside the frame in one line to the user and leave it there.";

const HARNESS = {
	isShellCall: (payload) =>
		payload.tool_name === "Bash" || payload.tool_name === "PowerShell",
	command: (payload) => payload.tool_input?.command,
	cwd: (payload) => payload.cwd,
	emitDeny: (text) => ({
		hookSpecificOutput: {
			hookEventName: "PreToolUse",
			permissionDecision: "deny",
			permissionDecisionReason: text,
		},
	}),
};

function main(stdin) {
	const payload = JSON.parse(stdin);
	if (!HARNESS.isShellCall(payload)) return;

	const command = HARNESS.command(payload);
	if (typeof command !== "string" || !command.trim()) return;

	const cwd = HARNESS.cwd(payload) || process.cwd();
	if (!findManifestRoot(cwd)) return;

	const commit = findCommitSegment(command, cwd);
	if (!commit) return;

	const topLevel = commit.dir ? runGit(commit.dir, ["rev-parse", "--show-toplevel"]) : null;
	if (topLevel && repoRegistersCommitCleanup(topLevel)) return;

	const commitTimeForm = describeCommitTimeStaging(commit.args);
	if (commitTimeForm) {
		writeStdout(HARNESS.emitDeny(buildStageFirstRemedy(commitTimeForm)));
		return;
	}
	if (commit.indexChangedBy) {
		writeStdout(HARNESS.emitDeny(buildSeparateCommandRemedy(commit.indexChangedBy)));
		return;
	}

	if (!commit.dir) return;

	const treeHash = runGit(commit.dir, ["write-tree"]);
	if (!treeHash) return;

	const stagedPaths = runGit(commit.dir, ["diff", "--cached", "--name-only"]);
	if (stagedPaths === null) return;
	const paths = stagedPaths.split("\n").filter(Boolean);
	if (paths.every((p) => p.startsWith(PLANS_PREFIX))) return;

	const markerDir = runGit(commit.dir, ["rev-parse", "--git-path", "commit-cleanup"]);
	if (!markerDir) return;
	const marker = path.join(path.resolve(commit.dir, markerDir), treeHash);
	if (existsSync(marker)) return;

	const instruction = readInstruction(topLevel);

	mkdirSync(path.dirname(marker), { recursive: true });
	writeFileSync(marker, "");
	writeStdout(HARNESS.emitDeny(instruction));
}

/**
 * Walks up from startDir looking for `.ai-spec/architect/manifest.json`,
 * returning the directory that carries it or null if the filesystem root is
 * reached with no match.
 */
function findManifestRoot(startDir) {
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

/**
 * True when the repo's own `.claude/settings.json` registers a hook whose
 * command names `commit-cleanup`. Any event and any matcher count, since the
 * point is only whether the repo gates its own commits. Unparseable JSON
 * falls back to a raw-text search so a trailing comma can't silently turn
 * this overlay back on.
 */
function repoRegistersCommitCleanup(topLevel) {
	const settingsPath = path.join(topLevel, SETTINGS_RELATIVE);
	if (!existsSync(settingsPath)) return false;
	const raw = readFileSync(settingsPath, "utf8");
	let settings;
	try {
		settings = JSON.parse(raw);
	} catch {
		return raw.includes("commit-cleanup");
	}
	const events = settings && typeof settings.hooks === "object" ? settings.hooks : {};
	return Object.values(events).some(
		(entries) =>
			Array.isArray(entries) &&
			entries.some(
				(entry) =>
					Array.isArray(entry?.hooks) &&
					entry.hooks.some(
						(hook) => typeof hook?.command === "string" && hook.command.includes("commit-cleanup")
					)
			)
	);
}

/**
 * Runs one git command in `dir` and returns trimmed stdout, or null on any
 * failure — a non-repo, an unmerged index, a missing binary. Callers treat
 * null as "emit nothing", which is the fail-open contract.
 */
function runGit(dir, args) {
	try {
		return execFileSync("git", ["-C", dir, ...args], {
			encoding: "utf8",
			stdio: ["ignore", "pipe", "ignore"],
			timeout: 5000,
		}).trim();
	} catch {
		return null;
	}
}

/**
 * Reads the instruction paragraph from the reference file: everything between
 * the H1 and the first `## ` heading. Falls back to the embedded copy when
 * the checkout has no reference file or the file yields no paragraph.
 */
function readInstruction(topLevel) {
	const referencePath = topLevel ? path.join(topLevel, REFERENCE_RELATIVE) : null;
	if (!referencePath || !existsSync(referencePath)) return EMBEDDED_INSTRUCTION;

	const body = [];
	let pastTitle = false;
	for (const line of readFileSync(referencePath, "utf8").split("\n")) {
		if (!pastTitle) {
			if (line.startsWith("# ")) pastTitle = true;
			continue;
		}
		if (line.startsWith("## ")) break;
		body.push(line);
	}
	return body.join("\n").trim() || EMBEDDED_INSTRUCTION;
}

function buildStageFirstRemedy(form) {
	return `commit-cleanup gate: ${form} stages files at commit time, so the staged tree can't be reviewed before it lands. Stage first, then commit from the index:\n\n    git add <paths>\n    git commit -m "<message>"\n\nSee .ai-spec/rules/worktree-git.md § Name the target for staging, too.`;
}

function buildSeparateCommandRemedy(subcommand) {
	return `commit-cleanup gate: \`git ${subcommand}\` changes the index in the same command as the commit, so the tree this gate reviewed is not the tree that would land. Run the staging step as its own command, then commit:\n\n    git ${subcommand} ...\n    git commit -m "<message>"`;
}

// --- Commit-form detection ---

const COMMIT_OPTS_WITH_ARG = new Set([
	"-m",
	"--message",
	"-F",
	"--file",
	"-C",
	"--reuse-message",
	"-c",
	"--reedit-message",
	"--fixup",
	"--squash",
	"--author",
	"--date",
	"-t",
	"--template",
	"--cleanup",
	"--trailer",
]);

/**
 * Returns the commit-time-staging form the args use, or null for a plain
 * index commit. `-a` and `-i`/`-o` are recognized inside a short-flag cluster
 * (`-am`), and a positional token is a pathspec with or without a `--` before
 * it — git reads both the same way. A positional token that could not
 * plausibly be a path — an embedded newline, or a leading `$(` — is a
 * tokenizer gap rather than a real pathspec and is skipped, per
 * `.ai-spec/architect/agent-hooks.md` § `Nag versus deny`: an uncertain parse
 * falls toward the miss, not the block.
 */
export function describeCommitTimeStaging(args) {
	for (let i = 0; i < args.length; i += 1) {
		const arg = args[i];
		if (arg === "--") return "a pathspec";
		// git reads the file named by --pathspec-from-file as the pathspec, so
		// this stages at commit time exactly as a positional path does.
		if (arg === "--pathspec-from-file" || arg.startsWith("--pathspec-from-file="))
			return "a pathspec";
		if (arg === "-a" || arg === "--all") return "`--all`";
		if (arg === "-i" || arg === "--include") return "`--include`";
		if (arg === "-o" || arg === "--only") return "`--only`";
		if (COMMIT_OPTS_WITH_ARG.has(arg)) {
			i += 1;
			continue;
		}
		if (/^-[a-zA-Z]+$/.test(arg)) {
			if (arg.includes("a")) return "`--all`";
			if (arg.includes("i")) return "`--include`";
			if (arg.includes("o")) return "`--only`";
			// A value-taking flag at the end of a cluster (`-sm`) consumes the next token.
			if (/[mFCct]$/.test(arg)) i += 1;
			continue;
		}
		if (arg.startsWith("-")) continue;
		if (looksLikePathspec(arg)) return "a pathspec";
	}
	return null;
}

/**
 * True when `token` could plausibly be a path: no embedded newline and no
 * leading `$(`. Neither is something an agent would type as a pathspec
 * argument, so failing this test means the token is spillage from a
 * tokenizer gap.
 */
function looksLikePathspec(token) {
	return !token.includes("\n") && !token.startsWith("$(");
}

// --- Command tokenizing and the segment walk ---

const SEPARATOR_CHARS = new Set([";", "&", "|", "(", ")", "<", ">", "\n", "\r"]);
// Bash `cd` and its PowerShell equivalents, so `Set-Location <repo>; git commit`
// moves the target the same way `cd <repo> && …` does. Only the bare
// `<cmd> <dir>` form is followed; a `-Path` flag form is an accepted miss.
const DIR_CHANGE_COMMANDS = new Set(["cd", "Set-Location", "Push-Location", "sl"]);
const GLOBAL_OPTS_WITH_ARG = new Set([
	"-C",
	"-c",
	"--git-dir",
	"--work-tree",
	"--namespace",
	"--exec-path",
	"--super-prefix",
	"--config-env",
]);

/**
 * Finds the first `git commit` segment in a command string and returns its
 * args, the directory it would run in, and the name of any earlier
 * index-changing git subcommand in the same command, or null when there is
 * no commit. `dir` is null when a `cd` or `-C` path can't be resolved
 * statically.
 */
export function findCommitSegment(command, sessionCwd) {
	let tokens;
	try {
		tokens = tokenize(command);
	} catch {
		return null;
	}

	let effectiveCwd = toHostPath(sessionCwd);
	let indexChangedBy = null;
	let segment = [];
	for (const tok of [...tokens, ";"]) {
		if (!isSeparator(tok)) {
			segment.push(tok);
			continue;
		}
		// A redirect separator (`>`, `2>&1`, `<`) carries a leading file
		// descriptor glued to the end of the segment (`git commit … 2>&1` →
		// `["git","commit",…,"2"]`). That digit is not a pathspec; drop it so a
		// stderr redirect on a commit isn't read as commit-time staging.
		if (/[<>]/.test(tok) && segment.length > 0 && /^\d+$/.test(segment[segment.length - 1])) {
			segment.pop();
		}
		if (segment.length > 0) {
			if (DIR_CHANGE_COMMANDS.has(segment[0]) && segment.length > 1) {
				effectiveCwd = resolveDir(segment[1], effectiveCwd);
			} else {
				const parsed = parseGitSegment(segment);
				if (parsed && parsed.sub === "commit") {
					let dir = effectiveCwd;
					for (const p of parsed.cPaths) dir = resolveDir(p, dir);
					return { args: parsed.args, dir, indexChangedBy };
				}
				if (parsed && changesIndex(parsed.sub, parsed.args)) {
					indexChangedBy = parsed.sub;
				}
			}
		}
		segment = [];
	}
	return null;
}

const INDEX_SUBCOMMANDS = new Set(["add", "rm", "mv", "reset"]);

/**
 * True for a git subcommand that changes the index: the four that always do,
 * `restore --staged`, and `stash pop`/`apply`. A plain `restore` touches only
 * the worktree and leaves the staged tree as it was.
 */
function changesIndex(sub, args) {
	if (INDEX_SUBCOMMANDS.has(sub)) return true;
	if (sub === "restore") return args.some((a) => a === "--staged" || a === "-S");
	if (sub === "stash") return args[0] === "pop" || args[0] === "apply";
	return false;
}

/**
 * Maps a Git Bash drive path (`/d/x`) to the form git.exe reads (`D:/x`) on
 * Windows. Everywhere else, and for every other shape, the path is returned
 * untouched.
 */
function toHostPath(p) {
	if (process.platform !== "win32" || typeof p !== "string") return p;
	const drive = /^\/([a-zA-Z])(\/|$)/.exec(p);
	return drive ? `${drive[1].toUpperCase()}:/${p.slice(drive[0].length)}` : p;
}

function isSeparator(tok) {
	return tok.length > 0 && [...tok].every((c) => SEPARATOR_CHARS.has(c));
}

/**
 * Walks leading VAR=val assignments, the `git` token, then git's global
 * options to reach the subcommand. `cPaths` collects every `-C` argument in
 * order, since git folds repeated `-C` cumulatively.
 */
function parseGitSegment(seg) {
	let i = 0;
	while (i < seg.length && seg[i].includes("=") && !seg[i].startsWith("-")) i += 1;
	if (seg[i] !== "git") return null;

	i += 1;
	const cPaths = [];
	while (i < seg.length) {
		const t = seg[i];
		if (t === "-C") {
			if (i + 1 < seg.length) cPaths.push(seg[i + 1]);
			i += 2;
			continue;
		}
		if (GLOBAL_OPTS_WITH_ARG.has(t)) {
			i += 2;
			continue;
		}
		if (t.startsWith("-")) {
			i += 1;
			continue;
		}
		break;
	}
	return { cPaths, sub: seg[i] ?? null, args: seg.slice(i + 1) };
}

/**
 * Resolves `p` the way the shell would, against the effective working
 * directory at that point in the command. Null when it can't be known
 * statically — an unexpanded `$VAR`, or a relative path with no base.
 */
function resolveDir(p, base) {
	if (!p || p.includes("$")) return null;
	p = toHostPath(p);
	if (path.isAbsolute(p)) return path.normalize(p);
	if (!base) return null;
	return path.normalize(path.join(base, p));
}

/**
 * A shlex-style tokenizer in POSIX mode: single quotes are literal, double
 * quotes honor backslash escapes and consume a nested `$( … )` — heredoc
 * bodies included — as literal text, a bare backslash escapes the next
 * character, runs of separator characters surface as one token, and a
 * newline outside quotes is a separator rather than whitespace. Throws on an
 * unbalanced quote.
 */
export function tokenize(command) {
	const tokens = [];
	let word = "";
	let inWord = false;
	let i = 0;

	const flush = () => {
		if (inWord) tokens.push(word);
		word = "";
		inWord = false;
	};

	while (i < command.length) {
		const c = command[i];
		if (c === "'") {
			const close = command.indexOf("'", i + 1);
			if (close === -1) throw new Error("unbalanced single quote");
			word += command.slice(i + 1, close);
			inWord = true;
			i = close + 1;
			continue;
		}
		if (c === '"') {
			i += 1;
			let closed = false;
			while (i < command.length) {
				const d = command[i];
				if (d === "\\" && i + 1 < command.length && '"\\$`\n'.includes(command[i + 1])) {
					word += command[i + 1];
					i += 2;
					continue;
				}
				if (d === "$" && command[i + 1] === "(") {
					const sub = consumeCommandSubstitution(command, i);
					word += sub.text;
					i = sub.end;
					continue;
				}
				if (d === '"') {
					closed = true;
					i += 1;
					break;
				}
				word += d;
				i += 1;
			}
			if (!closed) throw new Error("unbalanced double quote");
			inWord = true;
			continue;
		}
		if (c === "\\") {
			if (i + 1 < command.length) {
				word += command[i + 1];
				inWord = true;
			}
			i += 2;
			continue;
		}
		if (c === " " || c === "\t") {
			flush();
			i += 1;
			continue;
		}
		if (SEPARATOR_CHARS.has(c)) {
			flush();
			let run = "";
			while (i < command.length && SEPARATOR_CHARS.has(command[i])) {
				run += command[i];
				i += 1;
			}
			tokens.push(run);
			continue;
		}
		word += c;
		inWord = true;
		i += 1;
	}
	flush();
	return tokens;
}

/**
 * Consumes a `$( … )` command substitution nested inside a double-quoted
 * region, starting at the `$` of `command[start]`. Nested parens are
 * depth-counted so a subshell inside the substitution doesn't close it
 * early, and any heredoc body inside it is consumed whole via
 * `matchHeredocStart` rather than scanned character by character — a `"` or
 * `(` inside that body plays no part in either count. Returns the consumed
 * text, closing `)` included, and the index just past it.
 */
function consumeCommandSubstitution(command, start) {
	let i = start + 2; // past "$("
	let depth = 1;
	let text = "$(";
	while (i < command.length) {
		const heredocEnd = matchHeredocStart(command, i);
		if (heredocEnd !== null) {
			text += command.slice(i, heredocEnd);
			i = heredocEnd;
			continue;
		}
		const c = command[i];
		text += c;
		i += 1;
		if (c === "(") depth += 1;
		else if (c === ")") {
			depth -= 1;
			if (depth === 0) return { text, end: i };
		}
	}
	throw new Error("unbalanced $( ) inside a double-quoted region");
}

/**
 * Recognizes a heredoc redirect (`<<DELIM`, `<<'DELIM'`, `<<-DELIM`)
 * starting at `command[i]` and returns the index just past its terminator
 * line, or null when `i` isn't a heredoc start or the terminator line is
 * never reached. The delimiter can be quoted or bare; `<<-` allows the
 * terminator line to carry leading tabs.
 */
function matchHeredocStart(command, i) {
	if (command[i] !== "<" || command[i + 1] !== "<") return null;
	let j = i + 2;
	const dashed = command[j] === "-";
	if (dashed) j += 1;
	while (command[j] === " " || command[j] === "\t") j += 1;

	let delimiter;
	if (command[j] === "'" || command[j] === '"') {
		const quote = command[j];
		const close = command.indexOf(quote, j + 1);
		if (close === -1) return null;
		delimiter = command.slice(j + 1, close);
		j = close + 1;
	} else {
		const word = /^[^\s()<>|&;]+/.exec(command.slice(j));
		if (!word) return null;
		delimiter = word[0];
		j += word[0].length;
	}

	const lineEnd = command.indexOf("\n", j);
	if (lineEnd === -1) return null;

	let pos = lineEnd + 1;
	while (pos <= command.length) {
		const nextNewline = command.indexOf("\n", pos);
		const rawLine = command.slice(pos, nextNewline === -1 ? command.length : nextNewline);
		const line = dashed ? rawLine.replace(/^\t+/, "") : rawLine;
		if (line === delimiter) return nextNewline === -1 ? command.length : nextNewline + 1;
		if (nextNewline === -1) return null;
		pos = nextNewline + 1;
	}
	return null;
}

function writeStdout(body) {
	// A reader that stops early raises EPIPE as a stream event, not a throw,
	// so it needs its own listener to keep the fail-open guarantee real.
	process.stdout.on("error", () => {});
	process.stdout.write(JSON.stringify(body));
}

// The module-level guard lets the test suite import the parsers without
// running the gate against its own stdin.
if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
	try {
		main(readFileSync(0, "utf8"));
	} catch (err) {
		try {
			process.stderr.write(`commit-cleanup hook: ${err && err.message ? err.message : err}\n`);
		} catch {
			// stderr itself failing leaves nothing more to do
		}
	}
}
// Deliberately no process.exit(): exit() doesn't wait for a pending stdout
// write to flush, and every throwing path above is already caught, so
// falling off the end exits 0 with the payload drained.
