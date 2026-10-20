# Jellyfin for DSM — development OIDC proof

This wrapper uses the unmodified official Jellyfin 12.2 image, the unmodified
SSO Authentication 4.0.0.4 plugin, and the embedded SDK OIDC provider.
The development SPK is `SynoPkgJellyfin` / `12.2-0001` / x86_64.
Build `0002` was an unpublished upgrade-test fixture; the initial version remains
`12.2-0001`.

The native install wizard selects an existing Shared Folder for `/media`, mounted
read-only. Selection does not grant access: in DSM Shared Folder permissions,
choose **System internal user** and grant `SynoPkgJellyfin` read access.
Configuration and cache use private named volumes. GPU and DLNA are not enabled.

All integration files are under `synology/`. Upstream source, plugin code and the
registry image are unchanged. `upstream-source.json` identifies the release
source; the fork's main branch may already contain newer upstream development
commits. Do not describe its HEAD as the source tree of the pinned release image.

## Build

Use Node 24 and Go 1.26.9 on a Linux build host, with access to the released SDK
module. The dependency pins remain at released 0.19.0. Shared-folder selection
and host App-health readiness require the unreleased SDK and CLI changes below.
The released-only build is currently blocked; this development SPK must not be
published.

For development acceptance, check out SDK
`54c88fcddc0abcd3831ce0172329cb251b491f16` and CLI
`5eee189e5291e501aacb7eb688dc9cbef464048e` in temporary directories, build the CLI,
and set `SYNOPKGLAND_SDK_DIR` to the SDK checkout when invoking that CLI.
In the CLI checkout run `npm ci --ignore-scripts` followed by
`./node_modules/.bin/tsc --declaration false`; declaration emission currently
hits TS2742 in its optional e2e helper. The executable source is unchanged.
Do not change package pins to an unpublished version.

```sh
export SYNOPKGLAND_SDK_DIR=/absolute/path/to/sdk-checkout
CLI_BIN=/absolute/path/to/cli-checkout/dist/bin.js
cd synology
npm ci --ignore-scripts
python3 scripts/render.py
npm test
node "$CLI_BIN" check --json
node "$CLI_BIN" build --arch x86_64 --json
node "$CLI_BIN" inspect dist/SynoPkgJellyfin-12.2-0001-x86_64.spk --json
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
startup-status listener at each process launch. The development SDK waits for
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

Named volumes are App data. SDK 0.19.0 retains them even when Package Center
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
TODO: replace the development source override with released SDK/CLI versions
once Shared Folder selection, host App-health readiness and App privilege denial
fixes are released.
This repository does not enable Actions or publish releases/catalog entries.

## Licenses and source

Jellyfin's upstream license remains at the repository root. The plugin's original
release ZIP and matching source archive are in `vendor/`, with SHA-256 provenance
in `plugin-lock.json`. Its GPL-3.0 license is in `LICENSES/SSO-GPL-3.0.txt`.
The SDK-generated template license is in `LICENSES/TEMPLATE.txt`.
The wrapper adapter is GPL-3.0-or-later; upstream binaries retain their own licenses.
See [NOTICE](NOTICE). This proof is not a complete redistribution/release audit.
