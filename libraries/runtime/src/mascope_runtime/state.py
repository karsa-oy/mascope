"""
This file provides an API representing runtime state,

- `RuntimeJsonState` persisted to a `state.json` on disk
- `RuntimeTempState` persisted to an object in memory

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
`override` value is ephemeral, being cleared with
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

Implementation note: both classes intercept every public attribute
access via `__setattr__`/`__getattr__`, so their own internals are
kept in underscore-prefixed attributes written with
`object.__setattr__` to avoid recursion. State is stored per
instance — two Runtime instances in one process (e.g. the CLI's own
plus a temporary one built for a compose invocation) must not share
or clobber each other's state.
"""

import json
import os


default_state = {
    "env": {"active": "default", "override": None},
    "mode": {"active": "dev", "override": None},
    "modules": {
        "active": ["backend", "frontend"],
        "override": None,
    },
}


class RuntimeJsonState(object):
    """
    Persistent  runtime state

    This class represents the persistent runtime state,
    which is saved to `MASCOPE_PATH/runtime/state.json`.
    When instantiating the class, the JSON will be
    created if it doesn't exist. Every call to the
    attribute API updates the `state.json` file
    immediately.
    """

    def __init__(self, root_path):
        object.__setattr__(
            self, "_state_path", os.path.join(root_path, ".runtime", "state.json")
        )

    def __setattr__(self, attr: str, value: any):
        self.ensure_state_json()
        with open(self._state_path, "r") as f:
            state = json.load(f)
        with open(self._state_path, "w") as f:
            state[attr]["active"] = value
            json.dump(state, f, indent=2)

    def __getattr__(self, attr: str) -> any:
        self.ensure_state_json()

        # Check environment variable override for 'env'
        if attr == "env":
            env_override = os.environ.get("MASCOPE_ENV")
            if env_override:
                return env_override

        with open(self._state_path, "r") as f:
            state = json.load(f)
            return state[attr]["override"] or state[attr]["active"]

    def override(self, attr: str, value: any):
        self.ensure_state_json()
        with open(self._state_path, "r") as f:
            state = json.load(f)
        with open(self._state_path, "w") as f:
            state[attr]["override"] = value
            json.dump(state, f, indent=2)

    def ensure_state_json(self):
        if not os.path.exists(self._state_path):
            with open(self._state_path, "x") as f:
                json.dump(
                    default_state,
                    f,
                    indent=2,
                )


class RuntimeTempState(object):
    def __init__(
        self,
        env: str,
        mode: str,
    ):
        """
        Emphemeral  runtime state

        This class representates a temporary runtime state.
        State is persisted only in memory, in a regular
        Python dict object.
        """
        object.__setattr__(
            self,
            "_state",
            {
                "env": {"active": env or "default", "override": None},
                "mode": {"active": mode or "dev", "override": None},
            },
        )

    def __setattr__(self, attr: str, value: any):
        self._state[attr]["active"] = value

    def __getattr__(self, attr: str):
        return self._state[attr]["override"] or self._state[attr]["active"]

    def override(self, attr: str, value: any):
        self._state[attr]["override"] = value
