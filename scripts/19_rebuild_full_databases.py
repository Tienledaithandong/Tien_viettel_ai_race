"""
Script 19: Rebuild Full ICD-10 and RxNorm Databases from source files
- ICD-10: Parse icd102019en.xml (ClaML format)
- RxNorm: Parse RRF files (RXNCONSO.RRF, RXNREL.RRF)
- Then rebuild FAISS indexes
"""
import json
import os
import xml.etree.ElementTree as ET
from typing import Dict, List, Set

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ICD10_XML = os.path.join(PROJECT_ROOT, "databases", "icd10_vn", "icd102019en.xml")
ICD10_DB = os.path.join(PROJECT_ROOT, "databases", "icd10_vn", "icd10_database.json")
RXNORM_RRF = os.path.join(PROJECT_ROOT, "databases", "rxnorm", "rrf")
RXNORM_PRESCRIBE_RRF = os.path.join(PROJECT_ROOT, "databases", "rxnorm", "prescribe", "rrf")
RXNORM_DB = os.path.join(PROJECT_ROOT, "databases", "rxnorm", "rxnorm_database.json")

# ICD-10 chapter mapping for Vietnamese categories
ICD10_CHAPTERS = {
    "I": "Nhiễm trùng", "II": "Khối u", "III": "Máu",
    "IV": "Nội tiết", "V": "Tâm thần", "VI": "Thần kinh",
    "VII": "Mắt", "VIII": "Tai", "IX": "Tim mạch",
    "X": "Hô hấp", "XI": "Tiêu hóa", "XII": "Da liễu",
    "XIII": "Cơ xương khớp", "XIV": "Tiết niệu", "XV": "Sản khoa",
    "XVI": "Sơ sinh", "XVII": "Dị tật", "XVIII": "Triệu chứng",
    "XIX": "Chấn thương", "XX": "Ngộc độc", "XXI": "Khác",
    "XXII": "Kiểm tra",
}


def get_icd10_category(code: str) -> str:
    """Map ICD-10 code to Vietnamese category."""
    first = code[0].upper() if code else ""
    letter_groups = {
        "A": "Nhiễm trùng", "B": "Nhiễm trùng",
        "C": "Khối u", "D": "Máu",
        "E": "Nội tiết", "F": "Tâm thần",
        "G": "Thần kinh", "H": "Mắt/Tai",
        "I": "Tim mạch", "J": "Hô hấp",
        "K": "Tiêu hóa", "L": "Da liễu",
        "M": "Cơ xương khớp", "N": "Tiết niệu",
        "O": "Sản khoa", "P": "Sơ sinh",
        "Q": "Dị tật", "R": "Triệu chứng",
        "S": "Chấn thương", "T": "Chấn thương",
        "V": "Ngộc độc", "W": "Ngộc độc",
        "X": "Ngộc độc", "Y": "Ngộc độc",
        "Z": "Kiểm tra",
    }
    return letter_groups.get(first, "Khác")


def parse_icd10_xml():
    """Parse ICD-10 XML (ClaML format) and extract all category codes."""
    print("=== Parsing ICD-10 XML ===")
    tree = ET.parse(ICD10_XML)
    root = tree.getroot()

    entries = {}
    for cls in root.findall(".//Class"):
        kind = cls.get("kind", "")
        if kind != "category":
            continue

        code = cls.get("code", "")
        if not code:
            continue

        # Get preferred name
        name = ""
        for rubric in cls.findall("Rubric"):
            if rubric.get("kind") in ("preferred", "preferredLong"):
                label = rubric.find("Label")
                if label is not None:
                    name = "".join(label.itertext()).strip()
                if name:
                    break

        # Also get inclusion terms as additional names
        inclusion_names = []
        for rubric in cls.findall("Rubric"):
            if rubric.get("kind") == "inclusion":
                label = rubric.find("Label")
                if label is not None:
                    inc_name = "".join(label.itertext()).strip()
                    if inc_name and inc_name != name:
                        inclusion_names.append(inc_name)

        if code not in entries:
            entries[code] = {
                "code": code,
                "name_en": name,
                "name_vi": "",
                "category": get_icd10_category(code),
                "inclusions": inclusion_names[:5],
            }

    print(f"  Extracted {len(entries)} ICD-10 category codes from XML")
    return entries


