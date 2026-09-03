#!/usr/bin/env python3
from process_execution_smoke_support import scenario

if __name__ == "__main__":
    scenario("blocks_missing_gate")
    print("PASS: missing gate blocks work transition")
