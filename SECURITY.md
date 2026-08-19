# Security Policy

## Reporting a Vulnerability

**Please report security vulnerabilities privately through GitHub, not in a public issue.**

👉 **[Report a vulnerability](https://github.com/datacontract/datacontract-cli/security/advisories/new)**

That link opens a private security advisory that only you and the maintainers can
see. You can also reach it from the **Security** tab of this repository via
*Report a vulnerability*. Private reporting is enabled on this repository, so it
is the fastest and safest way to reach us — a public issue or pull request
discloses the problem to everyone before there is a fix available.

Please do not report vulnerabilities by email, on social media, or in the
community chat. Those channels are public or unmonitored for this purpose.

### What to include

The more of this you can provide, the faster we can confirm and fix:

- The version of Data Contract CLI (`datacontract --version`) and how it is
  installed (pip, `uvx`, Docker image, or as a Python library).
- Which command or API is affected, and the relevant part of the data contract,
  configuration, or server definition that triggers it.
- Steps to reproduce, ideally a minimal data contract file plus the command you
  ran. Please redact real credentials, hostnames, and data.
- The impact you think it has, and any suggested fix.

### What to expect

- We aim to acknowledge a report within **5 business days**.
- We will confirm the issue, tell you our assessment of its severity, and keep
  you updated as we work on a fix.
- We will credit you in the advisory and the release notes when the fix ships,
  unless you would rather stay anonymous.
- Once a fix is released we publish a GitHub Security Advisory for the issue.

Please give us a reasonable opportunity to release a fix before disclosing the
issue publicly.

## Supported Versions

Security fixes are released for the **most recent version** of Data Contract
CLI, published on [PyPI](https://pypi.org/project/datacontract-cli/) and as the
[`datacontract/cli`](https://hub.docker.com/r/datacontract/cli) Docker image.
There are no long-term support branches and fixes are not backported, so please
upgrade to the latest release before reporting an issue.

## Scope

Data Contract CLI reads data contract files, connects to data sources with
credentials taken from the environment or a configuration file, and can run as
a web server (`datacontract api`). Reports in these areas are especially
welcome:

- Credentials or other secrets leaking into logs, exported artifacts, test
  results, or error messages.
- A data contract file, schema, or server definition that causes code execution,
  file access, or requests beyond what the invoked command should do — including
  when the input comes from an untrusted source such as a remote URL.
- Injection into a generated query or exported artifact through contract fields.
- Authentication and authorization flaws in `datacontract api`, or exposure of
  data through it that the caller should not reach.
- Vulnerabilities in the published Docker image or in the release pipeline.

The following are generally **out of scope**:

- Vulnerabilities in a data source, database, or third-party service itself.
  Please report those to that project or vendor.
- Dependency advisories with no demonstrated exploit path through this project.
  Dependency updates are handled by Dependabot; if you believe a dependency
  advisory *is* exploitable here, please describe that path and report it
  privately.
- Findings that require an attacker to already control the machine, the
  environment variables, or the configuration file.

## Verifying a Release

Releases are signed, so you can check that an artifact really came from our
pipeline:

- The sdist and wheel are signed with [Sigstore](https://www.sigstore.dev/), and
  the signature bundles are attached to each
  [GitHub release](https://github.com/datacontract/datacontract-cli/releases)
  next to the artifacts they cover.
- Docker images are signed keylessly with
  [cosign](https://github.com/sigstore/cosign) and ship an SBOM and build
  provenance. Verify the signature with:

  ```bash
  cosign verify datacontract/cli:<version> \
    --certificate-identity-regexp 'https://github.com/datacontract/datacontract-cli/.*' \
    --certificate-oidc-issuer https://token.actions.githubusercontent.com
  ```
