#!/usr/bin/env python3
"""Draw the README figures: the manager workflow and one figure per skill.

Each figure is built as SVG, then rendered to PNG in docs/assets/ with headless
Chrome so the fonts are baked in. Edit the text or layout here and re-run:

    python3 scripts/render-diagrams.py            # all figures
    python3 scripts/render-diagrams.py manager    # one figure by name

Style: white ground, charcoal text, thin rules, square corners; navy for the
forward path, rust for feedback, a pale blue wash for emphasis.
"""

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "assets"

INK, NAVY, RUST, WASH, GREY = "#1d232b", "#1f3a68", "#b23a2a", "#e8edf4", "#6b7480"
SERIF = "'DejaVu Serif', Georgia, serif"
SANS = "'DejaVu Sans', Helvetica, Arial, sans-serif"


class Fig:
    """A tiny SVG builder: boxes, text, arrows."""

    def __init__(self, w, h):
        self.w, self.h, self.parts = w, h, []

    def add(self, s):
        self.parts.append(s)

    def rect(self, x, y, w, h, fill="#fff", stroke=INK, sw=1.4, dash=None):
        d = f' stroke-dasharray="{dash}"' if dash else ""
        self.add(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{fill}" '
                 f'stroke="{stroke}" stroke-width="{sw}"{d}/>')

    def text(self, x, y, s, size=15, anchor="middle", weight="normal",
             fill=INK, font=SANS, style="normal"):
        self.add(f'<text x="{x}" y="{y}" font-family="{font}" font-size="{size}" '
                 f'font-weight="{weight}" font-style="{style}" fill="{fill}" '
                 f'text-anchor="{anchor}">{escape(s)}</text>')

    def lines(self, x, y, rows, size=15, gap=1.35, **kw):
        for i, row in enumerate(rows):
            self.text(x, y + i * size * gap, row, size=size, **kw)

    def line(self, pts, color=NAVY, sw=1.8, dash=None, head=True):
        d = f' stroke-dasharray="{dash}"' if dash else ""
        m = f' marker-end="url(#h{color[1:]})"' if head else ""
        p = " ".join(f"{x},{y}" for x, y in pts)
        self.add(f'<polyline points="{p}" fill="none" stroke="{color}" '
                 f'stroke-width="{sw}"{d}{m}/>')

    def box(self, x, y, w, h, title, sub=None, fill="#fff", size=15, stroke=INK):
        self.rect(x, y, w, h, fill=fill, stroke=stroke)
        if sub is None:
            self.text(x + w / 2, y + h / 2 + size * 0.35, title, size=size, weight="bold")
        else:
            self.text(x + w / 2, y + h / 2 - 2, title, size=size, weight="bold")
            self.text(x + w / 2, y + h / 2 + size * 1.1, sub, size=size - 3, fill=GREY)

    def svg(self):
        markers = "".join(
            f'<marker id="h{c[1:]}" viewBox="0 0 10 10" refX="9" refY="5" '
            f'markerWidth="8" markerHeight="8" orient="auto-start-reverse">'
            f'<path d="M0,0 L10,5 L0,10 z" fill="{c}"/></marker>'
            for c in (NAVY, RUST, INK))
        return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.w}" '
                f'height="{self.h}" viewBox="0 0 {self.w} {self.h}">'
                f'<defs>{markers}</defs>'
                f'<rect width="100%" height="100%" fill="#fff"/>'
                + "".join(self.parts) + "</svg>")


# --------------------------------------------------------------------------
# Manager workflow


