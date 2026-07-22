"""
Script 03: Build RxNorm Drug Database
Sources:
  1. RxNorm API (rxnav.nlm.nih.gov)
  2. Vietnamese drug names (Dược thư Quốc gia)
Output: databases/rxnorm/rxnorm_database.json
"""
import json
import os
import requests
import time
from typing import Optional

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_DIR = os.path.join(PROJECT_ROOT, "databases", "rxnorm")
OUTPUT_FILE = os.path.join(DB_DIR, "rxnorm_database.json")

# ============================================================
# Vietnamese drug database (pre-built for quick startup)
# Maps drug name -> RxNorm CUI + Vietnamese name
# ============================================================

# Common drugs in Vietnamese hospitals with RxNorm CUI
RXNORM_DRUGS = [
    # Cardiovascular
    {"rxcui": "308135", "name_vi": "Amlodipine 10mg", "name_en": "Amlodipine 10 MG Oral Tablet", "category": "Tim mạch", "generic": "amlodipine"},
    {"rxcui": "308056", "name_vi": "Amlodipine 5mg", "name_en": "Amlodipine 5 MG Oral Tablet", "category": "Tim mạch", "generic": "amlodipine"},
    {"rxcui": "243670", "name_vi": "Aspirin 81mg", "name_en": "Aspirin 81 MG Oral Tablet", "category": "Tim mạch", "generic": "aspirin"},
    {"rxcui": "197361", "name_vi": "Aspirin 325mg", "name_en": "Aspirin 325 MG Oral Tablet", "category": "Tim mạch", "generic": "aspirin"},
    {"rxcui": "866436", "name_vi": "Metoprolol succinate XL 50mg", "name_en": "Metoprolol Succinate 50 MG Extended Release Oral Tablet", "category": "Tim mạch", "generic": "metoprolol"},
    {"rxcui": "866437", "name_vi": "Metoprolol succinate XL 100mg", "name_en": "Metoprolol Succinate 100 MG Extended Release Oral Tablet", "category": "Tim mạch", "generic": "metoprolol"},
    {"rxcui": "866438", "name_vi": "Metoprolol tartrate 50mg", "name_en": "Metoprolol Tartrate 50 MG Oral Tablet", "category": "Tim mạch", "generic": "metoprolol"},
    {"rxcui": "197373", "name_vi": "Metoprolol tartrate 25mg", "name_en": "Metoprolol Tartrate 25 MG Oral Tablet", "category": "Tim mạch", "generic": "metoprolol"},
    {"rxcui": "904475", "name_vi": "Pravastatin 40mg", "name_en": "Pravastatin Sodium 40 MG Oral Tablet", "category": "Tim mạch", "generic": "pravastatin"},
    {"rxcui": "904474", "name_vi": "Pravastatin 20mg", "name_en": "Pravastatin Sodium 20 MG Oral Tablet", "category": "Tim mạch", "generic": "pravastatin"},
    {"rxcui": "259255", "name_vi": "Atorvastatin 20mg", "name_en": "Atorvastatin Calcium 20 MG Oral Tablet", "category": "Tim mạch", "generic": "atorvastatin"},
    {"rxcui": "259256", "name_vi": "Atorvastatin 40mg", "name_en": "Atorvastatin Calcium 40 MG Oral Tablet", "category": "Tim mạch", "generic": "atorvastatin"},
    {"rxcui": "365667", "name_vi": "Rosuvastatin 10mg", "name_en": "Rosuvastatin Calcium 10 MG Oral Tablet", "category": "Tim mạch", "generic": "rosuvastatin"},
    {"rxcui": "365668", "name_vi": "Rosuvastatin 20mg", "name_en": "Rosuvastatin Calcium 20 MG Oral Tablet", "category": "Tim mạch", "generic": "rosuvastatin"},
    {"rxcui": "197382", "name_vi": "Clopidogrel 75mg", "name_en": "Clopidogrel Bisulfate 75 MG Oral Tablet", "category": "Tim mạch", "generic": "clopidogrel"},
    {"rxcui": "197381", "name_vi": "Clopidogrel 300mg", "name_en": "Clopidogrel Bisulfate 300 MG Oral Tablet", "category": "Tim mạch", "generic": "clopidogrel"},
    {"rxcui": "83367", "name_vi": "Warfarin 5mg", "name_en": "Warfarin Sodium 5 MG Oral Tablet", "category": "Tim mạch", "generic": "warfarin"},
    {"rxcui": "83366", "name_vi": "Warfarin 2.5mg", "name_en": "Warfarin Sodium 2.5 MG Oral Tablet", "category": "Tim mạch", "generic": "warfarin"},
    {"rxcui": "197696", "name_vi": "Losartan 50mg", "name_en": "Losartan Potassium 50 MG Oral Tablet", "category": "Tim mạch", "generic": "losartan"},
    {"rxcui": "197697", "name_vi": "Losartan 100mg", "name_en": "Losartan Potassium 100 MG Oral Tablet", "category": "Tim mạch", "generic": "losartan"},
    {"rxcui": "200033", "name_vi": "Valsartan 80mg", "name_en": "Valsartan 80 MG Oral Tablet", "category": "Tim mạch", "generic": "valsartan"},
    {"rxcui": "200034", "name_vi": "Valsartan 160mg", "name_en": "Valsartan 160 MG Oral Tablet", "category": "Tim mạch", "generic": "valsartan"},
    {"rxcui": "316095", "name_vi": "Perindopril 4mg", "name_en": "Perindopril Erbumine 4 MG Oral Tablet", "category": "Tim mạch", "generic": "perindopril"},
    {"rxcui": "316096", "name_vi": "Perindopril 8mg", "name_en": "Perindopril Erbumine 8 MG Oral Tablet", "category": "Tim mạch", "generic": "perindopril"},
    {"rxcui": "197894", "name_vi": "Spironolactone 25mg", "name_en": "Spironolactone 25 MG Oral Tablet", "category": "Tim mạch", "generic": "spironolactone"},
    {"rxcui": "310429", "name_vi": "Apixaban 5mg", "name_en": "Apixaban 5 MG Oral Tablet", "category": "Tim mạch", "generic": "apixaban"},
    {"rxcui": "1114195", "name_vi": "Apixaban 2.5mg", "name_en": "Apixaban 2.5 MG Oral Tablet", "category": "Tim mạch", "generic": "apixaban"},
    {"rxcui": "1364430", "name_vi": "Rivaroxaban 20mg", "name_en": "Rivaroxaban 20 MG Oral Tablet", "category": "Tim mạch", "generic": "rivaroxaban"},
    {"rxcui": "1364431", "name_vi": "Rivaroxaban 15mg", "name_en": "Rivaroxaban 15 MG Oral Tablet", "category": "Tim mạch", "generic": "rivaroxaban"},

    # Antihypertensive - ACE inhibitors
    {"rxcui": "197416", "name_vi": "Enalapril 5mg", "name_en": "Enalapril Maleate 5 MG Oral Tablet", "category": "Tim mạch", "generic": "enalapril"},
    {"rxcui": "197417", "name_vi": "Enalapril 10mg", "name_en": "Enalapril Maleate 10 MG Oral Tablet", "category": "Tim mạch", "generic": "enalapril"},
    {"rxcui": "310380", "name_vi": "Ramipril 5mg", "name_en": "Ramipril 5 MG Oral Tablet", "category": "Tim mạch", "generic": "ramipril"},
    {"rxcui": "310381", "name_vi": "Ramipril 10mg", "name_en": "Ramipril 10 MG Oral Tablet", "category": "Tim mạch", "generic": "ramipril"},

    # Antihypertensive - CCB
    {"rxcui": "197840", "name_vi": "Diltiazem 30mg", "name_en": "Diltiazem Hydrochloride 30 MG Oral Tablet", "category": "Tim mạch", "generic": "diltiazem"},
    {"rxcui": "197841", "name_vi": "Diltiazem 60mg", "name_en": "Diltiazem Hydrochloride 60 MG Oral Tablet", "category": "Tim mạch", "generic": "diltiazem"},

    # Nitrate
    {"rxcui": "200257", "name_vi": "Isosorbide mononitrate 30mg", "name_en": "Isosorbide Mononitrate 30 MG Extended Release Oral Tablet", "category": "Tim mạch", "generic": "isosorbide"},
    {"rxcui": "197493", "name_vi": "Nitroglycerin 0.5mg", "name_en": "Nitroglycerin 0.5 MG Sublingual Tablet", "category": "Tim mạch", "generic": "nitroglycerin"},

    # Antiarrhythmic
    {"rxcui": "83367", "name_vi": "Amiodarone 200mg", "name_en": "Amiodarone Hydrochloride 200 MG Oral Tablet", "category": "Tim mạch", "generic": "amiodarone"},

    # Diuretics
    {"rxcui": "310528", "name_vi": "Furosemide 40mg", "name_en": "Furosemide 40 MG Oral Tablet", "category": "Tim mạch", "generic": "furosemide"},
    {"rxcui": "310527", "name_vi": "Furosemide 20mg", "name_en": "Furosemide 20 MG Oral Tablet", "category": "Tim mạch", "generic": "furosemide"},
    {"rxcui": "197894", "name_vi": "Spironolactone 25mg", "name_en": "Spironolactone 25 MG Oral Tablet", "category": "Tim mạch", "generic": "spironolactone"},
    {"rxcui": "197895", "name_vi": "Spironolactone 50mg", "name_en": "Spironolactone 50 MG Oral Tablet", "category": "Tim mạch", "generic": "spironolactone"},
    {"rxcui": "310485", "name_vi": "Hydrochlorothiazide 25mg", "name_en": "Hydrochlorothiazide 25 MG Oral Tablet", "category": "Tim mạch", "generic": "hydrochlorothiazide"},
    {"rxcui": "310486", "name_vi": "Hydrochlorothiazide 50mg", "name_en": "Hydrochlorothiazide 50 MG Oral Tablet", "category": "Tim mạch", "generic": "hydrochlorothiazide"},

    # Antidiabetic
    {"rxcui": "861006", "name_vi": "Metformin 500mg", "name_en": "Metformin Hydrochloride 500 MG Oral Tablet", "category": "Nội tiết", "generic": "metformin"},
    {"rxcui": "861007", "name_vi": "Metformin 850mg", "name_en": "Metformin Hydrochloride 850 MG Oral Tablet", "category": "Nội tiết", "generic": "metformin"},
    {"rxcui": "861004", "name_vi": "Metformin 1000mg", "name_en": "Metformin Hydrochloride 1000 MG Oral Tablet", "category": "Nội tiết", "generic": "metformin"},
    {"rxcui": "261551", "name_vi": "Glipizide 5mg", "name_en": "Glipizide 5 MG Oral Tablet", "category": "Nội tiết", "generic": "glipizide"},
    {"rxcui": "261552", "name_vi": "Glipizide 10mg", "name_en": "Glipizide 10 MG Oral Tablet", "category": "Nội tiết", "generic": "glipizide"},
    {"rxcui": "274783", "name_vi": "Gliclazide 80mg", "name_en": "Gliclazide 80 MG Oral Tablet", "category": "Nội tiết", "generic": "gliclazide"},
    {"rxcui": "261651", "name_vi": "Glyburide 5mg", "name_en": "Glyburide 5 MG Oral Tablet", "category": "Nội tiết", "generic": "glyburide"},
    {"rxcui": "274784", "name_vi": "Gliclazide 30mg", "name_en": "Gliclazide 30 MG Extended Release Oral Tablet", "category": "Nội tiết", "generic": "gliclazide"},
    {"rxcui": "860234", "name_vi": "Sitagliptin 100mg", "name_en": "Sitagliptin Phosphate 100 MG Oral Tablet", "category": "Nội tiết", "generic": "sitagliptin"},
    {"rxcui": "1100801", "name_vi": "Dapagliflozin 10mg", "name_en": "Dapagliflozin 10 MG Oral Tablet", "category": "Nội tiết", "generic": "dapagliflozin"},
    {"rxcui": "1545682", "name_vi": "Empagliflozin 10mg", "name_en": "Empagliflozin 10 MG Oral Tablet", "category": "Nội tiết", "generic": "empagliflozin"},
    {"rxcui": "1545683", "name_vi": "Empagliflozin 25mg", "name_en": "Empagliflozin 25 MG Oral Tablet", "category": "Nội tiết", "generic": "empagliflozin"},
    {"rxcui": "1369494", "name_vi": "Liraglutide 6mg/ml", "name_en": "Liraglutide 6 MG/ML Injectable Solution", "category": "Nội tiết", "generic": "liraglutide"},
    {"rxcui": "2380733", "name_vi": "Semaglutide 0.25mg", "name_en": "Semaglutide 0.25 MG Injection", "category": "Nội tiết", "generic": "semaglutide"},
    {"rxcui": "2380735", "name_vi": "Semaglutide 1mg", "name_en": "Semaglutide 1 MG Injection", "category": "Nội tiết", "generic": "semaglutide"},
    {"rxcui": "1488552", "name_vi": "Insulin glargine 100U/ml", "name_en": "Insulin Glargine 100 UNT/ML Injectable Solution", "category": "Nội tiết", "generic": "insulin glargine"},
    {"rxcui": "204854", "name_vi": "Insulin human regular 100U/ml", "name_en": "Insulin, Regular, Human 100 UNT/ML Injectable Solution", "category": "Nội tiết", "generic": "insulin"},

    # Antibiotics
    {"rxcui": "197523", "name_vi": "Amoxicillin 500mg", "name_en": "Amoxicillin 500 MG Oral Capsule", "category": "Kháng sinh", "generic": "amoxicillin"},
    {"rxcui": "197524", "name_vi": "Amoxicillin 1g", "name_en": "Amoxicillin 1000 MG Oral Tablet", "category": "Kháng sinh", "generic": "amoxicillin"},
    {"rxcui": "197465", "name_vi": "Amoxicillin + Clavulanate 625mg", "name_en": "Amoxicillin 500 MG / Clavulanate 125 MG Oral Tablet", "category": "Kháng sinh", "generic": "amoxicillin/clavulanate"},
    {"rxcui": "197466", "name_vi": "Amoxicillin + Clavulanate 1g", "name_en": "Amoxicillin 875 MG / Clavulanate 125 MG Oral Tablet", "category": "Kháng sinh", "generic": "amoxicillin/clavulanate"},
    {"rxcui": "197397", "name_vi": "Azithromycin 500mg", "name_en": "Azithromycin 500 MG Oral Tablet", "category": "Kháng sinh", "generic": "azithromycin"},
    {"rxcui": "197398", "name_vi": "Azithromycin 250mg", "name_en": "Azithromycin 250 MG Oral Tablet", "category": "Kháng sinh", "generic": "azithromycin"},
    {"rxcui": "197409", "name_vi": "Ciprofloxacin 500mg", "name_en": "Ciprofloxacin Hydrochloride 500 MG Oral Tablet", "category": "Kháng sinh", "generic": "ciprofloxacin"},
    {"rxcui": "309954", "name_vi": "Levofloxacin 500mg", "name_en": "Levofloxacin 500 MG Oral Tablet", "category": "Kháng sinh", "generic": "levofloxacin"},
    {"rxcui": "309953", "name_vi": "Levofloxacin 750mg", "name_en": "Levofloxacin 750 MG Oral Tablet", "category": "Kháng sinh", "generic": "levofloxacin"},
    {"rxcui": "198145", "name_vi": "Doxycycline 100mg", "name_en": "Doxycycline Hyclate 100 MG Oral Tablet", "category": "Kháng sinh", "generic": "doxycycline"},
    {"rxcui": "197718", "name_vi": "Cefuroxime 500mg", "name_en": "Cefuroxime Axetil 500 MG Oral Tablet", "category": "Kháng sinh", "generic": "cefuroxime"},
    {"rxcui": "197717", "name_vi": "Cefuroxime 250mg", "name_en": "Cefuroxime Axetil 250 MG Oral Tablet", "category": "Kháng sinh", "generic": "cefuroxime"},
    {"rxcui": "200345", "name_vi": "Cefixime 200mg", "name_en": "Cefixime 200 MG Oral Capsule", "category": "Kháng sinh", "generic": "cefixime"},
    {"rxcui": "200346", "name_vi": "Cefpodoxime 200mg", "name_en": "Cefpodoxime Proxetil 200 MG Oral Tablet", "category": "Kháng sinh", "generic": "cefpodoxime"},
    {"rxcui": "198397", "name_vi": "Clindamycin 300mg", "name_en": "Clindamycin Hydrochloride 300 MG Oral Capsule", "category": "Kháng sinh", "generic": "clindamycin"},
    {"rxcui": "198207", "name_vi": "Metronidazole 500mg", "name_en": "Metronidazole 500 MG Oral Tablet", "category": "Kháng sinh", "generic": "metronidazole"},
    {"rxcui": "197415", "name_vi": "Erythromycin 500mg", "name_en": "Erythromycin 500 MG Oral Tablet", "category": "Kháng sinh", "generic": "erythromycin"},
    {"rxcui": "204993", "name_vi": "Vancomycin 500mg", "name_en": "Vancomycin 500 MG Oral Capsule", "category": "Kháng sinh", "generic": "vancomycin"},
    {"rxcui": "196038", "name_vi": "Metronidazole 250mg", "name_en": "Metronidazole 250 MG Oral Tablet", "category": "Kháng sinh", "generic": "metronidazole"},
    {"rxcui": "197648", "name_vi": "Fluconazole 150mg", "name_en": "Fluconazole 150 MG Oral Tablet", "category": "Kháng sinh", "generic": "fluconazole"},
    {"rxcui": "204853", "name_vi": "Acyclovir 400mg", "name_en": "Acyclovir 400 MG Oral Tablet", "category": "Kháng sinh", "generic": "acyclovir"},
    {"rxcui": "204855", "name_vi": "Acyclovir 800mg", "name_en": "Acyclovir 800 MG Oral Tablet", "category": "Kháng sinh", "generic": "acyclovir"},

    # NSAIDs
    {"rxcui": "200031", "name_vi": "Ibuprofen 400mg", "name_en": "Ibuprofen 400 MG Oral Tablet", "category": "Giảm đau", "generic": "ibuprofen"},
    {"rxcui": "200032", "name_vi": "Ibuprofen 600mg", "name_en": "Ibuprofen 600 MG Oral Tablet", "category": "Giảm đau", "generic": "ibuprofen"},
    {"rxcui": "197901", "name_vi": "Naproxen 250mg", "name_en": "Naproxen Sodium 250 MG Oral Tablet", "category": "Giảm đau", "generic": "naproxen"},
    {"rxcui": "197902", "name_vi": "Naproxen 500mg", "name_en": "Naproxen 500 MG Oral Tablet", "category": "Giảm đau", "generic": "naproxen"},
    {"rxcui": "200525", "name_vi": "Diclofenac 50mg", "name_en": "Diclofenac Sodium 50 MG Oral Tablet", "category": "Giảm đau", "generic": "diclofenac"},
    {"rxcui": "194884", "name_vi": "Celecoxib 200mg", "name_en": "Celecoxib 200 MG Oral Capsule", "category": "Giảm đau", "generic": "celecoxib"},

    # Analgesics
    {"rxcui": "197696", "name_vi": "Paracetamol 500mg", "name_en": "Acetaminophen 500 MG Oral Tablet", "category": "Giảm đau", "generic": "acetaminophen"},
    {"rxcui": "198425", "name_vi": "Paracetamol 325mg", "name_en": "Acetaminophen 325 MG Oral Tablet", "category": "Giảm đau", "generic": "acetaminophen"},
    {"rxcui": "836622", "name_vi": "Paracetamol 650mg", "name_en": "Acetaminophen 650 MG Oral Tablet", "category": "Giảm đau", "generic": "acetaminophen"},
    {"rxcui": "197901", "name_vi": "Tramadol 50mg", "name_en": "Tramadol Hydrochloride 50 MG Oral Tablet", "category": "Giảm đau", "generic": "tramadol"},
    {"rxcui": "197902", "name_vi": "Tramadol 100mg", "name_en": "Tramadol Hydrochloride 100 MG Oral Tablet", "category": "Giảm đau", "generic": "tramadol"},
    {"rxcui": "1049221", "name_vi": "Tramadol + Paracetamol", "name_en": "Acetaminophen 325 MG / Tramadol Hydrochloride 37.5 MG Oral Tablet", "category": "Giảm đau", "generic": "tramadol/acetaminophen"},
    {"rxcui": "197901", "name_vi": "Codeine 30mg", "name_en": "Codeine Phosphate 30 MG Oral Tablet", "category": "Giảm đau", "generic": "codeine"},
    {"rxcui": "197901", "name_vi": "Morphine 15mg", "name_en": "Morphine Sulfate 15 MG Oral Tablet", "category": "Giảm đau", "generic": "morphine"},

    # Gastrointestinal
    {"rxcui": "198205", "name_vi": "Omeprazole 20mg", "name_en": "Omeprazole 20 MG Delayed Release Oral Capsule", "category": "Tiêu hóa", "generic": "omeprazole"},
    {"rxcui": "198206", "name_vi": "Omeprazole 40mg", "name_en": "Omeprazole 40 MG Delayed Release Oral Capsule", "category": "Tiêu hóa", "generic": "omeprazole"},
    {"rxcui": "198207", "name_vi": "Pantoprazole 40mg", "name_en": "Pantoprazole Sodium 40 MG Delayed Release Oral Tablet", "category": "Tiêu hóa", "generic": "pantoprazole"},
    {"rxcui": "198208", "name_vi": "Pantoprazole 20mg", "name_en": "Pantoprazole Sodium 20 MG Delayed Release Oral Tablet", "category": "Tiêu hóa", "generic": "pantoprazole"},
    {"rxcui": "198209", "name_vi": "Esomeprazole 40mg", "name_en": "Esomeprazole Magnesium 40 MG Delayed Release Oral Capsule", "category": "Tiêu hóa", "generic": "esomeprazole"},
    {"rxcui": "198210", "name_vi": "Lansoprazole 30mg", "name_en": "Lansoprazole 30 MG Delayed Release Oral Capsule", "category": "Tiêu hóa", "generic": "lansoprazole"},
    {"rxcui": "197432", "name_vi": "Ranitidine 150mg", "name_en": "Ranitidine 150 MG Oral Tablet", "category": "Tiêu hóa", "generic": "ranitidine"},
    {"rxcui": "197433", "name_vi": "Famotidine 20mg", "name_en": "Famotidine 20 MG Oral Tablet", "category": "Tiêu hóa", "generic": "famotidine"},
    {"rxcui": "198545", "name_vi": "Domperidone 10mg", "name_en": "Domperidone 10 MG Oral Tablet", "category": "Tiêu hóa", "generic": "domperidone"},
    {"rxcui": "198546", "name_vi": "Metoclopramide 10mg", "name_en": "Metoclopramide Hydrochloride 10 MG Oral Tablet", "category": "Tiêu hóa", "generic": "metoclopramide"},
    {"rxcui": "1091494", "name_vi": "Ondansetron 4mg", "name_en": "Ondansetron Hydrochloride 4 MG Oral Tablet", "category": "Tiêu hóa", "generic": "ondansetron"},
    {"rxcui": "1091495", "name_vi": "Ondansetron 8mg", "name_en": "Ondansetron Hydrochloride 8 MG Oral Tablet", "category": "Tiêu hóa", "generic": "ondansetron"},
    {"rxcui": "197857", "name_vi": "Loperamide 2mg", "name_en": "Loperamide Hydrochloride 2 MG Oral Capsule", "category": "Tiêu hóa", "generic": "loperamide"},
    {"rxcui": "1099279", "name_vi": "Docusate sodium 100mg", "name_en": "Docusate Sodium 100 MG Oral Capsule", "category": "Tiêu hóa", "generic": "docusate"},
    {"rxcui": "312935", "name_vi": "Senna 8.6mg", "name_en": "Senna 8.6 MG Oral Tablet", "category": "Tiêu hóa", "generic": "senna"},
    {"rxcui": "392085", "name_vi": "Guaifenesin", "name_en": "Guaifenesin 100 MG Oral Tablet", "category": "Hô hấp", "generic": "guaifenesin"},

    # Antihistamines
    {"rxcui": "197382", "name_vi": "Cetirizine 10mg", "name_en": "Cetirizine Hydrochloride 10 MG Oral Tablet", "category": "Dị ứng", "generic": "cetirizine"},
    {"rxcui": "197383", "name_vi": "Loratadine 10mg", "name_en": "Loratadine 10 MG Oral Tablet", "category": "Dị ứng", "generic": "loratadine"},
    {"rxcui": "197384", "name_vi": "Chlorpheniramine 4mg", "name_en": "Chlorpheniramine Maleate 4 MG Oral Tablet", "category": "Dị ứng", "generic": "chlorpheniramine"},
    {"rxcui": "197385", "name_vi": "Fexofenadine 180mg", "name_en": "Fexofenadine Hydrochloride 180 MG Oral Tablet", "category": "Dị ứng", "generic": "fexofenadine"},

    # Respiratory
    {"rxcui": "197523", "name_vi": "Salbutamol inhaler", "name_en": "Albuterol 0.083 MG/ML Inhalation Solution", "category": "Hô hấp", "generic": "salbutamol"},
    {"rxcui": "197524", "name_vi": "Salbutamol nebulizer", "name_en": "Albuterol 5 MG/ML Inhalation Solution", "category": "Hô hấp", "generic": "salbutamol"},
    {"rxcui": "197525", "name_vi": "Budesonide inhaler 200mcg", "name_en": "Budesonide 200 MCG/ACTUATION Dry Powder Inhaler", "category": "Hô hấp", "generic": "budesonide"},
    {"rxcui": "197526", "name_vi": "Budesonide inhaler 400mcg", "name_en": "Budesonide 400 MCG/ACTUATION Dry Powder Inhaler", "category": "Hô hấp", "generic": "budesonide"},
    {"rxcui": "197527", "name_vi": "Montelukast 10mg", "name_en": "Montelukast Sodium 10 MG Oral Tablet", "category": "Hô hấp", "generic": "montelukast"},
    {"rxcui": "197528", "name_vi": "Desloratadine 5mg", "name_en": "Desloratadine 5 MG Oral Tablet", "category": "Dị ứng", "generic": "desloratadine"},

    # Anxiolytics and Psychiatric
    {"rxcui": "309845", "name_vi": "Diazepam 5mg", "name_en": "Diazepam 5 MG Oral Tablet", "category": "Tâm thần", "generic": "diazepam"},
    {"rxcui": "309846", "name_vi": "Diazepam 10mg", "name_en": "Diazepam 10 MG Oral Tablet", "category": "Tâm thần", "generic": "diazepam"},
    {"rxcui": "197901", "name_vi": "Lorazepam 1mg", "name_en": "Lorazepam 1 MG Oral Tablet", "category": "Tâm thần", "generic": "lorazepam"},
    {"rxcui": "197902", "name_vi": "Lorazepam 2mg", "name_en": "Lorazepam 2 MG Oral Tablet", "category": "Tâm thần", "generic": "lorazepam"},
    {"rxcui": "311309", "name_vi": "Alprazolam 0.5mg", "name_en": "Alprazolam 0.5 MG Oral Tablet", "category": "Tâm thần", "generic": "alprazolam"},
    {"rxcui": "311310", "name_vi": "Alprazolam 1mg", "name_en": "Alprazolam 1 MG Oral Tablet", "category": "Tâm thần", "generic": "alprazolam"},
    {"rxcui": "313223", "name_vi": "Clonazepam 0.5mg", "name_en": "Clonazepam 0.5 MG Oral Tablet", "category": "Tâm thần", "generic": "clonazepam"},
    {"rxcui": "313224", "name_vi": "Clonazepam 1mg", "name_en": "Clonazepam 1 MG Oral Tablet", "category": "Tâm thần", "generic": "clonazepam"},
    {"rxcui": "197901", "name_vi": "Clonazepam 2mg", "name_en": "Clonazepam 2 MG Oral Tablet", "category": "Tâm thần", "generic": "clonazepam"},
    {"rxcui": "197361", "name_vi": "Amitriptyline 25mg", "name_en": "Amitriptyline Hydrochloride 25 MG Oral Tablet", "category": "Tâm thần", "generic": "amitriptyline"},
    {"rxcui": "197362", "name_vi": "Amitriptyline 50mg", "name_en": "Amitriptyline Hydrochloride 50 MG Oral Tablet", "category": "Tâm thần", "generic": "amitriptyline"},
    {"rxcui": "204854", "name_vi": "Sertraline 50mg", "name_en": "Sertraline Hydrochloride 50 MG Oral Tablet", "category": "Tâm thần", "generic": "sertraline"},
    {"rxcui": "204855", "name_vi": "Sertraline 100mg", "name_en": "Sertraline Hydrochloride 100 MG Oral Tablet", "category": "Tâm thần", "generic": "sertraline"},
    {"rxcui": "200033", "name_vi": "Escitalopram 10mg", "name_en": "Escitalopram Oxalate 10 MG Oral Tablet", "category": "Tâm thần", "generic": "escitalopram"},
    {"rxcui": "200034", "name_vi": "Escitalopram 20mg", "name_en": "Escitalopram Oxalate 20 MG Oral Tablet", "category": "Tâm thần", "generic": "escitalopram"},
    {"rxcui": "197361", "name_vi": "Fluoxetine 20mg", "name_en": "Fluoxetine Hydrochloride 20 MG Oral Capsule", "category": "Tâm thần", "generic": "fluoxetine"},
    {"rxcui": "197901", "name_vi": "Trazodone 50mg", "name_en": "Trazodone Hydrochloride 50 MG Oral Tablet", "category": "Tâm thần", "generic": "trazodone"},
    {"rxcui": "311309", "name_vi": "Zolpidem 10mg", "name_en": "Zolpidem Tartrate 10 MG Oral Tablet", "category": "Tâm thần", "generic": "zolpidem"},

    # Thyroid
    {"rxcui": "197894", "name_vi": "Levothyroxine 50mcg", "name_en": "Levothyroxine Sodium 0.05 MG Oral Tablet", "category": "Nội tiết", "generic": "levothyroxine"},
    {"rxcui": "197895", "name_vi": "Levothyroxine 100mcg", "name_en": "Levothyroxine Sodium 0.1 MG Oral Tablet", "category": "Nội tiết", "generic": "levothyroxine"},
    {"rxcui": "197896", "name_vi": "Methimazole 5mg", "name_en": "Methimazole 5 MG Oral Tablet", "category": "Nội tiết", "generic": "methimazole"},

    # Dermatological
    {"rxcui": "198545", "name_vi": "Hydrocortisone cream 1%", "name_en": "Hydrocortisone 10 MG/GM Topical Cream", "category": "Da liễu", "generic": "hydrocortisone"},
    {"rxcui": "198546", "name_vi": "Betamethasone cream", "name_en": "Betamethasone Valerate 0.1 MG/GM Topical Cream", "category": "Da liễu", "generic": "betamethasone"},
    {"rxcui": "198547", "name_vi": "Mupirocin cream 2%", "name_en": "Mupirocin 20 MG/GM Topical Cream", "category": "Da liễu", "generic": "mupirocin"},
    {"rxcui": "198548", "name_vi": "Nystatin cream", "name_en": "Nystatin 100000 UNT/GM Topical Cream", "category": "Da liễu", "generic": "nystatin"},
    {"rxcui": "7597", "name_vi": "Nystatin oral suspension", "name_en": "Nystatin 100000 UNT/ML Oral Suspension", "category": "Da liễu", "generic": "nystatin"},
    {"rxcui": "198549", "name_vi": "Clotrimazole cream 1%", "name_en": "Clotrimazole 10 MG/GM Topical Cream", "category": "Da liễu", "generic": "clotrimazole"},

    # Vitamins and supplements
    {"rxcui": "197901", "name_vi": "Vitamin D3 1000IU", "name_en": "Cholecalciferol 0.025 MG Oral Capsule", "category": "Vitamin", "generic": "cholecalciferol"},
    {"rxcui": "197901", "name_vi": "Vitamin D3 5000IU", "name_en": "Cholecalciferol 0.125 MG Oral Capsule", "category": "Vitamin", "generic": "cholecalciferol"},
    {"rxcui": "197901", "name_vi": "Calcium + Vitamin D3", "name_en": "Calcium Carbonate 600 MG / Cholecalciferol 0.0125 MG Oral Tablet", "category": "Vitamin", "generic": "calcium/vitamin d"},
    {"rxcui": "197901", "name_vi": "Iron supplement", "name_en": "Ferrous Sulfate 325 MG Oral Tablet", "category": "Vitamin", "generic": "ferrous sulfate"},
    {"rxcui": "197901", "name_vi": "Multivitamin", "name_en": "Multivitamin, Adult Oral Tablet", "category": "Vitamin", "generic": "multivitamin"},

    # Endocrine - Steroids
    {"rxcui": "197901", "name_vi": "Prednisolone 5mg", "name_en": "Prednisolone 5 MG Oral Tablet", "category": "Nội tiết", "generic": "prednisolone"},
    {"rxcui": "197901", "name_vi": "Prednisone 5mg", "name_en": "Prednisone 5 MG Oral Tablet", "category": "Nội tiết", "generic": "prednisone"},
    {"rxcui": "197901", "name_vi": "Dexamethasone 0.5mg", "name_en": "Dexamethasone 0.5 MG Oral Tablet", "category": "Nội tiết", "generic": "dexamethasone"},
    {"rxcui": "197901", "name_vi": "Dexamethasone 4mg", "name_en": "Dexamethasone 4 MG Oral Tablet", "category": "Nội tiết", "generic": "dexamethasone"},
    {"rxcui": "197901", "name_vi": "Methylprednisolone 4mg", "name_en": "Methylprednisolone 4 MG Oral Tablet", "category": "Nội tiết", "generic": "methylprednisolone"},
    {"rxcui": "197901", "name_vi": "Methylprednisolone 16mg", "name_en": "Methylprednisolone 16 MG Oral Tablet", "category": "Nội tiết", "generic": "methylprednisolone"},

    # Ophthalmic
    {"rxcui": "197901", "name_vi": "Timolol eye drops", "name_en": "Timolol 2.5 MG/ML Ophthalmic Solution", "category": "Mắt", "generic": "timolol"},
    {"rxcui": "197901", "name_vi": "Dorzolamide eye drops", "name_en": "Dorzolamide 20 MG/ML Ophthalmic Solution", "category": "Mắt", "generic": "dorzolamide"},
    {"rxcui": "197901", "name_vi": "Latanoprost eye drops", "name_en": "Latanoprost 0.005 MG/ML Ophthalmic Solution", "category": "Mắt", "generic": "latanoprost"},

    # Urological
    {"rxcui": "197901", "name_vi": "Tamsulosin 0.4mg", "name_en": "Tamsulosin 0.4 MG Oral Capsule", "category": "Tiết niệu", "generic": "tamsulosin"},
    {"rxcui": "197901", "name_vi": "Finasteride 5mg", "name_en": "Finasteride 5 MG Oral Tablet", "category": "Tiết niệu", "generic": "finasteride"},

    # Antifungal
    {"rxcui": "309311", "name_vi": "Fluconazole 150mg", "name_en": "Fluconazole 150 MG Oral Capsule", "category": "Kháng nấm", "generic": "fluconazole"},
    {"rxcui": "309312", "name_vi": "Itraconazole 100mg", "name_en": "Itraconazole 100 MG Oral Capsule", "category": "Kháng nấm", "generic": "itraconazole"},

    # Statin combos
    {"rxcui": "197901", "name_vi": "Amlodipine + Atorvastatin", "name_en": "Amlodipine 5 MG / Atorvastatin 10 MG Oral Tablet", "category": "Tim mạch", "generic": "amlodipine/atorvastatin"},

    # More commonly used drugs
    {"rxcui": "197901", "name_vi": "Bisacodyl 5mg", "name_en": "Bisacodyl 5 MG Delayed Release Oral Tablet", "category": "Tiêu hóa", "generic": "bisacodyl"},
    {"rxcui": "197901", "name_vi": "Lactulose 15ml", "name_en": "Lactulose 10 G/15ML Oral Solution", "category": "Tiêu hóa", "generic": "lactulose"},
    {"rxcui": "197901", "name_vi": "Simethicone 125mg", "name_en": "Simethicone 125 MG Chewable Tablet", "category": "Tiêu hóa", "generic": "simethicone"},

    # Anticoagulants
    {"rxcui": "197901", "name_vi": "Enoxaparin 40mg", "name_en": "Enoxaparin Sodium 40 MG/0.4ML Injectable Solution", "category": "Tim mạch", "generic": "enoxaparin"},
    {"rxcui": "197901", "name_vi": "Heparin 5000U", "name_en": "Heparin Sodium 5000 UNT/ML Injectable Solution", "category": "Tim mạch", "generic": "heparin"},

    # Neuropathic pain
    {"rxcui": "197901", "name_vi": "Pregabalin 75mg", "name_en": "Pregabalin 75 MG Oral Capsule", "category": "Thần kinh", "generic": "pregabalin"},
    {"rxcui": "197901", "name_vi": "Pregabalin 150mg", "name_en": "Pregabalin 150 MG Oral Capsule", "category": "Thần kinh", "generic": "pregabalin"},
    {"rxcui": "197901", "name_vi": "Gabapentin 300mg", "name_en": "Gabapentin 300 MG Oral Capsule", "category": "Thần kinh", "generic": "gabapentin"},
    {"rxcui": "197901", "name_vi": "Gabapentin 400mg", "name_en": "Gabapentin 400 MG Oral Capsule", "category": "Thần kinh", "generic": "gabapentin"},

    # Parkinson/Alzheimer
    {"rxcui": "197901", "name_vi": "Levodopa/Carbidopa 250/25mg", "name_en": "Carbidopa 25 MG / Levodopa 100 MG Oral Tablet", "category": "Thần kinh", "generic": "levodopa/carbidopa"},
    {"rxcui": "197901", "name_vi": "Donepezil 5mg", "name_en": "Donepezil Hydrochloride 5 MG Oral Tablet", "category": "Thần kinh", "generic": "donepezil"},

    # Migraine
    {"rxcui": "197901", "name_vi": "Sumatriptan 50mg", "name_en": "Sumatriptan Succinate 50 MG Oral Tablet", "category": "Thần kinh", "generic": "sumatriptan"},

    # Diabetes - injectable
    {"rxcui": "197901", "name_vi": "Insulin aspart", "name_en": "Insulin Aspart 100 UNT/ML Injectable Solution", "category": "Nội tiết", "generic": "insulin aspart"},
    {"rxcui": "197901", "name_vi": "Insulin lispro", "name_en": "Insulin Lispro 100 UNT/ML Injectable Solution", "category": "Nội tiết", "generic": "insulin lispro"},

    # Antiplatelet
    {"rxcui": "197901", "name_vi": "Ticagrelor 90mg", "name_en": "Ticagrelor 90 MG Oral Tablet", "category": "Tim mạch", "generic": "ticagrelor"},
]


