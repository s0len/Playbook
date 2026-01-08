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
      verify_ssl: true                   # ⚠️ SECURITY WARNING: Setting false disables SSL/TLS verification and exposes you to MITM attacks - only for development with self-signed certs
```

