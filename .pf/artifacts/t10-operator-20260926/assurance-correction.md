# Assurance correction

The initial metrics smoke used a nanosecond-derived floating timestamp as its
exact comparison time against an ISO string rounded to microseconds. Depending
on rounding it could incorrectly construct a future timestamp. The fixture now
uses datetime's microsecond timestamp, matching its serialized representation.
Production future timestamps still fail closed. This changes only the new test
within declared scope; the immutable implementation evidence remains historical.

The existing monitor's three actual loopback requests did not all occur during
the concurrent suite. Its 0.75-second PID/network budgets intentionally produce
uncertainty; rerun this timing-sensitive integration alone before qualification.
No production timeout relaxation or hidden success substitution is made.
