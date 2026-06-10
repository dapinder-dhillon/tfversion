from dataclasses import dataclass
from typing import Optional


@dataclass
class BackendConfig:
    bucket: str
    key: str
    region: str
    profile: Optional[str]
    required_version: Optional[str]
