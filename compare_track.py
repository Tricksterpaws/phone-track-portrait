#!/usr/bin/env python3
"""Compare a solved portrait track to the fixture quads, and check its motion.

Usage:
  python compare_track.py [path/to/portrait.json]

Fixture check (exit code):
  Exit 0 if every fixture corner is within --tol (default 1.5px) of
  fixtures/portrait/expected.json. Exit 1 if any fixture corner moves
  more than the tolerance, or a fixture frame is missing. This is the
  check that catches a wrong-but-smooth track.

Motion check:
  Measures every frame's corner acceleration (change in per-frame
  movement, px/frame^2). A jump shows up as a spike. If expected.json
  stores a motion baseline, this fails when the worst spike is more
  than --jump-margin (default 1.0) above that baseline. A lower spike
  than the baseline is not by itself proof the track is right; the
  fixture check is what catches a wrong-but-smooth track.
"""
import argparse
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DEFAULT_TRACK = ROOT / "tracks" / "portrait.json"


def quads(track):
    out = []
    for flat in track["frames"]:
        if flat is None:
            out.append(None)
            continue
        out.append([[flat[k], flat[k + 1]] for k in range(0, 8, 2)])
    return out


def jumps(got, key_from=0):
    """(frame, px/frame^2) for every frame with a neighbour on each side.

    The frame where the screen turns green is skipped: the solve changes
    method there (bed flow -> keyed glass).
    """
    out = []
    for i in range(1, len(got) - 1):
        a, b, c = got[i - 1], got[i], got[i + 1]
        if a is None or b is None or c is None or abs(i - key_from) <= 1:
            continue
        acc = max(
            math.hypot(a[k][0] - 2 * b[k][0] + c[k][0], a[k][1] - 2 * b[k][1] + c[k][1])
            for k in range(4)
        )
        out.append((i, acc))
    return out


def main():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("track", nargs="?", default=str(DEFAULT_TRACK))
    parser.add_argument("--tol", type=float, default=1.5)
    parser.add_argument(
        "--jump-margin",
        type=float,
        default=1.0,
        help="allowed px/frame^2 above the stored motion baseline",
    )
    args = parser.parse_args()

    expected = json.loads((ROOT / "fixtures" / "portrait" / "expected.json").read_text())
    solved = json.loads(Path(args.track).read_text())
    got = quads(solved)
    worst = 0.0
    failed = False
    print("== fixture check ==")
    for item in expected["frames"]:
        i = item["index"]
        if i >= len(got) or got[i] is None:
            print(f"f{i:04d}  MISSING")
            failed = True
            continue
        err = 0.0
        for a, b in zip(item["quad"], got[i]):
            err = max(err, math.hypot(a[0] - b[0], a[1] - b[1]))
        worst = max(worst, err)
        flag = "  FAIL" if err > args.tol else ""
        print(f"f{i:04d}  {err:7.3f}px{flag}")
        if err > args.tol:
            failed = True
    print(f"worst {worst:.3f}px  tol {args.tol}px  frames {len(expected['frames'])}")

    fps = solved.get("fps", expected.get("fps", 24.0))
    js = sorted(jumps(got, solved.get("keyFrom", expected.get("keyFrom", 0))), key=lambda t: -t[1])
    top = js[:5]
    peak = top[0][1] if top else 0.0
    spikes = ", ".join(f"f{i:04d} ({i / fps:.2f}s) {a:.1f}" for i, a in top)
    print()
    print("== motion check ==")
    print(f"worst corner acceleration {peak:.2f} px/frame^2  [{spikes}]")
    if "motion" in expected:
        limit = expected["motion"]["max_jump"] + args.jump_margin
        if peak > limit:
            print(f"motion FAIL: {peak:.2f} > baseline {expected['motion']['max_jump']} + {args.jump_margin}")
            failed = True
        else:
            print(f"motion ok: baseline {expected['motion']['max_jump']} + {args.jump_margin}")
        print("A lower spike than the baseline is not proof the track is right.")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
