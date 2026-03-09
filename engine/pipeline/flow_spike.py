import importlib
import os
from dataclasses import dataclass

from engine.pipeline.runner import run_pipeline


FLOW_SPIKE_ENV = "CREWAI_FLOW_SPIKE_ENABLED"
FLOW_MEMORY_ENV = "CREWAI_FLOW_MEMORY_ENABLED"


@dataclass
class FlowSpikeConfig:
    flow_enabled: bool
    memory_enabled: bool


def load_flow_spike_config():
    return FlowSpikeConfig(
        flow_enabled=os.getenv(FLOW_SPIKE_ENV, "0") == "1",
        memory_enabled=os.getenv(FLOW_MEMORY_ENV, "0") == "1",
    )


def _resolve_crewai_flow_symbols():
    try:
        module = importlib.import_module("crewai.flow.flow")
    except Exception:
        return None

    flow_cls = getattr(module, "Flow", None)
    start = getattr(module, "start", None)
    listen = getattr(module, "listen", None)
    return flow_cls, start, listen


def _run_flow_spike(topic=None, limit=2, memory_enabled=False):
    symbols = _resolve_crewai_flow_symbols()
    if not symbols:
        print("[Flow Spike] CrewAI Flow API not available; falling back to standard runner.")
        run_pipeline(topic=topic, limit=limit)
        return

    print("[Flow Spike] Flow mode is enabled for architecture validation.")
    if memory_enabled:
        print("[Flow Spike] Memory mode is enabled (validation-only flag for future flow memory usage).")

    print("[Flow Spike] Running standard phase runner inside spike mode (non-breaking baseline).")
    run_pipeline(topic=topic, limit=limit)


def run_pipeline_entry(topic=None, limit=2):
    config = load_flow_spike_config()
    if not config.flow_enabled:
        run_pipeline(topic=topic, limit=limit)
        return

    _run_flow_spike(topic=topic, limit=limit, memory_enabled=config.memory_enabled)
