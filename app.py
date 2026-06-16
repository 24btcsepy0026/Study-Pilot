import streamlit as st
import json
import os
import tempfile
from datetime import datetime, date
from extract import extract_text_from_pdf, extract_syllabus_data, clean_json_response
from planner import allocate_hours, generate_weekly_plan, clean_json_response as clean_planner_json, redistribute_missed_days
from pdf_export import export_timetable_to_pdf
from remainder import send_reminder_email

st.set_page_config(page_title="StudyPilot", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
    <style>
    .main {
        padding: 2rem;
    }
    .input-section {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 2rem;
        border-radius: 1rem;
        margin-bottom: 2rem;
    }
    .results-section {
        background: #f5f5f5;
        padding: 2rem;
        border-radius: 1rem;
    }
    .action-button {
        margin-right: 1rem;
        margin-bottom: 1rem;
    }
    .day-row {
        padding: 1rem;
        margin-bottom: 0.5rem;
        border-radius: 0.5rem;
        border-left: 4px solid;
    }
    </style>
""", unsafe_allow_html=True)

st.title("📚 StudyPilot")
st.markdown("AI-Powered Study Scheduler - Generate Personalized Study Timetables")

if "syllabus_data" not in st.session_state:
    st.session_state.syllabus_data = None
if "timetable_data" not in st.session_state:
    st.session_state.timetable_data = None
if "allocated_subjects" not in st.session_state:
    st.session_state.allocated_subjects = None

st.markdown("---")

col1, col2 = st.columns([1, 2])

with col1:
    st.markdown("### 📋 Setup")

    st.markdown("**Step 1: Upload Syllabus**")
    uploaded_file = st.file_uploader("Upload your syllabus PDF", type="pdf")

    if uploaded_file is not None:
        with st.spinner("Processing PDF..."):
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
                tmp_file.write(uploaded_file.getbuffer())
                tmp_path = tmp_file.name

            try:
                st.info("Extracting text from PDF...")
                pdf_text = extract_text_from_pdf(tmp_path)

                st.info("Sending to AI for analysis...")
                raw_output = extract_syllabus_data(pdf_text)

                st.info("Cleaning and parsing response...")
                cleaned = clean_json_response(raw_output)
                st.session_state.syllabus_data = json.loads(cleaned)

                with open("syllabus.json", "w", encoding="utf-8") as f:
                    json.dump(st.session_state.syllabus_data, f, indent=4, ensure_ascii=False)

                st.success("✅ Syllabus extracted!")

            except Exception as e:
                st.error(f"Error processing PDF: {str(e)}")
            finally:
                os.unlink(tmp_path)

    if st.session_state.syllabus_data:
        st.success(f"✓ {len(st.session_state.syllabus_data)} subjects loaded")

    st.divider()

    st.markdown("**Step 2: Set Study Hours**")
    daily_hours = st.slider(
        "Daily study hours:",
        min_value=1.0,
        max_value=12.0,
        value=4.0,
        step=0.5
    )

    st.markdown("**Step 3: Plan Duration**")
    days_ahead = st.slider(
        "Days to plan ahead:",
        min_value=3,
        max_value=30,
        value=7,
        step=1
    )

    st.markdown("**Step 4: Email Reminders**")
    recipient_email = st.text_input(
        "Email to receive reminders:",
        value=os.getenv("GMAIL_ID", ""),
        help="Leave blank to use Gmail ID from .env"
    )

    st.divider()

    if st.button("🚀 Generate Plan", use_container_width=True, type="primary"):
        if st.session_state.syllabus_data is None:
            st.error("❌ Please upload a syllabus first")
        else:
            with st.spinner("🤖 Creating your personalized timetable..."):
                try:
                    st.session_state.allocated_subjects = allocate_hours(
                        st.session_state.syllabus_data,
                        daily_hours
                    )

                    raw_timetable = generate_weekly_plan(
                        st.session_state.allocated_subjects,
                        daily_hours,
                        days_ahead
                    )

                    cleaned_timetable = clean_planner_json(raw_timetable)
                    st.session_state.timetable_data = json.loads(cleaned_timetable)

                    with open("timetable.json", "w") as f:
                        json.dump(st.session_state.timetable_data, f, indent=2)

                    st.success("✅ Timetable generated!")

                except Exception as e:
                    st.error(f"Error generating timetable: {str(e)}")

with col2:
    if st.session_state.timetable_data is None:
        st.info("📌 Generate a timetable to see your personalized study plan here")

    else:
        st.markdown("### 📅 Your 7-Day Study Timetable")

        timetable = st.session_state.timetable_data.get("timetable", [])

        col_metrics = st.columns(3)
        with col_metrics[0]:
            total_minutes = sum(day["total_study_minutes"] for day in timetable)
            st.metric("Total Study Time", f"{total_minutes//60}h {total_minutes%60}m")
        with col_metrics[1]:
            st.metric("Days Planned", len(timetable))
        with col_metrics[2]:
            avg_daily = total_minutes // len(timetable) if timetable else 0
            st.metric("Avg Daily", f"{avg_daily//60}h {avg_daily%60}m")

        st.divider()

        for day in timetable:
            day_date = datetime.strptime(day["date"], "%Y-%m-%d")
            day_name = day_date.strftime("%a")

            if day["total_study_minutes"] == 0 and any(s["subject"] == "SKIPPED" for s in day["slots"]):
                st.markdown(f"""
                    <div class="day-row" style="border-color: #ffc107; background: #fff3cd;">
                    <b>Day {day['day']} - {day_date.strftime('%d %b')} ({day_name})</b> - ⏭️ SKIPPED
                    </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown(f"""
                    <div class="day-row" style="border-color: #667eea; background: #f0f4ff;">
                    <b>Day {day['day']} - {day_date.strftime('%d %b')} ({day_name})</b> | ⏱️ {day['total_study_minutes']} min
                    </div>
                """, unsafe_allow_html=True)

                for slot in day["slots"]:
                    if slot["subject"] != "SKIPPED":
                        chapters = ", ".join(slot.get("chapters_to_cover", []))
                        st.caption(f"📚 {slot['duration_minutes']} min | {slot['subject']}")
                        if chapters:
                            st.caption(f"   Topics: {chapters}")

        st.divider()

        st.markdown("### 🎯 Actions")

        col_actions = st.columns(4)

        with col_actions[0]:
            if st.button("📥 Download PDF", use_container_width=True):
                try:
                    with st.spinner("Generating PDF..."):
                        export_timetable_to_pdf("timetable.json", "timetable.pdf")

                    with open("timetable.pdf", "rb") as pdf_file:
                        st.download_button(
                            label="📥 Click to Download",
                            data=pdf_file,
                            file_name="timetable.pdf",
                            mime="application/pdf",
                            use_container_width=True
                        )
                    st.success("✅ PDF ready!")
                except Exception as e:
                    st.error(f"Error generating PDF: {str(e)}")

        with col_actions[1]:
            if st.button("📧 Send Email", use_container_width=True):
                if os.getenv("GMAIL_ID") and os.getenv("GMAIL_PASSWORD"):
                    if not recipient_email:
                        st.error("❌ Enter email first")
                    else:
                        with st.spinner("Sending email..."):
                            try:
                                send_reminder_email(recipient_email)
                                st.success("✅ Email sent!")
                            except Exception as e:
                                st.error(f"Error: {str(e)}")
                else:
                    st.warning("⚠️ Gmail credentials not configured")

        with col_actions[2]:
            if st.button("🔄 Redistribute", use_container_width=True):
                st.session_state.show_redistribute = True

        with col_actions[3]:
            if st.button("📋 View Details", use_container_width=True):
                st.session_state.show_details = True

        if st.session_state.get("show_redistribute", False):
            st.divider()
            st.markdown("### 🔄 Missed-Day Redistribution")
            st.info("Select which days you missed (topics will be redistributed to remaining days)")

            missed_days = st.multiselect(
                "Select missed days:",
                options=range(1, len(timetable) + 1),
                help="Topics from missed days will be spread across other days"
            )

            if st.button("✅ Redistribute Topics", use_container_width=True):
                if missed_days:
                    st.session_state.timetable_data = redistribute_missed_days(
                        st.session_state.timetable_data,
                        missed_days
                    )

                    with open("timetable.json", "w") as f:
                        json.dump(st.session_state.timetable_data, f, indent=2)

                    st.success("✅ Timetable updated! Refresh to see changes.")
                    st.session_state.show_redistribute = False
                    st.rerun()
                else:
                    st.warning("⚠️ Select at least one day to redistribute")

        if st.session_state.get("show_details", False):
            st.divider()
            st.markdown("### 📊 Detailed Breakdown")

            for subject in st.session_state.allocated_subjects:
                with st.expander(f"📚 {subject['subject']}"):
                    st.write(f"**Priority Score:** {subject['priority_score']:.2f}")
                    st.write(f"**Daily Time:** {subject['daily_minutes']} minutes")
                    st.write(f"**Exam Date:** {subject.get('exam_date', 'N/A')}")
                    st.write(f"**Chapters:** {len(subject['chapters'])} topics")
                    for chapter in subject['chapters']:
                        st.caption(f"• {chapter}")

st.divider()
st.caption("🎓 StudyPilot v1.0 | Powered by Streamlit & Groq AI")
