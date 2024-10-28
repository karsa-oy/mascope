class MascopeMissingPathException(Exception):
    def __init__(self):
        super().__init__(
            """
    MASCOPE_PATH environment variable is not set: please set it with to 
    a path containing a valid Mascope runtime directory.

    If you are a Mascope user, contact your Mascope server administrator.

    If you are a Mascope developer, this path can point to your local clone
    of the Mascope git repo. See the README.md for more information.
    """
        )


class MascopeConfigNotFoundException(Exception):
    def __init__(self, env: str, env_path: str, mode: str):
        super().__init__(
            f"""
    Runtime '{env}' is active but is missing a config file
    for '{mode}' mode. Please make sure that a valid Mascope
    config file called either '{mode}.mascope.toml' or 
    '{mode}.local.mascope.toml' is placed in the runtime path:
    
        '{env_path}'
    """
        )
