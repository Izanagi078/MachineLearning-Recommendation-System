# Contributing Guidelines

Welcome to the Movie Recommender ML project! We're glad you want to help make this recommendation engine better. Please follow these guidelines to set up your environment, write clean code, and run tests.

---

## 🛠️ Workspace Environment Setup

### 1. Backend Setup
1. **Python version**: Make sure you have Python 3.12+ installed.
2. **Virtual Environment**: Create a virtual environment inside the root directory:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows, use `.venv\Scripts\activate`
   ```
3. **Dependencies**: Install the required development packages:
   ```bash
   pip install -r backend/requirements.txt
   pip install pytest pytest-cov
   ```
4. **Environment Variables**: Copy `backend/.env.example` to `backend/.env` and adjust the variables. Never commit `.env` to git!

### 2. Frontend Setup
1. **Node.js version**: Node.js 18+ or 20+ is recommended.
2. **Install node packages**:
   ```bash
   cd frontend
   npm install
   ```
3. **Environment Variables**: Copy `frontend/.env.example` to `frontend/.env` to configure the API base URL.

---

## 🧪 Testing Guidelines

We prioritize comprehensive test coverage to ensure ML math correctness and API route stability.

### 1. Run Python Tests
You can execute all backend tests (math unit tests + integration router tests) from the project root using `pytest`:
```bash
python -m pytest backend/tests/ -v
```

### 2. Writing New Tests
- When adding a new feature or API endpoint, add a corresponding test file under `backend/tests/` (e.g. `test_featurename.py`).
- Make sure to use the `db` and `client` fixtures from `backend/tests/conftest.py` rather than creating raw SQLite connections.
- Ensure that the `TESTING` environment variable is checked/respected when writing database or initialization routines.

---

## 🌿 Git & Collaboration Workflow

We follow a structured branching and pull request workflow:

1. **Branch Naming Conventions**:
   - For bug fixes: `fix/issue-description`
   - For new features: `feature/feature-description`
   - For docs/CI updates: `chore/task-description`

2. **Commit Message Format**:
   - Keep commits atomic and descriptive.
   - Use imperative prefixes:
     - `feat: add LRU cache layer to stats endpoint`
     - `fix: resolve circular imports in router registration`
     - `test: add unit tests for online SVD matrix updates`

3. **Submitting a Pull Request**:
   - Run the test suite locally before pushing! If tests fail, the GitHub Actions CI pipeline will fail.
   - Make sure your PR contains a summary of the changes and references any issues it fixes.
