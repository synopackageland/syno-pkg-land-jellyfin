#!/bin/sh
# Runtime runs only as the package UID. No upstream source or image is changed.
set -eu
umask 077
state=/var/tmp/jellyfin
plugin="$state/config/plugins/SSO Authentication_4.0.0.4"
mkdir -p "$plugin" "$state/config/config" "$state/cache"
# Build-verified release files arrive in bounded base64 argv chunks, never downloaded at startup.
while [ "$#" -gt 0 ]; do
    file=$1; hash=$2; count=${3#chunks:}; shift 3
    case "$file" in SSO-Auth.dll|Duende.IdentityModel.dll|Duende.IdentityModel.OidcClient.dll|meta.json) ;; *) exit 1;; esac
    : > "$plugin/$file.pending"
    while [ "$count" -gt 0 ]; do
        printf '%s' "$1" | base64 -d >> "$plugin/$file.pending"
        shift; count=$((count-1))
    done
    printf '%s  %s\n' "$hash" "$plugin/$file.pending" | sha256sum -c - >/dev/null
    mv "$plugin/$file.pending" "$plugin/$file"
done
[ "${JELLYFIN_BIND:?}" = 127.0.0.1 ] || exit 1
case "${OIDC_SECRET:?}${BOOTSTRAP_PASSWORD:?}" in *[!0-9a-f]*) exit 1;; esac
[ "${#OIDC_SECRET}" -eq 64 ] && [ "${#BOOTSTRAP_PASSWORD}" -eq 64 ] || exit 1
# The SDK may regenerate secrets after delete-data while named volumes remain.
# Retain only the native bootstrap credential in the same private App volume.
if [ ! -f "$state/bootstrap.secret" ]; then
    printf '%s' "$BOOTSTRAP_PASSWORD" > "$state/bootstrap.secret"
