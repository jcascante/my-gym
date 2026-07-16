from typing import Any, Protocol

from app.services.program.adaptation import FeedbackAction


class FeedbackParser(Protocol):
    def parse(self, payload: dict[str, Any]) -> FeedbackAction: ...


class StructuredFeedbackParser:
    def parse(self, payload: dict[str, Any]) -> FeedbackAction:
        return FeedbackAction(**payload)
