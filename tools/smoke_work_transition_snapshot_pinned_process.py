#!/usr/bin/env python3
from process_execution_smoke_support import scenario

if __name__ == "__main__":
    scenario("snapshot_pinned")
    print("PASS: work transition uses pinned process")
