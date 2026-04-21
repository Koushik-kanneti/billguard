import base64
import json
import os

import uvicorn
from fastapi import FastAPI, File, Form, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from analyzer import analyze_bill
from database import get_business_reports, get_map_markers, get_stats, init_db, insert_report, search_businesses
from geocoder import geocode

app = FastAPI(title="BillGuard")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="static"), name="static")

# Initialise database on startup
init_db()


@app.get("/")
def root():
    return FileResponse("static/index.html")


@app.get("/map")
def map_page():
    return FileResponse("static/map.html")


@app.get("/health")
def health():
    key = os.getenv("GEMINI_API_KEY", "")
    return {
        "status": "ok",
        "api_key_set": bool(key),
        "api_key_prefix": key[:6] if key else "none",
    }


# ── Bill analysis ────────────────────────────────────────────────────────────

@app.post("/analyze")
async def analyze(
    bill_type: str = Form(...),
    image: UploadFile = File(None),
    image_base64: str = Form(None),
    bill_text: str = Form(None),
):
    image_data = None
    if image and image.filename:
        contents = await image.read()
        image_data = base64.b64encode(contents).decode()
    elif image_base64:
        image_data = image_base64

    result = await analyze_bill(bill_type, image_data, bill_text)
    return JSONResponse(content=result)


# ── Scam map ─────────────────────────────────────────────────────────────────

@app.post("/report")
async def save_report(
    business_name: str = Form(...),
    address: str = Form(...),
    bill_type: str = Form(...),
    risk_level: str = Form("low"),
    estimated_overcharge: float = Form(0.0),
    issues: str = Form("[]"),
):
    lat, lng = await geocode(address)
    try:
        parsed_issues = json.loads(issues)
    except Exception:
        parsed_issues = []

    insert_report(
        business_name=business_name.strip(),
        address=address.strip(),
        lat=lat,
        lng=lng,
        bill_type=bill_type,
        risk_level=risk_level,
        estimated_overcharge=estimated_overcharge,
        issues=parsed_issues,
    )
    return JSONResponse({
        "success": True,
        "geocoded": lat is not None,
        "lat": lat,
        "lng": lng,
    })


@app.get("/map/markers")
def map_markers():
    return JSONResponse(get_map_markers())


@app.get("/map/search")
def map_search(q: str = ""):
    return JSONResponse(search_businesses(q))


@app.get("/map/business")
def map_business(name: str = ""):
    if not name.strip():
        return JSONResponse([])
    return JSONResponse(get_business_reports(name))


@app.get("/map/stats")
def map_stats():
    return JSONResponse(get_stats())


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
