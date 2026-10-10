import streamlit as st
import pandas as pd
import json
import time
from openai import OpenAI

# ==========================================
# PAGE CONFIGURATION
# ==========================================
st.set_page_config(page_title="Amazon Synthetic A/B Tester", layout="wide", page_icon="🛒")

st.title("🛒 Amazon PDP Synthetic A/B Tester")
st.markdown("Run thousands of synthetic shoppers against your Amazon listings in seconds.")

# ==========================================
# SIDEBAR: API KEY & SETTINGS
# ==========================================
with st.sidebar:
    st.header("️ Settings")
    api_key = st.text_input("OpenAI API Key", type="password", help="Your key starts with sk-...")
    persona_count = st.slider("Number of Personas", 50, 1000, 200, step=50)
    st.caption("💡 Cost estimate: ~$0.01 per 50 personas.")

# ==========================================
# MAIN INPUTS
# ==========================================
col1, col2 = st.columns(2)

with col1:
    st.subheader("📝 Current Listing (Variant A)")
    a_b1 = st.text_area("Bullet 1", height=70)
    a_b2 = st.text_area("Bullet 2", height=70)
    a_b3 = st.text_area("Bullet 3", height=70)
    a_b4 = st.text_area("Bullet 4", height=70)
    a_b5 = st.text_area("Bullet 5", height=70)

with col2:
    st.subheader("🧪 Test Listing (Variant B)")
    b_b1 = st.text_area("Bullet 1", height=70, key="b1")
    b_b2 = st.text_area("Bullet 2", height=70, key="b2")
    b_b3 = st.text_area("Bullet 3", height=70, key="b3")
    b_b4 = st.text_area("Bullet 4", height=70, key="b4")
    b_b5 = st.text_area("Bullet 5", height=70, key="b5")

# Gather bullets into lists
variant_a_bullets = [a_b1, a_b2, a_b3, a_b4, a_b5]
variant_b_bullets = [b_b1, b_b2, b_b3, b_b4, b_b5]

# Clean empty bullets
variant_a_bullets = [b for b in variant_a_bullets if b.strip()]
variant_b_bullets = [b for b in variant_b_bullets if b.strip()]

# ==========================================
# RUN SIMULATION
# ==========================================
if st.button("🚀 Run Synthetic Test", type="primary", use_container_width=True):
    if not api_key.startswith("sk-"):
        st.error("Please enter a valid OpenAI API Key in the sidebar.")
    elif not variant_a_bullets or not variant_b_bullets:
        st.error("Please enter at least one bullet point for both Variant A and Variant B.")
    else:
        client = OpenAI(api_key=api_key)
        
        # 1. Generate Personas
        with st.spinner(f"🤖 Generating {persona_count} synthetic shoppers..."):
            persona_prompt = f"Generate exactly {persona_count} diverse Amazon shopper personas for a shoe rack. Return ONLY a JSON array of strings: ['A 25-year-old...', 'A 40-year-old...']"
            res = client.chat.completions.create(model="gpt-4o-mini", messages=[{"role": "user", "content": persona_prompt}], response_format={"type": "json_object"})
            personas_data = json.loads(res.choices[0].message.content)
            personas = list(personas_data.values())[0] if isinstance(personas_data, dict) else personas_data
        
        st.success(f"✅ Generated {len(personas)} personas. Starting simulation...")
        
        # 2. Run Simulations
        progress_bar = st.progress(0)
        status_text = st.empty()
        results = []
        
        variant_a = {"name": "Current (A)", "bullets": variant_a_bullets}
        variant_b = {"name": "Test (B)", "bullets": variant_b_bullets}
        variants = [variant_a, variant_b]
        
        total_tasks = len(personas) * 2
        current_task = 0

        for persona in personas:
            for variant in variants:
                bullets_text = "\n".join([f"• {b}" for b in variant["bullets"]])
                prompt = f"You are an Amazon shopper: {persona}\nLooking at:\nFEATURES:\n{bullets_text}\nReply ONLY in JSON: {{\"decision\": \"Add to Cart\" or \"Keep Shopping (Bounce)\", \"probability\": 0-100, \"reason\": \"1-sentence\"}}"
                
                try:
                    resp = client.chat.completions.create(model="gpt-4o-mini", messages=[{"role": "user", "content": prompt}], response_format={"type": "json_object"})
                    r = json.loads(resp.choices[0].message.content)
                    results.append({"Variant": variant["name"], "Decision": r.get("decision", "Bounce"), "Probability": r.get("probability", 0), "Reason": r.get("reason", "")})
                except Exception as e:
                    st.warning(f"API Error: {e}")
                
                current_task += 1
                progress_bar.progress(current_task / total_tasks)
                status_text.text(f"Processing shopper {current_task} of {total_tasks}...")

        # 3. Display Results
        status_text.text("✅ Simulation complete! Analyzing data...")
        df = pd.DataFrame(results)
        
        summary = df.groupby('Variant').agg(
            Total=('Decision', 'count'),
            Add_to_Cart=('Decision', lambda x: (x == 'Add to Cart').sum()),
            Bounce=('Decision', lambda x: x.str.contains('Bounce', na=False).sum()),
            Avg_Prob=('Probability', 'mean')
        ).round(2)
        summary['Conv_Rate (%)'] = (summary['Add_to_Cart'] / summary['Total'] * 100).round(2)

        a_conv = summary.loc['Current (A)', 'Conv_Rate (%)']
        b_conv = summary.loc['Test (B)', 'Conv_Rate (%)']
        lift = ((b_conv - a_conv) / a_conv * 100).round(2) if a_conv > 0 else 0

        st.markdown("### 📊 Executive Summary")
        col1, col2, col3 = st.columns(3)
        col1.metric("Variant A Conversion", f"{a_conv}%")
        col2.metric("Variant B Conversion", f"{b_conv}%")
        col3.metric("Projected Lift", f"{lift:+.2f}%")

        if lift > 5:
            st.success("✅ **Recommendation:** DEPLOY VARIANT B - Strong positive signal.")
        elif lift > 0:
            st.warning("️ **Recommendation:** MARGINAL IMPROVEMENT - Consider testing on Amazon.")
        else:
            st.error("❌ **Recommendation:** STICK WITH VARIANT A - Test variant underperformed.")

        st.markdown("### 📈 Detailed Metrics")
        st.dataframe(summary)
        
        st.markdown("### 🔍 Top Conversion Drivers (Variant B)")
        top_reasons = df[df['Variant'] == 'Test (B)'][df['Decision'] == 'Add to Cart']['Reason'].head(5)
        for i, reason in enumerate(top_reasons, 1):
            st.markdown(f"{i}. {reason}")
            
        st.download_button("💾 Download Full CSV Data", df.to_csv(index=False), file_name="synthetic_test_results.csv", mime="text/csv")