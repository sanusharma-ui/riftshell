# Orbit command extraction

Orbit combines the existing English/Hinglish rules with a local English semantic
extractor. A small pretrained sentence model compares unfamiliar wording with
reviewed command capabilities. Argument binding and validation are separate from
similarity scoring. The extractor does not execute commands or contact a cloud
provider. Matches use the existing action, safety, approval, and terminal path.

```text
User request
  -> normalize polite framing (preserve literal path contents)
  -> indexed phrases / compiled whole-request grammars
      unique rule match  -> registered-command / argument validation -> Orbit action
      ambiguous rules    -> Orbit reasoning with unconfirmed candidates
      rule miss          -> request guards + typed slot binding
                         -> local MiniLM semantic ranking
                         -> score / margin / capability validation
      confident match    -> Orbit action -> safety / approval -> terminal -> result
      ambiguous match    -> Orbit reasoning with unconfirmed candidates
      no match           -> existing conversation / inspection / code-writing flow
```

No match is silent: no extra AI call, command warning, or additional prompt text.
The normal Orbit conversation can still use the configured model. Multi-step
requests remain in the existing result-driven planning loop. Single-step local
actions set `continue_after_result=False`; completion uses the actual command
result without a second model call.

## Local model setup

```powershell
python -m pip install -r requirements.txt
python scripts/setup_intent_model.py
```

The installer downloads about 24 MB into `assets/intent-model/`, verifies every
file against pinned checksums, and includes the model card and Apache-2.0 license.
The model is [sentence-transformers/all-MiniLM-L6-v2](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2),
revision `1110a243fdf4706b3f48f1d95db1a4f5529b4d41`, using its quantized ONNX CPU
export. Runtime dependencies are ONNX Runtime, tokenizers and NumPy; PyTorch and
a cloud API key are not needed for extraction.

There are no automatic downloads during chat. Model initialization and capability
embeddings are cached per process. The first semantic request pays the initial
load cost; exact rule matches do not load the model. Missing/broken model assets
or dependencies leave the original rules and normal reasoning path available.
Restart after setup or after changing `RIFT_SEMANTIC_INTENTS=0` (rules only).
Packaged apps must include `assets/intent-model/`; see the README build command.

## Supported examples

| Request | Extracted command |
| --- | --- |
| Could you please show my current directory? | `where` |
| List the files in this folder | `files` |
| Show me folders | `folders` |
| Show me all the folders here | `folders` |
| Show files and folders inside this directory | `files` |
| List only directories in "My Reports" | `folders "My Reports"` |
| mujhe saare folders dikhao | `folders` |
| src ke folders dikhao | `folders src` |
| Which subdirectories exist here? | `folders` |
| Would you mind listing the available drives? | `drives` |
| Relocate notes.txt into Archive | `shift notes.txt Archive` (approval required) |
| Give me the specifications of this PC | `system` |
| Convert "hello world" to base64 | `base64 encode "hello world"` |
| Give me the bottom 5 lines from notes.txt | `tail notes.txt 5` |
| Assign shell variable MODE to "debug" | `setvar MODE debug` |
| Commit the staged changes with message "Fix bug" | `gcommit -m "Fix bug"` (approval required) |
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

Every bundled command has a reviewed semantic capability or equivalent mapping
(`goto` shares `cd`; file-based `take`/`count` requests can use `head`/`wc`).
This includes arithmetic, hashing, encoding, downloads, archives, text processing,
variables, aliases, native commands, and bundled Git/hello plugins. Coverage of a
command does not mean every option or sentence is understood. Unavailable registry
commands are excluded. New third-party plugins opt in explicitly as described below.

File and folder listings share noun and location grammars, including `here`,
`inside this directory`, `all the`, and literal paths. `files and folders` is
one listing request; `list folders and delete files` still needs reasoning.
Recursive, hidden-only, and sorted listings are not reduced to plain listings.

## Deliberate abstention

- `What does delete do?`, `files mat dikhao`, and `Don't delete notes.txt` are not
  local execution requests.
- `List files and then check git status` needs multi-step reasoning.
- `Write a calculator in app.py` keeps file inspection, code generation, diff
  review, approvals, and backups. `Create an empty file app.py` can be local.
- `Read notes.txt` keeps Orbit's existing file-understanding flow.
- Pronouns such as `it`/`that`, low-confidence wording, missing arguments, and
  conflicting complete matches are not guessed. Unquoted multiword paths must
  go through reasoning; quote them for deterministic extraction.
