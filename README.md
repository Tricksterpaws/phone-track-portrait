# phone-track-portrait

Planar corner track of the phone glass in the portrait plate.

This repository is portrait only. The track JSON is the only contract with a compositor. This repo does not include compositor, WebGL, or export code.

## Incomplete import

The portrait dumps archive (`phone-track-portrait-dumps-2.zip`) and the portrait plate did not arrive with the files available when this repo was built. Only the portrait half of the combined landscape-and-portrait dump is present: `fixtures/portrait/`.

**Not yet in this repo** (required for a full, reproducible five-pass run):

- `plate_portrait.mp4` (pinned sha256 `2259b5cdaa1f9ac6d182e6dbeb3b36d06ccfa461685fb250bfaf07738f26cb02`)
- `portrait/track2.py`, `refine.py`, `finalize.py`, `finalize2.py`, `export_track.py`
- intermediates (`raw2`, `ref`, `oriented`, `final`)
- `tracks/portrait.json`
- `qa/`

Until those files are added, the five-pass solve cannot be reproduced from this repo alone, and `compare_track.py` has no shipped oracle to exit 0 against. Do not use a file named `public/plate-portrait.mp4` in place of the pinned plate.

When the pinned plate is present:

```bash
sha256sum plate_portrait.mp4
# expected: 2259b5cdaa1f9ac6d182e6dbeb3b36d06ccfa461685fb250bfaf07738f26cb02
```

## JSON contract

When `tracks/portrait.json` is present, it is the shipped regression oracle. The contract is:

| Field | Value |
| --- | --- |
| `width` × `height` | 1080 × 1440 pixels |
| `fps` | 24 |
| `frameCount` | 583 |
| `frames` | 583 entries, each 8 numbers: corners **TL, TR, BR, BL** in pixels, `[x0,y0,x1,y1,x2,y2,x3,y3]` |
| `keyFrom` | 48 |
| `screenAspect` | glass width / height (fixture metadata: 0.4871) |
| `cornerRadius` | corner radius as a fraction of glass height (fixture metadata: 0.0607) |
| `slack` | per-frame; how far green spills past the tracked glass, in UV units, clamped |

`slack` is part of the portrait contract. The landscape track has no `slack` field; do not remove it here to match landscape, and do not add it to landscape to match portrait.

`keyFrom` is the first frame where the green screen is treated as a keyable fill.

These width, height, fps, frame count, `keyFrom`, `screenAspect`, and `cornerRadius` values are taken from `fixtures/portrait/expected.json`. Confirm them against `tracks/portrait.json` once that file is in the repo.

## Reproduce (once the five-pass scripts and plate are in the repo)

Paths must stay relative to this repository root. Do not hardcode a machine-absolute work directory.

The intended sequence is the five-pass run from this repo alone:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Exact invocation depends on the missing portrait/*.py scripts.
# Each pass should read and write paths under this repo (plate, intermediates,
# work/, tracks/ as documented by those scripts). Never overwrite the shipped
# tracks/portrait.json with a re-solve by default.

python3 compare_track.py work/portrait.json
python3 compare_track.py tracks/portrait.json
```

This README will be updated with the exact commands after the missing scripts are added and a dry run has been timed.

## Checks

`compare_track.py` always runs both checks. A smooth track can still be wrong.

### Fixture check (exit code)

Compares the solved track to `fixtures/portrait/expected.json`. Exit 1 if any fixture corner moves by more than **1.5px**, or if a fixture frame is missing. This is the check that catches a wrong-but-smooth track.

Fixture frames: 0, 48, 120, 196, 220, 258, 360, 440, 520, 575.

### Motion check (informational)

Flags frame-to-frame corner jumps (default flag threshold 5px). This check does **not** affect the exit code. A lower max jump is not proof the track is right.

## Layout

```
plate_portrait.mp4          pinned portrait plate (missing)
portrait/                   five-pass solvers (missing)
intermediates / work/       raw2, ref, oriented, final (missing)
tracks/portrait.json        shipped oracle (missing)
fixtures/portrait/          expected quads + source frames (present)
qa/                         (missing)
compare_track.py
requirements.txt
```
