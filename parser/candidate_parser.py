import json
import os
import re

from dotenv import load_dotenv

load_dotenv()

# Import shared groq client with fallback
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from agents.groq_client import groq_chat


def _build_prompt(text):
    return f"""You are a resume parser. Extract information from the resume below and return ONLY a valid JSON object.

CRITICAL RULES:
- Output NOTHING except the JSON object
- Do NOT add any explanation, markdown, or code blocks
- Do NOT wrap in ```json ... ```
- Start your response directly with {{ and end with }}

JSON Schema to fill:
{{
    "personal_info": {{
        "name": "",
        "email": "",
        "phone": "",
        "location": "",
        "linkedin": "",
        "github": "",
        "portfolio": ""
    }},
    "summary": "",
    "skills": [],
    "education": [],
    "experience": [],
    "projects": [],
    "certifications": [],
    "positions_of_responsibility": [],
    "achievements": [],
    "activities": [],
    "languages": [],
    "experience_years": 0
}}

Extract skills from: Skills section, Experience descriptions, Projects, Certifications, Summary.
Also infer skills from job titles and tasks (e.g. "Electrical Engineer" -> "Electrical Systems").

Resume:
{text}"""


def _extract_json(content: str):
    """Try multiple strategies to extract a JSON object from LLM output."""
    import re

    # Strip markdown code fences if present
    content = re.sub(r"```(?:json)?", "", content).strip()

    # Strategy 1: brace-depth counting
    start = content.find('{')
    if start != -1:
        depth = 0
        for i, ch in enumerate(content[start:], start):
            if ch == '{':
                depth += 1
            elif ch == '}':
                depth -= 1
                if depth == 0:
                    candidate = content[start:i + 1]
                    try:
                        return json.loads(candidate)
                    except json.JSONDecodeError:
                        break

    # Strategy 2: greedy regex
    match = re.search(r'\{.*\}', content, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass

    return None


def parse_resume(text):
    prompt = _build_prompt(text)

    last_error = None
    response = None
    content = groq_chat(
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
    )

    profile = _extract_json(content)
    if not profile:
        print(f"[candidate_parser] Full response that failed JSON parse:\n{content}")
        raise Exception(f"No JSON found in LLM response. Model returned: {content[:200]}")


    skills = set(str(s).strip() for s in profile.get("skills", []))

    # experience text se keywords add karo
    for exp in profile.get("experience", []):

        exp_text = str(exp).lower()

        if "electrical" in exp_text:
            skills.add("Electrical Systems")

        if "troubleshooting" in exp_text:
            skills.add("Troubleshooting")

        if "autocad" in exp_text:
            skills.add("AutoCAD")

        if "circuit" in exp_text:
            skills.add("Circuit Design")

        if "power system" in exp_text:
            skills.add("Power Systems")

        if "testing" in exp_text:
            skills.add("Testing")

        if "diagnostic" in exp_text:
            skills.add("Diagnostics")

    profile["skills"] = sorted(list(skills))

   
    print(profile["skills"])
    return profile
    # return json.loads(content)