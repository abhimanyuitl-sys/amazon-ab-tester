import streamlit as st
import pandas as pd
import json
import re
import cloudscraper
from bs4 import BeautifulSoup
from openai import OpenAI
from fpdf import FPDF
import datetime

# ==========================================
# PAGE CONFIGURATION & SESSION STATE
# ==========================================
st.set_page_config(page_title="Amazon Full-Funnel Simulator", layout="wide", page_icon="🛒")

if 'pdf_bytes' not in st.session_state:
    st.session_state['pdf_bytes'] = None
if 'last_metrics' not in st.session_state:
    st.session_state['last_metrics'] = None

st.title(" Amazon Full-Funnel SERP & PDP Simulator")
st.markdown("Simulate the entire customer journey: From Search Results (SEO/CTR) to Product Page (Conversion).")

# ==========================================
# SIDEBAR: API KEY & SETTINGS
# ==========================================
with st.sidebar:
    st.header("⚙️ Settings")
    api_key = st.text_input("OpenAI API Key", type="password", help="Your key starts with sk-...")
    test_type = st.radio("What do you want to test?", ["Title", "Bullet Points", "Title + Bullet Points"], horizontal=False)
    persona_count = st.slider("Number of Personas (for PDP)", 50, 500, 100, step=50)
    st.caption("💡 Cost estimate: ~$0.02 per 100 personas + 10 keywords.")

# ==========================================
# HELPER FUNCTIONS
# ==========================================
def get_price_diff(p1, p2):
    try:
        num1 = float(re.sub(r'[^\d.]', '', p1))
        num2 = float(re.sub(r'[^\d.]', '', p2))
        if num1 == 0: return 0
        return round(((num1 - num2) / num1) * 100, 1)
    except: return 0

def scrape_amazon(url):
    scraper = cloudscraper.create_scraper(browser={'browser': 'chrome', 'platform': 'windows', 'mobile': False})
    try:
        response = scraper.get(url, timeout=15)
        if response.status_code != 200 or "captcha" in response.text.lower(): return "", []
        soup = BeautifulSoup(response.text, 'html.parser')
        title_tag = soup.find('span', {'id': 'productTitle'})
        title = title_tag.get_text(strip=True) if title_tag else ""
        subtitle = ""
        subtitle_tag = soup.find('span', {'id': 'productSubtitle'})
        if subtitle_tag: subtitle = subtitle_tag.get_text(strip=True)
        full_title = f"{title}\n{subtitle}" if subtitle else title
        bullets = []
        bullet_container = soup.find('div', {'id': 'feature-bullets'})
        if bullet_container:
            for li in bullet_container.find_all('li'):
                span = li.find('span', {'class': 'a-list-item'})
                if span and span.get_text(strip=True): bullets.append(span.get_text(strip=True))
        return full_title, bullets[:5] 
    except: return "", []

def strip_emojis(text):
    emoji_pattern = re.compile("["
        u"\U0001F600-\U0001F64F"
        u"\U0001F300-\U0001F5FF"
        u"\U0001F680-\U0001F6FF"
        u"\U0001F1E0-\U0001F1FF"
        "]+", flags=re.UNICODE)
    return emoji_pattern.sub(r'', str(text))

# ==========================================
# MAIN INPUTS
# ==========================================
st.subheader("💰 Pricing & Target Keywords")
col_p1, col_p2 = st.columns(2)
with col_p1: a_price = st.text_input("Price (Variant A)", value="$37.61")
with col_p2: b_price = st.text_input("Price (Variant B)", value="$29.99")

keywords_input = st.text_area("🎯 Target Search Keywords (Comma-separated, up to 10)", 
                              value="metal shoe rack, shoe organizer for closet, 5 tier shoe rack, stackable shoe shelf", 
                              height=80)
keywords = [k.strip() for k in keywords_input.split(',') if k.strip()][:10]
if keywords:
    st.info(f"🔍 Simulating SERP for **{len(keywords)}** keywords: {', '.join(keywords)}")

