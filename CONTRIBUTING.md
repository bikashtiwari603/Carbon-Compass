# 🤝 Contributing to CarbonCompass

Thank you for your interest in contributing to **CarbonCompass** — an AI-powered carbon footprint tracking application! We welcome contributions from the community.

**Live App:** [https://carboncompass-rlzbi2esba-uc.a.run.app/](https://carboncompass-rlzbi2esba-uc.a.run.app/)  
**GitHub:** [https://github.com/bikashtiwari603/Carbon-Compass](https://github.com/bikashtiwari603/Carbon-Compass)

---

## 📋 Table of Contents

- [Code of Conduct](#code-of-conduct)
- [How to Contribute](#how-to-contribute)
- [Development Setup](#development-setup)
- [Project Structure](#project-structure)
- [Coding Standards](#coding-standards)
- [Testing](#testing)
- [Submitting a Pull Request](#submitting-a-pull-request)
- [Reporting Issues](#reporting-issues)

---

## 🌱 Code of Conduct

Be respectful, inclusive, and constructive. We are a community united by a mission to fight climate change — all contributors are welcome regardless of background.

---

## 🛠️ How to Contribute

There are many ways to contribute:

- 🐛 **Bug fixes** — Fix issues found in the app
- ✨ **New features** — Add new activity categories, badges, tips
- 📊 **Carbon data** — Improve CO₂ emission factor accuracy
- 🌍 **Localisation** — Add support for other countries/regions
- 📝 **Documentation** — Improve README, add docstrings
- 🧪 **Tests** — Expand test coverage
- 🎨 **UI/UX** — Enhance design, accessibility, animations

---

## 💻 Development Setup

### Prerequisites

- Python 3.12+
- A [Google Gemini API key](https://aistudio.google.com/app/apikey) (free tier available)

### 1. Fork and clone the repository

```bash
git clone https://github.com/YOUR_USERNAME/Carbon-Compass.git
cd Carbon-Compass
```

### 2. Set up environment

```bash
cp .env.example .env
# Edit .env and add your GEMINI_API_KEY
pip install -r requirements.txt
```

### 3. Run the development server

```bash
uvicorn main:app --reload --port 8080
```

Open: [http://localhost:8080](http://localhost:8080)

### 4. Run the test suite

```bash
pytest -v
```

All 79 tests should pass. Please ensure tests pass before submitting a PR.

---

## 📁 Project Structure

```
Carbon-Compass/
├── main.py           # FastAPI backend — add new endpoints here
├── static/
│   └── index.html    # Single-page frontend — all CSS & JS inline
├── test_main.py      # Backend tests — add tests here
├── conftest.py       # Test fixtures
├── requirements.txt  # Python dependencies
└── Dockerfile        # Production container
```

**Key areas:**

| Area | File | What to edit |
|---|---|---|
| New API endpoint | `main.py` | Add `@app.get(...)` or `@app.post(...)` routes |
| New activity category | `main.py` | Add to `ACTIVITIES_DATA["categories"]` |
| New badge | `main.py` | Add to `BADGES_DATA` and `_check_badges()` |
| New UI section | `static/index.html` | Add HTML + CSS + JS inline |
| New quiz question | `static/index.html` | Add to `QUIZ_DATA` array |
| New eco tip | `main.py` | Add to `TIPS_DATA["daily_tips"]` |

---

## ✏️ Coding Standards

### Python (Backend)

- Follow **PEP 8** style
- Add docstrings to all new functions
- All user inputs **must** be sanitised using `sanitize_input()`
- All endpoints **must** call `_rate_limit(request, key, max_requests)`
- Keep endpoints simple — complex logic should be in helper functions
- Use type hints where possible

```python
@app.get("/api/v1/my-endpoint")
async def my_endpoint(request: Request):
    """Brief description of what this endpoint does."""
    _rate_limit(request, "my-endpoint", max_requests=60)
    # ... logic here
    return {"key": "value"}
```

### JavaScript (Frontend)

- Use `const`/`let`, never `var`
- All user-displayed text from API should be XSS-escaped
- New API calls must use the `apiFetch(path, options)` helper
- Error states must be handled gracefully with a user-facing message

### CSS

- Use CSS custom properties (`var(--accent-green)`) — never hardcode colours
- Respect `prefers-reduced-motion` for all new animations
- Ensure both dark AND light themes look good for any new UI

---

## 🧪 Testing

When adding a new feature, please add corresponding tests to `test_main.py`:

```python
class TestMyFeature:
    def test_my_endpoint_returns_200(self, client):
        res = client.get("/api/v1/my-endpoint")
        assert res.status_code == 200

    def test_my_endpoint_has_expected_fields(self, client):
        data = client.get("/api/v1/my-endpoint").json()
        assert "key" in data
```

Run tests with:
```bash
pytest -v -k "TestMyFeature"
```

---

## 🔃 Submitting a Pull Request

1. **Fork** the repository on GitHub
2. **Create a branch** with a descriptive name:
   ```bash
   git checkout -b feat/add-solar-activity
   # or
   git checkout -b fix/badge-calculation
   ```
3. **Make your changes** following the coding standards above
4. **Run the test suite** and ensure all tests pass:
   ```bash
   pytest -v
   ```
5. **Commit** with a clear, conventional commit message:
   ```bash
   git commit -m "feat: add solar panel activity to green actions category"
   ```
6. **Push** to your fork and **open a Pull Request** against `main`
7. Fill in the PR description explaining what you changed and why

### Commit Message Format

We use [Conventional Commits](https://www.conventionalcommits.org/):

| Prefix | Use for |
|---|---|
| `feat:` | New feature |
| `fix:` | Bug fix |
| `docs:` | Documentation changes |
| `test:` | Adding or fixing tests |
| `refactor:` | Code changes without feature/fix |
| `chore:` | Build, CI, dependency updates |
| `style:` | CSS/UI changes |

---

## 🐛 Reporting Issues

Found a bug or have a feature idea? Please [open an issue](https://github.com/bikashtiwari603/Carbon-Compass/issues) with:

- **Bug reports**: Steps to reproduce, expected vs actual behaviour, browser/OS info
- **Feature requests**: Describe the problem you're solving and your proposed solution
- **Carbon data corrections**: Cite your source for the corrected emission factor

---

## 📊 Carbon Data Accuracy

If you're updating CO₂ emission factors, please cite authoritative sources:

- [IPCC AR6 Report](https://www.ipcc.ch/report/ar6/wg3/)
- [IEA Electricity Grid Emission Factors](https://www.iea.org/data-and-statistics)
- [Our World in Data — CO₂ Emissions](https://ourworldindata.org/co2-emissions)
- [India MoEFCC Greenhouse Gas Inventory](https://moef.gov.in)

---

## ❓ Questions?

Open a [GitHub Discussion](https://github.com/bikashtiwari603/Carbon-Compass/discussions) or raise an issue.

---

*Together we can Navigate Towards a Greener Future 🌱*
