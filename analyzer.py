import asyncio
import base64
import io
import json
import os
import re

import PIL.Image
from PIL import ImageEnhance, ImageFilter
from dotenv import load_dotenv
from google import genai

from rules.hospital import HOSPITAL_RULES
from rules.restaurant import RESTAURANT_RULES
from rules.online_order import ONLINE_ORDER_RULES

load_dotenv()
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
MODELS = ["gemini-2.5-flash-lite", "gemini-2.5-flash", "gemini-2.0-flash", "gemini-2.0-flash-lite"]


def preprocess_image(img: PIL.Image.Image) -> PIL.Image.Image:
    # Ensure RGB
    if img.mode != "RGB":
        img = img.convert("RGB")

    # Resize: cap longest side at 1920px to avoid token bloat
    max_dim = 1920
    w, h = img.size
    if max(w, h) > max_dim:
        ratio = max_dim / max(w, h)
        img = img.resize((int(w * ratio), int(h * ratio)), PIL.Image.LANCZOS)

    # Contrast boost — makes text pop against background
    img = ImageEnhance.Contrast(img).enhance(1.6)

    # Sharpness boost — reduces blur artifacts
    img = ImageEnhance.Sharpness(img).enhance(2.5)

    # Unsharp mask — final edge crisp-up
    img = img.filter(ImageFilter.UnsharpMask(radius=1.5, percent=120, threshold=2))

    return img

PROMPT_TEMPLATE = """You are BillGuard, an expert Indian consumer rights auditor specializing in billing fraud detection.

STEP 1 — READ THE BILL: If this is an image, carefully read EVERY line of text visible: restaurant name, each item, each charge, each tax line, and the final total. Extract all numbers exactly as printed.

STEP 2 — APPLY THESE RULES:
{rules}

STEP 3 — FLAG ALL VIOLATIONS: Check every single charge against the rules above. Do NOT skip service charge, GST calculation, or math accuracy. Be aggressive — if something looks wrong, flag it.

CRITICAL CHECKS YOU MUST ALWAYS DO:
1. Is there a service charge? → ALWAYS flag as red (illegal under CCPA 2022)
2. What is the GST rate? → Must be exactly 5% for restaurants. Flag if higher.
3. Is GST calculated on food subtotal only, or on subtotal+service charge? → If on subtotal+service charge, flag as red
4. Does subtotal + all charges = grand total? → Flag any math discrepancy
5. Are any soft drinks / beverages on the bill? → Check if billed price exceeds MRP. Coke/Pepsi/Diet Coke/Sprite 330ml MRP ≈ ₹40–50. If billed at ₹80+ flag as red MRP violation with overcharge = billed – ₹40.
6. If this is a TPA/insurance document with a "not covered" or "disallowed" column → ONLY flag as overcharge if the remarks say "Do not collect from patient" or "Inclusive of package". fair_amount = claimed - disallowed_with_that_remark. Items without that remark are patient's out-of-pocket responsibility — do NOT flag them.

Return ONLY raw JSON, no markdown, no explanation outside JSON:

{{
  "bill_type": "{bill_type}",
  "business_name_detected": "<exact business/restaurant/hospital name from bill header — null if not visible>",
  "business_address_detected": "<complete address from bill including city/area/pincode — null if not visible>",
  "extraction_confidence": "<high = both name and address clearly printed | medium = name found but address partial | low = neither clearly readable>",
  "total_amount_detected": <grand total number or null>,
  "estimated_overcharge": <sum of (billed_amount - fair_amount) for every flagged item where billed > fair. Example: illegal service charge ₹80 + extra GST ₹4.02 = 84.02. Never use the full GST amount — only the EXCESS above what's legally correct. 0 if no overcharge>,
  "risk_level": "high",
  "summary": "<2-3 sentences: name each violation with exact rupee amounts, then state the total overcharge as the sum of all illegal charges + excess taxes>",
  "flags": [
    {{
      "item": "<exact charge name from the bill>",
      "billed_amount": <number — never null if you can read the bill>,
      "fair_amount": <what it should legally be — ALWAYS a number, never null. For illegal charges like service charge use 0. For overcharged items use the correct legal amount>,
      "severity": "red",
      "issue": "<specific problem — include actual numbers>",
      "legal_basis": "<exact Indian law or rule violated>",
      "action": "<exact action the customer should take>"
    }}
  ],
  "your_rights": ["<specific right 1>", "<specific right 2>", "<specific right 3>"],
  "next_steps": ["<step 1>", "<step 2>", "<step 3>"],
  "helpline": "<helpline name and number>"
}}

risk_level rules: "high" = any red flag OR overcharge >₹100 | "medium" = yellow flags only | "low" = minor issues | "clean" = zero issues
severity rules: "red" = illegal | "yellow" = suspicious | "green" = acceptable but worth noting
Only return "clean" with empty flags if there are TRULY zero issues after checking all rules above."""


