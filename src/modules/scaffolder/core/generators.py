"""
Content generators – produces .gitignore, .env, pyproject.toml, README, Dockerfile, and setup scripts.

:project: CodeCortex
:package: Modules.Scaffolder.Core.Generators
:author: Steeven Andrian
:copyright: (c) 2026 CODDY Codework
:standard: CODDY-Scaffolder-v1.0
"""

from __future__ import annotations

import textwrap
from enum import Enum
from pathlib import Path
import shutil
import logging

logger = logging.getLogger(__name__)

class ProjectCategory(Enum):
    STANDARD = "Standard Python Project"
    DATA_SCIENCE = "Data Science Project"
    WEB_API = "Web API Project"
    CLI_TOOL = "CLI Tool"
    AUTOMATION = "Automation Script"
    CUSTOM = "Custom Boilerplate"

def gitignore(project_type: ProjectCategory) -> str:
    """Generate .gitignore content based on project type."""
    base = textwrap.dedent("""
        # --- Python / Byte-compiled ---
        __pycache__/
        *.py[cod]
        *$py.class

        # Virtual environments
        venv/
        .venv/
        env/

        # IDEs
        .vscode/
        .idea/
        *.swp
        *.swo

        # OS
        .DS_Store
        Thumbs.db

        # Logs
        logs/
        *.log

        # Caches
        caches/
        .mypy_cache/
        .pytest_cache/

        # Outputs
        outputs/

        # Runtime storage
        storage/

        # Vendored dependencies
        vendor/

        # Distribution / packaging
        dist/
        build/
        *.egg-info/

        # Environment variables (keep .env.example tracked)
        .env
        !.env.example
    """).lstrip()

    # Add type-specific ignores
    if project_type == ProjectCategory.DATA_SCIENCE:
        base += textwrap.dedent("""
            # Jupyter
            .ipynb_checkpoints/
            *.ipynb

            # Large data files
            *.csv
            *.h5
            *.hdf5
            *.parquet
            *.feather
        """)
    elif project_type == ProjectCategory.WEB_API:
        base += textwrap.dedent("""
            # Uploads
            uploads/

            # Static files
            staticfiles/
        """)

    return base

def env_boilerplate(project_type: ProjectCategory) -> str:
    """Generate .env.example template content."""
    base = textwrap.dedent("""
        # Copy to .env and fill real values
        # Keep .env.example in version control; .env is gitignored.
        DEBUG=True
        SECRET_KEY=change-me-to-a-secure-random-key
        PYTHONPATH=src
    """).lstrip()

    if project_type == ProjectCategory.DATA_SCIENCE:
        base += textwrap.dedent("""
            # Data Science settings
            DATA_PATH=datasets/
            MODEL_PATH=models/
        """)
    elif project_type == ProjectCategory.WEB_API:
        base += textwrap.dedent("""
            # Web API settings
            HOST=0.0.0.0
            PORT=8000
            DATABASE_URL=sqlite:///db.sqlite3
            CORS_ORIGINS=["http://localhost:3000", "http://127.0.0.1:3000"]
        """)

    return base

def pyproject(author: str, email: str, project_name: str, project_type: ProjectCategory, project_directory: str = None) -> str:
    """Generate pyproject.toml content."""
    base_deps = [
        'pydantic>=2.6',
        'pyyaml>=6.0',
        'python-dotenv>=1.0',
    ]

    if project_type == ProjectCategory.DATA_SCIENCE:
        base_deps.extend([
            'numpy>=1.24',
            'pandas>=2.0',
            'matplotlib>=3.7',
            'scikit-learn>=1.3',
            'jupyter>=1.0',
        ])
    elif project_type == ProjectCategory.WEB_API:
        base_deps.extend([
            'fastapi>=0.104',
            'uvicorn[standard]>=0.24',
            'sqlalchemy>=2.0',
            'alembic>=1.12',
        ])
    elif project_type == ProjectCategory.CLI_TOOL:
        base_deps.extend([
            'click>=8.1',
            'rich>=13.0',
        ])
    elif project_type == ProjectCategory.AUTOMATION:
        base_deps.extend([
            'schedule>=1.2',
            'requests>=2.31',
        ])

    deps_str = "\n".join([f'        "{dep}",' for dep in base_deps])

    # Use project_directory for script name (snake_case) or fallback to project_name converted to snake_case
    script_name = project_directory if project_directory else project_name.lower().replace(' ', '_')

    # Convert project_directory to kebab-case for PEP 508 compliance
    pep508_name = project_directory.replace('_', '-') if project_directory else project_name.lower().replace(' ', '-')

    return textwrap.dedent(f"""
        [build-system]
        requires = ["setuptools>=61.0", "wheel"]
        build-backend = "setuptools.build_meta"

        [project]
        name = "{pep508_name}"
        version = "0.1.0"
        description = "Add your description here"
        authors = [{{name = "{author}", email = "{email}"}}]
        readme = "README.md"
        requires-python = ">=3.10"
        dependencies = [
    {deps_str}
        ]

        [project.scripts]
        {script_name} = "src.main:cli"

        [tool.setuptools.packages.find]
        where = ["src"]

        [tool.mypy]
        python_version = "3.10"
        warn_return_any = true
        warn_unused_configs = true
        disallow_untyped_defs = true

        [tool.pytest.ini_options]
        testpaths = ["tests"]
        python_files = ["test_*.py"]
        python_classes = ["Test*"]
        python_functions = ["test_*"]
    """).lstrip()

