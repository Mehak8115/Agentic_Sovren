from database.mongodb import (
    available_jobs_collection
)

available_jobs_collection.delete_many({})

jobs = [
    {
"title":"Senior Captain - Mumbai Ferry Routes",
"role":"Captain",
"location":"Mumbai",
"salary":"₹120k-₹180k",
"vacancies":1,
"minimum_experience":8,
"mandatory_skills":[
"navigation",
"radar operation",
"crew management",
"seamanship"
],
"required_certifications":[
"Master Mariner Certificate",
"STCW Basic Safety Training"
]
},

{
"title":"Captain - Chennai Port Operations",
"role":"Captain",
"location":"Chennai",
"salary":"₹110k-₹160k",
"vacancies":2,
"minimum_experience":6,
"mandatory_skills":[
"navigation",
"radar operation",
"vessel operations"
],
"required_certifications":[
"Master Mariner Certificate"
]
},

{
"title":"Junior Captain - Goa Cruises",
"role":"Captain",
"location":"Goa",
"salary":"₹70k-₹100k",
"vacancies":2,
"minimum_experience":3,
"mandatory_skills":[
"navigation",
"seamanship"
],
"required_certifications":[
"STCW Basic Safety Training"
]
},

{
"title":"Marine Navigator - Kochi",
"role":"Navigator",
"location":"Kochi",
"salary":"₹70k-₹110k",
"vacancies":2,
"minimum_experience":2,
"mandatory_skills":[
"navigation",
"gps systems",
"route planning"
],
"required_certifications":[
"RADAR Navigation Certificate"
]
},

{
"title":"Chief Marine Engineer",
"role":"Engineer",
"location":"Mumbai",
"salary":"₹100k-₹150k",
"vacancies":1,
"minimum_experience":6,
"mandatory_skills":[
"marine engine repair",
"mechanical maintenance",
"electrical systems"
],
"required_certifications":[
"Marine Engineering License"
]
},

{
"title":"Marine Maintenance Engineer",
"role":"Engineer",
"location":"Kochi",
"salary":"₹80k-₹120k",
"vacancies":3,
"minimum_experience":3,
"mandatory_skills":[
"mechanical maintenance",
"troubleshooting",
"safety practices"
],
"required_certifications":[
"STCW Basic Safety Training"
]
},

{
"title":"Offshore Medical Officer",
"role":"Medic",
"location":"Mumbai",
"salary":"₹90k-₹130k",
"vacancies":1,
"minimum_experience":4,
"mandatory_skills":[
"first aid",
"cpr",
"emergency response"
],
"required_certifications":[
"Medical Care Onboard Ship"
]
},

{
"title":"Deckhand - Cargo Vessel",
"role":"Deckhand",
"location":"Chennai",
"salary":"₹35k-₹50k",
"vacancies":5,
"minimum_experience":1,
"mandatory_skills":[
"rope handling",
"loading operations",
"safety procedures"
],
"required_certifications":[
"STCW Basic Safety Training"
]
},

{
"title":"Cruise Steward",
"role":"Steward",
"location":"Goa",
"salary":"₹40k-₹60k",
"vacancies":3,
"minimum_experience":1,
"mandatory_skills":[
"customer service",
"hospitality",
"food service"
],
"required_certifications":[
"Food Safety Certificate"
]
},
]

available_jobs_collection.insert_many(
    jobs
)

print(
    f"{len(jobs)} Available Jobs Seeded"
)