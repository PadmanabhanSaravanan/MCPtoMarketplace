# **Plugins**

A **plugin** is a self-contained directory that bundles Skills, agents, hooks, and MCP servers into one installable unit. Where the previous modules configured each extension point separately in `.claude/`, a plugin packages them together so a whole team installs the same setup with one command.

---

## Where Plugins Fit

Everything the course has built so far becomes a plugin component.

| Module | Built | As a plugin component |
| --- | --- | --- |
| [07-skills](../07-skills/) → [12-containerization](../12-containerization/README.md) | Skills in `.claude/skills/` | `skills/` |
| [16-subagents](../16-subagents/README.md) | Agents in `.claude/agents/` | `agents/` |
| [17-hooks](../17-hooks/README.md) | Hooks in `.claude/settings.json` | `hooks/hooks.json` |
| [14-figmamcpserver](../14-figmamcpserver/) | MCP servers | `.mcp.json` |

| | Project config (`.claude/`) | Plugin |
| --- | --- | --- |
| **Scope** | One repository | Any project that installs it |
| **Distribution** | Copy files between repos | `claude plugin install` |
| **Versioning** | Git history of that repo | Semantic version in the manifest |
| **Namespacing** | Bare names | `plugin-name:component-name` |
| **Updates** | Manual copy | `claude plugin update` |

Build a plugin when the same setup should follow people across projects.

---

## Step 1: Understand the Directory Structure

Only `.claude-plugin/plugin.json` lives in the metadata directory. **Every other directory sits at the plugin root.**

```
todo-toolkit/
├── .claude-plugin/
│   └── plugin.json          # manifest — the ONLY file in here
├── skills/
│   └── api-contract-check/
│       └── SKILL.md
├── agents/
│   └── test-runner.md
├── hooks/
│   └── hooks.json
├── scripts/
│   └── protect-files.sh
├── commands/                # flat .md skills (legacy; prefer skills/)
├── .mcp.json                # MCP servers
├── .lsp.json                # language servers
└── bin/                     # executables added to the Bash PATH
```

> The most common mistake is putting `skills/` or `agents/` **inside** `.claude-plugin/`. They must be at the root.

### Default locations

| Component | Location |
| --- | --- |
| Manifest | `.claude-plugin/plugin.json` |
| Skills | `skills/<name>/SKILL.md` |
| Commands | `commands/*.md` |
| Agents | `agents/*.md` |
| Hooks | `hooks/hooks.json` |
| MCP servers | `.mcp.json` |
| LSP servers | `.lsp.json` |
| Executables | `bin/` |

Components in these locations are discovered automatically — the manifest only needs to list *custom* paths.

---

## Step 2: Write the Manifest

The manifest is **optional**. Without it, Claude Code discovers components in the default locations and derives the name from the directory. Add one when you want metadata or custom paths.

If you include a manifest, **`name` is the only required field.**

**[todo-toolkit/.claude-plugin/plugin.json](todo-toolkit/.claude-plugin/plugin.json)**

```json
{
  "$schema": "https://json.schemastore.org/claude-code-plugin-manifest.json",
  "name": "todo-toolkit",
  "displayName": "To-Do Toolkit",
  "version": "1.0.0",
  "description": "Skills, agents, and hooks for the full-stack To-Do application built in this course.",
  "author": {
    "name": "Course Team"
  },
  "license": "MIT",
  "keywords": ["todo", "fullstack", "testing", "course"]
}
```

### Metadata fields

| Field | Type | Notes |
| --- | --- | --- |
| `name` | string | **Required.** kebab-case, no spaces. Used for namespacing |
| `displayName` | string | Human-readable name in the `/plugin` picker |
| `version` | string | Semantic version. Setting it means users update only when you bump it |
| `description` | string | Shown during discovery |
| `author` | object | `{ name, email, url }` |
| `homepage`, `repository`, `license`, `keywords` | | Discovery metadata |
| `defaultEnabled` | boolean | `false` ships the plugin installed but off |
| `metadata` | object | Free-form; Claude Code never reads it |

### Component path fields

Use these only to add or override paths: `skills`, `commands`, `agents`, `workflows`, `hooks`, `mcpServers`, `outputStyles`, `lspServers`, plus `experimental.themes` and `experimental.monitors`.

Note the difference: `skills` **adds to** the default `skills/` scan, while `commands`, `agents`, and the rest **replace** their defaults.

> Unrecognized top-level fields are ignored, so one manifest can double as a `package.json` or VS Code manifest. `claude plugin validate` reports them as warnings.

---

## Step 3: Add Components

The example plugin bundles one of each. All three are copied from earlier modules, unchanged except for namespacing.

### Skill — `skills/api-contract-check/SKILL.md`

Same format as every Skill in this course. Invoked as `/todo-toolkit:api-contract-check`.

