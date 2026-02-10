"""
🌊 Sea Wolf - Ocean Cleanup Game (McKinsey PSG Style)
A Streamlit simulation of the McKinsey Problem Solving Game's Sea Wolf module.

Rules:
- 3 contaminated ocean sites to clean
- Each site has 3 numerical attributes (target ranges) + 1 desired trait + 1 undesired trait
- Select 3 microbes per site
- The AVERAGE of each attribute across your 3 microbes must fall within the site's range
- At least 1 microbe must have the desired trait
- NO microbe should have the undesired trait
- 20% penalty per unmet condition (max 100% per site)
- 30-minute timer for all 3 sites
"""

import streamlit as st
import random
import time
import math
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

# ─── CONFIG ────────────────────────────────────────────────────────────────────

ATTRIBUTE_NAMES = ["Permeability", "Rigidity", "Size", "Energy", "Adhesion", "Speed", "Density", "Mobility"]
TRAIT_NAMES = [
    "Heat-resistant", "Aerobic", "Hydrophilic", "Bioluminescent",
    "Acidophilic", "UV-tolerant", "Phosphorus-removing", "Photosensitive",
    "Cryogenic", "Alkaliphilic"
]
MICROBE_PREFIXES = ["Cyro", "Ops", "Neo", "Flux", "Zeta", "Axo", "Viro", "Plex", "Kino", "Rho", "Sigma", "Tau", "Delta", "Omni", "Hexa"]
MICROBE_SUFFIXES = ["Virus", "Amoeba", "Bacillus", "Spore", "Phage", "Coccus", "Flagella", "Microbe", "Cell", "Organism"]
MICROBE_ICONS = ["🦠", "🧫", "🔬", "💊", "🧬", "⚗️", "🫧", "🌀", "💠", "🔮"]

TOTAL_TIME = 30 * 60  # 30 minutes in seconds
MICROBES_PER_SITE = 10  # microbes to evaluate per site
MICROBES_TO_SELECT = 3  # final selection per site
NUM_SITES = 3
PENALTY_PER_MISS = 20  # 20% penalty per unmet condition

# ─── DATA STRUCTURES ──────────────────────────────────────────────────────────

@dataclass
class Microbe:
    name: str
    icon: str
    attributes: dict  # {attr_name: value (1-10)}
    traits: list      # list of trait names this microbe has

@dataclass  
class Site:
    site_number: int
    attribute_names: list       # 3 attribute names
    attribute_ranges: dict      # {attr_name: (low, high)}
    desired_trait: str
    undesired_trait: str
    microbe_pool: list          # list of Microbe objects

# ─── GENERATION FUNCTIONS ─────────────────────────────────────────────────────

def generate_microbe_name(used_names: set) -> str:
    for _ in range(100):
        name = f"{random.choice(MICROBE_PREFIXES)} {random.choice(MICROBE_SUFFIXES)}"
        if name not in used_names:
            used_names.add(name)
            return name
    return f"Microbe-{random.randint(1000,9999)}"