def manager():
    f = Fig(1536, 1320)
    f.text(768, 60, "Manager orchestration and PR delivery", size=34, weight="bold", font=SERIF)

    # (a) one manager, one team per work item
    f.text(60, 128, "(a)  One team per work item: a coordinator and the workers it starts", size=20, weight="bold", font=SERIF, anchor="start")
    f.rect(588, 160, 360, 80, fill=WASH)
    f.text(768, 196, "MANAGER", size=24, weight="bold", font=SERIF)
    f.text(768, 224, "launches and tracks, never does the work", size=13, fill=GREY)

    xs, cw, ty, th = [60, 568, 1076], 400, 340, 140
    for i, (x, name) in enumerate(zip(xs, "ABC")):
        cx = x + cw / 2
        if i == 0:
            f.line([(620, 240), (620, 270), (cx - 40, 270), (cx - 40, ty)], NAVY)
            f.line([(cx + 40, ty), (cx + 40, 296), (660, 296), (660, 240)], RUST, dash="7 5")
        elif i == 1:
            f.line([(748, 240), (748, ty)], NAVY)
            f.line([(788, ty), (788, 240)], RUST, dash="7 5")
        else:
            f.line([(916, 240), (916, 270), (cx + 40, 270), (cx + 40, ty)], NAVY)
            f.line([(cx - 40, ty), (cx - 40, 296), (876, 296), (876, 240)], RUST, dash="7 5")
        f.rect(x, ty, cw, th)
        f.text(cx, ty + 38, f"Work item {name}", size=19, weight="bold", font=SERIF)
        f.rect(cx - 90, ty + 58, 180, 40, fill=WASH)
        f.text(cx, ty + 84, "Coordinator", size=16, weight="bold")
        f.text(cx, ty + 122, "own worktree · one PR", size=13, fill=GREY)
        f.text(x + 14, ty + 18, "TEAM", size=11, weight="bold", fill=GREY, anchor="start")

    f.line([(60, 530), (110, 530)], NAVY)
    f.text(120, 535, "launch", size=13, anchor="start", fill=NAVY)
    f.line([(210, 530), (260, 530)], RUST, dash="7 5")
    f.text(270, 535, "results and record paths", size=13, anchor="start", fill=RUST)
    f.text(1476, 535, "Concurrent while capacity allows; the rest queue.", size=13, anchor="end", fill=GREY)

    # (b) inside one team
    f.line([(60, 588), (1476, 588)], INK, sw=1, head=False)
    f.text(60, 636, "(b)  Inside one team: what a coordinator does", size=20, weight="bold", font=SERIF, anchor="start")
    f.rect(603, 668, 330, 70, fill=WASH)
    f.text(768, 700, "Coordinator", size=20, weight="bold", font=SERIF)
    f.text(768, 724, "owns the item from plan to ready PR", size=13, fill=GREY)
    f.rect(1136, 668, 340, 70)
    f.text(1306, 700, "Issue + PR", size=17, weight="bold")
    f.text(1306, 724, "plan · findings · gate evidence", size=13, fill=GREY)
    f.line([(937, 703), (1132, 703)], NAVY)
    f.text(1035, 692, "records", size=13, fill=NAVY)
    workers = [("Planner", "reads, returns a plan", "read-only"),
               ("Implementer", "edits and commits", "the only writer"),
               ("Reviewers", "check independently", "read-only"),
               ("Tester", "runs the gate", "at the head commit")]
    wx = [60 + i * 360 for i in range(4)]
    for x, (t, d, note) in zip(wx, workers):
        cx = x + 160
        f.line([(768, 738), (768, 770), (cx, 770), (cx, 806)], NAVY)
        f.rect(x, 810, 320, 96)
        f.text(cx, 844, t, size=18, weight="bold")
        f.text(cx, 870, d, size=14)
        f.text(cx, 892, note, size=12, fill=GREY)
    f.text(768, 946, "Roles are chosen by the item's size and risk: a small change needs few, risky ones get more review.",
           size=13, fill=GREY)

    # (c) the lifecycle inside each team
    D = 400
    f.line([(60, 588 + D), (1476, 588 + D)], INK, sw=1, head=False)
    f.text(60, 636 + D, "(c)  Lifecycle inside each team", size=20, weight="bold", font=SERIF, anchor="start")
    names = ["Plan", "Review plan", "Build", "Review + fix", "Test", "Hand back"]
    sw_, gap, x0, y0, h = 190, 52, 60, 676 + D, 64
    for i, n in enumerate(names):
        x = x0 + i * (sw_ + gap)
        f.rect(x, y0, sw_, h)
        f.rect(x, y0, 40, h, fill=NAVY, stroke=NAVY)
        f.text(x + 20, y0 + 41, str(i + 1), size=20, weight="bold", fill="#fff")
        f.text(x + 40 + (sw_ - 40) / 2, y0 + 39, n, size=16, weight="bold")
        if i < 5:
            f.line([(x + sw_ + 6, y0 + h / 2), (x + sw_ + gap - 6, y0 + h / 2)], NAVY)
    mid = lambda i: x0 + i * (sw_ + gap) + sw_ / 2
    f.line([(mid(3), y0 + h), (mid(3), y0 + h + 30), (mid(2), y0 + h + 30), (mid(2), y0 + h + 4)], RUST)
    f.text((mid(2) + mid(3)) / 2, y0 + h + 54, "confirmed finding: fix", size=13, fill=RUST)
    f.line([(mid(5), y0 + h), (mid(5), y0 + h + 30), (mid(4), y0 + h + 30), (mid(4), y0 + h + 4)], RUST)
    f.text((mid(4) + mid(5)) / 2, y0 + h + 54, "CI failure: fix, re-run gate", size=13, fill=RUST)

    f.text(768, 840 + D, "Ready only when the gate exits 0, required CI passes, and no finding is open.",
           size=15, weight="bold")
    f.text(768, 868 + D, "One PR per item. Never auto-merged.", size=13, fill=GREY)
    return f


