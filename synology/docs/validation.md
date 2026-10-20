# Development acceptance

This is a development integration, not a publishable SPK. Dependencies remain
pinned to released 0.19.0. Shared-folder acceptance uses SDK commit
`6f58211ce8cd0f6a7bbb41ed4dac883fca036e5c` and CLI commit
`86631612d385e58cb8745ba1431eb5ca4b087cb5` through a temporary source build.
No release, registry or catalog entry is part of this change.

## Verified boundaries

- The pinned official Jellyfin 12.2 image loads the original SSO Authentication
  4.0.0.4 DLLs and reaches a `Healthy` response as a non-root UID. Plugin
  `targetAbi` 10.11.0.0 is a minimum ABI, not an exact version equality check.
- Source CLI type checking/build succeeds with declaration output disabled. Its
  normal declaration build encounters TS2742 in the optional e2e helper's inferred
  model type. No CLI source is patched for the local executable build.
- SDK declarations pass check, SPK build and inspect on Linux.
- Native installation selects an existing share. DSM ACL readback grants the
  package account read access. Container mount inspection reports `/media` with
  `rw=false`; the package UID reads the synthetic fixture and cannot create a file.
- Development upgrade `12.2-0001` to `12.2-0002` preserves configuration, the
  signed-sub JIT account and the saved media-share selection.

The browser suite passed both DSM session setups plus three tests: administrator
SSO, ordinary-user SSO, and anonymous refusal. Both users streamed the synthetic
MP4 with a 4096-byte HTTP 206 response, signed out through the native User Menu,
closed the App, reopened it from the DSM main menu, and signed in again with DSM. Identity readback confirmed distinct signed-sub
usernames and the expected administrator policy. Ordinary users need an explicit
DSM App privilege grant; enabling `dsm-users` does not grant that permission.

## Known blockers

Native start can report success and subsequently lose the gateway. Jellyfin's
startup-status server temporarily listens on the final port, then closes it
before the main server binds it again. Device socket observations show the
loopback upstream port disappearing during this transition. The SDK host-network
supervisor accepts the first listener, then treats the missing port as a fatal
`COMPOSE_NETWORK_NOT_READY` policy failure. SDK host readiness currently does not
check `compose.web.health`, unlike bridge readiness. The wrapper declares
`/System/Ping` (200 only in the main application; the startup-status server
returns 503), so a future SDK host HTTP gate can distinguish these phases. This must be fixed in the
SDK; increasing the total startup timeout does not resolve early admission.
No guard is disabled and runtime does not gain root privileges. To isolate OIDC
compatibility, acceptance can start the existing generated package-account start
script only after the backend is stable. This diagnostic action is not a passing
native lifecycle result or a production workaround.

The SDK automatic browser bridge redirects the plugin's hidden initialization
iframe and causes repeated SSO. The wrapper uses native login branding's one-click
DSM sign-in instead. App/TV clients use Jellyfin's native authentication, but this DSM-only ingress
does not provide a client passthrough. Native client access is unsupported; Web
SSO does not establish client compatibility. Native session lifetime and DSM
account deletion/revocation remain separate boundaries.

Anonymous gateway requests receive 401. The authenticated denied-account browser e2e expects 403 and fails with actual
503. Admission remains closed. The SDK OIDC CGI does not classify
`api.ErrAppPrivilegeDenied` as `access_denied`, so it produces
`temporarily_unavailable`. Preserve the 403 assertion as a regression test and
fix the mapping in the SDK. Set `JELLYFIN_E2E_DENIED=1` only for the separate
negative run after an administrator denies the fixture account this package,
then restore the previous App privilege rule.

The image's default healthcheck targets 8096. The wrapper declares an explicit
check of the configured loopback port and the exact `Healthy` response body.
The first media scan is requested from the final server because refresh is
asynchronous; stopping a temporary setup server immediately after requesting it
can cancel the scan.

The retained-volume regression first failed when SDK secrets were regenerated
because the plugin retained its old client secret. The adapter now retains its
native bootstrap credential mode 0600 in the private named volume and uses the
supported API to refresh provider configuration when the SDK client changes.
A two-boot Linux Docker integration test verifies this behavior without external
network access. Native data and credentials remain subject to named-volume retention.

## Resource and lifecycle limits

The container has one pinned CPU and a 1 GiB memory ceiling. One observed startup
peak was 615526400 bytes (about 587 MiB). Across twelve bounded startup samples,
the largest observed CPU value was 99.85% of one core.
A bounded software-transcode probe returned HTTP 200 and 35704 MP4 bytes;
server logs confirmed libx264, scaling to at most 160 by 90, and FFmpeg exit 0.
These observations cover a two-second fixture, not a sustained-load benchmark. No GPU or DLNA is enabled.
Hardware transcoding needs a reviewed SDK device/cgroup authority for `/dev/dri`;
DLNA needs explicit discovery/multicast ingress beyond the loopback host policy.
Neither capability is implemented or estimated as production-ready here.

Named volumes and selected shares are retained by the SDK uninstall contract,
including delete-data requests. Test cleanup must remove only the exact disposable
owned volumes and share, then read back absence. Keep DSM's retained package
identity. Browser and private API probes used an explicit test-only certificate
exception over SSH-forwarded HTTPS; they do not prove certificate validity.

## Reproduce browser acceptance

Prepare a disposable existing share containing a two-second synthetic H.264/AAC
video named `SSO Fixture.mp4`. Select that share in the install wizard, grant the
package account read access in **System internal user**, and grant the ordinary
fixture account this package's **Application Privileges**. If setup ran before
the share ACL was granted, grant access and use Package Center Repair before
starting again. Selection and permission are independent.

Use the exact development toolchains above and private `admin`/`reader` account
JSON files through the shared DSM login helper. Run the ordinary suite with
`npm run e2e`. Run the opt-in denied-account test separately with
`JELLYFIN_E2E_DENIED=1 npm run e2e -- --grep 'denied DSM'` after denying only this
package to the reader account; restore the previous rule and read it back.
The expected denied status is deliberately 403, so this run remains red against
the current SDK's actual 503. Keep profiles, screenshots and report output ignored.
