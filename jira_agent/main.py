"""Jira Ticket Automation Agent CLI.

Usage:
    jira-agent list-tickets [--config=<path>] [--status=<status>] [--limit=<n>] [--interactive]
    jira-agent list-prs [--config=<path>] [--state=<state>]
    jira-agent watch [--config=<path>] [--interval=<seconds>]
    jira-agent process [--config=<path>] [--repo=<repo>] [--status=<status>] [--limit=<n>] [--dry-run]
    jira-agent process-ticket <ticket_key> [--config=<path>] [--repo=<repo>] [--dry-run]
    jira-agent check-pr <pr_number> [--config=<path>] [--repo=<repo>]
    jira-agent fix-ci <pr_number> [--config=<path>] [--repo=<repo>]
    jira-agent serve [--port=<port>] [--host=<host>] [--config-dir=<dir>]
    jira-agent init-config <repo> [--output=<path>]
    jira-agent auth login [--service=<service>]
    jira-agent auth status
    jira-agent auth logout [--service=<service>]
    jira-agent config show
    jira-agent config validate <config_path>
    jira-agent health [--config=<path>]
    jira-agent learn status
    jira-agent learn publish [--dry-run] [--jira-agent-repo=<repo>]
    jira-agent learn list [--category=<cat>]
    jira-agent --help
    jira-agent --version

Commands:
    list-tickets    List tickets from a Jira board
    list-prs        List open PRs for the repository
    watch           Poll for merged PRs and auto-transition tickets to Done
    process         Process tickets from a Jira board
    process-ticket  Process a specific ticket by key
    check-pr        Check PR status and pending feedback
    fix-ci          Attempt to fix CI failures on a PR
    serve           Start webhook server for Jira/GitHub events
    init-config     Generate a config file for a new repository
    auth            Manage OAuth authentication
    config          Show or validate configuration
    health          Test all service connections (Anthropic, Jira, GitHub, Databricks)
    learn           Manage agent learnings (captured from resolved failures)

Options:
    -h --help                Show this help message
    --version                Show version
    --config=<path>          Path to repo config file
    --repo=<repo>            Repository in owner/name format (e.g., acme/data)
    --status=<status>        Filter tickets by Jira status (e.g., "To Do", "Ready for Dev")
    --state=<state>          Filter PRs by state: open, closed, all [default: open]
    --limit=<n>              Maximum tickets to process [default: 10]
    --interactive            Interactive mode: select ticket with arrow keys to process
    --dry-run                Preview actions without making changes
    --interval=<seconds>     Polling interval in seconds [default: 60]
    --port=<port>            Webhook server port [default: 8080]
    --host=<host>            Webhook server host [default: 0.0.0.0]
    --config-dir=<dir>       Directory containing repo config files [default: ./configs]
    --output=<path>          Output path for generated config
    --service=<service>      Service to authenticate: jira, github, databricks, or all [default: all]
    --jira-agent-repo=<repo> GitHub repo for jira-agent [default: djayatillake/jira-agent]
    --category=<cat>         Filter learnings by category: ci-failure, code-pattern, error-resolution

Environment Variables:
    ANTHROPIC_API_KEY           Required for Claude Agent SDK
    JIRA_AGENT_JIRA_OAUTH_CLIENT_ID      Jira OAuth app client ID
    JIRA_AGENT_JIRA_OAUTH_CLIENT_SECRET  Jira OAuth app client secret
    JIRA_AGENT_GITHUB_TOKEN              GitHub personal access token
    JIRA_AGENT_DATABRICKS_HOST           Databricks workspace URL
    JIRA_AGENT_DATABRICKS_TOKEN          Databricks personal access token
    JIRA_AGENT_WEBHOOK_SECRET            Secret for webhook validation

Examples:
    # Process all "Ready for Dev" tickets for acme/data
    jira-agent process --config configs/acme-data.yaml --status="Ready for Dev" --limit=5

    # Process a specific ticket
    jira-agent process-ticket AENG-1234 --config configs/acme-data.yaml

    # Start webhook server
    jira-agent serve --port 8080 --config-dir ./configs

    # Generate config for a new repo
    jira-agent init-config acme/new-repo --output configs/acme-new-repo.yaml

    # Authenticate with all services
    jira-agent auth login

    # Check authentication status
    jira-agent auth status

    # Test all service connections
    jira-agent health

    # Test connections with a specific config (tests repo access too)
    jira-agent health --config configs/acme-data.yaml

    # List tickets from board
    jira-agent list-tickets --config configs/acme-data.yaml

    # List tickets filtered by status
    jira-agent list-tickets --config configs/acme-data.yaml --status="To Do"

    # Interactive mode: browse and select a ticket to process
    jira-agent list-tickets --config configs/acme-data.yaml --interactive

    # List open PRs
    jira-agent list-prs --config configs/acme-data.yaml

    # Watch for merged PRs and auto-transition tickets (polls every 60s)
    jira-agent watch --config configs/acme-data.yaml

    # Watch with custom interval
    jira-agent watch --config configs/acme-data.yaml --interval=120

    # View pending learnings from agent execution
    jira-agent learn status

    # Publish learnings to jira-agent repo (creates PR)
    jira-agent learn publish

    # Publish with dry-run (preview only)
    jira-agent learn publish --dry-run

    # List learnings in knowledge base
    jira-agent learn list

    # List learnings by category
    jira-agent learn list --category=ci-failure
"""

