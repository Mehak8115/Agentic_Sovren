# agents/booking_tools.py

import json
import re
from datetime import datetime, date

from agents.groq_client import groq_chat
from dotenv import load_dotenv
from database.boat_repository import (
    get_all_boats,
    save_booking,
    get_or_create_user,
    update_user_booking,
    update_user_preference,
)

load_dotenv()


# ── Tool 1: Extract requirements + sentiment

def tool_extract_requirements(query: str) -> dict:
    """
    LLM extracts structured booking requirements + user sentiment.
    Returns: boat_type, location, route_from, route_to, travel_date (YYYY-MM),
             passengers, budget_min, budget_max, preferences[], user_sentiment
    """
    prompt = f"""Extract maritime booking requirements and user sentiment from this query.
Return ONLY valid JSON:
{{
  "boat_type": "cargo|cruise|fishing|ferry|yacht|houseboat|any",
  "location": "preferred city/port or null",
  "boat_name": "specific boat name if mentioned, else null",
  "route_from": "departure port or null",
  "route_to": "destination port or null",
  "travel_month": "YYYY-MM (e.g. 2026-07) or null",
  "passengers": number or null,
  "budget_min": number or null,
  "budget_max": number or null,
  "preferences": ["luxury", "budget", "fast", etc],
  "user_sentiment": "positive|neutral|frustrated|angry",
  "confirm_booking": true if user explicitly says book/confirm/proceed/yes book it, else false,
  "payment_method": "upi|card|cash|online" based on query, default "online"
}}

Query: "{query}"

Return ONLY JSON."""

    raw = groq_chat(
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
    )
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except Exception:
            pass
    return {
        "boat_type": "any", "location": None, "route_from": None, "route_to": None,
        "travel_month": None, "passengers": None,
        "budget_min": None, "budget_max": None,
        "preferences": [],
        "user_sentiment": "neutral",
    }


# ── Tool 2: Validate date 

def tool_validate_date(travel_month: str | None) -> dict:
    """Check if travel_month is past/present/future. Reject past dates."""
    if not travel_month:
        return {"valid": True, "error": None}
    
    try:
        req_year, req_month = travel_month.split("-")
        req_year, req_month = int(req_year), int(req_month)
        now = date.today()
        
        if req_year < now.year or (req_year == now.year and req_month < now.month):
            return {
                "valid": False,
                "error": f"Travel date {travel_month} is in the past. Please choose a future date."
            }
        return {"valid": True, "error": None}
    except Exception:
        return {"valid": True, "error": None}


# ── Tool 3: Search boats 

def tool_search_boats() -> list[dict]:
    boats = get_all_boats()
    for b in boats:
        b["_id"] = str(b["_id"])
    return boats


# ── Tool 4: Location + route matching

# State/region → city aliases (user "Kerala" → matches "Kochi", "Alleppey" etc.)
_LOCATION_ALIASES = {
    "kerala":       ["kochi", "alleppey", "kumarakom", "alappuzha", "kozhikode", "thrissur", "vembanad"],
    "goa":          ["goa", "panaji", "anjuna", "baga", "margao"],
    "mumbai":       ["mumbai", "bombay", "alibaug", "mandwa"],
    "rajasthan":    ["jaipur", "udaipur", "jodhpur"],
    "andaman":      ["port blair", "havelock", "neil island", "rangat"],
    "lakshadweep":  ["kavaratti", "agatti", "bangaram"],
    "tamil nadu":   ["chennai", "pondicherry", "tuticorin", "rameswaram", "mahabalipuram"],
    "west bengal":  ["kolkata", "sundarbans", "sagar island", "haldia"],
    "karnataka":    ["mangalore", "udupi", "karwar", "malpe"],
    "andhra pradesh": ["visakhapatnam", "kakinada", "bheemili", "rushikonda"],
}

