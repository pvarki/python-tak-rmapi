# CoT subscription guard

The default container entrypoint runs `takrmapi serve`, supervising Gunicorn and a
separate `takrmapi watch-subscriptions` process. The watcher uses PyJNIus and Ignite
subscription notifications to inspect each connection's TLS certificate. Java
callbacks only enqueue work; remote calls run under the existing shared JNI lock.
Notifications flush on Ignite's 25 ms timer. This keeps delivery to a failed client
outside cache-update locks that would otherwise block cluster topology changes.
Live scans every five seconds cover startup, missing notifications, queue overflow,
and registrations or revocations that change while clients remain connected.

Revocation records the SHA-256 fingerprints of both identities before contacting
TAK or CFSSL: the main RASENMAEHER certificate (`_rm`) and the TAK client-package
certificate. The SQLite denylist lives in
`TI_RMAPI_PERSISTENT_FOLDER/revocations.sqlite3` and survives restarts. Both
registrations and existing connections are removed through JNI. Incomplete
revocation returns HTTP 503 and must be retried; the denylist remains effective
even if registration removal or the CFSSL call fails.

The watcher disconnects expired, revoked, and (by default) unregistered certificate
identities. Registration is checked against TAK's file authentication users by
certificate fingerprint, never the client-supplied CoT UID or callsign. The denylist
takes precedence over registration and is retained until certificate expiry.
Restarted or stalled watchers are replaced with a fresh process and JVM. The health
endpoint reports unhealthy until a live scan completes, and again if the last scan
is more than 60 seconds old. JVM startup has a 180-second recovery deadline.

TAK's default Ignite client and connection timeouts are five minutes, as defined
in its [Ignite configuration schema](https://github.com/TAK-Product-Center/Server/blob/5187abd46d827d37cfc5708805eced197a837e49/src/takserver-common/src/main/xsd/TAKIgniteConfig.xsd). After a hard
client crash, saving user registrations can wait for the failed node. This bridge
bounds removal and guard service calls to five seconds, retains the denylist, and
returns an incomplete revocation for retry. A timed-out server operation may still
finish later. Shorter Ignite timeouts must be configured on TAK itself if faster
registration recovery is required.

Configuration uses the `TI_` prefix:

| Variable                                   | Default                                 | Purpose                                                                                                                                                                                                            |
| ------------------------------------------ | --------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `TI_SUBSCRIPTION_GUARD_ENABLED`            | `true`                                  | Start the watcher and require its health.                                                                                                                                                                          |
| `TI_SUBSCRIPTION_GUARD_REQUIRE_REGISTERED` | `true`                                  | Require a TAK file-user fingerprint. Set `false` for deployments that intentionally permit certificates authenticated solely by LDAP or another provider. Revoked and expired certificates are still disconnected. |
| `TI_SUBSCRIPTION_GUARD_INTERVAL`           | `5`                                     | Seconds between live scans; must be greater than zero and at most 30.                                                                                                                                              |
| `TI_SUBSCRIPTION_GUARD_HEARTBEAT`          | `/run/takrmapi/subscriptions.heartbeat` | Container-local health marker; its parent must be writable.                                                                                                                                                        |

Only one watcher may hold the lock in a shared persistent volume. Custom commands
that bypass the default entrypoint must arrange to run the watcher themselves, or
explicitly disable it and its health requirement.

This is asynchronous enforcement after TLS authentication. A reconnect can send
CoT before the disconnect completes. OCSP remains responsible for rejecting fresh
handshakes, but resumed sessions can bypass a fresh OCSP check and receive renewed
session tickets. Therefore an OCSP `REVOKED` response is insufficient reason to
remove a fingerprint from the denylist. A TAK-side authorization check before CoT
processing would be needed to eliminate that brief access window entirely.

## Validation

Validated with TAK Server 5.8-RELEASE-69 on the Java 17 JRE runtime in an isolated
Podman Compose project, `takanon`. The image used the existing runtime dependencies
with the updated package source and default entrypoint. Client tests used
CFSSL-signed EC P-256 certificates, trusted `/ca_public/ca_chain.pem`, and verified
the server hostname.

| Check                                                     | Result                                                                                                                                    |
| --------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------- |
| Local pytest suite                                        | 67 passed, 9 existing skips; 43.73% coverage against a 25% requirement.                                                                   |
| Static checks                                             | Strict mypy and the repository's prek hooks passed.                                                                                       |
| Both certificate identities, TLS 1.2/1.3, ports 8089/8090 | Valid clients connected.                                                                                                                  |
| Persisted revocation while registrations remained present | Both existing connections disconnected on reconciliation.                                                                                 |
| Reconnects before OCSP changed to `REVOKED`               | Fresh and resumed connections disconnected.                                                                                               |
| Reconnects after OCSP changed to `REVOKED`                | All eight fresh handshakes rejected by TAK; resumed connections disconnected by the guard.                                                |
| Five consecutive resumptions using renewed tickets        | Every connection disconnected.                                                                                                            |
| Two valid control clients                                 | Both remained connected throughout enforcement and watcher restart.                                                                       |
| Forced watcher process crash                              | HTTP health became unhealthy, the replacement recovered in about six seconds, and its startup scan closed the waiting revoked connection. |
| Registration updates during stale-client recovery         | Two completed; two returned a retryable failure after approximately five seconds each.                                                    |
| Cleanup                                                   | All disposable certificates revoked through CFSSL, temporary private keys removed, and the guard healthy at completion.                   |

The final run closed 29 invalid reconnects in 17–85 ms. All 29 deliberately sent
early CoT messages reached the anonymous-group control before disconnection,
confirming that this mechanism reduces ongoing access but cannot provide an
authorization barrier before CoT processing. These timings describe one local run.
