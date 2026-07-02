# DevBuddy — Setup Guide

Choose your language and follow the steps below.

---

## Prerequisites

- **Python 3.11+** (`python --version`) — for the Python blueprint
- **Node.js 20+** (`node --version`) — for the Node.js blueprint + Promptfoo evals
- **Git**
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

## Choose Your Language

### Python

Full guide: [`python/README.md`](python/README.md) — or continue below.

```bash
cd python
python -m venv .venv
source .venv/bin/activate        # macOS/Linux
# .venv\Scripts\activate         # Windows

pip install -r requirements.txt
cp .env.example .env
# Edit .env → add your OPENROUTER_API_KEY

python src/verification.py       # verify your environment
python tests/test_integration.py  # run the integration test suite
```

### Node.js

Full guide: [`nodejs/SETUP.md`](nodejs/SETUP.md) — or continue below.

```bash
cd nodejs
npm install
cp .env.example .env
# Edit .env → add your OPENROUTER_API_KEY

node src/verification.js   # verify your environment
npm test                    # run the integration test suite
```

---

## Step 3: Configure Your API Key

Edit `.env` in your language directory and add your OpenRouter API key:

```
OPENROUTER_API_KEY=sk-or-your-actual-key
DEVBUDDY_MODEL=openai/gpt-4o-mini
```

Change `DEVBUDDY_MODEL` to any OpenRouter model string (`anthropic/claude-sonnet`, `google/gemini-2.5-flash-lite`, etc.).

**Never commit `.env`.** It's in `.gitignore`.

---

## Step 4: Post to the Channel

Copy your terminal output and post it to `#devbuddy-series` with one sentence:

> *"I want DevBuddy to help me with _____."*

---

## Step 5: Verify Promptfoo (Optional)

Promptfoo runs evals against your LLM outputs — multi-model comparison, assertions, latency, cost.

```bash
cd shared/evals
export OPENROUTER_API_KEY=sk-or-your-key
npx promptfoo@latest eval --config week-00-smoke.yaml
```

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `OPENROUTER_API_KEY not set` | Did you copy `.env.example` to `.env`? Add your key? Running from the right directory? |
| `ModuleNotFoundError: langchain_openai` | `pip install -r requirements.txt` from `python/` |
| `ERR_MODULE_NOT_FOUND: @langchain/openai` | `npm install` from `nodejs/` |
| `ModuleNotFoundError: src` | You must run from `python/`: `cd python && python src/verification.py` |
| `Error: Cannot find module './llm.js'` | You must run from `nodejs/`: `cd nodejs && node src/verification.js` |
| `python: command not found` | Try `python3`, or install Python 3.11+ |
| `node: command not found` | Install Node.js 20+ from [nodejs.org](https://nodejs.org) or `nvm` |
| Script times out | Check network. Shared sandbox keys may be rate-limited. |
| Anything else | Post in `#devbuddy-series`. Public debugging builds shared knowledge. |