def readme(project_name: str, author: str, email: str, project_type: ProjectCategory, license_name: str) -> str:
    """Generate README.md content."""
    badges = [
        "![Status](https://img.shields.io/badge/status-active-success.svg)",
        "![GitHub](https://img.shields.io/badge/license-MIT-blue.svg)",
    ]

    if project_type == ProjectCategory.DATA_SCIENCE:
        badges.extend([
            "![Python](https://img.shields.io/badge/python-3.10%2B-blue)",
            "![Pandas](https://img.shields.io/badge/pandas-2.0%2B-blue)",
            "![Scikit-Learn](https://img.shields.io/badge/scikit--learn-1.3%2B-orange)",
        ])
    elif project_type == ProjectCategory.WEB_API:
        badges.extend([
            "![FastAPI](https://img.shields.io/badge/FastAPI-0.104%2B-green)",
            "![Python](https://img.shields.io/badge/python-3.10%2B-blue)",
        ])

    badges_str = "\n".join(badges)

    project_type_desc = {
        ProjectCategory.STANDARD: "A standard project with a professional structure.",
        ProjectCategory.DATA_SCIENCE: "A data science project with tools for analysis and machine learning.",
        ProjectCategory.WEB_API: "A web API project built with a modern framework.",
        ProjectCategory.CLI_TOOL: "A command-line interface tool.",
        ProjectCategory.AUTOMATION: "An automation script project.",
    }

    return textwrap.dedent(f"""
        # {project_name}

        {badges_str}

        {project_type_desc[project_type]}

        ---

        ## Project Structure

        ```
        {project_name}/
        ├── src/                    # Source code
        │   ├── core/               # Shared abstractions & utilities
        │   ├── app/                # Web application entry (UI)
        │   ├── api/                # API entry (REST/GraphQL)
        │   ├── Modules/            # Business modules (DDD)
        │   └── helpers/            # Module-specific helpers
        ├── config/                 # Configuration files
        ├── database/               # Database migrations & seeds
        ├── public/                 # Web root (static assets)
        ├── storage/                # Runtime data (uploads, cache)
        ├── tests/                  # Test suite
        │   ├── Unit/               # Unit tests
        │   ├── Integration/        # Integration tests
        │   └── Feature/            # Feature/E2E tests
        ├── scripts/                # CLI utilities
        ├── docs/                   # Documentation
        ├── outputs/                # Generated output artifacts
        ├── releases/               # Release artifacts
        ├── datasets/               # Data assets
        ├── .agents/                # AI agent context
        ├── .env.example            # Environment template
        └── .version                # Version file
        ```

        ## Quick Start

        ```bash
        # 1. Install & activate virtualenv
        python -m venv venv
        source venv/bin/activate   # Windows: venv\\Scripts\\activate

        # 2. Install dependencies
        pip install -e .

        # 3. Copy environment template
        cp .env.example .env

        # 4. Run the project
        python run.py
        ```

        ## Environment Variables

        | Variable | Description | Default |
        |----------|-------------|---------|
        | `DEBUG` | Enable debug mode | `True` |
        | `SECRET_KEY` | Secret key for encryption | *(required)* |
        | `PYTHONPATH` | Python module search path | `src` |

        See `.env.example` for the full list.

        ## Development

        ```bash
        # Run tests
        python -m pytest

        # Type checking
        python -m mypy src

        # Format code
        python -m black src tests

        # Lint
        python -m flake8 src
        ```

        ## License

        {f"Licensed under {license_name}" if license_name != "None" else "No license specified"}

        ## Author
        {author} ({email})
    """).lstrip()

