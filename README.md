# pmf-interview-synthesizer
AI-assisted synthesis of customer interviews for PMF discovery
import streamlit as st

st.set_page_config(page_title="PMF Interview Synthesizer", layout="centered")

st.title("PMF Interview Synthesizer (MVP)")
st.write("Paste customer interview notes below. This tool will synthesize insights.")

notes = st.text_area("Interview notes or transcript", height=250)

if st.button("Analyze"):
    if not notes.strip():
        st.warning("Please paste interview notes.")
    else:
        st.subheader("Key Pain Points")
        st.write("- Placeholder")

        st.subheader("Themes")
        st.write("- Placeholder")

        st.subheader("Representative Quotes")
        st.write("> Placeholder")

        st.subheader("Candidate PMF Hypotheses")
        st.write("- Placeholder")
      
