import os
import json

from typing import List

"""
This file provides an API representing runtime state,

- `MascopeRuntimeJsonState` persisted to a `state.json` on disk
- `MascopeRuntimeTempState` persisted to an object in memory

The API uses setters and getters to provide a simple
API to the state:

Read the `mode` field from the json
 print(state.mode) # 'dev'

Update the `env` field in the json:
  state.env = "foo"

Overrides

Additionally, an 'override' API is exposed allowing
the CLI to temporarily override a variable. Each field
in the `state` object has two values: `active` and 
`override`. The `active` value is persisted which the
`override` value is emphemeral, being cleared with
every time a CLI command is run.

When the CLI wants to temporarily override state, it can 
use the `.override` method to do so. Since passing `None` 
to this method will clear it, the CLI will thereby naturally 
reset the override whenever no option is passed. This is
currently only used for overriding the `env` selected.

Production

In the production containers, a special `state.json`
is used. You can find this file committed in
`runtime/lib/state.prod.json`
"""

default_state = {
    "env": {"active": "default", "override": None},
    "mode": {"active": "dev", "override": None},
    "modules": {
        "active": ["backend", "frontend"],
        "override": None,
    },
}

state_path = None  # *


class MascopeRuntimeJsonState(object):
    """
    Persistent Mascope runtime state

    This class represents the persistent runtime state,
    which is saved to `MASCOPE_PATH/runtime/state.json`.
    When instantiating the class, the JSON will be
    created if it doesn't exist. Every call to the
    attribute API updates the `state.json` file
    immediately.
    """

    def __init__(self, root_path):
        global state_path  # *
        state_path = os.path.join(root_path, "runtime", "state.json")

    def __setattr__(self, attr: str, value: any):
        global state_path
        self.ensure_state_json()
        with open(state_path, "r") as f:
            state = json.load(f)
        with open(state_path, "w") as f:
            state[attr]["active"] = value
            json.dump(state, f, indent=2)

    def __getattr__(self, attr: str) -> any:
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


temp_state = None  # *


class MascopeRuntimeTempState(object):
    def __init__(
        self,
        env: str,
        mode: str,
        modules: List[str],
    ):
        """
        Emphemeral Mascope runtime state

        This class representates a temporary runtime state.
        State is persisted only in memory, in a regular
        Python dict object.
        """
        global temp_state  # *
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


# * Global variables are used here in order
# to prevent conflicts with the __setattr__
# and __getattr__ methods. If instead we
# tried to put these inside the classes, we
# would run into infinite recursion.
