#!/usr/bin/env sh
set -e

EXCLUDE_DIRS="slurm_client frontend deployment"

for dir in */ ; do
  dir="${dir%/}"

  # skip excluded directories
  for exclude in $EXCLUDE_DIRS; do
    [ "$dir" = "$exclude" ] && continue 2
  done

  # only proceed if a compose file exists
  if [ -f "$dir/docker-compose.yml" ] || [ -f "$dir/compose.yml" ] || [ -f "$dir/compose.yaml" ]; then
    echo "▶ Bringing up $dir"
    (
      cd "$dir"
      docker compose up -d
    )
  else
    echo "⏭ Skipping $dir (no compose file)"
  fi
done

