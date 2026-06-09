# crew.py

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from api.resume_api    import router as resume_router
from api.matching_api  import router as matching_router
from api.skill_gap_api import router as skill_gap_router
from api.apply_api     import router as apply_router
from api.agent_api     import router as agent_router
from api.booking_api   import router as booking_router
from api.hr_api        import router as hr_router

print("ALL IMPORTS DONE")

app = FastAPI(title="Sovren")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── API routes ──────────────────────────────────────────────────────────
app.include_router(resume_router)
app.include_router(matching_router)
app.include_router(skill_gap_router)
app.include_router(apply_router,   tags=["Apply For Job"])
app.include_router(agent_router,   tags=["Agentic AI Agents"])
app.include_router(booking_router, tags=["Booking Agent"])
app.include_router(hr_router,      tags=["HR Agent"])

# ── Frontend ──────────────────────────────────────────────────────────────────
@app.get("/app", include_in_schema=False)
def frontend():
    return FileResponse("frontend/index.html")

# Static files (CSS, JS)
app.mount("/static", StaticFiles(directory="frontend"), name="static")
