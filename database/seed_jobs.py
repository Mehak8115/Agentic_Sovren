from database.mongodb import jobs_collection

jobs_collection.delete_many({})

jobs = [

{
    "title": "Captain",

    "mandatory_skills": [
        "navigation",
        "radar operation",
        "crew management",
        "vessel operations",
        "seamanship"
    ],

    "optional_skills": [
        "weather interpretation",
        "maritime law",
        "engine systems",
        "emergency response"
    ],

    "required_certifications": [
        "Master Mariner Certificate",
        "STCW Basic Safety Training",
        "RADAR Navigation Certificate",
        "GMDSS Certificate"
    ],

    "minimum_experience": 5
},

{
    "title": "Navigator",

    "mandatory_skills": [
        "navigation",
        "route planning",
        "gps systems",
        "radar operation",
        "chart plotting"
    ],

    "optional_skills": [
        "weather interpretation",
        "communication",
        "maritime law",
        "risk assessment"
    ],

    "required_certifications": [
        "STCW Basic Safety Training",
        "RADAR Navigation Certificate"
    ],

    "minimum_experience": 2
},

{
    "title": "Engineer",

    "mandatory_skills": [
        "marine engine repair",
        "mechanical maintenance",
        "electrical systems",
        "troubleshooting",
        "safety practices"
    ],

    "optional_skills": [
        "welding",
        "hydraulics",
        "diesel engines",
        "preventive maintenance"
    ],

    "required_certifications": [
        "Marine Engineering License",
        "STCW Basic Safety Training"
    ],

    "minimum_experience": 3
},

{
    "title": "Medic",

    "mandatory_skills": [
        "first aid",
        "patient care",
        "emergency response",
        "medical assistance",
        "cpr"
    ],

    "optional_skills": [
        "trauma care",
        "communication",
        "record keeping",
        "critical care"
    ],

    "required_certifications": [
        "First Aid at Sea",
        "CPR Certification",
        "Medical Care Onboard Ship"
    ],

    "minimum_experience": 2
},

{
    "title": "Deckhand",

    "mandatory_skills": [
        "rope handling",
        "boat maintenance",
        "loading operations",
        "safety procedures",
        "physical fitness"
    ],

    "optional_skills": [
        "painting",
        "cleaning",
        "cargo handling",
        "communication"
    ],

    "required_certifications": [
        "STCW Basic Safety Training"
    ],

    "minimum_experience": 1
},

{
    "title": "Steward",

    "mandatory_skills": [
        "customer service",
        "hospitality",
        "food service",
        "cleaning",
        "communication"
    ],

    "optional_skills": [
        "inventory management",
        "housekeeping",
        "teamwork",
        "guest relations"
    ],

    "required_certifications": [
        "Food Safety Certificate"
    ],

    "minimum_experience": 1
}

]

jobs_collection.insert_many(jobs)

print("Jobs seeded successfully.")