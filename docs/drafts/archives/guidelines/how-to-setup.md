# A.E.G.I.S <small>CODEWORK v0.1.0</small>
# Guide: Setup & Installation

This guide provides step-by-step instructions for deploying the CodeCortex Intelligence Engine in your local environment.

## 📋 Prerequisites

Before starting, ensure your system meets the following requirements:
- **Python**: v3.10 or higher.
- **Git**: Installed and available in the system PATH.
- **SQLite**: (Built-in with Python) for the primary metadata store.
- **Operating System**: Windows (primary target), Linux, or macOS.

## 🚀 Installation Steps

### 1. Clone the Repository
```powershell
git clone <repository-url>
cd codecortex
```

### 2. Prepare Environment
Create and activate a virtual environment to isolate dependencies:
```powershell
python -m venv .venv
.\.venv\Scripts\Activate
```

### 3. Install Dependencies
Install the required Python packages and Tree-Sitter grammars:
```powershell
pip install -r requirements.txt
```

### 4. Configuration
Create a `.env` file in the project root with the following variables:
```env
# Database Path (Relative to root or Absolute)
CODECORTEX_DB_PATH=database/codecortex.db

# Optional: Performance Optimization
CODECORTEX_USE_UPSTREAM_CODEINDEX=false
CODECORTEX_INCREMENTAL_FILE_THRESHOLD=2000

# Optional: Logging
LOG_LEVEL=INFO
```

## 🛠️ Running the Engine

CodeCortex can be run in two primary modes:

### Mode A: MCP Server (Recommended)
This mode allows AI agents (like Antigravity or Claude Desktop) to use CodeCortex tools.
```powershell
python src/main.py
```
*Note: The server communicates via standard I/O (stdio) and should be registered in your agent's configuration file.*

### Mode B: Direct CLI Integration
You can use the built-in scripts for one-off operations:
```powershell
# Example: Triggering a manual indexing
python -c "from src.main import CortexOrchestrator; orchestrator = CortexOrchestrator(); orchestrator.analyze('C:/path/to/project')"
```

## ✅ Verification

To verify the installation, run the following command to check if the MCP server initializes correctly:
```powershell
python src/main.py --help
```
If successful, you should see the FastMCP tool registration logs in the terminal.
