# Jellyfin DSM integration

Keep every wrapper change under synology/. Preserve upstream source and use the
unmodified official image and hash-pinned SSO plugin. Render declarations with
python3 scripts/render.py after changing the renderer or container adapter.

Use signed OIDC sub identity, dsm-users admission and DSM App privilege. Map the
admin group through the plugin's supported policy; do not replace OIDC with a
shared administrator account. Runtime must remain the package UID without root
or added capabilities.

The native wizard defaults to the dedicated Jellyfin share, mounted read-only.
DSM manages its package-account grant. Optional existing shares must pass the
SDK access validation; do not infer access from the selected path.

Dependency pins stay at released versions. Development source overrides must
identify exact reviewed SDK/CLI commits and must never be published as a release.
Keep credentials, DSM profiles, device addresses, traces and private fixtures out
of Git. Record actual acceptance boundaries in docs/validation.md.

Run affected tests, check, build and inspect. Device/browser acceptance must prove
menu entry, distinct JIT users, administrator mapping, denial, logout, media read
and lifecycle behavior before claiming them. Do not infer a pass from installation
or a transient running status. Do not publish or enable CI as part of a PR.
