# Validation scope

## 12.4-0002 SDK/CLI rebuild (blocked)

The repackage retains the official Jellyfin 12.4 image index digest and original
SSO plugin. SDK/App 0.38.2, CLI 0.41.6, templates 0.35.5 and executor/v0.38.2
are pinned without development overrides. There is no wrapper UI dependency.
The wizard declares the dedicated Jellyfin share (read-only media) and native
port selection. The upstream OIDC provider receives the selected loopback issuer
port using the documented SDK runtime binding; configuration fingerprints include
that port so retained App data is resynchronized when it changes.

`npm ci --ignore-scripts --offline --registry=https://registry.npmjs.org` passes
from integrity-checked official npm bytes; direct registry.npmjs.org requests
returned HTTP 403 on the build host, so the same official registry's
registry.npmjs.com endpoint supplied the initial downloads. The lock retains
canonical registry.npmjs.org URLs and official integrities. Four runtime tests,
five hardware-adapter tests, three version tests and the Go App-entry contract
package pass. CLI check passes with no warnings. Rendering is reproducible.
The Docker retention integration test is updated for the selected issuer port
but has not run for this rebuild.

CLI 0.41.6 blocks the SPK build with
`COMPOSE_STORAGE_INIT_INVALID: runtime port must reference install.ports`.
Its `dist/standalone/compose.js` `lockComposeImages` function passes
`installSettings` but omits `installPorts` when calling `readComposeApp`.
The earlier manifest-validation path passes both. SDK 0.38.2 correctly rejects
the missing port definition in `compose/plan.go`. The failure reproduces
offline by loading this valid manifest and calling
`lockComposeImages(manifest, 'x86_64', false)`; it is independent of registry
connectivity. No SDK/CLI patch or App-side workaround is included.

The initial image lookup also returned HTTP 403 from Docker Hub. The CLI's
documented metadata mirror transport advanced the build to the port-binding
failure without changing the upstream repository or pinned image digest.
No SPK was produced, so inspection and the SPK privacy scan are blocked.

The new minimal CLI-helper smoke suite retains the existing e2e suite and uses
Jellyfin's native `#loginPage` marker after DSM admission. A, N and X were all
executed against the designated test device with an existing non-admin account
from the project secrets file; none were skipped. All three failed before App
entry with browser `net::ERR_CERT_AUTHORITY_INVALID`. CLI `dsmTarget()` creates
the web engine without a certificate-trust configuration. This run does not
establish App authentication behavior. The existing installed package remains
12.2-0010 with DSM status `start_failed`; the blocked rebuild was not installed.
No accounts or device settings were changed. Device identity and raw traces
remain outside Git. A/N/X must be rerun on the rebuilt artifact after the CLI
port-binding fix and browser certificate trust are available.

The change is not approved for merge while build, inspect and device gates are
unmet. No release, catalog or CI change is included.

## 12.2-0006 port change

Four runtime tests, five hardware-adapter tests, three version tests and
published CLI 0.26.0 check/build/inspect pass locally. The built SPK declares
HTTPS 33443 consistently in `conf/resource`, `sso/gateway.json` and
`sso/native-nginx.conf`; its nginx listener no longer uses 29443. The regression
test fails against the previous 29443 declaration. The loopback issuer (29490),
streaming backend (29496) and bootstrap server (29497) are unchanged.
No NAS installation, upgrade or coexistence test has been run for this build.
Earlier device results below apply to their named builds only.

## 12.2-0006 SDK/CLI 0.28.0 pin

Pins moved to published CLI/templates/SDK/App `0.28.0` with `executor/v0.27.0`
(Go 1.26.10, UI 0.14.4 unchanged). `npm ci --ignore-scripts` installed the
locked packages; no source overrides were set. Ran locally on macOS:
`npm test` (runtime, hardware-adapter and version tests pass),
`synopkgland check --json` (ok), `synopkgland build --arch x86_64 --json`
(produced `SynoPkgJellyfin-12.2-0006-x86_64.spk`) and `synopkgland inspect`
(ok, no findings). `tests/retention_test.py` needs a storage-init binary and
Docker and was not run. The SPK is unsigned. No NAS installation, upgrade or
slow-start test has been run for this build, so slow-NAS behavior is
unverified on a device.

## Release inputs

Jellyfin `12.2-0002` uses published CLI/templates/SDK/App `0.21.0`,
`executor/v0.20.0`, and UI `0.12.5`. The npm lock matches public registry
integrities. SDK/App `0.21.0` is selected because published CLI `0.21.0` maps
that SDK version to the existing executor release. SDK/App `0.21.1` is newer,
but this CLI instead requests the nonexistent `executor/v0.21.1` for it.
Release builds use published modules without local source substitutions.

