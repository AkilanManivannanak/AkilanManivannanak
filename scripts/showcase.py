#!/usr/bin/env python3
"""Flagship cards, each drawn as a different kind of picture, and a self-rendered 3D
contribution chart. Everything is plain animated SVG so it moves on the GitHub profile.

Every figure on a flagship card is copied from the repo's own evaluation output; when a
card needs a second number to draw a comparison (a baseline), it is derived only from a
stated relative figure and labelled as such.
"""

import math
from html import escape

from visuals import PAL, SANS, MONO, _svg, _svg_clear, _write

W, H = 600, 320


def _frame(p, c, stack, title, body, link_c=None):
    """Shared card shell: panel, accent sweep, stack line, title, and the 'Open repo' cue."""
    link_c = link_c or c
    return f'''
<defs>
  <linearGradient id="sh" x1="0" x2="1"><stop offset="0" stop-color="{c}" stop-opacity="0"/>
    <stop offset=".5" stop-color="{c}" stop-opacity=".9"/><stop offset="1" stop-color="{c}" stop-opacity="0"/></linearGradient>
  <clipPath id="cl"><rect x="1" y="1" width="{W-2}" height="{H-2}" rx="16"/></clipPath>
</defs>
<rect x="1" y="1" width="{W-2}" height="{H-2}" rx="16" fill="{p["panel"]}" stroke="{p["line"]}"/>
<g clip-path="url(#cl)">
  <rect x="0" y="0" width="{W}" height="3" fill="{c}" opacity=".35"/>
  <rect x="-220" y="0" width="220" height="3" fill="url(#sh)">
    <animate attributeName="x" from="-220" to="{W}" dur="3.4s" repeatCount="indefinite"/></rect>
</g>
<text x="28" y="40" fill="{c}" font-family="{MONO}" font-size="11.5" letter-spacing="2.2">{escape(stack.upper())}</text>
<text x="28" y="76" fill="{p["text"]}" font-family="{SANS}" font-size="28" font-weight="750" letter-spacing="-.5">{escape(title)}</text>
{body}
<g font-family="{SANS}" font-size="13.5" font-weight="650" fill="{link_c}">
  <text x="{W-48}" y="{H-16}" text-anchor="end">Open repo</text>
  <text x="{W-42}" y="{H-16}">→<animate attributeName="x" values="{W-42};{W-35};{W-42}" dur="1.4s" repeatCount="indefinite"/></text>
</g>'''


def _metric(p, x, y, value, label, c, size=26, anchor="start"):
    return (f'<text x="{x}" y="{y}" text-anchor="{anchor}" fill="{c}" font-family="{SANS}" font-size="{size}" font-weight="750">{escape(value)}</text>'
            f'<text x="{x}" y="{y + 18}" text-anchor="{anchor}" fill="{p["mute"]}" font-family="{MONO}" font-size="10.5">{escape(label)}</text>')


# ----------------------------------------------------------------- 1. OpenDriveFM: camera rig

