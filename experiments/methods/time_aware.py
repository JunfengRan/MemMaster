from memmaster.engine import MemoryEngine
from memmaster.models import SearchRequest

def run(engine: MemoryEngine, query: str):
    return engine.search(SearchRequest(query=query, methods=["hybrid", "time"]))
