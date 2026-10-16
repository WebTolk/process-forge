# Runtime service-state publication, 2026-10-16

Status: independently accepted source correction. Installed Core remains the
previous private dev 75 until a separate clean cumulative archive/update.
This does not qualify actual Runtime CPU, the connected host or public 1.2.0.

A native restore failed with Windows error 5 while replacing service.json.
The created PID exited; native stale/no-live-owner readback preceded one
controlled recovery. Independent held-destination-reader tests reproduce the
original error 5 mechanism 5/5; they do not identify the historical holder.
No ACL, OS setting, service registration or old temporary file was changed.

The concrete Core RuntimeServiceStateWriter owns the existing JSON publication;
the service function delegates. Preparation, UTF8/native newline, sorted/indented
JSON, one unique temporary file and atomic replacement stay unchanged. Only
native Windows replacement conflicts 5/32/33 may retry, after the first failure,
for a private 50ms retry-admission window with at most five retries. Sleeps use
the remaining time. This is not a bound on an uninterruptible OS call or thread
scheduling. Successful replacement remains success after a slow call.

Unknown/non-Windows/preparation failures stay immediate. Repeated eligible
permanent denial raises the original error; destination is never deleted and
there is no non-atomic fallback, preparation replay, cache or new public knob.
Other lifecycle, singleton, authorization and original smoke assertions/timeouts
retain their AST. Core imports without CLI/Host/transport.

Executor 26controls and independent 41controls pass. The initial review rejected
one NEW test observation (R1): it counted preparation before the retry window.
The correction records first failed replacement and verifies conflict/release
order while retaining native success, same temp and exact bytes. A60ms
preparation-delay replay fails the previous assertion and passes the correction;
the two production files are unchanged. The original unwrapped primary
singleton/orphan smoke passes 2.101651s after R1, without allocator/PID/timeouts
patches. Worker sandbox pre/post tasklist-denial failures remain recorded.

Source, archive, installed bytes, restored Runtime and actual connected host
remain distinct. High Runtime CPU and journal/catalog costs require their own
measured corrections. Public 1.2.0 requires full cumulative qualification,
a detailed ready-candidate report and separate user approval.
