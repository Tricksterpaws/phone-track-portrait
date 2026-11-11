# phone-track-portrait

Planar corner track of the phone glass in the portrait plate.

This repository is portrait only. The track JSON is the only contract with a compositor. This repo does not include compositor, WebGL, or export-to-video code.

## Pinned plate

File: [`plate_portrait.mp4`](plate_portrait.mp4)

```
sha256  2259b5cdaa1f9ac6d182e6dbeb3b36d06ccfa461685fb250bfaf07738f26cb02
```

Verify:

```bash
sha256sum plate_portrait.mp4
```

This is the exact encode the portrait track was solved on (1080×1440, 24fps, 583 frames). Do not substitute a re-encode; compression can move green edges by up to 20px around frames 450–457.

## JSON contract

`tracks/portrait.json` is the shipped regression oracle.

| Field | Value |
| --- | --- |
| `width` × `height` | 1080 × 1440 pixels |
| `fps` | 24 |
| `frameCount` | 583 |
| `frames` | 583 entries, each 8 numbers: corners **TL, TR, BR, BL** in pixels, `[x0,y0,x1,y1,x2,y2,x3,y3]` |
| `keyFrom` | 48 |
| `screenAspect` | glass width / height (shipped: 0.4871) |
| `cornerRadius` | corner radius as a fraction of glass height (shipped: 0.0607) |
| `slack` | per-frame, 583 values; how far green spills past the tracked glass, in UV units, clamped (shipped range 0.02–0.33, clamp 0.4) |

`slack` is part of the portrait contract. The landscape track has no `slack` field; do not remove it here to match landscape, and do not add it to landscape to match portrait.

`keyFrom` is the first frame where the green screen is treated as a keyable fill. Frames 0–47 (black screen) follow the bed with optical flow.

## Reproduce the shipped JSON

From the repository root, with the pinned plate in place:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# All five passes write under work/ and do not overwrite
# portrait/intermediates/ or tracks/portrait.json.
python3 portrait/track2.py plate_portrait.mp4 work/raw2.json
python3 portrait/refine.py plate_portrait.mp4 work/raw2.json work/ref.json
python3 portrait/finalize.py
python3 portrait/finalize2.py
python3 portrait/export_track.py

python3 compare_track.py work/portrait.json
python3 compare_track.py tracks/portrait.json
```

`finalize.py`, `finalize2.py`, and `export_track.py` read and write `work/` relative to the repo root. `export_track.py` reads `plate_portrait.mp4` at the repo root and writes `work/portrait.json`.

`portrait/intermediates/` holds `raw2.json` (pass 1), `ref.json` (pass 2), `oriented.json` (pass 3), and `final.json` (pass 4) from the shipped solve. `final.json` is not the exported oracle; pass 5 adds per-frame `slack` and writes the contract JSON.


## Reproduction result (this import)

A dry run of the five passes above, from this repo on the pinned plate with Python 3.13, `numpy==2.5.4`, `opencv-python-headless==5.0.0.93`, and `scipy==1.18.1`, finished in **85.667 seconds** (Australia/Brisbane): track2 39.752s, refine 18.826s, finalize 0.141s, finalize2 0.929s, export 26.019s. Each intermediate under `work/` was byte-identical to `portrait/intermediates/`, and `work/portrait.json` was byte-identical to `tracks/portrait.json`. The shipped oracle and intermediates were not overwritten.

## Checks

`compare_track.py` always runs both checks. A smooth track can still be wrong.

### Fixture check (exit code)

Compares the solved track to `fixtures/portrait/expected.json`. Exit 1 if any fixture corner moves by more than **1.5px**, or if a fixture frame is missing. This is the check that catches a wrong-but-smooth track.

Fixture frames: 0, 48, 120, 196, 220, 258, 360, 440, 520, 575.

### Motion check

Reports the worst corner acceleration (px/frame²) on every frame. If `expected.json` stores a motion baseline (shipped: 4.26 at frames 453, 233, 232, 451, 236), the check fails when the worst spike is more than 1.0 above that baseline. A lower spike is not proof the track is right.

## QA overlays

Cyan is the tracked glass. Red is the raw hull of the visible green. The yellow dot marks the TL corner.

- `qa/plate-contact-sheet.jpg` — overview contact sheet of the plate
- `qa/pickup-raw-detection.jpg` — frames 198–455 before the pickup model, showing why one was needed
- `qa/lift-246-252-before-anchor-fix.jpg` — first pass of the lift fix, sitting short at the bottom
- `qa/lift-226-258-shipped.jpg` — the shipped lift section

## Layout

```
plate_portrait.mp4                 pinned portrait plate
portrait/track2.py                 pass 1: green hull + pre-green bed flow
portrait/refine.py                 pass 2: edge-line corners
portrait/finalize.py               pass 3: corner order (TL/TR/BR/BL)
portrait/finalize2.py              pass 4: pickup model, outliers, push-in, smooth
portrait/export_track.py           pass 5: slack + contract JSON
portrait/intermediates/            shipped raw2, ref, oriented, final
tracks/portrait.json               shipped oracle
fixtures/portrait/                 expected quads + source frames
qa/                                overlay contact sheets
compare_track.py
requirements.txt
```

`work/` is gitignored. Re-runs write there so shipped intermediates and the oracle stay untouched.
