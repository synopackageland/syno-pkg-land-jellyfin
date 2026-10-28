import importlib.util, pathlib, unittest, tempfile, json

ROOT = pathlib.Path(__file__).resolve().parents[1]


class RuntimeTests(unittest.TestCase):
    def test_dedicated_gateway_port_and_rendered_manifest(self):
        manifest = self.renderer().manifest()
        self.assertEqual(manifest["identity_gateway"]["listen"]["https"], 33443)
        self.assertEqual(manifest["identity_gateway"]["oidc"]["issuer_port"], 29490)
        self.assertEqual(manifest["compose"]["web"]["port"], 29496)
        self.assertIn("network 29497", (ROOT / "container/start.sh").read_text())
        self.assertEqual(manifest["build"], 12)
        self.assertEqual(json.loads((ROOT / "dsm-package.yaml").read_text()), manifest)

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
        self.assertEqual(manifest["version"], "12.2")
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
            {"mode": "select", "key": "media", "permission": "ro"},
        )
        self.assertEqual(
            manifest["compose"]["shares"]["media"],
            {
                "select": "install",
                "mounts": [{"service": "jellyfin", "target": "/media"}],
            },
        )
        self.assertNotIn("ctl", manifest)

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
