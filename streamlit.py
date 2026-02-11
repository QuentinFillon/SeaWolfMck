"""
🌊 Sea Wolf — Ocean Cleanup (McKinsey PSG Simulation)
Faithful reproduction of the 5-step per-site flow:
  Step 0: Review microbes saved from previous site (Sites 2 & 3 only)
  Step 1: Build microbe profile (choose 2 characteristics out of 8)
  Step 2: Categorize 10 microbes one-by-one (Keep / Save for Next / Reject)
  Step 3: Build prospect pool (6 given + pick 1-of-3 × 4 rounds = 10)
  Step 4: Create treatment (pick 3 from 10 prospects)

Scoring:
  - 100% default
  - -20% per attribute avg out of range (max -60%)
  - -20% if desired trait missing
  - -20% per undesired microbe in trio (max -60%)

FIX APPLIED:
  - Step 3 prospect pool now INITIALIZES with microbes kept in Step 2 (up to 6),
    then fills remaining slots with the 6 "given" microbes (no duplicates).
"""

import streamlit as st
import random
import time
from dataclasses import dataclass
from typing import List, Tuple, Dict, Set


# ─── CONSTANTS ────────────────────────────────────────────────────────────────
TOTAL_TIME = 30 * 60
NUM_SITES = 3
PENALTY = 20

FIXED_ATTRIBUTES = ["Permeability", "Mobility", "Energy"]

# Always width-2 intervals
POSSIBLE_RANGES = [(1, 3), (2, 4), (3, 5), (4, 6), (5, 7), (6, 8), (7, 9), (8, 10)]

ALL_TRAITS = [
    "Heat-resistant", "Aerobic", "Hydrophilic", "Bioluminescent",
    "Acidophilic", "UV-tolerant", "Phosphorus-removing",
    "Cryogenic", "Alkaliphilic", "Photosensitive",
    "Thermophilic", "Anaerobic", "Magnetotactic",
    "Halophilic", "Chemotrophic",
]

PREFIXES = [
    "Cyro", "Ops", "Neo", "Flux", "Zeta", "Axo", "Viro", "Plex",
    "Kino", "Rho", "Sigma", "Tau", "Delta", "Omni", "Hexa", "Tera",
    "Lyso", "Quor", "Myco", "Ecto", "Endo", "Para", "Xeno", "Meso"
]

SUFFIXES = ["Virus", "Amoeba", "Bacillus", "Spore", "Phage", "Coccus", "Flagella", "Microbe", "Cell", "Filament"]

ICONS = ["🦠", "🧫", "🔬", "💊", "🧬", "⚗️", "🫧", "🌀", "💠", "🔮",
         "🟣", "🔵", "🟢", "🟡", "⭕", "🔷", "🔶", "💎", "🌐", "⚛️"]


# ─── DATA CLASSES ─────────────────────────────────────────────────────────────
@dataclass
class Microbe:
    name: str
    icon: str
    attributes: Dict[str, int]   # Permeability, Mobility, Energy (1-10)
    trait: str                   # exactly 1 trait

    def __hash__(self):
        return hash(self.name)

    def __eq__(self, other):
        return isinstance(other, Microbe) and self.name == other.name


@dataclass
class SiteReqs:
    site_num: int
    attr_names: List[str]
    attr_ranges: Dict[str, Tuple[int, int]]
    desired_trait: str
    undesired_trait: str
    neutral_traits: List[str]
    all_traits: List[str]


# ─── GENERATION (one-time at game start) ──────────────────────────────────────
def _make_name(used_names: Set[str], rng: random.Random) -> str:
    for _ in range(200):
        n = f"{rng.choice(PREFIXES)} {rng.choice(SUFFIXES)}"
        if n not in used_names:
            used_names.add(n)
            return n
    return f"M-{rng.randint(1000, 9999)}"


