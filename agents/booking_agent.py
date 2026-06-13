# Booking_agent

import json
import re
from agents.groq_client import groq_chat
from dotenv import load_dotenv
from agents.booking_tools import (
    tool_extract_requirements, tool_validate_date, tool_search_boats,
    tool_location_route_matching, tool_capacity_matching, tool_availability_check,
    tool_price_range_filter, tool_review_sentiment_analysis,
    tool_activity_recommendation, tool_booking_assistance,
    tool_payment_processing, tool_booking_confirmation,
)
from database.boat_repository import get_or_create_user, update_user_preference

load_dotenv()
_MODEL = "llama-3.3-70b-versatile"  # kept for reference only, groq_chat handles fallback


class BookingAgent:

    def run(self, query, user_name="Guest", confirm_booking_override=None,
            payment_method_override=None, include_thought_process=False):
        self.memory = []

        intent    = self._intent(query)
        req       = tool_extract_requirements(query)

        # Guard: check if query is related to maritime booking
        if not self._is_relevant(query):
            return {
                "agent": "Maritime Booking Agent",
                "intent": intent,
                "user_name": user_name,
                "query": query,
                "response": "I'm sorry, I don't have information about that. I can only help with maritime boat bookings, availability, pricing, and related queries.",
                "suggested_questions": [],
                "data": {"total_boats_found": 0, "top_recommendations": [], "booking": None},
            }
        sentiment = req.get("user_sentiment", "neutral")
        confirm   = confirm_booking_override if confirm_booking_override is not None else req.get("confirm_booking", False)
        payment   = payment_method_override  if payment_method_override  is not None else req.get("payment_method", "online")
        self.memory.append(f"[INTENT] {intent} | req={req}")

        date_ok = tool_validate_date(req.get("travel_month"))
        if not date_ok["valid"]:
            return {"agent":"Maritime Booking Agent","error":date_ok["error"],
                    "response":f"Sorry — {date_ok['error']}. Please choose a future date.",
                    "suggested_questions":["What dates are available?","Can I book for next month?",
                        "What is the earliest date?","Can I search without a date?","How far ahead can I book?"],
                    "data":{"total_boats_found":0,"top_recommendations":[],"booking":None}}

        user = get_or_create_user(user_name)
        if req.get("location") and not user.get("preferred_location"):
            update_user_preference(user["user_id"], req["location"])
            user["preferred_location"] = req["location"]

        boats = tool_search_boats()
        self.memory.append(f"[OBS] {len(boats)} boats in DB")

        # Filter by specific boat name if mentioned
        if req.get("boat_name"):
            name_lower = req["boat_name"].lower()
            named = [b for b in boats if name_lower in b.get("name", "").lower()]
            if named:
                boats = named
                self.memory.append(f"[OBS] {len(boats)} after boat name filter")

        if req.get("location") or req.get("route_from") or req.get("route_to"):
            f = tool_location_route_matching(boats, req.get("location"), req.get("route_from"), req.get("route_to"))
            # If location was specified but NO boats match — do NOT fall back to all boats
            boats = f
            self.memory.append(f"[OBS] {len(boats)} after location filter")

        if req.get("passengers"):
            boats = tool_capacity_matching(boats, req["passengers"])
            self.memory.append(f"[OBS] {len(boats)} after capacity")

        boats = tool_availability_check(boats, req.get("travel_month"))
        self.memory.append(f"[OBS] {len(boats)} after availability")

        pre_price_boats = list(boats)  # save before price filter
        boats = tool_price_range_filter(boats, req.get("budget_min"), req.get("budget_max"))
        self.memory.append(f"[OBS] {len(boats)} after price filter")

        # If no results after price filter, try without it and note the difference
        if not boats and (req.get("budget_min") or req.get("budget_max")):
            boats_no_price = tool_price_range_filter(pre_price_boats, None, None)
            if boats_no_price:
                # Show what's available with a note
                boats = tool_review_sentiment_analysis(boats_no_price)
                top_boats = tool_activity_recommendation(boats, req)
                self.memory.append(f"[OBS] No boats in budget — showing {len(boats)} nearby boats")
                nl, qs = self._generate_over_budget_response(query, top_boats, req, user, sentiment)
                out = {
                    "agent":"Maritime Booking Agent","intent":intent,
                    "user_name":user["name"],"user_id":user["user_id"],
                    "query":query,"response":nl,"suggested_questions":qs,
                    "data":{
                        "total_boats_found":len(boats),
                        "top_recommendations":[
                            {"name":b["name"],"type":b["type"],"location":b.get("location"),
                             "route":b.get("route",[]),"capacity":b.get("capacity"),
                             "price_per_day":b.get("price_per_day"),"price_range":b.get("price_range"),
                             "rating":b.get("rating"),"review_score":b.get("review_score"),
                             "recommendation_score":b.get("recommendation_score"),
                             "booking_status":b.get("availability_status",b.get("booking_status","available")),
                             "availability":b.get("availability",[])[:4],
                             "amenities":b.get("amenities",[]),"crew":b.get("crew",[]),
                             "activities":b.get("activities",[]),"boat_id":b["_id"]}
                            for b in top_boats
                        ],"booking":None,
                    },
                }
                if include_thought_process:
                    out["thought_process"] = self.memory
                return out

        if not boats:
            loc = req.get("location") or "your location"
            COVERED_LOCATIONS = [
                "Mumbai", "Goa", "Kochi", "Alleppey", "Chennai",
                "Kolkata", "Visakhapatnam", "Mangalore", "Port Blair", "Lakshadweep"
            ]
            if req.get("location"):
                response = (
                    f"Unfortunately, our services do not cover **{loc}** at the moment.\n\n"
                    f"We currently operate in:\n"
                    + "  ".join(f"**{l}**" for l in COVERED_LOCATIONS)
                    + "\n\nWould you like me to show boats in any of these locations?"
                )
                qs = [f"Show boats in {l}" for l in COVERED_LOCATIONS[:5]]
            else:
                response = "No boats found matching your filters. Try adjusting your budget, travel date, or passenger count."
                qs = ["Try different location?", "Increase budget?", "Different month?", "Fewer passengers?", "Different boat type?"]

            return {
                "agent": "Maritime Booking Agent",
                "intent": intent,
                "user_name": user["name"],
                "query": query,
                "response": response,
                "suggested_questions": qs,
                "data": {"total_boats_found": 0, "top_recommendations": [], "booking": None}
            }

        # Detect if user wants worst/lowest rated boats
        sort_asc = any(w in query.lower() for w in [
            "worst", "lowest rated", "bad rating", "cheapest", "lowest price",
            "minimum", "least popular", "low rating"
        ])

        boats     = tool_review_sentiment_analysis(boats)
        top_boats = tool_activity_recommendation(boats, req)
        if sort_asc:
            # Re-sort ascending by recommendation_score for "worst" queries
            top_boats = sorted(boats, key=lambda b: b.get("recommendation_score", 0))[:5]
        self.memory.append(f"[OBS] Top: {top_boats[0]['name']} score={top_boats[0]['recommendation_score']}")

        booking_confirmation = None
        if intent == "book_boat" and confirm:
            summary              = tool_booking_assistance(top_boats[0], req, user)
            payment_result       = tool_payment_processing(summary, payment)
            booking_confirmation = tool_booking_confirmation(summary, payment_result, user)
            self.memory.append(f"[OBS] Confirmed: {booking_confirmation['booking_id']}")

        nl, qs = self._generate_response(query, top_boats, booking_confirmation, user, sentiment)
        self.memory.append("[DONE]")

        out = {
            "agent":"Maritime Booking Agent","intent":intent,
            "user_name":user["name"],"user_id":user["user_id"],
            "query":query,"response":nl,"suggested_questions":qs,
            "data":{
                "total_boats_found":len(boats),
                "top_recommendations":[
                    {"name":b["name"],"type":b["type"],"location":b.get("location"),
                     "route":b.get("route",[]),"capacity":b.get("capacity"),
                     "price_per_day":b.get("price_per_day"),"price_range":b.get("price_range"),
                     "rating":b.get("rating"),"review_score":b.get("review_score"),
                     "recommendation_score":b.get("recommendation_score"),
                     "booking_status":b.get("availability_status",b.get("booking_status","available")),
                     "availability":b.get("availability",[])[:4],
                     "amenities":b.get("amenities",[]),"crew":b.get("crew",[]),
                     "activities":b.get("activities",[]),"boat_id":b["_id"]}
                    for b in top_boats
                ],
                "booking":booking_confirmation,
            },
        }
        if include_thought_process:
            out["thought_process"] = self.memory
        return out


    def _is_relevant(self, query: str) -> bool:
        """Return False if query is clearly unrelated to maritime booking."""
        raw = groq_chat(
            messages=[{"role": "user", "content":
                f"""Is this query related to maritime boats, boat booking, boat rental, 
water travel, boat activities, boat pricing, or boat availability?
Query: "{query}"
Reply with ONLY: yes or no"""}],
            temperature=0,
        )
        return raw.lower().startswith("yes")

    def _intent(self, q):
        raw = groq_chat(
            messages=[{"role": "user", "content":
                f'Classify query into ONE of: search_boats|get_recommendation|book_boat|check_availability\nQuery:"{q}"\nReply ONLY the label.'}],
            temperature=0,
        ).lower()
        for l in ["search_boats", "get_recommendation", "book_boat", "check_availability"]:
            if l in raw:
                return l
        return "get_recommendation"

    def _generate_response(self, query, top_boats, booking_conf, user, sentiment):
        tones = {"positive":"Warm and enthusiastic.","neutral":"Clear and professional.",
                 "frustrated":"Brief and empathetic.","angry":"Very brief, acknowledge frustration."}
        tone = tones.get(sentiment, tones["neutral"])

        lines = []
        for b in top_boats:
            lines.append(
                f"• {b['name']} | Type: {b['type']} | Location: {b.get('location')} | "
                f"Price: Rs{b.get('price_per_day',0):,}/day | Rating: {b.get('rating')}/5 | "
                f"Capacity: {b.get('capacity')} people | "
                f"Status: {b.get('availability_status', b.get('booking_status','available'))} | "
                f"Crew: {', '.join(b.get('crew',[]))} | "
                f"Activities: {', '.join(b.get('activities',[]))}"
            )
        boats_block = "\n".join(lines)

        conf_block = ""
        if booking_conf:
            conf_block = (f"\nBOOKING CONFIRMED: ID={booking_conf['booking_id']} | "
                         f"Boat={booking_conf['boat_name']} | Date={booking_conf['travel_date']} | "
                         f"Txn={booking_conf['transaction_id']}")

        prompt = (
            f"Maritime booking assistant. Tone: {tone}\n"
            f"User {user['name']} asked: \"{query}\"\n\n"
            f"REAL boats from our database (use ONLY this data — do NOT invent anything):\n{boats_block}\n"
            f"{conf_block}\n"
            f"{'IMPORTANT: Booking NOT confirmed. Do NOT write BOOKING CONFIRMED or any booking ID. Do NOT mention transaction IDs.' if not booking_conf else ''}\n\n"
            f"Instructions:\n"
            f"- Greet {user['name']} by name (not 'Guest')\n"
            f"- Answer the user's SPECIFIC question using only the boat data above\n"
            f"- If they asked about one specific boat, focus only on that boat\n"
            f"- If they asked for suggestions, list boats as bullets: name, price in Rs, rating, status, crew, activities\n"
            f"- Use Rs (Indian Rupees) for ALL prices\n"
            f"{'- Show confirmation details' if booking_conf else '- Ask if they want to book'}\n\n"
            f"Then write EXACTLY this line:\n---QUESTIONS---\n"
            f"Then a JSON array of exactly 5 follow-up questions about these real boats:\n"
            f'["q1?","q2?","q3?","q4?","q5?"]'
        )
        return self._call_llm(prompt)

    def _call_llm(self, prompt):
        raw = groq_chat(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
        )
        return self._split(raw)

    def _generate_over_budget_response(self, query, top_boats, req, user, sentiment):
        tones = {"positive":"Warm.","neutral":"Helpful and honest.","frustrated":"Brief and empathetic.","angry":"Very brief."}
        tone = tones.get(sentiment, tones["neutral"])
        budget = f"Rs{req.get('budget_max'):,}" if req.get("budget_max") else "your budget"
        loc = req.get("location") or "this area"

        lines = [
            f"• {b['name']} ({b['type']}) — Rs{b.get('price_per_day',0):,}/day | "
            f"Rating: {b.get('rating')}/5 | {b.get('location')} | "
            f"Crew: {', '.join(b.get('crew',[]))} | Activities: {', '.join(b.get('activities',[]))}"
            for b in top_boats
        ]

        prompt = (
            f"You are a maritime booking assistant. Tone: {tone}\n"
            f"User {user['name']} asked: \"{query}\"\n\n"
            f"No boats in {loc} were found within {budget}. "
            f"But here are the closest available options from the same area:\n"
            + "\n".join(lines) +
            f"\n\nWrite a friendly, plain English response:\n"
            f"- Mention there are no boats within {budget} in {loc}\n"
            f"- But suggest these nearby options with their prices\n"
            f"- Do NOT use technical jargon like 'budget_max' or 'req'\n"
            f"- Be conversational and helpful\n"
            f"- Use Rs for prices\n\n"
            f"Then write:\n---QUESTIONS---\n"
            f'["q1?","q2?","q3?","q4?","q5?"]'
        )
        r = groq_chat(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
        )
        return self._split(r)

    def _split(self, raw):
        if "---QUESTIONS---" in raw:
            p  = raw.split("---QUESTIONS---", 1)
            nl = p[0].strip()
            qr = p[1].strip()
        else:
            nl = raw
            qr = "[]"

        # Strip any leaked booking confirmation block from the NL response
        nl = re.sub(
            r'BOOKING CONFIRMED:.*?(?=\n\n|\Z)',
            '', nl, flags=re.DOTALL | re.IGNORECASE
        ).strip()

        qs = []
        m = re.search(r"\[.*?\]", qr, re.DOTALL)
        if m:
            try:
                qs = [str(q).strip() for q in json.loads(m.group(0)) if str(q).strip()]
            except Exception:
                pass
        if not qs:
            qs = ["What activities are available?","Can I book for a specific date?",
                  "Are group discounts available?","What amenities are included?",
                  "How far ahead should I book?"]
        return nl, qs[:5]
