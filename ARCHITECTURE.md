# 🏗️ Evo-AI - Complete Architecture Documentation

> **Offline-first AI Desktop Assistant with System Control**

**Version:** 2.2.0  
**Status:** Production Ready  
**Platform:** Windows, macOS, Linux

---

## 📑 Table of Contents

1. [Overview](#overview)
2. [Quick Start](#quick-start)
3. [System Architecture](#system-architecture)
4. [🔥 NEW: Resolution Layer (Input Intelligence)](#-new-resolution-layer-input-intelligence)
5. [Conversational Fallback Layer](#conversational-fallback-layer)
6. [Parameter Extraction Layer](#parameter-extraction-layer)
7. [Execution Context Layer](#execution-context-layer)
8. [Core Components](#core-components)
9. [Features](#features)
10. [Usage Guide](#usage-guide)
11. [Development](#development)
12. [Testing](#testing)

---

## Overview

### What is Evo-AI?

Evo-AI is a **production-quality AI desktop assistant** that runs entirely on your computer. It combines ChatGPT-quality conversations with actual system control capabilities - all while keeping your data private and working completely offline.

### Key Features

- **Privacy First**: Everything runs locally - no data sent to cloud
- **Offline Capable**: Works without internet using local LLM (Ollama)
- **System Integration**: Can actually control your computer
- **ChatGPT-Quality**: Natural conversations with streaming responses
- **Environment Aware**: Cross-platform OS detection and path resolution
- **Verified Execution**: Strict verification eliminates false positives
- **Fast & Smart**: Hybrid intelligence - instant for commands, thoughtful for conversations

### Resource Usage

**Your laptop can easily handle it!**

- **Evo-AI**: ~25-50 MB RAM (very lightweight!)
- **Ollama (idle)**: ~30-100 MB RAM
- **Ollama (active)**: ~1.5-2.5 GB RAM when generating responses
- **Disk space**: ~2 GB total (0.3 MB code + 1.9 GB AI model)
- **CPU**: <1% idle, 20-80% for 2-10 seconds when generating

---

## Quick Start

### 1. Install Ollama

Download from: https://ollama.ai

```bash
# Install Ollama, then:
ollama serve
ollama pull llama3.2:latest
```

### 2. Install Dependencies

```bash
cd Evo-AI_mogwai_local
pip install -r requirements.txt
```

### 3. Run Evo-AI

**Terminal Interface (CLI)**:
```bash
python cli/Evo-AI_cli.py
```

**Windows Overlay (GUI)**:
```bash
cd os_overlay
python main.py
```

### 4. Try It!

```
You: hi
You: how much memory do you use?
You: system info
You: open youtube
You: tell me about python
You: open chrome and search for AI tutorials
```

---

## System Architecture

### High-Level Overview

```
┌─────────────────────────────────────────────────────────────┐
│                         USER INPUT                          │
│              "open chrome and search youtube"               │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                      CLI INTERFACE                          │
│                    (Evo-AI_cli.py)                            │
│  • Rich terminal UI with colors                            │
│  • Command handling and history                            │
│  • Session management                                       │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                         BRAIN                               │
│                     (brain.py)                              │
│  • Pure logic layer (no I/O)                               │
│  • Orchestrates all components                             │
│  • Single method: process(text) -> response                │
│  • Reusable by any interface                               │
└────────────────────────┬────────────────────────────────────┘
                         │
                    ┌────┴────┐
                    │         │
              Compound?    Single?
                    │         │
                    ▼         ▼
         ┌──────────────┐  ┌──────────────┐
         │   PLANNER    │  │   REASONER   │
         │  (compound)  │  │   (single)   │
         └──────┬───────┘  └──────┬───────┘
                │                 │
                │                 ▼
                │          ┌──────────────┐
                │          │ Pattern Match│
                │          │  or LLM?     │
                │          └──────┬───────┘
                │                 │
                └─────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                    EXECUTION FLOW                           │
│                                                             │
│  ┌──────────────┐                                          │
│  │  VERIFIER    │  Pre-Check: Validate parameters          │
│  │ (pre-check)  │  • File exists?                          │
│  └──────┬───────┘  • Required params?                      │
│         │          • Valid paths?                          │
│         ▼                                                   │
│  ┌──────────────┐                                          │
│  │   EXECUTOR   │  Execute: Run the action                 │
│  │   (execute)  │  • Registry lookup                       │
│  └──────┬───────┘  • Safety validation                     │
│         │          • Permission check                      │
│         ▼                                                   │
│  ┌──────────────┐                                          │
│  │  VERIFIER    │  Post-Check: Verify results              │
│  │ (post-check) │  • Process running?                      │
│  └──────┬───────┘  • File created?                         │
│         │          • No errors?                            │
│         ▼                                                   │
│  ┌──────────────┐                                          │
│  │    RESULT    │  Return verified result                  │
│  └──────────────┘                                          │
└─────────────────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                       RESPONSE                              │
│         "✓ Task completed successfully:                     │
│          1. Opened Chrome                                   │
│          2. Searched for 'youtube'"                         │
└─────────────────────────────────────────────────────────────┘
```

### Hybrid Intelligence (3-Tier System)

Evo-AI uses a smart routing system that balances speed and capability:

**Tier 1: Conversational Detection** (Instant)
- Detects: "hi", "hello", "tell me", "explain", "what is"
- Action: Route to LLM for natural conversation
- Speed: Instant pattern match

**Tier 2: Pattern Matching** (<10ms)
- Detects: "open youtube", "system info", "list files"
- Action: Execute directly without LLM
- Speed: <10ms

**Tier 3: LLM Reasoning** (2-10s)
- Complex queries that need understanding
- Action: LLM analyzes and suggests actions
- Speed: 2-10 seconds

---

---

## NEW: Resolution Layer (Input Intelligence)

> Added in v2.1.0, refined in v2.1.1.

### Why This Layer Exists

Before v2.1.0, the system used exact string matching to decide whether a target
was an app or a website. This caused failures on typos, aliases, and unknown
inputs. The Resolution Layer fixes this without adding any LLM-based decision
making.

---

### Execution Flow

```
User Input
    |
    v
+----------------------------------------------------------+
|  INPUT NORMALIZER  (core/input/input_normalizer.py)      |
|  - Lowercase + strip whitespace                          |
|  - Typo correction  ("spotfy" -> "spotify")              |
|  - Alias expansion  ("browser" -> "chrome")              |
+-------------------------+--------------------------------+
                          | normalized text
                          v
+----------------------------------------------------------+
|  TARGET RESOLVER   (core/resolution/target_resolver.py)  |
|                                                          |
|  Step 1: Known websites (<=10 entries, non-obvious URLs) |
|  Step 2: Everything CLI search -- es.exe (PRIMARY)       |
|  Step 3: Known-apps list (fallback, no Everything)       |
|  Step 4: Web search fallback (explicit, not silent)      |
|                                                          |
|  Returns: ResolutionResult                               |
|    category: "application" | "web_search" | "unknown"   |
|    query: normalized input (unchanged)                   |
|    confidence: "high" | "medium" | "low"                 |
|    resolved_path: full path or URL if found              |
+-------------------------+--------------------------------+
                          | ResolutionResult
                          v
              +-----------+------------+
              |                        |
    confidence low/fallback     confidence high/medium
              |                        |
              v                        v
          Debugger                  Reasoner
          (returns                     |
        DebugReport,                   v
        no execution)              Planner
                                       |
                                       v
                                   Executor
                                       |
                                       v
                                   Verifier
```

---

### Resolution Principles

**Deterministic** -- Every decision follows a fixed rule. No AI, no probability,
no guessing.

**Search-first** -- Everything CLI (es.exe) is the primary app resolution method.
It searches the actual filesystem, so it works for any installed app without
needing a hardcoded entry.

**Minimal hardcoding** -- The known-websites list is capped at 10 entries (sites
with non-obvious URLs like gmail -> mail.google.com). The known-apps list is a
fallback used only when Everything is unavailable.

**No silent fallbacks** -- When an app is not found locally, the resolver returns
category="web_search" with confidence="low". The reasoning layer attaches a
fallback_info dict so the execution layer can inform the user before searching,
rather than silently switching behavior.

**No URL guessing** -- The resolver never constructs www.{name}.com. Unknown
sites go through search_web.

**Separation of resolution vs execution** -- The resolver only classifies the
target and returns structured data. It never calls tools, builds URLs for unknown
sites, or decides what to execute. Those decisions belong to the reasoning and
execution layers.

---

### 4-Step Resolution Pipeline

```
1. KNOWN WEBSITES (<=10 entries)
   - Non-obvious canonical URLs only (gmail, spotify, teams...)
   - Returns: category=web_search, confidence=high, resolved_path=URL

2. EVERYTHING CLI (es.exe) -- PRIMARY
   - Searches actual filesystem for <target>.exe
   - Filters: .exe files only
   - Ranks: exact name (3) > prefix (2) > contains (1)
   - Tiebreak: shorter path wins
   - Returns: category=application, confidence=high, resolved_path=full_path

3. KNOWN-APPS LIST -- FALLBACK (Everything unavailable only)
   - Curated map of ~45 common apps -> executable names
   - Match order: exact -> prefix -> substring
   - Returns: category=application, confidence=medium, resolved_path=exe_name

4. WEB SEARCH FALLBACK -- EXPLICIT
   - No local match found
   - Returns: category=web_search, confidence=low, resolved_path=None
   - Caller receives fallback_info dict:
     { "status": "fallback", "reason": "APPLICATION_NOT_FOUND",
       "suggested_action": "web_search", "query": "<target>" }
   - Execution layer decides -- user is informed, not surprised
```

---

### Debugger Layer

The Debugger activates **after the Resolver** and **before the Planner/Executor**,
only when resolution confidence is low or a fallback_info is present.

```
User Input
    |
    v
Input Normalizer
    |
    v
Target Resolver
    |
    +-- confidence == "high" or "medium" ---------> Reasoner --> Planner --> Executor
    |
    +-- confidence == "low"  OR fallback_info -----> Debugger
                                                         |
                                                         v
                                                   DebugReport
                                                   (returned to user)
                                                   NO execution occurs
```

**DebugReport structure:**
```python
{
    "status":       "debug",
    "message":      "Application 'spotfy' was not found...",
    "suggestions":  [
        "Open application: spotify",
        "Search web for: spotfy",
    ],
    "next_actions": [
        {"action": "open_application", "params": {"app_name": "spotify"}, "label": "Open spotify"},
        {"action": "search_web",       "params": {"query": "spotfy"},     "label": "Search the web for 'spotfy'"},
    ]
}
```

**Principles:**
- Non-executing: the debugger never calls tools, never launches apps, never modifies state
- Deterministic: suggestions come from fuzzy matching on known-apps and known-websites lists
- No LLM: all logic is rule-based
- User in control: next_actions are presented as choices, not auto-executed
- Transparent: the message explains exactly what happened and why

**Location:** `core/debugger/debugger.py`

---

### Resolution Examples

| User Input     | After Normalizer | Category    | Confidence | Action Taken                     |
|----------------|-----------------|-------------|------------|----------------------------------|
| open spotfy    | open spotify    | web_search  | high       | Opens https://open.spotify.com   |
| open youtube   | open youtube    | web_search  | high       | Opens https://www.youtube.com    |
| open tinkercad | open tinkercad  | web_search  | low        | Searches Google for "tinkercad"  |
| open vscode    | open vscode     | application | medium     | Launches code.exe                |
| launch browser | launch chrome   | application | medium     | Launches chrome.exe              |
| open unknownapp| open unknownapp | web_search  | low        | Searches Google for "unknownapp" |

---

### Input Intelligence Enhancements

Added in v2.1.2 to address UX gaps found in stress testing.
All rules are deterministic — no LLM, no randomness.

#### 1. Verb Normalization

Common verb typos are corrected before any other processing:

```
opne  → open      lauch  → launch
opn   → open      launhc → launch
oen   → open      satrt  → start
```

This runs on the **first word only**, before the target is extracted.
Previously, `opne chrome` would bypass the entire resolution pipeline.
Now it correctly resolves to `open chrome`.

#### 2. Phrase-Level Aliases

The alias table now supports multi-word phrases as keys:

```
"my browser"   → chrome      "my editor"    → vscode
"web browser"  → chrome      "code editor"  → vscode
"the browser"  → chrome      "music player" → spotify
```

These are matched against the full target string (after the verb),
so `open my browser` correctly resolves to `open chrome`.

#### 3. Semantic Intent Mapping (Rule-Based)

A lightweight keyword → app mapping is applied **only when no direct
match or alias was found** (i.e. the target is still unresolved after
steps 1-2). This handles vague intent phrases:

```
music / songs / playlist  → spotify
video / movie / media     → vlc
coding / programming      → vscode
chat / messaging          → discord
browsing / web            → chrome
notes / writing           → notepad
3d / modeling             → blender
streaming / recording     → obs
gaming / games            → steam
```

Applied via `InputNormalizer.resolve_semantic()`. No LLM. No guessing.
`open something for music` → `open spotify`.

#### 4. Debugger Suggestion Filtering

The debugger's fuzzy matcher now enforces a **minimum score threshold
of 2** (prefix match or better). Score-1 matches (character overlap,
substring) are excluded from suggestions.

Before: `open asdfghjkl` → suggested `slack`, `signal`, `taskmgr` (meaningless)
After:  `open asdfghjkl` → only `Search web for: asdfghjkl` (honest)

Meaningful typos still get relevant suggestions:
`open discrod` → suggests `discord` (prefix match, score 2+).

---

### New Files

| File | Purpose |
|------|---------|
| `core/input/input_normalizer.py` | Typo correction + alias expansion |
| `core/input/__init__.py` | Module exports |
| `core/resolution/target_resolver.py` | 4-step resolution pipeline |
| `core/resolution/__init__.py` | Module exports |

### Modified Files (minimal changes)

| File | Change |
|------|--------|
| `core/reasoning.py` | Normalizer + resolver imports; OPEN block uses `category`/`confidence` to route; low-confidence fallback attaches `fallback_info` instead of silently searching |
| `core/tools.py` | `open_website` accepts pre-resolved URL; `open_application` uses `resolved_path`; no silent web-search fallback |

---

## Conversational Fallback Layer

> Added in v2.1.1 as part of the bug fix + UX polish pass.

### Purpose

Handles non-action queries (greetings, identity questions, capability questions,
random text) with a safe, deterministic response. Bypasses the entire execution
pipeline — no resolver, no planner, no executor, no LLM.

### Location

`core/reasoning.py` — `handle_general_query()` (module-level function)

### How It Works

```
User Input
    |
    v
InputNormalizer
    |
    v
Reasoner.analyze_request()
    |
    +-- Priority 1-5: System / process / action commands ──> normal pipeline
    |
    +-- Priority 6: _is_conversational() == True
    |       AND _is_system_related() == False
    |               |
    |               v
    |       handle_general_query()
    |               |
    |               v
    |       Returns deterministic string response
    |       intent = "general_query"
    |       use_llm = False
    |       actions = []
    |
    +-- _enhanced_pattern_match() conversational check ──> same fallback
```

### Trigger Conditions

The fallback activates when **any** of the following are true:

- Input matches `_is_conversational()`:
  - Short greetings: `hi`, `hello`, `hey`, `yo`, `sup`
  - Conversational starters: `tell me`, `explain`, `what is`, `how does`,
    `why`, `describe`, `can you`, `could you`, `would you`, `please`,
    `help me understand`, `what games`, `what can i`, `recommend`, `suggest`
  - Question words (`what`, `why`, `how`, `when`, `where`, `who`, `which`)
    when no system/file/process keyword is present
- No tool keyword scores > 0 in `_enhanced_pattern_match()`
- Input is empty or unrecognisable

### What It Does NOT Do

- Does **not** call the resolver or planner
- Does **not** call the executor or verifier
- Does **not** trigger the debugger
- Does **not** use the LLM (`use_llm` is always `False`)
- Does **not** modify system state

### Response

```
I am Evo-AI. I can help you with tasks like:
  - Opening applications
  - Searching the web
  - Executing system commands safely

Try commands like:
  open chrome
  open something for coding
  open youtube
```

### Integration in Brain

`Brain.generate_plan()` detects `intent == "general_query"` and returns a
`StructuredPlan` with `is_conversational=True` and the pre-built string stored
in `conversational_response`. `Brain.execute_plan()` returns it directly as an
`ExecutionResult` without touching the executor.

### Next Phase Preparation

The `next_actions` list in `DebugReport` (from the Debugger layer) is already
structured for interactive selection. The next phase — **Interactive Suggestions
Selection** — will allow the CLI to present `next_actions` as numbered choices
the user can pick from, rather than displaying them as plain text. No changes to
the Conversational Fallback Layer are required for that phase.

---

## Parameter Extraction Layer

> Added in v2.2.0 to fix missing structured parameters for file-search and web-search commands.

### Problem Solved

Before this layer, commands like `"find all python files in Documents"` correctly
detected `search_files` intent but produced empty `pattern` and `directory` params,
causing the tool to return "No search pattern provided".

### Location

`core/extraction/parameter_extractor.py`  
`core/extraction/__init__.py`

### Integration Point

```
Input → Normalizer → Resolver → ParameterExtractor (HERE) → Planner → Executor
```

Called inside `Reasoner.analyze_request()` as a post-resolution enrichment step.
The public method `analyze_request()` calls `_analyze_request_inner()` (all routing
logic) then passes the result through `_enrich_params()` before returning.

### What It Does

Converts natural-language intent strings into structured, typed parameter dicts.
Only fills in keys that are **missing** — never overwrites values already set by
the resolver.

**File type mapping** (natural word → glob pattern):
```
python → *.py       pdf → *.pdf       image → *.{png,jpg,...}
video  → *.{mp4,…}  txt → *.txt       markdown → *.md
… (50+ entries)
```

**Directory mapping** (natural name → absolute path):
```
Documents → ~/Documents    Downloads → ~/Downloads
Desktop   → ~/Desktop      Pictures  → ~/Pictures
Videos    → ~/Videos       Music     → ~/Music
```

**Search query extraction** (strips verb prefixes):
```
"search for spotify"        → query="spotify"
"google machine learning"   → query="machine learning"
```

**Process name extraction**:
```
"kill chrome"   → name="chrome"
"stop notepad"  → name="notepad"
```

### Examples

| Input | Tool | Extracted Params |
|---|---|---|
| `find all python files in Documents` | `search_files` | `{pattern: "*.py", directory: "~/Documents"}` |
| `find pdf files in Downloads` | `search_files` | `{pattern: "*.pdf", directory: "~/Downloads"}` |
| `search images on Desktop` | `search_files` | `{pattern: "*.{png,jpg,...}", directory: "~/Desktop"}` |
| `search for spotify` | `search_web` | `{query: "spotify"}` |

### Rules

- No LLM — all logic is regex + deterministic lookup tables
- Never executes anything
- Returns structured dicts only
- Lightweight — no I/O, no subprocess calls

---

## Execution Context Layer

> Added in v2.2.0 to fix browser continuity in multi-step workflows.

### Problem Solved

Before this layer, `"open chrome and search spotify"` opened Chrome correctly but
then opened the Spotify search in the system-default browser (Brave) instead of
Chrome, because the two steps had no shared state.

### Location

`core/context/execution_context.py`

### Design

```python
ctx = ExecutionContext()   # created fresh per plan execution
ctx.set_active_browser("chrome")
ctx.get_active_browser()  # → "chrome"
ctx.reset()               # clears all state
```

**Rules:**
- Context exists **only during workflow execution** — created in `Brain.execute_plan()`,
  discarded when the method returns
- No long-term memory, no persistence, no global variables
- Context must be explicitly passed — never imported as a singleton
- No autonomous state tracking — state is set only by explicit calls from Brain

### Integration in Brain.execute_plan()

```
Plan execution starts
    │
    ├─ ExecutionContext created (fresh, empty)
    │
    ├─ Pre-seed: ParameterExtractor.detect_browser(original_text)
    │       → if browser found in command text, set in context immediately
    │         so even the first search step targets the right browser
    │
    ├─ For each step:
    │       ├─ action == "search_web" AND context.has_active_browser()
    │       │       → inject params["browser"] = context.get_active_browser()
    │       │
    │       ├─ Execute action
    │       │
    │       └─ action == "open_application" AND result contains "✓"
    │               → detect_browser(app_name)
    │               → if browser: context.set_active_browser(browser)
    │
    └─ ExecutionContext goes out of scope — no state leaks between commands
```

### Browser Continuity Example

```
"open chrome and search spotify"

Step 1: open_application("chrome")
    → ExecutionContext.set_active_browser("chrome")

Step 2: search_web(query="spotify")
    → Brain injects: params["browser"] = "chrome"
    → BrowserAutomation.search(..., preferred_browser="chrome")
    → Finds chrome.exe path, launches Chrome with search URL
    → Result: Spotify search opens IN Chrome ✓
```

### Context Isolation

Each call to `Brain.execute_plan()` creates a new `ExecutionContext` instance.
Separate commands never share browser state.

```
Command 1: "open chrome and search spotify"  → ctx1 (chrome) → discarded
Command 2: "open edge and search youtube"    → ctx2 (edge)   → discarded
Command 3: "search github"                   → ctx3 (empty)  → uses default browser
```

### Updated search_web Tool

`search_web` now accepts an optional `browser` parameter:

```python
search_web(query="spotify", browser="chrome")
# → opens search in Chrome specifically

search_web(query="spotify")
# → falls back to default browser behavior (unchanged)
```

`BrowserAutomation.search()` and `open_url()` accept `preferred_browser` to
look up the specific browser path from `BROWSER_PATHS` before falling back to
the system default.

---

## Core Components

### 1. Brain (`core/brain.py`)

**Purpose**: Pure intelligence layer - orchestrates all AI logic

**Key Features**:
- NO input(), NO print(), NO I/O
- Single public method: `process(text: str) -> str`
- Reusable by CLI, voice, GUI, or any interface
- Manages reasoning, execution, LLM, memory, planning

**Responsibilities**:
- Detect compound vs single instructions
- Route to appropriate handler (Planner or Reasoner)
- Manage conversation flow
- Coordinate all components

### 2. Reasoner (`core/reasoning.py`)

**Purpose**: Intent detection and fast-path routing for single commands

**Key Features**:
- Pattern matching for common commands
- Intent classification
- Confidence scoring
- Tool registry awareness

**Routing Priority**:
1. System queries (CPU, RAM, processes) → Direct execution
2. Process queries → list_processes
3. Quick patterns (open, list, search) → Direct execution
4. Conversational queries → LLM
5. Enhanced pattern matching → Tool selection

### 3. Planner (`core/planner.py`)

**Purpose**: Deterministic multi-step execution for compound instructions

**Key Features**:
- NO LLM planning (deterministic only)
- Robust compound instruction splitting
- Sequential execution with immediate failure stop
- Integrated verification (pre-check + post-check)
- Order preservation

**Supported Connectors**:
- ", then " - `open chrome, then search youtube`
- ", and then " - `open chrome, and then search youtube`
- ", and " - `open chrome, and search youtube`
- ", after that " - `open chrome, after that search youtube`
- " and then " - `open chrome and then search youtube`
- " then " - `open chrome then search youtube`
- " after that " - `open chrome after that search youtube`
- " and " - `open chrome and search youtube`
- "," - `open chrome, search youtube, close chrome`

**Splitting Logic**:
- Case-insensitive pattern matching
- Handles mixed separators in single instruction
- Removes extra whitespace
- Filters leading/trailing connector words
- Deduplicates consecutive identical commands
- Preserves strict step order

**Realistic Windows Workflows Supported**:
```
"open file explorer and go to downloads and open report.pdf"
"open notepad then create test.txt in documents"
"open chrome, then search youtube, then close chrome"
"open settings and show system info"
"open explorer, find report.pdf from desktop, then open it"
```

**Execution Flow**:
```
For each step:
  1. PRE-CHECK: Validate parameters
  2. EXECUTE: Run the action
  3. POST-CHECK: Verify state changes
  4. Continue or stop on failure
```

**Testing**: 32 comprehensive unit tests covering:
- Multi-step parsing (9 connector types)
- Order preservation
- Mixed separators
- Edge cases (trailing/leading connectors, extra spaces, capitalization)
- Realistic Windows workflows
- Plan building and structure validation

### 4. Executor (`core/executor.py`)

**Purpose**: Registry-based action execution with safety validation

**Key Features**:
- Single execution path for all tools
- Automatic parameter validation
- Multi-layer safety checks
- Permission management
- Execution history tracking

**Safety Layers**:
1. Parameter validation (schema check)
2. Path safety validation (protected directories)
3. Permission check (user approval)
4. Audit logging (track all actions)

### 5. Verifier (`core/verifier.py`)

**Purpose**: Strict execution verification to eliminate false positives

**Key Features**:
- Pre-check: Validates before execution
- Post-check: Verifies actual state changes
- Error detection: 17 error keywords
- Deterministic: No LLM-based verification

**Verification Examples**:
- Application opened → Verifies process is running
- File created → Verifies file exists on disk
- Screenshot taken → Verifies image file created
- Process list → Verifies non-empty result

### 6. Environment Manager (`core/environment.py`)

**Purpose**: Cross-platform OS detection and path resolution

**Key Features**:
- OS detection (Windows, macOS, Linux)
- User information (username, home, desktop, documents, downloads)
- Natural path resolution ("file.txt from desktop" → full path)
- Process detection and management
- Path validation

**Cross-Platform**:
- Windows: Standard Windows paths
- macOS: Standard macOS paths
- Linux: XDG user directories with fallbacks

### 7. Tool Registry (`core/tool_registry.py`)

**Purpose**: Centralized tool registration and validation

**Key Features**:
- O(1) tool lookup
- Automatic parameter validation
- Schema enforcement
- Risk level classification
- OS compatibility tracking

**Tool Metadata**:
- Name, description, function
- Parameters with types and defaults
- Risk level (SAFE, LOW, MEDIUM, HIGH)
- Required permissions
- OS support

### 8. System Tools (`core/tools.py`)

**Purpose**: Actual system operations implementation

**Registered Tools (17 total)**:

**File Operations (5)**:
- list_directory, read_file, write_file, create_file, search_files

**System Information (3)**:
- get_system_info, get_network_info, get_self_info

**Process Management (2)**:
- list_processes, kill_process

**Application Control (1)**:
- open_application

**Media (1)**:
- take_screenshot

**Browser (2)**:
- open_website, search_web

**Clipboard (2)**:
- get_clipboard, set_clipboard

### 9. Safety Validator (`core/safety_validator.py`)

**Purpose**: Path and command safety validation

**Key Features**:
- Protected directory detection
- Path traversal prevention
- Dangerous command detection
- URL validation
- Query sanitization

### 10. Permission Manager (`core/permission_manager.py`)

**Purpose**: User permission management and audit logging

**Key Features**:
- Permission categories (read, write, execute, etc.)
- User approval prompts
- Audit trail (JSONL format)
- Risk-based prompts

### 11. LLM Client (`core/llm_client.py`)

**Purpose**: Ollama integration for conversations

**Key Features**:
- Local LLM (Ollama) integration
- Streaming responses
- Context management
- Fallback handling

### 12. Memory (`core/memory.py`)

**Purpose**: Conversation history and context management

**Key Features**:
- Message storage (user + assistant)
- Context window management (6 messages)
- System prompt management
- Message truncation

### 13. Action Parser (`core/action_parser.py`)

**Purpose**: Parse LLM responses for executable actions

**Key Features**:
- Extract action blocks from LLM output
- JSON parsing
- Multiple action support

---

## Features

### 🤖 AI Capabilities

- **ChatGPT-Style Conversations** - Natural language understanding
- **Streaming Responses** - Text appears word-by-word in real-time
- **Context Awareness** - Remembers conversation history (6 messages)
- **Smart Intent Detection** - Knows when to chat vs. execute commands
- **Self-Awareness** - Can answer questions about its own resource usage
- **Response Caching** - 20x faster for repeated questions

### 🖥️ System Control

- **File Operations** - List, read, write, create, search, delete files
- **Process Management** - View and manage running processes
- **Application Launching** - Open any installed application
- **Browser Automation** - Opens 40+ popular websites automatically
- **Screenshot Capture** - Take screenshots on command
- **System Information** - Hardware specs, network info, disk usage
- **Clipboard Operations** - Read and write clipboard

### 🌍 Environment Awareness

- **OS Detection** - Automatically detects Windows, macOS, or Linux
- **User Information** - Username, home directory, standard paths
- **Natural Path Resolution** - "file.txt from desktop" → full path
- **Process Detection** - Advanced process search and validation
- **Path Validation** - Safe path existence checking
- **Cross-Platform** - Works identically on all platforms

### ✅ Verified Execution

- **Pre-Check Validation** - Validates parameters before execution
- **Post-Check Verification** - Confirms actual state changes
- **Error Detection** - Comprehensive error keyword monitoring
- **Immediate Failure Stop** - Stops on first failure
- **No False Positives** - Only reports success when verified

### 🔒 Security & Privacy

- **Offline-First** - Works without internet
- **Permission System** - Explicit approval for sensitive actions
- **Audit Logging** - Track all actions taken
- **Local Data** - Everything stored on your computer
- **Multi-Layer Safety**:
  1. Parameter validation
  2. Path safety checks
  3. Permission management
  4. Audit logging
  5. Execution verification

### 🎨 User Experience

- **Beautiful Terminal UI** - Rich colors, panels, and formatting
- **Real-time Streaming** - See AI thinking in real-time
- **Clean Output** - No markdown symbols, just readable text
- **Command History** - Navigate previous commands
- **Status Indicators** - Clear connection and system status

---

## Usage Guide

### Available Commands

**System Commands**:
- `help` - Show all commands
- `status` - Show system status
- `tools` - List available tools
- `permissions` - Show current permissions
- `history` - Show execution history
- `clear` - Clear chat history
- `exit` / `quit` - Exit Evo-AI

**Quick Actions**:
```
system info              - Show hardware specs
open notepad             - Launch application
list files               - List current directory
running processes        - Show active processes
take screenshot          - Capture screen
```

**Natural Language**:
```
hi / hello                                    - Greet Evo-AI
tell me about python                          - Ask questions
how much memory do you use?                   - Check Evo-AI's resource usage
create a file called test.py with hello world - File operations
search for python files                       - Search files
open youtube                                  - Open websites
open chrome and search for AI tutorials       - Compound instructions
```

### Compound Instructions

Evo-AI can execute multiple commands in sequence with improved deterministic parsing:

**Supported Connectors** (9 types):
- "and" - `open chrome and search youtube`
- "then" - `open notepad then create file`
- ", and" - `open chrome, and search youtube`
- ", then" - `open chrome, then search youtube`
- ", after that" - `open chrome, after that search youtube`
- "and then" - `open chrome and then search youtube`
- ", and then" - `open chrome, and then search youtube`
- Plain comma - `open chrome, search youtube, close chrome`

**Realistic Windows Workflows**:
```
open file explorer and go to downloads and open report.pdf
open notepad then create test.txt in documents
open chrome, then search youtube, then close chrome
open settings and show system info
open explorer, find report.pdf from desktop, then open it
```

**Features**:
- Case-insensitive parsing
- Mixed separator support
- Extra whitespace handling
- Order preservation
- Duplicate removal
- Leading/trailing connector cleanup

**Execution**:
- Sequential execution (step 1, then step 2, etc.)
- Immediate stop on failure
- Verified execution (pre-check + post-check)
- Clear success/failure reporting

### Registered Tools

**File Operations (5)**:
- `list_directory` - List files and folders
- `read_file` - Read file contents
- `write_file` - Write to a file
- `create_file` - Create new file
- `search_files` - Search for files by pattern

**System Information (3)**:
- `get_system_info` - Hardware and system info
- `get_network_info` - Network information
- `get_self_info` - Evo-AI's own resource usage

**Process Management (2)**:
- `list_processes` - List running processes
- `kill_process` - Terminate a process

**Application Control (1)**:
- `open_application` - Launch an application

**Media (1)**:
- `take_screenshot` - Capture screen

**Browser (2)**:
- `open_website` - Open URL in browser (40+ popular sites)
- `search_web` - Search on Google/Bing

**Clipboard (2)**:
- `get_clipboard` - Read clipboard contents
- `set_clipboard` - Write to clipboard

---

## Development

### Project Structure

```
Evo-AI_mogwai_local/
├── cli/
│   └── Evo-AI_cli.py              # Terminal interface
├── core/
│   ├── brain.py                 # Pure logic orchestrator
│   ├── reasoning.py             # Intent detection (+ resolution pipeline)
│   ├── planner.py               # Compound instruction handler
│   ├── executor.py              # Action execution
│   ├── verifier.py              # Execution verification
│   ├── environment.py           # OS detection & path resolution
│   ├── llm_client.py            # Ollama integration
│   ├── memory.py                # Conversation history
│   ├── action_parser.py         # LLM response parsing
│   ├── tools.py                 # System operations
│   ├── tool_registry.py         # Tool registration
│   ├── safety_validator.py      # Path/command safety
│   ├── permission_manager.py    # Permission management
│   ├── browser_automation.py    # Browser control
│   ├── system_prompt.py         # LLM system prompt
│   ├── input/                   # 🔥 NEW: Input normalization
│   │   ├── __init__.py
│   │   └── input_normalizer.py  # Typo correction + alias expansion
│   └── resolution/              # 🔥 NEW: Target resolution pipeline
│       ├── __init__.py
│       └── target_resolver.py   # Website / app / web-search routing
├── interfaces/
│   └── voice/                   # Voice assistant (Windows)
├── config/
│   ├── permissions.json         # Permission settings
│   ├── permission_audit.jsonl   # Audit log
│   ├── personality.json         # AI personality
│   ├── settings.json            # App settings
│   └── system_paths.json        # Protected paths
├── tests/
│   ├── test_action_parser.py
│   ├── test_environment.py
│   ├── test_integration.py
│   ├── test_safety_validator.py
│   ├── test_tool_registry.py
│   └── test_verifier.py
├── logs/                        # Session logs
├── .env                         # Environment variables
├── requirements.txt             # Python dependencies
├── pytest.ini                   # Test configuration
├── README.md                    # Project overview
└── ARCHITECTURE.md              # This file
```

### Adding New Tools

1. **Define Tool Function** in `core/tools.py`:
```python
def my_new_tool(self, param1: str, param2: int = 10) -> str:
    """Tool description."""
    # Implementation
    return result
```

2. **Register Tool** in `_register_all_tools()`:
```python
registry.register_tool(ToolMetadata(
    name="my_new_tool",
    description="What the tool does",
    function=self.my_new_tool,
    parameters=[
        ToolParameter(name="param1", type="string", required=True),
        ToolParameter(name="param2", type="integer", required=False, default=10)
    ],
    risk_level=RiskLevel.SAFE,
    permissions_required=["read_system_info"],
    os_support=["windows", "linux", "darwin"],
    category="system"
))
```

3. **Tool is automatically available** - no executor changes needed!

### Adding New Interfaces

The Brain is interface-agnostic. Create any interface:

```python
from core.brain import Brain
from core.reasoning import Reasoner
from core.executor import Executor
from core.llm_client import LLMClient
from core.memory import Memory

# Initialize brain
brain = Brain(
    reasoner=Reasoner(),
    executor=Executor(),
    llm_client=LLMClient(),
    memory=Memory()
)

# Your custom I/O
while True:
    user_input = your_input_method()      # Custom I/O
    response = brain.process(user_input)  # Same brain!
    your_output_method(response)          # Custom I/O
```

---

## Testing

### Run All Tests

```bash
python -m pytest tests/ -v
```

### Run Specific Test Suite

```bash
python -m pytest tests/test_environment.py -v
python -m pytest tests/test_verifier.py -v
python -m pytest tests/test_integration.py -v
```

### Test Coverage

- **Action Parser**: 7 tests
- **Environment Manager**: 16 tests
- **Integration**: 5 tests
- **Planner**: 32 tests (NEW)
- **Safety Validator**: 8 tests
- **Tool Registry**: 6 tests
- **Verifier**: 19 tests

**Total**: 93 tests, all passing

---

## Configuration

### Environment Variables (`.env`)

```bash
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2:latest
```

### Permissions (`config/permissions.json`)

```json
{
  "open_file": true,
  "write_file": false,
  "open_app": true,
  "open_browser": true,
  "take_screenshot": true,
  "read_system_info": true,
  "run_code": false
}
```

### Protected Paths (`config/system_paths.json`)

```json
{
  "protected_directories": [
    "C:\\Windows",
    "C:\\Program Files",
    "/System",
    "/usr/bin"
  ]
}
```

---

## Performance

### Speed Benchmarks

| Operation | Speed | Example |
|-----------|-------|---------|
| Fast Path | < 10ms | system info, open app |
| Pattern Match | < 10ms | open youtube, list files |
| LLM Response | 2-10s | conversations, explanations |
| Streaming | Real-time | Word-by-word display |
| Verification | < 11ms | Pre-check + post-check |

### Resource Usage

- **Evo-AI**: 25-50 MB RAM
- **Ollama (idle)**: 30-100 MB RAM
- **Ollama (active)**: 1.5-2.5 GB RAM
- **Disk space**: ~2 GB total
- **CPU**: <1% idle, 20-80% when generating (2-10s)

---

## Architecture Principles

### 1. Separation of Concerns

- **Brain**: Pure logic, no I/O
- **Interfaces**: Pure I/O, no logic
- **Core**: Specialized components with single responsibilities

### 2. Registry-Based Design

- **Before**: 20+ elif blocks in executor
- **After**: Single execution path, O(1) lookup
- **Benefit**: 77% reduction in complexity

### 3. Deterministic Verification

- **No LLM-based verification** - fast and reliable
- **Actual state changes** - not just string checking
- **Immediate failure detection** - stop on first error

### 4. Cross-Platform Compatibility

- **OS-agnostic APIs** - works on Windows, macOS, Linux
- **Environment awareness** - automatic OS detection
- **Native paths** - uses OS-specific standard paths

### 5. Security by Design

- **Multi-layer safety** - validation → paths → permissions → audit
- **Explicit permissions** - user approval required
- **Protected directories** - prevents system file modifications
- **Audit logging** - track all actions

---

## What Makes This Special?

1. **True Offline Operation** - Unlike cloud assistants, runs entirely on your machine
2. **ChatGPT-Quality Responses** - Natural and helpful, not robotic
3. **System Integration** - Actually controls your computer
4. **Hybrid Intelligence** - Smart routing for speed and capability
5. **Environment Aware** - Cross-platform OS detection and path resolution
6. **Verified Execution** - Eliminates false positives with strict verification
7. **Self-Awareness** - Can answer questions about its own resource usage
8. **Beautiful Terminal** - Modern UI with colors and streaming
9. **Privacy Focused** - All data stays on your computer
10. **Production Ready** - Comprehensive testing, error handling, and documentation

---

## Interfaces

### Terminal Interface (CLI)

**Location**: `cli/Evo-AI_cli.py`

**Features**:
- Rich terminal UI with colors and formatting
- Command history navigation
- Session logging
- Execution gating with plan preview
- User confirmation for actions

**Usage**:
```bash
python cli/Evo-AI_cli.py
```

**Flow**:
1. User enters command
2. Brain generates plan (no execution)
3. CLI displays plan preview (steps, risk, permissions)
4. User confirms (y/n)
5. Brain executes plan if confirmed
6. CLI displays result

**Conversational queries** (greetings, questions) skip confirmation and execute immediately.

### Windows Overlay (GUI)

**Location**: `os_overlay/`

**Architecture**:
```
User Input
    ↓
OverlayWindow (Pure UI)
    ↓
OverlayController (Coordinator)
    ↓
Brain.generate_plan() → StructuredPlan
    ↓
User Approval
    ↓
Brain.execute_plan() → ExecutionResult
    ↓
Display Result
```

**Files**:
- `main.py` - Entry point, initializes Brain and starts UI
- `overlay_window.py` - Pure UI layer (NO AI logic, NO Brain imports)
- `controller.py` - Connects UI to Brain, handles threading

**Features**:
- Minimal Tkinter-based UI
- Execution gating (plan preview before execution)
- Threading (UI never freezes)
- Clean separation of concerns

**UI Components**:
- Input field (single-line entry)
- Status label (shows current state)
- Plan preview area (ScrolledText)
- Approve button (green, executes plan)
- Cancel button (red, resets UI)

**Usage**:
```bash
cd os_overlay
python main.py
```

**Workflow**:
1. Type command in input field
2. Press Enter → Plan generated (no execution)
3. Review plan in preview area (steps, risk, permissions)
4. Click Approve → Plan executed
5. View result in preview area

**Threading Model**:
- Main thread: Tkinter UI
- Background threads: Plan generation, execution
- Communication: `root.after()` for thread-safe updates
- No polling loops, event-driven architecture

**Constraints Compliance**:
- Did NOT modify Brain internals
- Did NOT modify any core components
- This is ONLY a UI wrapper
- No polling loops
- No background auto-execution
- No bypass of confirmation
- Only standard Tkinter (no new dependencies)

---

## Execution Gating

### Overview

Evo-AI supports execution gating - separating plan generation from execution to give users control.

### Brain Methods

**`generate_plan(text: str) -> StructuredPlan`**
- Generates plan WITHOUT execution
- Analyzes request and builds plan structure
- Computes risk level and extracts permissions
- Returns StructuredPlan (pure data container)

**`execute_plan(plan: StructuredPlan) -> ExecutionResult`**
- Executes a previously generated plan
- Iterates through steps with verification
- Stops immediately on failure
- Returns ExecutionResult with success status

**`process(text: str) -> str`**
- Legacy method for backward compatibility
- Generates plan and executes immediately
- Used by older code and tests

### Data Structures

```python
@dataclass
class StructuredPlan:
    steps: List[Dict[str, Any]]
    risk_level: str  # "low", "medium", "high"
    permissions_required: List[str]
    confidence: float
    is_compound: bool
    is_conversational: bool
    original_text: str

@dataclass
class ExecutionResult:
    success: bool
    completed_steps: int
    total_steps: int
    message: str
    failed_step: Optional[int] = None
    error_reason: Optional[str] = None
```

### Risk Assessment

- **Low**: Read-only operations (system info, list files)
- **Medium**: Write operations (create file, open app)
- **High**: Destructive operations (delete file, kill process)

### User Control

- Preview plan before execution
- Explicit confirmation required (except conversational queries)
- Cancel anytime
- Clear success/failure reporting

### Backward Compatibility

- `process()` method still works
- All existing tests pass
- No breaking changes

---

## License

MIT License

---

**Made with ❤️ for local-first AI**

**Version:** 2.0.0  
**Status:** Production Ready  
**Platform:** Windows, macOS, Linux

**🖥️ Terminal interface, 🤖 powerful AI, 🔒 complete privacy**
