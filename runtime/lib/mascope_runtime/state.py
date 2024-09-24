import os, json

from typing import List


default_state = {
    "env": {"active": "default", "override": None},
    "mode": {"active": "dev", "override": None},
    "modules": {
        "active": ["backend", "frontend"],
        "override": None,
    },
}

state_path = None


class MascopeRuntimeJsonState(object):

    def __init__(self, root_path):
        global state_path
        state_path = os.path.join(root_path, "runtime", "state.json")

    def __setattr__(self, attr: str, value: any):
        global state_path
        self.ensure_state_json()
        with open(state_path, "r") as f:
            state = json.load(f)
        with open(state_path, "w") as f:
            state[attr]["active"] = value
            json.dump(state, f, indent=2)

    def __getattr__(self, attr: str):
        global state_path
        self.ensure_state_json()
        with open(state_path, "r") as f:
            state = json.load(f)
            return state[attr]["override"] or state[attr]["active"]

    def override(self, attr: str, value: any):
        global state_path
        self.ensure_state_json()
        with open(state_path, "r") as f:
            state = json.load(f)
        with open(state_path, "w") as f:
            state[attr]["override"] = value
            json.dump(state, f, indent=2)

    def ensure_state_json(self):
        global state_path
        if not os.path.exists(state_path):
            with open(state_path, "x") as f:
                json.dump(
                    default_state,
                    f,
                    indent=2,
                )


temp_state = None


class MascopeRuntimeTempState(object):
    def __init__(
        self,
        env: str,
        mode: str,
        modules: List[str],
    ):
        global temp_state
        temp_state = {
            "env": {"active": env or "default", "override": None},
            "mode": {"active": mode or "dev", "override": None},
            "modules": {
                "active": modules or ["backend", "frontend"],
                "override": None,
            },
        }

    def __setattr__(self, attr: str, value: any):
        temp_state[attr]["active"] = value

    def __getattr__(self, attr: str):
        return temp_state[attr]["override"] or temp_state[attr]["active"]

    def override(self, attr: str, value: any):
        temp_state[attr]["override"] = value
