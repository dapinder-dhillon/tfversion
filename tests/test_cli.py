import json
from unittest.mock import MagicMock, patch

import pytest
from botocore.exceptions import ClientError, NoCredentialsError
from typer.testing import CliRunner

from tfversion.cli import app
from tfversion.parser import HclParser

runner = CliRunner()

TF_WITH_PROFILE = """
terraform {
  backend "s3" {
    bucket  = "my-bucket"
    key     = "terraform/prod/newrelic/terraform.tfstate"
    region  = "eu-west-1"
    profile = "aws-els-pmxprod"
  }
  required_version = "~>1.0.0"
}
"""

TF_WITHOUT_PROFILE = """
terraform {
  backend "s3" {
    bucket = "my-bucket"
    key    = "terraform/main-infra/terraform.tfstate"
    region = "eu-west-1"
  }
}
"""

STATE = {"terraform_version": "1.0.11", "version": 4}


def _make_session_mock(state: dict) -> MagicMock:
    body_mock = MagicMock()
    body_mock.read.return_value = json.dumps(state).encode()
    s3_mock = MagicMock()
    s3_mock.get_object.return_value = {"Body": body_mock}
    session_mock = MagicMock()
    session_mock.client.return_value = s3_mock
    return session_mock


def _make_s3_error(code: str) -> ClientError:
    return ClientError({"Error": {"Code": code, "Message": code}}, "GetObject")


@pytest.fixture
def dir_with_profile(tmp_path):
    (tmp_path / "state.tf").write_text(TF_WITH_PROFILE)
    return tmp_path


@pytest.fixture
def dir_without_profile(tmp_path):
    (tmp_path / "state.tf").write_text(TF_WITHOUT_PROFILE)
    return tmp_path


def test_help():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0


def test_parse_with_profile(dir_with_profile):
    config = HclParser(str(dir_with_profile)).parse()
    assert config.bucket == "my-bucket"
    assert config.profile == "aws-els-pmxprod"
    assert config.required_version == "~>1.0.0"


def test_parse_without_profile(dir_without_profile):
    config = HclParser(str(dir_without_profile)).parse()
    assert config.profile is None
    assert config.required_version is None


def test_no_tf_files(tmp_path):
    result = runner.invoke(app, [str(tmp_path)])
    assert result.exit_code == 1
    assert "No .tf files found" in result.output


def test_no_s3_backend(tmp_path):
    (tmp_path / "main.tf").write_text('terraform {\n  required_version = "~>1.0.0"\n}\n')
    result = runner.invoke(app, [str(tmp_path)])
    assert result.exit_code == 1
    assert "No S3 backend configuration found" in result.output


def test_missing_required_field(tmp_path):
    (tmp_path / "main.tf").write_text(
        'terraform {\n  backend "s3" {\n    bucket = "b"\n    key = "k"\n  }\n}\n'
    )
    result = runner.invoke(app, [str(tmp_path)])
    assert result.exit_code == 1
    assert "missing required field: region" in result.output


def test_prints_version_with_profile(dir_with_profile):
    with patch("tfversion.fetcher.boto3.Session", return_value=_make_session_mock(STATE)) as mock_session:
        result = runner.invoke(app, [str(dir_with_profile)])
    assert result.exit_code == 0
    assert result.output.strip() == "1.0.11"
    mock_session.assert_called_once_with(profile_name="aws-els-pmxprod")


def test_prints_version_without_profile(dir_without_profile):
    with patch("tfversion.fetcher.boto3.Session", return_value=_make_session_mock(STATE)) as mock_session:
        result = runner.invoke(app, [str(dir_without_profile)])
    assert result.exit_code == 0
    assert result.output.strip() == "1.0.11"
    mock_session.assert_called_once_with()


def test_defaults_to_cwd(dir_with_profile, monkeypatch):
    monkeypatch.chdir(dir_with_profile)
    with patch("tfversion.fetcher.boto3.Session", return_value=_make_session_mock(STATE)):
        result = runner.invoke(app, [])
    assert result.exit_code == 0
    assert result.output.strip() == "1.0.11"


def test_s3_no_such_key(dir_with_profile):
    session_mock = MagicMock()
    session_mock.client.return_value.get_object.side_effect = _make_s3_error("NoSuchKey")
    with patch("tfversion.fetcher.boto3.Session", return_value=session_mock):
        result = runner.invoke(app, [str(dir_with_profile)])
    assert result.exit_code == 1
    assert "State file not found" in result.output


def test_s3_access_denied(dir_with_profile):
    session_mock = MagicMock()
    session_mock.client.return_value.get_object.side_effect = _make_s3_error("AccessDenied")
    with patch("tfversion.fetcher.boto3.Session", return_value=session_mock):
        result = runner.invoke(app, [str(dir_with_profile)])
    assert result.exit_code == 1
    assert "Access denied" in result.output
    assert "aws-els-pmxprod" in result.output


def test_no_credentials(dir_with_profile):
    session_mock = MagicMock()
    session_mock.client.return_value.get_object.side_effect = NoCredentialsError()
    with patch("tfversion.fetcher.boto3.Session", return_value=session_mock):
        result = runner.invoke(app, [str(dir_with_profile)])
    assert result.exit_code == 1
    assert "Access denied" in result.output


def test_invalid_json_state(dir_with_profile):
    body_mock = MagicMock()
    body_mock.read.return_value = b"not valid json{{"
    session_mock = MagicMock()
    session_mock.client.return_value.get_object.return_value = {"Body": body_mock}
    with patch("tfversion.fetcher.boto3.Session", return_value=session_mock):
        result = runner.invoke(app, [str(dir_with_profile)])
    assert result.exit_code == 1
    assert "not valid JSON" in result.output


def test_terraform_version_absent_from_state(dir_with_profile):
    with patch("tfversion.fetcher.boto3.Session", return_value=_make_session_mock({"version": 4})):
        result = runner.invoke(app, [str(dir_with_profile)])
    assert result.exit_code == 1
    assert "terraform_version not found" in result.output


def test_verbose_shows_all_fields(dir_with_profile):
    with patch("tfversion.fetcher.boto3.Session", return_value=_make_session_mock(STATE)):
        result = runner.invoke(app, ["--verbose", str(dir_with_profile)])
    assert result.exit_code == 0
    assert "1.0.11" in result.output
    assert "~>1.0.0" in result.output
    assert "aws-els-pmxprod" in result.output
    assert "s3://my-bucket/terraform/prod/newrelic/terraform.tfstate" in result.output


def test_verbose_short_flag(dir_with_profile):
    with patch("tfversion.fetcher.boto3.Session", return_value=_make_session_mock(STATE)):
        result = runner.invoke(app, ["-v", str(dir_with_profile)])
    assert result.exit_code == 0
    assert "1.0.11" in result.output
    assert "~>1.0.0" in result.output
    assert "aws-els-pmxprod" in result.output
    assert "s3://my-bucket/terraform/prod/newrelic/terraform.tfstate" in result.output


def test_verbose_no_required_version(dir_without_profile):
    with patch("tfversion.fetcher.boto3.Session", return_value=_make_session_mock(STATE)):
        result = runner.invoke(app, ["--verbose", str(dir_without_profile)])
    assert result.exit_code == 0
    assert "(not set)" in result.output
