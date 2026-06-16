import pdfplumber
import os
import json
from groq import Groq
from dotenv import load_dotenv


# Step 1: Read PDF and convert to text
def extract_text_from_pdf(pdf_path):
    text = ""

    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()

            if page_text:
                text += page_text + "\n"

    return text


# Load API key
load_dotenv()

client = Groq(
    api_key=os.getenv("GROQ_API_KEY")
)


def extract_syllabus_data(text):

    prompt = f"""
You are a structured data explorer.

Extract only syllabus units.
Each unit should become one JSON object.

Do NOT create a separate object for the list of all units.
Do NOT treat unit names as chapters.
The chapters field should contain only the topics listed under that unit.

Return ONLY valid JSON.

Schema:

[
  {{
    "subject": "string",
    "unit": "string",
    "chapters": ["string"],
    "exam_date": "YYYY-MM-DD or null",
    "weightage": "percentage or null"
  }}
]

Syllabus text:

{text}
"""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ],
        temperature=0.1,
        max_tokens=4000
    )

    return response.choices[0].message.content

def clean_json_response(raw):
    start = raw.find("[")
    end = raw.rfind("]")

    if start == -1 or end == -1:
        raise ValueError("No JSON found")

    return raw[start:end + 1]

def main():

    print("Reading PDF...")
    text = extract_text_from_pdf("Syllabus.pdf")

    print("Sending to AI model...")
    raw_output = extract_syllabus_data(text)

    print("Cleaning JSON response...")
    cleaned = clean_json_response(raw_output)

    print("Parsing JSON...")
    data = json.loads(cleaned)
    
    print("Saving syllabus.json...")
    with open("syllabus.json", "w", encoding="utf-8") as file:
        json.dump(
            data,
            file,
            indent=4,
            ensure_ascii=False
        )

    print("Done! syllabus.json created successfully.")


# if __name__ == "__main__":
#     main()