def _make_microbe(used_names: Set[str], rng: random.Random,
                  site_traits: List[str], desired: str, undesired: str) -> dict:
    """Create a microbe dict (serializable for session state)."""
    attrs = {a: rng.randint(1, 10) for a in FIXED_ATTRIBUTES}
    # Each microbe gets exactly 1 trait from the site's 5 traits
    r = rng.random()
    if r < 0.30:
        trait = desired
    elif r < 0.45:
        trait = undesired
    else:
        trait = rng.choice(site_traits)  # could be any of the 5
    return {
        "name": _make_name(used_names, rng),
        "icon": rng.choice(ICONS),
        "attributes": attrs,
        "trait": trait,
    }


def _make_site(num: int, used_traits: Set[str], rng: random.Random) -> dict:
    """Create a site requirements dict."""
    ranges = {a: rng.choice(POSSIBLE_RANGES) for a in FIXED_ATTRIBUTES}

    avail_t = [t for t in ALL_TRAITS if t not in used_traits]
    if len(avail_t) < 5:
        avail_t = ALL_TRAITS.copy()
    t5 = rng.sample(avail_t, 5)
    used_traits.update(t5)

    return {
        "site_num": num,
        "attr_names": list(FIXED_ATTRIBUTES),
        "attr_ranges": ranges,
        "desired_trait": t5[0],
        "undesired_trait": t5[1],
        "neutral_traits": t5[2:],
        "all_traits": t5,
    }


def generate_game(seed=None):
    """Generate all sites and all microbes upfront. Returns serializable dicts."""
    rng = random.Random(seed)
    used_names: Set[str] = set()
    used_traits: Set[str] = set()

    sites = [_make_site(i + 1, used_traits, rng) for i in range(NUM_SITES)]
    all_microbes = {}

    for si, site in enumerate(sites):
        d = site["desired_trait"]
        u = site["undesired_trait"]
        traits = site["all_traits"]

        pool = {
            "step2": [_make_microbe(used_names, rng, traits, d, u) for _ in range(10)],
            "step3_given": [_make_microbe(used_names, rng, traits, d, u) for _ in range(6)],
            "step3_rounds": [
                [_make_microbe(used_names, rng, traits, d, u) for _ in range(3)]
                for _ in range(4)
            ],
        }
        all_microbes[si] = pool

    return sites, all_microbes


# ─── HELPERS (dict -> dataclass) ──────────────────────────────────────────────
def to_microbe(d: dict) -> Microbe:
    return Microbe(name=d["name"], icon=d["icon"], attributes=d["attributes"], trait=d["trait"])


def to_site(d: dict) -> SiteReqs:
    ar = {}
    for k, v in d["attr_ranges"].items():
        ar[k] = tuple(v) if isinstance(v, list) else v
    return SiteReqs(
        site_num=d["site_num"],
        attr_names=d["attr_names"],
        attr_ranges=ar,
        desired_trait=d["desired_trait"],
        undesired_trait=d["undesired_trait"],
        neutral_traits=d["neutral_traits"],
        all_traits=d["all_traits"],
    )


# ─── SCORING ──────────────────────────────────────────────────────────────────
def score_treatment(site: SiteReqs, trio: List[Microbe]) -> Tuple[int, List[str]]:
    details, penalties = [], 0

    for a in site.attr_names:
        vals = [m.attributes[a] for m in trio]
        avg = sum(vals) / 3
        lo, hi = site.attr_ranges[a]
        ok = lo <= avg <= hi
        details.append(f"{'✅' if ok else '❌'} {a}: avg {avg:.1f} (range {lo}–{hi})")
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


# ─── HTML HELPERS ─────────────────────────────────────────────────────────────
def fmt_time(s: int) -> str:
    return f"{s // 60:02d}:{s % 60:02d}"


def trait_html(t: str, desired: str, undesired: str) -> str:
    if t == desired:
        return f"<span style='background:#14532d;color:#86efac;padding:2px 10px;border-radius:6px;'>✅ {t}</span>"
    if t == undesired:
        return f"<span style='background:#7f1d1d;color:#fca5a5;padding:2px 10px;border-radius:6px;'>🚫 {t}</span>"
    return f"<span style='background:#1e293b;color:#d1d5db;padding:2px 10px;border-radius:6px;'>⚪ {t}</span>"


