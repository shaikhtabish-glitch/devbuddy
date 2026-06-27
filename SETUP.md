# DevBuddy — Setup Guide

---

## Prerequisites

- Python 3.11 or later (`python --version`)
- Node.js 20 or later (`node --version`) — for Promptfoo evals (Week 7)
- Git
- An OpenRouter API key (check `#devbuddy-series` or contact the ops team)

---

## Step 1: Fork the Repository

```bash
# Via GitHub CLI
gh repo fork org/devbuddy --clone

# Or via GitHub UI: click Fork → then clone your fork
git clone https://github.com/YOUR_USERNAME/devbuddy.git
cd devbuddy
```

---

## Step 2: Add Upstream Remote

```bash
git remote add upstream https://github.com/org/devbuddy.git
```

Each week: `git pull upstream main` to get the latest.

---

## Step 3: Set Up Python Environment

```bash
cd python
python -m venv .venv
source .venv/bin/activate        # macOS/Linux
# .venv\Scripts\activate         # Windows

pip install -r requirements.txt
```

---

## Step 4: Configure Your API Key

```bash
cp .env.example .env
```

Edit `.env` and add your OpenRouter API key:

```
OPENROUTER_API_KEY=sk-or-your-actual-key
```

**Never commit `.env`.** It's in `.gitignore`.

---

## Step 5: Run the Verification Script

```bash
python src/verification.py
```

Expected output:

```
============================================================
  DevBuddy Verification — Week 0
============================================================

[1/3] Checking: auth-service...
  Status:      passing
  Confidence:  30%
  Reason:      I don't have real CI access...
  Tokens:      147 (102 in / 45 out)
  Cost:        $0.000042
  Time:        1.23s
  Type:        BuildCheck ← typed object, not a string!

============================================================
  ✅ VERIFICATION PASSED
============================================================
```

---

## Step 6: Post to the Channel

Copy your terminal output and post it to `#devbuddy-series` with one sentence:

> *"I want DevBuddy to help me with _____."*

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `OPENROUTER_API_KEY not set` | Did you copy `.env.example` to `.env`? Add your key? Running from `python/`? |
| `ModuleNotFoundError: langchain_openai` | `pip install -r requirements.txt` from `python/` |
| `ModuleNotFoundError: src` | You must run from `python/`: `cd python && python src/verification.py` |
| `python: command not found` | Try `python3`, or install Python 3.11+ |
| Script times out | Check network. Shared sandbox keys may be rate-limited. |
| Anything else | Post in `#devbuddy-series`. Public debugging builds shared knowledge. |