def requirements(project_type: ProjectCategory) -> str:
    """Generate requirements.txt content."""
    from .config import get_config_manager
    config_manager = get_config_manager()

    # Get dependencies from configuration
    project_type_str = project_type.name.lower()
    project_deps = config_manager.get_dependencies_for_project_type(project_type_str)

    if project_deps:
        # Use dependencies from config
        requirements_list = []
        requirements_list.append(f"# {project_type.value} dependencies")
        requirements_list.extend(project_deps)
        return "\n".join(requirements_list)

    # Fallback to hardcoded dependencies if config doesn't provide them
    base = textwrap.dedent("""
        # Core dependencies
        pydantic>=2.6
        pyyaml>=6.0
        python-dotenv>=1.0

        # Development
        black>=23.0
        mypy>=1.0
        pytest>=7.0
        ipython>=8.0
    """).lstrip()

    if project_type == ProjectCategory.DATA_SCIENCE:
        base += textwrap.dedent("""
            # Data Science
            numpy>=1.24
            pandas>=2.0
            matplotlib>=3.7
            scikit-learn>=1.3
            jupyter>=1.0
            seaborn>=0.12
            scipy>=1.10
        """)
    elif project_type == ProjectCategory.WEB_API:
        base += textwrap.dedent("""
            # Web API
            fastapi>=0.104
            uvicorn[standard]>=0.24
            sqlalchemy>=2.0
            alembic>=1.12
            python-multipart>=0.0
        """)
    elif project_type == ProjectCategory.CLI_TOOL:
        base += textwrap.dedent("""
            # CLI Tool
            click>=8.1
            rich>=13.0
            typer>=0.9
        """)
    elif project_type == ProjectCategory.AUTOMATION:
        base += textwrap.dedent("""
            # Automation
            schedule>=1.2
            requests>=2.31
            beautifulsoup4>=4.12
            selenium>=4.15
        """)

    return base

def dockerfile(project_type: ProjectCategory) -> str:
    """Generate Dockerfile content."""
    from .config import get_config_manager
    config_manager = get_config_manager()
    config = config_manager.load_config()
    docker_config = config.docker

    base = textwrap.dedent(f"""
        FROM {docker_config.base_image}

        WORKDIR {docker_config.workdir}

        # Install system dependencies
        RUN apt-get update && apt-get install -y \\
            gcc \\
            && rm -rf /var/lib/apt/lists/*

        # Copy requirements and install Python dependencies
        COPY requirements.txt .
        RUN pip install --no-cache-dir -r requirements.txt

        # Copy application code
        COPY . .

        # Create necessary directories
        RUN mkdir -p datasets outputs logs caches

        # Set environment variables
        ENV PYTHONPATH={docker_config.workdir}/src
        ENV PYTHONUNBUFFERED=1

        EXPOSE {docker_config.port}

        CMD ["python", "run.py"]
    """).lstrip()

    if project_type == ProjectCategory.DATA_SCIENCE:
        base += textwrap.dedent("""
            # Additional system dependencies for data science
            RUN apt-get update && apt-get install -y \\
                libopenblas-dev \\
                liblapack-dev \\
                && rm -rf /var/lib/apt/lists/*
        """)

    return base

def docker_compose(project_type: ProjectCategory) -> str:
    """Generate docker-compose.yml content."""
    from .config import get_config_manager
    config_manager = get_config_manager()
    config = config_manager.load_config()
    docker_config = config.docker

    base = textwrap.dedent(f"""
        version: "3.9"
        services:
          app:
            build: .
            volumes:
              - ./datasets:{docker_config.workdir}/datasets
              - ./outputs:{docker_config.workdir}/outputs
              - ./logs:{docker_config.workdir}/logs
              - ./caches:{docker_config.workdir}/caches
            env_file:
              - .env
            ports:
              - "{docker_config.port}:{docker_config.port}"
    """).lstrip()

    if project_type == ProjectCategory.WEB_API:
        base += textwrap.dedent("""
          database:
            image: postgres:15
            environment:
              POSTGRES_USER: postgres
              POSTGRES_PASSWORD: postgres
              POSTGRES_DB: app_db
            volumes:
              - postgres_data:/var/lib/postgresql/data
            ports:
              - "5432:5432"

        volumes:
          postgres_data:
        """)

    return base

