"""
🌊 Sea Wolf — Ocean Cleanup (McKinsey PSG Simulation)
Faithful reproduction of the 5-step per-site flow:
  Step 0: Review microbes saved from previous site (Sites 2 & 3 only)
  Step 1: Build microbe profile (choose 2 characteristics)
  Step 2: Categorize 10 microbes one-by-one (Keep / Save for Next / Reject)
  Step 3: Build prospect pool (6 given + pick 1-of-3 x 4 rounds = 10)
  Step 4: Create treatment (pick 3 from 10 prospects)
"""

import streamlit as st
import random
import time
from dataclasses import dataclass
from typing import List, Tuple, Dict, Set

# ─── CONSTANTS ─────────────────────────────────────────────────────────────────
TOTAL_TIME = 30 * 60
NUM_SITES = 3
PENALTY = 20

ALL_ATTRIBUTES = [
    "Permeability", "Rigidity", "Size", "Energy",
    "Adhesion", "Speed", "Density", "Mobility", "Fluidity"
]
ALL_TRAITS = [
    "Heat-resistant", "Aerobic", "Hydrophilic", "Bioluminescent",
    "Acidophilic", "UV-tolerant", "Phosphorus-removing",
    "Cryogenic", "Alkaliphilic", "Photosensitive"
]
PREFIXES = ["Cyro", "Ops", "Neo", "Flux", "Zeta", "Axo", "Viro", "Plex",
            "Kino", "Rho", "Sigma", "Tau", "Delta", "Omni", "Hexa", "Tera",
            "Lyso", "Quor", "Myco", "Ecto", "Endo", "Para", "Xeno", "Meso"]
SUFFIXES = ["Virus", "Amoeba", "Bacillus", "Spore", "Phage",
            "Coccus", "Flagella", "Microbe", "Cell", "Filament"]
ICONS = ["🦠", "🧫", "🔬", "💊", "🧬", "⚗️", "🫧", "🌀", "💠", "🔮",
         "🟣", "🔵", "🟢", "🟡", "⭕", "🔷", "🔶", "💎", "🌐", "⚛️"]


# ─── DATA CLASSES ──────────────────────────────────────────────────────────────
@dataclass
class Microbe:
    name: str
    icon: str
    attributes: Dict[str, int]
    trait: str

@dataclass
class SiteReqs:
    site_num: int
    attr_names: List[str]
    attr_ranges: Dict[str, Tuple[int, int]]
    desired_trait: str
    undesired_trait: str


# ─── GENERATION ────────────────────────────────────────────────────────────────
_used_names: Set[str] = set()

def make_name() -> str:
    global _used_names
    for _ in range(200):
        n = f"{random.choice(PREFIXES)} {random.choice(SUFFIXES)}"
        if n not in _used_names:
            _used_names.add(n)
            return n
    return f"M-{random.randint(1000, 9999)}"


def make_microbe(attr_names, desired, undesired) -> Microbe:
    attrs = {a: random.randint(1, 10) for a in attr_names}
    # Every microbe always has exactly 1 trait
    other = [t for t in ALL_TRAITS if t not in (desired, undesired)]
    r = random.random()
    if r < 0.35:
        trait = desired
    elif r < 0.50:
        trait = undesired
    else:
        trait = random.choice(other)
    return Microbe(name=make_name(), icon=random.choice(ICONS),
                   attributes=attrs, trait=trait)


def make_site(num, used_attrs, used_traits) -> SiteReqs:
    avail_a = [a for a in ALL_ATTRIBUTES if a not in used_attrs]
    if len(avail_a) < 3:
        avail_a = ALL_ATTRIBUTES.copy()
    attrs = random.sample(avail_a, 3)
    used_attrs.update(attrs)
    ranges = {}
    for a in attrs:
        lo = random.randint(1, 8)
        hi = lo + 2
        if hi > 10:
            lo, hi = 8, 10
        ranges[a] = (lo, hi)
    avail_t = [t for t in ALL_TRAITS if t not in used_traits]
    if len(avail_t) < 2:
        avail_t = ALL_TRAITS.copy()
    t2 = random.sample(avail_t, 2)
    used_traits.update(t2)
    return SiteReqs(num, attrs, ranges, t2[0], t2[1])


