import streamlit as st
import zipfile
import os
import mailbox
from icalendar import Calendar
import json
from datetime import datetime
import hashlib

UPLOAD_DIR = "uploads"
UNZIP_DIR = "unzipped_takeout"
OUTPUT_DIR = "structured_output"

st.title("🧠 Life Ingestor – Google Takeout Parser (Multi-ZIP Support)")
uploaded_files = st.file_uploader(
    "Upload one or more Google Takeout ZIPs",
    type="zip",
    accept_multiple_files=True
)

all_events = []
all_emails = []

if uploaded_files:
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    os.makedirs(UNZIP_DIR, exist_ok=True)
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    for uploaded_file in uploaded_files:
        # Save each file with a hashed name to avoid conflicts
        file_hash = hashlib.sha1(uploaded_file.name.encode()).hexdigest()
        zip_path = os.path.join(UPLOAD_DIR, f"{file_hash}.zip")

        with open(zip_path, "wb") as f:
            f.write(uploaded_file.read())

        # Unzip each file into its own subfolder
        extract_path = os.path.join(UNZIP_DIR, file_hash)
        os.makedirs(extract_path, exist_ok=True)

        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_path)

        st.success(f"✅ Extracted: {uploaded_file.name}")

        # --- Parse Calendar Files ---
        st.subheader(f"📅 Parsing Calendar in {uploaded_file.name}...")
        for root, _, files in os.walk(extract_path):
            for file in files:
                if file.endswith(".ics"):
                    try:
                        with open(os.path.join(root, file), 'rb') as f:
                            cal = Calendar.from_ical(f.read())
                            for component in cal.walk():
                                if component.name == "VEVENT":
                                    event = {
                                        "type": "calendar_event",
                                        "timestamp": component.get('dtstart').dt.isoformat() if hasattr(component.get('dtstart').dt, 'isoformat') else str(component.get('dtstart').dt),
                                        "title": str(component.get('summary')),
                                        "source": "google_calendar",
                                        "source_file": uploaded_file.name
                                    }
                                    all_events.append(event)
                    except Exception as e:
                        st.warning(f"Could not parse calendar file: {file} - {e}")

        # --- Parse Gmail Headers ---
        st.subheader(f"📧 Parsing Emails in {uploaded_file.name}...")
        for root, _, files in os.walk(extract_path):
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
                                "source": "gmail",
                                "source_file": uploaded_file.name
                            }
                            all_emails.append(email)
                    except Exception as e:
                        st.warning(f"Could not parse email file: {file} - {e}")

    # --- Output Structured JSON ---
    st.subheader("📦 Saving Structured Output...")
    with open(os.path.join(OUTPUT_DIR, "calendar_events.json"), "w") as f:
        json.dump(all_events, f, indent=2)

    with open(os.path.join(OUTPUT_DIR, "emails.json"), "w") as f:
        json.dump(all_emails, f, indent=2)

    st.success("🎉 All data saved and structured!")
    st.download_button("Download All Calendar Events", json.dumps(all_events, indent=2), file_name="calendar_events.json")
    st.download_button("Download All Emails", json.dumps(all_emails, indent=2), file_name="emails.json")
