class MissingMascopePathException(Exception):
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
