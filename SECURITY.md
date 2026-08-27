# Security policy

## Reporting a vulnerability

Please report security issues **privately**, through GitHub's private
vulnerability reporting: open
<https://github.com/nicholsn/lokf/security/advisories/new>, or use the
**Report a vulnerability** button under the repository's **Security** tab.

Do not open a public issue for a vulnerability, and do not include exploit
details in a pull request.

LOKF is maintained by one person as an open-source side project, so please
expect a first response in days rather than hours. There is no bounty.

## Scope

In scope:

- The `lokf` package and CLI (`src/lokf/`) — in particular anything reachable by
  parsing an untrusted bundle: `lokf convert`, `lokf query`, `lokf validate`,
  `lokf propose`, the `lokf serve` HTTP surface, and the `lokf-mcp` server.
- The release pipeline (`.github/workflows/publish.yml`) and the published
  artifacts on PyPI.
- The scaffold (`lokf new`) and the agent skills it installs, where they could
  cause an agent to execute something the author did not intend.

Out of scope:

- The documentation site (`web/`), which serves static content only.
- A bundle that is merely *wrong* — validation is closed-world by design, but a
  producer's incorrect data is a data problem, not a vulnerability.

## What LOKF assumes about a bundle

A LOKF bundle is markdown plus YAML frontmatter, and consumers are specified to
be permissive (unknown keys and types MUST NOT cause rejection). Treat a bundle
from a third party as untrusted input: frontmatter is read with
`yaml.safe_load` (and ruamel's round-trip loader where `lokf propose --apply`
rewrites it), never a loader that constructs arbitrary objects; and a concept's
`resource`, `endpoint`, and relation targets are identifiers, not instructions
to fetch or execute. If you build an agent on
top of LOKF, the same applies to a bundle's prose — `AttestedComputation`
carries a *sanctioned* recipe precisely so an agent does not have to trust
free-form text.

## Supply chain

- PyPI releases use Trusted Publishing (OIDC); no long-lived API token exists.
- Releases carry PEP 740 attestations, verifiable at
  `https://pypi.org/integrity/lokf/<version>/<file>/provenance`.
- GitHub Actions are pinned to commit SHAs; Dependabot updates them weekly.
- `uv.lock` is committed, and CI runs with `--locked` so the tested and released
  dependency sets are the same.
