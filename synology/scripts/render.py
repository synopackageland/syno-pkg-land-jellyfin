#!/usr/bin/env python3
"""Render reviewed SDK declarations and embed only a hash-pinned upstream plugin."""

from pathlib import Path
import base64, hashlib, io, json, zipfile

ROOT = Path(__file__).resolve().parents[1]
PLUGIN_SHA = "c09f16ba31059a434ddd7f811e4f9608d4b4c4514cc80a5bf1ca33bee61e1107"
IMAGE = "jellyfin/jellyfin:12.2@sha256:357724bf0ae27a672c7cbaa899db2d9abeb13dbd8657ccce750258a4c059d037"
STATE = "/var/tmp/jellyfin"


def plugin_files(file):
    data = Path(file).read_bytes()
    if hashlib.sha256(data).hexdigest() != PLUGIN_SHA:
        raise ValueError("Plugin release SHA-256 mismatch")
    expected = {
        "meta.json",
        "SSO-Auth.dll",
        "Duende.IdentityModel.dll",
        "Duende.IdentityModel.OidcClient.dll",
    }
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        if set(z.namelist()) != expected:
            raise ValueError("Unexpected plugin release files")
        return {name: z.read(name) for name in sorted(expected)}


def provider(secret):
    return {
        "OidEndpoint": "http://127.0.0.1:29490",
        "OidClientId": "jellyfin",
        "OidSecret": secret,
        "Enabled": True,
        "EnableAuthorization": True,
        "EnableAllFolders": True,
        "AdminRoles": ["admin"],
        "Roles": [],
        "RoleClaim": "groups",
        "OidScopes": ["groups"],
        "DefaultUsernameClaim": "sub",
        "EnableLiveTv": False,
        "EnableLiveTvManagement": False,
        "NewPath": True,
        "SchemeOverride": "https",
        "DisableHttps": True,
        "DisablePushedAuthorization": True,
        "DoNotValidateEndpoints": False,
        "DoNotValidateIssuerName": False,
    }


def manifest():
    source = json.loads((ROOT / "upstream-source.json").read_text())
    return {
        "schema": 2,
        "package": "SynoPkgJellyfin",
        "version": source["tag"].removeprefix("v"),
        "build": source["build"],
        "displayname": "Jellyfin",
        "description": "Jellyfin media server with DSM sign-in and an install-selected, read-only media folder.",
        "maintainer": "synopackageland",
        "os_min_ver": "7.2.1-69057",
        "arches": ["x86_64"],
        "entry": "app-privilege",
        "capabilities": {"composeMounts": True},
        "install": {
            "sharedFolder": {"mode": "select", "key": "media", "permission": "ro"}
        },
        "compose": {
            "sdk": "0.21.0",
            "files": ["compose.yaml"],
            "devices": {"gpu": {"services": ["jellyfin"]}},
            "shares": {
                "media": {
                    "select": "install",
                    "mounts": [{"service": "jellyfin", "target": "/media"}],
                }
            },
            "startup_timeout_seconds": 600,
            "services": {
                "jellyfin": {
                    "network": "host",
                    "listener": {"env": "JELLYFIN_BIND", "format": "host"},
                    "storage_init": {
                        "directories": [{"base": "/var/tmp", "path": "jellyfin"}],
                        "runtime": {
                            "environment": {
                                "OIDC_SECRET": {"oidc_client": "jellyfin"},
                                "BOOTSTRAP_PASSWORD": {"secret": "bootstrap"},
                            },
                            "files": [
                                {"target": STATE + "/hwa.sh", "content": (ROOT / "container/hwa.sh").read_text()},
                                {
                                    "target": STATE + "/start.sh",
                                    "content": (
                                        ROOT / "container/start.sh"
                                    ).read_text(),
                                },
                                {
                                    "target": STATE + "/provider.json",
                                    "content": json.dumps(
                                        provider("__CLIENT_SECRET__")
                                    ),
                                },
                                {
                                    "target": STATE + "/branding.json",
                                    "content": json.dumps(
                                        {
                                            "LoginDisclaimer": '<form action="/sso/OID/start/dsm"><button class="raised block emby-button button-submit">Sign in with DSM</button></form>',
                                            "CustomCss": ".disclaimerContainer { display: block; }",
                                        }
                                    ),
                                },
                                {
                                    "target": STATE + "/library.json",
                                    "content": json.dumps(
                                        {
                                            "LibraryOptions": {
                                                "PathInfos": [{"Path": "/media"}],
                                                "EnableRealtimeMonitor": False,
                                                "EnableInternetProviders": False,
                                                "EnableAutomaticSeriesGrouping": False,
                                            }
                                        }
                                    ),
                                },
                            ],
                        },
                    },
                }
            },
            "web": {
                "service": "jellyfin",
                "port": 29496,
                "health": {"path": "/System/Ping", "status": 200},
            },
            "network": {"egress": "internet"},
        },
        "identity_gateway": {
            "sdk": "0.21.0",
            "mode": "oidc",
            "access": "dsm-users",
            "listen": {"https": 29443},
            "oidc": {
                "issuer_port": 29490,
                "clients": [
                    {
                        "id": "jellyfin",
                        "redirect_paths": ["/sso/OID/redirect/dsm"],
                        "pkce": True,
                    }
                ],
            },
        },
        "ui": {"launch": "new-page"},
    }


def render():
    files = plugin_files(ROOT / "vendor/sso-authentication_4.0.0.4.zip")
    args = []
    for name, data in files.items():
        if name == "meta.json":
            meta = json.loads(data)
            meta["autoUpdate"] = False
            data = json.dumps(meta).encode()
        encoded = base64.b64encode(data).decode()
        chunks = [encoded[n : n + 48000] for n in range(0, len(encoded), 48000)]
        args.extend(
            [
                name,
                hashlib.sha256(data).hexdigest(),
                "chunks:" + str(len(chunks)),
                *chunks,
            ]
        )
    compose = {
        "services": {
            "jellyfin": {
                "image": json.loads((ROOT / "compose.image.yaml").read_text())[
                    "services"
                ]["jellyfin"]["image"],
                "entrypoint": ["/bin/sh", STATE + "/start.sh"],
                "command": args,
                "environment": {
                    "JELLYFIN_DATA_DIR": STATE + "/config",
                    "JELLYFIN_CONFIG_DIR": STATE + "/config/config",
                    "JELLYFIN_CACHE_DIR": STATE + "/cache",
                    "JELLYFIN_LOG_DIR": STATE + "/config/log",
                },
                "read_only": True,
                "tmpfs": ["/tmp"],
                "volumes": ["data:/var/tmp"],
                "cpuset": "0-0",
                "mem_limit": "1g",
                "restart": "unless-stopped",
                "healthcheck": {
                    "test": [
                        "CMD-SHELL",
                        'test "$(curl -fsS http://127.0.0.1:29496/health)" = Healthy',
                    ],
                    "interval": "30s",
                    "timeout": "3s",
                    "retries": 3,
                    "start_period": "600s",
                },
                "stop_grace_period": "30s",
            }
        },
        "volumes": {"data": {}},
    }
    (ROOT / "compose.yaml").write_text(json.dumps(compose, indent=2) + "\n")
    (ROOT / "dsm-package.yaml").write_text(json.dumps(manifest(), indent=2) + "\n")


if __name__ == "__main__":
    render()
