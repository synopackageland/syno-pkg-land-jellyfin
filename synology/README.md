# Jellyfin for DSM

This wrapper uses the unmodified official Jellyfin 12.2 image, the unmodified
SSO Authentication 4.0.0.4 plugin, and the embedded SDK OIDC provider.
The SPK is `SynoPkgJellyfin` / `12.2-0002` / x86_64.

The native install wizard selects an existing Shared Folder for `/media`, mounted
read-only. Selection does not grant access: in DSM Shared Folder permissions,
choose **System internal user** and grant `SynoPkgJellyfin` read access.
Configuration and cache use private named volumes. Intel GPU support uses the
SDK capability described below; DLNA is not enabled.

All integration files are under `synology/`. Upstream source, plugin code and the
registry image are unchanged. `upstream-source.json` identifies the release
source; the fork's main branch may already contain newer upstream development
commits. Do not describe its HEAD as the source tree of the pinned release image.

## Build

Use Node 24 and Go 1.26.9 on a Linux build host with access to the released SDK
module. CLI/templates/SDK/App are pinned to 0.21.0, executor to executor/v0.20.0
and UI to 0.12.5. Install the locked published dependencies and run:

```sh
cd synology
npm ci --ignore-scripts
python3 scripts/render.py
npm test
npx --no-install synopkgland check --json
npx --no-install synopkgland build --arch x86_64 --json
npx --no-install synopkgland inspect dist/SynoPkgJellyfin-12.2-0002-x86_64.spk --json
```

`render.py` verifies the original plugin ZIP's pinned SHA-256 before embedding
its files in bounded argv chunks. Only local plugin metadata disables automatic
updates. Each embedded DLL is checked again before use. No executable is fetched
at NAS startup. The generated JSON documents are valid YAML; edit the renderer
and container adapter, then render again.

Runtime uses the package UID, all capabilities dropped, no-new-privileges,
read-only image files, a private directory under a sticky named volume, a 1 GiB
memory ceiling and one pinned CPU. The SDK creates and injects private OIDC and
bootstrap secrets. The initial local bootstrap account has an SDK-generated
random password retained in the private configuration volume. On regenerated
SDK client secrets the adapter reconfigures the plugin through its native API;
users never type a separate Jellyfin password for Web SSO.
Only supported native setup/configuration APIs and config files are used.

The first-configuration adapter uses loopback port 29497 and stops before the
configured server starts on loopback port 29496. Jellyfin briefly replaces its
startup-status listener at each process launch. The SDK waits for
`/System/Ping` to return exactly HTTP 200 before admitting the backend; inspect
reports `host-uid-listener-health`. OIDC issuer port 29490 stays loopback.
HTTPS 29443 is the SDK entry. Auxiliary discovery is disabled. The explicit host
network is required to reach the SDK loopback issuer; it is unrelated to DLNA.

## Login and acceptance

The SDK admits `dsm-users` and enforces the App entry privilege. The plugin uses
the signed OIDC `sub` as the canonical Jellyfin username, and maps the `groups`
claim's `admin` role to the native administrator policy. Account rename cannot
silently switch the linking key to email or a display name.

Jellyfin's supported login branding offers **Sign in with DSM** as the one-click
entry. The SDK automatic browser bridge is omitted: the plugin initializes Web
credentials through a hidden iframe, and the bridge's document redirects cause
a repeated login flow. No upstream script is patched. Logout returns to the
native login screen, where the same DSM button is available. Native app/TV login is not supported by this DSM-only ingress. Such clients
use native Jellyfin authentication, but a native account alone does not pass the
DSM gateway. A separately reviewed passthrough or Quick Connect design is needed. App session/token expiry and DSM
account deletion/revocation are separate acceptance boundaries.

