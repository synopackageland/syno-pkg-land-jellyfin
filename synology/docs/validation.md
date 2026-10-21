# Validation scope

## Intel HWA development acceptance

The unpublished source-override build uses SDK `5f69ba084dd2a4a7826cecb340b845d540c21f2e`, CLI `71ef896f62b7a12af194f593f4840aa5125355ff` and adapter
code `4c85b1377f866eb7d1fa078810cfb2d721ada910`. Published 0.20.0 dependency pins stay unchanged; this does not certify
a released dependency build with GPU support. The digest-pinned official image
was cached; this is not an uncached registry-pull acceptance.

A fresh native installation with empty App volumes on Intel Celeron J4025,
DSM 7.4 and Container Manager 24.0.2 initialized VAAPI automatically after the
upstream FFmpeg probe. The DSM-retained native package identity was left in place.
Readback showed the nonroot package UID, native videodriver supplementary GID,
only renderD128 mapped with rw access, read-only media, no privileged container,
cap_drop ALL and no-new-privileges. DSM added NET_BIND_SERVICE to the bounding
set; effective, permitted and ambient capabilities remained zero.

A synthetic 30-second H.264 1080p source was requested through Jellyfin's real
HTTP playback-transcode route at 720p. Automatic VAAPI used h264_vaapi, software
used libx264, and optional native QSV used h264_qsv. All returned HTTP 200 and
complete outputs that decoded without errors. Each run removed only the
package-private transcode cache and captured distinct new FFmpeg logs.

| Encoder | Container CPU seconds | Mean container CPU |
| --- | ---: | ---: |
| Automatic VAAPI | 4.00 | 10.48% over 38.18 s |
| Software | 29.40 | 48.54% over 60.57 s |

100% means one CPU core. CPU time fell about 86% for this one clip; these are
container-counter deltas using Docker's sample timestamps, including App work.
They are not a sustained-load or image-quality benchmark. Native QSV was restored
to VAAPI after its successful optional test.

Native package stop/start completed successfully. Readback preserved the native
GID and render-only mapping, and another real playback transcode used h264_vaapi
with a complete, error-free client decode. Native uninstall and independent
readback then confirmed the test package, project, containers, volumes and media
share absent. The package identity and official container engine were retained;
no daemon, mirror, CA, DSM setting or reboot was needed.

A separate no-GPU DSM 7.3.2 installation using the same development SPK emitted
software status, no GPU devices or added supplementary groups, and encoding type none.
Real 30-second playback used libx264, returned HTTP 200 and decoded completely.
Native uninstall and independent readback confirmed the test package, containers,
project volumes and media share absent; DSM package identity and the official
container engine were retained.

## Released dependency refresh

CLI/templates/SDK/App 0.20.0, executor/v0.20.0 and UI 0.12.5 are used without
source overrides. npm lock integrity matches the public registry. The unchanged
x86_64 initial SPK version passes affected tests, check, build and inspect with
`findings=[]`. The official image and adapter behavior are unchanged.

Fresh installation on DSM 7.3.2 selected an owned synthetic-media share with
read-only package-account ACL. Native start succeeded. DSM main-menu sign-in,
media read/playback and native stop/start passed. Native uninstall was followed
by independent readback: package, containers, project, test-only volumes and
share were absent. DSM-retained package identities were left in place.

The device's native registry preflight reported `COMPOSE_IMAGE_DENIED`, while
installation/start completed successfully using the pinned cached image. This
is not a clean image-pull test. No daemon, mirror, CA or DSM settings changed.
Browser acceptance used certificate-error tolerance only in its disposable test
browser. Other lifecycle and identity boundaries below retain their earlier
bounded evidence; no reboot or broader certification was repeated.

Inspect confirms `host-uid-listener-health` with `/System/Ping` HTTP 200.

The release uses published CLI/templates/SDK/App 0.20.0, executor/v0.20.0 and
UI 0.12.5. Source overrides are not used for release builds. The historical device
acceptance below used the reviewed development implementation; the release
dependency refresh is verified separately before publication.

## Verified boundaries

- The pinned official Jellyfin 12.2 image loads the original SSO Authentication
  4.0.0.4 DLLs and reaches a `Healthy` response as a non-root UID. Plugin
  `targetAbi` 10.11.0.0 is a minimum ABI, not an exact version equality check.
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

## SDK regression and remaining boundaries

A fresh `12.2-0001` install using the reviewed development implementation selects the
fixture share and starts through the native package lifecycle. Native stop exits
the container; native start returns success and remains running afterward, with
`/System/Ping` HTTP 200 and the gateway serving requests. No manual start hook is
used. Inspect reports `host-uid-listener-health`: the CLI passes the declared HTTP
health to the daemon, which waits through the startup-listener handoff.

Installation/start still emit a registry probe `COMPOSE_IMAGE_DENIED` message;
the pinned image is already cached and the native operations succeed. This
regression does not prove an uncached registry pull.

A focused browser run opens the DSM menu and verifies one-click administrator
SSO, signed-sub JIT and native administrator policy. The opt-in authenticated
denied-account browser test passes with HTTP 403 and the stable HTML error code
`dsm_app_privilege_denied`.
Only this package's App privilege fixture is changed, then restored with readback.
Anonymous refusal and ordinary-user media/account tests retain their earlier
acceptance evidence from SDK `6f58211ce8cd0f6a7bbb41ed4dac883fca036e5c` and CLI
`86631612d385e58cb8745ba1431eb5ca4b087cb5`; the ordinary-user tests were not rerun in the release refresh.
Build `0002` was only an unpublished upgrade-test fixture;
`12.2-0001` remains the initial package version.

The SDK automatic browser bridge redirects the plugin's hidden initialization
iframe and causes repeated SSO. The wrapper uses native login branding's one-click
DSM sign-in instead. App/TV clients use Jellyfin's native authentication, but this DSM-only ingress
does not provide a client passthrough. Native client access is unsupported; Web
SSO does not establish client compatibility. Native session lifetime and DSM
account deletion/revocation remain separate boundaries.

Anonymous gateway requests receive 401. Set `JELLYFIN_E2E_DENIED=1` only for the
separate denied-account run after an administrator denies the fixture account
this package, then restore the previous App privilege rule. The expected status
is 403; do not weaken the assertion for verification failures.

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
These earlier resource observations cover a two-second software fixture. The
reviewed HWA candidate and its separate device evidence are described above.
DLNA remains disabled and needs explicit discovery/multicast ingress beyond the
loopback host policy.

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
The expected denied status is 403. Keep profiles, screenshots and report output
ignored.
