# 🛡️ BillGuard

**AI-powered billing scam detector for Indian consumers.**

BillGuard analyzes hospital bills, restaurant bills, and food-delivery platform invoices to surface illegal charges, GST miscalculations, and MRP violations — with exact rupee amounts and the specific law being broken.

Built for the [AIVENTRA Hackathon 2026](https://aiventra.devpost.com/).

---

## ✨ Features

| Feature | Detail |
|---|---|
| **Image + text analysis** | Upload a photo of any bill or paste the text |
| **Camera capture** | Live camera with real-time blur/brightness quality checks |
| **Three bill types** | 🏥 Hospital · 🍽️ Restaurant · 📱 Online Order (Swiggy / Zomato / Dineout) |
| **Precise overcharge math** | Server-side recalculation — never trusts Gemini's arithmetic |
| **Legal citations** | Every flag cites the exact Indian law (CCPA 2022, GST Act, Legal Metrology, NPPA, IRDAI) |
| **Scam Map** | Interactive India map showing flagged businesses crowd-sourced from all reports |
| **Auto-geocoding** | Extracts business address from the bill and pins it on the map automatically |
| **Smart fallback geocoder** | Handles garbled OCR output like `PERUNGUDICHENNAI` → `PERUNGUDI, Chennai` |
| **Model fallback chain** | Tries 4 Gemini models in order so a quota hit on one doesn't break the app |

---

## 🏗️ Architecture

```
billguard/
├── main.py              # FastAPI app — all HTTP endpoints
├── analyzer.py          # Gemini Vision API integration + image preprocessing
├── database.py          # SQLite schema, queries, risk-scoring algorithm
├── geocoder.py          # Nominatim geocoding with smart address fallback
├── rules/
│   ├── hospital.py      # Hospital billing rules (NPPA, IRDAI, TPA documents)
│   ├── restaurant.py    # Restaurant rules (CCPA 2022 service charge, 5% GST, MRP)
│   └── online_order.py  # Platform rules (18% GST on fees, discount handling)
└── static/
    ├── index.html        # Single-page bill analyzer UI
    ├── map.html          # Interactive scam map (Leaflet.js)
    └── camera.js         # Live camera capture with quality detection
```

**Stack:** Python 3.11 · FastAPI · SQLite · Google Gemini Vision (`google-genai`) · Pillow · Leaflet.js · OpenStreetMap Nominatim · Tailwind CSS (CDN)

No frontend build step — pure HTML + vanilla JS.

---

## 🚀 Quick Start

### 1. Clone the repo

```bash
git clone https://github.com/your-username/billguard.git
cd billguard
```

### 2. Create a virtual environment

```bash
python -m venv venv
# Windows
venv\Scripts\activate
# macOS / Linux
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Get a Gemini API key

1. Go to [Google AI Studio](https://aistudio.google.com/app/apikey)
2. Click **Create API key** → create it in a **new Google Cloud project** (fresh projects have higher free-tier quotas)
3. Copy the key

### 5. Configure environment variables

```bash
cp .env.example .env
```

Edit `.env`:

```
GEMINI_API_KEY=your_key_here
```

### 6. Run

```bash
python main.py
```

Open **http://localhost:8000** in your browser.

---

## 🔍 How It Works

1. **Upload or capture** a bill image (or paste text).
2. **Select bill type** — Hospital, Restaurant, or Online Order.
3. BillGuard **preprocesses** the image (contrast boost, sharpness, unsharp mask) then sends it to **Gemini Vision** with a detailed Indian-law prompt.
4. Gemini returns structured JSON. The server **recalculates overcharge totals** from the flags array rather than trusting the model's arithmetic.
5. The UI shows a **risk report** — each flag has the item name, billed vs. fair amount, severity (red/yellow/green), the law violated, and what the customer should do.
6. If Gemini detects a business name and address, the report is **automatically geocoded** and pinned to the **Scam Map**.

### Overcharge recalculation logic

```python
# Server always recomputes estimated_overcharge
ILLEGAL_ZERO_FAIR = {"service charge", "staff welfare", "server charge", "cover charge"}
total_overcharge = sum(
    max(0, billed - fair)
    for flag in flags
    if billed is not None and fair is not None
)
```

### Model fallback chain

```python
MODELS = [
    "gemini-2.5-flash-lite",   # cheapest / fastest — try first
    "gemini-2.5-flash",
    "gemini-2.0-flash",
    "gemini-2.0-flash-lite",   # last resort
]
```

If one model returns 503 (busy) or 429 (quota), the next model is tried automatically.

---

## 🗺️ Scam Map

The map at `/map` shows every business that has been reported via BillGuard:

- **Red pin** = frequently flagged, high overcharges
- **Orange pin** = moderate risk
- **Green pin** = minor or isolated issues
- Clusters collapse and expand as you zoom
- Click a pin to see: total reports, average overcharge, issue breakdown, and a scrollable history of individual bills
- Filter by bill type (hospital / restaurant / online order)

Risk color is computed server-side from three weighted signals:

| Signal | Weight |
|---|---|
| Report frequency (capped at 10) | 40 pts |
| Average overcharge severity | 30 pts |
| Percentage of high-risk reports | 30 pts |

Score ≥ 55 → red · Score ≥ 25 → orange · otherwise → green

---

## 📋 Checks Performed

### Restaurant bills
- Illegal service charge (CCPA 2022 — flat banned in India)
- GST rate must be exactly 5% for restaurants
- GST must be calculated on food subtotal only, not on service charge
- Soft drink MRP violations (e.g., Coke 330 ml billed at ₹80 when MRP ≤ ₹50)
- Math accuracy (subtotal + taxes ≠ grand total)
- Gas / fuel surcharges (illegal to pass to customer)

### Hospital bills
- Drug pricing above NPPA ceiling (National List of Essential Medicines)
- Consumables above MRP (Legal Metrology Act)
- Duplicate charges for procedures included in packages
- TPA / insurance settlement documents: only flags "Do not collect from patient" or "Inclusive of package" disallowances — does NOT flag legitimate patient out-of-pocket items
- Undisclosed charges not in original estimate (Clinical Establishments Act)

### Online Order bills (Swiggy / Zomato / Dineout)
- Negative line items (discounts) are never flagged as violations
- Platform convenience fee GST at 18% is correct — not flagged
- Cover charge shown as negative = waived (benefit, not violation)
- Restaurant GST still checked at 5% on food items
- MRP violations on packaged goods

---

## 🔒 Security Notes

- **Never commit `.env`** — it is listed in `.gitignore`
- The `.env.example` file contains only a placeholder key — safe to commit
- `billguard.db` (SQLite) is also gitignored — it may contain user-submitted bill data
- The Gemini API key is loaded exclusively via `python-dotenv` at runtime
- No user data is sent anywhere except the Gemini API for analysis

---

## 🤝 Contributing

Pull requests are welcome. For major changes please open an issue first.

1. Fork the repo
2. Create a feature branch: `git checkout -b feature/my-improvement`
3. Commit your changes: `git commit -m "Add my improvement"`
4. Push: `git push origin feature/my-improvement`
5. Open a pull request

---

## 📜 Legal Disclaimer

BillGuard flags potential violations based on published Indian consumer protection laws. It is an educational tool and does not constitute legal advice. Always verify findings with a qualified professional before taking legal action.

---

## 🪪 License

[MIT](LICENSE)
