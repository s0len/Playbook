# Gotchas & Pitfalls

Things to watch out for in this codebase.

## [2026-01-02 22:27]
Run tests from worktree with PYTHONPATH=src, not from main repo. The verification commands in spec use main repo path but tests should run from worktree to pick up correct code changes.

_Context: Integration testing subtask 5-1 - tests failed when run from /Users/solen/GitHub/Playbook but passed when run from worktree with PYTHONPATH=src_
