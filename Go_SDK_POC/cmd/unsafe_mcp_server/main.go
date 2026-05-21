// UNSAFE MCP SERVER DEMO (Go)
// Forwards any received 'command' and 'args' directly to exec.Command (NO GUARDRAILS)
// Demonstrates how OS commands can be executed if developer does not validate input
package main

import (
	"database/sql"
	"encoding/json"
	"io/ioutil"
	"log"
	"net/http"
	"os"
	"os/exec"
	"path/filepath"

	_ "github.com/mattn/go-sqlite3"
)

type RunRequest struct {
	Command string   `json:"command"`
	Args    []string `json:"args"`
}

var dbPath = filepath.Join(filepath.Dir(os.Args[0]), "demo_employees.db")
var unsafeMarkerPath = "/tmp/mcp_unsafe_os_listing.txt"

func runHandler(w http.ResponseWriter, r *http.Request) {
	var req RunRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		http.Error(w, "invalid json", http.StatusBadRequest)
		return
	}
	cmd := exec.Command(req.Command, req.Args...)
	err := cmd.Run()
	if err != nil {
		w.WriteHeader(500)
		w.Write([]byte(`{"status":"error","error":"` + err.Error() + `"}`))
		return
	}
	w.Write([]byte(`{"status":"executed","command":"` + req.Command + `"}`))
}

func ensureEmployeeDB() error {
	db, err := sql.Open("sqlite3", dbPath)
	if err != nil {
		return err
	}
	defer db.Close()
	_, err = db.Exec(`CREATE TABLE IF NOT EXISTS employees (
		id INTEGER PRIMARY KEY,
		name TEXT NOT NULL,
		department TEXT NOT NULL,
		email TEXT NOT NULL
	)`)
	if err != nil {
		return err
	}
	var count int
	err = db.QueryRow("SELECT COUNT(*) FROM employees").Scan(&count)
	if err != nil {
		return err
	}
	if count == 0 {
		_, err = db.Exec(`INSERT INTO employees (name, department, email) VALUES
			('Asha Rao', 'Finance', 'asha.rao@example.com'),
			('Rohan Mehta', 'Engineering', 'rohan.mehta@example.com'),
			('Mira Sen', 'HR', 'mira.sen@example.com')
		`)
		if err != nil {
			return err
		}
	}
	return nil
}

func employeesHandler(w http.ResponseWriter, r *http.Request) {
	if err := ensureEmployeeDB(); err != nil {
		http.Error(w, "db error: "+err.Error(), 500)
		return
	}
	db, err := sql.Open("sqlite3", dbPath)
	if err != nil {
		http.Error(w, err.Error(), 500)
		return
	}
	defer db.Close()
	rows, err := db.Query("SELECT id, name, department, email FROM employees ORDER BY id")
	if err != nil {
		http.Error(w, err.Error(), 500)
		return
	}
	defer rows.Close()
	type Emp struct {
		ID         int    `json:"id"`
		Name       string `json:"name"`
		Department string `json:"department"`
		Email      string `json:"email"`
	}
	var emps []Emp
	for rows.Next() {
		var e Emp
		if err := rows.Scan(&e.ID, &e.Name, &e.Department, &e.Email); err != nil {
			http.Error(w, err.Error(), 500)
			return
		}
		emps = append(emps, e)
	}
	resp := map[string]interface{}{"status": "ok", "employees": emps}
	w.Header().Set("Content-Type", "application/json")
	enc := json.NewEncoder(w)
	enc.SetEscapeHTML(false)
	_ = enc.Encode(resp)
}

func unsafeOSListingHandler(w http.ResponseWriter, r *http.Request) {
	if _, err := os.Stat(unsafeMarkerPath); os.IsNotExist(err) {
		w.WriteHeader(404)
		json.NewEncoder(w).Encode(map[string]interface{}{"status": "missing", "detail": "No marker file yet"})
		return
	}
	content, err := ioutil.ReadFile(unsafeMarkerPath)
	if err != nil {
		w.WriteHeader(500)
		json.NewEncoder(w).Encode(map[string]interface{}{"status": "error", "detail": err.Error()})
		return
	}
	json.NewEncoder(w).Encode(map[string]interface{}{"status": "ok", "path": unsafeMarkerPath, "listing": string(content)})
}

func main() {
	logFile, err := os.OpenFile("unsafe_mcp_server.log", os.O_CREATE|os.O_WRONLY|os.O_APPEND, 0644)
	if err != nil {
		panic("Failed to open log file: " + err.Error())
	}
	log.SetOutput(logFile)
	http.HandleFunc("/run", runHandler)
	http.HandleFunc("/tool/employees", employeesHandler)
	http.HandleFunc("/unsafe/os-listing", unsafeOSListingHandler)
	log.Println("UNSAFE Go MCP server running on http://127.0.0.1:6005")
	log.Fatal(http.ListenAndServe(":6005", nil))
}