# --------------------------------------------------------------------------
# Per-skill figures (960 x 420)

W, H = 960, 420


def head(f, cmd, tagline):
    f.text(30, 46, cmd, size=28, weight="bold", font=SERIF, anchor="start")
    f.text(30, 74, tagline, size=14, fill=GREY, anchor="start")
    f.line([(30, 90), (W - 30, 90)], INK, sw=1, head=False)


def foot(f, s):
    f.rect(30, 364, W - 60, 40, fill=WASH, stroke=INK, sw=1)
    f.text(W / 2, 390, s, size=14)


def define():
    f = Fig(W, H)
    head(f, "/define", "A loose request becomes a problem, a scope, and done-criteria.")
    f.box(30, 160, 170, 100, "Request", "loose · unclear", size=18)
    f.line([(204, 210), (270, 210)])
    items = [("Problem statement", "what and why"), ("Scope", "in  ·  out"),
             ("Done-criteria", "numbered, checkable")]
    for i, (t, s) in enumerate(items):
        f.box(274, 110 + i * 80, 280, 64, t, s, size=16, fill=WASH)
        f.line([(558, 142 + i * 80), (680, 210)])
    f.box(684, 160, 246, 100, "Issue", "definition written to it", size=18)
    f.text(414, 352, "asks only what changes the plan", size=12, fill=RUST, style="italic")
    foot(f, "Designs no solution. Next step: /plan.")
    return f


def plan():
    f = Fig(W, H)
    head(f, "/plan", "A definition becomes small, verifiable tasks in dependency order.")
    f.box(30, 160, 170, 100, "Definition", "from the issue", size=18)
    f.line([(204, 210), (264, 210)])
    for i in range(3):
        x = 268 + i * 140
        f.rect(x, 120, 126, 180, fill="#fff")
        f.rect(x, 120, 126, 34, fill=WASH)
        f.text(x + 63, 143, f"Task {i + 1}", size=15, weight="bold")
        f.lines(x + 63, 184, ["scope", "acceptance", "criteria", "verification"], size=12, fill=GREY)
        if i < 2:
            f.line([(x + 128, 210), (x + 138, 210)], NAVY, sw=1.6)
    f.text(478, 330, "vertical slices: one complete path each", size=12, fill=RUST, style="italic")
    f.line([(692, 210), (740, 210)])
    f.rect(744, 120, 186, 180)
    f.rect(744, 120, 186, 34, fill=WASH)
    f.text(837, 143, "Issue", size=15, weight="bold")
    f.text(760, 184, "## Progress", size=13, weight="bold", anchor="start")
    f.lines(760, 208, ["[ ] task 1", "[ ] task 2", "[ ] task 3", "[ ] follow-ups"], size=13,
            anchor="start", fill=GREY)
    foot(f, "Writes no code. Next step: /build.")
    return f