import asyncio
import logging
import sys
from pathlib import Path

from docopt import docopt

from .config import get_settings
from .utils.logger import setup_logging

__version__ = "0.1.0"


def main() -> int:
    """Main entry point for the CLI."""
    args = docopt(__doc__, version=f"jira-agent {__version__}")

    settings = get_settings()
    setup_logging(settings.log_level)
    logger = logging.getLogger(__name__)

    try:
        if args["list-tickets"]:
            return asyncio.run(handle_list_tickets(args, settings))
        elif args["list-prs"]:
            return asyncio.run(handle_list_prs(args, settings))
        elif args["watch"]:
            return asyncio.run(handle_watch(args, settings))
        elif args["auth"]:
            return handle_auth(args, settings)
        elif args["config"]:
            return handle_config_command(args, settings)
        elif args["process"]:
            return asyncio.run(handle_process(args, settings))
        elif args["process-ticket"]:
            return asyncio.run(handle_process_ticket(args, settings))
        elif args["check-pr"]:
            return asyncio.run(handle_check_pr(args, settings))
        elif args["fix-ci"]:
            return asyncio.run(handle_fix_ci(args, settings))
        elif args["serve"]:
            return handle_serve(args, settings)
        elif args["init-config"]:
            return handle_init_config(args, settings)
        elif args["health"]:
            return asyncio.run(handle_health(args, settings))
        elif args["learn"]:
            return handle_learn(args, settings)
        else:
            print(__doc__)
            return 1
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        return 130
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        return 1


def handle_auth(args: dict, settings) -> int:
    """Handle authentication commands."""
    from .auth import AuthManager

    auth_manager = AuthManager(settings)

    if args["login"]:
        service = args["--service"] or "all"
        if service == "all":
            auth_manager.login_all()
        else:
            auth_manager.login(service)
        return 0
    elif args["status"]:
        auth_manager.print_status()
        return 0
    elif args["logout"]:
        service = args["--service"] or "all"
        if service == "all":
            auth_manager.logout_all()
        else:
            auth_manager.logout(service)
        return 0
    return 1


def handle_config_command(args: dict, settings) -> int:
    """Handle config commands."""
    if args["show"]:
        print("Current Configuration:")
        print("-" * 40)
        print(f"Claude Model: {settings.claude_model}")
        print(f"Anthropic API Key: {'*' * 8 if settings.has_anthropic_key else 'Not set'}")
        print(f"Jira OAuth: {'Configured' if settings.has_jira_oauth else 'Not set'}")
        print(f"GitHub Token: {'Configured' if settings.has_github_token else 'Not set'}")
        print(f"Databricks: {'Configured' if settings.has_databricks else 'Not set'}")
        print(f"Workspace Dir: {settings.workspace_dir}")
        print(f"Log Level: {settings.log_level}")
        return 0
    elif args["validate"]:
        from .repo_config.loader import ConfigLoader

        config_path = args["<config_path>"]
        try:
            loader = ConfigLoader()
            config = loader.load_from_file(config_path)
            print(f"Config valid: {config.full_repo_name}")
            print(f"  Jira Project: {config.jira.project_key}")
            print(f"  Default Branch: {config.repo.default_branch}")
            print(f"  PR Target: {config.repo.pr_target_branch}")
            print(f"  dbt Enabled: {config.dbt.enabled}")
            return 0
        except Exception as e:
            print(f"Config validation failed: {e}")
            return 1
    return 1


