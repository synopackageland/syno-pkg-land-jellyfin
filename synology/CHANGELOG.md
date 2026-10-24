# Changelog

## 12.2-0006

- Move the HTTPS gateway from port 29443 to 33443 so Jellyfin can coexist with
  Vaultwarden and ConvertX. After upgrading, change the server URL saved in your
  mobile App to `https://<nas-host>:33443`. Update browser bookmarks, firewall
  rules and port forwarding as well. This port change does not add support for
  native clients through the DSM-only gateway; the existing login limitations
  still apply.
- Keep the loopback OIDC issuer (29490), streaming backend (29496) and bootstrap
  server (29497) on their existing ports.
- Rebuilt with published SDK/App/CLI/templates 0.28.0 (executor/v0.27.0), which brings slow-NAS startup defaults (generous health and readiness timing). Not tested on a NAS.
- 以已發佈 SDK/App/CLI/templates 0.28.0（executor/v0.27.0）重建，採用 SDK 的慢速 NAS 啟動預設值（較寬鬆的健康檢查與就緒時間）。尚未在 NAS 上測試。

## 12.2-0005

- Rebuild 12.2-0005 with published SDK/App/CLI/templates 0.26.0, UI 0.14.4 and Go 1.26.10. Maintainer: Syno Package Land. Official images and application sources are unchanged. Check the selected shared folder permissions before starting; grant the package account the required access in DSM.
- 12.2-0005 使用已發佈 SDK/App/CLI/templates 0.26.0、UI 0.14.4 與 Go 1.26.10 重建；維護者顯示為 Syno Package Land。 官方映像與上游程式維持原樣。 啟動前檢查所選共用資料夾權限；請在 DSM 授予套件帳號所需存取權限。

A disposable DSM upgrade from 12.2-0004 starts normally when the package account can read the selected share (HTTP 200). Removing its share access makes prestart fail before the container starts and produces a native permission-remediation message.

以隔離 DSM fixture 從 12.2-0004 升級：套件帳號有讀取權限時正常啟動（HTTP 200）；移除該權限後，prestart 在容器啟動前拒絕，並提供原生權限補救訊息。