def card(m: Microbe, site: SiteReqs, border="#334155") -> str:
    attr_spans = "".join(
        f"<span style='margin-right:16px;'>"
        f"<span style='color:#d1d5db;'>{a}:</span> "
        f"<b style='color:#e5e7eb;'>{m.attributes[a]}</b>"
        f"</span>"
        for a in site.attr_names
    )
    return f"""
    <div style="background:#0f172a;border:2px solid {border};border-radius:12px;
         padding:14px 18px;margin-bottom:8px;">
      <div style="font-size:1.1em;font-weight:700;color:#f1f5f9;margin-bottom:6px;">{m.icon} {m.name}</div>
      <div style="margin-bottom:6px;">{attr_spans}</div>
      <div>{trait_html(m.trait, site.desired_trait, site.undesired_trait)}</div>
    </div>
    """


def site_box(site: SiteReqs) -> str:
    rows = "".join(
        f"<div style='display:inline-block;margin-right:28px;margin-bottom:6px;'>"
        f"<div style='color:#d1d5db;font-size:.78em;'>📊 {a}</div>"
        f"<div style='font-weight:700;font-size:1.15em;color:#f1f5f9;'>{lo} – {hi}</div></div>"
        for a in site.attr_names for lo, hi in [site.attr_ranges[a]]
    )
    return f"""
    <div style="background:#1e293b;border:1px solid #334155;border-radius:14px;
         padding:18px;margin-bottom:14px;">
      <div style="font-weight:700;color:#38bdf8;margin-bottom:10px;font-size:1.05em;">
        📍 Site {site.site_num} — Requirements</div>
      <div>{rows}</div>
      <div style="margin-top:10px;">
        <span style='background:#14532d;color:#86efac;padding:3px 12px;border-radius:6px;
              font-size:.88em;margin-right:14px;'>✅ Desired: {site.desired_trait}</span>
        <span style='background:#7f1d1d;color:#fca5a5;padding:3px 12px;border-radius:6px;
              font-size:.88em;margin-right:14px;'>🚫 Undesired: {site.undesired_trait}</span>
      </div>
    </div>
    """


def next_site_preview(next_site: SiteReqs) -> str:
    """Show a single attribute hint for the next site (like the real game)."""
    rng = random.Random(next_site.site_num)
    a = rng.choice(FIXED_ATTRIBUTES)
    lo, hi = next_site.attr_ranges[a]
    show_trait = next_site.desired_trait if rng.random() < 0.5 else next_site.undesired_trait
    trait_label = "Desired" if show_trait == next_site.desired_trait else "Undesired"
    return f"""
    <div style="background:#1a1a2e;border:1px dashed #9ca3af;border-radius:10px;
         padding:10px 14px;margin-top:10px;display:inline-block;">
      <span style="color:#b0b8c4;font-size:.82em;">👁 Next site preview — </span>
      <span style="color:#a5b4fc;font-weight:600;">{a}: {lo}–{hi}</span>
      <span style="color:#9ca3af;margin-left:14px;font-size:.82em;">{trait_label}: {show_trait}</span>
    </div>
    """


# ─── CSS ──────────────────────────────────────────────────────────────────────
CSS = """
<style>
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
</style>
"""


# ─── CORE APP ─────────────────────────────────────────────────────────────────
def reset_state():
    S = st.session_state
    defaults = dict(
        phase="menu",
        sites=None,
        microbes=None,
        cur_site=0,
        cur_step="step1",
        s2_index=0,
        s2_kept=None,
        s2_saved=None,
        s2_rejected=None,
        s0_index=0,
        s3_round=0,
        s3_prospects=None,
        s4_selection=None,
        site_scores=None,
        site_details=None,
        start_time=None,
        seed=None,
    )
    for k, v in defaults.items():
        if k not in S:
            S[k] = v


