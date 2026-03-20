# ============================================================
# config.py — SQL Agent Toolkit Configuration
# ============================================================
# Edit the values in this file before running anything.
# This is the only file you need to change per client/machine.
# ============================================================

# ------------------------------------------------------------
# ACTIVE CLIENT
# Change this to switch between clients
# ------------------------------------------------------------
ACTIVE_CLIENT = "client_example1"

# ------------------------------------------------------------
# DATABASE CONNECTION
# Fill in your SQL Server details below
# ------------------------------------------------------------
DB_CONFIG = {
    "server":   "localhost",          # e.g. localhost or DESKTOP-ABC\\SQLEXPRESS
    "database": "VEXA", # e.g. AcmeProduction
    "driver":   "ODBC Driver 17 for SQL Server",

    # --- Authentication: pick ONE option ---

    # Option A: Windows Authentication (most common for local dev)
    "trusted_connection": "yes",

    # Option B: SQL Server login (comment out Option A and uncomment these)
    # "trusted_connection": "no",
    # "username": "sa",
    # "password": "your_password",
}

# ------------------------------------------------------------
# OLLAMA SETTINGS
# ------------------------------------------------------------
OLLAMA_BASE_URL = "http://localhost:11434"

MODELS = {
    "optimizer": "qwen2.5-coder:14b",   # writes fixes, index scripts, reports
    "reasoner":  "deepseek-r1:14b",     # diagnoses WHY something is slow
}

# ------------------------------------------------------------
# AGENT BEHAVIOUR
# ------------------------------------------------------------
BENCHMARK_RUNS     = 10      # how many times to run before/after timing
MAX_SCHEMA_TABLES  = 20      # max tables to pull schema for in one call
AUTO_COMMIT_GIT    = True    # auto git commit after every optimization
SAVE_REPORTS       = True    # auto save reports to /reports folder

# ------------------------------------------------------------
# PATHS  (you generally don't need to change these)
# ------------------------------------------------------------
import os

BASE_DIR        = os.path.dirname(os.path.abspath(__file__))
PROJECTS_DIR    = os.path.join(BASE_DIR, "projects")
MIGRATIONS_DIR  = os.path.join(BASE_DIR, "migrations")
REPORTS_DIR     = os.path.join(BASE_DIR, "reports")
DEPLOYMENTS_DIR = os.path.join(BASE_DIR, "deployments")
PLANS_DIR       = os.path.join(BASE_DIR, "plans")
HISTORY_DB      = os.path.join(BASE_DIR, "query_history.db")

# Active client paths
CLIENT_DIR      = os.path.join(PROJECTS_DIR, ACTIVE_CLIENT)
