
import streamlit as st
import zipfile
import os
import mailbox
from icalendar import Calendar
import json
from datetime import datetime

UPLOAD_DIR = "uploads"
UNZIP_DIR = "unzipped_takeout"
OUTPUT_DIR = "structured_output"

st.title("🧠 Life Ingestor – Google Takeout Parser")

uploaded_file = st.file_uploader("Upload your Google Takeout ZIP", type="zip")

if uploaded_file:
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    zip_path = os.path.join(UPLOAD_DIR, "takeout.zip")

    with open(zip_path, "wb") as f:
        f.write(uploaded_file.read())

    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(UNZIP_DIR)

    st.success("✅ ZIP extracted!")

    # --- Parse Calendar Files ---
    st.subheader("📅 Parsing Calendar Data...")
    events = []
    for root, _, files in os.walk(UNZIP_DIR):
        for file in files:
            if file.endswith(".ics"):
                with open(os.path.join(root, file), 'rb') as f:
                    try:
                        cal = Calendar.from_ical(f.read())
                        for component in cal.walk():
                            if component.name == "VEVENT":
                                event = {
                                    "type": "calendar_event",
                                    "timestamp": component.get('dtstart').dt.isoformat() if hasattr(component.get('dtstart').dt, 'isoformat') else str(component.get('dtstart').dt),
                                    "title": str(component.get('summary')),
                                    "source": "google_calendar"
                                }
                                events.append(event)
                    except Exception as e:
                        st.warning(f"Could not parse calendar file: {file} - {e}")

    st.write(f"Parsed {len(events)} calendar events.")

    # --- Parse Gmail Headers from MBOX ---
    st.subheader("📧 Parsing Email Headers...")
    emails = []
    for root, _, files in os.walk(UNZIP_DIR):
        for file in files:
            if file.endswith(".mbox"):
                try:
                    mbox = mailbox.mbox(os.path.join(root, file))
                    for msg in mbox:
                        email = {
                            "type": "email_header",
                            "timestamp": msg.get("date"),
                            "from": msg.get("from"),
                            "to": msg.get("to"),
                            "subject": msg.get("subject"),
                            "source": "gmail"
                        }
                        emails.append(email)
                except Exception as e:
                    st.warning(f"Could not parse email file: {file} - {e}")

    st.write(f"Parsed {len(emails)} emails.")

    # --- Output Structured JSON ---
    st.subheader("📦 Saving Structured Output...")
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    with open(os.path.join(OUTPUT_DIR, "calendar_events.json"), "w") as f:
        json.dump(events, f, indent=2)

    with open(os.path.join(OUTPUT_DIR, "emails.json"), "w") as f:
        json.dump(emails, f, indent=2)

    st.success("🎉 Data saved and structured!")
    st.download_button("Download Calendar JSON", json.dumps(events, indent=2), file_name="calendar_events.json")
    st.download_button("Download Emails JSON", json.dumps(emails, indent=2), file_name="emails.json")
