# Reproducibility Notes

## The limitation

Runs completed before 2026-07-14 are not self-describing: their `.jsonl` logs record every
prompt, tool call, and retrieval, but never the model name, temperature, or run-size
settings that produced them. That metadata only existed in `src/config.py` at the moment
each run executed — and since this project has no git repository (`git status` confirms no
`.git` exists), earlier states of that file were overwritten in place by later edits with no
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

- **No git repository.** Nothing here substitutes for actual version control. Future code
  changes will have the same problem unless the project is put under git — the
  `VERIFIED_FROM_SOURCE_FILE` tier above only works because no further edits happened to
  `config.py`/`llm_client.py` between certain runs and now; it depends on this build having
  happened inside a single continuous, memorable session, which won't hold for a project
  that spans multiple sessions or contributors.
- **Live retrieval APIs.** Even with identical code and config, re-running any script will
  hit PubMed/Europe PMC, Open Targets, CIViC, and ClinicalTrials.gov live — results (and
  therefore generated hypotheses) are not byte-for-byte reproducible run to run, only
  auditable after the fact via the full logs.
- **Recommendation**: initialize git for this project (`git init`, commit the current
  state) so that going forward, "which code produced this run" is a `git log` lookup
  instead of a manual multi-source reconstruction exercise like the one behind this
  manifest.
