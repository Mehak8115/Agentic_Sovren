# database/seed_boats.p

from database.mongodb import db
from datetime import date, timedelta

boats_collection = db["boats"]


def _dates(start_str: str, count: int = 8) -> list[str]:
    """Generate `count` dates every 3 days starting from start_str."""
    start = date.fromisoformat(start_str)
    return [(start + timedelta(days=i * 3)).isoformat() for i in range(count)]


def _full_year() -> list[str]:
    """Generate dates across multiple months."""
    all_dates = []
    for ms in month_strs:
        start = date.fromisoformat(ms)
        all_dates += [(start + timedelta(days=i * 5)).isoformat() for i in range(per_month)]
    return all_dates

# Covers Jul → Dec 2026 for every boat
def _full_year(day: int = 1) -> list[str]:
    months = ["2026-07","2026-08","2026-09","2026-10","2026-11","2026-12"]
    all_dates = []
    for m in months:
        start = date.fromisoformat(f"{m}-{day:02d}")
        all_dates += [(start + timedelta(days=i*6)).isoformat() for i in range(4)]
    return all_dates


# ── 50 boats across Indian maritime routes ────────────────────────────────────
BOATS = [

    # ── Mumbai ──────────────────────────────────────────────────────────────
    {
        "name": "Mumbai Mariner",
        "location": "Mumbai",                          # home port
        "type": "cargo",
        "capacity": 60,
        "route": ["Mumbai", "Goa", "Kochi"],
        "price_per_day": 14000,
        "price_range": "budget",                       # budget / mid / luxury
        "availability": _full_year(),
        "booking_status": "available",                 # available / fully_booked / partially_booked
        "rating": 4.3,
        "reviews": [
            {"user": "Ravi", "text": "Reliable and on time.", "sentiment": "positive"},
            {"user": "Priya", "text": "Decent cargo space.", "sentiment": "positive"},
        ],
        "crew": ["Captain Arjun Singh", "Engineer Ramesh Nair", "Deckhand Suresh Kumar"],
        "amenities": ["GPS", "life jackets", "cargo hold", "crew quarters"],
        "activities": ["cargo loading experience", "sunset deck viewing"],
    },
    {
        "name": "Arabian Queen",
        "location": "Mumbai",
        "type": "cruise",
        "capacity": 150,
        "route": ["Mumbai", "Goa", "Lakshadweep"],
        "price_per_day": 45000,
        "price_range": "luxury",
        "availability": _full_year(),
        "booking_status": "available",
        "rating": 4.9,
        "reviews": [
            {"user": "Sneha", "text": "Absolutely breathtaking experience!", "sentiment": "positive"},
            {"user": "Rohan", "text": "Worth every rupee. Exceptional service.", "sentiment": "positive"},
            {"user": "Kiran", "text": "The food was mediocre but the views made up for it.", "sentiment": "neutral"},
        ],
        "crew": ["Captain Vikram Sharma", "Chef Anand Pillai", "Hostess Meera Joshi", "Navigator Deepak Rao"],
        "amenities": ["restaurant", "pool", "spa", "GPS", "life jackets", "luxury cabins", "bar"],
        "activities": ["dolphin watching", "snorkeling", "sunset cocktail cruise", "island hopping"],
    },
    {
        "name": "Harbor Swift",
        "location": "Mumbai",
        "type": "ferry",
        "capacity": 300,
        "route": ["Mumbai", "Alibaug", "Mandwa"],
        "price_per_day": 8000,
        "price_range": "budget",
        "availability": _full_year(),
        "booking_status": "available",
        "rating": 3.8,
        "reviews": [
            {"user": "Ajay", "text": "Gets the job done. Nothing fancy.", "sentiment": "neutral"},
            {"user": "Fatima", "text": "Crowded but affordable.", "sentiment": "neutral"},
        ],
        "crew": ["Captain Mohan Das", "Deckhand Vijay Patil"],
        "amenities": ["seating", "GPS", "life jackets", "cafeteria"],
        "activities": ["coastal sightseeing"],
    },

    {
        "name": "Mumbai Explorer",
        "location": "Mumbai",
        "type": "yacht",
        "capacity": 25,
        "route": ["Mumbai", "Elephanta Island", "Karanja"],
        "price_per_day": 28000,
        "price_range": "mid",
        "availability": _full_year(),
        "booking_status": "available",
        "rating": 4.6,
        "reviews": [
            {"user": "Neha", "text": "Perfect for a private party!", "sentiment": "positive"},
            {"user": "Siddharth", "text": "Crew was super helpful.", "sentiment": "positive"},
        ],
        "crew": ["Captain Aditya Mehta", "Hostess Riya Sen"],
        "amenities": ["GPS", "life jackets", "sun deck", "bar", "music system"],
        "activities": ["island visit", "snorkeling", "sunset cruise", "fishing"],
    },
    {
        "name": "Konkan Carrier",
        "location": "Mumbai",
        "type": "cargo",
        "capacity": 90,
        "route": ["Mumbai", "Ratnagiri", "Malvan"],
        "price_per_day": 19000,
        "price_range": "mid",
        "availability": _full_year(),
        "booking_status": "partially_booked",
        "rating": 4.1,
        "reviews": [
            {"user": "Rajesh", "text": "Good capacity, reliable schedule.", "sentiment": "positive"},
            {"user": "Sunita", "text": "Slight delay on return but manageable.", "sentiment": "neutral"},
        ],
        "crew": ["Captain Prakash Kadam", "Engineer Santosh More", "Deckhand Ganesh Patil"],
        "amenities": ["GPS", "life jackets", "large cargo hold", "crane", "crew quarters"],
        "activities": ["coastal cargo experience", "deck walk"],
    },

    # ── Goa ─────────────────────────────────────────────────────────────────
    {
        "name": "Goa Pearl",
        "location": "Goa",
        "type": "cruise",
        "capacity": 100,
        "route": ["Goa", "Lakshadweep", "Kochi"],
        "price_per_day": 38000,
        "price_range": "luxury",
        "availability": _full_year(),
        "booking_status": "available",
        "rating": 4.7,
        "reviews": [
            {"user": "Aryan", "text": "Stunning cruise, highly recommend!", "sentiment": "positive"},
            {"user": "Priyanka", "text": "Excellent crew and food.", "sentiment": "positive"},
            {"user": "Dev", "text": "A bit expensive but worth it.", "sentiment": "positive"},
        ],
        "crew": ["Captain Fernandez", "Chef Carla D'Souza", "Navigator Jose Pereira"],
        "amenities": ["restaurant", "pool", "GPS", "life jackets", "cabins", "bar", "spa"],
        "activities": ["snorkeling", "island hopping", "dolphin watching", "sunset cruise"],
    },
    {
        "name": "Mandovi Express",
        "location": "Goa",
        "type": "ferry",
        "capacity": 200,
        "route": ["Goa", "Panaji", "Betim", "Chorao Island"],
        "price_per_day": 6000,
        "price_range": "budget",
        "availability": _full_year(),
        "booking_status": "available",
        "rating": 3.9,
        "reviews": [
            {"user": "Lucia", "text": "Basic but does the job.", "sentiment": "neutral"},
            {"user": "Marco", "text": "Good for short hops.", "sentiment": "positive"},
        ],
        "crew": ["Captain Rodrigues", "Deckhand Anthony Gomes"],
        "amenities": ["seating", "GPS", "life jackets"],
        "activities": ["river sightseeing", "bird watching"],
    },
    {
        "name": "Sunset Voyager",
        "location": "Goa",
        "type": "yacht",
        "capacity": 20,
        "route": ["Goa", "Anjuna", "Baga Beach"],
        "price_per_day": 32000,
        "price_range": "luxury",
        "availability": _full_year(),
        "booking_status": "available",
        "rating": 4.8,
        "reviews": [
            {"user": "Tanya", "text": "Magical sunset experience!", "sentiment": "positive"},
            {"user": "Rahul", "text": "The best evening of my Goa trip.", "sentiment": "positive"},
        ],
        "crew": ["Captain Mark Fernandes", "Hostess Sophia D'Silva"],
        "amenities": ["GPS", "life jackets", "sun deck", "bar", "music system", "BBQ"],
        "activities": ["sunset cruise", "swimming", "beach hopping", "BBQ on deck"],
    },
    {
        "name": "Goa Cargo King",
        "location": "Goa",
        "type": "cargo",
        "capacity": 70,
        "route": ["Goa", "Mumbai", "Mangalore"],
        "price_per_day": 16000,
        "price_range": "mid",
        "availability": _full_year(),
        "booking_status": "fully_booked",
        "rating": 4.0,
        "reviews": [
            {"user": "Sanjay", "text": "Always on schedule.", "sentiment": "positive"},
            {"user": "Meena", "text": "Crew is professional.", "sentiment": "positive"},
        ],
        "crew": ["Captain Desai", "Engineer Pooja Naik", "Deckhand Ramu Gaonkar"],
        "amenities": ["GPS", "life jackets", "cargo hold", "crew quarters"],
        "activities": ["port tour", "cargo operations view"],
    },

    # ── Kochi (Kerala) ──────────────────────────────────────────────────────
    {
        "name": "Cochin Cruiser",
        "location": "Kochi",
        "type": "cruise",
        "capacity": 80,
        "route": ["Kochi", "Alleppey", "Kumarakom"],
        "price_per_day": 18000,
        "price_range": "mid",
        "availability": _full_year(),
        "booking_status": "available",
        "rating": 4.5,
        "reviews": [
            {"user": "Ananya", "text": "Peaceful backwaters experience.", "sentiment": "positive"},
            {"user": "Gopal", "text": "Good value for money.", "sentiment": "positive"},
        ],
        "crew": ["Captain Krishna Menon", "Chef Lakshmi Nair", "Navigator Suresh Pillai"],
        "amenities": ["restaurant", "GPS", "life jackets", "cabins", "sun deck"],
        "activities": ["backwater cruise", "village tour", "bird watching", "kayaking"],
    },
    {
        "name": "Kerala Mermaid",
        "location": "Alleppey",
        "type": "houseboat",
        "capacity": 12,
        "route": ["Kochi", "Alleppey", "Vembanad Lake"],
        "price_per_day": 15000,
        "price_range": "mid",
        "availability": _full_year(),
        "booking_status": "available",
        "rating": 4.7,
        "reviews": [
            {"user": "Divya", "text": "Perfect romantic getaway!", "sentiment": "positive"},
            {"user": "Amit", "text": "Serene and beautiful.", "sentiment": "positive"},
        ],
        "crew": ["Captain Thomas", "Chef Mary George"],
        "amenities": ["GPS", "life jackets", "bedroom", "kitchen", "dining area"],
        "activities": ["backwater cruise", "fishing", "local village visit", "birdwatching"],
    },
    {
        "name": "Vembanad Queen",
        "location": "Alleppey",
        "type": "houseboat",
        "capacity": 35,
        "route": ["Alleppey", "Kumarakom", "Vembanad Lake"],
        "price_per_day": 17000,
        "price_range": "mid",
        "availability": _full_year(),
        "booking_status": "available",
        "rating": 4.6,
        "reviews": [
            {"user": "Sreeja", "text": "Lovely houseboat, great crew.", "sentiment": "positive"},
            {"user": "Vishnu", "text": "Kerala backwaters at its best!", "sentiment": "positive"},
        ],
        "crew": ["Captain Rajan", "Chef Geetha", "Deckhand Biju"],
        "amenities": ["GPS", "life jackets", "bedroom", "kitchen", "dining area", "sun deck"],
        "activities": ["backwater cruise", "fishing", "village visit", "cooking demo", "sunset viewing"],
    },
    {
        "name": "Alleppey Explorer",
        "location": "Alleppey",
        "type": "ferry",
        "capacity": 100,
        "route": ["Alleppey", "Kottayam", "Kumarakom"],
        "price_per_day": 9000,
        "price_range": "budget",
        "availability": _full_year(),
        "booking_status": "available",
        "rating": 4.0,
        "reviews": [
            {"user": "Renu", "text": "Affordable and scenic route.", "sentiment": "positive"},
            {"user": "Manoj", "text": "Good for group travel.", "sentiment": "positive"},
        ],
        "crew": ["Captain Saji", "Deckhand Anil"],
        "amenities": ["seating", "GPS", "life jackets", "snack counter"],
        "activities": ["backwater sightseeing", "paddy field views"],
    },
    {
        "name": "Spice Coast Express",
        "location": "Kochi",
        "type": "ferry",
        "capacity": 150,
        "route": ["Kochi", "Vypeen Island", "Fort Kochi"],
        "price_per_day": 7000,
        "price_range": "budget",
        "availability": _full_year(),
        "booking_status": "available",
        "rating": 3.7,
        "reviews": [
            {"user": "Rajiv", "text": "Quick and cheap.", "sentiment": "neutral"},
            {"user": "Nisha", "text": "Crowded but efficient.", "sentiment": "neutral"},
        ],
        "crew": ["Captain Antony", "Deckhand Jeevan"],
        "amenities": ["seating", "GPS", "life jackets"],
        "activities": ["island hopping", "local sightseeing"],
    },
    {
        "name": "Backwater Breeze",
        "location": "Kochi",
        "type": "houseboat",
        "capacity": 40,
        "route": ["Kochi", "Alleppey", "Kumarakom", "Vembanad Lake"],
        "price_per_day": 19500,
        "price_range": "mid",
        "availability": _full_year(),
        "booking_status": "available",
        "rating": 4.4,
        "reviews": [
            {"user": "Pooja", "text": "Wonderful experience on the backwaters.", "sentiment": "positive"},
            {"user": "Rahul", "text": "Very peaceful and relaxing.", "sentiment": "positive"},
        ],
        "crew": ["Captain George", "Chef Susheela", "Deckhand Raju"],
        "amenities": ["GPS", "life jackets", "bedrooms", "kitchen", "dining", "sun deck", "AC"],
        "activities": ["backwater cruise", "fishing", "bird watching", "local market visit"],
    },

    # ── Chennai ─────────────────────────────────────────────────────────────
    {
        "name": "Marina Explorer",
        "location": "Chennai",
        "type": "yacht",
        "capacity": 30,
        "route": ["Chennai", "Pondicherry", "Mahabalipuram"],
        "price_per_day": 27000,
        "price_range": "mid",
        "availability": _full_year(),
        "booking_status": "available",
        "rating": 4.4,
        "reviews": [
            {"user": "Karthi", "text": "Great crew and clean boat.", "sentiment": "positive"},
            {"user": "Lakshmi", "text": "Smooth sailing experience.", "sentiment": "positive"},
        ],
        "crew": ["Captain Venkat", "Navigator Bala", "Hostess Anjali"],
        "amenities": ["GPS", "life jackets", "sun deck", "bar", "music system"],
        "activities": ["coastal cruise", "beach visit", "fishing", "sunset viewing"],
    },
    {
        "name": "Tamil Trader",
        "location": "Chennai",
        "type": "cargo",
        "capacity": 100,
        "route": ["Chennai", "Tuticorin", "Port Blair"],
        "price_per_day": 24000,
        "price_range": "mid",
        "availability": _full_year(),
        "booking_status": "partially_booked",
        "rating": 4.2,
        "reviews": [
            {"user": "Murugan", "text": "Reliable for long haul cargo.", "sentiment": "positive"},
            {"user": "Selvi", "text": "Good capacity and safe.", "sentiment": "positive"},
        ],
        "crew": ["Captain Ravi Kumar", "Engineer Saravanan", "Deckhand Selvam"],
        "amenities": ["GPS", "life jackets", "large cargo hold", "crane", "crew quarters"],
        "activities": ["port operations tour", "cargo handling demo"],
    },
    {
        "name": "Coromandel Ferry",
        "location": "Chennai",
        "type": "ferry",
        "capacity": 250,
        "route": ["Chennai", "Puducherry"],
        "price_per_day": 10000,
        "price_range": "budget",
        "availability": _full_year(),
        "booking_status": "available",
        "rating": 3.9,
        "reviews": [
            {"user": "Arvind", "text": "Good connectivity.", "sentiment": "positive"},
            {"user": "Gayathri", "text": "Timely service.", "sentiment": "positive"},
        ],
        "crew": ["Captain Subramanian", "Deckhand Raj"],
        "amenities": ["seating", "GPS", "life jackets", "snack counter"],
        "activities": ["coastal sightseeing"],
    },

    # ── Kolkata ────────────────────────────────────────────────────────────
    {
        "name": "Hooghly Navigator",
        "location": "Kolkata",
        "type": "ferry",
        "capacity": 200,
        "route": ["Kolkata", "Sundarbans", "Sagar Island"],
        "price_per_day": 9000,
        "price_range": "budget",
        "availability": _full_year(),
        "booking_status": "available",
        "rating": 4.0,
        "reviews": [
            {"user": "Souvik", "text": "Amazing Sundarbans experience.", "sentiment": "positive"},
            {"user": "Payal", "text": "Comfortable journey.", "sentiment": "positive"},
        ],
        "crew": ["Captain Debasis", "Navigator Arnab", "Deckhand Subhash"],
        "amenities": ["seating", "GPS", "life jackets", "cafeteria"],
        "activities": ["mangrove tour", "tiger spotting cruise", "bird watching"],
    },
    {
        "name": "Bengal Pride",
        "location": "Kolkata",
        "type": "cargo",
        "capacity": 85,
        "route": ["Kolkata", "Haldia", "Paradip"],
        "price_per_day": 20000,
        "price_range": "mid",
        "availability": _full_year(),
        "booking_status": "available",
        "rating": 4.1,
        "reviews": [
            {"user": "Arindam", "text": "Efficient cargo operations.", "sentiment": "positive"},
            {"user": "Shreya", "text": "Crew is skilled.", "sentiment": "positive"},
        ],
        "crew": ["Captain Chatterjee", "Engineer Banerjee", "Deckhand Roy"],
        "amenities": ["GPS", "life jackets", "cargo hold", "crane", "crew quarters"],
        "activities": ["port tour", "cargo operations view"],
    },

    # ── Visakhapatnam ──────────────────────────────────────────────────────
    {
        "name": "Vizag Voyager",
        "location": "Visakhapatnam",
        "type": "yacht",
        "capacity": 35,
        "route": ["Visakhapatnam", "Rushikonda", "Bheemili"],
        "price_per_day": 26000,
        "price_range": "mid",
        "availability": _full_year(),
        "booking_status": "available",
        "rating": 4.5,
        "reviews": [
            {"user": "Prasad", "text": "Beautiful coastal views!", "sentiment": "positive"},
            {"user": "Kavya", "text": "Professional crew and well-maintained.", "sentiment": "positive"},
        ],
        "crew": ["Captain Naidu", "Hostess Priya", "Navigator Raju"],
        "amenities": ["GPS", "life jackets", "sun deck", "bar", "music system"],
        "activities": ["beach cruise", "swimming", "fishing", "sunset viewing"],
    },
    {
        "name": "Andhra Carrier",
        "location": "Visakhapatnam",
        "type": "cargo",
        "capacity": 95,
        "route": ["Visakhapatnam", "Chennai", "Kakinada"],
        "price_per_day": 21000,
        "price_range": "mid",
        "availability": _full_year(),
        "booking_status": "available",
        "rating": 4.3,
        "reviews": [
            {"user": "Venkat", "text": "Timely deliveries every time.", "sentiment": "positive"},
            {"user": "Jyothi", "text": "Safe and secure cargo handling.", "sentiment": "positive"},
        ],
        "crew": ["Captain Rao", "Engineer Krishna", "Deckhand Babu"],
        "amenities": ["GPS", "life jackets", "large cargo hold", "crane", "crew quarters"],
        "activities": ["port operations experience"],
    },

    # ── Mangalore ───────────────────────────────────────────────────────────
    {
        "name": "Karavali Express",
        "location": "Mangalore",
        "type": "ferry",
        "capacity": 120,
        "route": ["Mangalore", "Udupi", "Karwar"],
        "price_per_day": 8500,
        "price_range": "budget",
        "availability": _full_year(),
        "booking_status": "available",
        "rating": 4.1,
        "reviews": [
            {"user": "Anil", "text": "Good service along the coast.", "sentiment": "positive"},
            {"user": "Suma", "text": "Clean and comfortable.", "sentiment": "positive"},
        ],
        "crew": ["Captain Shetty", "Deckhand Prabhu"],
        "amenities": ["seating", "GPS", "life jackets", "snack counter"],
        "activities": ["coastal tour", "beach stops"],
    },
    {
        "name": "Mangalore Pearl",
        "location": "Mangalore",
        "type": "yacht",
        "capacity": 22,
        "route": ["Mangalore", "Malpe", "St. Mary's Island"],
        "price_per_day": 24000,
        "price_range": "mid",
        "availability": _full_year(),
        "booking_status": "available",
        "rating": 4.6,
        "reviews": [
            {"user": "Shreyas", "text": "Perfect for island hopping!", "sentiment": "positive"},
            {"user": "Nandini", "text": "Beautiful boat and amazing crew.", "sentiment": "positive"},
        ],
        "crew": ["Captain Hegde", "Hostess Divya"],
        "amenities": ["GPS", "life jackets", "sun deck", "bar", "music system"],
        "activities": ["island visit", "snorkeling", "fishing", "sunset cruise"],
    },

    # ── Port Blair (Andaman) ────────────────────────────────────────────────
    {
        "name": "Andaman Explorer",
        "location": "Port Blair",
        "type": "cruise",
        "capacity": 60,
        "route": ["Port Blair", "Havelock", "Neil Island"],
        "price_per_day": 35000,
        "price_range": "luxury",
        "availability": _full_year(),
        "booking_status": "available",
        "rating": 4.9,
        "reviews": [
            {"user": "Manish", "text": "Spectacular island cruise!", "sentiment": "positive"},
            {"user": "Swati", "text": "Best experience ever. Highly recommend.", "sentiment": "positive"},
        ],
        "crew": ["Captain John", "Chef Ravi", "Navigator Sarah", "Hostess Rita"],
        "amenities": ["restaurant", "pool", "GPS", "life jackets", "cabins", "bar"],
        "activities": ["scuba diving", "snorkeling", "island hopping", "beach BBQ"],
    },
    {
        "name": "Tropical Ferry",
        "location": "Port Blair",
        "type": "ferry",
        "capacity": 100,
        "route": ["Port Blair", "Havelock", "Rangat"],
        "price_per_day": 12000,
        "price_range": "budget",
        "availability": _full_year(),
        "booking_status": "partially_booked",
        "rating": 3.8,
        "reviews": [
            {"user": "Nikhil", "text": "Does the job. No frills.", "sentiment": "neutral"},
            {"user": "Pooja", "text": "A bit cramped but okay for short trips.", "sentiment": "neutral"},
        ],
        "crew": ["Captain David", "Deckhand Sam"],
        "amenities": ["seating", "GPS", "life jackets"],
        "activities": ["island sightseeing"],
    },

    # ── Lakshadweep ─────────────────────────────────────────────────────────
    {
        "name": "Coral Dreams",
        "location": "Lakshadweep",
        "type": "yacht",
        "capacity": 18,
        "route": ["Kavaratti", "Agatti", "Bangaram"],
        "price_per_day": 42000,
        "price_range": "luxury",
        "availability": _full_year(),
        "booking_status": "available",
        "rating": 5.0,
        "reviews": [
            {"user": "Rohit", "text": "Paradise on water. Absolutely stunning!", "sentiment": "positive"},
            {"user": "Isha", "text": "Dream vacation. Every moment was perfect.", "sentiment": "positive"},
        ],
        "crew": ["Captain Ibrahim", "Hostess Laila", "Chef Yusuf"],
        "amenities": ["GPS", "life jackets", "sun deck", "bar", "music system", "BBQ", "diving gear"],
        "activities": ["scuba diving", "snorkeling", "island hopping", "underwater photography", "beach BBQ"],
    },
    # ── Extra budget boats in Goa under ₹15k ──────────────────────────────
    {
        "name": "Goa Budget Cruiser",
        "location": "Goa",
        "type": "ferry",
        "capacity": 50,
        "route": ["Goa", "Panjim", "Old Goa", "Divar Island"],
        "price_per_day": 10000,
        "price_range": "budget",
        "availability": _full_year(),
        "booking_status": "available",
        "rating": 4.0,
        "reviews": [
            {"user": "Priya", "text": "Good value for money in Goa!", "sentiment": "positive"},
            {"user": "Raj",   "text": "Clean and comfortable.",        "sentiment": "positive"},
        ],
        "crew": ["Captain Silva", "Deckhand Antonio"],
        "amenities": ["GPS", "life jackets", "seating", "cafeteria"],
        "activities": ["river cruise", "heritage site visit", "bird watching"],
    },
    {
        "name": "Panjim River Hopper",
        "location": "Goa",
        "type": "houseboat",
        "capacity": 30,
        "route": ["Goa", "Panjim", "Chorao", "Divar"],
        "price_per_day": 12000,
        "price_range": "budget",
        "availability": _full_year(),
        "booking_status": "available",
        "rating": 4.2,
        "reviews": [
            {"user": "Sneha", "text": "Lovely Goa river experience!", "sentiment": "positive"},
            {"user": "Arun",  "text": "Affordable and scenic.",        "sentiment": "positive"},
        ],
        "crew": ["Captain Fernandes", "Chef Maria"],
        "amenities": ["GPS", "life jackets", "dining area", "sun deck"],
        "activities": ["river cruise", "fishing", "mangrove tour", "sunset viewing"],
    },
]


def seed():
    boats_collection.delete_many({})
    result = boats_collection.insert_many(BOATS)
    print(f"Seeded {len(result.inserted_ids)} boats across Indian maritime locations")


if __name__ == "__main__":
    seed()
