# Changelog

## 12.4-0005

- Use CLI 0.47.1 and SDK/App 0.46.1 for existing shared-folder grants through DSM data-share and Package Center upgrade dispatch
- Retain the upstream application, data layout and entry policy
- Shared folders, files and package-account ACLs are retained on uninstall by DSM

## 12.4-0004

- Serve Jellyfin through the fixed DSM path `/synopkgland/SynoPkgJellyfin/`
- Configure the native BaseUrl, bootstrap API, login branding and health probes consistently
- Preserve OIDC, DSM App privilege, native authentication exceptions and retained data
- Pin CLI 0.43.0, SDK/App 0.43.1, templates 0.38.0 and executor v0.39.0

## 12.4-0003

- Rebuild unchanged Jellyfin 12.4 with CLI 0.42.2 and SDK/App 0.42.0
- Refresh the recorded UI pin to 0.19.2; Jellyfin does not use the UI kit
- Preserve DSM App privilege, OIDC identity, media access and retained data


## 12.2-0011: SDK entry-gate migration

Built with SDK/App/templates 0.32.0, CLI 0.34.0 and executor v0.32.0.
Every request retains the DSM entry gate. No upstream-authenticated path exceptions are enabled in this build.
Protected executor payloads changed: administrator approval is required again after upgrading.
No NAS installation or device acceptance was performed for this rebuild.

## 12.2-0008

- Improve opening the App from the DSM menu and external access settings
- 改善從 DSM 選單開啟 App 與外網存取設定
