import sys, io, json, xml.etree.ElementTree as ET
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

tree = ET.parse('databases/icd10_vn/icd102019en.xml')
root = tree.getroot()

with open('databases/icd10_vn/icd10_database.json', encoding='utf-8') as f:
    db = json.load(f)

existing_codes = set(db.get('codes', {}).keys())
print('Existing ICD-10 codes:', len(existing_codes))

new_entries = []
classes = root.findall('.//Class')

for c in classes:
    code = c.get('code', '')
    kind = c.get('kind', '')
    
    if kind not in ('category', 'subcategory'):
        continue
    
    if code in existing_codes:
        continue
    
    name_en = ''
    synonyms = []
    
    for rubric in c.findall('Rubric'):
        rkind = rubric.get('kind', '')
        label = rubric.find('Label')
        if label is None:
            continue
        
        # Text is direct child text of Label, not in a Text element
        full_text = label.text.strip() if label.text else ''
        
        # Also check for Text children (some entries use that format)
        if not full_text:
            for text_elem in label.findall('Text'):
                if text_elem.text and text_elem.text.strip():
                    full_text = text_elem.text.strip()
                    break
        
        if not full_text:
            continue
            
        if rkind == 'preferred' and not name_en:
            name_en = full_text
        elif rkind == 'inclusion':
            synonyms.append(full_text)
    
    if not name_en:
        continue
    
    entry = {
        'code': code,
        'name_en': name_en,
        'name_vi': name_en,
        'category': '',
        'synonyms': synonyms[:5],
        'search_text': (name_en + ' ' + ' '.join(synonyms[:3])).lower(),
    }
    new_entries.append(entry)

added = 0
for entry in new_entries:
    if entry['code'] not in db['codes']:
        db['codes'][entry['code']] = entry
        added += 1

db['total_codes'] = len(db['codes'])

with open('databases/icd10_vn/icd10_database.json', 'w', encoding='utf-8') as f:
    json.dump(db, f, ensure_ascii=False, indent=2)

print('Added %d new ICD-10 codes. Total: %d' % (added, db['total_codes']))
