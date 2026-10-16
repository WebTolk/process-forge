# Runtime operation scope experiment, 2026-10-16

The experiment did not justify expanding the parsed-YAML request scope around an entire Runtime tick. The existing implementation and limits were retained.

A fixture with four genuinely captured worker attempts and 500 generated historical assignments was measured in five alternating ordinary pairs. The median wall time was 2.091864 seconds without the outer scope and 2.155297 seconds with it. A separate counted pass recorded 538 loads, 517 parses, 21 hits and 6,940,506 retained text bytes. Results and 529 protected metadata files were unchanged. Timings trended downward and the existing Runtime was active; this is a negative fixture result, not a quiet installed comparison.

The installed development Runtime still consumed 87.948932 percent of one core in a later 45-second window. Overlapping stack groups show that scheduler collection, assignment discovery, stage projections and HTTP ingress perform distinct work. A scope in the scheduler cannot share values with a separate HTTP request.

Independent bounded investigations found two further facts. Objective lookup parsed 1,421 documents without cache hits; a streaming prototype was slower, so it was rejected as a performance fix. The journal owner has one index slot: interleaving two journals evicts the previous snapshot and repeats JSON parsing. This confirms a separate repair candidate, without qualifying a production implementation or a Runtime speed improvement.

The journal provider returned additional files inline. Automatic collection rejected the missing separate files; a serial curator preserved the original report and produced attributable artifacts in a new native manual recovery attempt. The failed attempt remains in history. Capture, report acknowledgement and acceptance remain distinct.

No product code, Runtime lifecycle, public release, diagnostic budget or broad smoke inventory was changed by this experiment. Further journal changes require their own design, implementation and independent review. Public 1.2.0 remains subject to a detailed report and explicit approval.
