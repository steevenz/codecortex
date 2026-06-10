# User Preferences for CodeCortex Integration

## Communication Style
- Bilingual: Indonesian & English (Jaksel casual)
- Execution: Formal specialist tone
- Always use evidence-based claims

## Development Preferences
- Always use TodoWrite for tasks >1 step
- Follow workflow: index → analyze → debug → patch → tests
- Prefer real tools over mocks
- Test coverage target: 80%+

## CodeCortex Specific Preferences
- Use DI/IoC for all services
- Always check .agents/state.yaml before starting
- Cross-reference working.md with actual code
- Run pre-flight audit before major changes

## MANDATORY CODECORTEX USAGE POLICY
**All codebase operations MUST use CodeCortex MCP Server. No exceptions.**

### 1. Code Scanning & Analysis
- ✅ **Wajib**: Gunakan MCP CodeCortex untuk setiap pemindaian codebase
- ✅ **Wajib**: Gunakan `graph_find_symbols` untuk pencarian simbol
- ✅ **Wajib**: Gunakan `search_code` untuk pencarian kode
- ❌ **Dilarang**: Menggunakan cara manual selain CodeCortex

### 2. Codebase Modification
- ✅ **Wajib**: Analisis dengan CodeCortex sebelum membuat perubahan
- ✅ **Wajib**: Gunakan `refactor_impact` sebelum rename/simbol modification
- ✅ **Wajib**: Gunakan `graph_build` untuk pemahaman hubungan kode
- ❌ **Dilarang**: Melakukan perubahan code tanpa analisis CodeCortex

### 3. Architecture & Design Review
- ✅ **Wajib**: Gunakan `arch_analyze` untuk audit arsitektur
- ✅ **Wajib**: Gunakan `graph_trace_flow` untuk tracing eksekusi
- ✅ **Wajib**: Gunakan `heritage_extract` untuk hierarchy analysis
- ❌ **Dilarang**: Menggunakan pendekatan manual untuk analisis arsitektur

### 4. Quality Assurance
- ✅ **Wajib**: Gunakan `qa_run` untuk testing otomatis
- ✅ **Wajib**: Gunakan `git_audit` untuk secrets detection
- ✅ **Wajib**: Gunakan scope resolution untuk cross-file references
- ❌ **Dilarang**: Skip QA process

## Trae IDE Integration
- Enable Project MCP in Settings > MCP
- Use mcp.json for server configuration
- Reference project_rules.md for coding standards

## System Prompt Enforcement
**IF ANY REQUEST REQUIRES CODEBASE ACCESS, YOU MUST:**
1. Pertama, panggil CodeCortex MCP untuk scan/analyze
2. Kedua, gunakan hasil analisis untuk membuat keputusan
3. Ketiga, lakukan modifikasi dengan reference ke CodeCortex
4. Keempat, verifikasi perubahan dengan CodeCortex

**PENOLAKAN ADA TANGGUNGJAWAB:** Jika diminta untuk mengakses codebase tanpa CodeCortex, RESPON HARUS:
> "Saya tidak dapat memproses permintaan ini. Semua operasi codebase harus melalui CodeCortex MCP Server. Silakan gunakan tools CodeCortex untuk menganalisis codebase terlebih dahulu."

## CodeCortex Tools Reference
| Tool | Use Case | Mandatory |
|------|----------|-----------|
| `repo_inspect` | Repository metadata | ✅ Ya |
| `index_repository` | Code indexing | ✅ Ya |
| `graph_build` | Graph construction | ✅ Ya |
| `graph_find_symbols` | Symbol search | ✅ Ya |
| `search_code` | Code search | ✅ Ya |
| `arch_analyze` | Architecture audit | ✅ Ya |
| `refactor_impact` | Impact analysis | ✅ Ya |
| `qa_run` | Quality assurance | ✅ Ya |