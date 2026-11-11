"""Shared pytest configuration for the backend tests."""

# Cloud-sync tools (iCloud, OneDrive) create conflict copies such as
# "test_units 2.py". They are ignored by git but would otherwise be collected
# and run as duplicate, possibly stale, tests. fnmatch "*" also spans folders.
collect_ignore_glob = ["* [0-9].py", "* [0-9][0-9].py"]
