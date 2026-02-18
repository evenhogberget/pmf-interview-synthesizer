import json
import requests
import streamlit as st
def load_demo():
    st.session_state["notes"] = """Interview 1 (shop owner):
- "We track inventory in spreadsheets. It's always wrong."
- "I lose sales because we run out of best sellers unexpectedly."
- "I tried software before but it was too complicated for my staff."
Interview 2 (manager):
- "Reordering takes too long; vendors all have different processes."
- "I don't trust the numbers from last week's count."
- "Training new employees on inventory is painful."
"""
# ----------------------------
# Config
# ----------------------------
st.set_page_config(page_title="PMF Interview Synthesizer", layout="centered")
st.title("PMF Interview Synthesizer")
st.caption("AI-assisted synthesis of customer interviews into evidence-based PMF insights.")
st.markdown("""
<style>
/* tighten spacing */
.block-container {padding-top: 2rem; padding-bottom: 2rem;}
/* nicer section titles */
h1, h2, h3 {letter-spacing: -0.02em;}
/* subtle card feel */
[data-testid="stVerticalBlockBorderWrapper"] {
  border-radius: 14px;
}
</style>
""", unsafe_allow_html=True)

# HERO
st.markdown("### PMF Interview Synthesizer")
st.markdown(
    "Turn messy interview notes into **evidence-based pain points, themes, quotes, and PMF hypotheses** in one click."
)

cA, cB, cC, cD = st.columns(4)
cA.markdown("✅ **Extract pain points**")
cB.markdown("🧩 **Cluster themes**")
cC.markdown("💬 **Pull quotes**")
cD.markdown("📌 **Generate hypotheses**")

st.divider()
with st.sidebar:
    st.header("Settings")
    st.write("Tip: keep notes short + include quotes for best results.")
    show_raw = st.checkbox("Show raw JSON", value=False)
    max_pain_points = st.slider("Max pain points", 5, 15, 10)

MODEL = "gpt-4o-mini"  # Good default for cost/speed. You can change later.

# ----------------------------
# Helpers
# ----------------------------
def call_openai_synthesis(api_key: str, notes: str, context: str = "") -> dict:

    system_instructions = (
        "You are an assistant helping early-stage product teams synthesize customer interview notes.\n"
        "Return ONLY valid JSON matching the schema exactly."
    )

    user_prompt = f"""
CONTEXT:
{context.strip()}

RAW INTERVIEW NOTES:
{notes.strip()}

TASK:

1) Extract 5-10 key customer pain points.
Each pain point must include:
- label
- description
- segments
- evidence_interviews (e.g., ["Interview 1", "Interview 3"])
- evidence_count (number of distinct interviews)
- evidence_strength ("low"=1, "medium"=2, "high"=3+)

2) Group pain points into 3-6 themes.
Each theme must include:
- theme
- pain_points (labels)
- evidence_count

3) Provide representative quotes with:
- quote
- segment
- interview
- supports (pain_point_label)

4) Write 4-6 structured PMF hypotheses in measurable format:
"For [segment] who [problem], we believe [change] will improve [metric] by [target] within [timeframe], validated by [test]."

5) Identify contradictions or meaningful segment differences.

6) List open validation questions.

STRICT OUTPUT JSON:
{{
  "pain_points": [
    {{
      "label": "...",
      "description": "...",
      "segments": ["..."],
      "evidence_interviews": ["Interview 1"],
      "evidence_count": 1,
      "evidence_strength": "low"
    }}
  ],
  "themes": [
    {{
      "theme": "...",
      "pain_points": ["..."],
      "evidence_count": 0
    }}
  ],
  "quotes": [
    {{
      "quote": "...",
      "segment": "...",
      "interview": "Interview 1",
      "supports": "..."
    }}
  ],
  "pmf_hypotheses": ["..."],
  "contradictions": ["..."],
  "open_questions": ["..."]
}}
""".strip()

    url = "https://api.openai.com/v1/responses"

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": MODEL,
        "input": [
            {"role": "system", "content": system_instructions},
            {"role": "user", "content": user_prompt},
        ],
        "text": {"format": {"type": "json_object"}},
    }

    r = requests.post(url, headers=headers, json=payload, timeout=60)

    if r.status_code != 200:
        raise RuntimeError(f"OpenAI API error {r.status_code}: {r.text}")

    data = r.json()
    json_text = data["output"][0]["content"][0]["text"]

    return json.loads(json_text)

def get_api_key() -> str:
    # Streamlit Cloud: store in Secrets as OPENAI_API_KEY
    return st.secrets.get("OPENAI_API_KEY", "").strip()
# ----------------------------
# UI
# ----------------------------

# (optional) remove duplicate titles above — you currently have st.title twice
left, right = st.columns([1.2, 1])

with left:
    st.subheader("Input")
    with st.container(border=True):
        context = st.text_area(
            "Context (optional)",
            height=90,
            placeholder="Example: Interviews with small retail store owners about inventory and reordering.",
        )

        st.text_area(
            "Interview notes or transcript",
            height=280,
            placeholder="Paste raw notes here. Include direct quotes when possible.",
            key="notes",
        )
        notes = st.session_state.get("notes", "")

        b1, b2 = st.columns([1, 1])
        with b1:
            analyze = st.button("Analyze", use_container_width=True)
        with b2:
            st.button("Use demo text", on_click=load_demo, use_container_width=True)

