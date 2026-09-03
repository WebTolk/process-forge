#!/usr/bin/env python3
from process_execution_smoke_support import scenario

if __name__ == "__main__":
    scenario("start_no_guessing")
    print("PASS: work start without stage guessing")