fi
BOOTSTRAP_PASSWORD=$(cat "$state/bootstrap.secret")
case "$BOOTSTRAP_PASSWORD" in *[!0-9a-f]*) exit 1;; esac
[ "${#BOOTSTRAP_PASSWORD}" -eq 64 ] || exit 1
oidc_fingerprint=$(printf '%s' "$OIDC_SECRET" | sha256sum | cut -d ' ' -f 1)
budget=${SYNOPKGLAND_STARTUP_BUDGET_SECONDS:?}
case "$budget" in ''|*[!0-9]*) exit 1;; esac
deadline=$(($(date +%s)+budget))
network() {
    printf '<?xml version="1.0"?><NetworkConfiguration><InternalHttpPort>%s</InternalHttpPort><EnableHttps>false</EnableHttps><EnableIPv4>true</EnableIPv4><EnableIPv6>false</EnableIPv6><AutoDiscovery>false</AutoDiscovery><EnableUPnP>false</EnableUPnP><LocalNetworkAddresses><string>%s</string></LocalNetworkAddresses><KnownProxies><string>127.0.0.1</string></KnownProxies></NetworkConfiguration>\n' "$1" "$JELLYFIN_BIND" > "$state/config/config/network.xml"
}
cleanup_secrets() { rm -f "$state/auth.json" "$state/curl-auth.conf" "$state/provider-live.json" "$state/library-list.json"; }
trap cleanup_secrets EXIT
server=''
stop() { cleanup_secrets; if [ -n "$server" ]; then kill "$server" 2>/dev/null || true; wait "$server" 2>/dev/null || true; fi; }
trap 'stop; exit 1' INT TERM HUP
if [ ! -f "$state/bootstrap.complete" ] || [ "$(cat "$state/oidc.fingerprint" 2>/dev/null || true)" != "$oidc_fingerprint" ]; then
    network 29497
    /jellyfin/jellyfin &
    server=$!
    until [ "$(curl -fsS --max-time 2 http://127.0.0.1:29497/health 2>/dev/null || true)" = Healthy ]; do
        kill -0 "$server" 2>/dev/null || { echo 'Bootstrap server failed' >&2; exit 1; }
        [ "$(date +%s)" -lt "$deadline" ] || { stop; echo 'Bootstrap deadline exceeded' >&2; exit 1; }
        sleep 1
    done
    api=http://127.0.0.1:29497
    info=$(curl -fsS --max-time 10 "$api/System/Info/Public")
    if ! printf '%s' "$info" | grep -iq '"StartupWizardCompleted"[[:space:]]*:[[:space:]]*true'; then
        curl -fsS --max-time 10 "$api/Startup/User" >/dev/null
        printf '{"Name":"package-bootstrap","Password":"%s"}' "$BOOTSTRAP_PASSWORD" > "$state/auth.json"
        curl -fsS --max-time 10 -H 'Content-Type: application/json' -X POST --data-binary @"$state/auth.json" "$api/Startup/User" >/dev/null
        curl -fsS --max-time 10 -X POST "$api/Startup/Complete" >/dev/null
    fi
    printf '{"Username":"package-bootstrap","Pw":"%s"}' "$BOOTSTRAP_PASSWORD" > "$state/auth.json"
    response=$(curl -fsS --max-time 10 -H 'Content-Type: application/json' -H 'Authorization: MediaBrowser Client="Package Setup", Device="Package", DeviceId="package-bootstrap", Version="1"' --data-binary @"$state/auth.json" "$api/Users/AuthenticateByName")
    token=$(printf '%s' "$response" | sed -n 's/.*"AccessToken"[[:space:]]*:[[:space:]]*"\([0-9a-fA-F]*\)".*/\1/p')
    [ -n "$token" ] || { stop; echo 'Bootstrap authentication failed' >&2; exit 1; }
    printf 'header = "Authorization: MediaBrowser Token=%s"\n' "$token" > "$state/curl-auth.conf"
    sed "s/__CLIENT_SECRET__/$OIDC_SECRET/g" "$state/provider.json" > "$state/provider-live.json"
    curl -fsS --max-time 10 -K "$state/curl-auth.conf" -H 'Content-Type: application/json' --data-binary @"$state/provider-live.json" "$api/sso/OID/Add/dsm" >/dev/null
    # The supported branding API provides a one-click fallback after native hash-route logout.
    curl -fsS --max-time 10 -K "$state/curl-auth.conf" -H 'Content-Type: application/json' --data-binary @"$state/branding.json" "$api/System/Configuration/Branding" >/dev/null
    curl -fsS --max-time 10 -K "$state/curl-auth.conf" "$api/Library/VirtualFolders" > "$state/library-list.json"
    if ! grep -q '"Name"[[:space:]]*:[[:space:]]*"Media"' "$state/library-list.json"; then
        curl -fsS --max-time 10 -K "$state/curl-auth.conf" -H 'Content-Type: application/json' --data-binary @"$state/library.json" "$api/Library/VirtualFolders?name=Media&collectionType=movies&refreshLibrary=false" >/dev/null
    fi
    printf '%s' "$oidc_fingerprint" > "$state/oidc.fingerprint"
    kill "$server"; wait "$server" || true; server=''
fi
# Only the final, configured server uses the SDK health/listen port.
network 29496
if [ -f "$state/bootstrap.complete" ]; then
    cleanup_secrets
    trap - INT TERM HUP
    exec /jellyfin/jellyfin
fi
/jellyfin/jellyfin &
server=$!
until [ "$(curl -fsS --max-time 2 http://127.0.0.1:29496/health 2>/dev/null || true)" = Healthy ]; do
    kill -0 "$server" 2>/dev/null || { cleanup_secrets; exit 1; }
    [ "$(date +%s)" -lt "$deadline" ] || { stop; exit 1; }
    sleep 1
done
# A refresh is asynchronous: request it from the final process, which remains alive.
curl -fsS --max-time 10 -K "$state/curl-auth.conf" -X POST http://127.0.0.1:29496/Library/Refresh >/dev/null
cleanup_secrets
: > "$state/bootstrap.complete"
wait "$server"