def card_opendrivefm(mode):
    p = PAL[mode]
    c = p["amber"]
    cx, cy = 482, 176
    cams = []
    names = ["FRONT", "F-RIGHT", "B-RIGHT", "BACK", "B-LEFT", "F-LEFT"]
    for i, n in enumerate(names):
        a = -90 + i * 60
        r = math.radians(a)
        spread = math.radians(26)
        x1, y1 = cx + 84 * math.cos(r - spread), cy + 84 * math.sin(r - spread)
        x2, y2 = cx + 84 * math.cos(r + spread), cy + 84 * math.sin(r + spread)
        faulty = i == 4
        col = p["crit"] if faulty else c
        anim = (f'<animate attributeName="fill" values="{c};{c};{p["crit"]};{p["crit"]};{c}" keyTimes="0;.45;.5;.85;1" dur="6s" repeatCount="indefinite"/>'
                if faulty else "")
        cams.append(f'<path d="M{cx} {cy} L{x1:.1f} {y1:.1f} A84 84 0 0 1 {x2:.1f} {y2:.1f} Z" fill="{c}" fill-opacity=".13" stroke="{c}" stroke-opacity=".35">'
                    + (f'<animate attributeName="fill-opacity" values=".13;.13;.03;.03;.13" keyTimes="0;.45;.5;.85;1" dur="6s" repeatCount="indefinite"/>' if faulty else "")
                    + '</path>')
        lx, ly = cx + 100 * math.cos(r), cy + 100 * math.sin(r)
        cams.append(f'<circle cx="{lx:.1f}" cy="{ly:.1f}" r="4" fill="{c}">{anim}</circle>')
    # occupancy cells flickering around the ego vehicle
    cells = []
    for i, (dx, dy) in enumerate([(-60, -40), (40, -62), (66, 20), (-30, 56), (-74, 8), (24, 48), (10, -80)]):
        cells.append(f'<rect x="{cx + dx}" y="{cy + dy}" width="12" height="9" rx="2" fill="{c}" opacity=".2">'
                     f'<animate attributeName="opacity" values=".2;.9;.2" dur="2.6s" begin="{i * .37:.2f}s" repeatCount="indefinite"/></rect>')
    # trust bars, one per camera, the faulty one dropping
    bars = []
    for i, n in enumerate(names):
        y = 112 + i * 21
        faulty = i == 4
        full = 120
        w = full * (0.86 + (i % 3) * 0.04)
        anim = (f'<animate attributeName="width" values="{w:.0f};{w:.0f};{full * .18:.0f};{full * .18:.0f};{w:.0f}" keyTimes="0;.45;.52;.85;1" dur="6s" repeatCount="indefinite"/>'
                f'<animate attributeName="fill" values="{p["teal"]};{p["teal"]};{p["crit"]};{p["crit"]};{p["teal"]}" keyTimes="0;.45;.52;.85;1" dur="6s" repeatCount="indefinite"/>'
                if faulty else "")
        bars.append(f'<text x="28" y="{y + 8}" fill="{p["mute"]}" font-family="{MONO}" font-size="9.5">{n}</text>'
                    f'<rect x="92" y="{y}" width="{full}" height="8" rx="4" fill="{p["line"]}"/>'
                    f'<rect x="92" y="{y}" width="{w:.0f}" height="8" rx="4" fill="{p["teal"]}">{anim}</rect>')
    body = f'''
<text x="28" y="100" fill="{p["sub"]}" font-family="{MONO}" font-size="10.5">per-camera trust · fault injected on one view</text>
{"".join(bars)}
<circle cx="{cx}" cy="{cy}" r="100" fill="none" stroke="{p["line"]}"/>
{"".join(cams)}{"".join(cells)}
<rect x="{cx - 7}" y="{cy - 12}" width="14" height="24" rx="4" fill="{p["text"]}"/>
{_metric(p, 236, 132, "0.764", "fault AUROC", c)}
{_metric(p, 236, 190, "71.2 FPS", "p50 13.9 ms", p["text"], 22)}
<text x="28" y="{H - 22}" fill="{p["sub"]}" font-family="{SANS}" font-size="13">Camera-only BEV occupancy that knows which camera to trust.</text>'''
    return _svg(W, H, "OpenDriveFM: per-camera trust, fault AUROC 0.764 at 71.2 FPS",
                _frame(p, c, "nuScenes · TorchScript · C++", "OpenDriveFM", body), p)


# ----------------------------------------------------------------- 2. Guardian Drive: monitor wall