def generate_game():
    global _used_names
    _used_names = set()
    ua, ut = set(), set()
    sites = [make_site(i + 1, ua, ut) for i in range(NUM_SITES)]
    all_m = {}
    for si, site in enumerate(sites):
        pool = {
            "step2": [make_microbe(site.attr_names, site.desired_trait, site.undesired_trait) for _ in range(10)],
            "step3_given": [make_microbe(site.attr_names, site.desired_trait, site.undesired_trait) for _ in range(6)],
            "step3_rounds": [[make_microbe(site.attr_names, site.desired_trait, site.undesired_trait) for _ in range(3)] for _ in range(4)],
        }
        all_m[si] = pool
    return sites, all_m


# ─── SCORING ───────────────────────────────────────────────────────────────────
def score_treatment(site: SiteReqs, trio: List[Microbe]) -> Tuple[int, List[str]]:
    details, penalties = [], 0
    for a in site.attr_names:
        vals = [m.attributes[a] for m in trio]
        avg = sum(vals) / 3
        lo, hi = site.attr_ranges[a]
        ok = lo <= avg <= hi
        details.append(f"{'✅' if ok else '❌'} {a}: avg {avg:.1f}  (range {lo}–{hi})")
        if not ok:
            penalties += 1
    has_d = any(m.trait == site.desired_trait for m in trio)
    details.append(f"{'✅' if has_d else '❌'} Desired «{site.desired_trait}»: {'present' if has_d else 'MISSING'}")
    if not has_d:
        penalties += 1
    bad = [m.name for m in trio if m.trait == site.undesired_trait]
    if not bad:
        details.append(f"✅ Undesired «{site.undesired_trait}»: absent")
    else:
        penalties += len(bad)
        details.append(f"❌ Undesired «{site.undesired_trait}»: found in {', '.join(bad)} (−{len(bad) * 20}%)")
    return max(0, 100 - penalties * PENALTY), details


# ─── HTML HELPERS ──────────────────────────────────────────────────────────────
def fmt_time(s):
    return f"{s // 60:02d}:{s % 60:02d}"


def attr_fg(val, lo, hi):
    return "#e5e7eb"  # neutral light gray, no hint


def trait_html(t, desired, undesired):
    if t == desired:
        return f"<span style='background:#14532d;color:#86efac;padding:2px 10px;border-radius:6px;'>✅ {t}</span>"
    if t == undesired:
        return f"<span style='background:#7f1d1d;color:#fca5a5;padding:2px 10px;border-radius:6px;'>🚫 {t}</span>"
    return f"<span style='background:#1e293b;color:#d1d5db;padding:2px 10px;border-radius:6px;'>⚪ {t}</span>"


def card(m: Microbe, site: SiteReqs, border="#334155"):
    attr_spans = "".join(
        f"<span style='margin-right:16px;'>"
        f"<span style='color:#d1d5db;'>{a}:</span> "
        f"<b style='color:{attr_fg(m.attributes[a], *site.attr_ranges[a])};'>{m.attributes[a]}</b>"
        f"</span>"
        for a in site.attr_names
    )
    return f"""<div style="background:#0f172a;border:2px solid {border};border-radius:12px;
        padding:14px 18px;margin-bottom:8px;">
        <div style="font-size:1.1em;font-weight:700;color:#f1f5f9;margin-bottom:6px;">{m.icon} {m.name}</div>
        <div style="margin-bottom:6px;">{attr_spans}</div>
        <div>{trait_html(m.trait, site.desired_trait, site.undesired_trait)}</div>
    </div>"""


