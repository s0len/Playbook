```cron
0 * * * * /usr/bin/docker run --rm \
  --name playbook-hourly \
  -e SOURCE_DIR="/downloads" \
  -e DESTINATION_DIR="/library" \
  -e CACHE_DIR="/cache" \
  -e LOG_DIR="/logs/playbook" \
  -v /srv/playbook/config:/config \
  -v /srv/downloads:/data/source \
  -v /srv/library:/data/destination \
  -v /srv/cache:/var/cache/playbook \
  -v /srv/logs:/var/log/playbook \
  ghcr.io/s0len/playbook:latest --dry-run
```

