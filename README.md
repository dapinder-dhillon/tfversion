<div align="center">

# tfversion

**Know the exact Terraform version before you `plan`.**

[![Python](https://img.shields.io/badge/python-3.13+-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Poetry](https://img.shields.io/endpoint?url=https://python-poetry.org/badge/v0.json)](https://python-poetry.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-22c55e)](LICENSE)
[![boto3](https://img.shields.io/badge/AWS-boto3-FF9900?logo=amazonaws&logoColor=white)](https://boto3.amazonaws.com/v1/documentation/api/latest/index.html)

<br/>

<img src="./docs/demo.gif" alt="tfversion demo" width="720"/>

<br/>

</div>

---

## The problem

Terraform records the exact version that last wrote a state file — not inside your `.tf` files, but inside the remote state itself. When a module only declares `required_version = "~>1.0.0"`, it doesn't tell you whether the team last ran `1.0.9` or `1.0.11`.

Run the wrong patch version and Terraform silently upgrades the state file format. That upgrade **cannot be rolled back** and immediately breaks every other developer working on the same module.

The usual fix is manual: download the state file, grep for `terraform_version`, switch with `tfenv`. `tfversion` automates that entire lookup in a single command.

---

## Features

- Parses `backend "s3"` blocks from any `.tf` file in the directory — no config needed
- Fetches the remote state over the same AWS profile declared in the backend block
- Prints a bare version string, ready to pipe into `tfenv`
- `--verbose` mode surfaces the full backend context at a glance
- Follows Terraform's own credential resolution order: named profile → `AWS_PROFILE` → default profile → instance role
- Zero state mutation — read-only `s3:GetObject`

---

## Installation

### pipx (recommended — isolated global install)

```bash
pipx install git+https://github.com/dapinder-dhillon/tfversion.git
```

### pip

```bash
pip install git+https://github.com/dapinder-dhillon/tfversion.git
```

### From source

```bash
git clone https://github.com/dapinder-dhillon/tfversion.git
cd tfversion
poetry install
```

After installation `tfversion` is on your `PATH`.

---

## Usage

### Default — bare version string

```
$ cd infra/modules/prod-newrelic
$ tfversion
1.0.11
```

The output is intentionally bare so it pipes cleanly:

```bash
tfenv use $(tfversion)
# Switching to v1.0.11
# Switching default version to v1.0.11
```

### `--verbose` / `-v` — full backend summary

```
$ tfversion --verbose
Backend:                  s3://my-org-tfstate/terraform/prod/newrelic/terraform.tfstate
Profile:                  aws-prod-admin
Region:                   eu-west-1
State version (last run): 1.0.11
Code constraint:          ~>1.0.0
```

### Explicit path

```bash
tfversion ./infra/modules/networking
tfversion --verbose ./infra/modules/networking
```

When `PATH` is omitted, `tfversion` defaults to the current working directory.

---

## AWS credentials

`tfversion` mirrors Terraform's own credential resolution. If the backend block declares a `profile`:

```hcl
terraform {
  backend "s3" {
    bucket  = "my-org-tfstate"
    key     = "terraform/prod/newrelic/terraform.tfstate"
    region  = "eu-west-1"
    profile = "aws-prod-admin"      # ← used by tfversion
  }
}
```

it creates a boto3 session with that profile. If no `profile` is present, it falls back to the default credential chain (`AWS_PROFILE`, `~/.aws/credentials` default, EC2/ECS instance role).

The only permission required is `s3:GetObject` on the state file key.

---

## Error reference

| Situation | Message |
|-----------|---------|
| No `.tf` files in directory | `No .tf files found in <path>` |
| No `backend "s3"` block found | `No S3 backend configuration found in <path>` |
| Required field missing | `Backend block is missing required field: <field>` |
| State file does not exist | `State file not found: s3://<bucket>/<key>` |
| Credentials missing or access denied | `Access denied fetching s3://<bucket>/<key> (profile: <name>)` |
| Other S3 error | `S3 error (<code>): s3://<bucket>/<key>` |
| State file is not valid JSON | `Remote state file is not valid JSON: s3://<bucket>/<key>` |
| `terraform_version` key absent | `terraform_version not found in state file: s3://<bucket>/<key>` |

All errors are written to **stderr** and exit with code `1`. Nothing is written to stdout on failure, so `tfenv use $(tfversion)` never receives a partial or error string.

---

## Development

```bash
git clone https://github.com/dapinder-dhillon/tfversion.git
cd tfversion
poetry install
poetry run pytest -v
```

### Project layout

```
src/tfversion/
├── config.py       # BackendConfig dataclass
├── parser.py       # HclParser  — reads .tf files, extracts backend block
├── fetcher.py      # S3StateFetcher — fetches and decodes state from S3
├── formatter.py    # VerboseFormatter — formats the --verbose output
└── cli.py          # Typer app + entry point
tests/
└── test_cli.py     # 17 tests, no real AWS calls, no moto
```

### Generating the demo GIF

Install [VHS](https://github.com/charmbracelet/vhs) then run:

```bash
vhs docs/demo.tape
```

---

## What it does not do

- **Auto-switch versions.** Use `tfenv use $(tfversion)` for that.
- **Support non-S3 backends.** GCS, Azure, Consul — not supported.
- **Cache results.** Every call fetches live state. A stale cache is more dangerous than a slow lookup.

---

## License

MIT © [Dapinder Singh](https://github.com/dapinder-dhillon)
