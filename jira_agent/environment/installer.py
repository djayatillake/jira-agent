"""Package installer for missing dependencies."""

import logging
import subprocess
from dataclasses import dataclass
from pathlib import Path

from .requirements import Requirement, RequirementsParser

logger = logging.getLogger(__name__)


@dataclass
class InstallResult:
    """Result of an installation attempt."""

    success: bool
    package: str
    command: str
    output: str
    error: str | None = None


class PackageInstaller:
    """Install missing packages and dependencies."""

    def __init__(self, repo_path: Path | None = None, auto_confirm: bool = False):
        """Initialize installer.

        Args:
            repo_path: Path to the repository (for context-aware installs).
            auto_confirm: If True, don't prompt for confirmation.
        """
        self.repo_path = repo_path
        self.auto_confirm = auto_confirm

    def install_python_package(
        self,
        package: str,
        version_spec: str | None = None,
        use_pip: bool = True,
    ) -> InstallResult:
        """Install a Python package.

        Args:
            package: Package name.
            version_spec: Optional version specifier (e.g., ">=2.0.0").
            use_pip: If True, use pip. Otherwise tries poetry.

        Returns:
            InstallResult with outcome.
        """
        if version_spec:
            pkg_spec = f"{package}{version_spec}"
        else:
            pkg_spec = package

        if use_pip:
            cmd = ["pip3", "install", pkg_spec]
        else:
            cmd = ["poetry", "add", pkg_spec]

        return self._run_install(cmd, package)

    def install_node_package(
        self,
        package: str,
        version_spec: str | None = None,
        dev: bool = False,
    ) -> InstallResult:
        """Install a Node.js package.

        Args:
            package: Package name.
            version_spec: Optional version specifier.
            dev: If True, install as dev dependency.

        Returns:
            InstallResult with outcome.
        """
        pkg_spec = f"{package}@{version_spec}" if version_spec else package

        # Check for yarn vs npm
        if self.repo_path and (self.repo_path / "yarn.lock").exists():
            cmd = ["yarn", "add"]
            if dev:
                cmd.append("--dev")
            cmd.append(pkg_spec)
        else:
            cmd = ["npm", "install"]
            if dev:
                cmd.append("--save-dev")
            else:
                cmd.append("--save")
            cmd.append(pkg_spec)

        return self._run_install(cmd, package)

    def install_system_tool(self, tool: str) -> InstallResult:
        """Install a system tool.

        Args:
            tool: Tool name.

        Returns:
            InstallResult with outcome.
        """
        # Map tools to install commands
        install_commands = {
            "pre-commit": ["pip3", "install", "pre-commit"],
            "dbt": ["pip3", "install", "dbt-core", "dbt-databricks"],
            "poetry": ["pip3", "install", "poetry"],
            "node": ["brew", "install", "node"],
            "gh": ["brew", "install", "gh"],
            "make": ["xcode-select", "--install"],
        }

        cmd = install_commands.get(tool)
        if not cmd:
            return InstallResult(
                success=False,
                package=tool,
                command="",
                output="",
                error=f"Don't know how to install {tool}",
            )

        return self._run_install(cmd, tool)

    def install_repo_requirements(
        self,
        python: bool = True,
        node: bool = True,
        run_setup: bool = True,
    ) -> list[InstallResult]:
        """Install all requirements for a repository.

        Args:
            python: Install Python requirements.
            node: Install Node.js requirements.
            run_setup: Run detected setup commands.

        Returns:
            List of InstallResult for each operation.
        """
        if not self.repo_path:
            return [InstallResult(
                success=False,
                package="",
                command="",
                output="",
                error="No repo_path set",
            )]

        results = []
        parser = RequirementsParser(self.repo_path)
        reqs = parser.parse_all()

        # Run setup commands (usually the best approach)
        if run_setup and reqs.setup_commands:
            for cmd_str in reqs.setup_commands:
                result = self._run_setup_command(cmd_str)
                results.append(result)

                # If poetry install or pip install succeeded, skip individual packages
                if result.success and ("poetry install" in cmd_str or "pip install -r" in cmd_str):
                    python = False
                if result.success and ("npm install" in cmd_str or "yarn install" in cmd_str):
                    node = False

        # Install missing Python packages individually if needed
        if python:
            missing_python, _ = parser.get_missing_packages()
            for req in missing_python:
                if not self.auto_confirm:
                    print(f"Installing {req.name}...")

                result = self.install_python_package(req.name, req.version_spec)
                results.append(result)

        # Install missing Node packages individually if needed
        if node:
            _, missing_node = parser.get_missing_packages()
            for req in missing_node:
                if not self.auto_confirm:
                    print(f"Installing {req.name}...")

                result = self.install_node_package(req.name, req.version_spec)
                results.append(result)

        return results

    def setup_pre_commit(self) -> InstallResult:
        """Install pre-commit hooks.

        Returns:
            InstallResult with outcome.
        """
        if not self.repo_path or not (self.repo_path / ".pre-commit-config.yaml").exists():
            return InstallResult(
                success=False,
                package="pre-commit",
                command="",
                output="",
                error="No .pre-commit-config.yaml found",
            )

        return self._run_install(
            ["pre-commit", "install"],
            "pre-commit hooks",
            cwd=self.repo_path,
        )

    def _run_setup_command(self, cmd_str: str) -> InstallResult:
        """Run a setup command string.

        Args:
            cmd_str: Command string (e.g., "poetry install").

        Returns:
            InstallResult with outcome.
        """
        import shlex
        cmd = shlex.split(cmd_str)
        return self._run_install(cmd, cmd_str, cwd=self.repo_path)

    def _run_install(
        self,
        cmd: list[str],
        package: str,
        cwd: Path | None = None,
    ) -> InstallResult:
        """Run an installation command.

        Args:
            cmd: Command to run.
            package: Package name (for reporting).
            cwd: Working directory.

        Returns:
            InstallResult with outcome.
        """
        cmd_str = " ".join(cmd)
        logger.info(f"Running: {cmd_str}")

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300,  # 5 minute timeout
                cwd=cwd,
            )

            success = result.returncode == 0
            output = result.stdout

            if not success:
                logger.warning(f"Install failed: {result.stderr}")

            return InstallResult(
                success=success,
                package=package,
                command=cmd_str,
                output=output,
                error=result.stderr if not success else None,
            )

        except subprocess.TimeoutExpired:
            return InstallResult(
                success=False,
                package=package,
                command=cmd_str,
                output="",
                error="Command timed out after 5 minutes",
            )
        except FileNotFoundError:
            return InstallResult(
                success=False,
                package=package,
                command=cmd_str,
                output="",
                error=f"Command not found: {cmd[0]}",
            )
        except Exception as e:
            return InstallResult(
                success=False,
                package=package,
                command=cmd_str,
                output="",
                error=str(e),
            )


