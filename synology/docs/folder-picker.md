# Folder selection migration

| Key | Existing source | New source | Container path | Access | Purpose |
| --- | --- | --- | --- | --- | --- |
| media | Saved shared-folder root | Same share plus an optional relative folder path | /media | ro | Media library |
| data | Package-owned named volume | Unchanged named volume | /var/tmp | rw | Private App state |
| sdk_image_5a0112e91f01 | Upstream image named volume | Unchanged named volume | /cache | rw | Upstream image-declared storage |
| sdk_image_ece49bdd30b2 | Upstream image named volume | Unchanged named volume | /config | rw | Upstream image-declared storage |

Fresh installs use the SDK folder picker over existing mounted local ACL shares.
The picker uses mode `select`; it does not create a dedicated share. DSM grants
RO to the package account for the whole share, even when only a subtree is mounted.
The container continues to run as the package UID without added privileges.

Existing installations retain the `media` key. An absent or empty subpath means
the original share root. Omitted upgrade answers must preserve the saved record;
the wizard must prefill the original share without requiring another selection.
Only the released CLI/SDK owns selection, validation and permission recovery.

SDK-generated runtime secret binds and storage-init assets remain read-only at
`/synopkgland/secrets/` and `/synopkgland/storage-init`; they are not user-selectable
data folders. Temporary files use the SDK disk scratch at `/tmp`, not a
user-selectable folder.

Published SDK 0.53.23 and CLI 0.52.15 preserve legacy share-only records as the
share root in silent and wizard upgrades. See [validation](validation.md).
