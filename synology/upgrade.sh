#!/usr/bin/env bash
# Merge an explicitly selected release and build the existing official-image wrapper.
set -euo pipefail
packaging=$(cd -- "$(dirname -- "$0")" && pwd)
repo=$(cd -- "$packaging/.." && pwd)
cd "$repo"
[[ $# == 2 && $1 =~ ^v?(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)(\.(0|[1-9][0-9]*))?$ ]] || {
  echo 'Usage: bash synology/upgrade.sh <[v]X.Y[.Z]> <build-number>' >&2; exit 2;
}
[[ -z $(git status --porcelain --untracked-files=normal) ]] || { echo 'Commit changes before upgrading.' >&2; exit 2; }
node "$packaging/version.mjs" "$1" "$2" --validate
git fetch --no-tags upstream "+refs/tags/$1:refs/synopkgland/selected-upstream"
commit=$(git rev-parse 'refs/synopkgland/selected-upstream^{commit}')
previous=$(node -e 'process.stdout.write(JSON.parse(require("fs").readFileSync(process.argv[1])).commit)' "$packaging/upstream-source.json")
git merge-base --is-ancestor "$previous" "$commit" || { echo 'Refusing upstream downgrade/divergence.' >&2; exit 2; }
git -c user.name=synopackageland -c user.email=synopackageland@gmail.com merge --no-ff -m "Merge upstream $1 [skip ci]" "$commit"
node "$packaging/update-image.mjs" "$1"
node "$packaging/version.mjs" "$1" "$2"
node -e 'const fs=require("fs"),p=process.argv[1],s=JSON.parse(fs.readFileSync(p));fs.writeFileSync(p,JSON.stringify({...s,commit:process.argv[2]},null,2)+"\n")' "$packaging/upstream-source.json" "$commit"
cd "$packaging"
python3 scripts/render.py
npm test
npm run check
npm run build
# Repeat OIDC compatibility and device acceptance before publishing a changed upstream version.