The upstream e2e suite uses the CLI's shared DSM login/profile helpers. Supply
private account JSON files, a private profile directory, a reachable DSM URL,
`JELLYFIN_E2E_URL`, and an ignored `synology/.e2e` output directory. See the helper's
`DSM_E2E_ACCOUNT_ADMIN`, `DSM_E2E_ACCOUNT_READER`, `DSM_E2E_PROFILE_DIR`, and
`DSM_E2E_OUTPUT_DIR` settings. Keep credentials, profiles, traces and screenshots
outside version control. Test certificate trust is separate from OIDC correctness.

The optional Linux Docker integration probe runs as root on a disposable Linux
Docker host (to prepare UID 65000 fixture-file ownership), with
`python3 tests/retention_test.py --storage-init /path/to/built/storage-init`. It
boots the actual pinned image twice with retained native data and regenerated
SDK secrets, checks provider synchronization and credential mode, and removes
only its randomly named test container and volume.

Named volumes are App data. The SDK retains them even when Package Center
**delete data** is selected and reports `COMPOSE_DATA_RETAINED`; do not claim
complete data deletion. Test-only fixture cleanup must verify the exact owned
volume inventory. No root cleanup hook is installed.

See [validation](docs/validation.md) for the verified boundary and limitations.

## Upgrade

After committing a clean tree, `bash synology/upgrade.sh v12.2 2` merges the
explicit upstream tag, re-pins the official image, updates source provenance and
builds. Upstream version strings retain two or three numeric components; build
numbers increase within a release and restart at `0001` for a new release.
A changed upstream/plugin requires fresh compatibility and device acceptance.
Build and upgrade scripts do not enable Actions or publish releases/catalog entries.

## Licenses and source

Jellyfin's upstream license remains at the repository root. The plugin's original
release ZIP and matching source archive are in `vendor/`, with SHA-256 provenance
in `plugin-lock.json`. Its GPL-3.0 license is in `LICENSES/SSO-GPL-3.0.txt`.
The SDK-generated template license is in `LICENSES/TEMPLATE.txt`.
The wrapper adapter is GPL-3.0-or-later; upstream binaries retain their own licenses.
See [NOTICE](NOTICE). The SPK references the official image and does not redistribute its layers.

## Intel hardware transcoding

This package opts Jellyfin into the SDK's native Intel render-device capability
through `compose.devices.gpu`, available in the published 0.21.x toolchain.
Release builds use only published dependencies.

On Intel iGPU models, the package maps only accepted `/dev/dri/renderD*` nodes,
runs as the fixed package UID and obtains the numeric `videodriver` GID through
DSM's native resource. It uses neither root nor privileged containers. Before
starting Jellyfin, its unchanged image's FFmpeg performs a bounded H.264 VAAPI
encode probe (60 seconds, then a five-second forced-termination grace period).
Probe failures report their exit code and select software. When successful, the first initialization writes Jellyfin's native
`encoding.xml` fields for VAAPI and the detected render path. Subsequent starts
preserve encoder choices while hardware remains usable; QSV can be selected in
Jellyfin's native dashboard after validation on the target device. Automatic QSV,
HEVC/AV1 encoding, HDR tone mapping and non-Intel GPUs are outside this release.

Without a usable device or encoder, the adapter selects native software
transcoding and retains unrelated encoding options. If hardware becomes usable
again it initializes VAAPI once more. HWA is a package capability, independent of
DSM sign-in or media-folder permissions. Hardware removal requires reinstalling
or upgrading to regenerate the SDK's device mappings.

DSM's native provider adds NET_BIND_SERVICE to the bounding set for Compose
packages. The SDK requests no added capabilities; the nonroot package process
with no-new-privileges has zero effective, permitted and ambient capabilities.
This general DSM behavior does not block GPU acceptance.

The reviewed implementation completed real H.264 VAAPI and optional native QSV
playback transcoding on Intel Celeron J4025, with complete client decoding. The
no-GPU software path also passed. See [validation scope](docs/validation.md) for
CPU measurements and lifecycle boundaries. The release verification is recorded separately there. These observations
do not certify other GPUs or codecs.
