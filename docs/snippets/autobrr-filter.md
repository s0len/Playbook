```toml
[[filters]]
name = "F1 1080p MWR"
enabled = true
priority = 10
match_releases = [
  "(?i)(F1|Formula.1).*2025.*Round\\d+.*(FP\\d?|Qualifying|Sprint|Race).*1080p.*MWR"
]
include = ["f1-seasonal"]
actions = [
  { type = "push", target = "qbittorrent", category = "sports/f1" },
  { type = "exec", command = "/usr/local/bin/notify-new-torrent.sh" }
]
required_words = ["mkv", "x264"]
excluded_words = ["480p", "cam"]
max_size = "15 GB"
```