def setup_sh(project_name: str, author: str) -> str:
    """Generate setup.sh script."""
    return textwrap.dedent(f"""#!/usr/bin/env bash
        # Setup script for {project_name} - Unix-like systems
        # Created by: {author}
        set -e

        # Parse command line arguments
        CLEAN_MODE=false
        SHOW_HELP=false

        while [[ $# -gt 0 ]]; do
            case $1 in
                --clean)
                    CLEAN_MODE=true
                    shift
                    ;;
                --help)
                    SHOW_HELP=true
                    shift
                    ;;
                *)
                    echo "Unknown option: $1"
                    exit 1
                    ;;
            esac
        done

        if [[ "$SHOW_HELP" == "true" ]]; then
            echo -e "\033[32m{project_name} Setup Script\033[0m"
            echo ""
            echo -e "\033[33mUsage: ./bin/setup.sh [options]\033[0m"
            echo ""
            echo -e "\033[36mOptions:\033[0m"
            echo -e "  --clean    Clean setup: remove existing venv, clear pip cache, force reinstall"
            echo -e "  --help     Show this help message"
            echo ""
            exit 0
        fi

        if [[ "$CLEAN_MODE" == "true" ]]; then
            echo -e "\033[33m🧹 Clean setup mode enabled\033[0m"
            echo -e "\033[32mSetting up {project_name} (CLEAN MODE)...\033[0m"
        else
            echo -e "\033[32mSetting up {project_name}...\033[0m"
        fi
        echo "Author: {author}"
        echo ""

        # Check if Python is installed
        echo -e "\033[33mChecking Python version...\033[0m"
        if ! command -v python3 &> /dev/null; then
            echo -e "\033[31mPython 3 is not installed or not in PATH. Please install Python 3.8 or higher.\033[0m"
            exit 1
        fi

        PYTHON_VERSION=$(python3 --version)
        echo -e "\033[32m$PYTHON_VERSION found\033[0m"
        echo ""

        # Handle clean setup - remove existing venv and clear cache
        if [[ "$CLEAN_MODE" == "true" ]]; then
            if [[ -d "venv" ]]; then
                echo "Removing existing virtual environment..."
                rm -rf venv
                echo -e "\033[32mExisting virtual environment removed\033[0m"
            fi

            echo "Clearing pip cache..."
            python3 -m pip cache purge 2>/dev/null || true
            echo -e "\033[32mPip cache cleared\033[0m"
            echo ""
        fi

        # Create virtual environment
        echo -e "\033[33mSetting up virtual environment...\033[0m"
        if [[ ! -d "venv" ]]; then
            echo "Creating virtual environment..."
            python3 -m venv venv
            echo -e "\033[32mVirtual environment created\033[0m"
        else
            echo -e "\033[32mVirtual environment already exists\033[0m"
        fi
        echo ""

        # Activate virtual environment
        echo -e "\033[33mActivating virtual environment...\033[0m"
        source venv/bin/activate
        echo -e "\033[32mVirtual environment activated\033[0m"
        echo ""

        # Upgrade pip
        echo -e "\033[33mUpgrading pip...\033[0m"
        if python -m pip install --upgrade pip; then
            echo -e "\033[32mPip upgraded\033[0m"
        else
            echo -e "\033[33mFailed to upgrade pip, continuing...\033[0m"
        fi
        echo ""

        # Install dependencies
        INSTALL_FLAGS=""
        if [[ "$CLEAN_MODE" == "true" ]]; then
            INSTALL_FLAGS="--force-reinstall --no-cache-dir"
            echo -e "\033[33mInstalling dependencies (clean mode: force reinstall, no cache)...\033[0m"
        else
            echo -e "\033[33mInstalling dependencies...\033[0m"
        fi

        if [[ -f "requirements.txt" ]]; then
            pip install -r requirements.txt $INSTALL_FLAGS
            echo -e "\033[32mDependencies installed from requirements.txt\033[0m"
        else
            echo -e "\033[33mrequirements.txt not found, installing project in editable mode...\033[0m"
            pip install -e . $INSTALL_FLAGS
            echo -e "\033[32mProject installed in editable mode\033[0m"
        fi

        # Install development dependencies
        echo -e "\033[33mInstalling development dependencies...\033[0m"
        if pip install black mypy pytest ipython $INSTALL_FLAGS; then
            echo -e "\033[32mDevelopment dependencies installed\033[0m"
        else
            echo -e "\033[33mFailed to install development dependencies, continuing...\033[0m"
        fi
        echo ""

        # Create necessary directories
        echo -e "\033[33mCreating necessary directories...\033[0m"
        mkdir -p datasets outputs logs caches
        echo -e "\033[32mDirectories created\033[0m"
        echo ""

        echo -e "\033[32mSetup completed successfully!\033[0m"
        echo ""
        echo -e "\033[36mTo get started:\033[0m"
        echo -e "  1. Activate the virtual environment: source venv/bin/activate"
        echo -e "  2. Run the project: python run.py"
        echo ""
        echo -e "\033[35mHappy coding!\033[0m"
    """).lstrip()

