# Orbit modes

Orbit is a user-directed AI shell assistant. A mode sets how much context and
generation it can use; it never authorizes extra commands, file edits or audits.
The **Mode** selector is in the Orbit panel. **Modes...** edits every preset and
can duplicate/remove profiles, including profiles with your own names. Saving
persists across restarts and applies to new tasks. An existing task retains its
selected mode, provider configuration and approval flow.

| Setting | Balanced default | High default |
| --- | ---: | ---: |
| Estimated prompt tokens per request | 4,500 | 32,000 |
| Maximum generated tokens per request | 768 | 4,096 |
| Recent conversation turns sent | 3 | 12 |
| Files inspected per task | 3 | 16 |
| Characters per file | 4,000 | 16,000 |
| Planning decisions / execution steps | 4 | 8 |
| Inspection passes per task | 2 | 3 |
| Prompt style | Compact | Full |

These are editable starting values, not branches keyed to the strings `Balanced`
or `High`. The planner uses the chosen profile's fields. It never increases them
because the user says "detailed", omits "briefly", or submits a difficult task.

The compact internal prompt asks for practical, concise shell assistance. For
"Explain this project", it requests purpose, stack, entry point and main folders
in a few useful bullets, using README, manifest and entry-point evidence. The
full prompt allows relevant architecture, file relationships and tradeoffs when
requested. Both include the actual numeric limits, remaining task budget,
instructions to finish valid JSON within the ceiling, and the same routing,
workspace, exact-path, untrusted-content and approval constraints. A short request
still gets a short answer in High mode. No mode turns Orbit into an autonomous
development engine.

Context packing prioritizes execution evidence and labelled file excerpts over
older history. Reading is capped per file and per task, including related-file
inspections. Oversized context is visibly marked in the model prompt. Stored
conversation history is not deleted when reducing the turns sent. Whole command
catalog entries are retained so executable syntax is never cut in half.

Output caps are passed to all providers: Groq `max_completion_tokens` (through
`extra_body` for compatibility with older installed SDKs), Gemini
`max_output_tokens`, and Ollama `num_predict`. A provider response stopped by the
output limit is discarded before action execution and does not cause automatic
fallback with a larger budget. Existing files are not offered as full replacements
when their inspection context was truncated. Choose a narrower edit or increase
the selected limits explicitly.

Prompt tokens use a local estimate of three UTF-8 bytes per token, not the exact
provider tokenizer. Output caps include the JSON envelope and can include model
reasoning. The prompt ceiling is per request, not a per-minute or daily quota;
provider retries and fallbacks can make additional requests. Mode limits cannot
guarantee that a shared API key has quota remaining. Existing server cooldowns,
configured provider fallback and cancellation continue to apply. Limits above a
model's supported output/context capacity can still be rejected by that provider.

## Environment configuration

Desktop saved mode preferences take precedence over environment defaults. The
Telegram planner uses environment defaults; desktop settings do not change its
configuration or add the desktop execution loop.

```dotenv
AI_MODE=Balanced
AI_MODES_FILE=D:\configs\orbit-modes.json
```

`AI_MODES_FILE` is optional. When present, it replaces the starting profile list
with a JSON array. Omitted profile fields inherit Balanced starting values.
`AI_MODE` defaults to the first profile if unset. Invalid values, duplicate names,
missing files and unknown selected profiles produce configuration errors.

```json
[
  {
    "name": "Balanced",
    "prompt_tokens": 4500,
    "output_tokens": 768,
    "history_turns": 3,
    "max_files": 3,
    "file_chars": 4000,
    "max_steps": 4,
    "inspection_passes": 2,
    "compact_prompt": true
  },
  {
    "name": "My detailed shell",
    "prompt_tokens": 16000,
    "output_tokens": 2048,
    "history_turns": 6,
    "max_files": 8,
    "file_chars": 10000,
    "max_steps": 6,
    "inspection_passes": 3,
    "compact_prompt": false
  }
]
```

Provider parameter references: [Groq API](https://console.groq.com/docs/api-reference),
[Gemini generation config](https://ai.google.dev/api/generate-content),
[Ollama generation options](https://docs.ollama.com/modelfile).

## Local verification

```powershell
python -m pytest tests/test_orbit_modes.py tests/test_ai_providers.py tests/test_provider_runtime.py tests/test_workspace_agent.py tests/test_agent_run.py tests/test_desktop_settings.py -q -p no:cacheprovider
```

These use mocked providers and an offline HTTP transport, not live API keys.
For a manual desktop check, select Balanced and ask "Explain this project";
then select High and repeat. Duplicate/edit a profile, restart RiftShell and
check persistence. Provider quota and response quality require a live test.
