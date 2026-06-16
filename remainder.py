import json
import sys
import smtplib
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv
import os

if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

load_dotenv()

def get_today_plan(timetable_file="timetable.json"):
    with open(timetable_file, "r") as f:
        data = json.load(f)

    timetable = data["timetable"]
    today = datetime.now().date()

    for day_data in timetable:
        day_date = datetime.strptime(day_data["date"], "%Y-%m-%d").date()
        if day_date == today:
            return day_data

    return timetable[0]

def calculate_days_to_exam(exam_date_str):
    exam_date = datetime.strptime(exam_date_str, "%Y-%m-%d").date()
    today = datetime.now().date()
    days = (exam_date - today).days
    return max(0, days)

def build_email_body(day_data, days_to_exam):
    subject = f"Today's Study Plan - Day {day_data['day']}"

    body = "Good morning! Here's your plan for today:\n\n"

    for slot in day_data["slots"]:
        duration = slot["duration_minutes"]
        subject_name = slot["subject"]
        chapters = ", ".join(slot["chapters_to_cover"])

        body += f"[{duration} min] {subject_name}\n"
        body += f"Chapters: {chapters}\n\n"

    body += f"EXAM in {days_to_exam} days - stay focused!\n\n"
    body += "---\n"
    body += "StudyPilot | AI-Powered Study Scheduler"

    return subject, body

def send_reminder_email(recipient_email=None):
    gmail_id = os.getenv("GMAIL_ID")
    gmail_password = os.getenv("GMAIL_PASSWORD")

    if not gmail_id or not gmail_password:
        print("[ERROR] Gmail credentials not found in .env")
        return

    if not recipient_email:
        recipient_email = gmail_id

    try:
        with open("timetable.json", "r") as f:
            data = json.load(f)

        exam_date = data["timetable"][-1]["date"]
        days_to_exam = calculate_days_to_exam(exam_date)

        today_plan = get_today_plan()
        subject, body = build_email_body(today_plan, days_to_exam)

        message = MIMEMultipart()
        message["From"] = gmail_id
        message["To"] = recipient_email
        message["Subject"] = subject

        message.attach(MIMEText(body, "plain"))

        server = smtplib.SMTP_SSL("smtp.gmail.com", 465)
        server.login(gmail_id, gmail_password)
        server.sendmail(gmail_id, recipient_email, message.as_string())
        server.quit()

        print("[SUCCESS] Email sent! Check your inbox - today's plan is waiting.")

    except Exception as e:
        print(f"[ERROR] Error sending email: {e}")

if __name__ == "__main__":
    send_reminder_email()