async def handle_list_tickets(args: dict, settings) -> int:
    """List tickets from a Jira board."""
    import questionary

    from .auth import AuthManager
    from .clients.jira_client import JiraClient
    from .repo_config.loader import ConfigLoader

    config_path = args["--config"]
    status_filter = args["--status"]
    limit = int(args["--limit"]) if args["--limit"] else 20
    interactive = args["--interactive"]

    if not config_path:
        print("Error: --config must be specified")
        return 1

    loader = ConfigLoader()
    repo_config = loader.load_from_file(config_path)

    auth_manager = AuthManager(settings)
    if not auth_manager.jira.is_authenticated():
        print("Error: Not authenticated with Jira. Run: jira-agent auth login --service=jira")
        return 1

    access_token = auth_manager.jira.get_access_token()
    cloud_id = auth_manager.jira.get_cloud_id()

    if not cloud_id:
        print("Error: Could not get Jira cloud ID. Try re-authenticating.")
        return 1

    jira_client = JiraClient(
        cloud_id=cloud_id,
        access_token=access_token,
    )

    print(f"Fetching tickets from {repo_config.jira.project_key}...")
    if status_filter:
        print(f"Filtering by status: {status_filter}")
    print()

    try:
        # Use JQL search (works with standard scopes)
        jql = f"project = {repo_config.jira.project_key}"
        if status_filter:
            jql += f' AND status = "{status_filter}"'
        jql += " ORDER BY updated DESC"
        tickets = await jira_client.search_issues(
            jql=jql,
            max_results=limit,
            fields=["summary", "status", "issuetype", "priority", "assignee"],
        )

        if not tickets:
            print("No tickets found.")
            return 0

        # Interactive mode: use questionary for selection
        if interactive:
            return await _interactive_ticket_selection(tickets, config_path, settings, repo_config)

        # Non-interactive: just print the table
        print(f"{'Key':<12} {'Status':<20} {'Type':<12} {'Summary'}")
        print("-" * 80)

        for ticket in tickets:
            key = ticket.get("key", "")
            fields = ticket.get("fields", {})
            status = fields.get("status", {}).get("name", "Unknown")
            issue_type = fields.get("issuetype", {}).get("name", "Unknown")
            summary = fields.get("summary", "")

            # Truncate summary if too long
            if len(summary) > 40:
                summary = summary[:37] + "..."

            print(f"{key:<12} {status:<20} {issue_type:<12} {summary}")

        print()
        print(f"Total: {len(tickets)} tickets")
        print()
        print("Tip: Use --interactive to browse and select a ticket to process")

    except Exception as e:
        print(f"Error fetching tickets: {e}")
        return 1

    return 0


async def _interactive_ticket_selection(
    tickets: list,
    config_path: str,
    settings,
    repo_config,
) -> int:
    """Interactive ticket selection with arrow keys."""
    import questionary
    from questionary import Style

    from .agent import JiraAgent

    # Custom style for the selection
    custom_style = Style([
        ("qmark", "fg:cyan bold"),
        ("question", "fg:white bold"),
        ("answer", "fg:green bold"),
        ("pointer", "fg:cyan bold"),
        ("highlighted", "fg:cyan bold"),
        ("selected", "fg:green"),
    ])

    # Build choices with ticket info
    choices = []
    for ticket in tickets:
        key = ticket.get("key", "")
        fields = ticket.get("fields", {})
        status = fields.get("status", {}).get("name", "Unknown")
        issue_type = fields.get("issuetype", {}).get("name", "Unknown")
        summary = fields.get("summary", "")

        # Truncate summary
        if len(summary) > 45:
            summary = summary[:42] + "..."

        # Format: KEY [Status] Summary
        label = f"{key:<12} [{status:<15}] {summary}"
        choices.append(questionary.Choice(title=label, value=ticket))

    # Add cancel option
    choices.append(questionary.Choice(title="Cancel", value=None))

    # Show selection prompt
    print(f"Found {len(tickets)} tickets. Use arrow keys to navigate, Enter to select:\n")

    selected = questionary.select(
        "Select a ticket to process:",
        choices=choices,
        style=custom_style,
        use_shortcuts=False,
        use_arrow_keys=True,
    ).ask()

    if selected is None:
        print("Cancelled.")
        return 0

    ticket_key = selected.get("key")
    fields = selected.get("fields", {})
    summary = fields.get("summary", "")
    status = fields.get("status", {}).get("name", "Unknown")

    print()
    print(f"Selected: {ticket_key}")
    print(f"Summary:  {summary}")
    print(f"Status:   {status}")
    print()

    # Ask what to do
    action = questionary.select(
        "What would you like to do?",
        choices=[
            questionary.Choice(title="Process this ticket (create PR)", value="process"),
            questionary.Choice(title="Process with dry-run (preview only)", value="dry-run"),
            questionary.Choice(title="View ticket details", value="details"),
            questionary.Choice(title="Cancel", value="cancel"),
        ],
        style=custom_style,
    ).ask()

    if action == "cancel" or action is None:
        print("Cancelled.")
        return 0

    if action == "details":
        # Show full ticket details
        print()
        print("=" * 60)
        print(f"Ticket: {ticket_key}")
        print("=" * 60)
        print(f"Summary:  {summary}")
        print(f"Type:     {fields.get('issuetype', {}).get('name', 'Unknown')}")
        print(f"Status:   {status}")
        print(f"Priority: {fields.get('priority', {}).get('name', 'Unknown')}")
        assignee = fields.get("assignee")
        print(f"Assignee: {assignee.get('displayName') if assignee else 'Unassigned'}")
        print()
        print("To process this ticket, run:")
        print(f"  jira-agent process-ticket {ticket_key} --config {config_path}")
        return 0

    # Process the ticket
    dry_run = action == "dry-run"

    if dry_run:
        print("Starting dry-run (no changes will be made)...")
    else:
        # Confirm before processing
        confirm = questionary.confirm(
            f"Process {ticket_key} and create a PR?",
            default=True,
            style=custom_style,
        ).ask()

        if not confirm:
            print("Cancelled.")
            return 0

        print(f"Processing {ticket_key}...")

    print()

    agent = JiraAgent(settings, repo_config, dry_run=dry_run)
    result = await agent.process_single_ticket(ticket_key)

    status_icon = "✓" if result["status"] == "completed" else "○" if result["status"] == "skipped" else "✗"
    print(f"{status_icon} {result['ticket']}: {result['status']}")
    if result.get("pr_url"):
        print(f"  PR: {result['pr_url']}")
    if result.get("error"):
        print(f"  Error: {result['error']}")

    return 0 if result["status"] in ("completed", "skipped") else 1