def build():
    f = Fig(W, H)
    head(f, "/build", "One task at a time, test first, one commit each.")
    f.box(30, 150, 140, 90, "Next task", "acceptance criteria", size=16)
    f.line([(174, 195), (214, 195)])
    xs = [218, 400, 582]
    labels = [("1  Red", "write a failing test", "#fbe9e6", RUST), ("2  Green", "minimum code to pass", "#e6f2ea", "#2f6b46"),
              ("3  Gate", "full suite passes", WASH, NAVY)]
    for x, (t, s, fill, col) in zip(xs, labels):
        f.rect(x, 150, 164, 90, fill=fill, stroke=col, sw=1.8)
        f.text(x + 82, 192, t, size=18, weight="bold", fill=col)
        f.text(x + 82, 216, s, size=12)
    f.line([(384, 195), (398, 195)])
    f.line([(566, 195), (580, 195)])
    f.line([(750, 195), (790, 195)])
    f.box(794, 150, 136, 90, "Commit", "Conventional", size=17, fill=WASH)
    f.line([(862, 244), (862, 290), (112, 290), (112, 244)], RUST)
    f.text(487, 312, "repeat for the next task", size=12, fill=RUST)
    foot(f, "Blocked, or a criterion is wrong: stop and update the plan, never widen scope.")
    return f


def verify():
    f = Fig(W, H)
    head(f, "/verify", "Check finished work against its acceptance criteria.")
    f.rect(30, 110, 380, 230)
    f.rect(30, 110, 380, 34, fill=WASH)
    f.text(220, 133, "Acceptance criteria (from the plan)", size=14, weight="bold")
    rows = [("1  User can sign in", "PASS", "#2f6b46"), ("2  Invalid password rejected", "PASS", "#2f6b46"),
            ("3  Session expires", "FAIL", RUST), ("4  Audit log written", "PASS", "#2f6b46")]
    for i, (t, r, c) in enumerate(rows):
        y = 176 + i * 40
        f.text(46, y, t, size=14, anchor="start")
        f.text(394, y, r, size=14, weight="bold", fill=c, anchor="end")
        f.line([(40, y + 14), (400, y + 14)], "#c9ced6", sw=0.8, head=False)
    f.text(220, 322, "each exercised end to end", size=12, fill=GREY, style="italic")
    f.line([(416, 225), (520, 225)])
    f.box(524, 120, 190, 70, "Tasks", "every task confirmed done", size=15)
    f.box(524, 210, 190, 70, "Result in issue", "pass or fail, recorded", size=15)
    f.line([(718, 245), (760, 245)])
    f.rect(764, 110, 166, 230, stroke=RUST)
    f.rect(764, 110, 166, 34, fill="#fbe9e6", stroke=RUST)
    f.text(847, 133, "Gaps", size=15, weight="bold", fill=RUST)
    f.lines(847, 180, ["3  Session", "expires", "", "no fix", "applied here"], size=13, fill=GREY)
    foot(f, "Reports; it does not fix. Gaps go back to /build.")
    return f


