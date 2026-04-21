ONLINE_ORDER_RULES = """
INDIAN ONLINE FOOD ORDERING PLATFORM RULES (Swiggy / Zomato / Dineout / EatSure etc.)

CRITICAL READING RULES — READ BEFORE ANALYZING:
- Negative values (shown with minus sign like -₹188, -₹26, -₹20) are DISCOUNTS. Do NOT flag them as charges.
- Green colored items in Dineout/Swiggy bills are usually discounts or savings. Do NOT flag as violations.
- "Cover Charge -₹X" = restaurant waived cover charge. This is a BENEFIT to the customer.
- "DineCash -₹X" or "Swiggy Money -₹X" = loyalty credits redeemed. BENEFIT to customer.
- "Deal Discount" or "Coupon Discount" = promotional discount. BENEFIT to customer.

1. CONVENIENCE FEE / PLATFORM FEE:
   - Platforms (Swiggy, Zomato, Dineout) are legally allowed to charge a convenience or platform fee.
   - This fee must be disclosed before final checkout — cannot be added as surprise.
   - GST on convenience/platform fee is 18% (it is a digital service, not food).
     Correct calculation: 18% of convenience fee amount.
   - DO NOT flag 18% GST on convenience fee — it is CORRECT.
   - Only flag if GST rate is ABOVE 18% or if the fee was not disclosed.

2. DELIVERY CHARGES:
   - Allowed and legal. Must be shown upfront before order confirmation.
   - Cannot be changed after order is placed.
   - GST on delivery: 18% (logistics service).
   - Only flag if delivery charge changed after order, or if undisclosed.

3. PACKAGING CHARGES:
   - Allowed. Must be itemized.
   - Only flag if packaging is charged above reasonable amount (>₹50 for a normal order) or hidden.

4. GST ON FOOD ITEMS:
   - 5% GST on food items from restaurant (same as dine-in).
   - If the bill shows separate restaurant bill total, 5% applies to that.

5. COVER CHARGE:
   - A restaurant CANNOT charge a cover charge without clearly disclosing it before seating/ordering.
   - On Dineout: If "Cover Charge" appears as a NEGATIVE value, it means the platform got it WAIVED — this is a benefit.
   - Only flag if cover charge is a POSITIVE charge that was not disclosed upfront.

6. SURGE / WEATHER / DEMAND SURCHARGE:
   - Must be clearly disclosed before order placement.
   - Cannot be added after order is placed.

7. COMMON SCAMS TO FLAG:
   - Convenience fee charged at a higher rate than shown at checkout.
   - GST on food items above 5%.
   - Undisclosed charges appearing only on final receipt.
   - Items billed that were not ordered or were cancelled.
   - Discount not applied even though coupon was shown as valid.
   - Delivery charge higher than what was shown before order confirmation.
   - Platform fee + convenience fee both charged (double platform charging).

8. LEGITIMATE CHARGES (DO NOT FLAG):
   - Convenience fee (any reasonable amount, disclosed upfront).
   - 18% GST on convenience/platform/delivery fee.
   - 5% GST on food subtotal.
   - Delivery fee (disclosed upfront).
   - Packaging fee (disclosed upfront).
   - Any negative/minus values — these are discounts, not charges.

9. CONSUMER RIGHTS FOR PLATFORM ORDERS:
   - Right to cancel within the cancellation window for full refund.
   - Right to refund if food is not delivered.
   - Right to complain if food quality is wrong.
   - FSSAI regulations apply to food quality.
   - File complaint: consumerhelpline.gov.in or call 1800-11-4000.
   - Platform grievance: each platform has an in-app grievance mechanism (mandatory by IT Rules 2021).
"""
