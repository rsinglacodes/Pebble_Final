# Pebble

Pebble turns a JSON request into a narrated Manim explainer video for a LeetCode
solution or an algorithm: request -> validated Manim script + narration +
solution, rendered scene by scene, narrated with Azure Speech, muxed and
stitched into a single `final.mp4`.

## Setup

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# system packages (macOS)
brew install pkg-config cairo pango ffmpeg
# LaTeX is optional. If missing, Pebble forbids MathTex/Tex/Axes/... automatically.
```

Copy `.env.example` to `.env` and fill in the Azure values. Never commit `.env`.

## Commands

```bash
# environment + config + live LLM ping
python run_local.py --doctor

# also synthesis one phrase and render one scene for real
python run_local.py --doctor --deep

# full pipeline (generate -> narrate -> render -> mux -> stitch)
python run_local.py samples/two_sum.json
python run_local.py samples/buggy_two_sum.json --job-id buggy_demo

# console verbosity: -v (DEBUG) / -q (banners, warnings and the summary only)
python run_local.py samples/two_sum.json -q

# generation only
python run_local.py samples/dijkstra_algorithm.json --stage generate

# cost history across runs
python run_local.py --costs

# tests
python -m pytest -q
```

Runtime output lands in `workspace/<job_id>/` (git-ignored): `final.mp4`,
`result.json`, `metadata.json` (including the `cost` block), `pipeline.log`,
`animation.py` (the generated script), `animation_render.py` (same text with the
helper import on line 1), `pebble_helpers.py`, `pebble_targets.json`,
`animation.attempt_N.py` (render repairs), `generation.json`,
`llm/attempt_N_{prompt,response}.txt`, `scenes/` (silent scene videos),
`audio/` (narration wavs), `muxed/` (per-scene muxed clips), `media/` (manim
working dirs), `render_logs/` (full manim output per scene), `frames/`
(spot-check frames). `workspace/cost_log.jsonl` collects one line per run.

## Pacing

Narration is synthesized **before** rendering. Each scene's audio duration +
0.35s hold is written to `pebble_targets.json`, and every scene ends with
`finish_scene(self)` (provided by `pebble/templates/pebble_helpers.py`): the
helper holds the finished picture until the narration ends and then fades out.
The script is never asked to guess durations, so a scene cannot freeze on a
blank frame while the voice keeps talking.

## Cost

`metadata.json -> cost` and the printed table use the prices in `.env`
(`LLM_INPUT_PRICE_PER_1M`, `LLM_OUTPUT_PRICE_PER_1M`, `TTS_PRICE_PER_1M_CHARS`,
optional `USD_TO_INR`). The defaults are estimates: check them against the
Azure pricing pages. Blob storage, egress and laptop compute are not counted.

## Input payload

```json
{
  "question": {"id": 1, "slug": "two-sum", "title": "Two Sum"},
  "solution": {"code": "...", "programming_language": "python", "validated": true},
  "preferences": {"explanation_language": "English", "explanation_style": "beginner_friendly"}
}
```

`question.id`/`slug` may be null or empty (then the request is an `algorithm`),
`solution` may be null, extra fields are ignored.
