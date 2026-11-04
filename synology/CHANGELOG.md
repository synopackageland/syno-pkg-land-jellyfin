# Changelog

## 12.4-0008

- en: Fix DSM sign-in when opening over HTTP
- zh-TW: 修正以 HTTP 開啟時的 DSM 登入
- zh-CN: 修复通过 HTTP 打开时的 DSM 登录
- ja: HTTP で開いた場合の DSM ログインを修正
- ko: HTTP로 열 때 DSM 로그인 수정
- de: DSM-Anmeldung beim Öffnen über HTTP korrigiert
- fr: Corriger la connexion DSM lors de l’ouverture via HTTP

## 12.4-0006

- en: Install wizard: port conflicts only warn; shared folder selection fixed
- zh-TW: 安裝精靈：連接埠衝突僅顯示警告，並修正共用資料夾選擇
- zh-CN: 安装向导：端口冲突仅显示警告，并修复共享文件夹选择
- de: Installationsassistent: Portkonflikte werden nur als Warnung angezeigt; Auswahl freigegebener Ordner korrigiert
- fr: Assistant d’installation : les conflits de ports affichent seulement un avertissement ; sélection des dossiers partagés corrigée
- ja: インストールウィザード：ポート競合は警告のみ表示し、共有フォルダーの選択を修正
- ko: 설치 마법사: 포트 충돌은 경고만 표시하며 공유 폴더 선택 수정

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