async def handle_list_prs(args: dict, settings) -> int:
    """List PRs for the repository."""
    import re

    from .clients.github_client import GitHubClient
    from .repo_config.loader import ConfigLoader

    config_path = args["--config"]
    state = args["--state"] or "open"

    if not config_path:
        print("Error: --config must be specified")
        return 1

    loader = ConfigLoader()
    repo_config = loader.load_from_file(config_path)

    if not settings.has_github_token:
        print("Error: GitHub token not configured")
        return 1

    github = GitHubClient(
        settings.github_token,
        repo_config.repo.owner,
        repo_config.repo.name,
    )

    print(f"Fetching {state} PRs from {repo_config.full_repo_name}...")
    print()

    try:
        prs = await github.list_pull_requests(state=state)

        if not prs:
            print("No PRs found.")
            return 0

        print(f"{'#':<6} {'State':<8} {'Ticket':<12} {'Title'}")
        print("-" * 80)

        ticket_pattern = rf"\b({re.escape(repo_config.jira.project_key)}-\d+)\b"

        for pr in prs:
            number = pr.get("number", "")
            pr_state = pr.get("state", "")
            title = pr.get("title", "")
            merged = pr.get("merged_at") is not None

            # Extract ticket from title or branch
            branch = pr.get("head", {}).get("ref", "")
            match = re.search(ticket_pattern, f"{title} {branch}", re.IGNORECASE)
            ticket = match.group(1).upper() if match else "-"

            if merged:
                pr_state = "merged"

            # Truncate title
            if len(title) > 45:
                title = title[:42] + "..."

            print(f"#{number:<5} {pr_state:<8} {ticket:<12} {title}")

        print()
        print(f"Total: {len(prs)} PRs")

    except Exception as e:
        print(f"Error fetching PRs: {e}")
        return 1
    finally:
        await github.close()

    return 0