def review():
    f = Fig(W, H)
    head(f, "/review", "Read the branch diff against main, verify each finding.")
    f.box(30, 150, 150, 100, "Diff", "branch vs main", size=18)
    f.line([(184, 200), (224, 200)])
    dims = ["correctness", "readability", "architecture", "security", "performance", "dead code", "docs currency"]
    f.rect(228, 106, 220, 250, fill="#fff")
    f.rect(228, 106, 220, 34, fill=WASH)
    f.text(338, 129, "Seven lenses", size=14, weight="bold")
    for i, d in enumerate(dims):
        f.text(248, 168 + i * 25, "· " + d, size=14, anchor="start")
    f.line([(452, 200), (500, 200)])
    f.box(504, 150, 170, 100, "Verify", "each finding checked", size=17)
    f.line([(678, 175), (730, 140)])
    f.line([(678, 225), (730, 270)])
    f.box(734, 106, 196, 76, "Trivial", "fixed behind lint + tests", size=15, fill="#e6f2ea", stroke="#2f6b46")
    f.rect(734, 236, 196, 110, stroke=RUST)
    f.text(832, 262, "Reported by severity", size=14, weight="bold", fill=RUST)
    f.lines(832, 290, ["critical", "major", "minor"], size=13, fill=GREY)
    foot(f, "Run before /ship, or to check what you just built.")
    return f


def ship():
    f = Fig(W, H)
    head(f, "/ship", "Deliver the finished work as you specify.")
    labels = [("Branch", "verified work"), ("Push", "branch to remote"),
              ("Draft PR", "summary + issue link"), ("CI", "followed until green"),
              ("Ready PR", "marked ready")]
    bw, gap = 150, 35
    for i, (t, s) in enumerate(labels):
        x = 30 + i * (bw + gap)
        f.box(x, 150, bw, 90, t, s, size=16, fill=WASH if i == 4 else "#fff")
        if i < 4:
            f.line([(x + bw + 3, 195), (x + bw + gap - 3, 195)])
    x4, x3 = 30 + 3 * (bw + gap) + bw / 2, 30 + 2 * (bw + gap) + bw / 2
    f.line([(x4, 244), (x4, 290), (x3, 290), (x3, 244)], RUST)
    f.text((x3 + x4) / 2, 312, "CI failure: fix, push again", size=12, fill=RUST)
    foot(f, "Default delivery is a PR. Say otherwise and it ships that way. It never merges.")
    return f


def ux():
    f = Fig(W, H)
    head(f, "/review-ux-psychology", "Review a flow's decision architecture to move a named metric.")
    for i, t in enumerate(["Step 1", "Step 2", "Step 3"]):
        x = 30 + i * 100
        f.rect(x, 130, 84, 150)
        f.rect(x, 130, 84, 22, fill=WASH)
        f.text(x + 42, 146, t, size=11, weight="bold")
        f.rect(x + 12, 166, 60, 12, fill="#c9ced6", stroke="none", sw=0)
        f.rect(x + 12, 188, 60, 12, fill="#c9ced6", stroke="none", sw=0)
        f.rect(x + 12, 246, 60, 20, fill=NAVY, stroke=NAVY)
        if i < 2:
            f.line([(x + 86, 205), (x + 98, 205)], GREY, sw=1.4)
    f.text(162, 304, "screen · flow · branch diff", size=12, fill=GREY, style="italic")
    f.line([(340, 205), (384, 205)])
    f.rect(388, 110, 250, 230)
    f.rect(388, 110, 250, 34, fill=WASH)
    f.text(513, 133, "Behavioral principles", size=14, weight="bold")
    for i, p in enumerate(["defaults", "progress", "framing", "anchoring", "friction"]):
        f.text(412, 176 + i * 30, "· " + p, size=15, anchor="start")
    f.line([(642, 205), (686, 205)])
    f.box(690, 110, 240, 100, "Findings", "each independently verified", size=16)
    f.text(810, 250, "target metric", size=12, fill=GREY)
    f.box(690, 262, 240, 78, "Signup · activation · checkout", None, size=13, fill=WASH)
    foot(f, "Conversion, not code quality. Fixes optional, behind your lint and build gate.")
    return f