````markdown
---
name: api-contract-check
description: Use this skill whenever the OpenAPI contract needs to be checked against the backend routes and the frontend service layer for drift.
---

# API Contract Check Skill

You are an API contract analyst for a Node.js + Express + React application.

## Objective

Find drift between the API contract and the code that is supposed to implement and consume it.

## Steps

1. Locate `openapi.yaml` and the backend route definitions.
2. Map every documented endpoint to its implementation.
3. Cross-check the frontend service layer against both.

## Report

| Category | What to look for |
|----------|------------------|
| Missing implementation | Documented in the contract, absent from the routes |
| Undocumented endpoint | Implemented in the routes, absent from the contract |
| Field mismatch | Request/response shapes differ between contract and code |
| Broken frontend call | Frontend targets an endpoint that does not exist |
| Status code drift | Implementation returns codes the contract does not declare |

Cite file paths and line numbers for every finding.

Report findings only — do not modify files unless explicitly asked.
````

### Agent — `agents/test-runner.md`

The subagent from [16-subagents](../16-subagents/README.md). Appears in the `@` typeahead as `todo-toolkit:test-runner`.

> Plugin agents support `name`, `description`, `model`, `effort`, `maxTurns`, `tools`, `disallowedTools`, `skills`, `memory`, `background`, and `isolation`. For security, **`hooks`, `mcpServers`, and `permissionMode` are ignored** in plugin agents.

### Hook — `hooks/hooks.json`

The protected-files hook from [17-hooks](../17-hooks/README.md), pointing at a bundled script:

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Edit|Write",
        "hooks": [
          {
            "type": "command",
            "command": "\"${CLAUDE_PLUGIN_ROOT}\"/scripts/protect-files.sh",
            "statusMessage": "Checking protected files..."
          }
        ]
      }
    ]
  }
}
```

---

## Step 4: Reference Bundled Files Correctly

A plugin is **copied into a cache** on install, so relative paths and anything outside the plugin directory break. Use the provided variables.

| Variable | Resolves to | Use for |
| --- | --- | --- |
| `${CLAUDE_PLUGIN_ROOT}` | The plugin's install directory | Bundled scripts, binaries, configs |
| `${CLAUDE_PLUGIN_DATA}` | Persistent directory surviving updates | `node_modules`, caches, generated files |
| `${CLAUDE_PROJECT_DIR}` | The project root | Project-local files |

Two rules that follow from caching:

* **No path traversal.** `../shared-utils` will not work — those files are never copied.
* **`${CLAUDE_PLUGIN_ROOT}` changes on update.** Never write state there; use `${CLAUDE_PLUGIN_DATA}`.

In shell-form hook commands, wrap the variable in quotes: `"${CLAUDE_PLUGIN_ROOT}"/scripts/run.sh`.

---

## Step 5: Validate

Run the official validator before sharing anything:

```bash
claude plugin validate ./todo-toolkit --strict
```

`--strict` promotes warnings to errors — use it in CI to catch typos and leftover fields.

Both manifests in this module pass:

```
Validating plugin manifest: .../todo-toolkit/.claude-plugin/plugin.json
✔ Validation passed
```

---

## Step 6: Distribute via a Marketplace

A **marketplace** is a catalog listing one or more plugins. The catalog lives at `.claude-plugin/marketplace.json` in the repository root — note this is a *different* `.claude-plugin/` from the plugin's own.

```
18-plugins/                          # marketplace root
├── .claude-plugin/
│   └── marketplace.json             # the catalog
└── todo-toolkit/                    # a plugin in the catalog
    └── .claude-plugin/
        └── plugin.json