async def handle_watch(args: dict, settings) -> int:
    """Watch for trigger status tickets and merged PRs."""
    import re
    from datetime import datetime, timezone

    from .agent import JiraAgent
    from .auth import AuthManager
    from .clients.github_client import GitHubClient
    from .clients.jira_client import JiraClient
    from .repo_config.loader import ConfigLoader

    config_path = args["--config"]
    interval = int(args["--interval"] or 60)

    if not config_path:
        print("Error: --config must be specified")
        return 1

    loader = ConfigLoader()
    repo_config = loader.load_from_file(config_path)

    if not settings.has_github_token:
        print("Error: GitHub token not configured")
        return 1

    auth_manager = AuthManager(settings)
    if not auth_manager.jira.is_authenticated():
        print("Error: Not authenticated with Jira. Run: jira-agent auth login --service=jira")
        return 1

    print(f"Watching {repo_config.full_repo_name}...", flush=True)
    print(f"Polling interval: {interval} seconds", flush=True)
    print(f"Jira project: {repo_config.jira.project_key}", flush=True)
    print(f"Trigger status: \"{repo_config.agent.status}\"", flush=True)
    print(f"Done status: \"{repo_config.agent.done_status}\"", flush=True)
    print(flush=True)
    print("Press Ctrl+C to stop", flush=True)
    print("-" * 50, flush=True)

    # Track processed items to avoid duplicates
    processed_prs: set[int] = set()
    processing_tickets: set[str] = set()  # Tickets currently being processed
    ticket_pattern = rf"\b({re.escape(repo_config.jira.project_key)}-\d+)\b"

    # Initialize agent
    agent = JiraAgent(settings, repo_config)

    def timestamp() -> str:
        return datetime.now(timezone.utc).strftime("%H:%M:%S")

    try:
        while True:
            try:
                # === Poll Jira for tickets in trigger status ===
                access_token = auth_manager.jira.get_access_token()
                cloud_id = auth_manager.jira.get_cloud_id()
                jira = JiraClient(cloud_id, access_token)

                jql = f'project = {repo_config.jira.project_key} AND status = "{repo_config.agent.status}"'
                tickets = await jira.search_issues(jql, max_results=10)

                for ticket in tickets:
                    ticket_key = ticket.get("key")

                    # Skip if already processing
                    if ticket_key in processing_tickets:
                        continue

                    print(f"[{timestamp()}] Found ticket {ticket_key} in \"{repo_config.agent.status}\"", flush=True)
                    processing_tickets.add(ticket_key)

                    # Process ticket (this creates a PR)
                    print(f"[{timestamp()}] Processing {ticket_key}...", flush=True)
                    result = await agent.process_single_ticket(ticket_key)

                    if result.get("status") == "completed":
                        print(f"[{timestamp()}] ✓ {ticket_key} -> PR created: {result.get('pr_url', 'N/A')}", flush=True)
                    elif result.get("status") == "skipped":
                        print(f"[{timestamp()}] ○ {ticket_key} skipped: {result.get('reason', 'N/A')}", flush=True)
                        processing_tickets.discard(ticket_key)
                    else:
                        print(f"[{timestamp()}] ✗ {ticket_key} failed: {result.get('error', 'Unknown error')}", flush=True)
                        processing_tickets.discard(ticket_key)

                await jira.close()

                # === Poll GitHub for merged PRs ===
                github = GitHubClient(
                    settings.github_token,
                    repo_config.repo.owner,
                    repo_config.repo.name,
                )

                prs = await github.list_pull_requests(state="closed")

                for pr in prs:
                    pr_number = pr.get("number")
                    merged_at = pr.get("merged_at")

                    # Skip if not merged or already processed
                    if not merged_at or pr_number in processed_prs:
                        continue

                    # Extract ticket key
                    title = pr.get("title", "")
                    branch = pr.get("head", {}).get("ref", "")
                    match = re.search(ticket_pattern, f"{title} {branch}", re.IGNORECASE)

                    if not match:
                        processed_prs.add(pr_number)
                        continue

                    ticket_key = match.group(1).upper()

                    print(f"[{timestamp()}] PR #{pr_number} merged -> transitioning {ticket_key} to \"{repo_config.agent.done_status}\"", flush=True)

                    # Transition ticket to done
                    result = await agent.transition_ticket_to_done(ticket_key)

                    if result.get("success"):
                        print(f"[{timestamp()}] ✓ {ticket_key} transitioned to {result.get('transition', 'Done')}", flush=True)
                        processing_tickets.discard(ticket_key)
                    else:
                        print(f"[{timestamp()}] ✗ Failed to transition {ticket_key}: {result.get('error')}", flush=True)

                    processed_prs.add(pr_number)

                await github.close()

            except Exception as e:
                print(f"[{timestamp()}] Error during poll: {e}", flush=True)

            # Wait for next poll
            await asyncio.sleep(interval)

    except KeyboardInterrupt:
        print("\nStopping watch...", flush=True)
        await agent.close()
        return 0


async def handle_process(args: dict, settings) -> int:
    """Process tickets from a Jira board."""
    from .agent import JiraAgent
    from .repo_config.loader import ConfigLoader

    config_path = args["--config"]
    repo_name = args["--repo"]
    status_filter = args["--status"]
    limit = int(args["--limit"])
    dry_run = args["--dry-run"]

    if not config_path and not repo_name:
        print("Error: Either --config or --repo must be specified")
        return 1

    loader = ConfigLoader()
    if config_path:
        repo_config = loader.load_from_file(config_path)
    else:
        repo_config = loader.load_for_repo(repo_name)

    agent = JiraAgent(settings, repo_config, dry_run=dry_run)
    results = await agent.process_tickets(status_filter=status_filter, limit=limit)

    print(f"\nProcessed {len(results)} tickets:")
    for result in results:
        status_icon = "✓" if result["status"] == "completed" else "○" if result["status"] == "skipped" else "✗"
        print(f"  {status_icon} {result['ticket']}: {result['status']}")
        if result.get("pr_url"):
            print(f"    PR: {result['pr_url']}")
        if result.get("error"):
            print(f"    Error: {result['error']}")

    return 0


async def handle_process_ticket(args: dict, settings) -> int:
    """Process a single ticket."""
    from .agent import JiraAgent
    from .repo_config.loader import ConfigLoader

    ticket_key = args["<ticket_key>"]
    config_path = args["--config"]
    repo_name = args["--repo"]
    dry_run = args["--dry-run"]

    if not config_path and not repo_name:
        print("Error: Either --config or --repo must be specified")
        return 1

    loader = ConfigLoader()
    if config_path:
        repo_config = loader.load_from_file(config_path)
    else:
        repo_config = loader.load_for_repo(repo_name)

    agent = JiraAgent(settings, repo_config, dry_run=dry_run)
    result = await agent.process_single_ticket(ticket_key)

    status_icon = "✓" if result["status"] == "completed" else "○" if result["status"] == "skipped" else "✗"
    print(f"{status_icon} {result['ticket']}: {result['status']}")
    if result.get("pr_url"):
        print(f"  PR: {result['pr_url']}")
    if result.get("error"):
        print(f"  Error: {result['error']}")

    return 0 if result["status"] in ("completed", "skipped") else 1


