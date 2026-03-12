"""JSON-based storage for user feedback on AI generations."""

import json
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional


@dataclass
class SectionFeedback:
    """Feedback for a single section."""
    section_type: str
    generated_text: str
    user_feedback: str
    rating: Optional[int] = None  # 1-5
    corrected_text: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    provider_used: str = ""
    model_used: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SectionFeedback":
        """Create from dictionary."""
        return cls(**data)


@dataclass
class FeedbackEntry:
    """Complete feedback entry for an audit."""
    audit_id: str
    site_url: str
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    sections: Dict[str, SectionFeedback] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "audit_id": self.audit_id,
            "site_url": self.site_url,
            "created_at": self.created_at,
            "sections": {
                key: fb.to_dict() for key, fb in self.sections.items()
            }
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "FeedbackEntry":
        """Create from dictionary."""
        sections = {
            key: SectionFeedback.from_dict(fb_data)
            for key, fb_data in data.get("sections", {}).items()
        }
        return cls(
            audit_id=data["audit_id"],
            site_url=data["site_url"],
            created_at=data.get("created_at", datetime.now().isoformat()),
            sections=sections
        )


class FeedbackStorage:
    """JSON-based storage for feedback data."""

    def __init__(self, data_dir: Path = None):
        """Initialize storage.

        Args:
            data_dir: Directory for feedback JSON files
        """
        self.data_dir = data_dir or Path("data/feedback")
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self._file_path = self.data_dir / "feedback.json"
        self._data = self._load_data()

    def _load_data(self) -> Dict[str, Any]:
        """Load data from JSON file."""
        if self._file_path.exists():
            try:
                with open(self._file_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                return {"version": "1.0", "feedbacks": []}
        return {"version": "1.0", "feedbacks": []}

    def _save_data(self):
        """Save data to JSON file."""
        with open(self._file_path, "w", encoding="utf-8") as f:
            json.dump(self._data, f, indent=2, ensure_ascii=False)

    def add_feedback_entry(self, entry: FeedbackEntry):
        """Add a new feedback entry."""
        self._data["feedbacks"].append(entry.to_dict())
        self._save_data()

    def add_section_feedback(
        self,
        audit_id: str,
        site_url: str,
        section_key: str,
        feedback: SectionFeedback
    ):
        """Add feedback for a specific section.

        Creates a new entry if audit_id doesn't exist.
        """
        # Find existing entry
        existing = None
        for entry_data in self._data["feedbacks"]:
            if entry_data["audit_id"] == audit_id:
                existing = entry_data
                break

        if existing:
            existing["sections"][section_key] = feedback.to_dict()
        else:
            entry = FeedbackEntry(
                audit_id=audit_id,
                site_url=site_url,
                sections={section_key: feedback}
            )
            self._data["feedbacks"].append(entry.to_dict())

        self._save_data()

    def get_feedback_for_section(
        self,
        section_type: str,
        limit: int = 10
    ) -> List[SectionFeedback]:
        """Get all feedback for a section type.

        Args:
            section_type: Type of section (e.g., 'alberatura')
            limit: Maximum number of feedback items to return

        Returns:
            List of SectionFeedback, most recent first
        """
        feedbacks = []

        # Iterate in reverse (most recent first)
        for entry_data in reversed(self._data["feedbacks"]):
            sections = entry_data.get("sections", {})
            if section_type in sections:
                feedbacks.append(SectionFeedback.from_dict(sections[section_type]))
                if len(feedbacks) >= limit:
                    break

        return feedbacks

    def get_high_rated_feedback(
        self,
        section_type: str,
        min_rating: int = 4,
        limit: int = 3
    ) -> List[SectionFeedback]:
        """Get high-rated feedback for few-shot learning.

        Args:
            section_type: Type of section
            min_rating: Minimum rating to include
            limit: Maximum number of items

        Returns:
            List of high-rated SectionFeedback
        """
        all_feedback = self.get_feedback_for_section(section_type, limit=50)
        high_rated = [
            fb for fb in all_feedback
            if fb.rating is not None and fb.rating >= min_rating
        ]
        return high_rated[:limit]

    def get_corrected_feedback(
        self,
        section_type: str,
        limit: int = 3
    ) -> List[SectionFeedback]:
        """Get feedback with user corrections.

        These are gold-standard examples for few-shot learning.
        """
        all_feedback = self.get_feedback_for_section(section_type, limit=50)
        corrected = [
            fb for fb in all_feedback
            if fb.corrected_text is not None and fb.corrected_text.strip()
        ]
        return corrected[:limit]

    def get_all_entries(self) -> List[FeedbackEntry]:
        """Get all feedback entries."""
        return [
            FeedbackEntry.from_dict(entry_data)
            for entry_data in self._data["feedbacks"]
        ]

    def get_entry_by_audit(self, audit_id: str) -> Optional[FeedbackEntry]:
        """Get feedback entry for a specific audit."""
        for entry_data in self._data["feedbacks"]:
            if entry_data["audit_id"] == audit_id:
                return FeedbackEntry.from_dict(entry_data)
        return None

    def delete_entry(self, audit_id: str) -> bool:
        """Delete a feedback entry."""
        for i, entry_data in enumerate(self._data["feedbacks"]):
            if entry_data["audit_id"] == audit_id:
                del self._data["feedbacks"][i]
                self._save_data()
                return True
        return False
