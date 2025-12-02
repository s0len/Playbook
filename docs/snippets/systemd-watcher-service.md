```ini
[Unit]
Description=Playbook watcher
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
WorkingDirectory=/opt/playbook
EnvironmentFile=/etc/playbook.env
ExecStart=/opt/playbook/.venv/bin/python -m playbook.cli --config /opt/playbook/config/playbook.yaml --watch
Restart=on-failure
RestartSec=5s
User=playbook
Group=playbook

[Install]
WantedBy=multi-user.target
```