def merge_icd10_databases():
    """Merge XML-extracted codes with existing Vietnamese database."""
    print("\n=== Merging ICD-10 databases ===")

    # Load existing DB if present
    existing = {}
    if os.path.exists(ICD10_DB):
        with open(ICD10_DB, "r", encoding="utf-8") as f:
            old_db = json.load(f)
        existing = old_db.get("codes", {})
        print(f"  Existing DB: {len(existing)} codes")

    # Parse XML
    xml_entries = parse_icd10_xml()
    print(f"  XML entries: {len(xml_entries)} codes")

    # Merge: XML provides codes + English names, existing provides Vietnamese names
    merged = {}
    for code, xml_info in xml_entries.items():
        entry = {
            "code": code,
            "name_en": xml_info["name_en"],
            "name_vi": "",
            "category": xml_info["category"],
            "search_text": "",
            "inclusions": xml_info.get("inclusions", []),
        }
        # If we have Vietnamese name from existing DB, use it
        if code in existing:
            entry["name_vi"] = existing[code].get("name_vi", "")
        merged[code] = entry

    # Add codes from existing DB not in XML
    for code, info in existing.items():
        if code not in merged:
            merged[code] = {
                "code": code,
                "name_en": info.get("name_en", ""),
                "name_vi": info.get("name_vi", ""),
                "category": info.get("category", get_icd10_category(code)),
                "search_text": info.get("search_text", ""),
                "inclusions": [],
            }

    # Build search_text
    for code, entry in merged.items():
        parts = [entry["name_en"], entry["name_vi"], code, entry["category"]]
        if entry.get("inclusions"):
            parts.extend(entry["inclusions"][:3])
        entry["search_text"] = " ".join(p for p in parts if p).lower().strip()

    database = {
        "version": "2.0",
        "description": "ICD-10 database for Vietnamese medical NER (full WHO dataset)",
        "total_codes": len(merged),
        "categories": sorted(set(e.get("category", "") for e in merged.values())),
        "codes": merged,
    }

    with open(ICD10_DB, "w", encoding="utf-8") as f:
        json.dump(database, f, ensure_ascii=False, indent=2)

    print(f"  Saved {len(merged)} ICD-10 codes to {ICD10_DB}")
    return database