def setup_bat(project_name: str, author: str) -> str:
    """Generate setup.bat script."""
    return textwrap.dedent(f"""
        @echo off
        REM Setup script for {project_name} - Windows Batch
        REM Created by: {author}
        setlocal

        REM Parse command line arguments
        set "CLEAN_MODE=false"
        set "SHOW_HELP=false"

        :parse_args
        if "%~1"=="" goto args_done
        if /i "%~1"=="--clean" (
            set "CLEAN_MODE=true"
            shift
            goto parse_args
        )
        if /i "%~1"=="--help" (
            set "SHOW_HELP=true"
            shift
            goto parse_args
        )
        echo Unknown option: %~1
        exit /b 1

        :args_done

        if "%SHOW_HELP%"=="true" (
            echo {project_name} Setup Script
            echo.
            echo Usage: bin\\setup.bat [options]
            echo.
            echo Options:
            echo   --clean    Clean setup: remove existing venv, clear pip cache, force reinstall
            echo   --help     Show this help message
            echo.
            exit /b 0
        )

        if "%CLEAN_MODE%"=="true" (
            echo Clean setup mode enabled
            echo Setting up {project_name} ^(CLEAN MODE^)...
        ) else (
            echo Setting up {project_name}...
        )
        echo Author: {author}
        echo.

        REM Check if Python is installed
        echo Checking Python version...
        python --version >nul 2>&1
        if %errorlevel% neq 0 (
            echo Python is not installed or not in PATH. Please install Python 3.8 or higher.
            pause
            exit /b 1
        )

        for /f "tokens=2" %%i in ('python --version 2^>^&1') do set "PYTHON_VERSION=%%i"
        echo Python %PYTHON_VERSION% found
        echo.

        REM Handle clean setup - remove existing venv and clear cache
        if "%CLEAN_MODE%"=="true" (
            if exist "venv" (
                echo Removing existing virtual environment...
                rmdir /s /q "venv"
                echo Existing virtual environment removed
            )

            echo Clearing pip cache...
            python -m pip cache purge >nul 2>&1
            echo Pip cache cleared
            echo.
        )

        REM Create virtual environment
        echo Setting up virtual environment...
        if not exist "venv" (
            echo Creating virtual environment...
            python -m venv venv
            if %errorlevel% neq 0 (
                echo Failed to create virtual environment
                pause
                exit /b 1
            )
            echo Virtual environment created
        ) else (
            echo Virtual environment already exists
        )
        echo.

        REM Activate virtual environment
        echo Activating virtual environment...
        call venv\\Scripts\\activate.bat
        if %errorlevel% neq 0 (
            echo Failed to activate virtual environment
            pause
            exit /b 1
        )
        echo Virtual environment activated
        echo.

        REM Upgrade pip
        echo Upgrading pip...
        python -m pip install --upgrade pip
        if %errorlevel% neq 0 (
            echo Failed to upgrade pip, continuing...
        ) else (
            echo Pip upgraded
        )
        echo.

        REM Install dependencies
        if "%CLEAN_MODE%"=="true" (
            echo Installing dependencies ^(clean mode: force reinstall, no cache^)...
            if exist "requirements.txt" (
                pip install -r requirements.txt --force-reinstall --no-cache-dir
                if %errorlevel% neq 0 (
                    echo Failed to install dependencies from requirements.txt
                    pause
                    exit /b 1
                )
                echo Dependencies installed from requirements.txt
            ) else (
                echo requirements.txt not found, installing project in editable mode...
                pip install -e . --force-reinstall --no-cache-dir
                if %errorlevel% neq 0 (
                    echo Failed to install project in editable mode
                    pause
                    exit /b 1
                )
                echo Project installed in editable mode
            )
            echo Installing development dependencies...
            pip install black mypy pytest ipython --force-reinstall --no-cache-dir
            if %errorlevel% neq 0 (
                echo Failed to install development dependencies
                pause
                exit /b 1
            )
        ) else (
            echo Installing dependencies...
            if exist "requirements.txt" (
                pip install -r requirements.txt
                if %errorlevel% neq 0 (
                    echo Failed to install dependencies from requirements.txt
                    pause
                    exit /b 1
                )
                echo Dependencies installed from requirements.txt
            ) else (
                echo requirements.txt not found, installing project in editable mode...
                pip install -e .
                if %errorlevel% neq 0 (
                    echo Failed to install project in editable mode
                    pause
                    exit /b 1
                )
                echo Project installed in editable mode
            )
            echo Installing development dependencies...
            pip install black mypy pytest ipython
            if %errorlevel% neq 0 (
                echo Failed to install development dependencies
                pause
                exit /b 1
            )
        )
        echo Development dependencies installed
        echo.

        REM Create necessary directories
        echo Creating necessary directories...
        if not exist datasets mkdir datasets
        if not exist outputs mkdir outputs
        if not exist logs mkdir logs
        if not exist caches mkdir caches
        echo Directories created
        echo.

        echo Setup completed successfully!
        echo.
        echo To get started:
        echo   1. Activate the virtual environment: venv\\Scripts\\activate.bat
        echo   2. Run the project: python run.py
        echo.
        echo Happy coding!
    """).lstrip()

