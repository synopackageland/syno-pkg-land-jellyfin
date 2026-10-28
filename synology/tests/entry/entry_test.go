package entry

import (
	"bytes"
	"context"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"os"
	"os/exec"
	"path/filepath"
	"reflect"
	"strings"
	"sync/atomic"
	"testing"
	"time"

	gateway "github.com/synopackageland/syno-pkg-land-sdk/idgateway"
)

var expected = []string{"/System", "/Users", "/QuickConnect", "/Items", "/UserItems", "/UserViews", "/Sessions", "/Videos", "/Audio", "/socket", "/Auth", "/Playback"}

type fixtureDirectory struct{}

func (fixtureDirectory) Name(context.Context, int) (string, error) { return "", gateway.ErrNoAccount }
func (fixtureDirectory) Groups(context.Context, string) ([]string, error) {
	return nil, gateway.ErrNoAccount
}

func TestEntryContract(t *testing.T) {
	root, err := filepath.Abs("../..")
	if err != nil {
		t.Fatal(err)
	}
	cmd := exec.Command("node", "--input-type=module", "--eval",
		`import {readFileSync} from 'node:fs'; import YAML from 'yaml'; process.stdout.write(JSON.stringify(YAML.parse(readFileSync('dsm-package.yaml','utf8'))));`)
	cmd.Dir = root
	raw, err := cmd.Output()
	if err != nil {
		t.Fatalf("read manifest with locked npm dependencies: %v", err)
	}
	var manifest struct {
		Package string         `json:"package"`
		Entry   string         `json:"entry"`
		Gateway gateway.Config `json:"identity_gateway"`
	}
	if err := json.Unmarshal(raw, &manifest); err != nil {
		t.Fatal(err)
	}
	cfg := manifest.Gateway
	if !reflect.DeepEqual(cfg.UpstreamAuthPaths, expected) {
		t.Fatalf("upstream_auth_paths = %v; want exactly %v", cfg.UpstreamAuthPaths, expected)
	}
	if manifest.Entry != "app-privilege" || cfg.Mode != "oidc" || cfg.Access != "dsm-users" {
		t.Fatalf("entry/login policy changed: %s %s %s", manifest.Entry, cfg.Mode, cfg.Access)
	}
	if cfg.UpstreamAccess != "" || len(cfg.Passthrough) != 0 || len(cfg.OptionalPassthrough) != 0 {
		t.Fatal("unexpected broader upstream bypass")
	}
	if path := os.Getenv("SPL_GATEWAY_POLICY"); path != "" {
		policy, err := gateway.LoadConfig(path)
		if err != nil {
			t.Fatal(err)
		}
		if !reflect.DeepEqual(policy.UpstreamAuthPaths, expected) ||
			policy.Entry != manifest.Entry || policy.Mode != cfg.Mode || policy.Access != cfg.Access {
			t.Fatal("packaged policy differs from the manifest contract")
		}
	}
	var hits atomic.Int64
	upstream := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		hits.Add(1)
		if r.Header.Get("Authorization") != "Bearer fixture" || r.Header.Get("Cookie") != "native=fixture" {
			t.Error("upstream credentials were changed")
		}
		if r.Header.Get("Remote-User") != "" || r.Header.Get("X-Syno-User") != "" {
			t.Error("trusted identity leaked to upstream-auth path")
		}
		w.WriteHeader(http.StatusNoContent)
	}))
	defer upstream.Close()
	frontConfig := gateway.FrontConfig{
		Package: manifest.Package, Entry: manifest.Entry, Mode: cfg.Mode, Access: cfg.Access,
		UpstreamAuthPaths: cfg.UpstreamAuthPaths, Upstream: upstream.URL,
		Key:      bytes.Repeat([]byte{42}, 32),
		Accounts: fixtureDirectory{}, Membership: fixtureDirectory{},
		AuthorizeCGI: "/webman/3rdparty/" + manifest.Package + "/sso/authorize.cgi",
		DSMPorts:     gateway.DSMPorts{HTTP: 5000, HTTPS: 5001},
	}
	if cfg.Mode == gateway.ModeOIDC {
		key, err := gateway.LoadOrCreateSigningKey(filepath.Join(t.TempDir(), "signing.pem"))
		if err != nil {
			t.Fatal(err)
		}
		frontConfig.Issuer = "http://127.0.0.1:18090"
		frontConfig.Provider, err = gateway.NewProvider(frontConfig.Issuer, "example.invalid", key,
			[]gateway.Client{{ID: "fixture", SecretSHA256: bytes.Repeat([]byte{42}, 32), RedirectPaths: []string{"/callback"}}}, time.Now)
		if err != nil {
			t.Fatal(err)
		}
	}
	front, err := gateway.NewFront(frontConfig)
	if err != nil {
		t.Fatal(err)
	}
	request := func(method, path string, browser bool) *httptest.ResponseRecorder {
		t.Helper()
		r := httptest.NewRequest(method, "https://app.example"+path, nil)
		r.RemoteAddr = "203.0.113.7:4444"
		r.Header.Set("Accept", "application/json")
		r.Header.Set("Authorization", "Bearer fixture")
		r.Header.Set("Cookie", "native=fixture; id=dsm; did=device")
		r.Header.Set("Remote-User", "forged")
		r.Header.Set("X-Syno-User", "forged")
		if browser {
			r.Header.Set("Accept", "text/html")
			r.Header.Set("Sec-Fetch-Mode", "navigate")
		}
		w := httptest.NewRecorder()
		front.ServeHTTP(w, r)
		return w
	}
	for _, prefix := range expected {
		for _, path := range []string{prefix, prefix + "/", prefix + "/child?key=value"} {
			for _, method := range []string{"GET", "POST"} {
				if w := request(method, path, false); w.Code != http.StatusNoContent {
					t.Fatalf("allowed %s %s: %d %s", method, path, w.Code, w.Body)
				}
			}
		}
	}
	protected := []string{"/", "/web", "/web/index.html", "/sso", "/sso/OID/start/dsm"}
	for _, prefix := range expected {
		protected = append(protected, prefix+"-outside")
		for i, c := range prefix {
			if c >= 'a' && c <= 'z' || c >= 'A' && c <= 'Z' {
				changed := byte(c) ^ 32
				protected = append(protected, prefix[:i]+string(changed)+prefix[i+1:])
				break
			}
		}
	}
	for _, path := range []string{"/_sso/private", "/_spl/private"} {
		before := hits.Load()
		w := request("GET", path, false)
		if w.Code != http.StatusNotFound && w.Code != http.StatusUnauthorized && w.Code != http.StatusForbidden {
			t.Fatalf("reserved %s was accepted: %d", path, w.Code)
		}
		if hits.Load() != before {
			t.Fatalf("reserved %s reached upstream", path)
		}
	}
	for _, path := range protected {
		before := hits.Load()
		for _, method := range []string{"GET", "POST"} {
			if w := request(method, path, false); w.Code != http.StatusUnauthorized && w.Code != http.StatusForbidden {
				t.Fatalf("unlisted %s %s escaped DSM gate: %d", method, path, w.Code)
			}
		}
		if path == "/" {
			w := request("GET", path, true)
			if w.Code != http.StatusFound || !strings.Contains(w.Header().Get("Location"), "/sso/authorize.cgi?") {
				t.Fatalf("browser root did not start DSM sign-in: %d %s", w.Code, w.Header().Get("Location"))
			}
		}
		if hits.Load() != before {
			t.Fatalf("protected %s reached upstream", path)
		}
	}
}
