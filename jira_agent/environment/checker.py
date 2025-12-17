"""Environment checker for system tools and dependencies."""

import logging
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class ToolCheck:
    """Result of checking a tool."""

    name: str
    required: bool
    installed: bool
    version: str | None = None
    path: str | None = None
    install_hint: str | None = None


@dataclass
class EnvironmentReport:
    """Report of environment checks."""

    tools: list[ToolCheck] = field(default_factory=list)
    missing_required: list[str] = field(default_factory=list)
    missing_optional: list[str] = field(default_factory=list)

    @property
    def is_ready(self) -> bool:
        """Check if environment is ready (all required tools present)."""
        return len(self.missing_required) == 0

    def summary(self) -> str:
        """Get a summary of the environment status."""
        lines = []

        if self.is_ready:
            lines.append("Environment is ready.")
        else:
            lines.append("Environment is NOT ready.")
            lines.append(f"Missing required tools: {', '.join(self.missing_required)}")

        if self.missing_optional:
            lines.append(f"Missing optional tools: {', '.join(self.missing_optional)}")

        return "\n".join(lines)


class EnvironmentChecker:
    """Checks system environment for required tools."""

    # Common tools and how to install them
    TOOL_INFO = {
        "python": {
            "check_cmd": ["python3", "--version"],
            "version_pattern": r"Python (\d+\.\d+\.\d+)",
            "install_hint": "Install Python 3.11+ from python.org or: brew install python@3.11",
        },
        "pip": {
            "check_cmd": ["pip3", "--version"],
            "version_pattern": r"pip (\d+\.\d+)",
            "install_hint": "Usually comes with Python. Try: python3 -m ensurepip",
        },
        "poetry": {
            "check_cmd": ["poetry", "--version"],
            "version_pattern": r"Poetry.*?(\d+\.\d+\.\d+)",
            "install_hint": "Install with: curl -sSL https://install.python-poetry.org | python3 -",
        },
        "git": {
            "check_cmd": ["git", "--version"],
            "version_pattern": r"git version (\d+\.\d+\.\d+)",
            "install_hint": "Install with: brew install git",
        },
        "node": {
            "check_cmd": ["node", "--version"],
            "version_pattern": r"v(\d+\.\d+\.\d+)",
            "install_hint": "Install from nodejs.org or: brew install node",
        },
        "npm": {
            "check_cmd": ["npm", "--version"],
            "version_pattern": r"(\d+\.\d+\.\d+)",
            "install_hint": "Comes with Node.js",
        },
        "dbt": {
            "check_cmd": ["dbt", "--version"],
            "version_pattern": r"dbt.*?(\d+\.\d+\.\d+)",
            "install_hint": "Install with: pip install dbt-core dbt-databricks",
        },
        "pre-commit": {
            "check_cmd": ["pre-commit", "--version"],
            "version_pattern": r"pre-commit (\d+\.\d+\.\d+)",
            "install_hint": "Install with: pip install pre-commit",
        },
        "gh": {
            "check_cmd": ["gh", "--version"],
            "version_pattern": r"gh version (\d+\.\d+\.\d+)",
            "install_hint": "Install with: brew install gh",
        },
        "docker": {
            "check_cmd": ["docker", "--version"],
            "version_pattern": r"Docker version (\d+\.\d+\.\d+)",
            "install_hint": "Install Docker Desktop from docker.com",
        },
        "make": {
            "check_cmd": ["make", "--version"],
            "version_pattern": r"GNU Make (\d+\.\d+)",
            "install_hint": "Install with: xcode-select --install (macOS)",
        },
    }

    def __init__(self):
        """Initialize the checker."""
        pass

    def check_tool(self, name: str, required: bool = True) -> ToolCheck:
        """Check if a tool is installed.

        Args:
            name: Name of the tool.
            required: Whether the tool is required.

        Returns:
            ToolCheck with results.
        """
        info = self.TOOL_INFO.get(name, {})
        check_cmd = info.get("check_cmd", [name, "--version"])
        install_hint = info.get("install_hint")

        # Check if tool exists
        path = shutil.which(check_cmd[0])

        if not path:
            return ToolCheck(
                name=name,
                required=required,
                installed=False,
                install_hint=install_hint,
            )

        # Get version
        version = None
        try:
            result = subprocess.run(
                check_cmd,
                capture_output=True,
                text=True,
                timeout=10,
            )
            output = result.stdout + result.stderr

            import re
            pattern = info.get("version_pattern", r"(\d+\.\d+\.\d+)")
            match = re.search(pattern, output)
            if match:
                version = match.group(1)

        except (subprocess.TimeoutExpired, Exception) as e:
            logger.debug(f"Failed to get version for {name}: {e}")

        return ToolCheck(
            name=name,
            required=required,
            installed=True,
            version=version,
            path=path,
            install_hint=install_hint,
        )

    def check_all(self, tools: list[tuple[str, bool]] | None = None) -> EnvironmentReport:
        """Check multiple tools.

        Args:
            tools: List of (tool_name, required) tuples. If None, checks common tools.

        Returns:
            EnvironmentReport with all results.
        """
        if tools is None:
            # Default tools to check
            tools = [
                ("python", True),
                ("pip", True),
                ("git", True),
                ("gh", False),
                ("pre-commit", False),
            ]

        report = EnvironmentReport()

        for name, required in tools:
            check = self.check_tool(name, required)
            report.tools.append(check)

            if not check.installed:
                if required:
                    report.missing_required.append(name)
                else:
                    report.missing_optional.append(name)

        return report

    def check_for_repo(self, repo_path: Path, repo_config=None) -> EnvironmentReport:
        """Check environment for a specific repository.

        Detects what tools are needed based on repo contents and config.

        Args:
            repo_path: Path to the repository.
            repo_config: Optional RepoConfig for additional context.

        Returns:
            EnvironmentReport with results.
        """
        tools = [
            ("python", True),
            ("pip", True),
            ("git", True),
        ]

        # Check for dbt
        if repo_config and repo_config.dbt.enabled:
            tools.append(("dbt", True))
        elif (repo_path / "dbt_project.yml").exists():
            tools.append(("dbt", True))
        elif any(repo_path.glob("**/dbt_project.yml")):
            tools.append(("dbt", True))

        # Check for pre-commit
        if (repo_path / ".pre-commit-config.yaml").exists():
            tools.append(("pre-commit", True))

        # Check for Node.js projects
        if (repo_path / "package.json").exists():
            tools.append(("node", True))
            tools.append(("npm", True))

        # Check for Poetry
        if (repo_path / "pyproject.toml").exists():
            content = (repo_path / "pyproject.toml").read_text()
            if "[tool.poetry]" in content:
                tools.append(("poetry", True))

        # Check for Makefile
        if (repo_path / "Makefile").exists():
            tools.append(("make", False))

        # Check for Docker
        if (repo_path / "Dockerfile").exists() or (repo_path / "docker-compose.yml").exists():
            tools.append(("docker", False))

        return self.check_all(tools)

    def print_report(self, report: EnvironmentReport) -> None:
        """Print a formatted environment report."""
        print("Environment Check")
        print("=" * 50)

        for tool in report.tools:
            status = "✓" if tool.installed else "✗"
            req = "(required)" if tool.required else "(optional)"

            if tool.installed:
                version_str = f"v{tool.version}" if tool.version else ""
                print(f"  {status} {tool.name:<15} {version_str:<12} {req}")
            else:
                print(f"  {status} {tool.name:<15} {'NOT FOUND':<12} {req}")
                if tool.install_hint:
                    print(f"      → {tool.install_hint}")

        print()
        print(report.summary())
