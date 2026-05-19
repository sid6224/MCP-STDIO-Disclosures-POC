// SAFE MCP SERVER DEMO (Go)
// Only allows a fixed allowlist of safe commands (GUARDRAILS)
// Demonstrates how developer validation prevents OS command injection
package main

import (
	"database/sql"
	"encoding/json"
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

var allowedCommand = "ls"
var allowedArgs = []string{"-lrth", "/"}

func runHandler(w http.ResponseWriter, r *http.Request) {
	var req RunRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		http.Error(w, "invalid json", http.StatusBadRequest)
		return
	}
	// GUARDRAIL: Only allow specific command/args
	if req.Command != allowedCommand || len(req.Args) != 2 || req.Args[0] != allowedArgs[0] || req.Args[1] != allowedArgs[1] {
		w.WriteHeader(403)
		w.Write([]byte(`{"status":"rejected","reason":"Command or args not allowed"}`))
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
	json.NewEncoder(w).Encode(resp)
}

func main() {
	http.HandleFunc("/run", runHandler)
	http.HandleFunc("/tool/employees", employeesHandler)
	log.Println("SAFE Go MCP server running on http://127.0.0.1:6006")
	log.Fatal(http.ListenAndServe(":6006", nil))
}