async def analyze_bill(bill_type: str, image_data: str = None, bill_text: str = None):
    if bill_type == "hospital":
        rules = HOSPITAL_RULES
    elif bill_type == "online_order":
        rules = ONLINE_ORDER_RULES
    else:
        rules = RESTAURANT_RULES
    prompt = PROMPT_TEMPLATE.format(rules=rules, bill_type=bill_type)

    # Preprocess image once before retries
    pil_image = None
    if image_data:
        image_bytes = base64.b64decode(image_data)
        pil_image = preprocess_image(PIL.Image.open(io.BytesIO(image_bytes)))

    last_error = None
    for model in MODELS:
        for attempt in range(2):
            try:
                # response_mime_type="application/json" breaks multimodal (vision) inputs
                # so we only set temperature=0 for determinism
                gen_config = genai.types.GenerateContentConfig(temperature=0)
                if pil_image:
                    response = client.models.generate_content(
                        model=model,
                        contents=[prompt, pil_image],
                        config=gen_config,
                    )
                else:
                    response = client.models.generate_content(
                        model=model,
                        contents=f"{prompt}\n\nBILL TEXT:\n{bill_text}",
                        config=gen_config,
                    )

                text = response.text.strip()
                text = re.sub(r"^```json\s*", "", text)
                text = re.sub(r"\s*```$", "", text)

                match = re.search(r"\{.*\}", text, re.DOTALL)
                if match:
                    result = json.loads(match.group())
                    # Recompute estimated_overcharge from flags — don't trust Gemini's math
                    ILLEGAL_ZERO_FAIR = {"service charge", "staff welfare", "server charge", "cover charge"}
                    total_overcharge = 0.0
                    for flag in result.get("flags", []):
                        billed = flag.get("billed_amount")
                        fair = flag.get("fair_amount")
                        item_name = (flag.get("item") or "").lower()
                        # If fair_amount is missing but item is an illegal charge, fair = 0
                        if billed is not None and fair is None:
                            if any(k in item_name for k in ILLEGAL_ZERO_FAIR):
                                fair = 0
                                flag["fair_amount"] = 0
                        if billed is not None and fair is not None:
                            diff = float(billed) - float(fair)
                            if diff > 0:
                                total_overcharge += diff
                    result["estimated_overcharge"] = round(total_overcharge, 2)
                    return result

                return {"error": "Could not parse AI response.", "raw": text[:500]}

            except Exception as e:
                last_error = str(e)
                print(f"[ERROR] model={model} attempt={attempt} error={last_error[:200]}")
                is_busy   = "503" in last_error or "UNAVAILABLE" in last_error
                is_quota  = "429" in last_error or "RESOURCE_EXHAUSTED" in last_error
                is_expired= "key expired" in last_error.lower() or "api key expired" in last_error.lower()
                is_invalid= "400" in last_error and not is_expired
                if is_expired or is_invalid:
                    # No point trying other models — key itself is bad
                    print(f"[ERROR] API key issue — aborting all models")
                    return {"error": "API key expired or invalid. Please create a new key at aistudio.google.com and update your .env file."}
                if is_busy and attempt == 0:
                    await asyncio.sleep(4)
                    continue
                if is_quota and attempt == 0:
                    await asyncio.sleep(6)
                    break
                if is_busy or is_quota:
                    break  # try next model
                break  # non-retryable error

    print(f"[ERROR] All models failed. Last error: {last_error}")
    # Give a specific message based on the last error type
    if last_error and ("429" in last_error or "RESOURCE_EXHAUSTED" in last_error):
        return {"error": "Daily API quota exhausted. Please wait until midnight (IST) for reset, or create a new API key at aistudio.google.com."}
    return {"error": "Gemini is busy right now — please try again in a few seconds."}
