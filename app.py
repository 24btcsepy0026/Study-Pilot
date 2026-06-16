import streamlit as st
import json
import os
import tempfile
from datetime import datetime, date
from extract import extract_text_from_pdf, extract_syllabus_data, clean_json_response
from planner import allocate_hours, generate_weekly_plan, clean_json_response as clean_planner_json
from pdf_export import export_timetable_to_pdf
from remainder import send_reminder_email

st.set_page_config(page_title="StudyPilot", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
    <style>
    .main {
        padding: 2rem;
    }
    .stTabs [data-baseweb="tab-list"] button {
        font-size: 1.1rem;
        font-weight: 600;
    }
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 1.5rem;
        border-radius: 0.5rem;
        text-align: center;
    }
    </style>
""", unsafe_allow_html=True)

st.title("📚 StudyPilot - AI-Powered Study Scheduler")
st.markdown("Generate personalized study timetables using AI")

if "syllabus_data" not in st.session_state:
    st.session_state.syllabus_data = None
if "timetable_data" not in st.session_state:
    st.session_state.timetable_data = None
if "allocated_subjects" not in st.session_state:
    st.session_state.allocated_subjects = None

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📖 Upload Syllabus",
    "⏱️ Time Allocation",
    "📅 Generate Timetable",
    "📊 View Schedule",
    "⚙️ Settings"
])

with tab1:
    st.header("Upload & Extract Syllabus")

    st.subheader("📄 Upload PDF")
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

                st.success("✅ Syllabus extracted successfully!")

            except Exception as e:
                st.error(f"Error processing PDF: {str(e)}")
            finally:
                os.unlink(tmp_path)

    if st.session_state.syllabus_data:
        st.subheader("Extracted Subjects")

        subjects_df = []
        for item in st.session_state.syllabus_data:
            subjects_df.append({
                "Subject": item.get("subject"),
                "Unit": item.get("unit"),
                "Chapters": len(item.get("chapters", [])),
                "Exam Date": item.get("exam_date", "N/A"),
                "Weightage": item.get("weightage", "N/A")
            })

        st.dataframe(subjects_df, use_container_width=True)

        with st.expander("View Full Details"):
            for i, item in enumerate(st.session_state.syllabus_data, 1):
                st.write(f"**{i}. {item['subject']} - {item['unit']}**")
                st.write(f"Chapters: {', '.join(item['chapters'])}")
                st.write(f"Exam Date: {item.get('exam_date', 'N/A')} | Weightage: {item.get('weightage', 'N/A')}")
                st.divider()

with tab2:
    st.header("Time Allocation & Priority")

    if st.session_state.syllabus_data is None:
        st.info("📌 Please upload a syllabus first in the 'Upload Syllabus' tab")
    else:
        col1, col2 = st.columns([3, 1])

        with col1:
            daily_hours = st.slider(
                "How many hours per day can you study?",
                min_value=1.0,
                max_value=12.0,
                value=4.0,
                step=0.5
            )

        with col2:
            if st.button("🔄 Allocate Hours", key="allocate"):
                with st.spinner("Calculating priorities..."):
                    st.session_state.allocated_subjects = allocate_hours(
                        st.session_state.syllabus_data,
                        daily_hours
                    )

        if st.session_state.allocated_subjects:
            st.subheader("Priority-Based Time Allocation")

            allocation_data = []
            total_daily_minutes = sum(s["daily_minutes"] for s in st.session_state.allocated_subjects)

            for i, subject in enumerate(st.session_state.allocated_subjects, 1):
                percentage = (subject["daily_minutes"] / total_daily_minutes * 100) if total_daily_minutes > 0 else 0
                allocation_data.append({
                    "Priority": i,
                    "Subject": subject["subject"],
                    "Daily Time": f"{subject['daily_minutes']} min",
                    "Priority Score": f"{subject['priority_score']:.2f}",
                    "Exam Date": subject.get("exam_date", "N/A"),
                    "Allocation %": f"{percentage:.1f}%"
                })

            st.dataframe(allocation_data, use_container_width=True)

            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Daily Study", f"{daily_hours:.1f} hrs")
            with col2:
                st.metric("Subjects", len(st.session_state.allocated_subjects))
            with col3:
                st.metric("Total Minutes", total_daily_minutes)

            with st.expander("View Subject Details"):
                for subject in st.session_state.allocated_subjects:
                    st.write(f"**{subject['subject']}**")
                    st.write(f"Chapters: {len(subject['chapters'])} topics")
                    st.write(f"Daily allocation: {subject['daily_minutes']} minutes")
                    st.write(f"Priority score: {subject['priority_score']:.2f}")
                    st.divider()

with tab3:
    st.header("Generate Your Study Timetable")

    if st.session_state.allocated_subjects is None:
        st.info("📌 Please complete time allocation in the previous tab")
    else:
        col1, col2 = st.columns(2)

        with col1:
            days_ahead = st.slider(
                "Number of days to plan ahead",
                min_value=3,
                max_value=30,
                value=7,
                step=1
            )

        with col2:
            daily_hours = st.number_input(
                "Daily study hours",
                min_value=1.0,
                max_value=12.0,
                value=4.0,
                step=0.5
            )

        if st.button("📅 Generate Timetable", key="generate"):
            with st.spinner("🤖 AI is creating your personalized timetable..."):
                try:
                    raw_timetable = generate_weekly_plan(
                        st.session_state.allocated_subjects,
                        daily_hours,
                        days_ahead
                    )

                    cleaned_timetable = clean_planner_json(raw_timetable)
                    st.session_state.timetable_data = json.loads(cleaned_timetable)

                    with open("timetable.json", "w") as f:
                        json.dump(st.session_state.timetable_data, f, indent=2)

                    st.success("✅ Timetable generated successfully!")

                except Exception as e:
                    st.error(f"Error generating timetable: {str(e)}")

        if st.session_state.timetable_data:
            st.subheader("✨ Your Generated Timetable")

            timetable = st.session_state.timetable_data.get("timetable", [])

            col1, col2, col3 = st.columns(3)
            with col1:
                total_minutes = sum(day["total_study_minutes"] for day in timetable)
                st.metric("Total Study Time", f"{total_minutes//60}h {total_minutes%60}m")
            with col2:
                st.metric("Days Planned", len(timetable))
            with col3:
                avg_daily = total_minutes // len(timetable) if timetable else 0
                st.metric("Avg Daily Study", f"{avg_daily//60}h {avg_daily%60}m")

with tab4:
    st.header("📊 View Your Schedule")

    if st.session_state.timetable_data is None:
        st.info("📌 Please generate a timetable first")
    else:
        timetable = st.session_state.timetable_data.get("timetable", [])

        view_type = st.radio("Select view:", ["Daily Breakdown", "Weekly Summary", "Raw JSON"])

        if view_type == "Daily Breakdown":
            for day in timetable:
                day_date = datetime.strptime(day["date"], "%Y-%m-%d")
                day_name = day_date.strftime("%A")

                with st.expander(f"📅 Day {day['day']} - {day_date.strftime('%d %B')} ({day_name})", expanded=day["day"] == 1):
                    col1, col2 = st.columns([3, 1])
                    with col2:
                        st.metric("Total Study Time", f"{day['total_study_minutes']} min")

                    for i, slot in enumerate(day["slots"], 1):
                        st.write(f"**Slot {i}: {slot['subject']}**")
                        st.write(f"⏱️ Duration: {slot['duration_minutes']} minutes")

                        chapters = slot.get("chapters_to_cover", [])
                        if chapters:
                            st.write("📚 Chapters to cover:")
                            for chapter in chapters:
                                st.write(f"  • {chapter}")

                        if slot.get("notes"):
                            st.info(f"📝 Note: {slot['notes']}")

                        st.divider()

        elif view_type == "Weekly Summary":
            st.subheader("Weekly Summary")

            if st.session_state.timetable_data.get("weekly_summary"):
                st.write(st.session_state.timetable_data["weekly_summary"])

            st.subheader("Week Overview")

            week_data = []
            for day in timetable:
                subjects = [slot['subject'] for slot in day['slots']]
                unique_subjects = ", ".join(set(subjects))

                week_data.append({
                    "Date": day["date"],
                    "Day": datetime.strptime(day["date"], "%Y-%m-%d").strftime("%a"),
                    "Subjects": unique_subjects,
                    "Total Time (min)": day["total_study_minutes"]
                })

            st.dataframe(week_data, use_container_width=True)

        else:
            st.subheader("Raw JSON Data")
            st.json(st.session_state.timetable_data)

with tab5:
    st.header("⚙️ Settings & Export")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("📄 Export Options")

        if st.session_state.timetable_data:
            if st.button("📥 Export to PDF", key="export_pdf"):
                try:
                    with st.spinner("Generating PDF..."):
                        export_timetable_to_pdf("timetable.json", "timetable.pdf")

                    with open("timetable.pdf", "rb") as pdf_file:
                        st.download_button(
                            label="Download PDF",
                            data=pdf_file,
                            file_name="timetable.pdf",
                            mime="application/pdf"
                        )
                    st.success("✅ PDF generated successfully!")
                except Exception as e:
                    st.error(f"Error generating PDF: {str(e)}")

    with col2:
        st.subheader("📧 Email Reminders")

        if os.getenv("GMAIL_ID") and os.getenv("GMAIL_PASSWORD"):
            recipient_email = st.text_input(
                "Enter email to receive reminders:",
                value=os.getenv("GMAIL_ID", ""),
                help="Leave blank to send to your Gmail ID"
            )

            if st.button("📤 Send Today's Plan via Email", key="send_email"):
                if not recipient_email:
                    st.error("❌ Please enter an email address")
                else:
                    with st.spinner("Sending email..."):
                        try:
                            send_reminder_email(recipient_email)
                            st.success("✅ Email sent successfully! Check your inbox.")
                        except Exception as e:
                            st.error(f"Error sending email: {str(e)}")
        else:
            st.warning("⚠️ Gmail credentials not configured. Add GMAIL_ID and GMAIL_PASSWORD to .env file.")

    st.divider()

    st.subheader("📋 File Management")

    col1, col2, col3 = st.columns(3)

    with col1:
        if os.path.exists("syllabus.json"):
            with open("syllabus.json", "r") as f:
                st.download_button(
                    label="Download Syllabus",
                    data=f.read(),
                    file_name="syllabus.json",
                    mime="application/json"
                )

    with col2:
        if os.path.exists("timetable.json"):
            with open("timetable.json", "r") as f:
                st.download_button(
                    label="Download Timetable",
                    data=f.read(),
                    file_name="timetable.json",
                    mime="application/json"
                )

    with col3:
        if os.path.exists("timetable.pdf"):
            with open("timetable.pdf", "rb") as f:
                st.download_button(
                    label="Download PDF",
                    data=f.read(),
                    file_name="timetable.pdf",
                    mime="application/pdf"
                )

    st.divider()

    st.subheader("ℹ️ About StudyPilot")
    st.markdown("""
    **StudyPilot** is an AI-powered study scheduler that helps students create personalized study timetables.

    **Features:**
    - 🤖 AI-powered syllabus extraction from PDFs
    - ⏱️ Smart time allocation based on exam dates and weightage
    - 📅 Intelligent timetable generation
    - 📊 Weekly study plans with daily breakdowns
    - 📄 PDF export for offline access
    - 📧 Email reminders for daily plans

    **How it works:**
    1. Upload your syllabus PDF
    2. Set your daily study hours
    3. Let AI allocate time based on priorities
    4. Generate a personalized timetable
    5. Export and track your progress

    ---
    **Version:** 1.0 | **Powered by Streamlit & Groq AI**
    """)
