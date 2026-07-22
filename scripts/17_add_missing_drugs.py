import json, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

new_drugs = [
    {"rxcui": "161", "name_en": "Acetaminophen 500 MG Oral Tablet", "name_vi": "Acetaminophen 500mg", "category": "Giảm đau", "generic": "acetaminophen"},
    {"rxcui": "1191", "name_en": "Aspirin 325 MG Oral Tablet", "name_vi": "Aspirin 325mg", "category": "Tim mạch", "generic": "aspirin"},
    {"rxcui": "83367", "name_en": "Aspirin 81 MG Oral Tablet", "name_vi": "Aspirin 81mg", "category": "Tim mạch", "generic": "aspirin"},
    {"rxcui": "259256", "name_en": "Atorvastatin 80 MG Oral Tablet", "name_vi": "Atorvastatin 80mg", "category": "Tim mạch", "generic": "atorvastatin"},
    {"rxcui": "197384", "name_en": "Metoprolol Succinate 100 MG Extended Release Oral Tablet", "name_vi": "Metoprolol succinate 100mg", "category": "Tim mạch", "generic": "metoprolol"},
    {"rxcui": "197385", "name_en": "Metoprolol Tartrate 25 MG Oral Tablet", "name_vi": "Metoprolol 25mg", "category": "Tim mạch", "generic": "metoprolol"},
    {"rxcui": "197388", "name_en": "Metoprolol Tartrate 5 MG Oral Tablet", "name_vi": "Metoprolol 5mg", "category": "Tim mạch", "generic": "metoprolol"},
    {"rxcui": "310429", "name_en": "Furosemide 40 MG Oral Tablet", "name_vi": "Furosemide 40mg", "category": "Tim mạch", "generic": "furosemide"},
    {"rxcui": "197381", "name_en": "Furosemide 20 MG Oral Tablet", "name_vi": "Furosemide 20mg", "category": "Tim mạch", "generic": "furosemide"},
    {"rxcui": "310494", "name_en": "Lisinopril 2.5 MG Oral Tablet", "name_vi": "Lisinopril 2.5mg", "category": "Tim mạch", "generic": "lisinopril"},
    {"rxcui": "316049", "name_en": "Prednisone 40 MG Oral Tablet", "name_vi": "Prednisone 40mg", "category": "Kháng viêm", "generic": "prednisone"},
    {"rxcui": "860975", "name_en": "Methylprednisolone 125 MG Injection", "name_vi": "Methylprednisolone 125mg", "category": "Kháng viêm", "generic": "methylprednisolone"},
    {"rxcui": "309845", "name_en": "Levofloxacin 750 MG Oral Tablet", "name_vi": "Levofloxacin 750mg", "category": "Kháng sinh", "generic": "levofloxacin"},
    {"rxcui": "11124", "name_en": "Vancomycin 1000 MG Injection", "name_vi": "Vancomycin 1g", "category": "Kháng sinh", "generic": "vancomycin"},
    {"rxcui": "309092", "name_en": "Ceftriaxone 250 MG Injection", "name_vi": "Ceftriaxone 250mg", "category": "Kháng sinh", "generic": "ceftriaxone"},
    {"rxcui": "200237", "name_en": "Bumetanide 2 MG Oral Tablet", "name_vi": "Bumetanide 2mg", "category": "Tim mạch", "generic": "bumetanide"},
    {"rxcui": "3322", "name_en": "Diazepam 5 MG Oral Tablet", "name_vi": "Diazepam 5mg", "category": "Tâm thần", "generic": "diazepam"},
    {"rxcui": "89711", "name_en": "Hydromorphone 2 MG Oral Tablet", "name_vi": "Hydromorphone 2mg", "category": "Giảm đau", "generic": "hydromorphone"},
    {"rxcui": "101833", "name_en": "Ranolazine 500 MG Oral Tablet", "name_vi": "Ranolazine 500mg", "category": "Tim mạch", "generic": "ranolazine"},
    {"rxcui": "311985", "name_en": "Nitroglycerin 0.4 MG Sublingual Tablet", "name_vi": "Nitroglycerin 0.4mg", "category": "Tim mạch", "generic": "nitroglycerin"},
    {"rxcui": "211985", "name_en": "Guaifenesin 400 MG Oral Tablet", "name_vi": "Guaifenesin 400mg", "category": "Hô hấp", "generic": "guaifenesin"},
    {"rxcui": "1361462", "name_en": "Tacrolimus 1 MG Oral Capsule", "name_vi": "Tacrolimus 1mg", "category": "Ức chế miễn dịch", "generic": "tacrolimus"},
    {"rxcui": "1361463", "name_en": "Tacrolimus 5 MG Oral Capsule", "name_vi": "Tacrolimus 5mg", "category": "Ức chế miễn dịch", "generic": "tacrolimus"},
    {"rxcui": "103726", "name_en": "Ondansetron 4 MG Oral Tablet", "name_vi": "Ondansetron 4mg", "category": "Tiêu hóa", "generic": "ondansetron"},
    {"rxcui": "310454", "name_en": "Losartan 50 MG Oral Tablet", "name_vi": "Losartan 50mg", "category": "Tim mạch", "generic": "losartan"},
    {"rxcui": "316517", "name_en": "Losartan 100 MG Oral Tablet", "name_vi": "Losartan 100mg", "category": "Tim mạch", "generic": "losartan"},
    {"rxcui": "316109", "name_en": "Amlodipine 10 MG / Benazepril 20 MG Oral Capsule", "name_vi": "Amlodipine 10mg + Benazepril 20mg", "category": "Tim mạch", "generic": "amlodipine/benazepril"},
    {"rxcui": "200033", "name_en": "Clopidogrel 75 MG Oral Tablet", "name_vi": "Clopidogrel 75mg", "category": "Tim mạch", "generic": "clopidogrel"},
    {"rxcui": "308136", "name_en": "Amlodipine 2.5 MG Oral Tablet", "name_vi": "Amlodipine 2.5mg", "category": "Tim mạch", "generic": "amlodipine"},
    {"rxcui": "197362", "name_en": "Omeprazole 20 MG Delayed Release Oral Capsule", "name_vi": "Omeprazole 20mg", "category": "Tiêu hóa", "generic": "omeprazole"},
    {"rxcui": "198208", "name_en": "Pantoprazole 40 MG Delayed Release Oral Tablet", "name_vi": "Pantoprazole 40mg", "category": "Tiêu hóa", "generic": "pantoprazole"},
    {"rxcui": "866437", "name_en": "Esomeprazole 40 MG Delayed Release Oral Capsule", "name_vi": "Esomeprazole 40mg", "category": "Tiêu hóa", "generic": "esomeprazole"},
    {"rxcui": "261973", "name_en": "Warfarin 5 MG Oral Tablet", "name_vi": "Warfarin 5mg", "category": "Tim mạch", "generic": "warfarin"},
    {"rxcui": "855333", "name_en": "Warfarin 2.5 MG Oral Tablet", "name_vi": "Warfarin 2.5mg", "category": "Tim mạch", "generic": "warfarin"},
]

with open("databases/rxnorm/rxnorm_database.json", encoding="utf-8") as f:
    db = json.load(f)

added = 0
for drug in new_drugs:
    if drug["rxcui"] not in db["drugs"]:
        drug["search_text"] = (drug["name_en"].lower() + " " + drug["name_vi"].lower() + " " + drug["generic"])
        db["drugs"][drug["rxcui"]] = drug
        added += 1

db["total_drugs"] = len(db["drugs"])

with open("databases/rxnorm/rxnorm_database.json", "w", encoding="utf-8") as f:
    json.dump(db, f, ensure_ascii=False, indent=2)

print("Added %d new drugs. Total: %d" % (added, db["total_drugs"]))
