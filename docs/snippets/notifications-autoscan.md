```yaml
notifications:
  targets:
    - type: autoscan
      url: http://autoscan:3030
      trigger: manual            # optional; defaults to /triggers/manual
      username: ${AUTOSCAN_USER:-}
      password: ${AUTOSCAN_PASS:-}
      rewrite:
        - from: ${DESTINATION_DIR:-/data/destination}
          to: /mnt/unionfs/Media
        - from: /data/destination
          to: /Volumes/Media
      timeout: 10
      verify_ssl: true
```