def _expand_location(location: str) -> list[str]:
    """Return list of city names that match a location/state query."""
    if not location:
        return []
    loc_lower = location.strip().lower()
    # Check if it's a state alias
    for state, cities in _LOCATION_ALIASES.items():
        if loc_lower == state or loc_lower in cities:
            return [loc_lower] + cities
    # Otherwise just use the location as-is
    return [loc_lower]


def tool_location_route_matching(
    boats: list[dict],
    location: str | None,
    route_from: str | None,
    route_to: str | None
) -> list[dict]:
    if not location and not route_from and not route_to:
        return boats

    location_terms = _expand_location(location) if location else []

    matched = []
    for boat in boats:
        boat_location = boat.get("location", "").lower()
        route         = [r.lower() for r in boat.get("route", [])]

        # Location match: ONLY against boat's home port (not route stops)
        # This prevents "Goa Cargo King" showing in Mumbai search just because
        # Mumbai appears in its route
        loc_match = not location or any(
            term == boat_location or term in boat_location
            for term in location_terms
        )

        # Route matching only when user explicitly specifies departure/destination
        from_ok = not route_from or any(route_from.lower() in r for r in route)
        to_ok   = not route_to   or any(route_to.lower()   in r for r in route)

        if loc_match and from_ok and to_ok:
            matched.append(boat)
    return matched


# ── Tool 5: Capacity matching

def tool_capacity_matching(boats: list[dict], passengers: int | None) -> list[dict]:
    if not passengers:
        return boats
    return [b for b in boats if b.get("capacity", 0) >= passengers]


# ── Tool 6: Availability check (month-based)

def tool_availability_check(boats: list[dict], travel_month: str | None) -> list[dict]:
    if not travel_month:
        for b in boats:
            b["availability_status"] = b.get("booking_status", "available")
        return boats
    
    matched = []
    for boat in boats:
        available_dates = boat.get("availability", [])
        # Check if any date in availability matches requested month
        month_match = any(d.startswith(travel_month) for d in available_dates)
        if month_match:
            boat["availability_status"] = boat.get("booking_status", "available")
            matched.append(boat)
    return matched


# ── Tool 7: Price range filter

def tool_price_range_filter(
    boats: list[dict],
    budget_min: float | None,
    budget_max: float | None
) -> list[dict]:
    # Normalize string values like "15k", "15000", "₹15,000"
    def _parse_budget(v):
        if v is None:
            return None
        if isinstance(v, (int, float)):
            return float(v)
        s = str(v).lower().replace(",", "").replace("₹", "").strip()
        if s.endswith("k"):
            try:
                return float(s[:-1]) * 1000
            except Exception:
                return None
        try:
            return float(s)
        except Exception:
            return None

    budget_min = _parse_budget(budget_min)
    budget_max = _parse_budget(budget_max)

    filtered = boats
    if budget_min is not None:
        filtered = [b for b in filtered if b.get("price_per_day", 0) >= budget_min]
    if budget_max is not None:
        filtered = [b for b in filtered if b.get("price_per_day", 0) <= budget_max]

    sorted_boats = sorted(filtered, key=lambda b: b.get("price_per_day", 0))
    for i, b in enumerate(sorted_boats):
        b["price_rank"] = i + 1
    return sorted_boats


# ── Tool 8: Review sentiment analysis

def tool_review_sentiment_analysis(boats: list[dict]) -> list[dict]:
    """
    Score boats based on rating + review sentiment.
    Attaches review_score (0-100).
    """
    for boat in boats:
        rating  = boat.get("rating", 0)
        reviews = boat.get("reviews", [])
        
        # Count sentiment distribution
        positive = sum(1 for r in reviews if r.get("sentiment") == "positive")
        neutral  = sum(1 for r in reviews if r.get("sentiment") == "neutral")
        negative = sum(1 for r in reviews if r.get("sentiment") == "negative")
        
        # Sentiment score: 70% from rating, 30% from review positivity
        rating_score    = (rating / 5) * 70
        sentiment_score = 0
        if len(reviews) > 0:
            sentiment_score = (positive / len(reviews)) * 30
        
        boat["review_score"] = round(rating_score + sentiment_score, 1)
        boat["sentiment_breakdown"] = {"positive": positive, "neutral": neutral, "negative": negative}
    
    return boats