with right:
    st.subheader("Tips")
    with st.container(border=True):
        st.markdown(
            """
**For best results**
- Label interviews like *Interview 1 (PM)*, *Interview 2 (Founder)*  
- Include 3–5 direct quotes  
- Keep each interview to 5–12 bullets  
- Avoid summaries—paste raw notes
"""
        )

with st.container(border=True):
    st.subheader("Inputs")
    context = st.text_input(
        "Context (optional)",
        placeholder="Example: Interviews with early-stage founders about PMF discovery failures."
    )

    st.text_area(
        "Interview notes / transcript",
        height=240,
        placeholder="Paste raw notes here. Include interview labels like 'Interview 1 (Founder): ...'",
        key="notes",
    )

c1, c2 = st.columns(2)
with c1:
    analyze = st.button("Analyze", type="primary")
with c2:
    st.button("Use demo text", on_click=load_demo)

# Run analysis only when button is clicked
if analyze:
    notes = st.session_state.get("notes", "")

    if not notes.strip():
        st.warning("Please paste interview notes first.")
        st.stop()

    api_key = get_api_key()
    if not api_key:
        st.error("Missing OPENAI_API_KEY.")
        st.stop()

    with st.spinner("Analyzing..."):
        try:
            result = call_openai_synthesis(api_key, notes, context)
        except Exception as e:
            st.error(f"Analysis failed: {e}")
            st.stop()

    # ---- Normalize evidence fields ----
    for p in result.get("pain_points", []):
        interviews = p.get("evidence_interviews", [])
        interviews = list(dict.fromkeys(interviews))  # unique, keep order
        p["evidence_interviews"] = interviews
        p["evidence_count"] = len(interviews)

        if p["evidence_count"] <= 1:
            p["evidence_strength"] = "low"
        elif p["evidence_count"] == 2:
            p["evidence_strength"] = "medium"
        else:
            p["evidence_strength"] = "high"

    # ---- Recompute theme evidence_count based on unique interviews ----
    pp_by_label = {p.get("label"): p for p in result.get("pain_points", [])}
    for t in result.get("themes", []):
        unique_interviews = set()
        for label in t.get("pain_points", []):
            p = pp_by_label.get(label)
            if p:
                unique_interviews.update(p.get("evidence_interviews", []))
        t["evidence_count"] = len(unique_interviews)

    # ---- Prep data for display ----
    pain_points = result.get("pain_points", [])
    themes = result.get("themes", [])
    quotes = result.get("quotes", [])
    hypotheses = result.get("pmf_hypotheses", [])
    contradictions = result.get("contradictions", [])
    open_questions = result.get("open_questions", [])

    st.success("Done ✅")

    # Top metrics row
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Pain points", len(pain_points))
    m2.metric("Themes", len(themes))
    m3.metric("Quotes", len(quotes))
    m4.metric("Hypotheses", len(hypotheses))

    st.download_button(
        "Download JSON",
        data=json.dumps(result, indent=2),
        file_name="pmf_synthesis.json",
        mime="application/json",
    )

    if not quotes:
        st.info("No quotes were returned. Try including direct quotes in your notes.")

    tab1, tab2, tab3, tab4, tab5 = st.tabs(
        ["Pain Points", "Themes", "Quotes", "Hypotheses", "Open Questions"]
    )

    with tab1:
        for p in pain_points:
            with st.container(border=True):
                st.subheader(p.get("label", ""))
                st.write(p.get("description", ""))
                st.caption("Segments: " + ", ".join(p.get("segments", [])))
                st.caption("Evidence: " + ", ".join(p.get("evidence_interviews", [])))
                st.caption(f"Count: {p.get('evidence_count')} | Strength: {p.get('evidence_strength')}")

    with tab2:
        for t in themes:
            with st.container(border=True):
                st.subheader(t.get("theme", ""))
                st.caption(f"Total evidence count: {t.get('evidence_count')}")
                for label in t.get("pain_points", []):
                    st.write(f"• {label}")

    with tab3:
        for q in quotes:
            with st.container(border=True):
                st.markdown(f'> "{q.get("quote", "")}"')
                st.caption(
                    f"Segment: {q.get('segment')} | Interview: {q.get('interview')} | Supports: {q.get('supports')}"
                )

    with tab4:
        for h in hypotheses:
            with st.container(border=True):
                st.write(h)

        if contradictions:
            st.divider()
            st.subheader("Contradictions / segment differences")
            for c in contradictions:
                st.write(f"• {c}")

    with tab5:
        for oq in open_questions:
            with st.container(border=True):
                st.write(f"• {oq}")

    if show_raw:
        st.divider()
        st.subheader("Raw JSON")
        st.code(json.dumps(result, indent=2), language="json")
st.divider()
st.caption("Built by Even • PMF Interview Synthesizer • MVP")