def generate_site(site_num: int, used_attrs: set, used_traits: set) -> Site:
    # Pick 3 unique attributes not used by previous sites
    available_attrs = [a for a in ATTRIBUTE_NAMES if a not in used_attrs]
    if len(available_attrs) < 3:
        available_attrs = ATTRIBUTE_NAMES.copy()
    attrs = random.sample(available_attrs, 3)
    for a in attrs:
        used_attrs.add(a)
    
    # Generate ranges for each attribute
    ranges = {}
    for attr in attrs:
        low = random.randint(1, 7)
        high = low + random.randint(1, 3)
        high = min(high, 10)
        if high - low < 1:
            low = max(1, high - 2)
        ranges[attr] = (low, high)
    
    # Pick traits
    available_traits = [t for t in TRAIT_NAMES if t not in used_traits]
    if len(available_traits) < 2:
        available_traits = TRAIT_NAMES.copy()
    chosen_traits = random.sample(available_traits, 2)
    desired = chosen_traits[0]
    undesired = chosen_traits[1]
    used_traits.add(desired)
    used_traits.add(undesired)
    
    # Generate microbe pool
    used_names = set()
    microbes = []
    
    # Ensure at least some microbes are viable (have desired trait, no undesired)
    # and some are tricky (have undesired trait or bad attributes)
    for i in range(MICROBES_PER_SITE):
        name = generate_microbe_name(used_names)
        icon = random.choice(MICROBE_ICONS)
        
        # Generate attributes - mix of in-range and out-of-range
        micro_attrs = {}
        for attr in attrs:
            low, high = ranges[attr]
            mid = (low + high) / 2
            if random.random() < 0.55:  # ~55% chance in/near range
                val = random.randint(max(1, low - 1), min(10, high + 1))
            else:
                val = random.randint(1, 10)
            micro_attrs[attr] = val
        
        # Generate traits
        micro_traits = []
        # ~40% chance of having the desired trait
        if random.random() < 0.40:
            micro_traits.append(desired)
        # ~20% chance of having the undesired trait
        if random.random() < 0.20:
            micro_traits.append(undesired)
        # Add 0-1 random other traits
        other_traits = [t for t in TRAIT_NAMES if t != desired and t != undesired]
        if random.random() < 0.3:
            micro_traits.append(random.choice(other_traits))
        
        microbes.append(Microbe(name=name, icon=icon, attributes=micro_attrs, traits=micro_traits))
    
    return Site(
        site_number=site_num,
        attribute_names=attrs,
        attribute_ranges=ranges,
        desired_trait=desired,
        undesired_trait=undesired,
        microbe_pool=microbes
    )

def generate_game():
    used_attrs = set()
    used_traits = set()
    sites = []
    for i in range(NUM_SITES):
        sites.append(generate_site(i + 1, used_attrs, used_traits))
    return sites

# ─── SCORING ──────────────────────────────────────────────────────────────────

def calculate_site_score(site: Site, selected_microbes: List[Microbe]) -> Tuple[int, list]:
    """Returns (score, list_of_details)"""
    if len(selected_microbes) != 3:
        return 0, ["❌ You must select exactly 3 microbes"]
    
    details = []
    penalties = 0
    
    # Check attribute averages
    for attr in site.attribute_names:
        values = [m.attributes[attr] for m in selected_microbes]
        avg = sum(values) / 3
        low, high = site.attribute_ranges[attr]
        in_range = low <= avg <= high
        if in_range:
            details.append(f"✅ {attr}: avg = {avg:.1f} (range {low}-{high})")
        else:
            details.append(f"❌ {attr}: avg = {avg:.1f} (range {low}-{high}) — OUT OF RANGE")
            penalties += 1
    
    # Check desired trait
    has_desired = any(site.desired_trait in m.traits for m in selected_microbes)
    if has_desired:
        details.append(f"✅ Desired trait '{site.desired_trait}': PRESENT")
    else:
        details.append(f"❌ Desired trait '{site.desired_trait}': MISSING — penalty!")
        penalties += 1
    
    # Check undesired trait
    has_undesired = any(site.undesired_trait in m.traits for m in selected_microbes)
    if not has_undesired:
        details.append(f"✅ Undesired trait '{site.undesired_trait}': ABSENT (good!)")
    else:
        culprits = [m.name for m in selected_microbes if site.undesired_trait in m.traits]
        details.append(f"❌ Undesired trait '{site.undesired_trait}': PRESENT in {', '.join(culprits)} — penalty!")
        penalties += 1
    
    score = max(0, 100 - penalties * PENALTY_PER_MISS)
    return score, details

# ─── UI HELPERS ───────────────────────────────────────────────────────────────

def format_time(seconds: int) -> str:
    m = seconds // 60
    s = seconds % 60
    return f"{m:02d}:{s:02d}"

def get_attr_color(value: int, low: int, high: int) -> str:
    if low <= value <= high:
        return "#22c55e"  # green
    elif abs(value - low) <= 1 or abs(value - high) <= 1:
        return "#f59e0b"  # amber
    else:
        return "#ef4444"  # red

