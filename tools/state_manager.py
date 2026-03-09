import json
import re
from pathlib import Path

STATE_FILE = Path("state/workflow_state.json")

def load_state(topic=None):
    """Load workflow state. If topic is provided, use topic-specific state file."""
    state_file = STATE_FILE
    if topic:
        safe_topic = re.sub(r'[^a-zA-Z0-9]', '_', topic.lower())
        state_file = Path(f"state/workflow_{safe_topic}.json")
        
    if not state_file.exists():
        return {"topic": topic} if topic else {}

    with open(state_file, "r") as f:
        return json.load(f)

def save_state(state, topic=None):
    """Save workflow state"""
    state_file = STATE_FILE
    current_topic = topic or state.get("topic")
    if current_topic:
        safe_topic = re.sub(r'[^a-zA-Z0-9]', '_', current_topic.lower())
        state_file = Path(f"state/workflow_{safe_topic}.json")
        
    with open(state_file, "w") as f:
        json.dump(state, f, indent=2)

def update_state(key, value, topic=None):
    """Update a single value in the state"""
    state = load_state(topic)
    state[key] = value
    save_state(state, topic)

def get_state_value(key, topic=None):
    """Retrieve specific value"""
    state = load_state(topic)
    return state.get(key)