def setup_ps1(project_name: str, author: str) -> str:
    """Generate setup.ps1 script."""
    return textwrap.dedent(f"""
        # Setup script for {project_name} - PowerShell
        # Created by: {author}

        param(
            [switch]$Clean,
            [switch]$Help
        )

        $ErrorActionPreference = "Stop"

        if ($Help) {{
            Write-Host "{project_name} Setup Script" -ForegroundColor Green
            Write-Host ""
            Write-Host "Usage: .\\bin\\setup.ps1 [options]" -ForegroundColor Yellow
            Write-Host ""
            Write-Host "Options:" -ForegroundColor Cyan
            Write-Host "  --clean    Clean setup: remove existing venv, clear pip cache, force reinstall" -ForegroundColor White
            Write-Host "  --help     Show this help message" -ForegroundColor White
            Write-Host ""
            exit 0
        }}

        if ($Clean) {{
            Write-Host "🧹 Clean setup mode enabled" -ForegroundColor Yellow
            Write-Host "Setting up {project_name} (CLEAN MODE)..." -ForegroundColor Green
        }} else {{
            Write-Host "Setting up {project_name}..." -ForegroundColor Green
        }}
        Write-Host "Author: {author}"
        Write-Host ""

        try {{
            # Check if Python is installed
            Write-Host "Checking Python version..." -ForegroundColor Yellow
            $pythonVersion = python --version 2>$null
            if ($LASTEXITCODE -ne 0) {{
                Write-Host "Python is not installed or not in PATH. Please install Python 3.8 or higher." -ForegroundColor Red
                Read-Host "Press Enter to exit"
                exit 1
            }}

            Write-Host "$pythonVersion found" -ForegroundColor Green
            Write-Host ""

            # Handle clean setup - remove existing venv and clear cache
            if ($Clean) {{
                if (Test-Path "venv") {{
                    Write-Host "Removing existing virtual environment..."
                    Remove-Item -Recurse -Force "venv"
                    Write-Host "Existing virtual environment removed" -ForegroundColor Green
                }}

                Write-Host "Clearing pip cache..."
                python -m pip cache purge 2>$null
                Write-Host "Pip cache cleared" -ForegroundColor Green
                Write-Host ""
            }}

            # Create virtual environment
            Write-Host "Setting up virtual environment..." -ForegroundColor Yellow
            if (-not (Test-Path "venv")) {{
                Write-Host "Creating virtual environment..."
                python -m venv venv
                if ($LASTEXITCODE -ne 0) {{
                    throw "Failed to create virtual environment"
                }}
                Write-Host "Virtual environment created" -ForegroundColor Green
            }} else {{
                Write-Host "Virtual environment already exists" -ForegroundColor Green
            }}
            Write-Host ""

            # Activate virtual environment
            Write-Host "Activating virtual environment..." -ForegroundColor Yellow
            & ".\\venv\\Scripts\\Activate.ps1"
            if ($LASTEXITCODE -ne 0) {{
                throw "Failed to activate virtual environment"
            }}
            Write-Host "Virtual environment activated" -ForegroundColor Green
            Write-Host ""

            # Upgrade pip
            Write-Host "Upgrading pip..." -ForegroundColor Yellow
            python -m pip install --upgrade pip
            if ($LASTEXITCODE -eq 0) {{
                Write-Host "Pip upgraded" -ForegroundColor Green
            }} else {{
                Write-Host "Failed to upgrade pip, continuing..." -ForegroundColor Yellow
            }}
            Write-Host ""

            # Install dependencies
            $installFlags = ""
            if ($Clean) {{
                $installFlags = "--force-reinstall --no-cache-dir"
                Write-Host "Installing dependencies (clean mode: force reinstall, no cache)..." -ForegroundColor Yellow
            }} else {{
                Write-Host "Installing dependencies..." -ForegroundColor Yellow
            }}

            if (Test-Path "requirements.txt") {{
                $command = "pip install -r requirements.txt $installFlags".Trim()
                Invoke-Expression $command
                if ($LASTEXITCODE -ne 0) {{
                    throw "Failed to install dependencies"
                }}
                Write-Host "Dependencies installed from requirements.txt" -ForegroundColor Green
            }} else {{
                Write-Host "requirements.txt not found, installing project in editable mode..." -ForegroundColor Yellow
                $command = "pip install -e . $installFlags".Trim()
                Invoke-Expression $command
                if ($LASTEXITCODE -ne 0) {{
                    throw "Failed to install project"
                }}
                Write-Host "Project installed in editable mode" -ForegroundColor Green
            }}

            # Install development dependencies
            Write-Host "Installing development dependencies..." -ForegroundColor Yellow
            $devCommand = "pip install black mypy pytest ipython $installFlags".Trim()
            Invoke-Expression $devCommand
            if ($LASTEXITCODE -eq 0) {{
                Write-Host "Development dependencies installed" -ForegroundColor Green
            }} else {{
                Write-Host "Failed to install development dependencies, continuing..." -ForegroundColor Yellow
            }}
            Write-Host ""

            # Create necessary directories
            Write-Host "Creating necessary directories..." -ForegroundColor Yellow
            @("datasets", "outputs", "logs", "caches") | ForEach-Object {{
                if (-not (Test-Path $_)) {{
                    New-Item -ItemType Directory -Path $_ -Force | Out-Null
                }}
            }}
            Write-Host "Directories created" -ForegroundColor Green
            Write-Host ""

            Write-Host "Setup completed successfully!" -ForegroundColor Green
            Write-Host ""
            Write-Host "To get started:" -ForegroundColor Cyan
            Write-Host "  1. Activate the virtual environment: .\\venv\\Scripts\\Activate.ps1" -ForegroundColor White
            Write-Host "  2. Run the project: python run.py" -ForegroundColor White
            Write-Host ""
            Write-Host "Happy coding!" -ForegroundColor Magenta

        }} catch {{
            Write-Host "Setup failed: $($_.Exception.Message)" -ForegroundColor Red
            Read-Host "Press Enter to exit"
            exit 1
        }}
    """).lstrip()