def render_microbe_card(microbe: Microbe, site: Site, idx: int, selected: bool, disabled: bool = False):
    """Render a microbe card with checkbox"""
    attrs_html = ""
    for attr in site.attribute_names:
        val = microbe.attributes[attr]
        low, high = site.attribute_ranges[attr]
        color = get_attr_color(val, low, high)
        attrs_html += f'<span style="color:{color}; font-weight:600;">{attr}: {val}</span> · '
    attrs_html = attrs_html.rstrip(" · ")
    
    traits_display = []
    for t in microbe.traits:
        if t == site.desired_trait:
            traits_display.append(f"🟢 {t}")
        elif t == site.undesired_trait:
            traits_display.append(f"🔴 {t}")
        else:
            traits_display.append(f"⚪ {t}")
    traits_str = " | ".join(traits_display) if traits_display else "No traits"
    
    border_color = "#3b82f6" if selected else "#374151"
    bg = "#1e293b" if selected else "#0f172a"
    
    st.markdown(f"""
    <div style="border: 2px solid {border_color}; border-radius: 10px; padding: 12px; 
                margin-bottom: 8px; background: {bg};">
        <div style="font-size: 1.1em; font-weight: bold;">
            {microbe.icon} {microbe.name}
        </div>
        <div style="margin-top: 6px; font-size: 0.9em;">
            {attrs_html}
        </div>
        <div style="margin-top: 4px; font-size: 0.85em; color: #94a3b8;">
            {traits_str}
        </div>
    </div>
    """, unsafe_allow_html=True)

# ─── MAIN APP ─────────────────────────────────────────────────────────────────

