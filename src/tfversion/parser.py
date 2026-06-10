import glob
import os
import re
from typing import Optional

import typer

from tfversion.config import BackendConfig


class HclParser:
    def __init__(self, path: str):
        self._path = path

    def parse(self) -> BackendConfig:
        content = self._read_content()
        block = self._extract_backend_block(content)
        fields = self._extract_fields(block)
        self._validate_fields(fields)
        return BackendConfig(
            bucket=fields["bucket"],
            key=fields["key"],
            region=fields["region"],
            profile=fields.get("profile"),
            required_version=self._extract_required_version(content),
        )

    def _read_content(self) -> str:
        tf_files = glob.glob(os.path.join(self._path, "*.tf"))
        if not tf_files:
            typer.echo(f"No .tf files found in {self._path}", err=True)
            raise typer.Exit(1)
        return "".join(open(f).read() for f in tf_files)

    def _extract_backend_block(self, content: str) -> str:
        match = re.search(r'backend\s+"s3"\s*\{([^}]+)\}', content, re.DOTALL)
        if not match:
            typer.echo(f"No S3 backend configuration found in {self._path}", err=True)
            raise typer.Exit(1)
        return match.group(1)

    def _extract_fields(self, block: str) -> dict:
        return dict(re.findall(r'(\w+)\s*=\s*"([^"]*)"', block))

    def _validate_fields(self, fields: dict) -> None:
        for field in ("bucket", "key", "region"):
            if field not in fields:
                typer.echo(f"Backend block is missing required field: {field}", err=True)
                raise typer.Exit(1)

    def _extract_required_version(self, content: str) -> Optional[str]:
        match = re.search(r'required_version\s*=\s*"([^"]*)"', content)
        return match.group(1) if match else None