def init_new_game():
    S = st.session_state
    seed = int(time.time() * 1000) % (2**31)
    sites, microbes = generate_game(seed)

    S.seed = seed
    S.sites = sites
    S.microbes = microbes

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


def go_next_site_or_results():
    S = st.session_state
    si = S.cur_site
    if si < NUM_SITES - 1:
        S.cur_site = si + 1
        # Step 0 only if previous site saved microbes exist
        S.cur_step = "step0" if S.s2_saved.get(si, []) else "step1"

        S.s4_selection = set()
        S.s2_index = 0
        S.s0_index = 0
        S.s3_round = 0
    else:
        S.phase = "results"


def build_step3_initial_prospects(si: int) -> List[dict]:
    """
    FIX: Start Step 3 with microbes kept in Step 2 (up to 6),
         then fill with step3_given to reach 6 (no duplicates).
    """
    S = st.session_state
    kept = list(S.s2_kept[si])                 # kept microbes from Step 2
    given = list(S.microbes[si]["step3_given"])  # fallback fillers

    prospects0 = []
    seen = set()

    for m in kept:
        n = m.get("name")
        if n and n not in seen:
            prospects0.append(m)
            seen.add(n)
        if len(prospects0) == 6:
            return prospects0

    for m in given:
        n = m.get("name")
        if n and n not in seen:
            prospects0.append(m)
            seen.add(n)
        if len(prospects0) == 6:
            break

    return prospects0


def main():
    st.set_page_config(page_title="🌊 Sea Wolf", layout="wide", initial_sidebar_state="collapsed")
    st.markdown(CSS, unsafe_allow_html=True)

    reset_state()
    S = st.session_state

    # ───────────────────────────── MENU ──────────────────────────────────────
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

Each site has **3 numerical attributes** (target ranges like 1–3, 4–6, 8–10)
and **5 traits** (1 desired, 1 undesired, 3 neutral).

### 🔄 Flow per site
| Step | Action |
|------|--------|
| **Step 0** *(sites 2–3 only)* | Review microbes saved from the previous site |
| **Step 1** | Choose 2 characteristics from 8 (3 attrs + 5 traits) |
| **Step 2** | 10 microbes shown **one by one** → Keep · Save for next · Reject |
| **Step 3** | Prospect pool: **6 starters** + pick **1 of 3** × 4 rounds = 10 |
| **Step 4** | Select **3 microbes** from 10 prospects → scored |

