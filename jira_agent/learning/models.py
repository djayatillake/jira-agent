"""Learning data models."""

import hashlib
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class LearningCategory(str, Enum):
    """Categories of learnings."""

    CI_FAILURE = "ci-failure"
    CODE_PATTERN = "code-pattern"
    ERROR_RESOLUTION = "error-resolution"


class LearningConfidence(str, Enum):
    """Confidence levels for learnings."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class FailureRecord(BaseModel):
    """Record of a failure that occurred during processing."""

    failure_type: str = Field(..., description="Type of failure (e.g., 'pre-commit', 'dbt-compile')")
    error_message: str = Field(..., description="The error message or output")
    command: str | None = Field(None, description="The command that failed")
    files_involved: list[str] = Field(default_factory=list, description="Files involved in the failure")
    iteration: int = Field(..., description="Agent loop iteration when failure occurred")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    context: dict[str, Any] = Field(default_factory=dict, description="Additional context")


class FixAttempt(BaseModel):
    """Record of an attempted fix."""

    failure_type: str = Field(..., description="Type of failure this fix targets")
    solution_description: str = Field(..., description="Description of what was done to fix")
    files_modified: list[str] = Field(default_factory=list, description="Files that were modified")
    code_changes: str | None = Field(None, description="Diff or summary of code changes")
    iteration: int = Field(..., description="Agent loop iteration when fix was attempted")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    verified: bool = Field(False, description="Whether this fix was verified to work")


class Learning(BaseModel):
    """A captured learning from a resolved failure.

    Learnings are only created when a fix has been VERIFIED to work.
    """

    id: str = Field(..., description="Unique identifier (hash of content)")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    ticket: str = Field(..., description="Jira ticket key")
    category: LearningCategory = Field(..., description="Category of the learning")
    subcategory: str = Field(..., description="Subcategory (e.g., 'pre-commit', 'dbt-compile')")
    repo: str = Field(..., description="Repository (owner/name)")
    title: str = Field(..., description="Short title describing the learning")
    problem: str = Field(..., description="Description of the problem encountered")
    error_output: str | None = Field(None, description="Original error output")
    solution: str = Field(..., description="Description of the solution")
    files_affected: list[str] = Field(default_factory=list, description="Files that were affected")
    code_diff: str | None = Field(None, description="Diff showing the fix")
    applicability: str = Field(..., description="When this learning should be applied")
    confidence: LearningConfidence = Field(
        LearningConfidence.MEDIUM, description="Confidence level"
    )

    @classmethod
    def compute_id(cls, category: str, subcategory: str, problem: str, solution: str) -> str:
        """Compute a unique ID for deduplication.

        The ID is based on the category, subcategory, and normalized
        problem/solution descriptions to avoid duplicates.
        """
        normalized = f"{category}:{subcategory}:{problem.lower().strip()}:{solution.lower().strip()}"
        return hashlib.sha256(normalized.encode()).hexdigest()[:12]

    @classmethod
    def from_verified_fix(
        cls,
        ticket: str,
        repo: str,
        failure: FailureRecord,
        fix: FixAttempt,
        title: str,
        applicability: str,
        confidence: LearningConfidence = LearningConfidence.MEDIUM,
    ) -> "Learning":
        """Create a Learning from a verified fix.

        Args:
            ticket: Jira ticket key
            repo: Repository name (owner/name)
            failure: The original failure record
            fix: The verified fix attempt
            title: Short title for the learning
            applicability: When this learning should be applied
            confidence: Confidence level

        Returns:
            A new Learning instance
        """
        # Determine category from failure type
        category = cls._categorize_failure(failure.failure_type)

        learning_id = cls.compute_id(
            category.value,
            failure.failure_type,
            failure.error_message,
            fix.solution_description,
        )

        return cls(
            id=learning_id,
            ticket=ticket,
            category=category,
            subcategory=failure.failure_type,
            repo=repo,
            title=title,
            problem=failure.error_message,
            error_output=failure.error_message,
            solution=fix.solution_description,
            files_affected=list(set(failure.files_involved + fix.files_modified)),
            code_diff=fix.code_changes,
            applicability=applicability,
            confidence=confidence,
        )

    @staticmethod
    def _categorize_failure(failure_type: str) -> LearningCategory:
        """Categorize a failure type into a learning category."""
        ci_types = {"pre-commit", "dbt-compile", "pytest", "mypy", "ruff", "black", "isort"}
        pattern_types = {"dbt-model", "sql-pattern", "python-pattern"}

        if failure_type.lower() in ci_types:
            return LearningCategory.CI_FAILURE
        elif failure_type.lower() in pattern_types:
            return LearningCategory.CODE_PATTERN
        else:
            return LearningCategory.ERROR_RESOLUTION
