import streamlit as st
import pdfplumber
import pytesseract
from PIL import Image
import re

# Text extraction function
def pdf_text_extract(file):
    text = ""
    with pdfplumber.open(file) as pdf:
        for page in pdf.pages:
            extracted = page.extract_text()
            if extracted:
                text += extracted + "\n"
    return text


def image_text_extract(file):
    image = Image.open(file)
    text = pytesseract.image_to_string(image)
    return text


# Vitals extraction form text
def extract_vitals(text):

    vitals = {}

    spo2_match = re.search(r"SpO2[:\s]*([0-9]+)%", text, re.IGNORECASE)
    vitals['spo2'] = int(spo2_match.group(1)) if spo2_match else None

    hr_match = re.search(r"(Heart Rate|HR)[:\s]*([0-9]+)", text, re.IGNORECASE)
    vitals['hr'] = int(hr_match.group(2)) if hr_match else None

    temp_match = re.search(r"(Temp|Temperature)[:\s]*([0-9]+\.?[0-9]*)", text, re.IGNORECASE)
    vitals['temp'] = float(temp_match.group(2)) if temp_match else None

    bp_match = re.search(r"BP[:\s]*([0-9]+)/([0-9]+)", text, re.IGNORECASE)

    if bp_match:
        vitals['bp_sys'] = int(bp_match.group(1))
        vitals['bp_dia'] = int(bp_match.group(2))
    else:
        vitals['bp_sys'] = None
        vitals['bp_dia'] = None

    rr_match = re.search(r"(Respiratory Rate|RR)[:\s]*([0-9]+)", text, re.IGNORECASE)
    vitals['rr'] = int(rr_match.group(2)) if rr_match else None

    return vitals


# Priority score function
def priority_score(vitals, chest_pain=False, bleeding=False):

    score = 0

    if vitals['spo2'] is not None:
        if vitals['spo2'] < 90:
            score += 60
        elif vitals['spo2'] < 94:
            score += 30

    if vitals['hr'] is not None:
        if vitals['hr'] > 140:
            score += 40
        elif vitals['hr'] > 110:
            score += 20

    if vitals['temp'] is not None:
        if vitals['temp'] > 103:
            score += 20
        elif vitals['temp'] > 101:
            score += 10

    if vitals['bp_sys'] is not None:
        if vitals['bp_sys'] < 90:
            score += 50
        elif vitals['bp_sys'] < 100:
            score += 20
    
    if vitals['bp_sys'] is not None:
        if vitals['bp_sys'] > 180:
            score += 50
        elif vitals['bp_sys'] < 160:
            score += 20

    if vitals['rr'] is not None:
        if vitals['rr'] > 28:
            score += 40
        elif vitals['rr'] > 22:
            score += 20

    if chest_pain:
        score += 50

    if bleeding:
        score += 60

    return score


# Zone classification
def classify_zone(score):

    if score >= 60:
        return "RED"
    elif score >= 25:
        return "YELLOW"
    else:
        return "GREEN"


# Streamlit
st.set_page_config(page_title="Patient Triage System", layout="wide")

st.title("AI-Based Patient Prioritization System")

patients = []


# Manual entry
st.header("Manual Patient Entry")

manual_entry = st.checkbox("Enter vitals manually")

if manual_entry:

    patient_name = st.text_input("Patient Name")

    col1, col2 = st.columns(2)

    with col1:
        spo2 = st.number_input("SpO2 (%)", 50, 100, 98)
        hr = st.number_input("Heart Rate", 30, 200, 80)
        rr = st.number_input("Respiratory Rate", 5, 50, 16)

    with col2:
        temp = st.number_input("Temperature (F)", 90.0, 110.0, 98.6)
        bp_sys = st.number_input("BP Systolic", 50, 200, 120)
        bp_dia = st.number_input("BP Diastolic", 30, 150, 80)

    chest_pain = st.checkbox("Chest Pain")
    bleeding = st.checkbox("Severe Bleeding")

    if st.button("Add Patient"):

        vitals = {
            "spo2": spo2,
            "hr": hr,
            "temp": temp,
            "bp_sys": bp_sys,
            "bp_dia": bp_dia,
            "rr": rr
        }

        score = priority_score(vitals, chest_pain, bleeding)
        zone = classify_zone(score)

        patients.append({
            "name": patient_name if patient_name else "Manual Patient",
            "score": score,
            "zone": zone
        })

        st.write("Vitals:", vitals)
        st.write("Score:", score)

        if zone == "RED":
            st.error("RED ZONE - Critical")
        elif zone == "YELLOW":
            st.warning("YELLOW ZONE - Moderate")
        else:
            st.success("GREEN ZONE - Stable")


# File upload 
st.header("Upload Patient Reports")

uploaded_files = st.file_uploader(
    "Upload PDF / Image files",
    accept_multiple_files=True
)

if uploaded_files:

    for file in uploaded_files:

        st.subheader(file.name)

        if file.type == "application/pdf":
            text = pdf_text_extract(file)
        else:
            text = image_text_extract(file)

        vitals = extract_vitals(text)

        score = priority_score(vitals)
        zone = classify_zone(score)

        patients.append({
            "name": file.name,
            "score": score,
            "zone": zone
        })

        st.write("Extracted vitals:", vitals)
        st.write("Score:", score)

        if zone == "RED":
            st.error("🔴 RED ZONE")
        elif zone == "YELLOW":
            st.warning("🟡 YELLOW ZONE")
        else:
            st.success("🟢 GREEN ZONE")


# Priority ranking
if patients:

    st.header("Patient Priority Ranking")

    ranked = sorted(patients, key=lambda x: x['score'], reverse=True)

    for i, p in enumerate(ranked, 1):

        if p['zone'] == "RED":
            st.error(f"{i}. {p['name']} | Score {p['score']} | RED")
        elif p['zone'] == "YELLOW":
            st.warning(f"{i}. {p['name']} | Score {p['score']} | YELLOW")
        else:
            st.success(f"{i}. {p['name']} | Score {p['score']} | GREEN")