price_diff = get_price_diff(a_price, b_price)
if price_diff > 0: st.info(f"💡 Variant B is **{price_diff}% cheaper** than Variant A.")
st.markdown("---")

st.subheader("️ Auto-Fill Variant A from URL")
col_url, col_btn = st.columns([3, 1])
with col_url: amazon_url = st.text_input("Paste Amazon Product URL", placeholder="https://www.amazon.com/dp/...")
with col_btn:
    st.write(""); st.write("")
    scrape_clicked = st.button("🕷️ Auto-Fill", use_container_width=True)

if scrape_clicked and amazon_url:
    with st.spinner("Bypassing security and scraping..."):
        scraped_title, scraped_bullets = scrape_amazon(amazon_url)
        if scraped_title:
            st.session_state['scraped_title'] = scraped_title
            st.session_state['scraped_bullets'] = scraped_bullets
            st.success(f"✅ Scraped Title and {len(scraped_bullets)} Bullets!")
        else: st.error("❌ Amazon blocked the request. Please paste manually.")

if 'scraped_title' not in st.session_state: st.session_state['scraped_title'] = ""
if 'scraped_bullets' not in st.session_state: st.session_state['scraped_bullets'] = ["", "", "", "", ""]
while len(st.session_state['scraped_bullets']) < 5: st.session_state['scraped_bullets'].append("")

# ==========================================
# DYNAMIC INPUTS
# ==========================================
content_a = ""; content_b = ""; content_label = ""

if test_type == "Title":
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("📝 Current Title (Variant A)")
        a_title = st.text_area("Title A", height=100, value=st.session_state['scraped_title'])
    with col2:
        st.subheader("🧪 Test Title (Variant B)")
        b_title = st.text_area("Title B", height=100)
    content_a = a_title; content_b = b_title; content_label = "TITLE"

elif test_type == "Bullet Points":
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("📝 Current Bullets (Variant A)")
        a_b1 = st.text_area("Bullet 1", height=60, value=st.session_state['scraped_bullets'][0])
        a_b2 = st.text_area("Bullet 2", height=60, value=st.session_state['scraped_bullets'][1])
        a_b3 = st.text_area("Bullet 3", height=60, value=st.session_state['scraped_bullets'][2])
        a_b4 = st.text_area("Bullet 4", height=60, value=st.session_state['scraped_bullets'][3])
        a_b5 = st.text_area("Bullet 5", height=60, value=st.session_state['scraped_bullets'][4])
        content_a = "\n".join([f"- {b}" for b in [a_b1, a_b2, a_b3, a_b4, a_b5] if b.strip()])
    with col2:
        st.subheader("🧪 Test Bullets (Variant B)")
        b_b1 = st.text_area("Bullet 1", height=60, key="b1")
        b_b2 = st.text_area("Bullet 2", height=60, key="b2")
        b_b3 = st.text_area("Bullet 3", height=60, key="b3")
        b_b4 = st.text_area("Bullet 4", height=60, key="b4")
        b_b5 = st.text_area("Bullet 5", height=60, key="b5")
        content_b = "\n".join([f"- {b}" for b in [b_b1, b_b2, b_b3, b_b4, b_b5] if b.strip()])
    content_label = "KEY FEATURES"
