package kb_test

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"os"
	"testing"
	"time"

	jwtpkg "github.com/mymikasa/pivot/pkg/jwt"
)

const (
	baseURL    = "http://localhost:8082"
	testSecret = "pivot-dev-jwt-secret-2026-change-in-prod"
)

func getToken(t *testing.T, userID int64, role string) string {
	t.Helper()
	issuer := jwtpkg.NewIssuer(jwtpkg.Config{
		Secret:     testSecret,
		AccessTTL:  15 * time.Minute,
		RefreshTTL: 168 * time.Hour,
		Issuer:     "pivot",
		Audience:   "kb",
	})
	access, _, err := issuer.Sign(userID, role)
	if err != nil {
		t.Fatalf("sign token: %v", err)
	}
	return access
}

func doRequest(t *testing.T, method, path string, body any, token string) *http.Response {
	t.Helper()
	var bodyReader io.Reader
	if body != nil {
		b, err := json.Marshal(body)
		if err != nil {
			t.Fatalf("marshal body: %v", err)
		}
		bodyReader = bytes.NewReader(b)
	}
	req, err := http.NewRequest(method, baseURL+path, bodyReader)
	if err != nil {
		t.Fatalf("new request: %v", err)
	}
	if token != "" {
		req.Header.Set("Authorization", "Bearer "+token)
	}
	if body != nil {
		req.Header.Set("Content-Type", "application/json")
	}
	resp, err := http.DefaultClient.Do(req)
	if err != nil {
		t.Fatalf("do request %s %s: %v", method, path, err)
	}
	return resp
}

func decodeJSON(t *testing.T, resp *http.Response, v any) {
	t.Helper()
	defer resp.Body.Close()
	if err := json.NewDecoder(resp.Body).Decode(v); err != nil {
		t.Fatalf("decode json: %v", err)
	}
}

// TestMain skips E2E tests unless PIVOT_E2E=1 is set.
func TestMain(m *testing.M) {
	if os.Getenv("PIVOT_E2E") != "1" {
		fmt.Println("skipping E2E tests; set PIVOT_E2E=1 to run")
		os.Exit(0)
	}
	os.Exit(m.Run())
}

