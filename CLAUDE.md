# tfversion — AI Instructions

## What this project is

A single-command Python CLI that reads an S3 Terraform state file and prints the
`terraform_version` field recorded in it. Entry point: `tfversion`. Built with Poetry + Typer.

## Project layout

```
tfversion/
├── pyproject.toml
├── README.md
├── CLAUDE.md
└── src/
    └── tfversion/
        ├── __init__.py
        └── cli.py
tests/
├── __init__.py
└── test_cli.py
```

Use the `src/` layout. All application code lives under `src/tfversion/`.

## Tech stack — no deviations

| Concern          | Tool          | Why                                                    |
|------------------|---------------|--------------------------------------------------------|
| Packaging        | Poetry        | Declared by the team                                   |
| CLI framework    | Typer         | Declared by the team                                   |
| AWS access       | boto3 only    | No subprocess/aws-cli; cleaner error handling          |
| HCL parsing      | `re` only     | python-hcl2 cannot parse Terraform's `~>` syntax       |
| Tests            | pytest        | No real AWS calls; mock boto3 at session level         |

Never use `python-hcl2`, `subprocess`, the `aws` CLI, or any HCL library.
Never add caching, config files, or auto-version-switching.

## HCL shapes to support

Only two shapes exist in the repos this tool targets. The regex must handle both.

Shape 1 — with named AWS profile:
```hcl
terraform {
  backend "s3" {
    bucket  = "elsevier-tio-pmx-308035896950"
    key     = "terraform/prod/newrelic/terraform.tfstate"
    region  = "eu-west-1"
    profile = "aws-els-pmxprod"
  }
  required_version = "~>1.0.0"
}
```

Shape 2 — no profile (relies on default credential chain):
```hcl
terraform {
  backend "s3" {
    bucket = "elsevier-tio-pmx-308035896950"
    key    = "terraform/main-infra/terraform.tfstate"
    region = "eu-west-1"
  }
}
```

Key parsing rules:
- Extract the `backend "s3" { ... }` block with a single regex (`re.DOTALL`). The S3 backend
  block never has nested braces, so `[^}]+` is safe.
- Extract `key = "value"` pairs from the block with a second regex.
- Extract `required_version` separately from the full file content (it sits outside the
  backend block in the `terraform {}` block).
- `profile` is optional. All other fields (`bucket`, `key`, `region`) are required.

## AWS session creation

```python
# profile present in backend block:
boto3.Session(profile_name=profile)

# profile absent:
boto3.Session()   # honours AWS_PROFILE, default profile, instance role, etc.
```

This mirrors Terraform's own credential resolution order.

## Entry point wiring

In `pyproject.toml`:
```toml
[tool.poetry.scripts]
tfversion = "tfversion.cli:run"
```

In `cli.py`, define `app = typer.Typer(...)` and expose:
```python
def run() -> None:
    app()
```

## CLI behaviour

Default (no flags): print only the bare version string to stdout, nothing else.
`--verbose` / `-v`: print a multi-line summary to stdout (see README for format).
All errors: print a human-readable message to **stderr**, nothing to stdout, exit code 1.

The bare-version default exists specifically so `tfenv use $(tfversion)` works without parsing.

## Error handling — exact messages and exit codes

| Situation                              | stderr message                                                          | exit |
|----------------------------------------|-------------------------------------------------------------------------|------|
| No `.tf` files in directory            | `No .tf files found in <path>`                                          | 1    |
| `.tf` files but no S3 backend block    | `No S3 backend configuration found in <path>`                           | 1    |
| Required field missing from block      | `Backend block is missing required field: <field>`                      | 1    |
| S3 `NoSuchKey`                         | `State file not found: s3://<bucket>/<key>`                             | 1    |
| S3 `AccessDenied` or `NoCredentials`   | `Access denied fetching s3://<bucket>/<key> (profile: <name or default>)` | 1  |
| Other S3 `ClientError`                 | `S3 error (<code>): s3://<bucket>/<key>`                                | 1    |
| JSON decode failure                    | `Remote state file is not valid JSON: s3://<bucket>/<key>`              | 1    |
| `terraform_version` key absent         | `terraform_version not found in state file: s3://<bucket>/<key>`       | 1    |

## Test requirements

Use `typer.testing.CliRunner` and `unittest.mock.patch`. Mock `boto3.Session` at the
import path `tfversion.cli.boto3.Session`. No `moto`, no real network.

Minimum test coverage:
- Happy path with profile: version printed, `Session(profile_name=...)` called with correct value
- Happy path without profile: version printed, `Session()` called with no args
- `--verbose` and `-v` flags both work; output includes backend URL, profile, region, version, constraint
- `--verbose` with no `required_version` in file shows `(not set)`
- No path argument: defaults to CWD (use `monkeypatch.chdir`)
- All eight error rows in the table above

## Coding principles

- Prefer classes over standalone functions unless the logic is trivially simple. Structure code using object-oriented design.
- Every class and every method must have a single responsibility. If something does two things, split it.
- No documentation anywhere in code — no docstrings on classes, methods, or modules, no inline comments explaining what the code does.

## What NOT to build

- No `--switch` / auto-tfenv behaviour
- No `.tfversionrc` or any config file
- No caching layer
- No support for backends other than S3
- No shell completion (set `add_completion=False` on the Typer app)
- No multi-paragraph docstrings or inline comments explaining what the code does