else: 
    st.subheader("📝 Current Listing (Variant A)")
    a_title = st.text_area("Title A", height=100, value=st.session_state['scraped_title'])
    a_b1 = st.text_area("Bullet 1", height=60, value=st.session_state['scraped_bullets'][0])
    a_b2 = st.text_area("Bullet 2", height=60, value=st.session_state['scraped_bullets'][1])
    a_b3 = st.text_area("Bullet 3", height=60, value=st.session_state['scraped_bullets'][2])
    a_b4 = st.text_area("Bullet 4", height=60, value=st.session_state['scraped_bullets'][3])
    a_b5 = st.text_area("Bullet 5", height=60, value=st.session_state['scraped_bullets'][4])
    content_a = f"TITLE: {a_title}\n\nBULLET POINTS:\n" + "\n".join([f"- {b}" for b in [a_b1, a_b2, a_b3, a_b4, a_b5] if b.strip()])

    st.subheader("🧪 Test Listing (Variant B)")
    b_title = st.text_area("Title B", height=100, key="b_title")
    b_b1 = st.text_area("Bullet 1", height=60, key="b1")
    b_b2 = st.text_area("Bullet 2", height=60, key="b2")
    b_b3 = st.text_area("Bullet 3", height=60, key="b3")
    b_b4 = st.text_area("Bullet 4", height=60, key="b4")
    b_b5 = st.text_area("Bullet 5", height=60, key="b5")
    content_b = f"TITLE: {b_title}\n\nBULLET POINTS:\n" + "\n".join([f"- {b}" for b in [b_b1, b_b2, b_b3, b_b4, b_b5] if b.strip()])
    content_label = "LISTING DETAILS"