```

**[.claude-plugin/marketplace.json](.claude-plugin/marketplace.json)**

```json
{
  "name": "course-plugins",
  "description": "Plugins built during the Claude Code course, packaging the Skills, agents, and hooks from earlier modules.",
  "owner": {
    "name": "Course Team"
  },
  "plugins": [
    {
      "name": "todo-toolkit",
      "source": "./todo-toolkit",
      "description": "Skills, agents, and hooks for the full-stack To-Do application built in this course."
    }
  ]
}
```

`source` accepts a relative path (as here), or a `github`, `git`, `url`, `archive`, or `npm` source for hosted plugins.

### Install from it — commands

From the directory containing `18-plugins`:

```
/plugin marketplace add ./18-plugins
/plugin install todo-toolkit@course-plugins
```

The path is relative to the session's working directory. If Claude Code is open at the repository root, use `./02_ClaudeCode/18-plugins`.

If the install summary says `Run /reload-plugins to activate.`, run that.

### Install from it — interactive picker

The same flow without typing plugin names. Works identically in the terminal and the VS Code extension — `/plugin` is a Claude Code command typed in the chat input, not a VS Code command-palette entry.

**1. Open the picker.** Type `/plugin` with no arguments and press Enter.

**2. Add the marketplace.** Choose **Manage marketplaces** → **Add marketplace**, then give it the directory that *contains* `.claude-plugin/marketplace.json`:

```
d:\01_LMS_Course_Content\ClaudeCode\claude\02_ClaudeCode\18-plugins
```

Point at the marketplace root — not `.claude-plugin/` itself, and not the repository root. An absolute path avoids the working-directory ambiguity above. The catalog registers under its manifest `name`, `course-plugins`.

**3. Install the plugin.** Back in the main picker, choose **Browse plugins**. `todo-toolkit` is listed under `course-plugins` with the `description` from its manifest. Select it and pick a scope:

| Scope | Effect |
| --- | --- |
| `user` | Every project on this machine |
| `project` | Written to `.claude/settings.json` and committed — teammates get it on pull |
| `local` | This machine and project only, not committed |

**4. Reload.** Choose **Reload plugins** from the picker, or run `/reload-plugins`. Starting a new session also works.

**5. Verify.** Reopen `/plugin` — `todo-toolkit` shows as enabled with its component counts. Then check the typeaheads: `/` lists `todo-toolkit:api-contract-check`, `@` lists `todo-toolkit:test-runner`.

> If `/plugin` reports `isn't available in this environment`, the session is non-interactive. Plugin management is disabled there for both the command and the picker — reopen Claude Code in an interactive session.

### Use the components

```
/todo-toolkit:api-contract-check
@todo-toolkit:test-runner
```

The hook needs no invocation — it fires on every `Edit` or `Write`.

---

## Step 7: Scaffold Your Own

`claude plugin init` generates a working skeleton:

```bash
claude plugin init my-helper
claude plugin init my-helper --with skills agents hooks mcp
```

`--with` accepts `skills`, `agents`, `hooks`, `mcp`, `lsp`, `output-style`, and `channel`. The plugin lands in `~/.claude/skills/<name>/` and loads on the next session as `<name>@skills-dir` — no install step.

---

## CLI Reference

| Command | Purpose |
| --- | --- |
| `claude plugin init <name>` | Scaffold a new plugin |
| `claude plugin validate <path>` | Validate a manifest (`--strict` for CI) |
| `claude plugin install <plugin>` | Install from a marketplace (`-s user\|project\|local`) |
| `claude plugin uninstall <plugin>` | Remove it (`--keep-data` preserves the data dir) |
| `claude plugin enable` / `disable` | Toggle without uninstalling |
| `claude plugin update <plugin>` | Update to the latest version |
| `claude plugin list` | List installed plugins |
| `claude plugin details <plugin>` | Show components and paths |

Interactively, `/plugin` opens the picker and `/reload-plugins` reloads after changes.

---

## Versioning

The version is the cache key that decides whether an update is available. It resolves from the first of:

1. `version` in `plugin.json`
2. `version` in the marketplace entry
3. The git commit SHA of the source
4. The SHA-256 digest, for archive sources
5. `unknown`

| Approach | How | Best for |
| --- | --- | --- |
| **Explicit version** | Set `version` in `plugin.json` | Published plugins with release cycles |
| **Commit SHA** | Omit `version` everywhere | Internal plugins under active development |
| **Digest** | Archive source, no `version` | Plugins published as zip files |

With explicit versions, follow semver and keep a `CHANGELOG.md`.

---

## Troubleshooting

| Symptom | Likely cause |
| --- | --- |
| Components not found | `skills/` or `agents/` placed inside `.claude-plugin/` instead of the root |
| Script not found at runtime | Relative path instead of `${CLAUDE_PLUGIN_ROOT}` |
| `../shared` path fails | Path traversal — files outside the plugin aren't copied to the cache |
| Plugin won't load | A recognized field has the wrong type — run `claude plugin validate` |
| Update does nothing | `version` in `plugin.json` wasn't bumped |
| Hook/agent field ignored | `hooks`, `mcpServers`, `permissionMode` are stripped from plugin agents |
| Skill name is a version string | Root `SKILL.md` with no frontmatter `name` |
| Changes not picked up | Run `/reload-plugins` |

A `CLAUDE.md` at the plugin root is **not** loaded as context. Ship instructions as a Skill instead.

---

## Validate Your Plugin

| Check | Expected |
| --- | --- |
| Manifest location | `.claude-plugin/plugin.json` |
| Component location | `skills/`, `agents/`, `hooks/` at the plugin **root** |
| `name` | Present, kebab-case, no spaces |
| Bundled paths | Use `${CLAUDE_PLUGIN_ROOT}`, quoted in shell form |
| No traversal | Nothing references files outside the plugin directory |
| Validation | `claude plugin validate <path> --strict` passes |
| Marketplace | `.claude-plugin/marketplace.json` with `name`, `owner`, `plugins` |
| Install test | Installs and components resolve under their namespace |