def logger_py(author: str) -> str:
    """Generate logger.py content with structured JSON logging per CODDY Codework standards."""
    return textwrap.dedent(f'''
        """
        src/core/logger.py
        Structured JSON logging module

        Complies with CODDY Codework logging-standard.md
        """

        from __future__ import annotations

        import json
        import logging
        import os
        import sys
        import uuid
        from datetime import datetime
        from pathlib import Path
        from typing import Any, Dict, Optional

        class JSONLogFormatter(logging.Formatter):
            """JSON formatter for structured logging."""

            def __init__(
                self,
                service: str = "app",
                environment: str = "development",
                version: str = "0.1.0"
            ):
                super().__init__()
                self.service = service
                self.environment = environment
                self.version = version

            def format(self, record: logging.LogRecord) -> str:
                """Format log record as JSON."""
                log_entry: Dict[str, Any] = {{
                    "timestamp": datetime.utcnow().isoformat(timespec="milliseconds") + "Z",
                    "level": record.levelname.lower(),
                    "context": record.name,
                    "message": record.getMessage(),
                    "service": self.service,
                    "environment": self.environment,
                    "version": self.version,
                }}

                # Add correlation IDs if available
                if hasattr(record, "request_id"):
                    log_entry["request_id"] = record.request_id
                if hasattr(record, "trace_id"):
                    log_entry["trace_id"] = record.trace_id

                # Add error info for exceptions
                if record.exc_info:
                    log_entry["error"] = {{
                        "type": record.exc_info[0].__name__ if record.exc_info[0] else None,
                        "message": str(record.exc_info[1]) if record.exc_info[1] else None,
                    }}

                return json.dumps(log_entry, separators=(",", ":"), default=str)

        class CorrelationIdFilter(logging.Filter):
            """Adds correlation IDs to log records."""

            def __init__(self):
                super().__init__()
                self._request_id: Optional[str] = None

            def set_request_id(self, request_id: Optional[str] = None) -> str:
                self._request_id = request_id or str(uuid.uuid4())
                return self._request_id

            def get_request_id(self) -> Optional[str]:
                return self._request_id

            def filter(self, record: logging.LogRecord) -> bool:
                if self._request_id:
                    record.request_id = self._request_id
                    record.trace_id = self._request_id
                else:
                    record.request_id = str(uuid.uuid4())
                    record.trace_id = record.request_id
                return True

        class LoggerFactory:
            """Factory for creating configured loggers."""

            @staticmethod
            def get_environment() -> str:
                env = (os.getenv("APP_ENV", "") or os.getenv("ENV", "")).lower()
                if env in ("prod", "production"):
                    return "production"
                elif env in ("sandbox", "staging", "stage", "preprod", "pre-prod"):
                    return "sandbox"
                return "development"

            @staticmethod
            def read_version(project_root: Optional[Path] = None) -> str:
                if project_root is None:
                    project_root = Path.cwd()
                version_path = project_root / ".version"
                try:
                    if version_path.exists():
                        return version_path.read_text(encoding="utf-8").strip()
                except Exception:
                    return "unknown"
                return "development"

            @staticmethod
            def get_log_dir(project_root: Optional[Path] = None) -> Path:
                """Get log dir: outputs/logs/{{environment}}/{{YYYY-MM-DD}}/"""
                if project_root is None:
                    project_root = Path.cwd()

                env = LoggerFactory.get_environment()
                today = datetime.now().strftime("%Y-%m-%d")

                log_dir = project_root / "outputs" / "logs" / env / today
                log_dir.mkdir(parents=True, exist_ok=True)

                return log_dir

            @staticmethod
            def create_logger(
                name: str,
                service: str = "app",
                version: Optional[str] = None,
                project_root: Optional[Path] = None,
                log_level: Optional[str] = None
            ) -> logging.Logger:
                """Create and configure a logger."""
                logger = logging.getLogger(name)

                if logger.handlers:
                    return logger

                env = LoggerFactory.get_environment()
                if log_level:
                    level = getattr(logging, log_level.upper(), logging.INFO)
                elif env == "production":
                    level = logging.INFO
                else:
                    level = logging.DEBUG

                logger.setLevel(level)

                # Add correlation filter
                correlation_filter = CorrelationIdFilter()
                logger.addFilter(correlation_filter)

                # Create formatter
                resolved_version = version or LoggerFactory.read_version(project_root)
                formatter = JSONLogFormatter(service=service, environment=env, version=resolved_version)

                # Console handler
                console_handler = logging.StreamHandler(sys.stdout)
                console_handler.setLevel(level)
                console_handler.setFormatter(formatter)
                logger.addHandler(console_handler)

                # File handlers
                log_dir = LoggerFactory.get_log_dir(project_root)
                log_files = {{"application": level, "error": logging.ERROR}}

                for log_type, file_level in log_files.items():
                    log_file = log_dir / f"{{log_type}}.log"
                    file_handler = logging.FileHandler(log_file, encoding="utf-8")
                    file_handler.setLevel(file_level)
                    file_handler.setFormatter(formatter)
                    logger.addHandler(file_handler)

                return logger

        def set_request_id(logger: logging.Logger, request_id: Optional[str] = None) -> str:
            """Set request ID for correlation."""
            for filter_obj in logger.filters:
                if isinstance(filter_obj, CorrelationIdFilter):
                    return filter_obj.set_request_id(request_id)
            return str(uuid.uuid4())

        def get_logger(name: str, project_root: Optional[Path] = None, log_level: Optional[str] = None) -> logging.Logger:
            """Get a configured logger (convenience function)."""
            return LoggerFactory.create_logger(name=name, project_root=project_root, log_level=log_level)
    ''').lstrip()

