# Publish an MCP Server as a Claude Code Plugin

Take the Python MCP server from `ClaudeAPI/13_MCP/custom-mcp-python`, add a stdio transport, package it as a Claude Code plugin, publish it to GitHub with CI and releases, and install it from your own marketplace.

**Time needed:** 60–90 minutes
**You will end with:** a GitHub repository that works as a plugin marketplace, with a CI workflow, a release workflow, and an MCP server you installed from it into Claude Code.

## How the pieces fit

```text
MCP server (Python)
  ├─ stdio transport  → used by Claude Code when the plugin is installed
  └─ HTTP transport   → used for remote or manual testing
        │
        ▼
Plugin folder (mcp-demo/)  ── .mcp.json tells Claude Code how to launch the server
        │
        ▼
GitHub repository  ── .claude-plugin/marketplace.json makes it a marketplace
        │
        ├─ CI workflow       validates manifests and smoke-tests the server on every push
        └─ Release workflow  bundles the plugin and creates a GitHub Release on a version tag
        │
        ▼
/plugin marketplace add <github-user>/MCPtoMarketplace
```

> **Note:** *SSE* (Server-Sent Events) was the original HTTP transport for MCP. The current spec replaces it with *Streamable HTTP*, which still streams responses with SSE when needed. This guide uses Streamable HTTP, which is what your server already does.

> **Note:** For a Claude Code plugin, GitHub *is* the marketplace. Pushing to the repository is the publish step. There is no separate upload.

## Prerequisites