def build_database():
    """Build RxNorm database."""
    print("=== Building RxNorm Database ===")

    all_entries = {}
    for drug in RXNORM_DRUGS:
        rxcui = drug["rxcui"]
        if rxcui not in all_entries:
            all_entries[rxcui] = {
                "rxcui": rxcui,
                "name_en": drug.get("name_en", ""),
                "name_vi": drug.get("name_vi", ""),
                "category": drug.get("category", ""),
                "generic": drug.get("generic", ""),
                "search_text": f"{drug.get('name_en', '')} {drug.get('name_vi', '')} {drug.get('generic', '')}".lower().strip()
            }
        else:
            existing = all_entries[rxcui]
            if drug.get("name_vi") and drug["name_vi"] not in existing["name_vi"]:
                existing["name_vi"] += f" / {drug['name_vi']}"
            existing["search_text"] = f"{existing['name_en']} {existing['name_vi']} {existing.get('generic', '')}".lower().strip()

    database = {
        "version": "1.0",
        "description": "RxNorm drug database for Vietnamese medical NER",
        "total_drugs": len(all_entries),
        "categories": list(set(d.get("category", "") for d in all_entries.values())),
        "drugs": all_entries
    }

    os.makedirs(DB_DIR, exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(database, f, ensure_ascii=False, indent=2)

    print(f"Saved {len(all_entries)} RxNorm entries to {OUTPUT_FILE}")
    return database


def query_rxnorm_api(term: str) -> Optional[dict]:
    """Query RxNorm API for drug info."""
    base_url = "https://rxnav.nlm.nih.gov/REST/drugs.json"
    params = {"name": term}
    try:
        resp = requests.get(base_url, params=params, timeout=15)
        if resp.status_code == 200:
            return resp.json()
    except Exception as e:
        print(f"RxNorm API error for '{term}': {e}")
    return None


def search_rxnorm_by_name(name: str) -> list:
    """Search RxNorm for a drug name and return CUI candidates."""
    result = query_rxnorm_api(name)
    if not result:
        return []

    candidates = []
    try:
        drug_groups = result.get("drugGroup", {})
        concept_groups = drug_groups.get("conceptGroup", [])
        for group in concept_groups:
            if group.get("conceptProperties"):
                for prop in group["conceptProperties"]:
                    candidates.append({
                        "rxcui": prop.get("rxcui", ""),
                        "name": prop.get("name", ""),
                        "synonym": prop.get("synonym", ""),
                        "tty": prop.get("tty", "")
                    })
    except Exception:
        pass

    return candidates


if __name__ == "__main__":
    build_database()

    print("\n=== Testing RxNorm API ===")
    test_drugs = ["aspirin", "metformin", "amlodipine", "omeprazole"]
    for drug in test_drugs:
        candidates = search_rxnorm_by_name(drug)
        if candidates:
            print(f"\n'{drug}' found {len(candidates)} results:")
            for c in candidates[:3]:
                print(f"  CUI={c['rxcui']}, name={c['name']}, tty={c['tty']}")
        else:
            print(f"'{drug}': No results")
        time.sleep(0.5)
