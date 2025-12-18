"""Track PRs created by the agent for monitoring."""

import json
import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Default location for PR tracking data
DEFAULT_TRACKER_PATH = Path.home() / ".jirade" / "pr_tracker.json"


@dataclass
class TrackedPR:
    """A PR created by the agent that may need attention."""

    pr_number: int
    pr_url: str
    repo: str  # owner/name
    ticket_key: str
    branch: str
    created_at: str
    last_checked: str | None = None
    status: str = "open"  # open, merged, closed, needs_attention
    ci_status: str = "pending"  # pending, success, failure
    has_feedback: bool = False
    feedback_addressed: bool = False


@dataclass
class PRTracker:
    """Tracks PRs created by the agent."""

    prs: dict[str, TrackedPR] = field(default_factory=dict)  # key: "owner/repo#number"
    tracker_path: Path = field(default_factory=lambda: DEFAULT_TRACKER_PATH)

    def __post_init__(self):
        self._load()

    def _load(self) -> None:
        """Load tracked PRs from disk."""
        if self.tracker_path.exists():
            try:
                data = json.loads(self.tracker_path.read_text())
                for key, pr_data in data.get("prs", {}).items():
                    self.prs[key] = TrackedPR(**pr_data)
            except Exception as e:
                logger.warning(f"Failed to load PR tracker: {e}")

    def _save(self) -> None:
        """Save tracked PRs to disk."""
        self.tracker_path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "prs": {key: asdict(pr) for key, pr in self.prs.items()},
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        self.tracker_path.write_text(json.dumps(data, indent=2))

    def _key(self, repo: str, pr_number: int) -> str:
        """Generate key for a PR."""
        return f"{repo}#{pr_number}"

    def add_pr(
        self,
        pr_number: int,
        pr_url: str,
        repo: str,
        ticket_key: str,
        branch: str,
    ) -> TrackedPR:
        """Add a new PR to track.

        Args:
            pr_number: PR number.
            pr_url: Full PR URL.
            repo: Repository (owner/name).
            ticket_key: Jira ticket key.
            branch: Branch name.

        Returns:
            The tracked PR.
        """
        key = self._key(repo, pr_number)
        pr = TrackedPR(
            pr_number=pr_number,
            pr_url=pr_url,
            repo=repo,
            ticket_key=ticket_key,
            branch=branch,
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        self.prs[key] = pr
        self._save()
        logger.info(f"Tracking PR #{pr_number} for {ticket_key}")
        return pr

    def update_pr(
        self,
        repo: str,
        pr_number: int,
        **updates: Any,
    ) -> TrackedPR | None:
        """Update a tracked PR.

        Args:
            repo: Repository (owner/name).
            pr_number: PR number.
            **updates: Fields to update.

        Returns:
            Updated PR or None if not found.
        """
        key = self._key(repo, pr_number)
        pr = self.prs.get(key)
        if not pr:
            return None

        for field_name, value in updates.items():
            if hasattr(pr, field_name):
                setattr(pr, field_name, value)

        pr.last_checked = datetime.now(timezone.utc).isoformat()
        self._save()
        return pr

    def get_pr(self, repo: str, pr_number: int) -> TrackedPR | None:
        """Get a tracked PR."""
        return self.prs.get(self._key(repo, pr_number))

    def get_open_prs(self, repo: str | None = None) -> list[TrackedPR]:
        """Get all open PRs, optionally filtered by repo.

        Args:
            repo: Optional repo filter (owner/name).

        Returns:
            List of open tracked PRs.
        """
        result = []
        for pr in self.prs.values():
            if pr.status == "open":
                if repo is None or pr.repo == repo:
                    result.append(pr)
        return result

    def get_prs_needing_attention(self, repo: str | None = None) -> list[TrackedPR]:
        """Get PRs that need attention (CI failed or has unaddressed feedback).

        Args:
            repo: Optional repo filter.

        Returns:
            List of PRs needing attention.
        """
        result = []
        for pr in self.prs.values():
            if pr.status != "open":
                continue
            if repo and pr.repo != repo:
                continue

            needs_attention = (
                pr.ci_status == "failure"
                or (pr.has_feedback and not pr.feedback_addressed)
            )
            if needs_attention:
                result.append(pr)

        return result

    def remove_pr(self, repo: str, pr_number: int) -> bool:
        """Remove a PR from tracking.

        Args:
            repo: Repository (owner/name).
            pr_number: PR number.

        Returns:
            True if removed, False if not found.
        """
        key = self._key(repo, pr_number)
        if key in self.prs:
            del self.prs[key]
            self._save()
            return True
        return False

    def cleanup_closed(self) -> int:
        """Remove closed/merged PRs from tracking.

        Returns:
            Number of PRs removed.
        """
        to_remove = [
            key for key, pr in self.prs.items()
            if pr.status in ("merged", "closed")
        ]
        for key in to_remove:
            del self.prs[key]
        if to_remove:
            self._save()
        return len(to_remove)