def site_box(site: SiteReqs):
    rows = "".join(
        f"<div style='display:inline-block;margin-right:28px;margin-bottom:6px;'>"
        f"<div style='color:#d1d5db;font-size:.78em;'>📊 {a}</div>"
        f"<div style='font-weight:700;font-size:1.15em;color:#f1f5f9;'>{lo} – {hi}</div></div>"
        for a in site.attr_names for lo, hi in [site.attr_ranges[a]]
    )
    return f"""<div style="background:#1e293b;border:1px solid #334155;border-radius:14px;
        padding:18px;margin-bottom:14px;">
        <div style="font-weight:700;color:#38bdf8;margin-bottom:10px;font-size:1.05em;">
            📍 Site {site.site_num} — Requirements</div>
        <div>{rows}</div>
        <div style="margin-top:10px;">
            <span style='background:#14532d;color:#86efac;padding:3px 12px;border-radius:6px;
                font-size:.88em;margin-right:14px;'>✅ Desired: {site.desired_trait}</span>
            <span style='background:#7f1d1d;color:#fca5a5;padding:3px 12px;border-radius:6px;
                font-size:.88em;'>🚫 Undesired: {site.undesired_trait}</span>
        </div></div>"""


def next_preview(site: SiteReqs):
    a = site.attr_names[0]
    lo, hi = site.attr_ranges[a]
    return f"""<div style="background:#1a1a2e;border:1px dashed #475569;border-radius:10px;
        padding:10px 14px;margin-top:10px;display:inline-block;">
        <span style="color:#b0b8c4;font-size:.82em;">👁 Next site preview — </span>
        <span style="color:#a5b4fc;font-weight:600;">{a}: {lo}–{hi}</span></div>"""


# ─── CSS ───────────────────────────────────────────────────────────────────────
CSS = """<style>
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;700;800&display=swap');
.stApp { background:#020617; color:#d1d5db; }
* { color:#d1d5db; }
h1,h2,h3,h4 { font-family:'Outfit',sans-serif !important; color:#e5e7eb !important; }
p, li, span, label, td, th, summary { color:#d1d5db !important; }
.big-title { font-family:'Outfit',sans-serif; font-size:2.6em; font-weight:800; text-align:center;
    background:linear-gradient(135deg,#22d3ee,#3b82f6,#a78bfa);
    -webkit-background-clip:text; -webkit-text-fill-color:transparent; }
.sub { text-align:center; color:#9ca3af !important; font-size:1.05em; margin-bottom:18px; }
.step-badge { display:inline-block; background:#1e40af; color:#dbeafe !important; padding:5px 16px;
    border-radius:8px; font-weight:700; font-size:.95em; }
.timer-box { font-family:'Outfit',sans-serif; text-align:center; font-size:2.2em;
    font-weight:700; padding:8px; border-radius:12px; }
.sbox { background:linear-gradient(135deg,#1e293b,#0f172a); border:1px solid #334155;
    border-radius:14px; padding:14px; text-align:center; }
.snum { font-family:'Outfit',sans-serif; font-size:2.2em; font-weight:800; }
.cat-sec { background:#0f172a; border:1px solid #1e293b; border-radius:10px;
    padding:10px 12px; min-height:60px; }
.cat-hd { font-weight:700; margin-bottom:4px; font-size:.88em; }
.cat-it { font-size:.82em; color:#d1d5db !important; padding:1px 0; }
.stCheckbox label span { color:#d1d5db !important; }
.stCheckbox label { color:#d1d5db !important; }
.stMarkdown p, .stMarkdown li, .stMarkdown span { color:#d1d5db !important; }
.stSlider label { color:#d1d5db !important; }
div[data-testid="stExpander"] summary span { color:#d1d5db !important; }
div[data-testid="stButton"] button { font-weight:600 !important; }
div[data-testid="stAlert"] p { color:#1f2937 !important; }
</style>"""


