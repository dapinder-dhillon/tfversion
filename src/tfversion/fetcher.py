import json

import boto3
import typer
from botocore.exceptions import ClientError, NoCredentialsError

from tfversion.config import BackendConfig


class S3StateFetcher:
    def __init__(self, config: BackendConfig):
        self._config = config

    def fetch_version(self) -> str:
        session = self._create_session()
        body = self._get_raw_body(session)
        state = self._decode_json(body)
        return self._extract_version(state)

    def _create_session(self):
        if self._config.profile:
            return boto3.Session(profile_name=self._config.profile)
        return boto3.Session()

    def _get_raw_body(self, session) -> bytes:
        c = self._config
        s3 = session.client("s3")
        url = f"s3://{c.bucket}/{c.key}"
        profile_label = c.profile or "default"
        try:
            return s3.get_object(Bucket=c.bucket, Key=c.key)["Body"].read()
        except ClientError as e:
            code = e.response["Error"]["Code"]
            if code == "NoSuchKey":
                typer.echo(f"State file not found: {url}", err=True)
            elif code == "AccessDenied":
                typer.echo(f"Access denied fetching {url} (profile: {profile_label})", err=True)
            else:
                typer.echo(f"S3 error ({code}): {url}", err=True)
            raise typer.Exit(1)
        except NoCredentialsError:
            typer.echo(f"Access denied fetching {url} (profile: {profile_label})", err=True)
            raise typer.Exit(1)

    def _decode_json(self, body: bytes) -> dict:
        c = self._config
        try:
            return json.loads(body)
        except json.JSONDecodeError:
            typer.echo(f"Remote state file is not valid JSON: s3://{c.bucket}/{c.key}", err=True)
            raise typer.Exit(1)

    def _extract_version(self, state: dict) -> str:
        c = self._config
        if "terraform_version" not in state:
            typer.echo(f"terraform_version not found in state file: s3://{c.bucket}/{c.key}", err=True)
            raise typer.Exit(1)
        return state["terraform_version"]
