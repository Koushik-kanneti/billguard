HOSPITAL_RULES = """
INDIAN HOSPITAL BILLING RULES & CONSUMER RIGHTS:

1. DRUG PRICING — NPPA (National Pharmaceutical Pricing Authority):
   - All scheduled drugs have a government-fixed Maximum Retail Price (MRP).
   - Hospitals CANNOT charge above MRP for any medicine or consumable.
   - Common inflated items:
       * IV fluids / Ringer's Lactate: MRP ~₹60–80, often billed ₹200–400
       * Syringes (2ml/5ml): MRP ₹5–10, often billed ₹40–80
       * Surgical gloves (pair): MRP ₹15–30, often billed ₹100+
       * Surgical masks: MRP ₹2–5, often billed ₹30–50
       * IV cannula: MRP ₹20–40, often billed ₹150+

2. CLINICAL ESTABLISHMENTS ACT:
   - Hospitals must display rates for all services publicly.
   - Must provide a fully itemized bill on request — cannot refuse.
   - Cannot charge for services not rendered.

3. PACKAGE BILLING:
   - If patient opted for a package (e.g., delivery package, surgery package),
     hospitals CANNOT charge separately for items already included in the package.
   - Any deviation from the package must be consented to by the patient in writing.

4. COMMON SCAMS TO FLAG:
   - Charging for unused medicines or consumables returned in sealed condition.
   - Billing ICU charges when patient was in a general ward or HDU.
   - Duplicate charges — same item billed twice (e.g., two ECGs on same day).
   - Charging branded drug rate when generic equivalent was administered.
   - "Miscellaneous" or "sundries" charges without itemization (illegal).
   - Doctor visit charges for consultations that did not occur.
   - Inflated oxygen charges — O2 should not cost more than ₹100–200/day.
   - Nursing charges beyond standard rates.
   - Charging GST on hospital bills — healthcare services are GST-EXEMPT.
   - Charging for tests not performed or not prescribed.
   - Disposable charges above MRP.

5. TPA / INSURANCE SETTLEMENT DOCUMENTS — CRITICAL READING RULES:
   These documents have specific columns. Read them VERY carefully:

   COLUMN: "Expenses not covered as per policy / Terms and Conditions against Hospital Bill"
   → This is the amount the INSURANCE COMPANY is DISALLOWING.
   → If remarks say "Do not collect from patient" or "Inclusive of package" → the hospital CANNOT charge the patient this amount. Flag as RED overcharge = that full disallowed amount.
   → If no such remark → the patient may need to pay it out of pocket (insurance just won't cover it). Do NOT automatically flag.

   COLUMN: "Claimed Amount"
   → The total the hospital billed. This is the billed_amount.

   HOW TO CALCULATE fair_amount FOR TPA DOCUMENTS:
   - If "Do not collect from patient" remark exists: fair_amount = claimed_amount - disallowed_amount
   - If no such remark: fair_amount = claimed_amount (patient owes it, insurance just won't pay)

   EXAMPLE (correct interpretation):
   - Implant claimed ₹1,87,774 | Not covered ₹67,240 | Remark: "Do not collect from patient"
     → billed_amount = 187774, fair_amount = 120534, overcharge = 67240 ✓
   - Investigation claimed ₹8,107 | Not covered ₹8,107 | No "do not collect" remark
     → Patient pays ₹8,107 out of pocket. Do NOT flag as overcharge.

   HOSPITAL PACKAGE BILLING:
   - If an item is marked "Inclusive of package" and "Do not collect from patient" → the hospital has already been paid for this via the package. Charging again = double billing = RED flag.
   - Hospital cannot charge the patient amounts beyond what insurance covers without explicit prior written consent.
   - Pre-authorization approval amount is the ceiling — extras need fresh consent.

6. CONSUMER RIGHTS:
   - Demand itemized bill before payment — it is your legal right.
   - You can withhold payment for disputed items while paying undisputed ones.
   - File complaint: National Consumer Helpline — 1800-11-4000 (toll-free)
   - File online: consumerhelpline.gov.in
   - Approach: District Consumer Disputes Redressal Commission
   - For drug pricing violations: contact NPPA at 1800-111-255
"""