# ═══════════════════════════════════════════════════════════════════════════════
def main():
    st.set_page_config(page_title="🌊 Sea Wolf", layout="wide", initial_sidebar_state="collapsed")
    st.markdown(CSS, unsafe_allow_html=True)

    S = st.session_state
    defaults = dict(
        phase="menu", sites=None, microbes=None, cur_site=0, cur_step="step1",
        s2_index=0, s2_kept=None, s2_saved=None, s2_rejected=None,
        s0_index=0,
        s3_round=0, s3_prospects=None,
        s4_selection=None,
        site_scores=None, site_details=None,
        start_time=None,
    )
    for k, v in defaults.items():
        if k not in S:
            S[k] = v

    # ══════════════════════════════════════════════════════════════════════════
    #  MENU
    # ══════════════════════════════════════════════════════════════════════════
    if S.phase == "menu":
        st.markdown("&nbsp;", unsafe_allow_html=True)
        st.markdown('<div class="big-title">🌊 Sea Wolf</div>', unsafe_allow_html=True)
        st.markdown('<div class="sub">Ocean Cleanup — McKinsey PSG Simulation</div>', unsafe_allow_html=True)
        st.markdown("---")
        _, c2, _ = st.columns([1, 2, 1])
        with c2:
            st.markdown("""
### 🎯 Objective
Clean **3 ocean sites** by building optimal microbe treatments.

### 🔄 Flow per site

| Step | Action |
|------|--------|
| **Step 0** *(sites 2–3 only)* | Review microbes saved from the previous site |
| **Step 1** | Choose 2 profile characteristics |
| **Step 2** | 10 microbes shown **one by one** → Keep · Save for next · Reject |
| **Step 3** | Prospect pool: 6 given + pick **1 of 3** × 4 rounds = 10 |
| **Step 4** | Select **3 microbes** from 10 prospects → scored |

### 📏 Scoring (per site, max 100 %)
- Attribute avg out of range → **−20 %** each
- Desired trait missing → **−20 %**
- Each microbe with undesired trait → **−20 %**
""")
            st.markdown("")
            if st.button("🚀  Start Game", use_container_width=True, type="primary"):
                sites, microbes = generate_game()
                S.sites, S.microbes = sites, microbes
                S.phase = "playing"
                S.cur_site, S.cur_step = 0, "step1"
                S.start_time = time.time()
                S.s2_index, S.s0_index, S.s3_round = 0, 0, 0
                S.s2_kept = {i: [] for i in range(NUM_SITES)}
                S.s2_saved = {i: [] for i in range(NUM_SITES)}
                S.s2_rejected = {i: [] for i in range(NUM_SITES)}
                S.s3_prospects = {i: [] for i in range(NUM_SITES)}
                S.s4_selection = set()
                S.site_scores, S.site_details = {}, {}
                st.rerun()
        return

    # ══════════════════════════════════════════════════════════════════════════
    #  RESULTS
    # ══════════════════════════════════════════════════════════════════════════
    if S.phase == "results":
        st.markdown('<div class="big-title">🌊 Mission Complete</div>', unsafe_allow_html=True)
        st.markdown('<div class="sub">Final Treatment Report</div>', unsafe_allow_html=True)
        st.markdown("---")
        scores = [S.site_scores.get(i, 0) for i in range(NUM_SITES)]
        avg = sum(scores) / NUM_SITES
        gc = "#4ade80" if avg >= 80 else ("#fbbf24" if avg >= 50 else "#f87171")
        grade = ("🏆 Excellent!" if avg >= 80 else
                 "✅ Good" if avg >= 60 else
                 "⚠️ Needs work" if avg >= 40 else "❌ Below threshold")
        st.markdown(f"""<div style="text-align:center;padding:30px;background:#0f172a;
            border:2px solid {gc}40;border-radius:20px;margin-bottom:24px;">
            <div style="color:#d1d5db;">Overall Effectiveness</div>
            <div style="font-family:'Outfit',sans-serif;font-size:4em;font-weight:800;color:{gc};">{avg:.0f}%</div>
            <div style="font-size:1.2em;color:#f1f5f9;">{grade}</div>
            <div style="color:#9ca3af;margin-top:6px;">Total: {sum(scores)} / 300</div>
        </div>""", unsafe_allow_html=True)
        cols = st.columns(NUM_SITES)
        for i in range(NUM_SITES):
            sc = scores[i]
            c = "#4ade80" if sc >= 80 else ("#fbbf24" if sc >= 40 else "#f87171")
            with cols[i]:
                st.markdown(f'<div class="sbox"><div style="color:#d1d5db;font-size:.9em;">Site {i+1}</div>'
                            f'<div class="snum" style="color:{c};">{sc}%</div></div>', unsafe_allow_html=True)
                for d in S.site_details.get(i, []):
                    st.markdown(d)
        if S.start_time:
            used = min(time.time() - S.start_time, TOTAL_TIME)
            st.markdown(f"<div style='text-align:center;color:#9ca3af;margin-top:16px;'>"
                        f"⏱️ Time used: {fmt_time(int(used))} / {fmt_time(TOTAL_TIME)}</div>",
                        unsafe_allow_html=True)
        st.markdown("---")
        if st.button("🔄  Play Again", type="primary", use_container_width=True):
            S.phase = "menu"
            st.rerun()
        return

    # ══════════════════════════════════════════════════════════════════════════
    #  PLAYING
    # ══════════════════════════════════════════════════════════════════════════
    sites = S.sites
    si = S.cur_site
    site = sites[si]
    step = S.cur_step
    elapsed = time.time() - S.start_time
    remaining = max(0, TOTAL_TIME - int(elapsed))

    if remaining <= 0:
        for i in range(NUM_SITES):
            if i not in S.site_scores:
                S.site_scores[i] = 0
                S.site_details[i] = ["⏰ Time's up — site not completed"]
        S.phase = "results"
        st.rerun()

    # ── TOP BAR ──
    tc = "#4ade80" if remaining > 300 else ("#fbbf24" if remaining > 60 else "#f87171")
    t1, t2, t3, t4, t5 = st.columns([1.6, .9, .9, .9, 1.4])
    with t1:
        st.markdown(f'<div class="timer-box" style="color:{tc};">⏱️ {fmt_time(remaining)}</div>',
                    unsafe_allow_html=True)
    for idx, col in enumerate([t2, t3, t4]):
        with col:
            if idx in S.site_scores:
                sc = S.site_scores[idx]
                c = "#4ade80" if sc >= 80 else ("#fbbf24" if sc >= 40 else "#f87171")
                st.markdown(f'<div class="sbox"><div style="color:#d1d5db;font-size:.78em;">Site {idx+1}</div>'
                            f'<div class="snum" style="color:{c};">{sc}%</div></div>', unsafe_allow_html=True)
            else:
                lbl = "▶ Active" if idx == si else "◻ Pending"
                st.markdown(f'<div class="sbox"><div style="color:#d1d5db;font-size:.78em;">Site {idx+1}</div>'
                            f'<div style="color:#9ca3af;margin-top:4px;">{lbl}</div></div>', unsafe_allow_html=True)
    with t5:
        step_labels = {"step0": "Step 0 · Review", "step1": "Step 1 · Profile",
                       "step2": "Step 2 · Categorize", "step3": "Step 3 · Prospects",
                       "step4": "Step 4 · Treatment"}
        st.markdown(f'<div class="step-badge">{step_labels.get(step, step)}</div>',
                    unsafe_allow_html=True)

    st.markdown("---")
    st.markdown(site_box(site), unsafe_allow_html=True)

    # ──────────────────────────────────────────────────────────────────────────
    #  STEP 0
    # ──────────────────────────────────────────────────────────────────────────
    if step == "step0":
        prev_saved = S.s2_saved.get(si - 1, [])
        if not prev_saved:
            S.cur_step = "step1"
            st.rerun()
        idx = S.s0_index
        if idx >= len(prev_saved):
            S.cur_step = "step1"
            S.s0_index = 0
            st.rerun()

        st.markdown("### Step 0 — Review Saved Microbes")
        st.markdown(f"These microbes were saved for this site during the previous site's Step 2. "
                    f"**Keep** or **Reject** each one. ({idx + 1} / {len(prev_saved)})")
        m = prev_saved[idx]
        st.markdown(card(m, site, "#6366f1"), unsafe_allow_html=True)
        c1, c2, _ = st.columns([1, 1, 2])
        with c1:
            if st.button("✅  Keep for this site", key=f"s0k{idx}", use_container_width=True, type="primary"):
                S.s2_kept[si].append(m)
                S.s0_index += 1
                st.rerun()
        with c2:
            if st.button("🗑️  Reject", key=f"s0r{idx}", use_container_width=True):
                S.s0_index += 1
                st.rerun()

    # ──────────────────────────────────────────────────────────────────────────
    #  STEP 1
    # ──────────────────────────────────────────────────────────────────────────
    elif step == "step1":
        st.markdown("### Step 1 — Build Microbe Profile")
        st.markdown("Choose **2 characteristics** (attributes or traits) to define your preferred microbe profile. "
                    "This helps structure your approach for the next steps.")

        options = site.attr_names + [site.desired_trait, site.undesired_trait]
        extras = [t for t in ALL_TRAITS if t not in (site.desired_trait, site.undesired_trait)][:2]
        options += extras

        chosen = []
        cols = st.columns(3)
        for i, ch in enumerate(options):
            with cols[i % 3]:
                is_attr = ch in site.attr_names
                lbl = f"📊 {ch}" if is_attr else f"🧪 {ch}"
                if st.checkbox(lbl, key=f"s1c_{si}_{ch}"):
                    chosen.append(ch)

        if len(chosen) > 2:
            st.warning("⚠️ Select exactly 2 characteristics.")
        for ch in chosen[:2]:
            if ch in site.attr_names:
                lo, hi = site.attr_ranges[ch]
                st.slider(f"Preferred range for **{ch}**", 1, 10, (lo, hi), key=f"s1r_{si}_{ch}")

        st.markdown("")
        if st.button("✅  Confirm Profile & Continue →", type="primary",
                      disabled=len(chosen) != 2, use_container_width=True):
            S.cur_step = "step2"
            S.s2_index = 0
            st.rerun()

    # ──────────────────────────────────────────────────────────────────────────
    #  STEP 2 — Categorize 10 microbes one by one
    # ──────────────────────────────────────────────────────────────────────────
    elif step == "step2":
        pool = S.microbes[si]["step2"]
        idx = S.s2_index

        st.markdown("### Step 2 — Categorize Microbes")

        if idx >= len(pool):
            st.success(f"All 10 microbes categorized!  "
                       f"**Kept:** {len(S.s2_kept[si])}  ·  "
                       f"**Saved:** {len(S.s2_saved[si])}  ·  "
                       f"**Rejected:** {len(S.s2_rejected[si])}")
            if st.button("➡️  Continue to Step 3", type="primary", use_container_width=True):
                S.cur_step = "step3"
                S.s3_round = 0
                S.s3_prospects[si] = list(S.microbes[si]["step3_given"])
                st.rerun()
        else:
            st.markdown(f"**Microbe {idx + 1} / 10**")
            m = pool[idx]
            st.markdown(card(m, site, "#38bdf8"), unsafe_allow_html=True)

            if si < NUM_SITES - 1:
                st.markdown(next_preview(sites[si + 1]), unsafe_allow_html=True)

            c1, c2, c3 = st.columns(3)
            with c1:
                if st.button("✅  Keep for this site", key=f"s2k{si}_{idx}",
                              use_container_width=True, type="primary"):
                    S.s2_kept[si].append(m)
                    S.s2_index += 1
                    st.rerun()
            with c2:
                is_last = si >= NUM_SITES - 1
                if st.button("📦  Save for next site" if not is_last else "📦  N/A (last site)",
                              key=f"s2s{si}_{idx}", use_container_width=True, disabled=is_last):
                    S.s2_saved[si].append(m)
                    S.s2_index += 1
                    st.rerun()
            with c3:
                if st.button("🗑️  Reject", key=f"s2r{si}_{idx}", use_container_width=True):
                    S.s2_rejected[si].append(m)
                    S.s2_index += 1
                    st.rerun()

        # Categorized summary
        st.markdown("---")
        cc1, cc2, cc3 = st.columns(3)
        with cc1:
            st.markdown(f"<div class='cat-sec'><div class='cat-hd' style='color:#4ade80;'>"
                        f"✅ Kept ({len(S.s2_kept[si])})</div>", unsafe_allow_html=True)
            for km in S.s2_kept[si]:
                st.markdown(f"<div class='cat-it'>{km.icon} {km.name}</div>", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)
        with cc2:
            st.markdown(f"<div class='cat-sec'><div class='cat-hd' style='color:#a78bfa;'>"
                        f"📦 Saved ({len(S.s2_saved[si])})</div>", unsafe_allow_html=True)
            for sm in S.s2_saved[si]:
                st.markdown(f"<div class='cat-it'>{sm.icon} {sm.name}</div>", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)
        with cc3:
            st.markdown(f"<div class='cat-sec'><div class='cat-hd' style='color:#9ca3af;'>"
                        f"🗑️ Rejected ({len(S.s2_rejected[si])})</div>", unsafe_allow_html=True)
            for rm in S.s2_rejected[si]:
                st.markdown(f"<div class='cat-it'>{rm.icon} {rm.name}</div>", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)

    # ──────────────────────────────────────────────────────────────────────────
    #  STEP 3 — Build prospect pool
    # ──────────────────────────────────────────────────────────────────────────
    elif step == "step3":
        prospects = S.s3_prospects[si]
        rnd = S.s3_round
        rounds_data = S.microbes[si]["step3_rounds"]

        st.markdown("### Step 3 — Build Prospect Pool")
        st.markdown(f"**{len(prospects)} / 10** prospects in pool.  "
                    f"6 given + pick 1 of 3 in each round.")

        with st.expander(f"📋 Current prospects ({len(prospects)})", expanded=False):
            for p in prospects:
                st.markdown(card(p, site), unsafe_allow_html=True)

        if rnd >= 4:
            st.success(f"Prospect pool complete! ({len(prospects)} microbes)")
            if st.button("➡️  Continue to Step 4", type="primary", use_container_width=True):
                S.cur_step = "step4"
                S.s4_selection = set()
                st.rerun()
        else:
            st.markdown(f"#### Round {rnd + 1} of 4 — Pick 1 of 3")
            cands = rounds_data[rnd]
            cols = st.columns(3)
            for ci, cand in enumerate(cands):
                with cols[ci]:
                    st.markdown(card(cand, site, "#475569"), unsafe_allow_html=True)
                    if st.button(f"✅ Select", key=f"s3p{si}_{rnd}_{ci}",
                                  use_container_width=True, type="primary"):
                        S.s3_prospects[si].append(cand)
                        S.s3_round += 1
                        st.rerun()

    # ──────────────────────────────────────────────────────────────────────────
    #  STEP 4 — Create treatment
    # ──────────────────────────────────────────────────────────────────────────
    elif step == "step4":
        prospects = S.s3_prospects[si]
        sel = S.s4_selection if S.s4_selection else set()

        st.markdown("### Step 4 — Create Treatment")
        st.markdown(f"Select **3 microbes** from your prospects to form the treatment.  ({len(sel)} / 3 selected)")

        # Live preview
        if sel:
            sel_ms = [prospects[j] for j in sel]
            pcols = st.columns(len(site.attr_names) + 2)
            for ai, a in enumerate(site.attr_names):
                vals = [m_.attributes[a] for m_ in sel_ms]
                avg = sum(vals) / len(vals)
                lo, hi = site.attr_ranges[a]
                ok = lo <= avg <= hi
                c = "#4ade80" if ok else "#f87171"
                with pcols[ai]:
                    st.markdown(f"<div style='text-align:center;'>"
                                f"<div style='color:#d1d5db;font-size:.75em;'>Avg {a}</div>"
                                f"<div style='color:{c};font-weight:700;font-size:1.3em;'>{avg:.1f}</div>"
                                f"<div style='color:#9ca3af;font-size:.7em;'>target {lo}–{hi}</div></div>",
                                unsafe_allow_html=True)
            with pcols[-2]:
                has_d = any(m_.trait == site.desired_trait for m_ in sel_ms)
                st.markdown(f"<div style='text-align:center;'>"
                            f"<div style='font-size:1.2em;'>{'✅' if has_d else '⚠️'}</div>"
                            f"<div style='color:#d1d5db;font-size:.7em;'>Desired</div></div>",
                            unsafe_allow_html=True)
            with pcols[-1]:
                has_u = any(m_.trait == site.undesired_trait for m_ in sel_ms)
                st.markdown(f"<div style='text-align:center;'>"
                            f"<div style='font-size:1.2em;'>{'✅' if not has_u else '🚨'}</div>"
                            f"<div style='color:#d1d5db;font-size:.7em;'>No undesired</div></div>",
                            unsafe_allow_html=True)

        st.markdown("---")

        col_l, col_r = st.columns(2)
        for pi, p in enumerate(prospects):
            col = col_l if pi < 5 else col_r
            with col:
                is_sel = pi in sel
                border = "#3b82f6" if is_sel else "#1e293b"
                st.markdown(card(p, site, border), unsafe_allow_html=True)
                disabled = len(sel) >= 3 and not is_sel
                checked = st.checkbox(f"Select {p.icon} {p.name}", value=is_sel,
                                      key=f"s4c{si}_{pi}", disabled=disabled)
                if checked and pi not in sel:
                    S.s4_selection.add(pi)
                    st.rerun()
                elif not checked and pi in sel:
                    S.s4_selection.discard(pi)
                    st.rerun()

        st.markdown("---")

        # Score preview
        can_submit = len(sel) == 3
        if can_submit:
            trio = [prospects[j] for j in sel]
            prev_score, prev_det = score_treatment(site, trio)
            sc_c = "#4ade80" if prev_score >= 80 else ("#fbbf24" if prev_score >= 40 else "#f87171")
            st.markdown(f"<div style='background:#0f172a;border:1px solid #334155;border-radius:12px;"
                        f"padding:16px;text-align:center;margin-bottom:12px;'>"
                        f"<div style='font-weight:700;color:{sc_c};font-size:1.5em;'>"
                        f"Preview: {prev_score}% effectiveness</div></div>", unsafe_allow_html=True)
            for d in prev_det:
                st.markdown(d)

        if st.button("🔬  Submit Treatment", type="primary",
                      disabled=not can_submit, use_container_width=True):
            trio = [prospects[j] for j in sel]
            score, details = score_treatment(site, trio)
            S.site_scores[si] = score
            S.site_details[si] = details
            if si < NUM_SITES - 1:
                S.cur_site = si + 1
                S.cur_step = "step0" if S.s2_saved.get(si, []) else "step1"
                S.s4_selection = set()
                S.s2_index = 0
                S.s0_index = 0
                S.s3_round = 0
            else:
                S.phase = "results"
            st.rerun()


if __name__ == "__main__":
    main()
