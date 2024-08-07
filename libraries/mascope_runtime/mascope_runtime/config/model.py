from pydantic import BaseModel

from typing import Literal, List

EnvMode = Literal["development", "production"]

EnvPlatform = Literal[
    "linux_x86_64",
    "macos_i386",
    "macos_universal",
    "macos_x86_64",
    "windows_x64",
    "windows_x86",
]


class MascopeMetaConfig(BaseModel):
    name: str
    description: str
    path: str
    mode: EnvMode = "production"
    platform: EnvPlatform = "linux_x86_64"


class MascopeServerConfig(BaseModel):
    port: int = 8090
    database: str = r"./database"
    filestreams: str = r"./filestreams"
    filestore: str = r"./filestore"


class MascopeFileConverterConfig(BaseModel):
    threads: int = 2
    ping: bool = False
    source: str = r"./filestreams"
    target: str = r"./filestore"
    recursive: bool = False
    patterns: List[str] = ["*.h5", "*.raw"]


class MascopeTofAgentConfig(BaseModel):
    host: str
    port: int = 8090
    source: str
    target: str


class MascopeFileMoverConfig(BaseModel):
    mask: str = "*.raw"
    timeout: int = 10
    source: str
    target: str


class MascopeConfig(BaseModel):
    meta: MascopeMetaConfig
    server: MascopeServerConfig
    file_converter: MascopeFileConverterConfig
    tof_agent: MascopeTofAgentConfig
    file_mover: MascopeFileMoverConfig
