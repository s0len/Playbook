```yaml
notifications:
  mentions:
    formula1: "<@&222333444555666777>"
    default: "@here"
  targets:
    - type: discord
      webhook_url: ${DISCORD_WEBHOOK_URL}
      mentions:
        formula1: "<@&999>"
    - type: autoscan
      url: http://autoscan:3030
      trigger: manual
      username: ${AUTOSCAN_USERNAME:-}
      password: ${AUTOSCAN_PASSWORD:-}
      rewrite:
        - from: ${DESTINATION_DIR:-/data/destination}
          to: /mnt/unionfs/Media
        - from: /data/destination
          to: /Volumes/Media
      timeout: 10
      verify_ssl: true
```

