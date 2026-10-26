# Reproducibility Notes

## Historical scope: pre-Git snapshot of 14 July 2026

The reconstruction below describes the evidence available before Git was initialized.
The project is now version-controlled; this does not recover earlier overwritten code or
retroactively assign commits to the historical runs. References below to "current" source
files and "now" mean the files at the time of that reconstruction, not today's checkout.
The [run manifest](RUN_MANIFEST.md) preserves the dated provenance and uncertainty tags.

## The limitation

Runs completed before 2026-07-14 are not self-describing: their `.jsonl` logs record every
prompt, tool call, and retrieval, but never the model name, temperature, or run-size
settings that produced them. That metadata only existed in `src/config.py` at the moment
each run executed. At the pre-Git snapshot, `git status` confirmed that no repository
existed; earlier states of that file had been overwritten in place by later edits with no
way to recover them byte-for-byte. Combined with `Edit`-in-place tooling (no diffs or
backups kept), this means: for any pipeline file touched *after* a given run but before now,
the exact code that actually produced that run's output is not recoverable with certainty
from the file alone.

## How it was addressed

1. **Going forward**: `src/logging_utils.py` now writes model/temperature/run-size/etc. as
   the first line of every new run's log automatically (`run_config` event), so this
   specific gap cannot recur for any future run.
2. **For past runs**: [RUN_MANIFEST.json](RUN_MANIFEST.json) / [RUN_MANIFEST.md](RUN_MANIFEST.md)
   reconstruct what can honestly be attributed to each of the 10 completed runs. No field is
   reconstructed from a single source — every reconstructed value is corroborated across:
   - the configuration file's current content,
   - file-modification timestamps establishing *when* that content came into effect
     relative to each run,
   - the completed run's own log (e.g. whether it finished successfully, how many turns it
     actually used), and
   - explicit confirmation of whether the relevant source files were modified after that
     run completed.

   This produced two honest tiers rather than one blanket "reconstructed" label:
   - **`run_size` / `candidates_per_generator` / `disease_context`** turned out to be
     **directly recoverable** for every run — they're embedded in each run's own logged
     prompt text, so these are verified from the artifact itself, not reconstructed at all.
   - **`model_name` / `temperature` / `max_agent_turns`**: for the 4 most recent runs,
     `src/config.py` (and `src/llm_client.py`, which reads those fields) is confirmed
     unmodified since before the run started. Based on the available evidence, the current
     file content is consistent with the configuration used for those runs, rather than a
     reconstruction. For the other 6 earlier runs, those files
     were edited afterward, so the exact historical value can't be hash-verified; those
     fields are labeled `RECONSTRUCTED_MULTI_SOURCE` with the full corroborating-evidence
     chain stated per field.
   - One incomplete run's failure cause could not be established from either the log or
     this session's transcript and is marked `unknown` rather than inferred. Nothing else
     was guessed.

## What's still a limitation

- **No Git history for the pre-Git runs.** Later version control cannot recover the
  overwritten states. The `VERIFIED_FROM_SOURCE_FILE` tier above relies on the recorded
  evidence that `config.py`/`llm_client.py` had not changed between certain runs and the
  14 July reconstruction; it does not verify an arbitrary later checkout.
- **Live retrieval APIs.** Even with identical code and config, re-running any script will
  hit PubMed/Europe PMC, Open Targets, CIViC, and ClinicalTrials.gov live — results (and
  therefore generated hypotheses) are not byte-for-byte reproducible run to run, only
  auditable after the fact via the full logs.

## Current workflow

Clone the existing repository using the [installation instructions](README.md#installation);
do not initialize a separate repository. For future runs, record the commit ID and any
uncommitted changes alongside the configuration and logs. Git commits track saved source
states, but do not automatically associate a run with its code revision. The historical
recommendation to initialize Git has been addressed; the pre-Git provenance gaps remain.

Full JSONL logs are local research records and are intentionally not tracked in Git, as
explained in the [repository overview](README.md#reproducibility). A clone therefore does
not include every primary log cited by the retrospective manifest.
