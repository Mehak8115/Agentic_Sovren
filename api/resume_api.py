# resume_api
from fastapi import APIRouter, UploadFile, File
import os
from database.candidate_repository import save_candidate
from parser.resume_extractor import extract_resume_text
from parser.candidate_parser import parse_resume

router = APIRouter()

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@router.post(
    "/upload-resume",
    summary="Upload and Parse Resume",
    description="""
    Upload a candidate resume in PDF or DOCX format.

    The system:
    - Extracts resume text
    - Uses AI to parse candidate information
    - Stores the profile in MongoDB
    - Returns a candidate ID for future operations

    Use the returned candidate_id for:
    - Job Matching
    - Skill Gap Analysis
    - Candidate Ranking
    """
)
async def upload_resume(
    file: UploadFile = File(...)
):

    file_path = os.path.join(
        UPLOAD_DIR,
        file.filename
    )

    with open(file_path, "wb") as f:
        f.write(await file.read())

    text = extract_resume_text(file_path)

    profile = parse_resume(text)

    candidate_id = save_candidate(
    profile,
    file_path
)

    profile.pop("_id", None)

    # print(profile) 
    import json

    try:
        json.dumps(profile)
        print("PROFILE IS JSON SERIALIZABLE")
    except Exception as e:
        print("JSON ERROR:", e)

    return {
        "candidate_id": candidate_id,
        "profile": profile
    }


#     print(type(profile))
#     print(profile)

#     return {
#     "candidate_id": candidate_id,
#     "name": profile.get("personal_info", {}).get("name")
# }

    