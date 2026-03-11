import streamlit as st
import os
import json
import re
from pathlib import Path
import time
import subprocess

from tools.wordpress_tool import post_to_wordpress
from tools.state_manager import load_pipeline_status, load_qa_summary, load_state, save_state
from engine.pipeline.helpers import get_cluster_pillar, get_cluster_spokes

st.set_page_config(
    page_title="Content Engine",
    layout="wide",
    page_icon="⚙",
    initial_sidebar_state="collapsed"
)

def load_css():
    with open("style.css") as f:
        st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)
load_css()

# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────
def get_safe_name(s):
    return re.sub(r'[^a-zA-Z0-9]', '_', s.lower())


def is_canonical_output_markdown(filename):
    return filename.endswith(".md") and not filename.endswith("_seo.md") and not filename.endswith("_seo_final.md")

def load_queue():
    p = "topics_queue.json"
    if os.path.exists(p):
        with open(p, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def save_queue(q):
    with open("topics_queue.json", "w", encoding="utf-8") as f:
        json.dump(q, f, indent=2)

def load_topic_state(topic):
    return load_state(topic)


def load_topic_pipeline_status(topic):
    return load_pipeline_status(topic)

def save_topic_state(topic, state):
    save_state(state, topic)

def parse_blueprint(topic):
    """Returns (data_dict, error_str)."""
    bf = f"outputs/{get_safe_name(topic)}_cluster.json"
    if not os.path.exists(bf):
        return None, None
    try:
        raw = Path(bf).read_text(encoding="utf-8").strip()
        clean = re.sub(r'^```[a-z]*\n', '', raw).strip("`")
        return json.loads(clean), None
    except Exception as e:
        return None, str(e)

def run_engine(cmd_args, session_ph, table_ph=None):
    """Blocking subprocess runner with real-time status updates."""
    env = os.environ.copy()
    env["PYTHONUTF8"] = "1"
    env["PYTHONUNBUFFERED"] = "1"
    
    process = subprocess.Popen(
        cmd_args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        env=env
    )
    
    error_log = []
    last_table_res = 0.0
    
    try:
        if process.stdout:
            while True:
                lb = process.stdout.readline()
                if not lb and process.poll() is not None:
                    break
                
                if lb:
                    line = lb.decode("utf-8", errors="replace").strip()
                    error_log.append(line)
                    if len(error_log) > 20:
                        error_log.pop(0)

                    # ── Stdout → session state parser ──
                    if "Phase 0" in line:
                        st.session_state.phase = "PHASE 0  —  CLUSTER MAP"
                        st.session_state.article = ""
                        st.session_state.agent_stage = "Planning pillar and spoke architecture..."
                    elif "Phase 1.5" in line:
                        st.session_state.phase = "PHASE 1.5  —  SERP"
                        st.session_state.article = ""
                        st.session_state.agent_stage = "Reverse-engineering ranking structures..."
                    elif "Phase 1" in line:
                        st.session_state.phase = "PHASE 1  —  STRATEGY"
                        st.session_state.article = ""
                        st.session_state.agent_stage = "Building topic cluster..."
                    elif "Phase 2" in line:
                        st.session_state.phase = "PHASE 2  —  PILLAR"
                        st.session_state.agent_stage = ""
                    elif "Phase 3" in line:
                        st.session_state.phase = "PHASE 3  —  SPOKES"
                        st.session_state.agent_stage = "Writing spoke articles..."
                    elif "Phase 4" in line:
                        st.session_state.phase = "PHASE 4  —  SEO"
                        st.session_state.agent_stage = "Optimizing articles..."
                    elif "Phase 5" in line:
                        st.session_state.phase = "PHASE 5  —  INTELLIGENCE"
                        st.session_state.agent_stage = "Running content gap detection..."
                    elif "Phase 6" in line:
                        st.session_state.phase = "PHASE 6  —  SCALING"
                        st.session_state.agent_stage = "Applying scaling rules..."
                    elif "Phase 7" in line:
                        st.session_state.phase = "PHASE 7  —  LINK INJECTION"
                        st.session_state.agent_stage = "Injecting internal links..."
                    elif "Phase 8" in line:
                        st.session_state.phase = "PHASE 8  —  HUMANIZATION"
                        st.session_state.agent_stage = "Improving readability and tone..."
                    elif "Phase 9" in line:
                        st.session_state.phase = "PHASE 9  —  QA"
                        st.session_state.agent_stage = "Reviewing final articles for publish readiness..."
                    elif "Writing Pillar:" in line:
                        title = line.split("Writing Pillar:")[-1].strip().rstrip(".")
                        st.session_state.article = f"Pillar: {title}"
                        st.session_state.agent_stage = "Starting pillar article..."
                    elif "Writing Spoke" in line:
                        m = re.search(r'Spoke \((\d+/\d+)\):\s*(.+)', line)
                        if m:
                            prog, title = m.group(1), m.group(2).strip().rstrip(".")
                            st.session_state.article = f"Spoke ({prog}): {title}"
                            st.session_state.agent_stage = "Writing..."
                    elif "Batch limit" in line:
                        st.session_state.agent_stage = "Batch limit reached — wrapping up."
                    elif "SEO Analysis:" in line:
                        fname = line.split("SEO Analysis:")[-1].strip()
                        st.session_state.article = f"Optimising: {fname}"
                    elif "Skipping" in line:
                        st.session_state.agent_stage = "Skipping (already done)"
                    # Capture CrewAI agent chatter
                    elif line.startswith("Agent:") or "Working Agent:" in line:
                        st.session_state.agent_stage = line[:80]
                    elif line.startswith("Task:") or "Current Task:" in line:
                        st.session_state.agent_stage = f"Task: {line[5:60]}..."

                    render_status(session_ph, running=True)
                    
                    if table_ph and time.time() - last_table_res > 3.0:
                        try:
                            render_table(table_ph)
                            last_table_res = time.time()
                        except:
                            pass
        
        process.wait()
        return process.returncode, error_log
    finally:
        if process.poll() is None:
            process.terminate()
            process.wait()
            st.session_state.is_running = False

def render_status(ph, running=False):
    import html
    phase   = st.session_state.get("phase", "IDLE")
    topic   = st.session_state.get("active_topic", "—")
    article = html.escape(st.session_state.get("article", ""))
    agent   = html.escape(st.session_state.get("agent_stage", ""))
    thinking_html = "<div class='thinking'>PROCESSING</div>" if running else ""

    with ph.container():
        st.markdown(f"""
            <div class="status-card">
                <div class="s-phase">{phase}</div>
                <div class="s-topic">{topic}</div>
                {"<div class='s-article'>" + article + "</div>" if article else ""}
                {"<div class='s-agent'>" + agent + "</div>" if agent else ""}
                {thinking_html}
            </div>
        """, unsafe_allow_html=True)

def render_table(ph):
    import pandas as pd

    def status_chip(value):
        value = (value or "pending").upper()
        if value == "COMPLETED":
            return "DONE"
        if value == "RUNNING":
            return "RUNNING"
        if value == "FAILED":
            return "FAILED"
        return "PENDING"

    rows = []
    for item in load_queue():
        topic = item["topic"]
        state = load_topic_state(topic)
        pipeline_status = load_topic_pipeline_status(topic)
        location = item.get("location") if isinstance(item.get("location"), dict) else {}
        d = state.get("spokes_completed", 0)
        t = state.get("spokes_total", "?")
        bp_data, _ = parse_blueprint(topic)
        cluster_size = len(get_cluster_spokes(bp_data)) if bp_data else 0

        location_parts = [part for part in [location.get("city"), location.get("area"), location.get("country")] if part]
        location_label = ", ".join(location_parts) if location_parts else "—"

        rows.append({
            "TOPIC": topic,
            "LOCATION": location_label,
            "CLUSTER SIZE": cluster_size,
            "MAP": status_chip(pipeline_status.get("cluster_map")),
            "SERP": status_chip(pipeline_status.get("serp_analysis")),
            "WRITE": status_chip(pipeline_status.get("writer")),
            "PILLAR STATUS": "DONE" if state.get("pillar_written") else ("READY" if state.get("cluster_approved") else "PENDING"),
            "SPOKE STATUS": f"{d}/{t}" if state.get("spokes_total") else ("DONE" if state.get("spokes_written") else "PENDING"),
            "SEO STATUS": status_chip(pipeline_status.get("seo")),
            "LINKS": status_chip(pipeline_status.get("linking")),
            "QA": "PASS" if state.get("publish_ready") else (status_chip(pipeline_status.get("qa")) if state.get("qa_reviewed") else "PENDING"),
        })
    ph.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

# ─────────────────────────────────────────────
# SESSION STATE INIT
# ─────────────────────────────────────────────
for k, v in [("phase","IDLE"),("active_topic","NO ACTIVE TOPIC"),
              ("article",""),("agent_stage",""),("is_running",False)]:
    if k not in st.session_state:
        st.session_state[k] = v

# ─────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────
with st.sidebar:
    st.caption("ENGINE SETTINGS")
    batch_limit = st.slider("LIMIT", 1, 10, 2)

    st.divider()
    st.caption("ADD TOPIC")
    n_topic = st.text_input("TOPIC", placeholder="Dental Implants")
    n_url   = st.text_input("URL", placeholder="Competitor URL")
    n_prio  = st.selectbox("PRIORITY", ["high","medium","low"], index=1)
    n_city = st.text_input("CITY", placeholder="Dublin")
    n_area = st.text_input("AREA", placeholder="Dublin 8")
    n_country = st.text_input("COUNTRY", placeholder="Ireland")
    n_business_name = st.text_input("BUSINESS NAME", placeholder="Dental Care Dublin 8")
    n_business_phone = st.text_input("BUSINESS PHONE", placeholder="01 4549688")
    if st.button("ADD TO QUEUE", use_container_width=True):
        if n_topic:
            q = load_queue()
            new_item = {"topic": n_topic, "competitor_url": n_url, "priority": n_prio}

            if any([n_city, n_area, n_country]):
                new_item["location"] = {
                    "city": n_city,
                    "area": n_area,
                    "country": n_country,
                }

            if any([n_business_name, n_business_phone]):
                new_item["business"] = {
                    "name": n_business_name,
                    "phone": n_business_phone,
                }

            q.append(new_item)
            save_queue(q)
            st.success(f"ADDED")
            time.sleep(0.8); st.rerun()

    st.divider()
    if st.button("WIPE QUEUE", use_container_width=True):
        save_queue([]); st.rerun()

# ─────────────────────────────────────────────
# MAIN LAYOUT
# ─────────────────────────────────────────────
st.title("CONTENT ENGINE")
st.markdown("<br>", unsafe_allow_html=True)

# Status Placeholder
session_ph = st.empty()
render_status(session_ph)

queue  = load_queue()
topics = [item["topic"] for item in queue]

if not topics:
    st.caption("QUEUE EMPTY — ADD A TOPIC IN THE SIDEBAR")
else:
    # ── Step 1: Run Controls ──
    rc1, rc2, rc3 = st.columns([2.5, 1, 1])
    with rc1:
        target = st.selectbox("TARGET", topics, label_visibility="collapsed")
    
    target_state = load_topic_state(target)
    bp_data, bp_err = parse_blueprint(target)
    
    with rc2:
        needs_approval = bp_data and not target_state.get("cluster_approved")
        if needs_approval:
            approve_checked = st.checkbox("AUTHORIZE", value=False, help="Check to authorize strategy and start production")
        else:
            approve_checked = False
            if target_state.get("cluster_approved"):
                st.markdown("<div style='margin-top:0.4rem; color:#8b949e; font-size:0.8rem;'>✓ AUTHORIZED</div>", unsafe_allow_html=True)
                
    with rc3:
        start_btn = st.button("EXECUTE RUN", use_container_width=True, type="primary")
        autopilot_mode = st.toggle("AUTOPILOT", value=st.session_state.get("autopilot", False), help="Automatically loop through all pending topics")
        if autopilot_mode != st.session_state.get("autopilot"):
            st.session_state.autopilot = autopilot_mode
            if autopilot_mode:
                st.rerun()

    # ── Auto-Select Next Topic for Autopilot ──
    if st.session_state.get("autopilot") and not start_btn:
        next_target = None
        for t in topics:
            t_state = load_topic_state(t)
            is_done = (
                t_state.get("pillar_written")
                and t_state.get("spokes_written")
                and t_state.get("seo_optimized")
                and t_state.get("links_injected")
                and t_state.get("humanized")
                and t_state.get("qa_reviewed")
            )
            if not is_done:
                next_target = t
                break
        
        # If there's a pending target, simulate a start click for it
        if next_target:
            target = next_target
            target_state = load_topic_state(target)
            approve_checked = True  # Auto-approve in autopilot
            start_btn = True
        else:
            st.session_state.autopilot = False
            st.session_state.phase = "QUEUE COMPLETED"
            render_status(session_ph)

    # ── Step 1: Strategy Blueprint immediately below run controls ──
    if bp_data:
        spokes = get_cluster_spokes(bp_data)
        spoke_labels = []
        for s in spokes:
            label = s.get("title") or s.get("topic") or s.get("sub_topic","?")
            spoke_labels.append(label)

        with st.expander("STRATEGY BLUEPRINT", expanded=needs_approval):
            st.markdown(f"""
                <div class="blueprint-card">
                    <div class="pillar-label">PILLAR ARTICLE</div>
                    <div class="pillar-title">{get_cluster_pillar(bp_data,'')}</div>
                    <div class="pillar-label">SPOKE ARTICLES  ({len(spokes)})</div>
                    {"".join(f"<div>· {s}</div>" for s in spoke_labels)}
                </div>
            """, unsafe_allow_html=True)
    elif bp_err:
        st.caption(f"BLUEPRINT ERROR: {bp_err}")
    else:
        st.caption("STRATEGY NOT YET GENERATED — RUN PHASE 1 FIRST")

    # ── Pipeline Status Table (Fragment) ──
    st.divider()
    table_ph = st.empty()

    @st.fragment(run_every="5s")
    def table_fragment():
        render_table(table_ph)
        
    table_fragment()

    # ── Execution ──
    if start_btn:
        if approve_checked:
            target_state["cluster_approved"] = True
            save_topic_state(target, target_state)
            

        st.session_state.is_running = True
        st.session_state.active_topic = target
        st.session_state.phase = "INITIALIZING"
        st.session_state.article = ""
        st.session_state.agent_stage = ""

        # ── Kill Switch UI ──
        stop_ph = st.empty()
        # If the user clicks STOP during autopilot, it will reload the script, 
        # but since process runs in background, we just terminate it inside `run_engine` finally block when stopped.
        if stop_ph.button("🚨 STOP ENTIRE RUN", use_container_width=True, help="Click to immediately abort the engine"):
            st.session_state.autopilot = False
            st.rerun()

        cmd_args = [".venv\\Scripts\\python", "main.py", "--topic", target, "--limit", str(batch_limit)]
        code, err_log = run_engine(cmd_args, session_ph, table_ph=table_ph)
        
        stop_ph.empty() # Remove the stop button once done

        st.session_state.is_running = False
        if code == 0:
            st.session_state.phase = "COMPLETED"
            st.session_state.article = ""
            st.session_state.agent_stage = ""
            render_status(session_ph)
            time.sleep(1); st.rerun()
        else:
            st.session_state.autopilot = False # Abort autopilot if crashed
            st.session_state.phase = "FINISHED WITH ERRORS"
            st.session_state.article = "Run aborted or crashed"
            st.session_state.agent_stage = "Check traceback below"
            render_status(session_ph)
            st.error("ENGINE CRASH TRACEBACK")
            st.code("\n".join(err_log), language="text")

    # ─────────────────────────────────────────
    # TOPIC MANAGEMENT (below status table)
    # ─────────────────────────────────────────
    st.markdown("<br>", unsafe_allow_html=True)
    st.subheader("TOPIC MANAGEMENT")
    m_target = st.selectbox("MANAGE TARGET", topics, label_visibility="collapsed", key="manage_sel")

    if m_target:
        m_state = load_topic_state(m_target)
        m_pipeline = load_topic_pipeline_status(m_target)

        # Action buttons
        ac1, ac2, ac3, ac4 = st.columns(4)
        with ac1:
            if st.button("RESET STATE", use_container_width=True):
                save_topic_state(m_target, {"topic": m_target}); st.rerun()
        with ac2:
            if st.button("DELETE FROM QUEUE", use_container_width=True, type="secondary"):
                save_queue([i for i in queue if i["topic"] != m_target]); st.rerun()
        with ac3:
            if st.button("PUBLISH TO CMS", use_container_width=True):
                st.info("CMS PUBLISHING — NOT CONFIGURED")
        with ac4:
            edit_mode = st.button("EDIT TOPIC", use_container_width=True, key=f"edit_{m_target}")

        # Edit form
        if 'edit_topic_active' not in st.session_state:
            st.session_state['edit_topic_active'] = None
        if edit_mode:
            st.session_state['edit_topic_active'] = m_target
        if st.session_state['edit_topic_active'] == m_target:
            st.markdown("<br>", unsafe_allow_html=True)
            st.subheader("Edit Topic")
            # Find topic in queue
            topic_item = next((i for i in queue if i["topic"] == m_target), None)
            if topic_item:
                with st.form(key=f"edit_form_{m_target}"):
                    new_topic = st.text_input("TOPIC", value=topic_item.get("topic", ""))
                    new_url = st.text_input("URL", value=topic_item.get("competitor_url", ""))
                    new_prio = st.selectbox("PRIORITY", ["high","medium","low"], index=["high","medium","low"].index(topic_item.get("priority","medium")))
                    loc = topic_item.get("location", {})
                    new_city = st.text_input("CITY", value=loc.get("city", ""))
                    new_area = st.text_input("AREA", value=loc.get("area", ""))
                    new_country = st.text_input("COUNTRY", value=loc.get("country", ""))
                    bus = topic_item.get("business", {})
                    new_business_name = st.text_input("BUSINESS NAME", value=bus.get("name", ""))
                    new_business_phone = st.text_input("BUSINESS PHONE", value=bus.get("phone", ""))
                    submit = st.form_submit_button("SAVE CHANGES")
                    cancel = st.form_submit_button("CANCEL")
                    if submit:
                        # Update topic in queue
                        for i in queue:
                            if i["topic"] == m_target:
                                i["topic"] = new_topic
                                i["competitor_url"] = new_url
                                i["priority"] = new_prio
                                i["location"] = {"city": new_city, "area": new_area, "country": new_country}
                                i["business"] = {"name": new_business_name, "phone": new_business_phone}
                        save_queue(queue)
                        st.session_state['edit_topic_active'] = None
                        st.success("Topic updated.")
                        time.sleep(0.8); st.rerun()
                    elif cancel:
                        st.session_state['edit_topic_active'] = None
                        st.info("Edit cancelled.")
                        time.sleep(0.5); st.rerun()

        with st.expander("PIPELINE STATUS", expanded=False):
            st.json(m_pipeline)

        qa_summary = load_qa_summary(m_target)
        if qa_summary:
            with st.expander("QA SUMMARY", expanded=False):
                st.json(qa_summary)

        # Artifacts — match pillar files AND spoke files from cluster
        st.markdown("<br>", unsafe_allow_html=True)
        safe = get_safe_name(m_target)
        if os.path.exists("outputs"):
            all_md = [f for f in os.listdir("outputs") if is_canonical_output_markdown(f)]
            # Always include files with the parent topic slug
            matched = [f for f in all_md if safe in f.lower()]
            # Also pull in spoke files via the cluster blueprint
            m_bp_data, _ = parse_blueprint(m_target)
            if m_bp_data:
                for spoke in get_cluster_spokes(m_bp_data):
                    s_name = spoke.get("title") or spoke.get("topic") or spoke.get("sub_topic","")
                    if s_name:
                        s_safe = get_safe_name(s_name)
                        for f in all_md:
                            if f.startswith("spoke_") and s_safe in f and f not in matched:
                                matched.append(f)
            files = sorted(matched)
            if files:
                f_sel = st.selectbox("ARTIFACT", files, label_visibility="collapsed")
                with open(f"outputs/{f_sel}", "r", encoding="utf-8", errors="replace") as f:
                    text = f.read()
                st.divider()
                st.markdown(text)
            else:
                st.caption("NO ARTIFACTS YET")

