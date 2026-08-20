from __future__ import annotations

from pathlib import Path

from memmaster.adapters.im import IMAdapter
from memmaster.adapters.mail import MailAdapter
from memmaster.adapters.meeting import MeetingAdapter
from memmaster.adapters.web import WebAdapter
from memmaster.registry import ConnectorRegistry


def default_registry(corpus_root: Path) -> ConnectorRegistry:
    registry = ConnectorRegistry()
    registry.register(MailAdapter(corpus_root / "mail"))
    registry.register(MeetingAdapter(corpus_root / "meeting"))
    registry.register(IMAdapter(corpus_root / "im"))
    registry.register(WebAdapter(corpus_root / "web"))
    return registry
