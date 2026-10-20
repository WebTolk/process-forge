# Focused regression cases

The new `tests/runtime_monitor/test_uptime.py` provides 36 cases against the
actual monitor module, covering:

- zero duration and complete-minute truncation;
- minute, hour, day, month, and year boundaries;
- January 31 clamping to February in ordinary and leap years;
- one minute before a monthly anniversary and leap-day annual anniversaries;
- UTC normalization of timezone-aware observations and durations over 99 years;
- unavailable, boolean, negative, nonnumeric, infinite, NaN, malformed, naive,
  and datetime-overflow inputs;
- compact output at 35/80 columns, the field legend, and `unknown` rendering;
- unchanged numeric snapshot values after rendering.

Before implementation: 35 cases failed and one existing unknown-render case
passed. After implementation: all 36 passed. The existing runtime-monitor smoke
remains part of the complete public PF source suite.
