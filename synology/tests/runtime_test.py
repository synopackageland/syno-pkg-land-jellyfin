import importlib.util, pathlib, unittest, tempfile, json, os, subprocess, hashlib

ROOT = pathlib.Path(__file__).resolve().parents[1]


class RuntimeTests(unittest.TestCase):
    def test_path_ingress_and_rendered_manifest(self):
        manifest = self.renderer().manifest()
        self.assertEqual(manifest["identity_gateway"]["ingress"]["path"], "/synopkgland/SynoPkgJellyfin/")
        self.assertNotIn("listen", manifest["identity_gateway"])
        self.assertTrue(manifest["install"]["ports"])  # Loopback OIDC issuer only
        self.assertEqual(manifest["identity_gateway"]["oidc"]["issuer_port"], 29490)
        self.assertEqual(manifest["compose"]["web"]["port"], 29496)
        self.assertEqual(manifest["compose"]["web"]["health"]["path"], "/synopkgland/SynoPkgJellyfin/System/Ping")
        self.assertIn("network 29497", (ROOT / "container/start.sh").read_text())
        self.assertEqual(manifest["build"], json.loads((ROOT / "upstream-source.json").read_text())["build"])
        self.assertEqual(json.loads((ROOT / "dsm-package.yaml").read_text()), manifest)

    def test_retained_volume_resynchronizes_and_bootstraps_under_base_url(self):
        base = "/synopkgland/SynoPkgJellyfin"
        with tempfile.TemporaryDirectory() as d:
            state = pathlib.Path(d)
            (state / "config/config").mkdir(parents=True)
            (state / "bootstrap.complete").touch()
            (state / "bootstrap.secret").write_text("a" * 64)
            # Same credentials, issuer and base URL as the HTTPS-only provider.
            (state / "oidc.fingerprint").write_text(hashlib.sha256(("b" * 64 + ":29490:" + base).encode()).hexdigest())
            (state / "hwa.sh").write_text("hwa_setup() { :; }\n")
            for name in ["branding.json", "library.json"]:
                (state / name).write_text("{}")
            (state / "provider.json").write_text(json.dumps(self.renderer().provider("__CLIENT_SECRET__")))
            binary = state / "bin"
            binary.mkdir()
            curl = binary / "curl"
            curl.write_text('''#!/bin/sh
for url; do :; done
printf '%s\\n' "$url" >> "$REQUEST_LOG"
case "$url" in
  */health) printf Healthy;;
  */System/Info/Public) printf '{"StartupWizardCompleted":true}';;
  */Users/AuthenticateByName) printf '{"AccessToken":"abcdef"}';;
  */Library/VirtualFolders) printf '[{"Name":"Media"}]';;
  */sso/OID/Add/dsm) cp "$STATE/provider-live.json" "$STATE/provider-posted.json";;
esac
''')
            curl.chmod(0o755)
            server = binary / "jellyfin"
            server.write_text('''#!/bin/sh
if grep -q '<InternalHttpPort>29497</InternalHttpPort>' "$STATE/config/config/network.xml"; then
    exec sleep 30
fi
''')
            server.chmod(0o755)
            script = (ROOT / "container/start.sh").read_text().replace("state=/var/tmp/jellyfin", f"state={state}").replace("/jellyfin/jellyfin", str(server))
            env = dict(os.environ, PATH=str(binary) + ":" + os.environ["PATH"], STATE=str(state), REQUEST_LOG=str(state / "requests"), JELLYFIN_BASE_URL=base, JELLYFIN_BIND="127.0.0.1", OIDC_SECRET="b" * 64, BOOTSTRAP_PASSWORD="a" * 64, OIDC_ISSUER_PORT="29490", SYNOPKGLAND_STARTUP_BUDGET_SECONDS="60")
            subprocess.run(["sh", "-c", script], env=env, check=True, capture_output=True, timeout=10)
            self.assertTrue((state / "requests").exists(), "An old provider fingerprint must trigger resynchronization")
            urls = (state / "requests").read_text().splitlines()
            self.assertTrue(urls)
            self.assertTrue(all(url.startswith("http://127.0.0.1:29497" + base + "/") for url in urls), urls)
            self.assertIn("http://127.0.0.1:29497" + base + "/sso/OID/Add/dsm", urls)
            self.assertIn("http://127.0.0.1:29497" + base + "/System/Configuration/Branding", urls)
            posted = json.loads((state / "provider-posted.json").read_text())
            self.assertNotIn("SchemeOverride", posted)
            self.assertEqual(posted["OidSecret"], "b" * 64)
            self.assertEqual(posted["OidEndpoint"], "http://127.0.0.1:29490")
            self.assertIn("<BaseUrl>" + base + "</BaseUrl>", (state / "config/config/network.xml").read_text())
            self.assertIn("<InternalHttpPort>29496</InternalHttpPort>", (state / "config/config/network.xml").read_text())
            import xml.etree.ElementTree as ET
            network = ET.parse(state / "config/config/network.xml").getroot()
            self.assertEqual([p.text for p in network.findall("KnownProxies/string")], ["127.0.0.1"])
            self.assertEqual(network.findtext("EnableHttps"), "false")
            provider_hash = hashlib.sha256((state / "provider.json").read_bytes()).hexdigest()
            expected = hashlib.sha256(("b" * 64 + ":29490:" + base + ":" + provider_hash).encode()).hexdigest()
            self.assertEqual((state / "oidc.fingerprint").read_text(), expected)
            (state / "requests").unlink()
            subprocess.run(["sh", "-c", script], env=env, check=True, capture_output=True, timeout=10)
            self.assertFalse((state / "requests").exists(), "Unchanged configuration must skip bootstrap")

    def renderer(self):
        spec = importlib.util.spec_from_file_location(
            "render", ROOT / "scripts/render.py"
        )
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
        return m

    def test_tampered_plugin_is_rejected(self):
        m = self.renderer()
        with tempfile.TemporaryDirectory() as d:
            p = pathlib.Path(d) / "plugin.zip"
            p.write_bytes(b"not the release artifact")
            with self.assertRaises(ValueError):
                m.plugin_files(p)

    def test_native_identity_and_readonly_media(self):
        m = self.renderer()
        manifest = m.manifest()
        self.assertEqual(manifest["version"], "12.4")
        self.assertEqual(
            manifest["build"],
            json.loads((ROOT / "upstream-source.json").read_text())["build"],
        )
        gw = manifest["identity_gateway"]
        self.assertEqual(gw["access"], "dsm-users")
        self.assertEqual(gw["mode"], "oidc")
        self.assertEqual(
            gw["oidc"]["clients"][0]["redirect_paths"], ["/sso/OID/redirect/dsm"]
        )
        service = manifest["compose"]["services"]["jellyfin"]
        self.assertEqual(service["network"], "host")
        self.assertEqual(
            manifest["install"]["sharedFolder"],
            {"mode": "select", "key": "media", "permission": "ro", "picker": "folder"},
        )
        self.assertEqual(
            manifest["compose"]["shares"]["media"],
            {
                "select": "install",
                "picker": "folder",
                "permission": "ro",
                "mounts": [{"service": "jellyfin", "target": "/media"}],
            },
        )
        self.assertNotIn("ctl", manifest)

    def test_callback_uses_request_scheme(self):
        provider = self.renderer().provider("a" * 64)
        self.assertNotIn("SchemeOverride", provider)
        self.assertNotIn("PortOverride", provider)
        # This permits the loopback HTTP issuer; external scheme comes from the request.
        self.assertTrue(provider["DisableHttps"])

    def test_render_embeds_only_verified_plugin_files(self):
        m = self.renderer()
        files = m.plugin_files(ROOT / "vendor/sso-authentication_4.0.0.4.zip")
        self.assertEqual(
            set(files),
            {
                "meta.json",
                "SSO-Auth.dll",
                "Duende.IdentityModel.dll",
                "Duende.IdentityModel.OidcClient.dll",
            },
        )
        self.assertEqual(m.provider("a" * 64)["DefaultUsernameClaim"], "sub")
        self.assertEqual(m.provider("a" * 64)["AdminRoles"], ["admin"])


if __name__ == "__main__":
    unittest.main()
