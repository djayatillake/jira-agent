"""Parse and check repository requirements."""

import json
import logging
import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class Requirement:
    """A package requirement."""

    name: str
    version_spec: str | None = None
    installed: bool = False
    installed_version: str | None = None
    source: str = ""  # e.g., "requirements.txt", "pyproject.toml"


@dataclass
class RepoRequirements:
    """Requirements detected from a repository."""

    python_packages: list[Requirement] = field(default_factory=list)
    node_packages: list[Requirement] = field(default_factory=list)
    system_packages: list[str] = field(default_factory=list)
    setup_commands: list[str] = field(default_factory=list)

    @property
    def has_python(self) -> bool:
        """Check if repo has Python requirements."""
        return len(self.python_packages) > 0

    @property
    def has_node(self) -> bool:
        """Check if repo has Node.js requirements."""
        return len(self.node_packages) > 0


class RequirementsParser:
    """Parse requirements from various file formats."""

    def __init__(self, repo_path: Path):
        """Initialize parser.

        Args:
            repo_path: Path to the repository.
        """
        self.repo_path = repo_path

    def parse_all(self) -> RepoRequirements:
        """Parse all requirements from the repository.

        Returns:
            RepoRequirements with all detected requirements.
        """
        reqs = RepoRequirements()

        # Python requirements
        reqs.python_packages.extend(self._parse_requirements_txt())
        reqs.python_packages.extend(self._parse_pyproject_toml())
        reqs.python_packages.extend(self._parse_setup_py())

        # Node.js requirements
        reqs.node_packages.extend(self._parse_package_json())

        # Detect setup commands
        reqs.setup_commands.extend(self._detect_setup_commands())

        # Check what's installed
        self._check_installed_python(reqs.python_packages)
        self._check_installed_node(reqs.node_packages)

        return reqs

    def _parse_requirements_txt(self) -> list[Requirement]:
        """Parse requirements.txt files."""
        requirements = []

        # Check multiple possible locations
        req_files = [
            self.repo_path / "requirements.txt",
            self.repo_path / "requirements" / "base.txt",
            self.repo_path / "requirements" / "dev.txt",
            self.repo_path / "requirements-dev.txt",
        ]

        for req_file in req_files:
            if not req_file.exists():
                continue

            source = str(req_file.relative_to(self.repo_path))
            content = req_file.read_text()

            for line in content.split("\n"):
                line = line.strip()

                # Skip comments and empty lines
                if not line or line.startswith("#"):
                    continue

                # Skip -r includes
                if line.startswith("-r") or line.startswith("--"):
                    continue

                # Parse package name and version
                req = self._parse_requirement_line(line, source)
                if req:
                    requirements.append(req)

        return requirements

    def _parse_pyproject_toml(self) -> list[Requirement]:
        """Parse pyproject.toml for dependencies."""
        requirements = []
        pyproject_path = self.repo_path / "pyproject.toml"

        if not pyproject_path.exists():
            return requirements

        try:
            import tomllib
        except ImportError:
            try:
                import tomli as tomllib
            except ImportError:
                logger.debug("tomllib/tomli not available, skipping pyproject.toml")
                return requirements

        try:
            content = pyproject_path.read_text()
            data = tomllib.loads(content)

            # Poetry dependencies
            if "tool" in data and "poetry" in data["tool"]:
                poetry = data["tool"]["poetry"]

                for section in ["dependencies", "dev-dependencies"]:
                    if section not in poetry:
                        continue

                    for name, spec in poetry[section].items():
                        if name == "python":
                            continue

                        version_spec = None
                        if isinstance(spec, str):
                            version_spec = spec
                        elif isinstance(spec, dict):
                            version_spec = spec.get("version")

                        requirements.append(Requirement(
                            name=name,
                            version_spec=version_spec,
                            source="pyproject.toml (poetry)",
                        ))

            # PEP 621 dependencies
            if "project" in data and "dependencies" in data["project"]:
                for dep in data["project"]["dependencies"]:
                    req = self._parse_requirement_line(dep, "pyproject.toml")
                    if req:
                        requirements.append(req)

        except Exception as e:
            logger.warning(f"Failed to parse pyproject.toml: {e}")

        return requirements

    def _parse_setup_py(self) -> list[Requirement]:
        """Parse setup.py for install_requires (basic parsing)."""
        requirements = []
        setup_path = self.repo_path / "setup.py"

        if not setup_path.exists():
            return requirements

        try:
            content = setup_path.read_text()

            # Basic regex to find install_requires
            match = re.search(
                r"install_requires\s*=\s*\[(.*?)\]",
                content,
                re.DOTALL,
            )

            if match:
                deps_str = match.group(1)
                # Extract quoted strings
                deps = re.findall(r"['\"]([^'\"]+)['\"]", deps_str)

                for dep in deps:
                    req = self._parse_requirement_line(dep, "setup.py")
                    if req:
                        requirements.append(req)

        except Exception as e:
            logger.debug(f"Failed to parse setup.py: {e}")

        return requirements

    def _parse_package_json(self) -> list[Requirement]:
        """Parse package.json for Node.js dependencies."""
        requirements = []
        package_path = self.repo_path / "package.json"

        if not package_path.exists():
            return requirements

        try:
            data = json.loads(package_path.read_text())

            for section in ["dependencies", "devDependencies"]:
                if section not in data:
                    continue

                for name, version in data[section].items():
                    requirements.append(Requirement(
                        name=name,
                        version_spec=version,
                        source=f"package.json ({section})",
                    ))

        except Exception as e:
            logger.warning(f"Failed to parse package.json: {e}")

        return requirements

    def _parse_requirement_line(self, line: str, source: str) -> Requirement | None:
        """Parse a single requirement line.

        Args:
            line: Requirement line (e.g., "requests>=2.0.0").
            source: Source file name.

        Returns:
            Requirement or None if parsing fails.
        """
        line = line.strip()

        # Remove comments
        if "#" in line:
            line = line.split("#")[0].strip()

        if not line:
            return None

        # Handle extras like package[extra]
        line = re.sub(r"\[.*?\]", "", line)

        # Parse version specifier
        match = re.match(r"^([a-zA-Z0-9_-]+)\s*([<>=!~].*)?$", line)
        if match:
            name = match.group(1)
            version_spec = match.group(2)
            return Requirement(
                name=name,
                version_spec=version_spec.strip() if version_spec else None,
                source=source,
            )

        return None

    def _detect_setup_commands(self) -> list[str]:
        """Detect setup commands from repo files."""
        commands = []

        # Check for Makefile with setup/install target
        makefile = self.repo_path / "Makefile"
        if makefile.exists():
            content = makefile.read_text()
            if re.search(r"^(setup|install|init):", content, re.MULTILINE):
                commands.append("make setup")

        # Poetry
        if (self.repo_path / "pyproject.toml").exists():
            content = (self.repo_path / "pyproject.toml").read_text()
            if "[tool.poetry]" in content:
                commands.append("poetry install")

        # pip requirements
        if (self.repo_path / "requirements.txt").exists():
            commands.append("pip install -r requirements.txt")

        # npm/yarn
        if (self.repo_path / "package.json").exists():
            if (self.repo_path / "yarn.lock").exists():
                commands.append("yarn install")
            else:
                commands.append("npm install")

        # pre-commit
        if (self.repo_path / ".pre-commit-config.yaml").exists():
            commands.append("pre-commit install")

        # dbt deps
        if any(self.repo_path.glob("**/dbt_project.yml")):
            commands.append("dbt deps")

        return commands

    def _check_installed_python(self, requirements: list[Requirement]) -> None:
        """Check which Python packages are installed."""
        try:
            result = subprocess.run(
                ["pip3", "list", "--format=json"],
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode == 0:
                installed = {
                    pkg["name"].lower(): pkg["version"]
                    for pkg in json.loads(result.stdout)
                }

                for req in requirements:
                    name_lower = req.name.lower()
                    if name_lower in installed:
                        req.installed = True
                        req.installed_version = installed[name_lower]

        except Exception as e:
            logger.debug(f"Failed to check installed Python packages: {e}")

    def _check_installed_node(self, requirements: list[Requirement]) -> None:
        """Check which Node.js packages are installed."""
        node_modules = self.repo_path / "node_modules"
        if not node_modules.exists():
            return

        for req in requirements:
            pkg_path = node_modules / req.name / "package.json"
            if pkg_path.exists():
                try:
                    data = json.loads(pkg_path.read_text())
                    req.installed = True
                    req.installed_version = data.get("version")
                except Exception:
                    pass

    def get_missing_packages(self) -> tuple[list[Requirement], list[Requirement]]:
        """Get lists of missing Python and Node.js packages.

        Returns:
            Tuple of (missing_python, missing_node).
        """
        reqs = self.parse_all()

        missing_python = [r for r in reqs.python_packages if not r.installed]
        missing_node = [r for r in reqs.node_packages if not r.installed]

        return missing_python, missing_node

    def print_report(self, reqs: RepoRequirements | None = None) -> None:
        """Print a formatted requirements report."""
        if reqs is None:
            reqs = self.parse_all()

        print("Repository Requirements")
        print("=" * 50)

        if reqs.python_packages:
            print("\nPython Packages:")
            installed = [r for r in reqs.python_packages if r.installed]
            missing = [r for r in reqs.python_packages if not r.installed]

            print(f"  Installed: {len(installed)}")
            print(f"  Missing:   {len(missing)}")

            if missing:
                print("\n  Missing packages:")
                for req in missing[:10]:
                    ver = f" ({req.version_spec})" if req.version_spec else ""
                    print(f"    - {req.name}{ver}")
                if len(missing) > 10:
                    print(f"    ... and {len(missing) - 10} more")

        if reqs.node_packages:
            print("\nNode.js Packages:")
            installed = [r for r in reqs.node_packages if r.installed]
            missing = [r for r in reqs.node_packages if not r.installed]

            print(f"  Installed: {len(installed)}")
            print(f"  Missing:   {len(missing)}")

        if reqs.setup_commands:
            print("\nDetected Setup Commands:")
            for cmd in reqs.setup_commands:
                print(f"  $ {cmd}")