# ── Tool 9: Activity-based recommendation

def tool_activity_recommendation(boats: list[dict], requirements: dict) -> list[dict]:
    """
    Score boats by: price_rank, review_score, activity match, preference match.
    Returns top 5.
    """
    preferences = [p.lower() for p in (requirements.get("preferences") or [])]
    
    for boat in boats:
        score = boat.get("review_score", 50)
        
        # Price rank bonus
        price_rank = boat.get("price_rank", 5)
        score += max(0, (6 - price_rank) * 3)
        
        # Activity match
        activities = [a.lower() for a in boat.get("activities", [])]
        for pref in preferences:
            if any(pref in act for act in activities):
                score += 5
        
        # Preference match (amenities + boat type + price range)
        amenities  = " ".join(boat.get("amenities", [])).lower()
        boat_type  = boat.get("type", "").lower()
        price_range = boat.get("price_range", "").lower()
        
        context = f"{amenities} {boat_type} {price_range}"
        for pref in preferences:
            if pref in context:
                score += 5
        
        boat["recommendation_score"] = round(score, 1)
    
    return sorted(boats, key=lambda b: b["recommendation_score"], reverse=True)[:5]


# ── Tool 10: Booking assistance

def tool_booking_assistance(boat: dict, requirements: dict, user_profile: dict) -> dict:
    travel_month = requirements.get("travel_month")
    # Pick first available date in the month
    available_dates = boat.get("availability", [])
    travel_date     = None
    if travel_month:
        travel_date = next((d for d in available_dates if d.startswith(travel_month)), available_dates[0] if available_dates else None)
    else:
        travel_date = available_dates[0] if available_dates else None
    
    return {
        "boat_id":        boat["_id"],
        "boat_name":      boat["name"],
        "boat_type":      boat["type"],
        "location":       boat.get("location"),
        "route":          boat.get("route", []),
        "travel_date":    travel_date,
        "passengers":     requirements.get("passengers") or 1,
        "price_per_day":  boat.get("price_per_day"),
        "crew":           boat.get("crew", []),
        "amenities":      boat.get("amenities", []),
        "activities":     boat.get("activities", []),
        "rating":         boat.get("rating"),
        "user_name":      user_profile.get("name"),
        "status":         "pending_confirmation",
    }


# ── Tool 11: Payment processing

def tool_payment_processing(booking_summary: dict, payment_method: str = "online") -> dict:
    import uuid
    return {
        "payment_status":  "success",
        "transaction_id":  str(uuid.uuid4()),
        "payment_method":  payment_method,
        "amount_charged":  booking_summary.get("price_per_day"),
        "currency":        "INR",
    }


# ── Tool 12: Booking confirmation

def tool_booking_confirmation(booking_summary: dict, payment_result: dict, user_profile: dict) -> dict:
    booking = {
        **booking_summary,
        "user_id":   user_profile.get("user_id"),
        "payment":   payment_result,
        "status":    "confirmed",
        "booked_at": datetime.utcnow().isoformat(),
    }
    booking_id = save_booking(booking)
    
    # Update user memory
    update_user_booking(
        user_id=user_profile.get("user_id"),
        booking_id=booking_id,
        boat_name=booking_summary.get("boat_name"),
        travel_date=booking_summary.get("travel_date"),
    )
    update_user_preference(
        user_id=user_profile.get("user_id"),
        location=booking_summary.get("location"),
    )
    
    return {
        "booking_id":     booking_id,
        "boat_name":      booking_summary.get("boat_name"),
        "travel_date":    booking_summary.get("travel_date"),
        "passengers":     booking_summary.get("passengers"),
        "price_per_day":  booking_summary.get("price_per_day"),
        "transaction_id": payment_result.get("transaction_id"),
        "status":         "confirmed",
        "message":        f"Booking confirmed for {user_profile.get('name')}! Booking ID: {booking_id}",
    }
