"""Linux Docker integration: retained native data must adopt regenerated SDK secrets."""

from pathlib import Path
import argparse, tempfile, uuid, re
import json, subprocess, os, time, xml.etree.ElementTree as ET

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--storage-init", type=Path, required=True)
parser.add_argument(
    "--image",
    default="jellyfin/jellyfin@sha256:357724bf0ae27a672c7cbaa899db2d9abeb13dbd8657ccce750258a4c059d037",
)
parser.add_argument("--name-prefix", default="jellyfin-retention")
options = parser.parse_args()
if os.geteuid() != 0:
    parser.error(
        "Run on a disposable Linux Docker host as root to prepare UID 65000 fixture files"
    )
if not re.fullmatch(r"[a-z][a-z0-9-]{0,40}", options.name_prefix):
    parser.error("Use a short lowercase Docker resource prefix")
project = Path(__file__).resolve().parents[1]
workspace = tempfile.TemporaryDirectory(prefix=options.name_prefix + "-")
root = Path(workspace.name)
m = json.loads((project / "dsm-package.yaml").read_text())
c = json.loads((project / "compose.yaml").read_text())["services"]["jellyfin"]
secret = root / "rotation-secrets"
secret.mkdir(exist_ok=True)
secret.chmod(0o755)
media = root / "rotation-media"
media.mkdir(exist_ok=True)
media.chmod(0o555)
name = options.name_prefix + "-" + uuid.uuid4().hex[:12]
volume = name + "-data"
image = options.image


def run(value):
    for file in ["runtime-bootstrap.secret", "oidc-jellyfin.secret"]:
        p = secret / file
        p.write_text(value * 64)
        p.chmod(0o600)
        os.chown(p, 65000, 65000)
    args = [
        "docker",
        "run",
        "-d",
        "--name",
        name,
        "--network",
        "none",
        "--memory",
        "1g",
        "--cpus",
        "1",
        "--user",
        "65000:65000",
        "--cap-drop",
        "ALL",
        "--security-opt",
        "no-new-privileges",
        "--read-only",
        "--tmpfs",
        "/tmp",
        "-v",
        volume + ":/var/tmp",
        "-v",
        str(options.storage_init.resolve()) + ":/synopkgland/storage-init:ro",
        "-v",
        str(secret) + ":/synopkgland/secrets:ro",
        "-v",
        str(media) + ":/media:ro",
        "-e",
        "JELLYFIN_BIND=127.0.0.1",
        "-e",
        "SYNOPKGLAND_STARTUP_BUDGET_SECONDS=120",
    ]
    for key, val in c["environment"].items():
        args += ["-e", key + "=" + val]
    args += [
        "--entrypoint",
        "/synopkgland/storage-init",
        image,
        "--initialization",
        json.dumps(m["compose"]["services"]["jellyfin"]["storage_init"]),
        "--",
        *c["entrypoint"],
        *c["command"],
    ]
    r = subprocess.run(args, capture_output=True, text=True)
    assert r.returncode == 0, "container start failed"
    healthy = False
    for n in range(120):
        time.sleep(1)
        status = subprocess.run(
            [
                "docker",
                "exec",
                name,
                "sh",
                "-c",
                'test -f /var/tmp/jellyfin/bootstrap.complete && test "$(curl -fsS --max-time 2 http://127.0.0.1:29496/health)" = Healthy',
            ],
            capture_output=True,
            text=True,
        )
        if status.returncode == 0:
            healthy = True
            break
        if (
            subprocess.check_output(
                ["docker", "inspect", "--format", "{{.State.Running}}", name], text=True
            ).strip()
            != "true"
        ):
            break
    assert healthy, "runtime did not become healthy"
    raw = subprocess.check_output(
        [
            "docker",
            "exec",
            name,
            "cat",
            "/var/tmp/jellyfin/config/plugins/configurations/SSO-Auth.xml",
        ]
    )
    configured = any(
        node.text == value * 64 for node in ET.fromstring(raw).iter("OidSecret")
    )
    print("configuration matches current SDK client:", configured, flush=True)
    mode = subprocess.check_output(
        [
            "docker",
            "exec",
            name,
            "stat",
            "-c",
            "%a",
            "/var/tmp/jellyfin/bootstrap.secret",
        ],
        text=True,
    ).strip()
    assert mode == "600", "native bootstrap credential must remain private"
    assert (
        configured
    ), "retained native config did not adopt the regenerated SDK client secret"
    subprocess.run(
        ["docker", "stop", "--time", "20", name], capture_output=True, check=True
    )
    subprocess.run(["docker", "rm", name], capture_output=True, check=True)


try:
    run("a")
    run("b")
    print("Retained data and regenerated SDK secrets: PASS", flush=True)
finally:
    subprocess.run(["docker", "rm", "-f", name], capture_output=True)
    subprocess.run(["docker", "volume", "rm", volume], capture_output=True)
    workspace.cleanup()
