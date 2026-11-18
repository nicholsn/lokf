#!/usr/bin/env bash
# Build three fresh `lokf new` sites with this checkout's toolkit, then inspect
# their static outputs. Used by both PR and release workflows.
set -euo pipefail

repo_root="$(cd "$(dirname "$0")/.." && pwd)"
smoke_dir="${1:?pass an empty output directory, such as \$RUNNER_TEMP/lokf-site-smoke}"
export LOKF_EXPORT_EXECUTABLE="${LOKF_EXPORT_EXECUTABLE:-$repo_root/.venv/bin/lokf}"
if [[ ! -x "$LOKF_EXPORT_EXECUTABLE" ]]; then
  echo "local LOKF exporter is not executable: $LOKF_EXPORT_EXECUTABLE" >&2
  exit 1
fi

cd "$repo_root"
mkdir -p "$smoke_dir"
uv run --locked lokf new root-kb --path "$smoke_dir" --base-iri https://kb.example.com/
uv run --locked lokf new project-kb --path "$smoke_dir" --base-iri https://owner.github.io/project-kb/
uv run --locked lokf new domain-kb --path "$smoke_dir" --base-iri https://ex.org/kb/
cp "$smoke_dir/project-kb/lokf.views.example.yaml" "$smoke_dir/project-kb/lokf.views.yaml"

# The domain fixture is copied into a scaffolded site. Its vocabulary stays
# at the repo path because its relative import intentionally reaches lokf.yaml.
domain_site="$smoke_dir/domain-kb"
rm "$domain_site/knowledge/glossary/active-user.md" "$domain_site/knowledge/metrics/weekly-active-users.md"
cp tests/fixtures/domain-vocabulary/prefixed-target/*.md "$domain_site/knowledge/"
cp tests/fixtures/domain-vocabulary/prefixed-target/lokf.views.yaml "$domain_site/"
uv run --locked python - "$repo_root/tests/fixtures/domain-vocabulary/prefixes-the-bundle.yaml" "$domain_site/pyproject.toml" <<'PY'
import json
import sys
from pathlib import Path

Path(sys.argv[2]).write_text('[tool.lokf]\nschema = ' + json.dumps(sys.argv[1]) + '\n')
PY

for name in root-kb project-kb domain-kb; do
  (
    cd "$smoke_dir/$name"
    npm install --no-audit --no-fund
    if [[ "$name" == root-kb ]]; then node --test tests/*.test.mjs; fi
    npm run build
  )
done

uv run --locked python scripts/verify_scaffold_site.py "$smoke_dir/root-kb" /
uv run --locked python scripts/verify_scaffold_site.py "$smoke_dir/project-kb" /project-kb
uv run --locked python scripts/verify_scaffold_site.py "$domain_site" /kb domain
