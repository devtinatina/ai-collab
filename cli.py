#!/usr/bin/env python3
"""AI Collaboration CLI - Agile-style AI teamwork tool"""

import os
import sys

import click
import yaml
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt

from ai_clients import create_client
from workflow import CollaborationWorkflow

console = Console()


def load_config(config_path: str = None) -> dict:
    """Load configuration from YAML file"""
    if config_path is None:
        config_path = os.path.join(os.path.dirname(__file__), "config.yaml")

    if os.path.exists(config_path):
        with open(config_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    return {}


def create_workflow(config: dict) -> CollaborationWorkflow:
    """Create workflow from config"""
    models = config.get("models", {})
    workflow_config = config.get("workflow", {})

    manager_config = models.get("manager", {})
    developer_config = models.get("developer", {})

    # Create clients
    manager_client = create_client(
        provider=manager_config.get("provider", "openai"),
        model=manager_config.get("model", "gpt-4o"),
        temperature=manager_config.get("temperature", 0.3),
    )

    developer_client = create_client(
        provider=developer_config.get("provider", "anthropic"),
        model=developer_config.get("model", "claude-sonnet-4-20250514"),
        temperature=developer_config.get("temperature", 0.7),
    )

    return CollaborationWorkflow(
        manager_client=manager_client,
        developer_client=developer_client,
        max_iterations=workflow_config.get("max_iterations", 10),
        output_dir=workflow_config.get("output_dir", "./output"),
        # Advanced control parameters
        max_tokens=workflow_config.get("max_tokens"),
        max_cost=workflow_config.get("max_cost"),
        checkpoint_interval=workflow_config.get("checkpoint_interval"),
        max_no_progress=workflow_config.get("max_no_progress", 3),
        early_stop_similarity=workflow_config.get("early_stop_similarity", 0.95),
        budget_mode=workflow_config.get("budget_mode", "balanced"),
    )


@click.group()
@click.option("--config", "-c", default=None, help="Path to config file")
@click.pass_context
def cli(ctx, config):
    """AI Collaboration Tool - PM(OpenAI) + Developer(Claude) teamwork"""
    ctx.ensure_object(dict)
    ctx.obj["config"] = load_config(config)


@cli.command()
@click.argument("requirements", required=False)
@click.option("--file", "-f", type=click.Path(exists=True), help="Read requirements from file")
@click.pass_context
def develop(ctx, requirements, file):
    """Run development workflow with PM review loop"""
    if file:
        with open(file, "r", encoding="utf-8") as f:
            requirements = f.read()
    elif not requirements:
        console.print("[bold blue]Enter your requirements (press Ctrl+D when done):[/]")
        requirements = sys.stdin.read().strip()

    if not requirements:
        console.print("[red]No requirements provided[/]")
        return

    console.print(Panel(
        "[bold green]Development Workflow[/]\n\n"
        "PM (OpenAI) will review Developer (Claude)'s work until approved.",
        title="AI Collaboration"
    ))

    try:
        workflow = create_workflow(ctx.obj["config"])
        result = workflow.run_development(requirements)

        console.print("\n")
        if result.success:
            console.print(Panel(
                f"[bold green]APPROVED[/] after {result.iterations} iteration(s)",
                title="Result"
            ))
        else:
            console.print(Panel(
                f"[bold yellow]Reached max iterations ({result.iterations})[/]",
                title="Result"
            ))

    except Exception as e:
        console.print(f"[red]Error: {e}[/]")
        raise


@cli.command()
@click.option("--file", "-f", type=click.Path(exists=True), help="Code file to review")
@click.option("--context", "-x", default="", help="Additional context for review")
@click.pass_context
def review(ctx, file, context):
    """Run code review workflow"""
    if file:
        with open(file, "r", encoding="utf-8") as f:
            code = f.read()
    else:
        console.print("[bold blue]Paste your code (press Ctrl+D when done):[/]")
        code = sys.stdin.read().strip()

    if not code:
        console.print("[red]No code provided[/]")
        return

    console.print(Panel(
        "[bold yellow]Code Review Workflow[/]\n\n"
        "PM will review and Developer will improve until approved.",
        title="AI Collaboration"
    ))

    try:
        workflow = create_workflow(ctx.obj["config"])
        result = workflow.run_review(code, context)

        console.print("\n")
        if result.success:
            console.print(Panel(
                f"[bold green]APPROVED[/] after {result.iterations} iteration(s)",
                title="Result"
            ))
        else:
            console.print(Panel(
                f"[bold yellow]Reached max iterations ({result.iterations})[/]",
                title="Result"
            ))

    except Exception as e:
        console.print(f"[red]Error: {e}[/]")
        raise


@cli.command()
@click.argument("project", required=False)
@click.option("--file", "-f", type=click.Path(exists=True), help="Read project description from file")
@click.pass_context
def plan(ctx, project, file):
    """Run project planning workflow"""
    if file:
        with open(file, "r", encoding="utf-8") as f:
            project = f.read()
    elif not project:
        console.print("[bold blue]Describe your project (press Ctrl+D when done):[/]")
        project = sys.stdin.read().strip()

    if not project:
        console.print("[red]No project description provided[/]")
        return

    console.print(Panel(
        "[bold cyan]Planning Workflow[/]\n\n"
        "Developer creates plan, PM reviews until approved.",
        title="AI Collaboration"
    ))

    try:
        workflow = create_workflow(ctx.obj["config"])
        result = workflow.run_planning(project)

        console.print("\n")
        if result.success:
            console.print(Panel(
                f"[bold green]APPROVED[/] after {result.iterations} iteration(s)",
                title="Result"
            ))
        else:
            console.print(Panel(
                f"[bold yellow]Reached max iterations ({result.iterations})[/]",
                title="Result"
            ))

    except Exception as e:
        console.print(f"[red]Error: {e}[/]")
        raise


@cli.command()
@click.argument("topic", required=False)
@click.option("--context", "-x", default="", help="Additional context")
@click.option("--file", "-f", type=click.Path(exists=True), help="Read topic from file")
@click.pass_context
def docs(ctx, topic, context, file):
    """Run documentation workflow"""
    if file:
        with open(file, "r", encoding="utf-8") as f:
            topic = f.read()
    elif not topic:
        topic = Prompt.ask("[bold blue]What would you like to document?[/]")

    if not topic:
        console.print("[red]No topic provided[/]")
        return

    console.print(Panel(
        "[bold magenta]Documentation Workflow[/]\n\n"
        "Developer writes docs, PM reviews until approved.",
        title="AI Collaboration"
    ))

    try:
        workflow = create_workflow(ctx.obj["config"])
        result = workflow.run_documentation(topic, context)

        console.print("\n")
        if result.success:
            console.print(Panel(
                f"[bold green]APPROVED[/] after {result.iterations} iteration(s)",
                title="Result"
            ))
        else:
            console.print(Panel(
                f"[bold yellow]Reached max iterations ({result.iterations})[/]",
                title="Result"
            ))

    except Exception as e:
        console.print(f"[red]Error: {e}[/]")
        raise


@cli.command()
@click.pass_context
def interactive(ctx):
    """Interactive mode - choose workflow type"""
    console.print(Panel(
        "[bold]AI Collaboration Tool[/]\n\n"
        "PM (OpenAI/GPT-4) + Developer (Claude)\n"
        "Agile-style collaboration with strict review",
        title="Welcome"
    ))

    workflow_type = Prompt.ask(
        "\n[bold]Select workflow type[/]",
        choices=["develop", "review", "plan", "docs", "quit"],
        default="develop"
    )

    if workflow_type == "quit":
        console.print("[dim]Goodbye![/]")
        return

    console.print(f"\n[bold blue]Enter your input (press Ctrl+D when done):[/]")
    user_input = sys.stdin.read().strip()

    if not user_input:
        console.print("[red]No input provided[/]")
        return

    try:
        workflow = create_workflow(ctx.obj["config"])

        if workflow_type == "develop":
            result = workflow.run_development(user_input)
        elif workflow_type == "review":
            result = workflow.run_review(user_input)
        elif workflow_type == "plan":
            result = workflow.run_planning(user_input)
        elif workflow_type == "docs":
            result = workflow.run_documentation(user_input)

        console.print("\n")
        status = "[bold green]APPROVED[/]" if result.success else "[bold yellow]Max iterations reached[/]"
        console.print(Panel(f"{status} - {result.iterations} iteration(s)", title="Result"))

    except Exception as e:
        console.print(f"[red]Error: {e}[/]")
        raise


def main():
    cli(obj={})


if __name__ == "__main__":
    main()
