# PF App Server dev delivery

Product source: `a5095e8b43a64382899a7098913398ffaf6cc9db`.
Dev archive: `processforge-v1.2.0-dev-20261019-a5095e8.zip`.
SHA256: `8deca3358237605f2d091893cc5d997b3e220776ae0109c9f979df123ac46a5f`.

Foreground server consoles show the PF logo, version and purpose. A disconnected
HTTP response closes that connection without retrying the response or accepted
event; ordinary application errors retain their existing behavior. The monitor
remains separate future work.

The dev candidate was built from a clean checkout and installed successfully.
Managed payload and preserved local configuration were verified. Current-launch
E2E confirms background operation without a server window and continued readiness
after aborted GET connections. The windowless launcher uses an existing platform
configuration option; shared server commands and Linux code remain unchanged.

Verification includes before/after response-disconnect regression, independent
source and device-plan review, native archive quick, extracted operator/checksum/
schema/cleanliness checks, installed/Runtime checks and user visual confirmation.
The archive has exactly four entries differing from its previously qualified
baseline; the other 1393 entries are identical. Qualification is differential.
Historical failed full runs remain failures. The reviewer's fixture permission
failure was preserved and its explicit operator-rerun condition was satisfied.

Actual login-time observation and connected-host code reload are outside this
acceptance. No stable release or branch merge was published. This receipt is
committed separately from the unchanged product source identified above.