| Tool | Check with | Needed for |
|---|---|---|
| Python 3.10+ | `python --version` | Running the server |
| `uv` | `uv --version` | Running the server with its dependencies (install from [docs.astral.sh/uv](https://docs.astral.sh/uv/)) |
| Git | `git --version` | Publishing |
| A GitHub account | Sign in at github.com | Hosting the marketplace |
| Claude Code 2.x | `claude --version` | Validating and installing plugins |
| Node.js 18+ (optional) | `node --version` | MCP Inspector in Part 3 |

Commands use PowerShell on Windows. On macOS or Linux, the commands are the same unless a note says otherwise.

## Part 1: Run the existing server

Run the server as it is today, so you know what you are starting from.

1. Open a terminal in `ClaudeAPI/13_MCP/custom-mcp-python`.
2. Create and activate a virtual environment.

   ```powershell
   python -m venv .venv
   .venv\Scripts\Activate.ps1
   ```

   On macOS or Linux, run `source .venv/bin/activate` instead.

3. Install the dependencies.

   ```powershell
   pip install -r requirements.txt
   ```

4. Start the server.

   ```powershell
   python server.py
   ```

   Expected output:

   ```text
   MCP server running at http://localhost:3000
   ```

5. Press `Ctrl+C` to stop it.

> **Warning:** Always use a virtual environment here. A global Python may have `mcp` 1.x installed, which has no `MCPServer` class. You then get `ImportError: cannot import name 'MCPServer'`. `requirements.txt` asks for `mcp>=2.0.0`.

## Part 2: Set up the marketplace repository folder

Work in a **working folder outside the course repository**, `MCPtoMarketplace`. A marketplace must sit at the root of its own GitHub repository, so this folder is the repository you publish. Claude Code looks for `.claude-plugin/marketplace.json` at the repository root, so do not nest the plugin files inside a subfolder. This guide is the repository's `README.md`.

The folder already holds the marketplace catalog and the `todo-toolkit` plugin. You add the `mcp-demo` plugin, the tests, and the workflows.

1. Open a terminal in the `MCPtoMarketplace` folder.

2. Create the new folders.

   ```powershell
   New-Item -ItemType Directory -Force mcp-demo\.claude-plugin, mcp-demo\server, tests, .github\workflows
   ```

3. Check that a `.gitignore` file exists in the repository root. If not, create it.

   ```text
   .env
   .venv/
   __pycache__/
   dist/
   ```

By the end of the guide you have this layout:

```text
MCPtoMarketplace/                       # the repository root
├── .claude-plugin/marketplace.json     # the catalog, named mcp-marketplace-demo
├── .github/workflows/                  # CI and release (Parts 9 and 10)
│   ├── ci.yml
│   └── release.yml
├── .gitignore
├── README.md                           # this guide
├── docs/                               # background notes
├── mcp-demo/                           # the new plugin
│   ├── .claude-plugin/plugin.json
│   ├── .mcp.json
│   └── server/server.py
├── todo-toolkit/                       # the existing plugin
└── tests/
    ├── smoke_test.py
    └── http_check.py
```

> **Note:** The repository name and the marketplace name differ on purpose. `MCPtoMarketplace` is the GitHub repository, which you pass to `/plugin marketplace add`. `mcp-marketplace-demo` is the `name` in `marketplace.json`, which you type after `@` when installing.

## Part 3: Add the stdio transport to the server

Claude Code launches a plugin's MCP server as a local process and talks to it over stdin and stdout. That is the *stdio* transport, and your current server does not offer it.

1. Create `mcp-demo/server/server.py` with this content.

   ```python
   # /// script
   # requires-python = ">=3.10"
   # dependencies = [
   #     "mcp>=2.0.0",
   #     "fastapi>=0.141.0",
   #     "uvicorn>=0.52.0",
   #     "httpx>=0.28.0",
   # ]
   # ///
   """Demo MCP server with two transports.

   Run over stdio (for Claude Code):  uv run server.py --transport stdio
   Run over HTTP (for remote use):    uv run server.py --transport http --port 3000
   """

   import argparse
   from contextlib import asynccontextmanager

   import httpx
   from fastapi import FastAPI
   from mcp.server import MCPServer

   mcp_server = MCPServer(name="Demo", version="1.0.0")


   @mcp_server.tool(name="add")
   def add(a: float, b: float) -> str:
       """Add two numbers."""
       return str(a + b)


   @mcp_server.tool(name="get-energy-prices")
   async def get_energy_prices() -> str:
       """Fetch tomorrow's energy prices."""
       async with httpx.AsyncClient() as client:
           response = await client.get("https://api.awattar.de/v1/marketdata")
           data = response.json()
       return f"Energy prices for tomorrow: {data}"


   @mcp_server.tool(name="get-todos")
   async def get_todos() -> str:
       """Fetch a public todo list."""
       async with httpx.AsyncClient() as client:
           response = await client.get("https://jsonplaceholder.typicode.com/todos")
           data = response.json()
       return f"Todos: {data}"


   @mcp_server.resource("greeting://{name}")
   def greeting(name: str) -> str:
       """Return a greeting for `name`."""
       return f"Hello, {name}!"


   def build_http_app() -> FastAPI:
       """Return a FastAPI app that serves the MCP endpoint at /mcp."""
       mcp_app = mcp_server.streamable_http_app()

       @asynccontextmanager
       async def lifespan(app: FastAPI):
           async with mcp_app.router.lifespan_context(mcp_app):
               yield

       app = FastAPI(lifespan=lifespan)
       app.mount("/", mcp_app)
       return app


   def main() -> None:
       """Parse arguments and start the server on the chosen transport."""
       parser = argparse.ArgumentParser(description="Demo MCP server")
       parser.add_argument("--transport", choices=["stdio", "http"], default="stdio")
       parser.add_argument("--port", type=int, default=3000)
       args = parser.parse_args()

       if args.transport == "stdio":
           # Never print() to stdout here: stdout carries the MCP protocol.
           mcp_server.run(transport="stdio")
       else:
           import uvicorn

           uvicorn.run(build_http_app(), host="127.0.0.1", port=args.port)


   if __name__ == "__main__":
       main()
   ```

   The comment block at the top is *inline script metadata* (PEP 723). It lets `uv run server.py` install the dependencies by itself, so the plugin needs no virtual environment.

2. Check that you changed three things from the original: the `--transport` switch, the dependencies header, and the HTTP app moved into `build_http_app()`.

> **Warning:** In stdio mode, never write to stdout with `print()`. Stdout carries the MCP messages, and extra text corrupts them. Log to stderr instead.

## Part 4: Test the server

### Test stdio

1. Create `tests/smoke_test.py`.

   ```python
   """Smoke-test the demo MCP server over stdio.

   Run with: uv run --with "mcp>=2.0.0" tests/smoke_test.py <path-to-server.py>
   """

   import asyncio
   import sys

   from mcp import Client, StdioServerParameters


   async def main(server_path: str) -> None:
       """Start the server, list its tools, and call `add`."""
       params = StdioServerParameters(
           command="uv", args=["run", server_path, "--transport", "stdio"]
       )
       async with Client(params) as client:
           tools = await client.list_tools()
           names = sorted(tool.name for tool in tools.tools)
           assert names == ["add", "get-energy-prices", "get-todos"], names

           result = await client.call_tool("add", {"a": 2, "b": 3})
           text = result.content[0].text
           assert text == "5.0", text
       print("PASS: tools =", names, "| add(2, 3) =", text)


   if __name__ == "__main__":
       asyncio.run(main(sys.argv[1]))
   ```

2. Run it.

   ```powershell
   uv run --with "mcp>=2.0.0" tests/smoke_test.py mcp-demo/server/server.py
   ```

   The first run takes about 30 seconds while `uv` downloads packages. Expected output:

   ```text
   PASS: tools = ['add', 'get-energy-prices', 'get-todos'] | add(2, 3) = 5.0
   ```

### Test HTTP

1. Create `tests/http_check.py`.

   ```python
   """Call `add` on a running HTTP MCP server."""

   import asyncio
   import sys

   from mcp import Client


   async def main(url: str) -> None:
       """Connect to `url` and call the `add` tool."""
       async with Client(url) as client:
           result = await client.call_tool("add", {"a": 4, "b": 6})
           print("add(4, 6) =", result.content[0].text)


   if __name__ == "__main__":
       asyncio.run(main(sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:3000/mcp"))
   ```

2. Start the HTTP server in terminal 1.

   ```powershell
   uv run mcp-demo/server/server.py --transport http --port 3000
   ```

3. Run the check in terminal 2.

   ```powershell
   uv run --with "mcp>=2.0.0" tests/http_check.py
   ```

   Expected output:

   ```text
   add(4, 6) = 10.0
   ```

4. Press `Ctrl+C` in terminal 1 to stop the server.

> **Tip:** To explore the server in a browser UI, run `npx @modelcontextprotocol/inspector` and connect to `http://127.0.0.1:3000/mcp` with the **Streamable HTTP** transport.

## Part 5: Write the plugin files

1. Create `mcp-demo/.claude-plugin/plugin.json`.

   ```json
   {
     "$schema": "https://json.schemastore.org/claude-code-plugin-manifest.json",
     "name": "mcp-demo",
     "displayName": "MCP Demo",
     "version": "1.0.0",
     "description": "A demo MCP server with add, get-energy-prices, get-todos, and a greeting resource.",
     "author": { "name": "<your-name>" },
     "license": "MIT",
     "keywords": ["mcp", "demo", "course"]
   }
   ```

2. Create `mcp-demo/.mcp.json`.

   ```json
   {
     "mcpServers": {
       "demo": {
         "command": "uv",
         "args": ["run", "${CLAUDE_PLUGIN_ROOT}/server/server.py", "--transport", "stdio"]
       }
     }
   }
   ```

   `${CLAUDE_PLUGIN_ROOT}` is the folder Claude Code copies the plugin into when someone installs it. Never use a relative path here, because the plugin runs from that copy.

3. Add the plugin to `.claude-plugin/marketplace.json` by appending a second entry to `plugins`.

   ```json
   {
     "name": "mcp-marketplace-demo",
     "description": "Plugins built during the Claude Code course, packaging the Skills, agents, and hooks from earlier modules.",
     "owner": { "name": "<your-name>" },
     "plugins": [
       {
         "name": "todo-toolkit",
         "source": "./todo-toolkit",
         "description": "Skills, agents, and hooks for the full-stack To-Do application built in this course."
       },
       {
         "name": "mcp-demo",
         "source": "./mcp-demo",
         "description": "A demo MCP server with add, get-energy-prices, get-todos, and a greeting resource."
       }
     ]
   }
   ```

4. Validate the marketplace and both plugins.

   ```powershell
   claude plugin validate . --strict
   claude plugin validate ./mcp-demo --strict
   claude plugin validate ./todo-toolkit --strict
   ```

   Expected output for each command ends with:

   ```text
   ✔ Validation passed
   ```

## Part 6: Test the plugin locally

Test before you publish, so a mistake costs you a restart and not a release.

1. Start Claude Code with the plugin loaded from disk.

   ```powershell
   claude --plugin-dir ./mcp-demo
   ```

2. Run `/mcp` and check that `plugin:mcp-demo:demo` is listed as **connected**.
3. Ask Claude: `Use the add tool to add 2 and 3.` Claude calls the tool and answers `5.0`.

> **Note:** `/plugin` and `/mcp` work only in an interactive session. In a non-interactive session, `/plugin` reports `isn't available in this environment`.

## Part 7: Publish to GitHub

1. Create an empty repository named `MCPtoMarketplace` on github.com. Leave **Add a README** and **.gitignore** unchecked.
2. Commit and push your folder.

   ```powershell
   git init -b main
   git add .
   git commit -m "Add mcp-demo plugin and marketplace"
   git remote add origin https://github.com/<github-user>/MCPtoMarketplace.git
   git push -u origin main
   ```

3. Open the repository in your browser. Check that `.claude-plugin/marketplace.json` is at the **top level**, not inside a subfolder. Claude Code looks for it there.

> **Warning:** If you made the repository private, installing needs your Git credentials. Public repositories need none.

## Part 8: Install from GitHub

1. Open an interactive Claude Code session in any project.
2. Add your marketplace.

   ```text
   /plugin marketplace add <github-user>/MCPtoMarketplace
   ```

3. Install the plugin.

   ```text
   /plugin install mcp-demo@mcp-marketplace-demo
   ```

4. Run `/reload-plugins` if the install summary asks for it.
5. Run `/mcp`. Check that `plugin:mcp-demo:demo` is connected, then repeat the `add` test from Part 6.

## Part 9: Add CI with GitHub Actions

CI runs your checks on every push and pull request, so a broken manifest never reaches users.

1. Create `.github/workflows/ci.yml`.

   ```yaml
   name: CI

   on:
     push:
       branches: [main]
     pull_request:

   jobs:
     validate:
       runs-on: ubuntu-latest
       steps:
         - uses: actions/checkout@v4

         - uses: astral-sh/setup-uv@v5

         - uses: actions/setup-node@v4
           with:
             node-version: 22

         - name: Install the Claude Code CLI
           run: npm install -g @anthropic-ai/claude-code

         - name: Validate the marketplace and plugins
           run: |
             claude plugin validate . --strict
             claude plugin validate ./mcp-demo --strict
             claude plugin validate ./todo-toolkit --strict

         - name: Smoke-test the MCP server
           run: uv run --with "mcp>=2.0.0" tests/smoke_test.py mcp-demo/server/server.py
   ```

2. Commit and push.

   ```powershell
   git add .github/workflows/ci.yml
   git commit -m "Add CI workflow"
   git push
   ```

3. Open the **Actions** tab on GitHub. Check that the **CI** run turns green.

> **Note:** The commands in this workflow ran successfully on a local machine while writing this guide. The workflow itself runs for the first time when you push it. If `claude plugin validate` fails on the runner, read the log, because it may be asking for something the local run did not.

## Part 10: Release and bundle

A release does two jobs: it freezes a version of the plugin, and it attaches a downloadable `.zip` bundle.

1. Create `.github/workflows/release.yml`.

   ```yaml
   name: Release

   on:
     push:
       tags: ["v*"]

   permissions:
     contents: write

   jobs:
     release:
       runs-on: ubuntu-latest
       steps:
         - uses: actions/checkout@v4

         - name: Check the tag matches the plugin version
           run: |
             VERSION=$(jq -r .version mcp-demo/.claude-plugin/plugin.json)
             if [ "v$VERSION" != "$GITHUB_REF_NAME" ]; then
               echo "Tag $GITHUB_REF_NAME does not match plugin version $VERSION"
               exit 1
             fi

         - name: Bundle the plugin
           run: |
             mkdir dist
             (cd mcp-demo && zip -r "../dist/mcp-demo-$GITHUB_REF_NAME.zip" .)

         - name: Create the GitHub Release
           env:
             GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
           run: gh release create "$GITHUB_REF_NAME" dist/*.zip --generate-notes
   ```

   The version check stops you from tagging `v1.1.0` while `plugin.json` still says `1.0.0`.

2. Commit and push the workflow.

   ```powershell
   git add .github/workflows/release.yml
   git commit -m "Add release workflow"
   git push
   ```

### Cut a release

1. Change `version` in `mcp-demo/.claude-plugin/plugin.json` to the new number, for example `1.1.0`.
2. Commit, tag, and push.

   ```powershell
   git add mcp-demo/.claude-plugin/plugin.json
   git commit -m "Release mcp-demo 1.1.0"
   git tag v1.1.0
   git push
   git push origin v1.1.0
   ```

3. Open the **Releases** page on GitHub. Check that `v1.1.0` has an `mcp-demo-v1.1.0.zip` attachment.
4. Update the installed plugin in Claude Code.

   ```powershell
   claude plugin update mcp-demo
   ```

> **Note:** Claude Code decides whether an update exists from the `version` in `plugin.json`. If you forget to bump it, `claude plugin update` finds nothing, even though the code changed.

## Verify

Check each line before you call the exercise done.

- [ ] `uv run --with "mcp>=2.0.0" tests/smoke_test.py mcp-demo/server/server.py` prints `PASS`
- [ ] `claude plugin validate . --strict` prints `✔ Validation passed`
- [ ] The CI run on GitHub is green
- [ ] `/plugin marketplace add <github-user>/MCPtoMarketplace` succeeds in a clean session
- [ ] `/mcp` shows `plugin:mcp-demo:demo` as connected
- [ ] A release tag produced a `.zip` on the Releases page

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `ImportError: cannot import name 'MCPServer'` | A global Python has `mcp` 1.x | Use a virtual environment or `uv run`, which installs `mcp>=2.0.0` |
| `ModuleNotFoundError: No module named 'httpx'` | Running `server.py` with a Python that lacks the dependencies | Run it with `uv run`, which reads the script header |
| Smoke test fails with `Connection closed` | The server crashed on startup | Run `uv run mcp-demo/server/server.py --transport stdio` and read the error |
| `/mcp` shows the server as failed | `uv` is not on the `PATH` Claude Code sees | Install `uv`, then restart Claude Code |
| Garbled or invalid MCP messages | Something wrote to stdout in stdio mode | Remove `print()` calls from the stdio path |
| `/plugin` says `isn't available in this environment` | The session is non-interactive | Open Claude Code in an interactive terminal or the VS Code extension |
| `marketplace add` cannot find the catalog | `marketplace.json` is not at the repository root | Move `.claude-plugin/` to the top level of the repository |
| `claude plugin update` finds nothing | `version` was not bumped | Change `version` in `plugin.json` and push |
| Release workflow fails at the version check | Tag and `plugin.json` version differ | Delete the tag, fix the version, and tag again |
| Port 3000 is already in use | Another process holds the port | Pass `--port 3001` |

## Going further

The Claude Code plugin marketplace is the shortest route, but it is not the only one. Each option below needs extra packaging that this guide does not cover.

| Destination | What it adds |
|---|---|
| [Official MCP Registry](https://registry.modelcontextprotocol.io) | Publish the server to PyPI or as a Docker image, add a `server.json`, and publish with the `mcp-publisher` tool |
| Claude Desktop extension directory | Build a `.mcpb` bundle and submit it for manual review |
