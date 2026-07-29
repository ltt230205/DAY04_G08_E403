# Demo Version Evidence

Use these exact run files during demo. Do not open the Gemini v0 files as final
metric evidence because they contain provider quota errors.

## One-line story

The original prompt/tool declarations allowed guessing, automatic send, and tool
calls for out-of-scope requests. After tightening the prompt and tool
declarations around clarification, confirmation boundaries, no-tool cases, and
format routing, base eval improved from 75% to 100%, and group eval improved
from 60% to 100%.

## Runs to open

| Demo point | Open this run JSON | What to show |
|---|---|---|
| v0/provider setup caveat | `runs/v0_B_base_gemini_20260729T151417161667.json` | Gemini baseline attempted, but `provider_error_cases=17` due quota, so this is not valid metric evidence. |
| v1 baseline with OpenRouter | `runs/v1_B_base_openrouter_20260729T154044120855.json` | Valid run: `provider_error_cases=0`, `passed_cases=15/20`, `case_accuracy=0.75`. |
| v2 repeated baseline check | `runs/v2_B_base_openrouter_20260729T154133103153.json` | Same metric as v1: `15/20`, showing no improvement when artifacts did not meaningfully change. |
| fix round evidence | `runs/v3_B_base_openrouter_20260729T155631771314.json` | After boundary/no-tool/clarify fixes: `19/20`, only `R10_missing_handle` still failed. |
| final base proof | `runs/v3_B_base_openrouter_20260729T155834213223.json` | Final base: `20/20`, all routing/args/multiturn metrics `1.0`. |
| group before fix | `runs/v3_B_group_openrouter_20260729T154717596923.json` | Group eval before final prompt/tool cleanup: `6/10`, `case_accuracy=0.6`. |
| final group proof | `runs/v3_B_group_openrouter_20260729T160725159669.json` | Final group: `10/10`, all metrics `1.0`. |

## What changed

### v0 / Gemini setup attempt

Open:

```text
runs/v0_B_base_gemini_20260729T151417161667.json
```

Say:

```text
This run proves the eval command executed, but it is not valid for metric
comparison because Gemini hit quota.
```

Show in JSON:

```text
summary.provider_error_cases = 17
summary.measured_cases = 3
```

Main evidence:

```text
429 RESOURCE_EXHAUSTED
```

### v1 / first valid baseline

Open:

```text
runs/v1_B_base_openrouter_20260729T154044120855.json
```

Say:

```text
We switched to OpenRouter so all 20 cases were measured. The baseline passed
15/20. The failures show the model still guessed missing info, sent without
confirmation, and called tools for out-of-scope tasks.
```

Show:

```text
summary.provider_error_cases = 0
summary.passed_cases = 15
summary.case_accuracy = 0.75
summary.failure_counts = {
  "out_of_scope": 2,
  "missing_info": 2,
  "wrong_boundary": 1
}
```

Failed cases to click/search inside JSON:

```text
R08_out_of_scope
R10_missing_handle
R11_missing_url
R12_confirm_before_send
R14_out_of_scope_coding
```

### v2 / no real improvement yet

Open:

```text
runs/v2_B_base_openrouter_20260729T154133103153.json
```

Say:

```text
This run was useful because it showed that simply rerunning or making
insufficient artifact changes did not improve the agent. The same five failures
remained, so the next fix had to target the prompt/tool contract directly.
```

Show:

```text
summary.provider_error_cases = 0
summary.passed_cases = 15
summary.case_accuracy = 0.75
```

Important note:

```text
Do not claim v2 improved over v1. It did not. It is evidence that the first
attempt was not enough.
```

### Fix round / 95%

Open:

```text
runs/v3_B_base_openrouter_20260729T155631771314.json
```

Say:

```text
After explicitly forbidding automatic send, forcing clarify for missing URLs,
and blocking out-of-scope tool calls, base accuracy improved to 19/20. The only
remaining error was the empty social_search query for a missing tweet topic.
```

Show:

```text
summary.passed_cases = 19
summary.case_accuracy = 0.95
summary.failure_counts = {"missing_info": 1}
```

Failed case:

```text
R10_missing_handle
actual_tool_calls = social_search(query="")
```

### Final base / 100%

Open:

```text
runs/v3_B_base_openrouter_20260729T155834213223.json
```

Say:

```text
The final fix added a rule that social_search must never be called with an empty
query. If a tweet request has no account and no topic, the agent must clarify.
That cleared the last base failure.
```

Show:

```text
summary.total_cases = 20
summary.measured_cases = 20
summary.provider_error_cases = 0
summary.passed_cases = 20
summary.case_accuracy = 1.0
summary.tool_routing_accuracy = 1.0
summary.argument_accuracy = 1.0
summary.multiturn_accuracy = 1.0
summary.failure_counts = {}
```

### Group eval / before and after

Open before:

```text
runs/v3_B_group_openrouter_20260729T154717596923.json
```

Show:

```text
summary.passed_cases = 6
summary.case_accuracy = 0.6
```

Failed cases:

```text
G01_format_digest_routing
G04_confirm_before_send_even_if_urgent
G05_out_of_scope_translation
GM04_boundary_even_if_user_insists
```

Open after:

```text
runs/v3_B_group_openrouter_20260729T160725159669.json
```

Show:

```text
summary.total_cases = 10
summary.measured_cases = 10
summary.provider_error_cases = 0
summary.passed_cases = 10
summary.case_accuracy = 1.0
summary.tool_routing_accuracy = 1.0
summary.argument_accuracy = 1.0
summary.multiturn_accuracy = 1.0
```

## Demo script

1. Open the Gemini v0 run and say it is not valid metric evidence because the
   provider hit quota.
2. Open the v1 OpenRouter run and show the first valid baseline: 15/20.
3. Open the v2 OpenRouter run and show no improvement: still 15/20.
4. Open the 95% fix run and show only `R10_missing_handle` remained.
5. Open the final base run and show 20/20.
6. Open group before/after and show 6/10 to 10/10.

## Commands if asked

```powershell
python run_eval.py --provider openrouter --version v3 --suite base --eval-cases data/eval_base.json
python run_eval.py --provider openrouter --version v3 --suite group --eval-cases data/eval_group.json
python scripts/parse_runs.py runs/ --output analysis/base_runs.csv
```