### 📏 Scoring (per site, max 100 %)
- Attribute avg out of range → **−20 %** each (max −60 %)
- Desired trait missing → **−20 %**
- Each microbe with undesired trait → **−20 %** each (max −60 %)
""")
            if st.button("🚀 Start Game", use_container_width=True, type="primary"):
                init_new_game()
                st.rerun()
        return

    # ───────────────────────────── RESULTS ───────────────────────────────────
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

        st.markdown(f"""
        <div style="text-align:center;padding:30px;background:#0f172a;
             border:2px solid {gc}40;border-radius:20px;margin-bottom:24px;">
          <div style="color:#d1d5db;">Overall Effectiveness</div>
          <div style="font-family:'Outfit',sans-serif;font-size:4em;font-weight:800;color:{gc};">{avg:.0f}%</div>
          <div style="font-size:1.2em;color:#f1f5f9;">{grade}</div>
          <div style="color:#9ca3af;margin-top:6px;">Total: {sum(scores)} / 300</div>
        </div>
        """, unsafe_allow_html=True)

        cols = st.columns(NUM_SITES)
        for i in range(NUM_SITES):
            sc = scores[i]
            c = "#4ade80" if sc >= 80 else ("#fbbf24" if sc >= 40 else "#f87171")
            with cols[i]:
                st.markdown(
                    f"<div class='sbox'><div style='color:#d1d5db;font-size:.78em;'>Site {i+1}</div>"
                    f"<div class='snum' style='color:{c};'>{sc}%</div></div>",
                    unsafe_allow_html=True
                )
                for d in S.site_details.get(i, []):
                    st.markdown(d)

        if S.start_time:
            used = min(time.time() - S.start_time, TOTAL_TIME)
            st.markdown(
                f"<div style='text-align:center;color:#9ca3af;margin-top:16px;'>"
                f"⏱️ Time used: {fmt_time(int(used))} / {fmt_time(TOTAL_TIME)}</div>",
                unsafe_allow_html=True
            )

        st.markdown("---")
        if st.button("🔄 Play Again", type="primary", use_container_width=True):
            for k in list(st.session_state.keys()):
                del st.session_state[k]
            st.rerun()
        return

    # ───────────────────────────── PLAYING ───────────────────────────────────
    sites_data = S.sites
    si = S.cur_site
    site = to_site(sites_data[si])
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
        st.markdown(f"<div class='timer-box' style='color:{tc};'>⏱️ {fmt_time(remaining)}</div>",
                    unsafe_allow_html=True)

    for idx, col in enumerate([t2, t3, t4]):
        with col:
            if idx in S.site_scores:
                sc = S.site_scores[idx]
                c = "#4ade80" if sc >= 80 else ("#fbbf24" if sc >= 40 else "#f87171")
                st.markdown(
                    f"<div class='sbox'><div style='color:#d1d5db;font-size:.78em;'>Site {idx+1}</div>"
                    f"<div class='snum' style='color:{c};'>{sc}%</div></div>",
                    unsafe_allow_html=True
                )
            else:
                lbl = "▶ Active" if idx == si else "◻ Pending"
                st.markdown(
                    f"<div class='sbox'><div style='color:#d1d5db;font-size:.78em;'>Site {idx+1}</div>"
                    f"<div style='color:#9ca3af;margin-top:4px;'>{lbl}</div></div>",
                    unsafe_allow_html=True
                )

    with t5:
        step_labels = {
            "step0": "Step 0 · Review",
            "step1": "Step 1 · Profile",
            "step2": "Step 2 · Categorize",
            "step3": "Step 3 · Prospects",
            "step4": "Step 4 · Treatment",
        }
        st.markdown(f"<div class='step-badge'>{step_labels.get(step, step)}</div>", unsafe_allow_html=True)

    st.markdown("---")
    st.markdown(site_box(site), unsafe_allow_html=True)

    # ───────────────────────────── STEP 0 ────────────────────────────────────
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
        st.markdown(
            f"These microbes were saved for this site during the previous site's Step 2. "
            f"**Keep** or **Reject** each one. ({idx + 1} / {len(prev_saved)})"
        )

        m_data = prev_saved[idx]
        m = to_microbe(m_data)
        st.markdown(card(m, site, "#6366f1"), unsafe_allow_html=True)

        c1, c2, _ = st.columns([1, 1, 2])
        with c1:
            if st.button("✅ Keep for this site", key=f"s0k{si}_{idx}", use_container_width=True, type="primary"):
                S.s2_kept[si].append(m_data)
                S.s0_index += 1
                st.rerun()
        with c2:
            if st.button("🗑️ Reject", key=f"s0r{si}_{idx}", use_container_width=True):
                S.s0_index += 1
                st.rerun()

    # ───────────────────────────── STEP 1 ────────────────────────────────────
    elif step == "step1":
        st.markdown("### Step 1 — Build Microbe Profile")
        st.markdown("Choose **2 characteristics** (attributes or traits).")

        chosen = []

        st.markdown("**📊 Numerical Attributes:**")
        cols_a = st.columns(3)
        for i, attr in enumerate(FIXED_ATTRIBUTES):
            with cols_a[i]:
                lo, hi = site.attr_ranges[attr]
                if st.checkbox(f"📊 {attr} ({lo}–{hi})", key=f"s1c_{si}_{attr}"):
                    chosen.append(attr)

        st.markdown("**🧪 Traits:**")
        cols_t = st.columns(3)
        for i, tr in enumerate(site.all_traits):
            with cols_t[i % 3]:
                if tr == site.desired_trait:
                    label = f"✅ {tr} (Desired)"
                elif tr == site.undesired_trait:
                    label = f"🚫 {tr} (Undesired)"
                else:
                    label = f"⚪ {tr}"
                if st.checkbox(label, key=f"s1c_{si}_{tr}"):
                    chosen.append(tr)

        if len(chosen) > 2:
            st.warning("⚠️ Select exactly 2 characteristics. (Only first 2 will be used for sliders below.)")

        for ch in chosen[:2]:
            if ch in FIXED_ATTRIBUTES:
                lo, hi = site.attr_ranges[ch]
                st.slider(f"Preferred range for **{ch}**", 1, 10, (lo, hi), key=f"s1r_{si}_{ch}")

        if st.button("✅ Confirm Profile & Continue →", type="primary", disabled=(len(chosen) != 2), use_container_width=True):
            S.cur_step = "step2"
            S.s2_index = 0
            st.rerun()

    # ───────────────────────────── STEP 2 ────────────────────────────────────
    elif step == "step2":
        pool = S.microbes[si]["step2"]  # stable list
        idx = S.s2_index

        st.markdown("### Step 2 — Categorize Microbes")

        if idx >= len(pool):
            st.success(
                f"All 10 microbes categorized! "
                f"**Kept:** {len(S.s2_kept[si])} · "
                f"**Saved:** {len(S.s2_saved[si])} · "
                f"**Rejected:** {len(S.s2_rejected[si])}"
            )
            if st.button("➡️ Continue to Step 3", type="primary", use_container_width=True):
                S.cur_step = "step3"
                S.s3_round = 0

                # ✅ FIX: Initialize Step 3 prospects from kept microbes (up to 6), then fill with given
                S.s3_prospects[si] = build_step3_initial_prospects(si)

                st.rerun()
        else:
            st.markdown(f"**Microbe {idx + 1} / 10**")
            m_data = pool[idx]
            m = to_microbe(m_data)
            st.markdown(card(m, site, "#38bdf8"), unsafe_allow_html=True)

            if si < NUM_SITES - 1:
                next_site = to_site(sites_data[si + 1])
                st.markdown(next_site_preview(next_site), unsafe_allow_html=True)

            c1, c2, c3 = st.columns(3)
            with c1:
                if st.button(f"✅ Keep for Site {si + 1}", key=f"s2k{si}_{idx}", use_container_width=True, type="primary"):
                    S.s2_kept[si].append(m_data)
                    S.s2_index += 1
                    st.rerun()
            with c2:
                is_last = si >= NUM_SITES - 1
                btn_label = f"📦 Save for Site {si + 2}" if not is_last else "📦 N/A (last site)"
                if st.button(btn_label, key=f"s2s{si}_{idx}", use_container_width=True, disabled=is_last):
                    S.s2_saved[si].append(m_data)
                    S.s2_index += 1
                    st.rerun()
            with c3:
                if st.button("🗑️ Reject", key=f"s2r{si}_{idx}", use_container_width=True):
                    S.s2_rejected[si].append(m_data)
                    S.s2_index += 1
                    st.rerun()

            st.markdown("---")
            cc1, cc2, cc3 = st.columns(3)
            with cc1:
                st.markdown(
                    f"<div class='cat-sec'><div class='cat-hd' style='color:#4ade80;'>✅ Kept ({len(S.s2_kept[si])})</div>",
                    unsafe_allow_html=True
                )
                for km in S.s2_kept[si]:
                    st.markdown(f"<div class='cat-it'>{km['icon']} {km['name']}</div>", unsafe_allow_html=True)
                st.markdown("</div>", unsafe_allow_html=True)
            with cc2:
                st.markdown(
                    f"<div class='cat-sec'><div class='cat-hd' style='color:#a78bfa;'>📦 Saved ({len(S.s2_saved[si])})</div>",
                    unsafe_allow_html=True
                )
                for sm in S.s2_saved[si]:
                    st.markdown(f"<div class='cat-it'>{sm['icon']} {sm['name']}</div>", unsafe_allow_html=True)
                st.markdown("</div>", unsafe_allow_html=True)
            with cc3:
                st.markdown(
                    f"<div class='cat-sec'><div class='cat-hd' style='color:#9ca3af;'>🗑️ Rejected ({len(S.s2_rejected[si])})</div>",
                    unsafe_allow_html=True
                )
                for rm in S.s2_rejected[si]:
                    st.markdown(f"<div class='cat-it'>{rm['icon']} {rm['name']}</div>", unsafe_allow_html=True)
                st.markdown("</div>", unsafe_allow_html=True)

    # ───────────────────────────── STEP 3 ────────────────────────────────────
    elif step == "step3":
        prospects = S.s3_prospects[si]
        rnd = S.s3_round
        rounds_data = S.microbes[si]["step3_rounds"]

        st.markdown("### Step 3 — Build Prospect Pool")
        st.markdown(f"**{len(prospects)} / 10** prospects in pool. 6 starters + pick 1 of 3 in each round.")

        with st.expander(f"📋 Current prospects ({len(prospects)})", expanded=False):
            for p_data in prospects:
                p = to_microbe(p_data)
                st.markdown(card(p, site), unsafe_allow_html=True)

        if rnd >= 4:
            st.success(f"Prospect pool complete! ({len(prospects)} microbes)")
            if st.button("➡️ Continue to Step 4", type="primary", use_container_width=True):
                S.cur_step = "step4"
                S.s4_selection = set()
                st.rerun()
        else:
            st.markdown(f"#### Round {rnd + 1} of 4 — Pick 1 of 3")
            cands = rounds_data[rnd]
            cols = st.columns(3)
            for ci, cand_data in enumerate(cands):
                cand = to_microbe(cand_data)
                with cols[ci]:
                    st.markdown(card(cand, site, "#475569"), unsafe_allow_html=True)
                    if st.button("✅ Select", key=f"s3p{si}_{rnd}_{ci}", use_container_width=True, type="primary"):
                        # avoid duplicates
                        existing_names = {m["name"] for m in S.s3_prospects[si]}
                        if cand_data["name"] not in existing_names:
                            S.s3_prospects[si].append(cand_data)
                        S.s3_round += 1
                        st.rerun()

    # ───────────────────────────── STEP 4 ────────────────────────────────────
    elif step == "step4":
        prospects = S.s3_prospects[si]
        sel = S.s4_selection if S.s4_selection else set()

        st.markdown("### Step 4 — Create Treatment")
        st.markdown(f"Select **3 microbes** from your prospects. ({len(sel)} / 3 selected)")

        if sel:
            sel_names = [to_microbe(prospects[j]).name for j in sorted(sel)]
            st.markdown(f"**Selected:** {', '.join(sel_names)}")

        st.markdown("---")

        col_l, col_r = st.columns(2)
        for pi, p_data in enumerate(prospects):
            p = to_microbe(p_data)
            col = col_l if pi < 5 else col_r
            with col:
                is_sel = pi in sel
                border = "#3b82f6" if is_sel else "#1e293b"
                st.markdown(card(p, site, border), unsafe_allow_html=True)

                disabled = len(sel) >= 3 and not is_sel
                checked = st.checkbox(
                    f"Select {p.icon} {p.name}",
                    value=is_sel,
                    key=f"s4c{si}_{pi}",
                    disabled=disabled
                )

                if checked and pi not in sel:
                    S.s4_selection.add(pi)
                    st.rerun()
                elif not checked and pi in sel:
                    S.s4_selection.discard(pi)
                    st.rerun()

        st.markdown("---")

        can_submit = len(sel) == 3
        if st.button("🔬 Submit Treatment", type="primary", disabled=not can_submit, use_container_width=True):
            trio = [to_microbe(prospects[j]) for j in sorted(sel)]
            score, details = score_treatment(site, trio)
            S.site_scores[si] = score
            S.site_details[si] = details

            go_next_site_or_results()
            st.rerun()


if __name__ == "__main__":
    main()