def batch():
    f = Fig(W, H)
    head(f, "/batch-merge-prs", "Merge the PRs you name onto one new local branch.")
    for i, (n, st) in enumerate([("#101", "new"), ("#102", "already in main"), ("#103", "conflicts")]):
        y = 112 + i * 78
        f.box(30, y, 150, 62, "PR " + n, st, size=15)
    f.line([(184, 143), (300, 200)])
    f.line([(184, 221), (300, 221), ], GREY, dash="6 4", head=False)
    f.text(250, 214, "skipped", size=11, fill=GREY, anchor="middle", style="italic")
    f.line([(184, 299), (300, 240)])
    f.text(250, 326, "resolved, both", size=11, fill=NAVY, anchor="middle")
    f.text(250, 340, "sides kept", size=11, fill=NAVY, anchor="middle")
    f.rect(304, 150, 240, 120, fill=WASH)
    f.text(424, 190, "batch/<YYYYMMDD-HHMM>", size=14, weight="bold")
    f.text(424, 216, "one new local branch", size=13)
    f.text(424, 240, "evidence shown per PR", size=12, fill=GREY)
    f.line([(548, 210), (600, 210)])
    f.box(604, 150, 150, 120, "Tests", "project's own suite", size=16)
    f.line([(758, 210), (798, 210)])
    f.box(802, 150, 128, 120, "Review", "merged branch", size=16)
    foot(f, "Never pushes and never closes a PR.")
    return f


def issues():
    f = Fig(W, H)
    head(f, "/file-issues", "A long-lived session: one description in, one good issue out.")
    f.box(30, 150, 150, 90, "Description", "you type it", size=16)
    stages = [("Duplicate", "search"), ("Code-grounded", "permalinks"), ("Repo title", "+ labels")]
    f.line([(184, 195), (222, 195)])
    for i, (t, s) in enumerate(stages):
        x = 226 + i * 186
        f.box(x, 150, 160, 90, t, s, size=15, fill=WASH)
        f.line([(x + 164, 195), (x + 182, 195)])
    f.box(790, 150, 140, 90, "GitHub issue", "filed", size=16)
    f.line([(860, 244), (860, 290), (110, 290), (110, 244)], RUST)
    f.text(485, 312, "next description: same session, same conventions", size=12, fill=RUST)
    foot(f, "Files issues only. Never edits code, branches, commits, or opens PRs.")
    return f


FIGURES = {
    "manager": ("manager-workflow", manager),
    "define": ("skill-define", define),
    "plan": ("skill-plan", plan),
    "build": ("skill-build", build),
    "verify": ("skill-verify", verify),
    "review": ("skill-review", review),
    "ship": ("skill-ship", ship),
    "review-ux-psychology": ("skill-review-ux-psychology", ux),
    "batch-merge-prs": ("skill-batch-merge-prs", batch),
    "file-issues": ("skill-file-issues", issues),
}


def chrome():
    for name in ("google-chrome", "chromium", "chromium-browser"):
        path = shutil.which(name)
        if path:
            return path
    sys.exit("render-diagrams: no Chrome or Chromium on PATH")


def main(argv):
    wanted = argv or list(FIGURES)
    unknown = [n for n in wanted if n not in FIGURES]
    if unknown:
        sys.exit(f"render-diagrams: unknown figure {unknown}; choose from {list(FIGURES)}")
    OUT.mkdir(parents=True, exist_ok=True)
    browser = chrome()
    with tempfile.TemporaryDirectory() as tmp:
        for key in wanted:
            stem, build_fig = FIGURES[key]
            fig = build_fig()
            svg = Path(tmp) / f"{stem}.svg"
            svg.write_text(fig.svg(), encoding="utf-8")
            png = OUT / f"{stem}.png"
            subprocess.run(
                [browser, "--headless=new", "--disable-gpu",
                 "--hide-scrollbars", "--force-device-scale-factor=2",
                 f"--window-size={fig.w},{fig.h}", f"--screenshot={png}",
                 svg.as_uri()],
                check=True, capture_output=True)
            print(f"wrote {png.relative_to(ROOT)}")


if __name__ == "__main__":
    main(sys.argv[1:])
