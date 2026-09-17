# Orbit command extraction

Orbit has a local, English-first command extractor with common Hinglish forms.
It does not call a model, inspect files, or execute anything. Clear single-step
requests take the existing action, safety, approval, and terminal result path.
Provider SDKs are initialized only when a request needs model reasoning.

```text
User request
  -> normalize polite framing (preserve literal path contents)
  -> indexed phrases / compiled whole-request grammars
  -> registered-command + argument validation
      unique exact match -> Orbit action -> safety / approval -> terminal -> result
      ambiguous match    -> Orbit reasoning with unconfirmed candidates
      no match           -> existing conversation / inspection / code-writing flow
```

No match is silent: no extra AI call, command warning, or additional prompt text.
The normal Orbit conversation can still use the configured model. Multi-step
requests remain in the existing result-driven planning loop. Single-step local
actions set `continue_after_result=False`; completion uses the actual command
result without a second model call.

## Supported examples

| Request | Extracted command |
| --- | --- |
| Could you please show my current directory? | `where` |
| List the files in this folder | `files` |
| Show git status | `gstatus` (when the Git plugin is registered) |
| Show running processes | `processes` |
| Go to src | `cd src` |
| Create a folder named "My Reports" | `makefolder "My Reports"` |
| Copy "My Reports/Notes.TXT" to "Archive/Notes.TXT" | `duplicate "My Reports/Notes.TXT" "Archive/Notes.TXT"` |
| Delete file notes.txt | `delete confirm notes.txt` (approval still required) |
| Show the first 10 lines of notes.txt | `head notes.txt 10` |
| files dikhao | `files` |
| src mein jao | `cd src` |
| current folder batao | `where` |
| reports folder banao | `makefolder reports` |

Also covered: folder listings, home/parent navigation, clearing the terminal,
system/memory/disk/network information, history, time/date, user/computer identity,
plugin/version/help listings, Git inspection, empty-file creation, move/rename,
opening named paths, last lines, and ping. Registered bare command names and
`/cmd <command>` retain their existing explicit-command behavior.

## Deliberate abstention

- `What does delete do?`, `files mat dikhao`, and `Don't delete notes.txt` are not
  local execution requests.
- `List files and then check git status` needs multi-step reasoning.
- `Write a calculator in app.py` keeps file inspection, code generation, diff
  review, approvals, and backups. `Create an empty file app.py` can be local.
- `Read notes.txt` keeps Orbit's existing file-understanding flow.
- Pronouns such as `it`/`that`, unfamiliar wording, missing arguments, and
  conflicting complete matches are not guessed. Unquoted multiword paths must
  go through reasoning; quote them for deterministic extraction.
- Paths retain case, internal spacing and backslashes. Relative paths are relative
  to the active session, not inferred Windows special folders. Environment
  variables, wildcards, shell operators, and quoted prose are not interpreted as
  local execution syntax. Use the explicit command path when needed.

Matching covers defined English/Hinglish constructions, not every paraphrase or
language. Scores of `1.0` on rules mean exact grammar matches, not measured ML
probabilities. False positives matter more than maximizing automatic coverage.

## Adding commands and plugins

The extraction engine is in `ai/command_intent.py`; built-in declarations are in
`ai/command_intents.py`. `IntentRule` separates the command name, literal arguments,
typed captures, response message, and language patterns. Phrase lookup is indexed;
regexes are compiled at extractor construction and optionally indexed by their
first word with `starts`. Input is bounded to 4096 characters.

Plugins can explicitly supply declarations through existing registry metadata:

```python
from ai.command_intent import IntentRule

registry.register(HealthCommand(), extra={
    "orbit_intents": (
        IntentRule(
            intent="service_health",
            command="health",
            message="I will check service health.",
            phrases=("check service health", "service health dikhao"),
        ),
    ),
})
```

The command must be registered. Each metadata declaration must belong to its
owning command. Descriptions and aliases are not automatically promoted to
executable natural-language patterns. Plugin declarations are trusted Python
code and need the same review as their command implementation.

For arguments, use named regex captures, `slots=(("target", "path"),)` and
`arguments=("{target}",)`. Supported slot types are `path`, `file_path` (requires
path-like syntax or quotes), `integer` (1–10000), and `host`. Matching uses
`fullmatch`, never a substring. Overlapping rules producing different commands
return `ambiguous`; they are not resolved by registration order.

## Future ML/LLM adapters

`IntentExtractor.extract(text) -> Extraction` is the replaceable interface, passed
as `AgentPlanner.intent_extractor`. Results carry a status and structured
`CommandCandidate` objects with intent, command name, arguments, provenance and
confidence. A composition adapter can run rules first and a local classifier or
semantic matcher only when appropriate.

Only unique, validated `source="rules", confidence=1.0` candidates currently take
the automatic path. Future ML candidates must use their real source label; Orbit
receives up to three valid candidates as unconfirmed hints and decides from the
full request. A low-confidence/no-command result should return `Extraction()`.
Do not label a model guess as a rule match. Adding automatic ML execution requires
a separate confidence/evaluation policy; the current interface does not silently
enable it. Safety and approval checks remain downstream of all extractors.

## Verification

```powershell
python -m pytest tests/test_command_intent.py tests/test_agent_run.py tests/test_workspace_agent.py tests/test_ai_providers.py -q -p no:cacheprovider
python -m pytest -q -p no:cacheprovider
```

Tests cover English/Hinglish matches, negation and conversational abstention,
conflicts, plugin registration, literal paths, unchanged approval requirements,
zero provider calls for matched requests, normal model routing for misses,
future adapter validation, and actual shell operations in an isolated directory.
Live desktop latency and provider response times require a separate manual run.
