Contributing to Meridian 🚀
Thank you for your interest in contributing! Meridian is built on top of the
open-source [DeepTutor](https://github.com/HKUDS/DeepTutor) engine (HKUDS,
Apache 2.0) — see [ATTRIBUTION.md](./ATTRIBUTION.md) for what is inherited
versus original. We welcome developers of all skill levels to help build the
`meridian/` layer (auth, tenancy, learner intelligence, curriculum,
evaluation, observability).

For questions about the underlying tutoring engine itself (not the
Meridian-specific layer), the upstream DeepTutor community channels are the
better fit — see [Communication.md](./Communication.md).

## Table of Contents
- [Contribution Requirements](#️-contribution-requirements)
- [Code Quality & Security](#-code-quality--security)
- [Security Best Practices](#-security-best-practices)
- [Coding Standards](#-coding-standards)
- [Development Setup](#-development-setup)
- [Commit Message Format](#-commit-message-format)
- [How to Get Started](#-how-to-get-started)

## ⚠️ Contribution Requirements
[!IMPORTANT]
All contributions must be based on the `dev` branch!
1. Fork the repository and clone it locally.
2. **Synchronize**: Always pull from the `dev` branch before starting:
   ```bash
   git checkout dev && git pull origin dev
   ```
3. **Branch**: Create your feature branch from `dev`:
   ```bash
   git checkout -b feature/your-feature-name
   ```
4. **PR Target**: Submit your Pull Request to the `dev` branch (not `main`).
5. **Validation**: Ensure all pre-commit checks pass before submitting.

## 🛠️ Code Quality & Security
We use a suite of automated tools to maintain high standards of code quality and security. These are configured via `pyproject.toml` and `.pre-commit-config.yaml`.

### Our Toolstack
- **Ruff**: High-performance Python linting and formatting.
- **Prettier**: Consistent formatting for frontend and configuration files.
- **detect-secrets**: Scans for high-entropy strings and hardcoded secrets.
- **pip-audit**: Scans dependencies for known vulnerabilities (V3.x compatible).
- **Bandit**: Analyzes code for common security issues.
- **MyPy**: Static type checking to ensure code reliability.
- **Interrogate**: Reports docstring coverage. While it won't block your commit, please aim for high coverage.

[!TIP]
Before submitting a PR, you MUST run:
```bash
pre-commit run --all-files
```
While local pre-commit hooks are configured to be lenient and may only show warnings, the CI will perform strict checks and will automatically reject PRs that fail.

## 🔒 Security Best Practices
### File Uploads
- **Size Limits**: General files are capped at 100MB; PDFs are capped at 50MB to prevent resource exhaustion.
- **Validation**: We enforce multi-layer validation (Extension + MIME type + Content sanitization).
- **Sanitization**: All filenames are sanitized to prevent path traversal attacks.

### Development Standards
- **Subprocesses**: Always use `shell=False` when calling subprocesses to prevent command injection.
- **Pathing**: Use `pathlib.Path` for all operations to ensure cross-platform (Windows/Linux/macOS) compatibility.
- **Line Endings**: LF (Unix) line endings are enforced for critical scripts via `.gitattributes`.

## 💻 Coding Standards
To keep the codebase maintainable, please follow these guidelines:
### Python Guidelines
- Use Type Hints for all function signatures.
- Prefer f-strings for string formatting.
- Follow PEP 8 (mostly enforced by Ruff/Black).
- Keep functions small and focused on a single responsibility.

### Documentation
- Every new module, class, and public function should have a docstring.
- Use the Google Python Style Guide for docstring formatting.
- Update `README.md` if your change introduces new features or configuration variables.

## ⚙️ Development Setup
<details>
<summary><b>Setting Up Your Environment (Recommended)</b></summary>

**Step 1: Create a virtual environment**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

**Step 2: Install dependencies**
```bash
pip install -e ".[all]"
```
</details>

<details>
<summary><b>Setting Up Pre-commit (First Time Only)</b></summary>

**Step 1: Install pre-commit**
```bash
# Using pip
pip install pre-commit

# Or using conda
conda install -c conda-forge pre-commit
```

**Step 2: Install Git hooks**
```bash
pre-commit install
```
Hooks will now run automatically on every commit.

**Step 3: Initialize the Secrets Baseline**
If you encounter new "false positive" secrets (like API hash placeholders), update the baseline:
```bash
detect-secrets scan > .secrets.baseline
```
</details>

### Common Commands
| Task              | Command                                        |
|-------------------|------------------------------------------------|
| Check all files   | `pre-commit run --all-files`                   |
| Check quietly     | `pre-commit run --all-files -q`                |
| Update tools      | `pre-commit autoupdate`                        |
| Emergency skip    | `git commit --no-verify -m "message"` (Not recommended) |

## 📋 Commit Message Format
We follow a structured commit format to maintain a clean history:
```
<type>: <short description>

[optional body]
```
- `feat`: A new feature (corresponds to a MINOR version bump).
- `fix`: A bug fix (corresponds to a PATCH version bump).
- `docs`: Documentation only changes.
- `style`: Changes that do not affect the meaning of the code (formatting, missing semi-colons, etc).
- `refactor`: A code change that neither fixes a bug nor adds a feature.
- `test`: Adding missing tests or correcting existing tests.
- `chore`: Routine tasks (updating build processes, etc).

## 💡 How to Get Started
1. Browse this repository's [Issues](https://github.com/dhruvshah464/DeepTutor/issues) for tasks labeled `good first issue`.
2. Comment on the issue to let others know you're working on it.
3. Follow the process above and submit your PR!

For issues in the inherited tutoring engine itself, check whether they're
already tracked upstream at https://github.com/HKUDS/DeepTutor/issues.
