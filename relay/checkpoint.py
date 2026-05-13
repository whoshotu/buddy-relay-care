import json
import os
from typing import List

CHECKPOINT_DIR = "/tmp/buddy_checkpoints"
os.makedirs(CHECKPOINT_DIR, exist_ok=True)

def save_checkpoint(session_id: str, messages: list):
    path = os.path.join(CHECKPOINT_DIR, f"{session_id}.json")
    with open(path, "w") as f:
        json.dump([m.dict() for m in messages], f)

def load_checkpoint(session_id: str) -> List[dict]:
    path = os.path.join(CHECKPOINT_DIR, f"{session_id}.json")
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return []
