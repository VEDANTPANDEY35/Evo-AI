<div align="center">

# Evo-AI

**A local-first AI computing interface with deterministic execution and workflow-aware desktop control.**

[![Version](https://img.shields.io/badge/version-2.3.0-7C6AF7?style=flat-square)](https://github.com/VEDANTPANDEY35/Evo-AI)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue?style=flat-square)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey?style=flat-square)](https://github.com/VEDANTPANDEY35/Evo-AI)
[![License](https://img.shields.io/badge/license-MIT-green?style=flat-square)](https://github.com/VEDANTPANDEY35/Evo-AI/blob/main/LICENSE)
[![Ollama](https://img.shields.io/badge/LLM-Ollama%20%2F%20llama3.2-orange?style=flat-square)](https://ollama.ai)

*Plan. Approve. Execute. Every action is shown to you before it runs — no autonomous behavior, no surprises.*

</div>

---

## What is Evo-AI?


Evo-AI is a deterministic AI computing interface that connects a local LLM to real desktop capabilities — opening apps, searching the web, managing files, and executing workflows safely through explicit user approval.


The key difference from a chatbot: **Evo-AI plans before it acts, shows you the plan, and only executes after you approve.** Every action goes through five independent safety layers. Nothing runs autonomously.


### How it looks

> Demo GIF coming soon — overlay interaction, workflow execution, and debugger suggestions.


```
You: open chrome and search spotify

  📋 Execution Plan
  Steps: 2  |  Risk: MEDIUM  |  Confidence: 90%
  1. Opening Chrome
  2. Searching Spotify

  Execute this plan? (y/n): y

  ✓ Opened Chrome
  ✓ Searching for 'spotify' on google in Chrome
```

### Core ideas

| Principle | What it means in practice |
|---|---|
| **Deterministic execution** | 80% of commands never touch the LLM — routing is rule-based and predictable |
| **Human approval before action** | `generate_plan()` and `execute_plan()` are always separate — you see the plan first |
| **Workflow-aware context** | Multi-step commands share state — `open chrome and search spotify` searches *inside* Chrome |
| **Local-first AI** | Runs entirely on your machine via Ollama; no data leaves without explicit opt-in |
| **Search-driven app resolution** | Finds installed apps by searching the actual filesystem, not a hardcoded list |

---

## Screenshots

> *Screenshots and GIFs will be added here. Run the overlay to see it live.*

**Overlay — Idle state**
<!-- ![Overlay idle](docs/screenshots/overlay-idle.png) -->
`Ctrl+Space` → floating command bar appears with breathing dots

**Overlay — Thinking state**
<!-- ![Overlay thinking](docs/screenshots/overlay-thinking.png) -->
Dots orbit while `Brain.generate_plan()` runs in a background thread

**Overlay — Plan approval**
<!-- ![Overlay approval](docs/screenshots/overlay-approval.png) -->
Structured plan card expands with numbered steps and Execute / Cancel buttons

**Overlay — Debugger suggestions**
<!-- ![Overlay debugger](docs/screenshots/overlay-debugger.png) -->
Arrow-key-navigable suggestion list when an app isn't found locally

---

## Table of Contents

- [What is Evo-AI?](#what-is-evo-ai)
- [Screenshots](#screenshots)
- [Features](#features)
- [Why Deterministic?](#why-deterministic)
- [Quick Start](#quick-start)
- [Interfaces](#interfaces)
  - [CLI](#cli-terminal-interface)
  - [Overlay (GUI)](#overlay-gui)
  - [Voice](#voice-interface)
- [How It Works](#how-it-works)
  - [Architecture Overview](#architecture-overview)
  - [Intelligence Pipeline](#intelligence-pipeline)
  - [Resolution Pipeline](#resolution-pipeline)
  - [Parameter Extraction](#parameter-extraction)
  - [Execution Context](#execution-context)
  - [Safety Layers](#safety-layers)
- [All 17 Tools](#all-17-tools)
- [Command Reference](#command-reference)
- [Configuration](#configuration)
- [Project Structure](#project-structure)
- [Requirements](#requirements)
- [Resource Usage](#resource-usage)
- [Limitations](#limitations)
- [Architecture](#architecture)

---

## Features

### Privacy & Offline
- Runs entirely on your machine — no data sent to any cloud service
- Works without internet using Ollama (local LLM)
- Optional online API fallback (OpenAI-compatible, opt-in only)

### System Control
- Open any installed application by name, typo-tolerant
- Search the web in a specific browser
- File operations: list, read, write, create, search, delete
- Process management: list and kill running processes
- Screenshots, clipboard read/write, network info

### Intelligent Input Processing
- Typo correction: `opne chorme` → `open chrome`
- Alias expansion: `open my browser` → `open chrome`
- Semantic mapping: `open something for music` → `open spotify`
- Compound commands: `open chrome and search spotify then take a screenshot`
- Structured parameter extraction: `find all python files in Documents` → `{pattern: "*.py", directory: "~/Documents"}`

### Safety by Design
- Plan preview before every execution — you approve or cancel
- Five independent safety layers (schema validation → path safety → permissions → audit log → post-execution verification)
- Permission system with once/always/deny options, full audit trail
- Protected directories and dangerous command detection

### Modern Overlay UI
- Borderless floating command bar (`Ctrl+Space`)
- Animated interaction dots (idle → listening → thinking → ready)
- Structured plan card with human-readable step labels
- Debugger suggestion UI with arrow-key navigation
- Smooth fade-in/fade-out transitions (~216ms)

---

## Why Deterministic?

Most AI assistants route every request through a language model and execute whatever it decides. Evo-AI takes a different approach.

**The problem with unrestricted autonomous execution:**
- LLM outputs are probabilistic — the same input can produce different actions
- Errors compound silently across multi-step workflows
- There is no natural point for the user to review or intervene
- Audit trails are difficult to reconstruct after the fact

**How Evo-AI is different:**

The system separates reasoning, planning, and execution into distinct, inspectable stages. The LLM is used only for open-ended conversation — every actionable command is handled by a deterministic rule-based pipeline that produces the same output for the same input, every time.

```
Input → Normalizer → Resolver → Parameter Extractor → Planner
                                                          ↓
                                              StructuredPlan (data only)
                                                          ↓
                                              User reviews and approves
                                                          ↓
                                              Executor → Verifier → Result
```

The plan is a pure data structure — no side effects, no execution. The user sees exactly what will happen before anything runs. This makes the system:

- **Explainable** — every decision traces back to a specific rule
- **Predictable** — identical inputs produce identical plans
- **Auditable** — every permission request is logged to `config/permission_audit.jsonl`
- **Safe by default** — five independent safety layers, each catching different failure modes

The LLM is a collaborator for conversation, not an autonomous agent for execution.

---

## Quick Start

### 1. Install Ollama

```bash
# Download from https://ollama.ai, then:
ollama serve
ollama pull llama3.2:latest
```

### 2. Clone and install

```bash
git clone https://github.com/VEDANTPANDEY35/Evo-AI.git
cd Evo-AI
pip install -r requirements.txt
```

### 3. Run

```bash
# Terminal interface
python cli/cli.py

# Modern overlay (GUI)
cd os_overlay
python main.py
```

### 4. Try it

```
open youtube
open chrome and search for AI tutorials
find all python files in Documents
system info
running processes
take a screenshot
tell me about yourself
```

---

## Interfaces

### CLI (Terminal Interface)

`cli/cli.py` — Rich-powered terminal UI with colors, spinners, and streaming output.

**Start:**
```bash
python cli/cli.py
python cli/cli.py --debug    # verbose logging
```

**Built-in commands:**

| Command | Description |
|---|---|
| `help` | Show all commands and examples |
| `status` | LLM connection, session ID, message count |
| `history` | Last 10 executed actions |
| `clear` | Clear conversation history |
| `save` | Save session to `logs/session_YYYYMMDD_HHMMSS.txt` |
| `exit` / `quit` | Exit and save session |

**Interaction flow:**
1. You type a command
2. Evo-AI analyzes it and shows a plan preview (steps, risk level, confidence)
3. You confirm with `y` or cancel with `n`
4. Result streams to the terminal

**API wrapper** — `run_ai(user_input: str) → str` in `cli.py` provides a non-interactive programmatic interface with no confirmation prompts.

---

### Overlay (GUI)

`os_overlay/` — Modern floating command bar inspired by Raycast and Spotlight.

**Start:**
```bash
cd os_overlay
python main.py
```

**Hotkey:** `Ctrl+Space` — toggles the overlay from anywhere on your desktop.

**UI States:**

| State | Dots | Microcopy |
|---|---|---|
| Idle | Breathing cluster | *(empty)* |
| Listening | Pulse outward | Listening… |
| Thinking | Orbital motion | Working on it… |
| Approval | Stabilised violet | Ready to execute |
| Executing | Stabilised amber | Running… |
| Success | Stabilised green | Done |
| Debugger | Stabilised amber | I found a few possibilities |
| Error | Stabilised red | Something went wrong |

**Keyboard navigation:**

| Key | Action |
|---|---|
| `Ctrl+Space` | Open / focus overlay |
| `Enter` | Submit command / confirm suggestion |
| `↑` / `↓` | Navigate debugger suggestions |
| `Escape` | Close overlay |

**Plan card** — when a plan is ready, the overlay expands to show numbered step rows with human-readable labels (`Opening Chrome`, `Searching Spotify`) and Execute / Cancel buttons.

**Debugger card** — when an app isn't found, shows selectable suggestions. Selecting one builds a plan card — you still press Execute. Nothing auto-runs.

**Window:** 560px wide, borderless, draggable, always-on-top. Positioned at 32% from top (Spotlight feel). Fades in/out over ~216ms.

---

### Voice Interface

`interfaces/voice/` — Speech recognition + TTS.

```bash
pip install -r interfaces/voice/requirements.txt
python interfaces/voice/voice_assistant.py        # full (requires PyAudio)
python interfaces/voice/voice_assistant_simple.py # Windows-only, no PyAudio
```

- Speech recognition: offline Sphinx first, Google fallback
- TTS: pyttsx3, female voice preference, 175 WPM
- Wires into `Brain.process()` — same pipeline as CLI

---

## How It Works

### Architecture Overview

```
User Input
    │
    ▼
┌─────────────────────────────────────────────────────────┐
│  Interface Layer                                        │
│  CLI (cli.py) │ Overlay (os_overlay/) │ Voice           │
└────────────────────────┬────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│  Brain  (core/brain.py)  — pure logic, zero I/O         │
│                                                         │
│  generate_plan(text) → StructuredPlan                   │
│  execute_plan(plan)  → ExecutionResult                  │
└──────────┬──────────────────────────┬───────────────────┘
           │ compound?                │ single?
           ▼                          ▼
    ┌─────────────┐           ┌──────────────┐
    │   Planner   │           │   Reasoner   │
    │ (planner.py)│           │(reasoning.py)│
    └──────┬──────┘           └──────┬───────┘
           │                         │
           │              ┌──────────▼──────────┐
           │              │  Input Normalizer    │
           │              │  Target Resolver     │
           │              │  Parameter Extractor │
           │              │  Debugger (if low    │
           │              │  confidence)         │
           │              └──────────┬───────────┘
           │                         │
           └─────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│  Execution Flow                                         │
│                                                         │
│  Verifier.pre_check()                                   │
│       ↓                                                 │
│  Executor.execute_action()                              │
│    → ToolRegistry (schema validation)                   │
│    → SafetyValidator (path / command safety)            │
│    → PermissionManager (user approval + audit)          │
│    → SystemTools → OSAdapter → actual OS call           │
│       ↓                                                 │
│  Verifier.post_check()                                  │
└─────────────────────────────────────────────────────────┘
                         │
                         ▼
                    ExecutionResult
```

**Key design principle:** `Brain` has zero I/O — no `print()`, no `input()`. All interfaces are pure wrappers. `generate_plan()` and `execute_plan()` are intentionally separate so the interface can show the plan and ask for confirmation before anything runs.

---

### Intelligence Pipeline

Evo-AI uses a **3-tier hybrid routing system** that avoids LLM calls for 80% of requests:

**Tier 1 — Instant pattern matching (<1ms)**
Handles: greetings, system info queries, process queries, open/launch commands, screenshots.
No LLM involved. Deterministic routing.

**Tier 2 — Resolution pipeline (<10ms)**
For open/launch commands: normalizer → resolver → parameter extractor → planner.
Finds the actual app on disk or resolves to a known URL. Still no LLM.

**Tier 3 — LLM conversation (2–10s)**
Only for genuine open-ended questions that don't match any tool.
Uses Ollama locally with conversation history (last 4 turns).

**Priority routing order inside `Reasoner.analyze_request()`:**

| Priority | Trigger | Action |
|---|---|---|
| 1 | CPU / RAM / disk / memory keywords | Lock to `get_system_info` or `list_processes` |
| 2 | "running processes", "what's running" | `list_processes` |
| 3 | "my system", "computer specs" | `get_system_info` |
| 4 | `open` / `launch` / `start` commands | Resolution pipeline |
| 5 | Screenshots, greetings, thanks | Quick pattern match |
| 6 | Everything else | `handle_general_query()` (deterministic fallback) |

---

### Resolution Pipeline

When you say `open <something>`, the target goes through a 4-step pipeline:

```
"open spotfy"
    │
    ▼ InputNormalizer
"open spotify"   ← typo fixed, aliases expanded, semantic mapping applied
    │
    ▼ TargetResolver
Step 1: Known websites (≤10 entries)
        spotify → https://open.spotify.com  ✓ confidence=high
        ─────────────────────────────────────────────────────
Step 2: Everything CLI (es.exe) — searches actual filesystem for <target>.exe
        Ranks: exact name (3) > prefix (2) > contains (1)
        ─────────────────────────────────────────────────────
Step 3: Known-apps fallback (~45 entries, only if Everything unavailable)
        ─────────────────────────────────────────────────────
Step 4: Web search fallback — explicit, never silent
        Returns fallback_info → Debugger activates
    │
    ▼ Debugger (only on low confidence)
        Fuzzy-matches against known apps/sites
        Returns DebugReport with selectable suggestions
        NO execution — user chooses
```

**Normalizer corrections:**

| Input | Output |
|---|---|
| `opne chorme` | `open chrome` |
| `open spotfy` | `open spotify` |
| `open my browser` | `open chrome` |
| `open something for music` | `open spotify` |
| `open something for coding` | `open vscode` |

---

### Parameter Extraction

`core/extraction/parameter_extractor.py` — runs after intent resolution, before the planner. Fills in missing structured parameters from natural language.

**File search:**
```
"find all python files in Documents"
  → pattern="*.py", directory="C:/Users/you/Documents"

"search images on Desktop"
  → pattern="*.{png,jpg,jpeg,gif,bmp,webp,svg}", directory="C:/Users/you/Desktop"
```

**Supported file types (50+ entries):**
`python`, `pdf`, `word`, `excel`, `image`, `video`, `audio`, `zip`, `json`, `markdown`, `jupyter`, and more.

**Supported directories:**
`Documents`, `Downloads`, `Desktop`, `Pictures`, `Videos`, `Music`

**Web search:**
```
"search for spotify"        → query="spotify"
"google machine learning"   → query="machine learning", engine="google"
```

**Process:**
```
"kill chrome"   → name="chrome"
"stop notepad"  → name="notepad"
```

---

### Execution Context

`core/context/execution_context.py` — ephemeral workflow context that lives only for the duration of one multi-step command.

**Problem it solves:** `open chrome and search spotify` used to open Chrome correctly but then open the Spotify search in the system-default browser instead of Chrome.

**How it works:**
```
"open chrome and search spotify"

Step 1: open_application("chrome")
    → ExecutionContext.set_active_browser("chrome")

Step 2: search_web(query="spotify")
    → Brain injects: params["browser"] = "chrome"
    → Search opens in Chrome  ✓
```

Rules:
- Created fresh per `execute_plan()` call — discarded when it returns
- No persistence, no global state, no autonomous tracking
- Context is explicitly passed, never imported as a singleton

---

### Safety Layers

Five independent layers, each catching different failure modes:

| Layer | File | What it checks |
|---|---|---|
| 1. Schema validation | `tool_registry.py` | Required params, types, allowed values |
| 2. Path safety | `safety_validator.py` | Protected dirs, path traversal, dangerous commands |
| 3. Permission management | `permission_manager.py` | User approval (once/always/deny), audit log |
| 4. Audit logging | `config/permission_audit.jsonl` | Append-only record of every permission request |
| 5. Execution verification | `verifier.py` | Post-execution state check (process running? file exists?) |

**Protected directories** (writes/deletes blocked):
Windows: `System32`, `Program Files`, `Windows`
Unix: `/bin`, `/etc`, `/sys`, `/usr`, `/boot`
macOS: `/System`, `/Library`

**Default permissions:**
`open_file=true`, `open_app=true`, `read_system_info=true`, `open_browser=true`
Everything else defaults to `false` and prompts on first use.

---

## All 17 Tools

### File Operations

| Tool | Parameters | Risk | Description |
|---|---|---|---|
| `list_directory` | `path` (optional, default `.`) | SAFE | List files and folders |
| `read_file` | `path` (required) | SAFE | Read file contents |
| `write_file` | `path`, `content` | MEDIUM | Write to a file |
| `create_file` | `path`, `content` | MEDIUM | Create a new file |
| `search_files` | `pattern`, `directory` (optional) | SAFE | Glob search, recursive, max 100 results |

### System Information

| Tool | Parameters | Risk | Description |
|---|---|---|---|
| `get_system_info` | — | SAFE | OS, CPU, RAM, disk usage for all partitions |
| `get_network_info` | — | SAFE | Network interfaces and active connections |
| `get_self_info` | — | SAFE | Evo-AI's own RAM, CPU, disk usage + Ollama status |

### Process Management

| Tool | Parameters | Risk | Description |
|---|---|---|---|
| `list_processes` | — | SAFE | Top 50 processes by memory usage |
| `kill_process` | `pid` or `name` | HIGH | Terminate a process (critical system processes blocked) |

### Application & Browser

| Tool | Parameters | Risk | Description |
|---|---|---|---|
| `open_application` | `app_name` | LOW | Launch any installed app via resolution pipeline |
| `open_website` | `site_name`, `url` (optional) | SAFE | Open a URL in the preferred browser |
| `search_web` | `query`, `engine` (default `google`), `browser` (optional) | SAFE | Web search with browser continuity support |

### System Utilities

| Tool | Parameters | Risk | Description |
|---|---|---|---|
| `take_screenshot` | `filename` (optional) | SAFE | Capture screen, saves to file |
| `get_clipboard` | — | SAFE | Read clipboard contents |
| `set_clipboard` | `text` | SAFE | Write to clipboard |

> **Note:** macOS and Linux OS adapters are stubs — system operations (open app, screenshot, clipboard) are fully implemented on Windows only. Resolution, normalizer, and file tools work cross-platform.

---

## Command Reference

### Natural language examples

```bash
# Applications
open chrome
open vscode
open spotify
open my browser
open something for coding
opne chorme                    # typo — auto-corrected

# Websites
open youtube
open github
open gmail

# Web search
search for machine learning
google python tutorials
open chrome and search spotify  # browser continuity

# Files
list files
find all python files in Documents
find pdf files in Downloads
search images on Desktop
read file report.txt

# System
system info
running processes
how much memory do you use?
take a screenshot
what's in my clipboard

# Compound commands (9 connector types supported)
open chrome and search youtube
open notepad then create test.txt
open chrome, search spotify, take a screenshot

# Conversational
hi
tell me about yourself
what can you do
who are you
```

### Compound command connectors

```
open chrome and search youtube
open chrome, then search youtube
open chrome, and then search youtube
open chrome then search youtube
open chrome, search youtube, close chrome
open chrome after that search youtube
```

### Session mode (goal-oriented)

```
goal: set up a python project
continue          # get next stage
abort             # stop session
```

---

## Configuration

All config files live in `config/`.

### `config/settings.json`

```json
{
  "default_mode": "offline",
  "auto_save_chat": true,
  "max_memory_messages": 50,
  "temperature": 0.7,
  "max_tokens": 2000,
  "debug": false,
  "streaming": true
}
```

### `config/personality.json`

```json
{
  "name": "Evo-AI",
  "identity": "I am your lawful local companion that runs entirely on your computer.",
  "principles": [
    "Always respect user control.",
    "Stay operational offline.",
    "Never send data online without consent.",
    "Explain before executing."
  ],
  "style": { "tone": "calm", "confidence": "balanced" }
}
```

### `config/permissions.json`

Stores current permission state. Managed by `PermissionManager` — edit manually or use the `permissions` command in CLI.

Default grants: `open_file`, `open_app`, `read_system_info`, `open_browser`

### `config/permission_audit.jsonl`

Append-only audit log of every permission request. One JSON object per line.

### `.env` (optional)

```env
OPENAI_API_KEY=sk-...          # online LLM fallback
OPENAI_BASE_URL=https://...    # custom OpenAI-compatible endpoint
```

### LLM settings (`core/llm_client.py`)

| Setting | Value |
|---|---|
| Model | `llama3.2:latest` (Ollama) |
| Temperature | 0.7 |
| Top-p | 0.9 |
| Top-k | 40 |
| Repeat penalty | 1.1 |
| Max tokens | 1500 |
| Response cache | 50 entries (LRU) |
| Conversation history | Last 4 turns (500 chars each) |

---

## Project Structure

```
Evo-AI/
│
├── cli/
│   └── cli.py                    # Rich terminal interface + run_ai() API wrapper
│
├── core/
│   ├── brain.py                  # Orchestrator — generate_plan() + execute_plan()
│   ├── reasoning.py              # Intent routing (6-priority hierarchy)
│   ├── planner.py                # Compound instruction splitter (deterministic)
│   ├── executor.py               # Registry-based action execution
│   ├── tools.py                  # 17 registered system tools
│   ├── tool_registry.py          # Singleton tool registry with schema validation
│   ├── verifier.py               # Pre/post execution verification
│   ├── safety.py                 # Legacy permission filter
│   ├── safety_validator.py       # Path + command safety rules
│   ├── permission_manager.py     # Interactive permissions + audit log
│   ├── llm_client.py             # Ollama integration + online fallback
│   ├── memory.py                 # Conversation history + session saving
│   ├── action_parser.py          # LLM response → tool call parser
│   ├── browser_automation.py     # Browser detection + URL/search launcher
│   ├── environment.py            # Cross-platform path resolution
│   ├── learning_layer.py         # Pattern learning (built, not yet wired)
│   ├── session_engine.py         # Goal-oriented multi-stage sessions
│   ├── system_prompt.py          # LLM system prompt + few-shot examples
│   │
│   ├── input/
│   │   └── input_normalizer.py   # Typo correction, aliases, semantic mapping
│   │
│   ├── resolution/
│   │   └── target_resolver.py    # 4-step app/website resolution pipeline
│   │
│   ├── extraction/
│   │   └── parameter_extractor.py # Natural language → structured params
│   │
│   ├── context/
│   │   ├── context_engine.py     # 3-mode context: surface / deep / visual
│   │   ├── system_context.py     # Active window, top processes
│   │   ├── workspace_context.py  # Recent files in standard locations
│   │   ├── project_analyzer.py   # Project type detection, file stats
│   │   ├── visual_context.py     # Screenshot with permission gate
│   │   └── execution_context.py  # Ephemeral workflow context (browser continuity)
│   │
│   ├── debugger/
│   │   └── debugger.py           # Fuzzy-match suggestion engine
│   │
│   ├── capabilities/
│   │   ├── base_capability.py    # BaseCapability ABC
│   │   ├── capability_registry.py
│   │   ├── capability_initializer.py
│   │   └── file_management_capability.py  # organize_downloads, find_file, list_recent
│   │
│   └── os_adapter/
│       ├── base_adapter.py       # Abstract interface
│       ├── windows_adapter.py    # Full implementation
│       ├── macos_adapter.py      # Stub (NotImplementedError)
│       └── linux_adapter.py      # Stub (NotImplementedError)
│
├── os_overlay/
│   ├── main.py                   # Entry point
│   ├── overlay_window.py         # Modern UI: dots, plan card, debugger card
│   ├── controller.py             # UI ↔ Brain glue, state machine
│   └── hotkey.py                 # Ctrl+Space global hotkey
│
├── interfaces/
│   └── voice/
│       ├── voice_assistant.py        # Full voice (PyAudio)
│       ├── voice_assistant_simple.py # Windows-only (no PyAudio)
│       └── requirements.txt
│
├── config/
│   ├── settings.json
│   ├── personality.json
│   ├── permissions.json
│   ├── permission_audit.jsonl
│   └── system_paths.json
│
├── logs/                         # Session transcripts (auto-saved)
├── ARCHITECTURE.md               # Full technical architecture documentation
└── README.md                     # This file
```

---

## Requirements

### Core dependencies

```
ollama                  # local LLM runtime (install separately from ollama.ai)
rich                    # terminal UI
psutil                  # process and system info
keyboard                # global hotkey registration
Pillow                  # screenshots
pywin32                 # Windows clipboard + active window (Windows only)
requests                # Ollama API calls
```

### Voice interface (optional)

```bash
pip install -r interfaces/voice/requirements.txt
# Windows (no PyAudio): pywin32, pyttsx3, SpeechRecognition
# All platforms:        pyttsx3, SpeechRecognition, PyAudio
```

### Everything CLI (optional but recommended)

[Everything](https://www.voidtools.com/) (`es.exe`) dramatically improves app resolution on Windows — finds any installed `.exe` instantly by searching the actual filesystem. Without it, Evo-AI falls back to a curated list of ~45 known apps.

### Python version

Python 3.10 or higher.

---

## Resource Usage

| Component | RAM (idle) | RAM (active) | Disk |
|---|---|---|---|
| Evo-AI | ~25–50 MB | ~25–50 MB | ~0.3 MB |
| Ollama (idle) | ~30–100 MB | — | — |
| Ollama (generating) | — | ~1.5–2.5 GB | — |
| llama3.2 model | — | — | ~1.9 GB |
| **Total** | **~55–150 MB** | **~1.5–2.5 GB** | **~2 GB** |

CPU: <1% idle, 20–80% for 2–10 seconds when generating a response.

---

## Limitations

- **macOS and Linux system operations** (open app, screenshot, clipboard) are not yet implemented — the OS adapters raise `NotImplementedError`. File operations, web search, and the resolution pipeline work cross-platform.
- **Learning layer** (`core/learning_layer.py`) is built and functional but not wired into the main routing pipeline.
- **Session engine** goal mode is available via `goal: <text>` in the CLI but not exposed in the overlay UI.
- **Everything CLI** (`es.exe`) is Windows-only. On other platforms, app resolution falls back to the known-apps list.
- **LLM responses** require Ollama to be running (`ollama serve`). Without it, conversational queries return an error; all deterministic commands (open, search, files, system info) still work.

---

## Architecture

For the full technical architecture — resolution pipeline details, safety layer internals, overlay state machine, parameter extraction tables, execution context design, and PySide6 migration path — see [`ARCHITECTURE.md`](ARCHITECTURE.md).

---

*Built with Python · Runs locally · No cloud required*
