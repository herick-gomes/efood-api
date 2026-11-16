"""Keep Docker/pip and Vercel dependency manifests identical."""

import tomllib
from pathlib import Path

root = Path(__file__).resolve().parent.parent
project = tomllib.loads((root / "pyproject.toml").read_text())["project"]
requirements = {
    line.strip()
    for line in (root / "requirements.txt").read_text().splitlines()
    if line.strip() and not line.startswith("#")
}
if set(project["dependencies"]) != requirements:
    raise SystemExit("Keep pyproject.toml project.dependencies and requirements.txt in sync.")
print("Deployment dependency manifests match.")