async def handle_check_pr(args: dict, settings) -> int:
    """Check PR status."""
    from .agent import JiraAgent
    from .repo_config.loader import ConfigLoader

    pr_number = int(args["<pr_number>"])
    config_path = args["--config"]
    repo_name = args["--repo"]

    if not config_path and not repo_name:
        print("Error: Either --config or --repo must be specified")
        return 1

    loader = ConfigLoader()
    if config_path:
        repo_config = loader.load_from_file(config_path)
    else:
        repo_config = loader.load_for_repo(repo_name)

    agent = JiraAgent(settings, repo_config)
    status = await agent.check_pr_status(pr_number)

    print(f"PR #{pr_number} Status:")
    print(f"  State: {status.get('state', 'unknown')}")
    print(f"  Mergeable: {status.get('mergeable', 'unknown')}")
    print(f"  CI Status: {status.get('ci_status', 'unknown')}")
    if status.get("pending_reviews"):
        print(f"  Pending Reviews: {len(status['pending_reviews'])}")
    if status.get("failed_checks"):
        print(f"  Failed Checks: {', '.join(status['failed_checks'])}")

    return 0


async def handle_fix_ci(args: dict, settings) -> int:
    """Attempt to fix CI failures on a PR."""
    from .agent import JiraAgent
    from .repo_config.loader import ConfigLoader

    pr_number = int(args["<pr_number>"])
    config_path = args["--config"]
    repo_name = args["--repo"]

    if not config_path and not repo_name:
        print("Error: Either --config or --repo must be specified")
        return 1

    loader = ConfigLoader()
    if config_path:
        repo_config = loader.load_from_file(config_path)
    else:
        repo_config = loader.load_for_repo(repo_name)

    agent = JiraAgent(settings, repo_config)
    result = await agent.fix_ci_failures(pr_number)

    if result["fixed"]:
        print(f"✓ CI issues fixed for PR #{pr_number}")
        if result.get("commit_sha"):
            print(f"  New commit: {result['commit_sha']}")
    else:
        print(f"✗ Could not fix CI issues for PR #{pr_number}")
        if result.get("error"):
            print(f"  Error: {result['error']}")

    return 0 if result["fixed"] else 1


def handle_serve(args: dict, settings) -> int:
    """Start the webhook server."""
    from .triggers.server import run_server

    port = int(args["--port"])
    host = args["--host"]
    config_dir = Path(args["--config-dir"])

    print(f"Starting webhook server on {host}:{port}")
    print(f"Config directory: {config_dir}")
    run_server(host=host, port=port, config_dir=config_dir, settings=settings)
    return 0


def handle_init_config(args: dict, settings) -> int:
    """Generate a config file for a new repository."""
    repo = args["<repo>"]
    output_path = args["--output"]

    if "/" not in repo:
        print("Error: Repository must be in owner/name format (e.g., acme/data)")
        return 1

    owner, name = repo.split("/", 1)

    if not output_path:
        output_path = f"configs/{owner}-{name}.yaml"

    template = f"""# Configuration for {repo}
repo:
  owner: "{owner}"
  name: "{name}"
  default_branch: "main"
  pr_target_branch: "main"

jira:
  base_url: "https://your-org.atlassian.net"
  project_key: "PROJ"
  board_id: null  # Set your board ID

branching:
  pattern: "{{type}}/{{ticket_key}}-{{description}}"
  types:
    feature: "feat"
    bugfix: "fix"
    refactor: "refactor"

pull_request:
  title_pattern: "{{type}}({{scope}}): {{description}} ({{ticket_key}})"
  template_path: ".github/PULL_REQUEST_TEMPLATE.md"
  contributing_path: ".github/CONTRIBUTING.md"

commits:
  style: "conventional"
  scope_required: false
  ticket_in_message: true

skip:
  comment_phrase: "[AGENT-SKIP]"
  labels:
    - "no-automation"
    - "manual-only"

dbt:
  enabled: false
  projects: []

databricks:
  enabled: false

ci:
  system: "github_actions"
  auto_fix:
    - "pre-commit"
"""

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(template)

    print(f"Generated config at: {output_path}")
    print("Please edit the file to customize for your repository.")
    return 0