# ==========================================
# RUN FULL-FUNNEL SIMULATION
# ==========================================
if st.button("🚀 Run Full-Funnel Simulation", type="primary", use_container_width=True):
    if not api_key.startswith("sk-"): st.error("Please enter a valid OpenAI API Key.")
    elif not content_a.strip() or not content_b.strip(): st.error("Please enter content for both variants.")
    else:
        client = OpenAI(api_key=api_key)
        
        # --- PHASE 1: SERP & SEO SIMULATION ---
        st.markdown("### 🔍 Phase 1: Simulating Search Results (SERP)")
        seo_results = []
        progress_seo = st.progress(0)
        
        for i, keyword in enumerate(keywords):
            for variant_name, content in [("Variant A", content_a), ("Variant B", content_b)]:
                prompt = f"""You are an Amazon Shopper AND the Amazon A10 Search Algorithm.
                A shopper types this EXACT phrase into the Amazon search bar: "{keyword}"
                They see this product title in the search results:
                "{content}"
                
                Evaluate two things:
                1. SEO Relevance (0-100): How perfectly does this title match the search intent of "{keyword}"?
                2. SERP Click-Through Rate (0-100): In a crowded search results page, how likely is the shopper to click THIS title over competitors?
                
                Reply ONLY in JSON: {{"seo_score": 0-100, "ctr_score": 0-100, "reason": "1-sentence explanation"}}"""
                
                try:
                    resp = client.chat.completions.create(model="gpt-4o-mini", messages=[{"role": "user", "content": prompt}], response_format={"type": "json_object"})
                    r = json.loads(resp.choices[0].message.content)
                    seo_results.append({"Keyword": keyword, "Variant": variant_name, "SEO_Score": r.get("seo_score", 0), "CTR_Score": r.get("ctr_score", 0), "Reason": r.get("reason", "")})
                except: pass
            progress_seo.progress((i + 1) / len(keywords))
        
        st.success("✅ Phase 1 Complete! Analyzing Search Performance...")
        df_seo = pd.DataFrame(seo_results)
        seo_summary = df_seo.groupby('Variant')[['SEO_Score', 'CTR_Score']].mean().round(1)

        # --- PHASE 2: PDP CONVERSION SIMULATION ---
        st.markdown("### 🛒 Phase 2: Simulating Product Page (PDP) Conversion")
        with st.spinner(f"🤖 Generating {persona_count} synthetic shoppers..."):
            personas = []
            batch_size = 25 
            for i in range((persona_count // batch_size) + 1):
                remaining = persona_count - len(personas)
                if remaining <= 0: break
                current_batch = min(batch_size, remaining)
                prompt = f"""Generate exactly {current_batch} diverse Amazon shopper personas. 
                Return ONLY a JSON array of objects with 'persona' (string) and 'price_sensitivity' ('High', 'Medium', 'Low').
                Mix: 40% High, 40% Medium, 20% Low."""
                try:
                    res = client.chat.completions.create(model="gpt-4o-mini", messages=[{"role": "user", "content": prompt}], response_format={"type": "json_object"})
                    data = json.loads(res.choices[0].message.content)
                    if isinstance(data, list): personas.extend(data)
                    elif isinstance(data, dict):
                        for v in data.values():
                            if isinstance(v, list): personas.extend(v); break
                except: pass
            personas = personas[:persona_count]
        
        st.success(f"✅ Generated {len(personas)} personas. Running PDP simulation...")
        progress_bar = st.progress(0)
        status_text = st.empty()
        results = []
        
        variant_a = {"name": "Variant A", "price": a_price, "content": content_a}
        variant_b = {"name": "Variant B", "price": b_price, "content": content_b}
        variants = [variant_a, variant_b]
        total_tasks = len(personas) * 2
        current_task = 0

        for persona_obj in personas:
            persona_text = persona_obj.get("persona", "Unknown")
            price_sens = persona_obj.get("price_sensitivity", "Medium")
            for variant in variants:
                prompt = f"""You are an Amazon shopper: {persona_text}
                Trait: '{price_sens}' price sensitive. 
                CONTEXT: Exact same product, quality, and reviews. Only copy and price differ.
                Price: {variant['price']}
                {content_label}: {variant['content']}
                
                RULES: If cheaper and you are High/Medium sensitivity, view as great deal (prob 85-95%). Do not assume cheaper = lower quality.
                Reply JSON: {{"decision": "Add to Cart" or "Keep Shopping (Bounce)", "probability": 0-100, "reason": "1-sentence"}}"""
                try:
                    resp = client.chat.completions.create(model="gpt-4o-mini", messages=[{"role": "user", "content": prompt}], response_format={"type": "json_object"})
                    r = json.loads(resp.choices[0].message.content)
                    results.append({"Variant": variant["name"], "Decision": r.get("decision", "Bounce"), "Probability": r.get("probability", 0)})
                except: pass
                current_task += 1
                progress_bar.progress(current_task / total_tasks)
                status_text.text(f"Processing shopper {current_task} of {total_tasks}...")

        # --- FINAL ANALYSIS & PDF GENERATION ---
        status_text.text("✅ Simulation complete! Calculating Full-Funnel Impact...")
        df_cvr = pd.DataFrame(results)
        cvr_summary = df_cvr.groupby('Variant').agg(
            Add_to_Cart=('Decision', lambda x: (x == 'Add to Cart').sum()),
            Total=('Decision', 'count')
        ).round(2)
        cvr_summary['CVR (%)'] = (cvr_summary['Add_to_Cart'] / cvr_summary['Total'] * 100).round(2)
        
        final_metrics = seo_summary.join(cvr_summary[['CVR (%)']])
        final_metrics['Projected_Sales_Index'] = (final_metrics['CTR_Score'] * final_metrics['CVR (%)']).round(2)
        
        a_sales = final_metrics.loc['Variant A', 'Projected_Sales_Index']
        b_sales = final_metrics.loc['Variant B', 'Projected_Sales_Index']
        total_lift = ((b_sales - a_sales) / a_sales * 100).round(2) if a_sales > 0 else 0

        st.session_state['last_metrics'] = {
            'final_metrics': final_metrics,
            'total_lift': total_lift,
            'df_seo': df_seo
        }

        # --- PDF GENERATION ---
        try:
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", size=12)
            
            pdf.set_font("Arial", 'B', 16)
            pdf.cell(0, 10, "Amazon Full-Funnel Simulation Report", ln=True, align='C')
            pdf.set_font("Arial", size=10)
            pdf.cell(0, 10, f"Generated on: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}", ln=True, align='C')
            pdf.ln(10)
            
            pdf.set_font("Arial", 'B', 14)
            pdf.cell(0, 10, "Executive Summary (Variant B)", ln=True)
            pdf.set_font("Arial", size=11)
            pdf.cell(0, 8, f"Avg SEO Score: {final_metrics.loc['Variant B', 'SEO_Score']}/100", ln=True)
            pdf.cell(0, 8, f"Avg CTR Score: {final_metrics.loc['Variant B', 'CTR_Score']}/100", ln=True)
            pdf.cell(0, 8, f"PDP Conversion Rate: {final_metrics.loc['Variant B', 'CVR (%)']}%", ln=True)
            pdf.cell(0, 8, f"Total Projected Sales Lift: {total_lift:+.2f}%", ln=True)
            pdf.ln(10)
            
            pdf.set_font("Arial", 'B', 14)
            pdf.cell(0, 10, "Keyword-by-Keyword SERP Breakdown", ln=True)
            pdf.set_font("Arial", size=9)
            
            pdf.set_fill_color(200, 220, 255)
            pdf.cell(40, 8, "Keyword", 1, 0, 'C', True)
            pdf.cell(30, 8, "Variant", 1, 0, 'C', True)
            pdf.cell(20, 8, "SEO", 1, 0, 'C', True)
            pdf.cell(20, 8, "CTR", 1, 0, 'C', True)
            pdf.cell(70, 8, "Reason", 1, 1, 'C', True)
            
            for index, row in df_seo.iterrows():
                reason = strip_emojis(str(row['Reason']))[:45] + "..." if len(str(row['Reason'])) > 45 else strip_emojis(str(row['Reason']))
                pdf.cell(40, 8, strip_emojis(str(row['Keyword']))[:20], 1, 0, 'L')
                pdf.cell(30, 8, str(row['Variant']), 1, 0, 'L')
                pdf.cell(20, 8, str(row['SEO_Score']), 1, 0, 'C')
                pdf.cell(20, 8, str(row['CTR_Score']), 1, 0, 'C')
                pdf.cell(70, 8, reason, 1, 1, 'L')
                
            st.session_state['pdf_bytes'] = pdf.output()
            st.session_state['pdf_ready'] = True
        except Exception as e:
            st.error(f"PDF generation failed: {e}")
            st.session_state['pdf_ready'] = False

# ==========================================
# DISPLAY RESULTS & PDF BUTTON
# ==========================================
if st.session_state.get('last_metrics'):
    fm = st.session_state['last_metrics']['final_metrics']
    tl = st.session_state['last_metrics']['total_lift']
    df_seo_display = st.session_state['last_metrics']['df_seo']

    st.markdown("### 📊 FULL-FUNNEL EXECUTIVE SUMMARY")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Avg SEO Score", f"{fm.loc['Variant B', 'SEO_Score']}/100", f"{fm.loc['Variant B', 'SEO_Score'] - fm.loc['Variant A', 'SEO_Score']:+.1f} vs A")
    col2.metric("Avg CTR Score", f"{fm.loc['Variant B', 'CTR_Score']}/100", f"{fm.loc['Variant B', 'CTR_Score'] - fm.loc['Variant A', 'CTR_Score']:+.1f} vs A")
    col3.metric("PDP Conv. Rate", f"{fm.loc['Variant B', 'CVR (%)']}%", f"{fm.loc['Variant B', 'CVR (%)'] - fm.loc['Variant A', 'CVR (%)']:+.2f}% vs A")
    col4.metric("Total Sales Lift", f"{tl:+.2f}%", "CTR x CVR Impact")

    if tl > 5: st.success("✅ **DEPLOY VARIANT B** - Strong positive signal across the full funnel.")
    elif tl > 0: st.warning("⚠️ **MARGINAL IMPROVEMENT** - Consider testing on Amazon.")
    else: st.error("❌ **STICK WITH VARIANT A** - Test variant underperformed.")

    st.markdown("### 🔍 Keyword-by-Keyword SERP Breakdown")
    st.dataframe(df_seo_display)
    
    st.markdown("---")
    if st.session_state.get('pdf_ready'):
        st.success("📄 PDF Report Generated Successfully!")
        st.download_button(
            label="⬇️ DOWNLOAD FULL PDF REPORT",
            data=st.session_state['pdf_bytes'],
            file_name="amazon_simulation_report.pdf",
            mime="application/pdf",
            use_container_width=True,
            type="primary"
        )
    else:
        st.warning("⚠️ PDF generation failed. Please check for special characters in your input.")
else:
    st.info(" Run a simulation to see results and generate a PDF.")