def parse_rxnorm_rrf():
    """Parse RxNorm RRF files to extract all drugs."""
    print("\n=== Parsing RxNorm RRF files ===")

    # Try prescribe RRF first (newer), then regular RRF
    rrf_dir = RXNORM_PRESCRIBE_RRF if os.path.exists(RXNORM_PRESCRIBE_RRF) else RXNORM_RRF
    conso_path = os.path.join(rrf_dir, "RXNCONSO.RRF")
    rel_path = os.path.join(rrf_dir, "RXNREL.RRF")
    sat_path = os.path.join(rrf_dir, "RXNSAT.RRF")

    print(f"  Using RRF directory: {rrf_dir}")

    # Step 1: Read RXNCONSO.RRF to get all RxNorm concepts
    # Columns: RXCUI|LAT|TS|LUI|STT|SUI|ISPREF|RXAUI|SAUI|SCUI|SDUI|SAB|TTY|CODE|STR|SRL|SUPPRESS|CVF
    concepts = {}  # rxcui -> {name, tty, sab}
    if os.path.exists(conso_path):
        print(f"  Reading {conso_path}...")
        with open(conso_path, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                parts = line.strip().split("|")
                if len(parts) < 16:
                    continue
                rxcui = parts[0].strip()
                sab = parts[11].strip()
                tty = parts[12].strip()
                name = parts[14].strip()

                if sab != "RXNORM":
                    continue

                if rxcui not in concepts:
                    concepts[rxcui] = {"name": name, "tty": tty}
                # Prefer PT (Preferred Term) over SY (Synonym)
                if tty == "PT":
                    concepts[rxcui]["name"] = name
        print(f"  Found {len(concepts)} RxNorm concepts")
    else:
        print(f"  WARNING: {conso_path} not found")

    # Step 2: Read RXNSAT.RRF for additional attributes (ingredients, doses, forms)
    # Columns: RXCUI|LUI|SUI|ATUI|ATN|SAB|ATV|SUPPRESS|CVF
    attributes = {}  # rxcui -> {atn: atv}
    if os.path.exists(sat_path):
        print(f"  Reading {sat_path}...")
        with open(sat_path, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                parts = line.strip().split("|")
                if len(parts) < 8:
                    continue
                rxcui = parts[0].strip()
                sab = parts[5].strip()
                atn = parts[4].strip()
                atv = parts[6].strip()

                if sab != "RXNORM":
                    continue
                if rxcui not in attributes:
                    attributes[rxcui] = {}
                attributes[rxcui][atn] = atv
        print(f"  Found attributes for {len(attributes)} concepts")

    # Step 3: Filter for clinical drug forms (SBD, SCD, BPCK, GPCK)
    # These are the most useful for NER linking
    drug_tty = {"SBD", "SCD", "BPCK", "GPCK", "SBDG", "SCDG"}
    drugs = {}

    for rxcui, info in concepts.items():
        tty = info["tty"]
        name = info["name"]

        # Include clinical drugs and semantic brands
        if tty in drug_tty or tty in {"BN", "IN", "PIN"}:
            attrs = attributes.get(rxcui, {})

            # Extract generic name from ingredient or use the name itself
            generic = attrs.get("RXN_IN", attrs.get("ATC_LEVEL_4", ""))
            if not generic:
                # Try to extract from name (e.g., "Aspirin 325 MG Oral Tablet" -> "aspirin")
                name_lower = name.lower()
                generic = name_lower.split(" ")[0] if name_lower else ""

            # Get ATC code for categorization
            atc = attrs.get("ATC_LEVEL_4", attrs.get("EPC", ""))

            drugs[rxcui] = {
                "rxcui": rxcui,
                "name_en": name,
                "name_vi": "",  # Will be filled if we have Vietnamese mapping
                "generic": generic,
                "category": "",
                "tty": tty,
                "atc": atc,
                "search_text": "",
            }

    print(f"  Filtered to {len(drugs)} clinical drug entries")
    return drugs


def merge_rxnorm_databases():
    """Merge RRF-extracted drugs with existing database."""
    print("\n=== Merging RxNorm databases ===")

    # Load existing DB if present
    existing = {}
    if os.path.exists(RXNORM_DB):
        with open(RXNORM_DB, "r", encoding="utf-8") as f:
            old_db = json.load(f)
        existing = old_db.get("drugs", {})
        print(f"  Existing DB: {len(existing)} entries")

    # Parse RRF
    rrf_drugs = parse_rxnorm_rrf()
    print(f"  RRF entries: {len(rrf_drugs)} drugs")

    # Merge: RRF provides structure, existing provides Vietnamese names + categories
    merged = {}

    # Start with RRF entries
    for rxcui, info in rrf_drugs.items():
        entry = {
            "rxcui": rxcui,
            "name_en": info["name_en"],
            "name_vi": "",
            "generic": info["generic"],
            "category": "",
            "search_text": "",
        }
        # If we have Vietnamese name from existing DB, use it
        if rxcui in existing:
            entry["name_vi"] = existing[rxcui].get("name_vi", "")
            entry["category"] = existing[rxcui].get("category", "")
        merged[rxcui] = entry

    # Add entries from existing DB not in RRF (they might have valid RxNorm CUIs)
    for rxcui, info in existing.items():
        if rxcui not in merged:
            merged[rxcui] = {
                "rxcui": rxcui,
                "name_en": info.get("name_en", ""),
                "name_vi": info.get("name_vi", ""),
                "generic": info.get("generic", ""),
                "category": info.get("category", ""),
                "search_text": info.get("search_text", ""),
            }

    # Build search_text
    for rxcui, entry in merged.items():
        parts = [
            entry["name_en"],
            entry["name_vi"],
            entry["generic"],
            rxcui,
            entry["category"],
        ]
        entry["search_text"] = " ".join(p for p in parts if p).lower().strip()

    database = {
        "version": "2.0",
        "description": "RxNorm drug database for Vietnamese medical NER (full dataset)",
        "total_drugs": len(merged),
        "categories": sorted(set(d.get("category", "") for d in merged.values())),
        "drugs": merged,
    }

    with open(RXNORM_DB, "w", encoding="utf-8") as f:
        json.dump(database, f, ensure_ascii=False, indent=2)

    print(f"  Saved {len(merged)} RxNorm entries to {RXNORM_DB}")
    return database


def build_faiss_indexes():
    """Build FAISS indexes for both databases."""
    print("\n=== Building FAISS indexes ===")
    from src.entity_linking.build_index import build_all_indexes
    build_all_indexes()


if __name__ == "__main__":
    print("=" * 60)
    print("REBUILDING FULL DATABASES")
    print("=" * 60)

    merge_icd10_databases()
    merge_rxnorm_databases()

    print("\n" + "=" * 60)
    print("BUILDING FAISS INDEXES")
    print("=" * 60)

    build_faiss_indexes()

    print("\n" + "=" * 60)
    print("DONE!")
    print("=" * 60)