func TestKBFullFlow(t *testing.T) {
	token := getToken(t, 1, "admin")

	// Step 1: List KBs (should be empty or return existing)
	t.Run("list_empty", func(t *testing.T) {
		resp := doRequest(t, http.MethodGet, "/api/v1/kb", nil, token)
		if resp.StatusCode != http.StatusOK {
			body, _ := io.ReadAll(resp.Body)
			resp.Body.Close()
			t.Fatalf("expected 200, got %d: %s", resp.StatusCode, body)
		}
		var result struct {
			Items []struct {
				ID string `json:"id"`
			} `json:"items"`
		}
		decodeJSON(t, resp, &result)
		t.Logf("initial KB count: %d", len(result.Items))
	})

	// Step 2: Create KB
	var kbID string
	t.Run("create", func(t *testing.T) {
		resp := doRequest(t, http.MethodPost, "/api/v1/kb", map[string]string{
			"name":        fmt.Sprintf("e2e-test-%d", time.Now().UnixMilli()),
			"description": "created by e2e test",
		}, token)
		if resp.StatusCode != http.StatusOK {
			body, _ := io.ReadAll(resp.Body)
			resp.Body.Close()
			t.Fatalf("expected 200, got %d: %s", resp.StatusCode, body)
		}
		var result struct {
			Kb struct {
				ID          string `json:"id"`
				Name        string `json:"name"`
				Description string `json:"description"`
				OwnerID     string `json:"owner_id"`
			} `json:"kb"`
		}
		decodeJSON(t, resp, &result)
		kbID = result.Kb.ID
		if kbID == "" {
			t.Fatal("expected non-empty kb id")
		}
		if result.Kb.OwnerID != "1" {
			t.Fatalf("expected owner_id=1, got %s", result.Kb.OwnerID)
		}
		t.Logf("created KB id=%s name=%s", kbID, result.Kb.Name)
	})

	if kbID == "" {
		t.Fatal("cannot proceed without kbID")
	}

	kbName := fmt.Sprintf("e2e-updated-%d", time.Now().UnixMilli())

	// Step 3: Get KB
	t.Run("get", func(t *testing.T) {
		resp := doRequest(t, http.MethodGet, "/api/v1/kb/"+kbID, nil, token)
		if resp.StatusCode != http.StatusOK {
			body, _ := io.ReadAll(resp.Body)
			resp.Body.Close()
			t.Fatalf("expected 200, got %d: %s", resp.StatusCode, body)
		}
	})

	// Step 4: Update KB
	t.Run("update", func(t *testing.T) {
		resp := doRequest(t, http.MethodPost, "/api/v1/kb/"+kbID+"/update", map[string]string{
			"name":        kbName,
			"description": "updated by e2e",
		}, token)
		if resp.StatusCode != http.StatusOK {
			body, _ := io.ReadAll(resp.Body)
			resp.Body.Close()
			t.Fatalf("expected 200, got %d: %s", resp.StatusCode, body)
		}
		var result struct {
			Kb struct {
				Name        string `json:"name"`
				Description string `json:"description"`
			} `json:"kb"`
		}
		decodeJSON(t, resp, &result)
		if result.Kb.Name != kbName {
			t.Fatalf("expected name=%s, got %s", kbName, result.Kb.Name)
		}
	})

	// Step 5: Upload document
	t.Run("upload_document", func(t *testing.T) {
		uploadResp := doRequest(t, http.MethodPost, "/api/v1/kb/"+kbID+"/documents/upload", map[string]string{
			"filename":     "test.txt",
			"contentType":  "text/plain",
			"data":         "aGVsbG8gZTJl", // base64("hello e2e")
		}, token)
		if uploadResp.StatusCode != http.StatusOK {
			body, _ := io.ReadAll(uploadResp.Body)
			uploadResp.Body.Close()
			t.Fatalf("expected 200, got %d: %s", uploadResp.StatusCode, body)
		}
	})

	// Step 6: List documents
	var docID string
	t.Run("list_documents", func(t *testing.T) {
		resp := doRequest(t, http.MethodGet, "/api/v1/kb/"+kbID+"/documents", nil, token)
		if resp.StatusCode != http.StatusOK {
			body, _ := io.ReadAll(resp.Body)
			resp.Body.Close()
			t.Fatalf("expected 200, got %d: %s", resp.StatusCode, body)
		}
		var result struct {
			Items []struct {
				ID       string `json:"id"`
				Filename string `json:"filename"`
				Status   string `json:"status"`
			} `json:"items"`
		}
		decodeJSON(t, resp, &result)
		if len(result.Items) == 0 {
			t.Fatal("expected at least 1 document")
		}
		docID = result.Items[0].ID
		t.Logf("document id=%s filename=%s status=%s", docID, result.Items[0].Filename, result.Items[0].Status)
	})

	// Step 7: Delete document
	if docID != "" {
		t.Run("delete_document", func(t *testing.T) {
			resp := doRequest(t, http.MethodPost, "/api/v1/kb/"+kbID+"/documents/"+docID+"/delete", nil, token)
			if resp.StatusCode != http.StatusOK {
				body, _ := io.ReadAll(resp.Body)
				resp.Body.Close()
				t.Fatalf("expected 200, got %d: %s", resp.StatusCode, body)
			}
		})
	}

	// Step 8: Delete KB
	t.Run("delete_kb", func(t *testing.T) {
		resp := doRequest(t, http.MethodPost, "/api/v1/kb/"+kbID+"/delete", nil, token)
		if resp.StatusCode != http.StatusOK {
			body, _ := io.ReadAll(resp.Body)
			resp.Body.Close()
			t.Fatalf("expected 200, got %d: %s", resp.StatusCode, body)
		}
	})

	// Step 9: Verify KB is gone
	t.Run("get_deleted", func(t *testing.T) {
		resp := doRequest(t, http.MethodGet, "/api/v1/kb/"+kbID, nil, token)
		if resp.StatusCode == http.StatusOK {
			t.Fatal("expected non-200 for deleted KB")
		}
		t.Logf("deleted KB returns %d (expected)", resp.StatusCode)
		resp.Body.Close()
	})
}

func TestKBUnauthorized(t *testing.T) {
	t.Run("no_token", func(t *testing.T) {
		resp := doRequest(t, http.MethodGet, "/api/v1/kb", nil, "")
		if resp.StatusCode == http.StatusOK {
			t.Fatal("expected non-200 without token")
		}
		resp.Body.Close()
		t.Logf("unauthenticated request returns %d (expected)", resp.StatusCode)
	})
}

func TestKBPermissionDenied(t *testing.T) {
	// Create KB with admin (uid=1)
	adminToken := getToken(t, 1, "admin")
	resp := doRequest(t, http.MethodPost, "/api/v1/kb", map[string]string{
		"name":        fmt.Sprintf("perm-test-%d", time.Now().UnixMilli()),
		"description": "permission test",
	}, adminToken)
	if resp.StatusCode != http.StatusOK {
		body, _ := io.ReadAll(resp.Body)
		resp.Body.Close()
		t.Fatalf("create kb: expected 200, got %d: %s", resp.StatusCode, body)
	}
	var createResult struct {
		Kb struct {
			ID string `json:"id"`
		} `json:"kb"`
	}
	decodeJSON(t, resp, &createResult)
	kbID := createResult.Kb.ID
	defer func() {
		doRequest(t, http.MethodPost, "/api/v1/kb/"+kbID+"/delete", nil, adminToken)
	}()

	// Try to delete with different user (uid=2, role=user)
	userToken := getToken(t, 2, "user")
	delResp := doRequest(t, http.MethodPost, "/api/v1/kb/"+kbID+"/delete", nil, userToken)
	if delResp.StatusCode == http.StatusOK {
		t.Fatal("expected permission denied for non-owner user")
	}
	t.Logf("non-owner delete returns %d (expected)", delResp.StatusCode)
	delResp.Body.Close()
}