def main():
    st.set_page_config(page_title="🌊 Sea Wolf - Ocean Cleanup", layout="wide", initial_sidebar_state="collapsed")
    
    # Custom CSS
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;700;800&display=swap');
    
    .stApp {
        background: linear-gradient(180deg, #020617 0%, #0c1929 40%, #0a1628 100%);
        color: #e2e8f0;
    }
    
    .main-title {
        font-family: 'Outfit', sans-serif;
        font-size: 2.8em;
        font-weight: 800;
        text-align: center;
        background: linear-gradient(135deg, #22d3ee, #3b82f6, #8b5cf6);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0;
    }
    
    .subtitle {
        text-align: center;
        color: #64748b;
        font-size: 1.1em;
        margin-bottom: 20px;
    }
    
    .score-card {
        background: linear-gradient(135deg, #1e293b, #0f172a);
        border: 1px solid #334155;
        border-radius: 16px;
        padding: 20px;
        text-align: center;
    }
    
    .score-big {
        font-family: 'Outfit', sans-serif;
        font-size: 3em;
        font-weight: 800;
    }
    
    .timer-display {
        font-family: 'Outfit', sans-serif;
        font-size: 2.5em;
        font-weight: 700;
        text-align: center;
        padding: 10px;
        border-radius: 12px;
    }
    
    .site-header {
        font-family: 'Outfit', sans-serif;
        font-size: 1.8em;
        font-weight: 700;
        color: #22d3ee;
        margin-bottom: 10px;
    }
    
    .site-req-box {
        background: linear-gradient(135deg, #1e293b 0%, #172033 100%);
        border: 1px solid #2563eb40;
        border-radius: 12px;
        padding: 16px;
        margin-bottom: 16px;
    }
    
    .result-box {
        border-radius: 14px;
        padding: 20px;
        margin: 10px 0;
    }
    
    .result-success { background: #052e16; border: 1px solid #22c55e40; }
    .result-partial { background: #1c1917; border: 1px solid #f59e0b40; }
    .result-fail { background: #1c0a0a; border: 1px solid #ef444440; }
    
    div[data-testid="stVerticalBlock"] > div:has(> div.stCheckbox) {
        margin-bottom: -10px;
    }
    
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px;
        padding: 8px 20px;
        background: #1e293b;
        color: #94a3b8;
    }
    .stTabs [aria-selected="true"] {
        background: #1e40af !important;
        color: white !important;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # ─── SESSION STATE INIT ───────────────────────────────────────────────────
    if "game_state" not in st.session_state:
        st.session_state.game_state = "menu"  # menu, playing, results
    if "sites" not in st.session_state:
        st.session_state.sites = None
    if "current_site" not in st.session_state:
        st.session_state.current_site = 0
    if "selections" not in st.session_state:
        st.session_state.selections = {0: set(), 1: set(), 2: set()}
    if "site_scores" not in st.session_state:
        st.session_state.site_scores = {}
    if "site_details" not in st.session_state:
        st.session_state.site_details = {}
    if "start_time" not in st.session_state:
        st.session_state.start_time = None
    if "time_up" not in st.session_state:
        st.session_state.time_up = False
    if "submitted_sites" not in st.session_state:
        st.session_state.submitted_sites = set()
    
    # ─── MENU SCREEN ──────────────────────────────────────────────────────────
    if st.session_state.game_state == "menu":
        st.markdown("")
        st.markdown("")
        st.markdown('<div class="main-title">🌊 Sea Wolf</div>', unsafe_allow_html=True)
        st.markdown('<div class="subtitle">Ocean Cleanup — McKinsey PSG Simulation</div>', unsafe_allow_html=True)
        
        st.markdown("---")
        
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.markdown("""
            ### 🎯 Objective
            Clean **3 contaminated ocean sites** by selecting the right combination of **microbes** for each site.
            
            ### 📋 Rules
            - Each site has **3 numerical attributes** with target ranges (1–10) and **2 traits** (1 desired, 1 undesired)
            - Select **3 microbes** per site  
            - The **average** of each attribute across your 3 microbes must fall within the site's target range
            - At least **1 microbe** must have the **desired trait** ✅
            - **No microbe** should have the **undesired trait** ❌
            - **−20% penalty** for each condition not met (5 conditions max → min score 0%)
            
            ### ⏱️ Timer
            You have **30 minutes** for all 3 sites. Budget your time wisely!
            
            ### 🎨 Color Guide
            - 🟢 **Green** value = within site's target range  
            - 🟡 **Amber** value = close (±1 from range)  
            - 🔴 **Red** value = far from range  
            """)
            
            st.markdown("")
            if st.button("🚀 Start Game", use_container_width=True, type="primary"):
                st.session_state.sites = generate_game()
                st.session_state.game_state = "playing"
                st.session_state.current_site = 0
                st.session_state.selections = {0: set(), 1: set(), 2: set()}
                st.session_state.site_scores = {}
                st.session_state.site_details = {}
                st.session_state.start_time = time.time()
                st.session_state.time_up = False
                st.session_state.submitted_sites = set()
                st.rerun()
    
    # ─── PLAYING SCREEN ──────────────────────────────────────────────────────
    elif st.session_state.game_state == "playing":
        sites = st.session_state.sites
        cs = st.session_state.current_site
        site = sites[cs]
        
        # Timer calculation
        elapsed = time.time() - st.session_state.start_time
        remaining = max(0, TOTAL_TIME - int(elapsed))
        
        if remaining <= 0 and not st.session_state.time_up:
            st.session_state.time_up = True
            # Auto-score any unsubmitted sites
            for i in range(NUM_SITES):
                if i not in st.session_state.submitted_sites:
                    sel_indices = st.session_state.selections[i]
                    if len(sel_indices) == 3:
                        selected = [sites[i].microbe_pool[j] for j in sel_indices]
                        score, details = calculate_site_score(sites[i], selected)
                    else:
                        score, details = 0, ["⏰ Time's up — incomplete selection"]
                    st.session_state.site_scores[i] = score
                    st.session_state.site_details[i] = details
                    st.session_state.submitted_sites.add(i)
            st.session_state.game_state = "results"
            st.rerun()
        
        # ─── TOP BAR: Timer + Score ───────────────────────────────────
        top1, top2, top3, top4 = st.columns([2, 1.5, 1.5, 1.5])
        
        with top1:
            timer_color = "#22c55e" if remaining > 300 else ("#f59e0b" if remaining > 60 else "#ef4444")
            st.markdown(f"""
            <div class="timer-display" style="color: {timer_color};">
                ⏱️ {format_time(remaining)}
            </div>
            """, unsafe_allow_html=True)
        
        for idx, col in enumerate([top2, top3, top4]):
            with col:
                if idx in st.session_state.submitted_sites:
                    sc = st.session_state.site_scores[idx]
                    color = "#22c55e" if sc >= 80 else ("#f59e0b" if sc >= 40 else "#ef4444")
                    st.markdown(f"""
                    <div class="score-card">
                        <div style="color:#94a3b8; font-size:0.85em;">Site {idx+1}</div>
                        <div class="score-big" style="color:{color};">{sc}%</div>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    status = "🔵 Current" if idx == cs else ("⬜ Pending" if idx > cs else "⬜")
                    st.markdown(f"""
                    <div class="score-card">
                        <div style="color:#94a3b8; font-size:0.85em;">Site {idx+1}</div>
                        <div style="font-size:1.2em; color:#64748b; margin-top:8px;">{status}</div>
                    </div>
                    """, unsafe_allow_html=True)
        
        st.markdown("---")
        
        # Auto-refresh timer every 5 seconds
        if remaining > 0:
            time.sleep(0.1)  # small delay for smoother UX
        
        # ─── SITE DISPLAY ─────────────────────────────────────────────
        if cs in st.session_state.submitted_sites:
            # This site is done, show result and nav
            score = st.session_state.site_scores[cs]
            details = st.session_state.site_details[cs]
            
            result_class = "result-success" if score >= 80 else ("result-partial" if score >= 40 else "result-fail")
            st.markdown(f'<div class="site-header">📍 Site {cs+1} — Treatment Result</div>', unsafe_allow_html=True)
            st.markdown(f"""
            <div class="result-box {result_class}">
                <div style="font-size: 2em; font-weight: 700; text-align:center;">
                    Treatment Effectiveness: {score}%
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            for d in details:
                st.markdown(f"**{d}**")
            
            st.markdown("")
            nav1, nav2 = st.columns(2)
            with nav1:
                if cs > 0:
                    if st.button("← Previous Site", use_container_width=True):
                        st.session_state.current_site = cs - 1
                        st.rerun()
            with nav2:
                if cs < NUM_SITES - 1:
                    if st.button("Next Site →", use_container_width=True, type="primary"):
                        st.session_state.current_site = cs + 1
                        st.rerun()
                else:
                    if len(st.session_state.submitted_sites) == NUM_SITES:
                        if st.button("📊 View Final Results", use_container_width=True, type="primary"):
                            st.session_state.game_state = "results"
                            st.rerun()
        else:
            # ─── ACTIVE SITE ──────────────────────────────────────────
            st.markdown(f'<div class="site-header">📍 Site {cs+1} of {NUM_SITES} — Select 3 Microbes</div>', unsafe_allow_html=True)
            
            # Site requirements
            st.markdown('<div class="site-req-box">', unsafe_allow_html=True)
            req_cols = st.columns(5)
            for i, attr in enumerate(site.attribute_names):
                low, high = site.attribute_ranges[attr]
                with req_cols[i]:
                    st.markdown(f"""
                    **📊 {attr}**  
                    Range: **{low} – {high}**
                    """)
            with req_cols[3]:
                st.markdown(f"""
                **✅ Desired Trait**  
                {site.desired_trait}
                """)
            with req_cols[4]:
                st.markdown(f"""
                **❌ Undesired Trait**  
                {site.undesired_trait}
                """)
            st.markdown('</div>', unsafe_allow_html=True)
            
            # Live average preview
            sel_indices = st.session_state.selections[cs]
            if len(sel_indices) > 0:
                selected_microbes = [site.microbe_pool[j] for j in sel_indices]
                preview_cols = st.columns(5)
                for i, attr in enumerate(site.attribute_names):
                    vals = [m.attributes[attr] for m in selected_microbes]
                    avg = sum(vals) / len(vals)
                    low, high = site.attribute_ranges[attr]
                    in_range = low <= avg <= high
                    color = "#22c55e" if in_range else "#ef4444"
                    with preview_cols[i]:
                        st.markdown(f"""
                        <div style="text-align:center; font-size:0.85em; color:#64748b;">
                            Current avg ({len(sel_indices)}/3)
                        </div>
                        <div style="text-align:center; font-size:1.4em; font-weight:700; color:{color};">
                            {avg:.1f}
                        </div>
                        """, unsafe_allow_html=True)
                
                # Trait status
                has_desired = any(site.desired_trait in m.traits for m in selected_microbes)
                has_undesired = any(site.undesired_trait in m.traits for m in selected_microbes)
                with preview_cols[3]:
                    icon = "✅" if has_desired else "⚠️"
                    st.markdown(f"<div style='text-align:center; font-size:1.3em;'>{icon}</div>", unsafe_allow_html=True)
                with preview_cols[4]:
                    icon = "✅" if not has_undesired else "🚨"
                    st.markdown(f"<div style='text-align:center; font-size:1.3em;'>{icon}</div>", unsafe_allow_html=True)
            
            st.markdown("---")
            
            # Microbe grid
            st.markdown(f"**Select 3 microbes from the pool** ({len(sel_indices)} selected)")
            
            col_left, col_right = st.columns(2)
            
            for idx, microbe in enumerate(site.microbe_pool):
                col = col_left if idx < 5 else col_right
                with col:
                    is_selected = idx in sel_indices
                    
                    # Build attribute display
                    attr_parts = []
                    for attr in site.attribute_names:
                        val = microbe.attributes[attr]
                        low, high = site.attribute_ranges[attr]
                        color = get_attr_color(val, low, high)
                        attr_parts.append(f"**{attr}:** :{('green' if color == '#22c55e' else ('orange' if color == '#f59e0b' else 'red'))}[{val}]")
                    
                    # Traits
                    trait_parts = []
                    for t in microbe.traits:
                        if t == site.desired_trait:
                            trait_parts.append(f"🟢 {t}")
                        elif t == site.undesired_trait:
                            trait_parts.append(f"🔴 {t}")
                        else:
                            trait_parts.append(f"⚪ {t}")
                    traits_str = " | ".join(trait_parts) if trait_parts else "No traits"
                    
                    disabled = (len(sel_indices) >= 3 and not is_selected)
                    
                    checked = st.checkbox(
                        f"{microbe.icon} **{microbe.name}** — {' · '.join(attr_parts)} — {traits_str}",
                        value=is_selected,
                        key=f"site{cs}_micro{idx}",
                        disabled=disabled
                    )
                    
                    if checked and idx not in sel_indices:
                        st.session_state.selections[cs].add(idx)
                        st.rerun()
                    elif not checked and idx in sel_indices:
                        st.session_state.selections[cs].discard(idx)
                        st.rerun()
            
            st.markdown("---")
            
            # Action buttons
            btn_cols = st.columns([1, 1, 1])
            
            with btn_cols[0]:
                if cs > 0:
                    if st.button("← Previous Site", use_container_width=True):
                        st.session_state.current_site = cs - 1
                        st.rerun()
            
            with btn_cols[1]:
                can_submit = len(sel_indices) == 3
                if st.button(
                    f"🔬 Submit Treatment for Site {cs+1}",
                    use_container_width=True,
                    type="primary",
                    disabled=not can_submit
                ):
                    selected = [site.microbe_pool[j] for j in sel_indices]
                    score, details = calculate_site_score(site, selected)
                    st.session_state.site_scores[cs] = score
                    st.session_state.site_details[cs] = details
                    st.session_state.submitted_sites.add(cs)
                    
                    # Auto-advance to next unsubmitted site or results
                    if cs < NUM_SITES - 1:
                        st.session_state.current_site = cs + 1
                    elif len(st.session_state.submitted_sites) == NUM_SITES:
                        st.session_state.game_state = "results"
                    st.rerun()
            
            with btn_cols[2]:
                if cs < NUM_SITES - 1:
                    if st.button("Skip → Next Site", use_container_width=True):
                        st.session_state.current_site = cs + 1
                        st.rerun()
        
        # Auto-refresh for timer (rerun every 10 seconds)
        if remaining > 0 and remaining % 10 == 0:
            st.rerun()
    
    # ─── RESULTS SCREEN ──────────────────────────────────────────────────────
    elif st.session_state.game_state == "results":
        st.markdown('<div class="main-title">🌊 Mission Complete</div>', unsafe_allow_html=True)
        st.markdown('<div class="subtitle">Ocean Cleanup — Final Report</div>', unsafe_allow_html=True)
        
        st.markdown("---")
        
        # Calculate total
        total_score = 0
        for i in range(NUM_SITES):
            total_score += st.session_state.site_scores.get(i, 0)
        avg_score = total_score / NUM_SITES
        
        # Total score display
        grade_color = "#22c55e" if avg_score >= 80 else ("#f59e0b" if avg_score >= 50 else "#ef4444")
        grade = "🏆 Excellent!" if avg_score >= 80 else ("✅ Good" if avg_score >= 60 else ("⚠️ Needs Improvement" if avg_score >= 40 else "❌ Below Threshold"))
        
        st.markdown(f"""
        <div style="text-align:center; padding: 30px; background: linear-gradient(135deg, #1e293b, #0f172a);
                    border: 2px solid {grade_color}40; border-radius: 20px; margin-bottom: 30px;">
            <div style="font-size: 1.2em; color: #94a3b8;">Overall Treatment Effectiveness</div>
            <div style="font-size: 4em; font-weight: 800; color: {grade_color}; font-family: 'Outfit', sans-serif;">
                {avg_score:.0f}%
            </div>
            <div style="font-size: 1.3em; margin-top: 5px;">{grade}</div>
            <div style="color: #64748b; margin-top: 10px;">
                Total: {total_score:.0f} / 300 points
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # Per-site breakdown
        site_cols = st.columns(NUM_SITES)
        for i in range(NUM_SITES):
            score = st.session_state.site_scores.get(i, 0)
            details = st.session_state.site_details.get(i, [])
            color = "#22c55e" if score >= 80 else ("#f59e0b" if score >= 40 else "#ef4444")
            result_class = "result-success" if score >= 80 else ("result-partial" if score >= 40 else "result-fail")
            
            with site_cols[i]:
                st.markdown(f"""
                <div class="result-box {result_class}" style="text-align:center;">
                    <div style="font-size: 0.9em; color: #94a3b8;">Site {i+1}</div>
                    <div style="font-size: 2.5em; font-weight: 800; color: {color};">
                        {score}%
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                for d in details:
                    st.markdown(d)
        
        # Time used
        if st.session_state.start_time:
            elapsed = time.time() - st.session_state.start_time
            used = min(elapsed, TOTAL_TIME)
            st.markdown(f"""
            <div style="text-align: center; color: #64748b; margin-top: 20px;">
                ⏱️ Time used: {format_time(int(used))} / {format_time(TOTAL_TIME)}
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown("---")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔄 Play Again", use_container_width=True, type="primary"):
                st.session_state.game_state = "menu"
                st.session_state.sites = None
                st.session_state.current_site = 0
                st.session_state.selections = {0: set(), 1: set(), 2: set()}
                st.session_state.site_scores = {}
                st.session_state.site_details = {}
                st.session_state.start_time = None
                st.session_state.time_up = False
                st.session_state.submitted_sites = set()
                st.rerun()
        with col2:
            if st.button("📋 View Scoring Guide", use_container_width=True):
                st.info("""
                **Scoring Guide:**
                - Each site has 5 conditions (3 attribute averages + desired trait + no undesired trait)
                - Each unmet condition = −20% penalty
                - 100% = all conditions met · 80% = 1 miss · 60% = 2 misses · etc.
                - Overall score = average across all 3 sites
                - Target: ≥80% average to "pass" (estimated McKinsey threshold)
                """)

if __name__ == "__main__":
    main()
