# Run Manifest

Human-readable summary. Full machine-readable detail (every file hash, every provenance
note) is in [RUN_MANIFEST.json](RUN_MANIFEST.json) — this file is a summary of it, not a
replacement for it.

Generated 2026-07-14, retrospectively, at explicit user request, to make prior runs
self-describing after the fact. **Nothing below was invented** — every field is either
pulled directly from an existing artifact, verified against source files still known to be
unchanged, reconstructed from multiple corroborating sources with the basis stated, or
explicitly marked `unknown` where none of that was possible.

## Historical scope

This is a **pre-Git provenance snapshot dated 14 July 2026**, retained as a historical
record. The repository is now version-controlled. References below to "current" source
files, timestamps and session evidence describe the reconstruction date, not the latest
checkout. Later commits do not establish the missing code revisions for earlier runs.
See [current reproducibility guidance](REPRODUCIBILITY_NOTES.md#current-workflow).
The machine-readable manifest and recorded results are unchanged.

## Reconstruction methodology

No single source is treated as sufficient on its own. Every reconstructed field is
corroborated across: **(a)** the current configuration file content, **(b)**
file-modification-timestamp evidence establishing when that content came into effect
relative to each run, **(c)** the completed run's own log content where relevant (e.g.
successful completion, observed turn counts), and **(d)** explicit verification of whether
the relevant source files were modified after the run in question. A field unsupported by
this combined evidence is marked `unknown`, not guessed.

## Version control

**At the pre-Git snapshot, no Git repository existed for this project.** The recorded
`git status` result was `fatal: not a git repository`. No contemporaneous commit hash was
available for the runs below. This describes the historical absence of version control,
not the state of the current repository.

## Provenance tags

| Tag | Meaning |
|---|---|
| `VERIFIED_FROM_LOG` | Read directly out of that run's own `.jsonl` log or `.json` output. |
| `VERIFIED_FROM_SOURCE_FILE` | `src/config.py` (and, where applicable, `src/llm_client.py`) is confirmed via file-modification-timestamp comparison to be **unchanged since before this run started**. Based on the available evidence, its current content is consistent with the configuration used for that run, rather than a reconstruction. |
| `RECONSTRUCTED_MULTI_SOURCE` | The relevant source file *was* modified after this run started, so its exact historical content can't be hash-verified (no git, no backups). Value is reconstructed from config.py's current content + the mtime timeline + this run's own log + confirmation that the invocation mechanism (`llm_client.py` reading `CONFIG.model_name`/`CONFIG.temperature`) was in place — combined, this supports the stated value as most likely, but it is labeled a reconstruction, not a fact. |
| `VERBATIM_SESSION_TRANSCRIPT` | For failed runs only — a Python traceback printed to this session's terminal and preserved verbatim in the conversation, not present in the log file itself. |
| `NOT_VERIFIED` | Could not be established from any source; marked unknown rather than guessed. |

## Completed runs (10)

`run_size`/`candidates_per_generator`/`disease_context` are **`VERIFIED_FROM_LOG`** for
every run below — parsed directly from each run's own logged prompt text (e.g. "Generate 50
... hypotheses for cholangiocarcinoma"). `model_name` (`claude-sonnet-5`), `temperature`
(`1.0`), and `max_agent_turns` (`15`) split into two tiers depending on whether
`src/config.py` was still unmodified at the time each run started:

| Run ID | System | Requested N (per role) | Actual hyps | Retrieved sources | model/temp/max_turns provenance |
|---|---|---|---|---|---|
| `baseline_20260713T193206Z` | baseline | 10 | 10 | 0 *(predates `retrieved_sources` field)* | `RECONSTRUCTED_MULTI_SOURCE` |
| `baseline_20260713T200812Z` | baseline | 10 | 10 | 70 | `RECONSTRUCTED_MULTI_SOURCE` |
| `baseline_20260713T215554Z` | baseline | 50 | 52 | 194 | **`VERIFIED_FROM_SOURCE_FILE`** |
| `multiagent_20260713T194031Z` | multiagent | 5, 5, 5 | 10 | 0 *(predates field)* | `RECONSTRUCTED_MULTI_SOURCE` |
| `multiagent_20260713T201524Z` | multiagent | 5, 5, 5 | 5 *(truncation bug)* | 193 | `RECONSTRUCTED_MULTI_SOURCE` |
| `multiagent_20260713T202858Z` | multiagent | 5, 5, 5 | 10 | 436 | `RECONSTRUCTED_MULTI_SOURCE` |
| `multiagent_20260713T220106Z` | multiagent | 25, 25, 25 | 50 *(ranking no-op bug)* | 1610 | **`VERIFIED_FROM_SOURCE_FILE`** |
| `multiagent_20260713T232713Z` | multiagent | 25, 25, 25 | 50 | 1596 | **`VERIFIED_FROM_SOURCE_FILE`** |
| `evaluation_20260713T210801Z` | evaluation | n/a | scores 10+10 | n/a | `RECONSTRUCTED_MULTI_SOURCE` |
| `evaluation_20260714T022723Z` | evaluation | n/a | scores 52+50 | n/a | **`VERIFIED_FROM_SOURCE_FILE`** |