async def handle_health(args: dict, settings) -> int:
    """Test all service connections."""
    import httpx
    from anthropic import Anthropic

    from .auth import AuthManager

    print("Health Check")
    print("=" * 50)

    all_ok = True
    config_path = args.get("--config")
    repo_config = None

    # Load repo config if provided
    if config_path:
        from .repo_config.loader import ConfigLoader

        try:
            loader = ConfigLoader()
            repo_config = loader.load_from_file(config_path)
            print(f"Config: {repo_config.full_repo_name}")
        except Exception as e:
            print(f"Config: FAILED - {e}")
            all_ok = False

    print()

    # Test Anthropic API
    print("Anthropic API:")
    if settings.has_anthropic_key:
        try:
            client = Anthropic(api_key=settings.anthropic_api_key)
            # Make a minimal API call to verify the key
            response = client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=10,
                messages=[{"role": "user", "content": "Say OK"}],
            )
            print(f"  Status: OK")
            print(f"  Model configured: {settings.claude_model}")
        except Exception as e:
            print(f"  Status: FAILED - {e}")
            all_ok = False
    else:
        print("  Status: NOT CONFIGURED (ANTHROPIC_API_KEY not set)")
        all_ok = False

    print()

    # Test Jira connection
    print("Jira:")
    auth_manager = AuthManager(settings)
    jira_token = auth_manager.jira.get_access_token() if auth_manager.jira.is_authenticated() else None
    if jira_token:
        try:
            async with httpx.AsyncClient() as client:
                # Get accessible resources to find cloud ID
                response = await client.get(
                    "https://api.atlassian.com/oauth/token/accessible-resources",
                    headers={"Authorization": f"Bearer {jira_token}"},
                )
                if response.status_code == 200:
                    resources = response.json()
                    if resources:
                        print(f"  Status: OK")
                        print(f"  Accessible sites: {len(resources)}")
                        for r in resources[:3]:  # Show up to 3
                            print(f"    - {r.get('name', 'Unknown')} ({r.get('url', '')})")

                        # If we have a config, test access to the specific project
                        if repo_config and repo_config.jira.project_key:
                            cloud_id = resources[0]["id"]
                            project_response = await client.get(
                                f"https://api.atlassian.com/ex/jira/{cloud_id}/rest/api/3/project/{repo_config.jira.project_key}",
                                headers={"Authorization": f"Bearer {jira_token}"},
                            )
                            if project_response.status_code == 200:
                                project = project_response.json()
                                print(f"  Project {repo_config.jira.project_key}: OK ({project.get('name', '')})")
                            else:
                                print(f"  Project {repo_config.jira.project_key}: FAILED (status {project_response.status_code})")
                                all_ok = False
                    else:
                        print(f"  Status: WARNING - No accessible Jira sites")
                else:
                    print(f"  Status: FAILED - Token invalid or expired (status {response.status_code})")
                    all_ok = False
        except Exception as e:
            print(f"  Status: FAILED - {e}")
            all_ok = False
    else:
        print("  Status: NOT AUTHENTICATED")
        print("  Run: jira-agent auth login --service=jira")
        all_ok = False

    print()

    # Test GitHub connection
    print("GitHub:")
    if settings.has_github_token:
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    "https://api.github.com/user",
                    headers={
                        "Authorization": f"Bearer {settings.github_token}",
                        "Accept": "application/vnd.github.v3+json",
                    },
                )
                if response.status_code == 200:
                    user = response.json()
                    print(f"  Status: OK")
                    print(f"  User: {user.get('login', 'Unknown')}")

                    # If we have a config, test access to the repo
                    if repo_config:
                        repo_response = await client.get(
                            f"https://api.github.com/repos/{repo_config.repo.owner}/{repo_config.repo.name}",
                            headers={
                                "Authorization": f"Bearer {settings.github_token}",
                                "Accept": "application/vnd.github.v3+json",
                            },
                        )
                        if repo_response.status_code == 200:
                            repo = repo_response.json()
                            perms = repo.get("permissions", {})
                            print(f"  Repo {repo_config.full_repo_name}: OK")
                            print(f"    Push access: {'Yes' if perms.get('push') else 'No'}")
                        else:
                            print(f"  Repo {repo_config.full_repo_name}: FAILED (status {repo_response.status_code})")
                            all_ok = False
                else:
                    print(f"  Status: FAILED - Token invalid (status {response.status_code})")
                    all_ok = False
        except Exception as e:
            print(f"  Status: FAILED - {e}")
            all_ok = False
    else:
        print("  Status: NOT CONFIGURED")
        print("  Either run 'gh auth login' or set JIRA_AGENT_GITHUB_TOKEN")
        all_ok = False

    print()

    # Test Databricks connection (optional)
    print("Databricks:")
    if settings.has_databricks:
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{settings.databricks_host}/api/2.0/clusters/list",
                    headers={"Authorization": f"Bearer {settings.databricks_token}"},
                )
                if response.status_code == 200:
                    print(f"  Status: OK")
                    print(f"  Host: {settings.databricks_host}")
                else:
                    print(f"  Status: FAILED - (status {response.status_code})")
                    all_ok = False
        except Exception as e:
            print(f"  Status: FAILED - {e}")
            all_ok = False
    else:
        print("  Status: NOT CONFIGURED (optional)")

    print()
    print("=" * 50)
    if all_ok:
        print("All required services are healthy!")
        return 0
    else:
        print("Some services have issues. Please fix them before using the agent.")
        return 1


