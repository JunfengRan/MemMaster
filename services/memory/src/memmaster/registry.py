from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterable

from memmaster.models import CanonicalDocument, SourceCursor


class SourceAdapter(ABC):
    source_id: str

    @abstractmethod
    def probe(self) -> dict:
        ...

    @abstractmethod
    def sync(self, cursor: SourceCursor | None = None) -> tuple[list[CanonicalDocument], SourceCursor]:
        ...


class ConnectorRegistry:
    def __init__(self) -> None:
        self._adapters: dict[str, SourceAdapter] = {}

    def register(self, adapter: SourceAdapter) -> None:
        self._adapters[adapter.source_id] = adapter

    def get(self, source_id: str) -> SourceAdapter:
        if source_id not in self._adapters:
            raise KeyError(f"unknown adapter: {source_id}")
        return self._adapters[source_id]

    def ids(self) -> list[str]:
        return sorted(self._adapters)

    def all(self) -> Iterable[SourceAdapter]:
        return self._adapters.values()

    @classmethod
    def discover(cls, extra: Iterable[SourceAdapter] | None = None) -> "ConnectorRegistry":
        registry = cls()
        try:
            from importlib.metadata import entry_points

            for ep in entry_points().select(group="memmaster.sources"):
                adapter = ep.load()
                instance = adapter() if isinstance(adapter, type) else adapter
                registry.register(instance)
        except Exception:
            pass
        if extra:
            for adapter in extra:
                registry.register(adapter)
        return registry
