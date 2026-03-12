"""Feedback learner for constructing few-shot examples."""

from typing import List, Dict, Any, Optional

from .storage import FeedbackStorage, SectionFeedback


class FeedbackLearner:
    """Builds few-shot examples and style instructions from feedback."""

    def __init__(self, storage: FeedbackStorage):
        """Initialize learner.

        Args:
            storage: FeedbackStorage instance
        """
        self.storage = storage

    def get_examples_for_section(
        self,
        section_type: str,
        max_examples: int = 3
    ) -> List[Dict[str, Any]]:
        """Get few-shot examples for a section.

        Priority order:
        1. Examples with user corrections (gold standard)
        2. Examples with high rating (>= 4)
        3. Examples with positive feedback

        Args:
            section_type: Type of section (e.g., 'alberatura')
            max_examples: Maximum number of examples

        Returns:
            List of example dictionaries for prompt construction
        """
        examples = []

        # 1. Corrected examples (best for learning)
        corrected = self.storage.get_corrected_feedback(section_type, limit=max_examples)
        for fb in corrected:
            examples.append({
                "type": "corrected",
                "original_text": self._truncate(fb.generated_text, 300),
                "corrected_text": self._truncate(fb.corrected_text, 300),
                "feedback_text": fb.user_feedback,
                "rating": fb.rating,
            })
            if len(examples) >= max_examples:
                return examples

        # 2. High-rated examples
        remaining = max_examples - len(examples)
        if remaining > 0:
            high_rated = self.storage.get_high_rated_feedback(
                section_type, min_rating=4, limit=remaining
            )
            for fb in high_rated:
                # Skip if already included as corrected
                if any(e.get("original_text") == self._truncate(fb.generated_text, 300)
                       for e in examples):
                    continue

                examples.append({
                    "type": "high_rated",
                    "original_text": self._truncate(fb.generated_text, 300),
                    "feedback_text": fb.user_feedback,
                    "rating": fb.rating,
                })
                if len(examples) >= max_examples:
                    return examples

        # 3. Any feedback with text
        remaining = max_examples - len(examples)
        if remaining > 0:
            all_feedback = self.storage.get_feedback_for_section(section_type, limit=10)
            for fb in all_feedback:
                if fb.user_feedback and fb.user_feedback.strip():
                    # Skip if already included
                    if any(e.get("original_text") == self._truncate(fb.generated_text, 300)
                           for e in examples):
                        continue

                    examples.append({
                        "type": "feedback_only",
                        "original_text": self._truncate(fb.generated_text, 300),
                        "feedback_text": fb.user_feedback,
                        "rating": fb.rating,
                    })
                    if len(examples) >= max_examples:
                        return examples

        return examples

    def build_few_shot_prompt(self, examples: List[Dict[str, Any]]) -> str:
        """Build few-shot section of the prompt.

        Args:
            examples: List of example dictionaries

        Returns:
            Formatted string for prompt
        """
        if not examples:
            return ""

        parts = [
            "",
            "ESEMPI DI FEEDBACK RICEVUTI SU SEZIONI SIMILI:",
            ""
        ]

        for i, ex in enumerate(examples, 1):
            parts.append(f"Esempio {i}:")

            if ex["type"] == "corrected":
                parts.append(f'- Testo originale: "{ex["original_text"]}"')
                parts.append(f'- Feedback utente: "{ex["feedback_text"]}"')
                parts.append(f'- Testo corretto: "{ex["corrected_text"]}"')
                parts.append("→ Usa lo stile della versione corretta.")
            elif ex["type"] == "high_rated":
                parts.append(f'- Testo (rating {ex["rating"]}/5): "{ex["original_text"]}"')
                if ex.get("feedback_text"):
                    parts.append(f'- Feedback positivo: "{ex["feedback_text"]}"')
                parts.append("→ Questo stile ha ricevuto feedback positivo.")
            else:
                parts.append(f'- Testo generato: "{ex["original_text"]}"')
                parts.append(f'- Feedback utente: "{ex["feedback_text"]}"')
                parts.append("→ Tieni conto di questo feedback.")

            parts.append("")

        parts.append("Genera tenendo conto di questi feedback.")
        return "\n".join(parts)

    def get_style_preferences(self, section_type: str = None) -> Dict[str, Any]:
        """Analyze feedback to extract style preferences.

        Args:
            section_type: Optional filter by section type

        Returns:
            Dictionary with style preferences
        """
        preferences = {
            "avg_rating": None,
            "common_issues": [],
            "positive_patterns": [],
        }

        # Get all feedback
        if section_type:
            feedbacks = self.storage.get_feedback_for_section(section_type, limit=50)
        else:
            feedbacks = []
            for entry in self.storage.get_all_entries():
                feedbacks.extend(entry.sections.values())

        if not feedbacks:
            return preferences

        # Calculate average rating
        ratings = [fb.rating for fb in feedbacks if fb.rating is not None]
        if ratings:
            preferences["avg_rating"] = sum(ratings) / len(ratings)

        # Extract common themes from feedback text
        negative_keywords = ["lungo", "generico", "tecnico", "vago", "ripetitivo"]
        positive_keywords = ["conciso", "chiaro", "specifico", "dettagliato", "ottimo"]

        for fb in feedbacks:
            if not fb.user_feedback:
                continue

            feedback_lower = fb.user_feedback.lower()

            for kw in negative_keywords:
                if kw in feedback_lower and kw not in preferences["common_issues"]:
                    preferences["common_issues"].append(kw)

            for kw in positive_keywords:
                if kw in feedback_lower and kw not in preferences["positive_patterns"]:
                    preferences["positive_patterns"].append(kw)

        return preferences

    def _truncate(self, text: str, max_length: int) -> str:
        """Truncate text with ellipsis."""
        if not text:
            return ""
        if len(text) <= max_length:
            return text
        return text[:max_length - 3] + "..."
