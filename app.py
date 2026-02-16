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
    """
    Calls OpenAI Responses API and returns structured JSON.
    """
    system_instructions = (
        "You are an assistant helping early-stage product teams synthesize customer interview notes.\n"
        "Your job: extract evidence-based insights, avoid making up facts, and avoid overconfident conclusions.\n"
        "Return ONLY valid JSON matching the schema exactly. No markdown, no extra text."
    )

    user_prompt = f"""
CONTEXT (optional):
{context.strip()}

RAW INTERVIEW NOTES:
{notes.strip()}

    user_prompt = f"""
CONTEXT (optional):
{context.strip()}

RAW INTERVIEW NOTES:
{notes.strip()}

TASK:
1) Extract 5–10 key customer pain points.
   - Each pain point must include:
     - A short label
     - A clear description
     - The segment(s) who expressed it (e.g., shop owner, manager)
     - An evidence_count (number of distinct interviews mentioning it)

2) Group pain points into 3–6 themes.
   - Each theme must include:
     - Theme name
     - Pain points under it
     - Total evidence_count (sum of mentions across interviews)

3) Provide 6–10 representative quotes.
   - Each quote must include:
     - The quote text (verbatim)
     - The segment (who said it)
     - What pain point it supports

4) Write 4–7 PMF hypotheses in structured format:
   "For [segment] who [problem], we believe [solution direction] will lead to [outcome], validated by [test]."

5) Identify contradictions or segment differences (if any).

6) List 3–6 open validation questions.

STRICT OUTPUT JSON SCHEMA:
{{
  "pain_points": [
    {{
      "label": "...",
      "description": "...",
      "segments": ["..."],
      "evidence_count": 0
    }}
  ],
  "themes": [
    {{
      "theme": "...",
      "pain_points": ["pain_point_label"],
      "evidence_count": 0
    }}
  ],
  "quotes": [
    {{
      "quote": "...",
      "segment": "...",
      "supports": "pain_point_label"
    }}
  ],
  "pmf_hypotheses": ["..."],
  "contradictions": ["..."],
  "open_questions": ["..."]
}}

RULES:
- Use ONLY evidence grounded in the notes.
- evidence_count must reflect distinct interviews, not repeated quotes.
- If evidence is weak, reflect that honestly.
- Return ONLY JSON.
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
        # Encourage reliable JSON output
        "text": {"format": {"type": "json_object"}},
    }

    r = requests.post(url, headers=headers, json=payload, timeout=60)
    if r.status_code != 200:
        raise RuntimeError(f"OpenAI API error {r.status_code}: {r.text}")

    data = r.json()

    # The Responses API returns text in output[0].content[0].text for many models
    # We'll robustly search for the first text chunk.
    json_text = None
    try_paths = [
        lambda d: d["output"][0]["content"][0]["text"],
        lambda d: d["output_text"],
    ]
    for fn in try_paths:
        try:
            candidate = fn(data)
            if isinstance(candidate, str) and candidate.strip():
                json_text = candidate
                break
        except Exception:
            pass

    if not json_text:
        raise RuntimeError("Could not find model output text in response.")

    try:
        return json.loads(json_text)
    except json.JSONDecodeError:
        raise RuntimeError(f"Model did not return valid JSON. Raw output:\n{json_text}")


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
        st.error("Missing OPENAI_API_KEY. Add it in Streamlit Secrets, then rerun the app.")
        st.stop()

    with st.spinner("Analyzing notes..."):
        try:
            result = call_openai_synthesis(api_key=api_key, notes=notes, context=context)
        except Exception as e:
            st.error(f"Analysis failed: {e}")
            st.stop()

    # ----------------------------
    # Render results
    # ----------------------------
    st.success("Done")

    st.subheader("Key Pain Points")
for p in result.get("pain_points", []):
    st.markdown(f"**{p.get('label')}**")
    st.write(p.get("description"))
    st.caption(f"Segments: {', '.join(p.get('segments', []))}")
    st.caption(f"Evidence count: {p.get('evidence_count')}")
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
    st.caption(f'Segment: {q.get("segment")} | Supports: {q.get("supports")}')
    st.write("")

    st.subheader("Candidate PMF Hypotheses")
    for h in result.get("pmf_hypotheses", []):
        st.write(f"- {h}")

    st.subheader("Open Questions to Validate Next")
    for oq in result.get("open_questions", []):
        st.write(f"- {oq}")
        
    st.subheader("Contradictions / Segment Differences")
for c in result.get("contradictions", []):
    st.write(f"- {c}")

    # Useful for copying / debugging
    st.divider()
    st.subheader("Raw JSON (copy/export)")
    st.code(json.dumps(result, indent=2), language="json")
