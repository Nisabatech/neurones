"""Main Click group entry point for Neurones CLI."""

from __future__ import annotations

import asyncio
import sys

import click

from neurones import __version__
from neurones.cli.compare_cmd import compare
from neurones.cli.run_cmd import run
from neurones.cli.status_cmd import status


class NeuronGroup(click.Group):
    """Custom Click group that treats unknown args as a prompt for orchestration."""

    def parse_args(self, ctx, args):
        # If the first arg looks like a subcommand, let Click handle it normally
        if args and args[0] in self.commands:
            return super().parse_args(ctx, args)

        # Check for flags first
        if not args or args == ["--tui"] or (len(args) == 1 and args[0].startswith("--")):
            return super().parse_args(ctx, args)

        # Otherwise, treat remaining non-flag args as a prompt
        # Extract flags first
        prompt_parts = []
        remaining = []
        i = 0
        while i < len(args):
            if args[i].startswith("--"):
                remaining.append(args[i])
                # Check if this flag takes a value
                if i + 1 < len(args) and not args[i + 1].startswith("--"):
                    remaining.append(args[i + 1])
                    i += 1
            else:
                prompt_parts.append(args[i])
            i += 1

        if prompt_parts:
            ctx.params["prompt"] = " ".join(prompt_parts)
        return super().parse_args(ctx, remaining)


@click.group(cls=NeuronGroup, invoke_without_command=True)
@click.version_option(__version__, prog_name="neurones")
@click.option("--tui", is_flag=True, help="Launch the TUI dashboard")
@click.pass_context
def cli(ctx: click.Context, tui: bool) -> None:
    """Neurones — AI Agent Orchestrator.

    Run with a prompt to orchestrate across AI agents,
    or without arguments to launch the TUI dashboard.
    """
    ctx.ensure_object(dict)

    if ctx.invoked_subcommand is not None:
        return

    prompt = ctx.params.get("prompt")

    if tui or prompt is None:
        _launch_tui()
    else:
        from neurones.cli.orchestrate_cmd import orchestrate
        asyncio.run(orchestrate(prompt))


def _launch_tui() -> None:
    """Launch the Textual TUI dashboard."""
    from neurones.tui.app import NeuronApp
    app = NeuronApp()
    app.run()


def _make_config_group() -> click.Group:
    """Create the config subcommand group."""

    @click.group()
    def config() -> None:
        """View and modify Neurones configuration."""

    @config.command("show")
    def config_show() -> None:
        """Display current configuration."""
        from neurones.config import CONFIG_FILE, load_config
        from neurones.output.console import console

        cfg = load_config()
        console.print(f"\n[header]Neurones Configuration[/header] ({CONFIG_FILE})\n")
        console.print(f"  primary: [primary]{cfg.primary}[/primary]")
        console.print(f"  parallel_timeout: {cfg.parallel_timeout}s")
        console.print(f"  json_output: {cfg.json_output}")
        console.print()
        for name, agent_cfg in cfg.agents.items():
            marker = " (primary)" if name == cfg.primary else ""
            console.print(f"  [agent.{name}]{name}[/agent.{name}]{marker}:")
            console.print(f"    auto_approve: {agent_cfg.auto_approve}")
            console.print(f"    timeout: {agent_cfg.timeout}s")
            if agent_cfg.default_model:
                console.print(f"    model: {agent_cfg.default_model}")
            if agent_cfg.max_turns:
                console.print(f"    max_turns: {agent_cfg.max_turns}")
            if agent_cfg.extra_args:
                console.print(f"    extra_args: {agent_cfg.extra_args}")
        console.print()

    @config.command("set")
    @click.argument("key")
    @click.argument("value")
    def config_set(key: str, value: str) -> None:
        """Set a configuration value (e.g., 'primary claude')."""
        from neurones.config import load_config, save_config
        from neurones.output.console import console

        cfg = load_config()

        if key == "primary":
            cfg.primary = value
        elif key == "parallel_timeout":
            cfg.parallel_timeout = int(value)
        elif key == "json_output":
            cfg.json_output = value.lower() in ("true", "1", "yes")
        elif "." in key:
            parts = key.split(".")
            if len(parts) == 3 and parts[0] == "agents":
                agent_name = parts[1]
                field = parts[2]
                agent_cfg = cfg.get_agent_config(agent_name)
                if field == "auto_approve":
                    agent_cfg.auto_approve = value.lower() in ("true", "1", "yes")
                elif field == "timeout":
                    agent_cfg.timeout = int(value)
                elif field == "default_model":
                    agent_cfg.default_model = value
                elif field == "max_turns":
                    agent_cfg.max_turns = int(value)
                else:
                    console.print(f"[status.failed]Unknown field: {field}[/status.failed]")
                    return
                cfg.agents[agent_name] = agent_cfg
            else:
                console.print(f"[status.failed]Unknown key: {key}[/status.failed]")
                return
        else:
            console.print(f"[status.failed]Unknown key: {key}[/status.failed]")
            return

        save_config(cfg)
        console.print(f"[status.success]Set {key} = {value}[/status.success]")

    return config


# Register subcommands
cli.add_command(run)
cli.add_command(compare)
cli.add_command(status)
cli.add_command(_make_config_group(), "config")
