# 🚢 Sovren — Maritime Crew AI Platform

An agentic AI platform for the Indian maritime industry that automates crew hiring, job matching, skill gap analysis, and boat booking using LLM-powered agents.

---

## Problem Statement

The Indian maritime industry employs hundreds of thousands of seafarers — Captains, Engineers, Deckhands, Medics, Stewards, and more. Despite this scale, the hiring process remains largely manual and inefficient:

- **Crew members** struggle to find relevant openings that match their certifications and experience, often applying blindly to roles they are unqualified for.
- **HR managers** spend hours manually screening resumes, checking STCW certifications, calculating skill-fit, and shortlisting candidates — work that is repetitive and error-prone.
- **Boat operators** have no intelligent system to match passengers with vessels based on route, capacity, budget, and availability.
- **Skill gaps** go unaddressed because candidates have no visibility into what they are missing for specific roles.

**Sovren** solves all of this with a multi-agent AI system. Upload a resume, ask a question — the agents handle the rest.

---

## Features

### 🧑‍✈️ Crew Career Agent
- Upload a resume (PDF or DOCX) and ask natural language queries like *"What jobs am I eligible for?"* or *"What skills am I missing?"*
- LLM parses the resume and extracts skills, certifications, experience, and personal info
- Runs gap analysis against all available maritime jobs
- Returns ranked job matches with eligibility labels, skill match %, and actionable recommendations
- Suggests 5 follow-up career questions specific to the candidate

### 🧑‍💼 HR Agent
- Generate professional Job Descriptions for any maritime role with a single prompt
- Rank all candidates in the database against a specific job automatically
- Generate recruitment reports and interview summaries
- Publish or close job postings
- Full shortlisting with deduplication and eligibility scoring

### 🚤 Boat Booking Agent
- Search available boats by location, route, capacity, budget, and travel month
- Intelligent filters: availability check, price range, capacity matching, route matching
- Review sentiment analysis to score and rank boats
- Confirm bookings with payment processing and booking ID generation
- Remembers user preferences across sessions

### 📊 Skill Gap Analysis
- Detailed breakdown of matched vs. missing mandatory/optional skills per job
- Certification gap check
- Experience gap check
- Composite gap score (40% skills + 40% experience + 20% certifications)
- Priority learning recommendations for each missing skill and certification

### 📄 Resume Parsing
- Supports PDF and DOCX uploads
- LLM extracts: name, email, phone, location, summary, skills, education, experience, projects, certifications, achievements, languages, experience years
- Infers technical skills from job descriptions and project contexts
- Saves parsed candidate profiles to MongoDB

### 💼 Job Application
- Candidates can apply for specific jobs by candidate ID + job ID
- Duplicate application prevention
- Eligibility check runs automatically on apply
- Application status tracked in database

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend API | FastAPI |
| LLM Provider | Groq (llama-3.3-70b-versatile + fallbacks) |
| Database | MongoDB (local, `sovren` database) |
| Resume Parsing | PyPDF2, python-docx |
| Frontend | Vanilla HTML / CSS / JavaScript |
| Environment | Python 3.11+, python-dotenv |

---

## Project Structure

```
crew/
├── agents/
│   ├── groq_client.py          # Shared LLM client with model fallback
│   ├── supervisor_agent.py     # Routes requests to correct agent
│   ├── crew_agent.py           # Crew career matching agent
│   ├── crew_tools.py           # Tools used by crew agent
│   ├── hr_agent.py             # HR management agent
│   ├── hr_tools.py             # Tools used by HR agent
│   ├── booking_agent.py        # Boat booking agent
│   ├── booking_tools.py        # Tools used by booking agent
│   └── agent_engine.py         # Generic ReAct loop engine
│
├── api/
│   ├── agent_api.py            # /agent/run, /agent/run-with-resume
│   ├── hr_api.py               # /hr/* endpoints
│   ├── booking_api.py          # /booking/* endpoints
│   ├── apply_api.py            # /apply endpoints
│   ├── resume_api.py           # /resume/upload
│   ├── matching_api.py         # /match endpoints
│   └── skill_gap_api.py        # /skill-gap endpoints
│
├── database/
│   ├── mongodb.py              # MongoDB connection + collections
│   ├── candidate_repository.py
│   ├── available_job_repository.py
│   ├── hr_repository.py
│   ├── boat_repository.py
│   ├── job_repository.py
│   ├── seed_available_jobs.py  # Seeds 9 maritime jobs
│   ├── seed_boats.py           # Seeds 30+ boats across India
│   └── seed_jobs.py
│
├── parser/
│   ├── candidate_parser.py     # LLM resume parser
│   ├── resume_extractor.py     # PDF/DOCX text extractor
│   ├── pdf_parser.py
│   └── docx_parser.py
│
├── matching/
│   ├── job_matcher.py
│   ├── skill_similarity.py     # Fuzzy skill matching
│   ├── skill_utils.py
│   └── recommender.py
│
├── skill_gap/
│   ├── advanced_gap_analyzer.py  # Core gap scoring engine
│   ├── analyser.py
│   ├── role_analyzer.py
│   └── recommendation.py
│
├── application/
│   └── apply_matcher.py        # Job application logic
│
├── frontend/
│   ├── index.html              # Single-page UI
│   ├── app.js                  # Frontend logic
│   └── style.css
│
├── data/
│   └── user_memory.json        # Booking agent user memory
│
├── uploads/                    # Uploaded resume files
├── crew.py                     # FastAPI app entry point
├── .env                        # API keys
└── README.md
```