def setup_environment(
    repo_path: Path,
    auto_install: bool = False,
    verbose: bool = True,
) -> tuple[bool, list[str]]:
    """Check and optionally set up environment for a repository.

    This is a convenience function that combines checking and installing.

    Args:
        repo_path: Path to the repository.
        auto_install: If True, automatically install missing dependencies.
        verbose: If True, print progress information.

    Returns:
        Tuple of (success, list of issues/actions taken).
    """
    from .checker import EnvironmentChecker

    issues = []
    checker = EnvironmentChecker()

    # Check system tools
    if verbose:
        print("Checking system tools...")

    report = checker.check_for_repo(repo_path)

    if report.missing_required:
        issues.append(f"Missing required tools: {', '.join(report.missing_required)}")

        if auto_install:
            installer = PackageInstaller(repo_path, auto_confirm=True)
            for tool in report.missing_required:
                if verbose:
                    print(f"Installing {tool}...")
                result = installer.install_system_tool(tool)
                if not result.success:
                    issues.append(f"Failed to install {tool}: {result.error}")

    # Check repo requirements
    if verbose:
        print("Checking repository requirements...")

    parser = RequirementsParser(repo_path)
    reqs = parser.parse_all()

    missing_python, missing_node = parser.get_missing_packages()

    if missing_python or missing_node:
        if missing_python:
            issues.append(f"Missing {len(missing_python)} Python packages")
        if missing_node:
            issues.append(f"Missing {len(missing_node)} Node.js packages")

        if auto_install:
            if verbose:
                print("Installing repository dependencies...")

            installer = PackageInstaller(repo_path, auto_confirm=True)
            results = installer.install_repo_requirements()

            for result in results:
                if not result.success:
                    issues.append(f"Failed: {result.command} - {result.error}")
                elif verbose:
                    print(f"  ✓ {result.package}")

    # Final check
    success = len([i for i in issues if "Failed" in i or "Missing required" in i]) == 0

    if verbose:
        if success:
            print("\nEnvironment is ready!")
        else:
            print("\nEnvironment has issues:")
            for issue in issues:
                print(f"  - {issue}")

    return success, issues