Affected Python and Node tests, Linux check/build/inspect pass. Inspect reports
`findings=[]`, `host-uid-listener-health`, and `/System/Ping` HTTP 200. GPU
inspection reports native `video-driver`, GID source `videodriver`, runtime
Intel render-node discovery, and software fallback. The official Jellyfin
12.2 image and original SSO Authentication 4.0.0.4 plugin remain hash pinned.
Plugin `targetAbi` 10.11.0.0 is a minimum ABI, not exact version equality.

## Release device verification

Upgrading the published `12.2-0001` SPK to the release artifact on Intel
Celeron J4025 / DSM 7.4 retained the native system configuration byte for byte,
a package-private data marker, and the selected read-only media share. DSM
main-menu entry and one-click sign-in created a signed-sub native administrator
session with the expected role. Native
GPU discovery supplied renderD128 and videodriver GID; the adapter selected VAAPI
automatically. Native stop/start both returned success; stop left no running
package container, and restart retained VAAPI, the render mapping and GID with
healthy HTTP readback. Real 30-second H.264 1080p to 720p playback used `h264_vaapi`,
returned HTTP 200 and 6,192,959 bytes, and decoded completely without errors.

A fresh installation of the same release artifact on a no-GPU DSM 7.3.2 machine
uses the package UID with no GPU devices or supplementary groups, encoding
`none`, and read-only media. A synthetic 30-second H.264 1080p source played
through Jellyfin's real HTTP transcode route at 720p using `libx264`:
HTTP 200, 5,544,017 bytes, and a complete error-free client decode. Native
uninstall and independent readback confirmed the package, container, project,
owned volumes and disposable share absent; the retained DSM identity and
official Container Manager remained.

The official image was cached. The native registry preflight can emit
`COMPOSE_IMAGE_DENIED` even when installation/start succeeds with that image;
these observations do not establish an uncached image pull. Test-browser
certificate tolerance is separate from certificate-validity acceptance.

## Earlier bounded acceptance

The reviewed Intel implementation was previously tested on Celeron J4025,
DSM 7.4 and Container Manager 24.0.2. Fresh initialization selected VAAPI after
the upstream FFmpeg probe. Readback showed the package UID, native videodriver
GID, only renderD128 mapped with rw access, read-only media, cap_drop ALL,
no-new-privileges, and no privileged container. DSM adds NET_BIND_SERVICE to
the bounding set; effective, permitted and ambient capabilities were zero.

The same 30-second H.264 1080p source was transcoded to 720p. Automatic VAAPI
used `h264_vaapi`, software used `libx264`, and the manually selected native
QSV option used `h264_qsv`. All returned HTTP 200 and fully decoded outputs.
Native stop/start preserved GPU mapping and another VAAPI playback passed.
The separate no-GPU path used software. These earlier results cover that
implementation; the release verification above records the published pins.

One earlier clip comparison measured 4.00 container CPU seconds with VAAPI
and 29.40 with software. It was a single bounded sample including App work,
not a sustained-load or image-quality benchmark. Automatic QSV, HEVC/AV1
encoding, HDR tone mapping, non-Intel GPUs, hotplug and long-running load are
outside the verified scope.

Earlier browser acceptance covered DSM main-menu entry, one-click DSM sign-in,
distinct administrator and ordinary signed-sub JIT identities, role mapping,
read-only media streaming, native logout/reopen, anonymous 401 refusal and
App-privilege-denied 403. Those broader identity tests are not repeated by a
narrow release refresh. DSM App privilege and media-share permission are
separate requirements; selecting a folder does not grant access.

## Limits and retention

Web sign-in uses the plugin's native **Sign in with DSM** button. Automatic
browser bridging interferes with its hidden initialization iframe and is
omitted. TV/mobile native clients cannot use this DSM-only ingress. Native
session expiry and DSM account revocation remain separate boundaries. DLNA
is disabled and needs a separate discovery/multicast design.

Runtime may use any core with a low CPU weight (`cpu_shares: 256`) so DSM and
other services win under contention, and has a 2 GiB memory ceiling. On a
12-core Linux host with the pinned image, idle anonymous memory was 119 MiB and
concurrent software 1080p-to-720p transcodes peaked at 423, 729 and 1034 MiB
for one, two and three streams; three streams exceed the former 1 GiB ceiling. Named App data volumes
remain after uninstall, including delete-data requests. Fixture cleanup removes
only the verified owned volumes/share and retains DSM's package identity and
the official container engine. There is no installed root purge hook.

A two-boot Linux retention test previously verified reconfiguration of the SSO
provider after SDK client-secret regeneration. The package retains the native
bootstrap credential in its private volume with mode 0600 and uses supported
Jellyfin APIs to synchronize the provider. User filesystem access continues to
use the fixed package account rather than the signed-in user's ACL.
