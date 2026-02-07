# Neurones

<p align="center">
  <img src="https://raw.githubusercontent.com/Nisabatech/neurones/main/assets/logo.png" alt="Neurones logo" width="700" />
</p>

Neurones is a multi-model orchestrator for developer-focused AI CLIs.  
It coordinates Claude Code, Gemini CLI, and Codex CLI from a single interface.

## Highlights

- Orchestrated workflow: analyze, delegate, collect, synthesize
- Direct run mode per agent
- Parallel compare mode across agents
- Terminal UI dashboard with live per-agent panels
- Retry handling for rate-limited agent calls

## Installation

```bash
pip install neurones
```

Or from source:

```bash
git clone https://github.com/Nisabatech/neurones.git
cd neurones
pip install -e .
```

## Requirements

- Python 3.11+
- At least one installed AI CLI:
  - `claude`
  - `gemini`
  - `codex`

## Usage

Run orchestration with a prompt:

```bash
nr "Plan and implement a FastAPI auth module with tests"
```

Run a prompt directly on one agent:

```bash
nr run codex "Refactor this function for readability"
```

Compare answers from multiple agents:

```bash
nr compare "Explain this architecture"
```

Show detected agents and active config:

```bash
nr status
nr config show
```

Launch TUI:

```bash
nr --tui
```

## Configuration

Configuration file is created at:

```text
~/.neurones/config.toml
```

Example:

```toml
primary = "claude"
parallel_timeout = 600
json_output = true

[agents.codex]
auto_approve = true
timeout = 300
extra_args = ["--skip-git-repo-check"]
```

## Project Links

- Repository: https://github.com/Nisabatech/neurones
- Issues: https://github.com/Nisabatech/neurones/issues