def author_file(author: str, email: str) -> str:
    """Generate .author metadata file content per modular-core-standard.md §3."""
    return textwrap.dedent(f"""\
        name: {author}
        email: {email}
        role: owner
    """)

def ai_ignore() -> str:
    """Generate .aiignore content per modular-core-standard.md §3."""
    return textwrap.dedent("""\
        # .aiignore — AI agent ignore patterns
        # Files and directories listed here are excluded from AI analysis.
        vendor/
        node_modules/
        __pycache__/
        .git/
        .svn/
        outputs/
        storage/
        releases/
        datasets/
        *.pyc
        *.pyo
        .env
    """)

def copy_boilerplate(boilerplate_path: Path, target_path: Path, progress_callback=None) -> bool:
    """Copy boilerplate files to target directory."""
    if not boilerplate_path.exists():
        logger.error(f"Boilerplate path {{boilerplate_path}} does not exist")
        return False

    try:
        # Copy all files and directories
        for item in boilerplate_path.rglob('*'):
            if progress_callback:
                progress_callback(f"Copying: {{item.name}}")

            rel_path = item.relative_to(boilerplate_path)
            target_item = target_path / rel_path

            if item.is_dir():
                target_item.mkdir(parents=True, exist_ok=True)
            else:
                shutil.copy2(item, target_item)

        return True
    except Exception as e:
        logger.error(f"Error copying boilerplate: {{e}}")
        return False
