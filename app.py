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
st.title("PMF Interview Synthesizer (MVP)")
st.write("Paste customer interview notes below. This tool synthesizes pain points, themes, quotes, and PMF hypotheses.")

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
with st.expander("Optional context (who is being interviewed / what problem space?)", expanded=False):
    context = st.text_area(
        "Context (optional)",
        height=80,
        placeholder="Example: Interviews with small retail store owners about inventory and reordering.",
    )

st.text_area(
    "Interview notes or transcript",
    height=260,
    placeholder="Paste raw notes here. Include direct quotes when possible.",
    key="notes",
)
notes = st.session_state.get("notes", "")

col1, col2 = st.columns([1, 1])
with col1:
    analyze = st.button("Analyze")
with col2:
  st.button("Use demo text", on_click=load_demo)
if analyze:

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

    # --- normalize evidence ---
    for p in result.get("pain_points", []):
        interviews = p.get("evidence_interviews", [])
        interviews = list(dict.fromkeys(interviews))
        p["evidence_interviews"] = interviews
        p["evidence_count"] = len(interviews)

        if p["evidence_count"] <= 1:
            p["evidence_strength"] = "low"
        elif p["evidence_count"] == 2:
            p["evidence_strength"] = "medium"
        else:
            p["evidence_strength"] = "high"

    # --- recompute theme evidence ---
    pp_by_label = {p["label"]: p for p in result.get("pain_points", [])}

    for t in result.get("themes", []):
        unique_interviews = set()
        for label in t.get("pain_points", []):
            p = pp_by_label.get(label)
            if p:
                unique_interviews.update(p.get("evidence_interviews", []))
        t["evidence_count"] = len(unique_interviews)

    st.success("Done")

    # ---- ALL rendering must stay here ----

    st.subheader("Key Pain Points")
    for p in result.get("pain_points", []):
        st.markdown(f"### {p.get('label')}")
        st.write(p.get("description"))
        st.caption(f"Segments: {', '.join(p.get('segments', []))}")
        st.caption(f"Evidence interviews: {', '.join(p.get('evidence_interviews', []))}")
        st.caption(f"Evidence count: {p.get('evidence_count')} | Strength: {p.get('evidence_strength')}")
        st.write("")

    st.subheader("Themes")
    for t in result.get("themes", []):
        st.markdown(f"### {t.get('theme')}")
        st.caption(f"Total evidence count: {t.get('evidence_count')}")
        for label in t.get("pain_points", []):
            st.write(f"- {label}")
        st.write("")

    st.subheader("Representative Quotes")
    for q in result.get("quotes", []):
        st.markdown(f'> "{q.get("quote")}"')
        st.caption(
            f'Segment: {q.get("segment")} | Interview: {q.get("interview")} | Supports: {q.get("supports")}'
        )
        st.write("")

    st.subheader("Candidate PMF Hypotheses")
    for h in result.get("pmf_hypotheses", []):
        st.write(f"- {h}")

    st.subheader("Contradictions / Segment Differences")
    for c in result.get("contradictions", []):
        st.write(f"- {c}")

    st.subheader("Open Questions to Validate Next")
    for oq in result.get("open_questions", []):
        st.write(f"- {oq}")

    st.divider()
    st.subheader("Raw JSON")
    st.code(json.dumps(result, indent=2), language="json")
