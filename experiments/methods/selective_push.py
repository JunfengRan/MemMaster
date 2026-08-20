"""Selective push wrapper."""
from memmaster.engine import MemoryEngine
from memmaster.models import InterventionRequest

def run(engine: MemoryEngine, session_id: str, text: str):
    return engine.intervene(InterventionRequest(session_id=session_id, recent_text=text))
