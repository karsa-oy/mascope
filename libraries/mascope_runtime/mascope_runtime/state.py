import os, json

mascope_path = os.environ["MASCOPE_PATH"]
state_path = os.path.join(mascope_path, "runtime", "state.json")


def ensure_state_json():
    if not os.path.exists(state_path):
        with open(state_path, "x") as f:
            defaults = {"default": None, "temp": None}
            json.dump(defaults, f, indent=2)


class MascopeState(object):
    def __setattr__(self, attr: str, value: any):
        ensure_state_json()
        with open(state_path, "r") as f:
            state = json.load(f)
        with open(state_path, "w") as f:
            state[attr] = value
            json.dump(state, f, indent=2)

    def __getattr__(self, attr: str):
        ensure_state_json()
        with open(state_path, "r") as f:
            state = json.load(f)
            return state[attr]


state = MascopeState()