def card_guardian(mode):
    p = PAL[mode]
    c = p["crit"]
    ecg = "M0 40 L40 40 L48 40 L54 14 L60 64 L66 28 L72 40 L118 40 L124 34 L130 40 L170 40"
    trace = (f'<g transform="translate(28 98)"><rect width="300" height="80" rx="10" fill="{p["bg"]}" stroke="{p["line"]}"/>'
             f'<g transform="translate(14 6) scale(.9 .9)"><path d="{ecg} M170 40 L210 40 L218 40 L224 14 L230 64 L236 28 L242 40 L300 40" fill="none" stroke="{c}" stroke-width="2.2" '
             f'stroke-dasharray="420" stroke-dashoffset="420"><animate attributeName="stroke-dashoffset" values="420;0;0" keyTimes="0;.8;1" dur="2.6s" repeatCount="indefinite"/></path></g>'
             f'<text x="12" y="16" fill="{p["mute"]}" font-family="{MONO}" font-size="9.5">CARDIAC</text>'
             f'<circle cx="284" cy="16" r="4" fill="{c}"><animate attributeName="r" values="3;6;3" dur="1s" repeatCount="indefinite"/></circle></g>')
    # eyelid / drowsiness meter
    eye = (f'<g transform="translate(28 192)"><rect width="300" height="56" rx="10" fill="{p["bg"]}" stroke="{p["line"]}"/>'
           f'<text x="12" y="20" fill="{p["mute"]}" font-family="{MONO}" font-size="10">DROWSINESS</text>'
           f'<ellipse cx="150" cy="32" rx="34" ry="12" fill="none" stroke="{p["amber"]}" stroke-width="2">'
           f'<animate attributeName="ry" values="12;12;1;12;12" keyTimes="0;.6;.66;.72;1" dur="3.2s" repeatCount="indefinite"/></ellipse>'
           f'<circle cx="150" cy="32" r="6" fill="{p["amber"]}"><animate attributeName="r" values="6;6;0;6;6" keyTimes="0;.6;.66;.72;1" dur="3.2s" repeatCount="indefinite"/></circle></g>')
    # eight detector lights
    leds = []
    for i in range(8):
        x, y = 372 + (i % 4) * 46, 108 + (i // 4) * 44
        leds.append(f'<circle cx="{x}" cy="{y}" r="13" fill="{p["teal"]}" fill-opacity=".14" stroke="{p["teal"]}" stroke-opacity=".5"/>'
                    f'<circle cx="{x}" cy="{y}" r="5" fill="{p["teal"]}"><animate attributeName="opacity" values="1;.3;1" dur="{1.6 + (i % 3) * .5:.1f}s" begin="{i * .2:.1f}s" repeatCount="indefinite"/></circle>')
    body = f'''
{trace}{eye}
<text x="350" y="86" fill="{p["mute"]}" font-family="{MONO}" font-size="10">8 HAZARD DETECTORS · SAFETY FSM</text>
{"".join(leds)}
{_metric(p, 352, 222, "0.961", "cardiac AUC", c)}
{_metric(p, 470, 222, "0.951", "drowsiness AUC", p["amber"])}
<text x="28" y="{H - 22}" fill="{p["sub"]}" font-family="{SANS}" font-size="13">nuScenes ADE 3.159 m · fused with the BEV stack</text>'''
    return _svg(W, H, "Guardian Drive: cardiac AUC 0.961, drowsiness AUC 0.951, eight hazard detectors",
                _frame(p, c, "BEVFormer · DDPM · C++17 · TensorRT", "Guardian Drive", body), p)


# ----------------------------------------------------------------- 3. SafeTruck-AV2: trajectories

def card_safetruck(mode):
    p = PAL[mode]
    c = p["amber"]
    ox, oy = 28, 96
    road = (f'<rect x="{ox}" y="{oy}" width="544" height="130" rx="12" fill="{p["bg"]}" stroke="{p["line"]}"/>'
            f'<line x1="{ox + 10}" y1="{oy + 44}" x2="{ox + 534}" y2="{oy + 44}" stroke="{p["line"]}" stroke-dasharray="14 12"/>'
            f'<line x1="{ox + 10}" y1="{oy + 88}" x2="{ox + 534}" y2="{oy + 88}" stroke="{p["line"]}" stroke-dasharray="14 12">'
            f'<animate attributeName="stroke-dashoffset" values="0;-26" dur=".8s" repeatCount="indefinite"/></line>')
    truth = f"M{ox + 70} {oy + 66} C{ox + 200} {oy + 66} {ox + 260} {oy + 30} {ox + 380} {oy + 24} S{ox + 500} {oy + 22} {ox + 530} {oy + 22}"
    model = f"M{ox + 70} {oy + 66} C{ox + 205} {oy + 64} {ox + 265} {oy + 34} {ox + 385} {oy + 28} S{ox + 505} {oy + 26} {ox + 530} {oy + 27}"
    cv = f"M{ox + 70} {oy + 66} L{ox + 530} {oy + 66}"
    cone = f"M{ox + 70} {oy + 66} C{ox + 205} {oy + 52} {ox + 265} {oy + 14} {ox + 530} {oy + 8} L{ox + 530} {oy + 46} C{ox + 265} {oy + 52} {ox + 205} {oy + 76} {ox + 70} {oy + 66} Z"

    def draw(d, col, dash="", w=2.4, delay=0):
        return (f'<path d="{d}" fill="none" stroke="{col}" stroke-width="{w}" stroke-linecap="round" {dash} pathLength="100" '
                f'stroke-dasharray="100" stroke-dashoffset="100"><animate attributeName="stroke-dashoffset" values="100;0;0;100" '
                f'keyTimes="0;.4;.9;1" dur="5s" begin="{delay}s" repeatCount="indefinite"/></path>')
    truck = (f'<g><rect x="-14" y="-8" width="28" height="16" rx="3" fill="{p["text"]}"/><rect x="8" y="-6" width="8" height="12" rx="2" fill="{c}"/>'
             f'<animateMotion dur="5s" repeatCount="indefinite" keyPoints="0;1;1;0" keyTimes="0;.4;.9;1" calcMode="linear" path="{model}"/></g>')
    legend = (f'<g font-family="{MONO}" font-size="10.5">'
              f'<line x1="{ox + 14}" y1="{oy + 112}" x2="{ox + 34}" y2="{oy + 112}" stroke="{p["text"]}" stroke-width="2.4"/><text x="{ox + 40}" y="{oy + 116}" fill="{p["sub"]}">ground truth</text>'
              f'<line x1="{ox + 140}" y1="{oy + 112}" x2="{ox + 160}" y2="{oy + 112}" stroke="{c}" stroke-width="2.4"/><text x="{ox + 166}" y="{oy + 116}" fill="{p["sub"]}">SafeTruck forecast + uncertainty</text>'
              f'<line x1="{ox + 390}" y1="{oy + 112}" x2="{ox + 410}" y2="{oy + 112}" stroke="{p["mute"]}" stroke-width="2" stroke-dasharray="4 4"/><text x="{ox + 416}" y="{oy + 116}" fill="{p["sub"]}">const-velocity</text></g>')
    body = f'''
{road}
<path d="{cone}" fill="{c}" opacity=".12"><animate attributeName="opacity" values="0;.14;.14;0" keyTimes="0;.4;.9;1" dur="5s" repeatCount="indefinite"/></path>
<path d="{cv}" fill="none" stroke="{p["mute"]}" stroke-width="2" stroke-dasharray="4 4" opacity="0"><animate attributeName="opacity" values="0;1;1;0" keyTimes="0;.2;.9;1" dur="5s" repeatCount="indefinite"/></path>
{draw(truth, p["text"])}
{draw(model, c, w=3)}
{truck}
{legend}
{_metric(p, 28, 254, "18.78 m", "ADE · forecast error", c)}
{_metric(p, 200, 254, "−45%", "error vs const-velocity", p["teal"])}
<text x="372" y="248" fill="{p["sub"]}" font-family="{SANS}" font-size="12.5">Guardrails with a Normal</text>
<text x="372" y="265" fill="{p["sub"]}" font-family="{SANS}" font-size="12.5">to Min-Risk fallback ladder</text>'''
    return _svg(W, H, "SafeTruck-AV2: trajectory forecast ADE 18.78 m, 45% lower than constant velocity",
                _frame(p, c, "FastAPI · React · nuScenes", "SafeTruck-AV2", body), p)


# ----------------------------------------------------------------- 4. Talentra: agent pipeline

def card_talentra(mode):
    p = PAL[mode]
    c = p["teal"]
    agents = ["Screener", "Ranker", "Interviewer", "Bias auditor", "Copilot"]
    nodes, y = [], 128
    xs = [64 + i * 118 for i in range(5)]
    for i, (x, n) in enumerate(zip(xs, agents)):
        nodes.append(f'<circle cx="{x}" cy="{y}" r="24" fill="{p["bg"]}" stroke="{c}" stroke-width="2"/>'
                     f'<circle cx="{x}" cy="{y}" r="24" fill="{c}" opacity="0"><animate attributeName="opacity" values="0;.35;0;0" keyTimes="0;.06;.16;1" dur="4s" begin="{i * .8:.1f}s" repeatCount="indefinite"/></circle>'
                     f'<text x="{x}" y="{y + 5}" text-anchor="middle" fill="{p["text"]}" font-family="{MONO}" font-size="13" font-weight="700">{i + 1}</text>'
                     f'<text x="{x}" y="{y + 44}" text-anchor="middle" fill="{p["sub"]}" font-family="{SANS}" font-size="11.5">{n}</text>')
    pipe = f'<line x1="{xs[0]}" y1="{y}" x2="{xs[-1]}" y2="{y}" stroke="{c}" stroke-opacity=".35" stroke-width="2"/>'
    packet = (f'<circle r="6" fill="{p["text"]}"><animateMotion dur="4s" repeatCount="indefinite" path="M{xs[0]} {y} L{xs[-1]} {y}"/></circle>'
              f'<circle r="6" fill="{p["text"]}" opacity=".5"><animateMotion dur="4s" begin="2s" repeatCount="indefinite" path="M{xs[0]} {y} L{xs[-1]} {y}"/></circle>')
    fallback = (f'<path d="M{xs[0]} {y + 64} L{xs[-1]} {y + 64}" stroke="{p["mute"]}" stroke-dasharray="3 5"/>'
                f'<text x="{(xs[0] + xs[-1]) / 2}" y="{y + 58}" text-anchor="middle" fill="{p["mute"]}" font-family="{MONO}" font-size="10">fallback path at every stage</text>')
    # latency vs SLO on a log axis: 1 ms .. 2 s
    lx, lw, ly = 28, 330, 238

    def pos(ms):
        return lx + lw * (math.log10(ms) - 0) / (math.log10(2000))
    lat = (f'<rect x="{lx}" y="{ly}" width="{lw}" height="10" rx="5" fill="{p["line"]}"/>'
           f'<rect x="{lx}" y="{ly}" width="0" height="10" rx="5" fill="{c}"><animate attributeName="width" values="0;{pos(4.81) - lx:.0f}" dur="1.2s" fill="freeze"/></rect>'
           f'<line x1="{pos(1500):.0f}" y1="{ly - 6}" x2="{pos(1500):.0f}" y2="{ly + 16}" stroke="{p["crit"]}" stroke-width="2"/>'
           f'<text x="{pos(1500):.0f}" y="{ly - 10}" text-anchor="middle" fill="{p["crit"]}" font-family="{MONO}" font-size="10">SLO 1.5 s</text>'
           f'<text x="{pos(4.81):.0f}" y="{ly - 10}" text-anchor="middle" fill="{c}" font-family="{MONO}" font-size="10">p95</text>'
           f'<text x="{lx}" y="{ly + 30}" fill="{p["mute"]}" font-family="{MONO}" font-size="9.5">1 ms</text>'
           f'<text x="{lx + lw}" y="{ly + 30}" text-anchor="end" fill="{p["mute"]}" font-family="{MONO}" font-size="9.5">2 s · log scale</text>')
    body = f'''
{pipe}{"".join(nodes)}{packet}{fallback}
{lat}
{_metric(p, 392, 248, "4.81 ms", "p95 latency", c)}
{_metric(p, 500, 248, "$0.000", "per request", p["text"], 20)}'''
    return _svg(W, H, "Talentra Copilot: five agents, p95 4.81 ms against a 1.5 s SLO",
                _frame(p, c, "LangGraph · FastAPI · Prometheus", "Talentra Copilot", body), p)


# ----------------------------------------------------------------- 5. CineWave: funnel + lift

def card_cinewave(mode):
    p = PAL[mode]
    c = p["sky"]
    stages = [("Catalog", 250), ("ALS retrieval", 190), ("LightGBM ranker", 130), ("Bandit explore", 92), ("Top 10", 56)]
    out = []
    for i, (n, w) in enumerate(stages):
        y = 96 + i * 34
        x = 28 + (250 - w) / 2
        out.append(f'<rect x="{x:.0f}" y="{y}" width="{w}" height="26" rx="6" fill="{c}" fill-opacity="{.16 + i * .14:.2f}" stroke="{c}" stroke-opacity=".5">'
                   f'<animate attributeName="opacity" values="0;1" begin="{i * .25:.2f}s" dur=".4s" fill="freeze"/></rect>'
                   f'<text x="153" y="{y + 17}" text-anchor="middle" fill="{p["text"]}" font-family="{MONO}" font-size="11">{n}</text>')
    drops = "".join(f'<circle cx="{110 + (i * 23) % 90}" r="2.5" fill="{c}"><animate attributeName="cy" values="92;262" dur="2.4s" begin="{i * .4:.1f}s" repeatCount="indefinite"/>'
                    f'<animate attributeName="opacity" values="1;0" dur="2.4s" begin="{i * .4:.1f}s" repeatCount="indefinite"/></circle>' for i in range(6))
    # NDCG lift bars; the ALS baseline is derived from the stated +253% lift
    base = 0.1409 / 3.53
    bx, by, bw = 330, 112, 240
    bars = (f'<text x="{bx}" y="{by - 10}" fill="{p["mute"]}" font-family="{MONO}" font-size="10">NDCG@10</text>'
            f'<rect x="{bx}" y="{by}" width="{bw}" height="20" rx="5" fill="{p["line"]}"/>'
            f'<rect x="{bx}" y="{by}" width="{bw * base / .16:.0f}" height="20" rx="5" fill="{p["mute"]}"/>'
            f'<text x="{bx + bw * base / .16 + 8:.0f}" y="{by + 15}" fill="{p["sub"]}" font-family="{MONO}" font-size="11">ALS only</text>'
            f'<rect x="{bx}" y="{by + 34}" width="{bw}" height="20" rx="5" fill="{p["line"]}"/>'
            f'<rect x="{bx}" y="{by + 34}" width="0" height="20" rx="5" fill="{c}"><animate attributeName="width" values="0;{bw * .1409 / .16:.0f}" begin=".6s" dur="1.2s" fill="freeze"/></rect>'
            f'<text x="{bx + 8}" y="{by + 49}" fill="{p["bg"]}" font-family="{MONO}" font-size="11" font-weight="700">two-stage 0.1409</text>')
    body = f'''
{"".join(out)}{drops}
{bars}
{_metric(p, 330, 214, "+253%", "NDCG@10 over ALS", c, 30)}
{_metric(p, 476, 214, "<50 ms", "p95 serving", p["text"], 20)}
<text x="330" y="258" fill="{p["sub"]}" font-family="{SANS}" font-size="12.5">27 policy gates · REINFORCE + LinUCB</text>'''
    return _svg(W, H, "CineWave: NDCG@10 0.1409, 253% over ALS, p95 under 50 ms",
                _frame(p, c, "Spark ALS · LightGBM · Bandits", "CineWave", body), p)


# ----------------------------------------------------------------- 6. KWS: noise sweep

def card_kws(mode):
    p = PAL[mode]
    c = p["violet"]
    ox, oy, ww, hh = 28, 96, 544, 96
    bars = []
    for i in range(68):
        x = ox + 8 + i * 7.9
        sig = 0.25 + 0.75 * abs(math.sin(i * 0.31) * math.cos(i * 0.07))
        if 22 <= i <= 34:
            sig = min(1, sig + .5)  # the keyword
        h_clean = hh * .8 * sig
        noise = hh * .8 * (0.35 + 0.45 * abs(math.sin(i * 1.7)))
        h_noisy = max(h_clean, noise)
        col = c if 22 <= i <= 34 else p["sub"]
        bars.append(f'<rect x="{x:.1f}" width="4.4" rx="2.2" fill="{col}" y="{oy + hh / 2 - h_clean / 2:.1f}" height="{h_clean:.1f}" opacity="{.95 if 22 <= i <= 34 else .45}">'
                    f'<animate attributeName="height" values="{h_clean:.1f};{h_noisy:.1f};{h_clean:.1f}" dur="5s" repeatCount="indefinite"/>'
                    f'<animate attributeName="y" values="{oy + hh / 2 - h_clean / 2:.1f};{oy + hh / 2 - h_noisy / 2:.1f};{oy + hh / 2 - h_clean / 2:.1f}" dur="5s" repeatCount="indefinite"/></rect>')
    detect = (f'<rect x="{ox + 8 + 22 * 7.9 - 4:.0f}" y="{oy + 4}" width="{13 * 7.9 + 4:.0f}" height="{hh - 8}" rx="8" fill="none" stroke="{c}" stroke-width="2">'
              f'<animate attributeName="stroke-opacity" values="1;.3;1" dur="1.2s" repeatCount="indefinite"/></rect>'
              f'<text x="{ox + 8 + 28 * 7.9:.0f}" y="{oy - 6}" text-anchor="middle" fill="{c}" font-family="{MONO}" font-size="10">distress keyword</text>')
    # SNR readout that tracks the noise animation
    snr = (f'<text x="{ox + ww - 10}" y="{oy + 18}" text-anchor="end" fill="{p["mute"]}" font-family="{MONO}" font-size="10">'
           f'<tspan>SNR </tspan><tspan fill="{p["text"]}">clean<animate attributeName="opacity" values="1;0;1" keyTimes="0;.5;1" dur="5s" repeatCount="indefinite"/></tspan></text>'
           f'<text x="{ox + ww - 10}" y="{oy + 32}" text-anchor="end" fill="{p["crit"]}" font-family="{MONO}" font-size="10" opacity="0">0 dB noise'
           f'<animate attributeName="opacity" values="0;1;0" keyTimes="0;.5;1" dur="5s" repeatCount="indefinite"/></text>')
    body = f'''
<rect x="{ox}" y="{oy}" width="{ww}" height="{hh}" rx="12" fill="{p["bg"]}" stroke="{p["line"]}"/>
{"".join(bars)}{detect}{snr}
{_metric(p, 28, 236, "88.4%", "accuracy · clean", p["text"])}
{_metric(p, 150, 236, "77.0%", "accuracy · 0 dB SNR", c)}
{_metric(p, 300, 236, "0.43 MB", "model size", p["text"], 22)}
{_metric(p, 420, 236, "2.18 ms", "p95 on device", p["text"], 22)}
<text x="28" y="{H - 22}" fill="{p["sub"]}" font-family="{SANS}" font-size="13">In-cabin distress keywords, heard through real noise.</text>'''
    return _svg(W, H, "Noise-robust keyword spotting: 77.0% accuracy at 0 dB SNR, 0.43 MB model",
                _frame(p, c, "MFCC · CNN · PyTorch", "Noise-Robust KWS", body), p)


FLAGSHIP_CARDS = [
    ("opendrivefm", "OpenDriveFM", card_opendrivefm),
    ("guardian-drive", "Guardian Drive", card_guardian),
    ("autonomy-vision", "SafeTruck-AV2", card_safetruck),
    ("talentra_copilot", "Talentra Copilot", card_talentra),
    ("two-stage-recommender-als-ranker-api", "CineWave", card_cinewave),
    ("noise-robust-kws-distress-detection", "Noise-Robust KWS", card_kws),
]


# ----------------------------------------------------------------- 3D contribution city

LEVELS = {
    "dark": ["#161b22", "#0e4429", "#006d32", "#26a641", "#39d353"],
    "light": ["#ebedf0", "#9be9a8", "#40c463", "#30a14e", "#216e39"],
}
LANG_COLORS = {"Python": "#3572A5", "TypeScript": "#3178c6", "JavaScript": "#f1e05a", "Jupyter Notebook": "#DA5B0B",
               "HTML": "#e34c26", "Vue": "#41b883", "Java": "#b07219", "Go": "#00ADD8", "C++": "#f34b7d",
               "Shell": "#89e051", "R": "#198CE7", "CSS": "#563d7c"}


def _shade(hexc, k):
    hexc = hexc.lstrip("#")
    r, g, b = (int(hexc[i:i + 2], 16) for i in (0, 2, 4))
    return "#%02x%02x%02x" % (int(r * k), int(g * k), int(b * k))


def contrib_city(days, stats, langs, mode):
    """days: [{'d','c'}] oldest first. stats: dict with total, commits, prs, issues, reviews,
    repos, stars, streak, busiest. langs: [(name, weight)]."""
    p = PAL[mode]
    lv = LEVELS[mode]
    CW, CH = 1200, 680
    if not days:
        return _svg(CW, CH, "No contribution data yet", "", p)
    import datetime as _dt
    first = _dt.date.fromisoformat(days[0]["d"])
    start = first - _dt.timedelta(days=(first.weekday() + 1) % 7)  # Sunday on or before
    peak = max(d["c"] for d in days) or 1
    nonzero = sorted(d["c"] for d in days if d["c"] > 0)

    def level(cn):
        if cn <= 0:
            return 0
        q = [nonzero[int(len(nonzero) * f)] for f in (.25, .5, .75)] if nonzero else [1, 2, 3]
        return 1 + sum(cn > t for t in q)

    s = 15.5
    ax, ay = s * 0.866, s * 0.5
    ox, oy = 70, 178
    cols = []
    cells = []
    for d in days:
        dt = _dt.date.fromisoformat(d["d"])
        i = (dt - start).days // 7
        j = (dt.weekday() + 1) % 7
        cells.append((i + j, i, j, d))
    cells.sort(key=lambda t: (t[0], t[1]))
    for _, i, j, d in cells:
        bx = ox + (i - j + 7) * ax
        by = oy + (i + j) * ay
        cn = d["c"]
        lvl = level(cn)
        top = lv[lvl]
        h = 0 if cn <= 0 else 6 + 120 * math.sqrt(cn / peak)
        t = (f"0,{-h:.1f} {ax:.1f},{-h + ay:.1f} 0,{-h + 2 * ay:.1f} {-ax:.1f},{-h + ay:.1f}")
        left = f"{-ax:.1f},{-h + ay:.1f} 0,{-h + 2 * ay:.1f} 0,{2 * ay:.1f} {-ax:.1f},{ay:.1f}"
        right = f"0,{-h + 2 * ay:.1f} {ax:.1f},{-h + ay:.1f} {ax:.1f},{ay:.1f} 0,{2 * ay:.1f}"
        title = f'<title>{d["d"]}: {cn} contribution{"s" if cn != 1 else ""}</title>'
        if h == 0:
            cols.append(f'<polygon transform="translate({bx:.1f} {by:.1f})" points="{t}" fill="{top}" stroke="{p["bg"]}" stroke-width=".6">{title}</polygon>')
        else:
            delay = 0.2 + i * 0.035
            cols.append(f'<g transform="translate({bx:.1f} {by + 2 * ay:.1f})"><g>'
                        f'<animateTransform attributeName="transform" type="scale" values="1 0;1 1" dur=".7s" begin="{delay:.2f}s" fill="freeze"/>'
                        f'<g transform="translate(0 {-2 * ay:.1f})">'
                        f'<polygon points="{left}" fill="{_shade(top, .62)}"/><polygon points="{right}" fill="{_shade(top, .8)}"/>'
                        f'<polygon points="{t}" fill="{top}">{title}</polygon></g></g></g>')
    # radar (log scale), top-right
    rx, ry, rr = 980, 205, 108
    axes = [("Commit", stats.get("commits", 0)), ("Issue", stats.get("issues", 0)), ("PullReq", stats.get("prs", 0)),
            ("Review", stats.get("reviews", 0)), ("Repo", stats.get("repos", 0))]

    def rad(k):
        return math.radians(-90 + k * 72)
    rings = "".join(
        f'<polygon points="{" ".join(f"{rx + rr * f * math.cos(rad(k)):.1f},{ry + rr * f * math.sin(rad(k)):.1f}" for k in range(5))}" '
        f'fill="none" stroke="{p["mute"]}" stroke-opacity=".35" stroke-dasharray="3 4"/>' for f in (.25, .5, .75, 1))
    spokes = "".join(f'<line x1="{rx}" y1="{ry}" x2="{rx + rr * math.cos(rad(k)):.1f}" y2="{ry + rr * math.sin(rad(k)):.1f}" stroke="{p["mute"]}" stroke-opacity=".3"/>' for k in range(5))
    labels = "".join(f'<text x="{rx + (rr + 22) * math.cos(rad(k)):.1f}" y="{ry + (rr + 22) * math.sin(rad(k)) + 5:.1f}" text-anchor="middle" '
                     f'fill="{p["text"]}" font-family="{SANS}" font-size="14" font-weight="600">{n}</text>' for k, (n, _) in enumerate(axes))
    ticks = "".join(f'<text x="{rx + 4}" y="{ry - rr * f + 4:.1f}" fill="{p["mute"]}" font-family="{MONO}" font-size="9">{t}</text>'
                    for f, t in ((.25, "1"), (.5, "10"), (.75, "100"), (1, "1K+")))

    def rv(v):
        return 0 if v <= 0 else min(1.0, .25 + .25 * math.log10(v))
    shape = " ".join(f"{rx + rr * rv(v) * math.cos(rad(k)):.1f},{ry + rr * rv(v) * math.sin(rad(k)):.1f}" for k, (_, v) in enumerate(axes))
    radar = (f'{rings}{spokes}{ticks}{labels}'
             f'<g transform="translate({rx} {ry})"><g><animateTransform attributeName="transform" type="scale" values="0;1" dur="1s" begin=".6s" fill="freeze"/>'
             f'<polygon transform="translate({-rx} {-ry})" points="{shape}" fill="{lv[3]}" fill-opacity=".3" stroke="{lv[3]}" stroke-width="2.5"/></g></g>')
    # language donut, bottom-left
    dx, dy, dr = 130, 560, 70
    total_w = sum(w for _, w in langs) or 1
    acc, arcs, legend = 0.0, [], []
    circ = 2 * math.pi * dr
    for k, (name, w) in enumerate(langs):
        frac = w / total_w
        col = LANG_COLORS.get(name, p["mute"])
        arcs.append(f'<circle cx="{dx}" cy="{dy}" r="{dr}" fill="none" stroke="{col}" stroke-width="30" '
                    f'stroke-dasharray="0 {circ:.1f}" transform="rotate({-90 + acc * 360:.1f} {dx} {dy})">'
                    f'<animate attributeName="stroke-dasharray" values="0 {circ:.1f};{max(0, frac * circ - 1.5):.1f} {circ:.1f}" dur=".9s" begin="{.4 + k * .15:.2f}s" fill="freeze"/></circle>')
        legend.append(f'<rect x="{dx + 110}" y="{dy - 70 + k * 27}" width="16" height="16" rx="3" fill="{col}"/>'
                      f'<text x="{dx + 134}" y="{dy - 57 + k * 27}" fill="{p["text"]}" font-family="{SANS}" font-size="15">{escape(name)}</text>'
                      f'<text x="{dx + 290}" y="{dy - 57 + k * 27}" text-anchor="end" fill="{p["mute"]}" font-family="{MONO}" font-size="12">{frac:.0%}</text>')
        acc += frac
    # totals, stacked to the right of the ribbon
    tx, ty = 880, 430
    tot = (f'<text x="{tx}" y="{ty}" fill="{p["gold"]}" font-family="{SANS}" font-size="44" font-weight="800">{stats.get("total", 0):,}</text>'
           f'<text x="{tx}" y="{ty + 26}" fill="{p["text"]}" font-family="{SANS}" font-size="17">contributions in the last year</text>'
           f'<text x="{tx}" y="{ty + 72}" fill="{p["text"]}" font-family="{SANS}" font-size="24" font-weight="700">★ {stats.get("stars", 0)}</text>'
           f'<text x="{tx + 90}" y="{ty + 72}" fill="{p["text"]}" font-family="{SANS}" font-size="24" font-weight="700">{stats.get("repos", 0)} repos</text>'
           f'<text x="{tx}" y="{ty + 104}" fill="{p["sub"]}" font-family="{MONO}" font-size="12.5">longest streak {stats.get("streak", 0)} days</text>'
           f'<text x="{tx}" y="{ty + 124}" fill="{p["sub"]}" font-family="{MONO}" font-size="12.5">busiest day {escape(str(stats.get("busiest", "")))}</text>')
    rng = f'{days[0]["d"]} / {days[-1]["d"]}'
    body = (f'<text x="{CW - 28}" y="40" text-anchor="end" fill="{p["sub"]}" font-family="{SANS}" font-size="15">{rng}</text>'
            f'<text x="28" y="40" fill="{p["amber"]}" font-family="{MONO}" font-size="12" letter-spacing="2.4">CONTRIBUTION CITY · EACH COLUMN IS ONE DAY</text>'
            f'{"".join(cols)}{radar}{"".join(arcs)}{"".join(legend)}{tot}')
    return _svg(CW, CH, f"{stats.get('total', 0):,} contributions from {rng} as a 3D city of columns, with an activity radar and language mix", body, p)


def render(contrib, langs, mode_stats):
    for mode in PAL:
        for key, _, fn in FLAGSHIP_CARDS:
            _write(f"flag-{key}", mode, fn(mode))
        _write("contrib-city", mode, contrib_city(contrib, mode_stats, langs, mode))