def handle_learn(args: dict, settings) -> int:
    """Handle learn commands."""
    if args["status"]:
        return handle_learn_status(args, settings)
    elif args["publish"]:
        return handle_learn_publish(args, settings)
    elif args["list"]:
        return handle_learn_list(args, settings)
    return 1


def handle_learn_status(args: dict, settings) -> int:
    """Show pending learnings in workspace."""
    from .learning import LearningStorage

    storage = LearningStorage(settings.workspace_dir)
    learnings = storage.collect_from_workspace()

    if not learnings:
        print("No pending learnings found in workspace.")
        print(f"Workspace: {settings.workspace_dir}")
        return 0

    print(f"Found {len(learnings)} pending learnings:")
    print("-" * 60)

    # Group by repo
    by_repo: dict[str, list] = {}
    for learning in learnings:
        by_repo.setdefault(learning.repo, []).append(learning)

    for repo, repo_learnings in sorted(by_repo.items()):
        print(f"\n{repo}:")
        for learning in repo_learnings:
            print(f"  - [{learning.category.value}] {learning.title}")
            print(f"    Ticket: {learning.ticket}, Subcategory: {learning.subcategory}")

    print()
    print(f"Run 'jira-agent learn publish' to create a PR with these learnings.")
    return 0


def handle_learn_publish(args: dict, settings) -> int:
    """Publish learnings to jira-agent repo."""
    from .learning import LearningPublisher

    dry_run = args.get("--dry-run", False)
    jira_agent_repo = args.get("--jira-agent-repo") or getattr(
        settings, "jira_agent_repo", "djayatillake/jira-agent"
    )

    if not settings.has_github_token:
        print("Error: GitHub token not configured")
        print("Either run 'gh auth login' or set JIRA_AGENT_GITHUB_TOKEN")
        return 1

    print(f"Publishing learnings to {jira_agent_repo}...")
    if dry_run:
        print("(dry-run mode)")
    print()

    publisher = LearningPublisher(
        github_token=settings.github_token,
        jira_agent_repo=jira_agent_repo,
        workspace_dir=settings.workspace_dir,
    )

    result = publisher.publish(dry_run=dry_run)

    if result["status"] == "no_learnings":
        print("No learnings to publish.")
        return 0

    if result["status"] == "all_duplicates":
        print("All learnings already exist in knowledge base.")
        return 0

    if result["status"] == "dry_run":
        print(f"Would publish {result['learnings_count']} learnings:")
        for file_path in result.get("files_to_create", []):
            print(f"  - {file_path}")
        return 0

    if result["status"] == "success":
        print(f"Successfully published {result['learnings_count']} learnings!")
        print(f"PR: {result['pr_url']}")
        return 0

    print(f"Failed to publish: {result.get('message', 'Unknown error')}")
    return 1


def handle_learn_list(args: dict, settings) -> int:
    """List learnings in the knowledge base."""
    from pathlib import Path

    from .learning import LearningCategory
    from .learning.publisher import CATEGORY_DIRS, KNOWLEDGE_BASE_DIR
    from .learning.storage import LearningStorage

    category_filter = args.get("--category")

    # Try to find knowledge base in current directory or jira-agent clone
    kb_paths = [
        Path.cwd() / KNOWLEDGE_BASE_DIR,
        settings.workspace_dir / "djayatillake-jira-agent" / KNOWLEDGE_BASE_DIR,
        Path(__file__).parent.parent / KNOWLEDGE_BASE_DIR,
    ]

    kb_path = None
    for path in kb_paths:
        if path.exists():
            kb_path = path
            break

    if not kb_path:
        print("Knowledge base not found.")
        print("Searched in:")
        for path in kb_paths:
            print(f"  - {path}")
        return 1

    print(f"Knowledge base: {kb_path}")
    print("-" * 60)

    storage = LearningStorage()
    total_count = 0

    for category, dir_name in CATEGORY_DIRS.items():
        if category_filter and category.value != category_filter:
            continue

        cat_path = kb_path / dir_name
        if not cat_path.exists():
            continue

        md_files = list(cat_path.glob("*.md"))
        md_files = [f for f in md_files if f.name != "README.md"]

        if not md_files:
            continue

        print(f"\n{category.value} ({len(md_files)} learnings):")

        for md_file in sorted(md_files)[:10]:  # Show first 10
            learning = storage.parse_markdown(md_file)
            if learning:
                print(f"  - {learning.title}")
                print(f"    {learning.subcategory} | {learning.ticket}")

        if len(md_files) > 10:
            print(f"  ... and {len(md_files) - 10} more")

        total_count += len(md_files)

    if total_count == 0:
        print("\nNo learnings found in knowledge base.")
    else:
        print(f"\nTotal: {total_count} learnings")

    return 0


if __name__ == "__main__":
    sys.exit(main())
