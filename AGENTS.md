# AGENTS.md

## 🧭 Overview
This document defines the development, testing, and pull request (PR) standards for Codex-based agents.  
All contributors must follow these conventions to maintain **clean, consistent, and testable** code.

---

## ⚙️ Development Environment

### Toolchain
- **Node:** Use the latest LTS version.  
- **Python:** Use ≥3.11 for scripts or testing helpers.  
- **Package Manager:** `pnpm` (preferred)  
- **Linters & Formatters:**  
  - **Ruff** – for linting and code quality checks.  
  - **Black** – for code formatting.  
- **Tests:**  
  - **Unit tests:** Required for all new features or changes.  
  - **Integration tests:** Required for interactions with external services (APIs, MQTT, etc.).  
  - **Contract tests:** Recommended for validating message formats or schemas.

---

### Dev Shortcuts

| Action | Command |
|--------|----------|
| Jump to a workspace package | `pnpm dlx turbo run where <project_name>` |
| Add a package to workspace | `pnpm install --filter <project_name>` |
| Create new React+Vite+TS project | `pnpm create vite@latest <project_name> -- --template react-ts` |
| Confirm correct package name | Check `"name"` field in `<package_name>/package.json` (not root) |

---

## 🧪 Testing Instructions

### Running Tests
- **All checks for one package:**
  ```bash
  pnpm turbo run test --filter <project_name>
  ```
- **From package root:**
  ```bash
  pnpm test
  ```
- **Target a specific test:**
  ```bash
  pnpm vitest run -t "<test name>"
  ```

### Requirements
- All PRs **must** pass:
  - **Linting:** `pnpm lint --filter <project_name>`
  - **Type checks:** via TypeScript or `mypy` (if Python is present)
  - **Unit tests:** green before merge
- **No merge** is allowed with red tests, lint errors, or type violations.

### Test Design Principles
- Use the **AAA pattern** (Arrange–Act–Assert).  
- Mock or fake external calls—**never** rely on live network data.  
- Keep test data **isolated** and **repeatable**.  
- Follow coverage target: **≥80%** of changed lines.  
- Integration tests should confirm system boundaries work (e.g., MQTT, REST, SCADA).  
- Contract tests must verify message payloads conform to the agreed schema.

---

## 🧹 Code Style & Quality Standards

### Python Code (if applicable)
Follow:
- **PEP 8** – Style guide
- **PEP 20** – Zen of Python
- **PEP 257** – Docstring conventions
- Type hints for all public functions
- `dataclasses` or `attrs` for structured data
- `pathlib`, `logging`, and `contextlib` over legacy alternatives
- Explicit error handling; no silent exceptions

### Formatting & Linting
Run before each commit:
```bash
ruff check . --fix
black .
```

Recommended `pyproject.toml`:
```toml
[tool.black]
line-length = 120
target-version = ["py311"]

[tool.ruff]
line-length = 120
select = ["E", "F", "I", "B", "UP", "SIM", "PL", "RUF"]
ignore = ["E203"]
fix = true
```

---

## 🧩 Pull Request Guidelines

### PR Title Format
```
[<project_name>] <short concise title>
```

### PR Checklist
Before opening or merging a PR:
- [ ] Code formatted with **Black**
- [ ] Lint passes (Ruff/ESLint)
- [ ] Tests pass (`pnpm test`)
- [ ] Unit tests added for all new logic
- [ ] Integration/contract tests added if applicable
- [ ] Type checks clean (TypeScript or mypy)
- [ ] README or inline docs updated if behaviour changes
- [ ] No console.log or print debugging left in production code

### Example CI flow
1. `pnpm lint`
2. `pnpm test`
3. (Optional) `pnpm build`
4. PR merge only after all checks succeed.

---

## 📄 Best Practices Summary
- **Keep functions small, pure, and explicit.**  
- **Fail fast:** raise clear exceptions early.  
- **Document all public functions.**  
- **Avoid magic numbers:** use constants or enums.  
- **Use logging instead of prints.**  
- **Secure secrets:** never hardcode credentials.  
- **Include examples** for any public API or library integration.

---

### TL;DR (pt-PT)
As novas instruções garantem código limpo e padronizado: segue PEP8/20/257, usa **Ruff** e **Black**, e obriga a **testes unitários**. Testes de integração e contrato são recomendados.  
Antes de fazer merge, certifica-te que `lint`, `test` e `type checks` passam, e que todo o código está documentado e formatado.