- Paths retain case, internal spacing and backslashes. Relative paths are relative
  to the active session, not inferred Windows special folders. Environment
  variables, wildcards, shell operators, and quoted prose are not interpreted as
  local execution syntax. Use the explicit command path when needed.

The learned layer currently focuses on short English requests. Existing Hinglish
rules remain available. No natural-language matcher guarantees every paraphrase.
Semantic requests are bounded to 1024 characters and 256 word pieces; the encoder
rejects longer input without truncating trailing instructions. Text values and
native argv must be quoted; paths with spaces must also be quoted. Unsupported
modifiers, multiple actions, uncertain targets and shell operators go to reasoning.

Semantic results need cosine similarity >= 0.64, a margin >= 0.07 over the next
valid command and conversational examples, literal argument validation, and
capability checks for distinctions such as first/last or encode/decode. A stronger
interpretation with missing arguments can veto a weaker match. Scores are not
calibrated probabilities. These thresholds are regression-tested heuristics,
not a proof that all future wording is safe or understood.

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

The semantic catalog is in `ai/semantic_catalog.py`, matching and binding are in
`ai/semantic_intent.py`, and the ONNX runtime is in `ai/intent_model.py`. Semantic
examples describe a capability; they are embedded and compared by meaning rather
than matched as exact strings. Shared layouts bind literal values in the request.

Plugins can additionally declare reviewed semantic capabilities:

```python
from ai.semantic_catalog import SemanticIntent

registry.register(HealthCommand(), extra={
    "orbit_semantics": (
        SemanticIntent(
            key="service_health",
            command="health",
            examples=("Check service health", "Inspect the service readiness status"),
        ),
    ),
})
```

The declaration must belong to the registered command. Descriptions alone never
opt a plugin into execution. Invalid schema declarations are ignored. For a single
literal argument, use `layout="one"`, `kinds=("path",)`, `arguments=("{0}",)`.
Layouts include `none`, `one`, `location`, `pair`, `search`, `lines`, `depth`, and
`range`. Argument indices define the actual command order independently of prose.
Slot kinds include path, file, integer, seconds, host, name, branch, process, text,
URL, a registered theme, arithmetic expression and explicitly quoted native argv. Native execution
and plugin effects still pass through the existing safety/approval flow.

## Adapter trust boundary

`IntentExtractor.extract(text) -> Extraction` is the replaceable interface, passed
as `AgentPlanner.intent_extractor`. Results carry a status and structured
`CommandCandidate` objects with intent, command name, arguments, provenance and
confidence. `HybridIntentExtractor` runs existing rules first, then the local
semantic layer only on a miss.

Unique validated rules retain `source="rules", confidence=1.0`. The built-in
hybrid extractor can also return validated `source="local_semantic"` candidates.
The planner checks the extractor type before allowing that route; injected
adapters cannot gain automatic execution by copying the source label. Other
learned adapters remain unconfirmed hints. A no-command result is `Extraction()`.
Safety, workspace containment and approval checks remain downstream.

The shell removes paired grouping quotes at its argument boundary so multiword
text, arithmetic and Git messages arrive as literal values. Parsing and safety
review still inspect the original command string.

## Verification

```powershell
python -m pytest tests/test_command_intent.py tests/test_agent_run.py tests/test_workspace_agent.py tests/test_ai_providers.py -q -p no:cacheprovider
python -m pytest tests/test_semantic_intent.py -q -p no:cacheprovider
python -m pytest -q -p no:cacheprovider
```

Tests cover English/Hinglish matches, negation and conversational abstention,
conflicts, plugin registration, literal paths, unchanged approval requirements,
zero provider calls for matched requests, normal model routing for misses,
future adapter validation, and actual shell operations in an isolated directory.
`tests/semantic_cases.py` keeps regression requests separate from capability
descriptions. Real-model checks cover English paraphrases across the bundled
catalog, negative/modified requests, cloud bypass, approvals and real shell
operations. They explicitly skip when the model is absent; mocked checks are
not a substitute for the real-model run.
Live desktop latency and provider response times require a separate manual run.
The exact `show me folders` request is covered through extraction, planner,
desktop worker, real folder filtering, and input unlock without continuation.
Worker tests isolate desktop settings and credentials; they do not measure
credential-store latency, native terminal startup, or a running packaged app.
