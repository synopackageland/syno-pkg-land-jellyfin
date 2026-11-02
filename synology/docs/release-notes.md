## 12.4-0006

Install wizard: port conflicts only warn; shared folder selection fixed

Rebuilt with CLI 0.47.4; SDK/UI pins retained. No tests, NAS installs or live checks were run
Approval retention is unknown because the current inspector rejects the previous release’s legacy wizard baseline

# Release notes

## 12.4-0004

Open Jellyfin at `/synopkgland/SynoPkgJellyfin/` on the DSM HTTPS origin
The public gateway port is removed; only the loopback OIDC issuer remains configurable
The official image, SSO plugin, DSM App privilege and native user data are retained

## 12.4-0003

Rebuild unchanged upstream Jellyfin 12.4 with published CLI 0.42.2, SDK/App
0.42.0 and executor/v0.42.0. The recorded UI pin is 0.19.2; Jellyfin uses its
own upstream UI. The wrapper templates dependency remains 0.35.5; the CLI
resolves its own templates 0.37.0. Entry and OIDC policies remain unchanged.
See [validation](validation.md) for this artifact's device acceptance boundary.

## 12.2-0012

Built with published SDK/App/templates 0.32.0, CLI 0.34.0 and executor v0.32.0.
The fixed client prefixes in the README use upstream authentication; browser
entry and every unlisted route retain the existing DSM gate. Entry and login
policy are unchanged. Protected executors require administrator approval.
Mobile/native first-login and deployed client acceptance remain unverified.
See [mobile and native clients](../README.md#mobile-and-native-clients) for the
exact prefix list, upstream credentials, revocation and client limitations.