Four runs (bold above) have `src/config.py` and `src/llm_client.py` independently confirmed
unmodified since before they started — for those, `model_name`/`temperature`/
`max_agent_turns` are directly verified from the source file, not reconstructed. The other
six predate the file edits that later changed `run_size`/`candidates_per_generator`/
`max_tokens`, so those three fields fall back to the multi-source reconstruction described
above (full per-field basis text is in `RUN_MANIFEST.json`).

**The two flagged runs are not the ones RESULTS.md is based on.** `multiagent_201524Z` (the
token-truncation bug — two of three generators silently returned 0 candidates) and
`multiagent_220106Z` (the ranking-array-stringification bug — ranking silently degraded to
a no-op) were both diagnosed via log inspection, fixed, and superseded by a clean re-run
before being used for any reported comparison. `RESULTS.md`'s n=10 table uses
`baseline_200812Z` + `multiagent_202858Z` + `evaluation_210801Z`; its n=50 table uses
`baseline_215554Z` + `multiagent_232713Z` + `evaluation_022723Z`.

### Source-code state per run

Beyond `config.py`/`llm_client.py` specifically, every one of the ~26 pipeline files has a
per-run verification list in `RUN_MANIFEST.json` (`source_file_verification`) — which files'
current hash is trustworthy for that run (unmodified since before it started) versus which
were edited afterward and are therefore unverifiable for that run. The two most recent runs
(`multiagent_232713Z`, `evaluation_022723Z`) have every pipeline file verified except
`src/logging_utils.py` (which only gained the `run_config` line afterward).

## Incomplete / failed runs (6)

Produced a `.jsonl` log but no output file — included for full transparency, not folded
into the completed-runs table above.

| Log ID | System | Events | Last event | Cause |
|---|---|---|---|---|
| `baseline_20260713T191909Z` | baseline | 1 | `agent_start` | `401 invalid x-api-key` (verbatim transcript) |
| `baseline_20260713T191951Z` | baseline | 1 | `agent_start` | `401 invalid x-api-key`, retry after pinning `base_url`; root cause was the key itself (verbatim transcript) |
| `multiagent_20260713T200814Z` | multiagent | 108 | `agent_submit` | `TypeError: can only concatenate list (not "str") to list` — model returned a bare string instead of an array (verbatim transcript); fixed in `adversarial_agent.py` |
| `multiagent_20260713T202646Z` | multiagent | 15 | `agent_submit` | **unknown** — no output produced, no verbatim cause recorded for this specific run; not guessed at |
| `evaluation_20260713T204933Z` | evaluation | 278 | `tool_call` | `anthropic.BadRequestError`: credit balance too low, at 14/20 hypotheses (verbatim transcript + log-derived progress count) |
| `evaluation_20260714T004840Z` | evaluation | 1337 | `judge_start` | `anthropic.BadRequestError`: credit balance too low, at 62/102 hypotheses (verbatim transcript + log-derived progress count) |

## The logging_utils.py change

On 2026-07-14, `RunLogger.__init__` (in `src/logging_utils.py`) was changed to write one
extra `run_config` event as the first line of every new run's log, recording
`model_name`, `temperature`, `run_size`, `candidates_per_generator`, `max_agent_turns`, and
`disease_context` (API key deliberately excluded).

**This is the only code change made for this purpose**, verified by comparing every
pipeline file's last-modified timestamp against the start time of the last completed run —
see `RUN_MANIFEST.json`'s `logging_change_explanation` for the exact verification method.
It does not touch prompts, model-call parameters, retrieval, generation, ranking, or
evaluation logic — it adds one `self.log(...)` call, executed once at logger construction,
before any real work happens.

## Smoke test

Verified the change works using a log directory entirely outside this project (this
session's private scratchpad) — **no files were added to `logs/` or `outputs/`**. Result:
**PASS**. `run_config` was the correct first line, with all six intended fields present and
the API key correctly excluded. Full detail (including the exact first-line content
produced) is in `RUN_MANIFEST.json`'s `smoke_test` section.
