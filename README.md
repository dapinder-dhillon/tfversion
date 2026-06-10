# tfversion

A command-line tool that tells you which exact Terraform version you need to use before touching a module.

## The problem

Terraform records the exact version that last wrote a state file inside the remote state itself.
When a module's `state.tf` only says `required_version = "~>1.0.0"`, it does not tell you whether
the team last ran `1.0.9` or `1.0.11`. If you run a different patch version, Terraform silently
upgrades the state file format — a change that cannot be rolled back, and that will break every
other team member working on that module.

The usual workaround is to manually download the remote state file, inspect the
`terraform_version` field, and then switch to that version with `tfenv`. This tool automates
that lookup.

## What it does

Run `tfversion` inside any Terraform module directory. It reads the `backend "s3"` block from
your `.tf` files, fetches the remote state file from S3 using the same AWS profile declared in
that block, and prints the exact version string recorded there.

```
$ cd 308035896950/prod/ech
$ tfversion
1.0.11
```

The output is a bare version string so you can pipe it directly:

```bash
tfenv use $(tfversion)
```

## Verbose mode

```
$ tfversion --verbose
Backend:                  s3://elsevier-tio-pmx-308035896950/terraform/prod/ech/terraform.tfstate
Profile:                  aws-els-pmxprod
Region:                   eu-west-1
State version (last run): 1.0.11
Code constraint:          ~>1.0.0
```

## Installation

Requires Python 3.9+ and an AWS profile that has `s3:GetObject` on the relevant state bucket.

```bash
# From source using pip
pip install -e /path/to/tfversion

# Or with pipx for an isolated global install
pipx install /path/to/tfversion
```

After installation, `tfversion` is available anywhere on your PATH.

## Usage

```
tfversion [PATH] [OPTIONS]

Arguments:
  PATH    Terraform module directory. Defaults to the current directory.

Options:
  -v, --verbose   Show backend URL, profile, region, and code constraint.
  --help          Show this message and exit.
```

## Requirements

- Python 3.9+
- `boto3` (AWS SDK — installed automatically)
- An AWS profile configured in `~/.aws/config` that matches the `profile` field in the
  module's `backend "s3"` block. If no `profile` is declared in the backend, boto3 uses
  its default credential chain (`AWS_PROFILE` env var, default profile, instance role).

## What it does not do

- Auto-switch Terraform versions. Use `tfenv use $(tfversion)` for that.
- Support backends other than S3.
- Cache results. Every call fetches live state — a stale cache is more dangerous than a
  slow lookup.