---

## Setup

### 1. Prerequisites
- Python 3.11+
- MongoDB running locally on port 27017
- Groq API key — get one free at [console.groq.com](https://console.groq.com)

### 2. Install dependencies

```bash
pip install fastapi uvicorn pymongo python-dotenv groq PyPDF2 python-docx pydantic
```

### 3. Configure environment

Create a `.env` file in the project root:

```env
GROQ_API_KEY=gsk_your_key_here
```

### 4. Seed the database

```bash
python database/seed_available_jobs.py
python database/seed_boats.py
```

### 5. Start the server

```bash
python -m uvicorn crew:app --reload
```

### 6. Open the frontend

Visit `http://localhost:8000/app`

---

## API Endpoints

### Crew Career Agent
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/agent/run-with-resume` | Upload resume + run agent |
| POST | `/agent/run` | Run agent with existing candidate ID |

### HR Agent
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/hr/generate-jd` | Generate job description |
| POST | `/hr/rank-candidates` | Rank all candidates for a job |
| POST | `/hr/recruitment-report` | Generate recruitment report |
| GET | `/hr/jobs` | List all HR jobs |

### Booking Agent
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/booking/run` | Run booking agent with natural language query |

### Applications
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/apply` | Apply for a job |
| GET | `/apply/{candidate_id}` | Get candidate's applications |
| GET | `/hr/applications/{job_id}` | Get all applications for a job |

### Resume & Matching
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/resume/upload` | Upload and parse resume |
| POST | `/match` | Match candidate to jobs |
| POST | `/skill-gap` | Run skill gap analysis |

---

## How the Gap Score Works

Each candidate-job pair gets a **gap score out of 100**:

```
Gap Score = (Skill Match % × 0.4) + (Cert Score × 0.2) + (Experience Score × 0.4)
```

| Score Range | Label |
|-------------|-------|
| 70 – 100 | Excellent match |
| 50 – 69 | Good match |
| 30 – 49 | Partial match |
| 0 – 29 | Not suitable |

Eligibility requires: missing mandatory skills ≤ 4 AND experience years ≥ minimum required.

---

## LLM Fallback Strategy

To handle Groq's free tier rate limits, all LLM calls go through `agents/groq_client.py` which automatically tries models in order:

1. `llama-3.3-70b-versatile` (primary)
2. `llama-3.1-8b-instant`
3. `gemma2-9b-it`
4. `mixtral-8x7b-32768`

If all models are rate-limited, the API returns HTTP 429 with a clear message.

---

## Database Collections (MongoDB — `sovren`)

| Collection | Contents |
|-----------|---------|
| `candidates` | Parsed resume profiles |
| `available_jobs` | Maritime job postings |
| `applications` | Job applications with gap scores |
| `hr_jobs` | HR-generated job descriptions |
| `boats` | Boat listings across India |
| `bookings` | Confirmed boat bookings |
| `users` | Booking agent user memory |

---

## Available Maritime Jobs (Seeded)

- Senior Captain — Mumbai Ferry Routes
- Captain — Chennai Port Operations
- Junior Captain — Goa Cruises
- Marine Navigator — Kochi
- Chief Marine Engineer — Mumbai
- Marine Maintenance Engineer — Kochi
- Offshore Medical Officer — Mumbai
- Deckhand — Cargo Vessel, Chennai
- Cruise Steward — Goa

---

## Available Boat Fleet (Seeded)

30+ boats across Mumbai, Goa, Kochi, Alleppey, Chennai, Kolkata, Visakhapatnam, Mangalore, Port Blair, and Lakshadweep — covering cargo, cruise, ferry, yacht, and houseboat types with price ranges from ₹6,000 to ₹45,000/day.
