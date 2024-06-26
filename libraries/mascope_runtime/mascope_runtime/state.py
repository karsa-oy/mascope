import os

mascope_path=os.environ['MASCOPE_PATH']
state_dir = os.path.join(mascope_path, 'runtime', 'state')

def state_path(key: str):
    return os.path.join(state_dir, *key.split('_'))

class MascopeStatePathUndefined(Exception):
    def __init__(self, path: str):
        super().__init__(f"""

    Attempting to access a Mascope state path which
    is not defined. Make sure the following file and
    path exists:
                        
        {path}
    """)

class MascopeState(object):
    def __setattr__(self, attr: str, value: any):
        path = state_path(attr)
        if not os.path.exists(path):
            raise MascopeStatePathUndefined(path)
        else:
            with open(path, "w") as f:
                if value:
                    stripped=str(value).strip()
                    f.write(stripped)
                else:
                    f.write('')

    def __getattr__(self, attr: str):
        path = state_path(attr)
        if not os.path.exists(path):
            raise MascopeStatePathUndefined(path)
        else:
            with open(path, "r") as f:
                raw = f.read()
                stripped = raw.strip()
                if len(stripped) == 0:
                    return None
                else:
                    return stripped
                
state = MascopeState()