"""
Script 02: Build ICD-10 Database (English + Vietnamese mapping)
Sources:
  1. WHO ICD-10 API (icd.who.int)
  2. CMS Medicare ICD-10 files (downloadable CSV)
  3. Vietnamese ICD-10 from Bộ Y Tế (scraped)
Output: databases/icd10_vn/icd10_database.json
"""
import json
import os
import csv
import io
import requests
import time

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_DIR = os.path.join(PROJECT_ROOT, "databases", "icd10_vn")
OUTPUT_FILE = os.path.join(DB_DIR, "icd10_database.json")

# ============================================================
# PART 1: Common ICD-10 codes used in Vietnamese hospitals
# This is a comprehensive pre-built mapping for quick startup
# ============================================================

ICD10_CORE = [
    # A00-B99: Infectious diseases
    {"code": "A09", "name_en": "Infectious gastroenteritis and colitis, unspecified", "name_vi": "Viêm dạ dày ruột nhiễm trùng và viêm đại tràng không xác định", "category": "Nhiễm trùng"},
    {"code": "B34.9", "name_en": "Viral infection, unspecified", "name_vi": "Nhiễm virus không xác định", "category": "Nhiễm trùng"},
    # C00-D49: Neoplasms
    {"code": "C34.90", "name_en": "Malignant neoplasm of unspecified part of bronchus or lung", "name_vi": "Khối u ác tính không xác định của phế quản hoặc phổi", "category": "Khối u"},
    {"code": "C50.919", "name_en": "Malignant neoplasm of unspecified site of unspecified female breast", "name_vi": "Khối u ác tính vú nữ không xác định vị trí", "category": "Khối u"},
    {"code": "C61", "name_en": "Malignant neoplasm of prostate", "name_vi": "Khối u ác tính tuyến tiền liệt", "category": "Khối u"},
    {"code": "D50.9", "name_en": "Iron deficiency anemia, unspecified", "name_vi": "Thiếu máu do thiếu sắt không xác định", "category": "Máu"},
    # E00-E89: Endocrine, nutritional and metabolic diseases
    {"code": "E11.9", "name_en": "Type 2 diabetes mellitus without complications", "name_vi": "Đái tháo đường typ 2 không có biến chứng", "category": "Nội tiết"},
    {"code": "E11.65", "name_en": "Type 2 diabetes mellitus with hyperglycemia", "name_vi": "Đái tháo đường typ 2 với tăng đường huyết", "category": "Nội tiết"},
    {"code": "E11.21", "name_en": "Type 2 diabetes mellitus with diabetic nephropathy", "name_vi": "Đái tháo đường typ 2 với bệnh thận do đái tháo đường", "category": "Nội tiết"},
    {"code": "E11.22", "name_en": "Type 2 diabetes mellitus with diabetic chronic kidney disease", "name_vi": "Đái tháo đường typ 2 với bệnh thận mạn do đái tháo đường", "category": "Nội tiết"},
    {"code": "E11.40", "name_en": "Type 2 diabetes mellitus with diabetic neuropathy, unspecified", "name_vi": "Đái tháo đường typ 2 với bệnh thần kinh do đái tháo đường", "category": "Nội tiết"},
    {"code": "E11.51", "name_en": "Type 2 diabetes mellitus with diabetic peripheral angiopathy without gangrene", "name_vi": "Đái tháo đường typ 2 với bệnh mạch máu ngoại vi do đái tháo đường", "category": "Nội tiết"},
    {"code": "E11.9", "name_en": "Type 2 diabetes mellitus without complications", "name_vi": "Đái tháo đường typ 2 không biến chứng", "category": "Nội tiết"},
    {"code": "E78.0", "name_en": "Pure hypercholesterolemia", "name_vi": "Tăng cholesterol máu nguyên phát", "category": "Chuyển hóa"},
    {"code": "E78.5", "name_en": "Hyperlipidemia, unspecified", "name_vi": "Tăng lipid máu không xác định", "category": "Chuyển hóa"},
    {"code": "E03.9", "name_en": "Hypothyroidism, unspecified", "name_vi": "Suy giáp không xác định", "category": "Nội tiết"},
    {"code": "E05.90", "name_en": "Thyrotoxicosis, unspecified", "name_vi": "Cường giáp không xác định", "category": "Nội tiết"},
    # F01-F99: Mental and behavioral disorders
    {"code": "F32.1", "name_en": "Major depressive disorder, single episode, moderate", "name_vi": "Rối loạn trầm cảm nặng, một đợt, trung bình", "category": "Tâm thần"},
    {"code": "F32.9", "name_en": "Major depressive disorder, single episode, unspecified", "name_vi": "Rối loạn trầm cảm nặng, một đợt, không xác định", "category": "Tâm thần"},
    {"code": "F41.0", "name_en": "Panic disorder without agoraphobia", "name_vi": "Rối loạn hoảng sợ không sợ không gian mở", "category": "Tâm thần"},
    {"code": "F41.1", "name_en": "Generalized anxiety disorder", "name_vi": "Rối loạn lo âu lan tỏa", "category": "Tâm thần"},
    {"code": "F41.9", "name_en": "Anxiety disorder, unspecified", "name_vi": "Rối loạn lo âu không xác định", "category": "Tâm thần"},
    {"code": "F51.01", "name_en": "Primary insomnia", "name_vi": "Mất ngủ nguyên phát", "category": "Tâm thần"},
    # G00-G99: Diseases of the nervous system
    {"code": "G43.909", "name_en": "Migraine, unspecified, not intractable, without status migrainosus", "name_vi": "Đau nửa đầu không xác định", "category": "Thần kinh"},
    {"code": "G47.0", "name_en": "Insomnia", "name_vi": "Mất ngủ", "category": "Thần kinh"},
    {"code": "G89.29", "name_en": "Other chronic pain", "name_vi": "Đau mạn khác", "category": "Thần kinh"},
    {"code": "G40.909", "name_en": "Epilepsy, unspecified, not intractable", "name_vi": "Động kinh không xác định", "category": "Thần kinh"},
    # H00-H59: Diseases of the eye
    {"code": "H10.9", "name_en": "Conjunctivitis, unspecified", "name_vi": "Viêm kết mạc không xác định", "category": "Mắt"},
    {"code": "H40.11", "name_en": "Primary open-angle glaucoma, mild stage", "name_vi": "Tăng nhãn áp nguyên phát mở góc mức độ nhẹ", "category": "Mắt"},
    {"code": "H25.9", "name_en": "Senile cataract, unspecified", "name_vi": "Đục thủy tinh thể do tuổi già", "category": "Mắt"},
    # I00-I99: Diseases of the circulatory system
    {"code": "I10", "name_en": "Essential (primary) hypertension", "name_vi": "Tăng huyết áp nguyên phát", "category": "Tim mạch"},
    {"code": "I11.0", "name_en": "Hypertensive heart disease with heart failure", "name_vi": "Bệnh tim do tăng huyết áp với suy tim", "category": "Tim mạch"},
    {"code": "I11.9", "name_en": "Hypertensive heart disease without heart failure", "name_vi": "Bệnh tim do tăng huyết áp không suy tim", "category": "Tim mạch"},
    {"code": "I13.10", "name_en": "Hypertensive chronic kidney disease with stage 1 through stage 4 CKD, or unspecified CKD", "name_vi": "Tăng huyết áp với bệnh thận mạn giai đoạn 1-4", "category": "Tim mạch"},
    {"code": "I20.0", "name_en": "Unstable angina", "name_vi": "Đau thồi ngực không ổn định", "category": "Tim mạch"},
    {"code": "I20.9", "name_en": "Angina pectoris, unspecified", "name_vi": "Đau thồi ngực không xác định", "category": "Tim mạch"},
    {"code": "I21.0", "name_en": "ST elevation (STEMI) myocardial infarction of anterior wall", "name_vi": "Nhồi máu cơ tim cấp ST elevn", "category": "Tim mạch"},
    {"code": "I21.9", "name_en": "Acute myocardial infarction, unspecified", "name_vi": "Nhồi máu cơ tim cấp không xác định", "category": "Tim mạch"},
    {"code": "I25.10", "name_en": "Atherosclerotic heart disease of native coronary artery without angina pectoris", "name_vi": "Bệnh động mạch vành xơ vữa không đau thồi ngực", "category": "Tim mạch"},
    {"code": "I25.11", "name_en": "Atherosclerotic heart disease of native coronary artery with angina pectoris", "name_vi": "Bệnh động mạch vành xơ vữa với đau thồi ngực", "category": "Tim mạch"},
    {"code": "I42.9", "name_en": "Cardiomyopathy, unspecified", "name_vi": "Bệnh cơ tim không xác định", "category": "Tim mạch"},
    {"code": "I48.91", "name_en": "Unspecified atrial fibrillation", "name_vi": "Rung nhĩ không xác định", "category": "Tim mạch"},
    {"code": "I48.0", "name_en": "Paroxysmal atrial fibrillation", "name_vi": "Rung nhĩ kịch phát", "category": "Tim mạch"},
    {"code": "I48.1", "name_en": "Persistent atrial fibrillation", "name_vi": "Rung nhĩ kéo dài", "category": "Tim mạch"},
    {"code": "I48.2", "name_en": "Chronic atrial fibrillation", "name_vi": "Rung nhĩ mạn", "category": "Tim mạch"},
    {"code": "I50.9", "name_en": "Heart failure, unspecified", "name_vi": "Suy tim không xác định", "category": "Tim mạch"},
    {"code": "I50.22", "name_en": "Chronic systolic heart failure", "name_vi": "Suy tim tâm thu mạn", "category": "Tim mạch"},
    {"code": "I50.23", "name_en": "Chronic diastolic heart failure", "name_vi": "Suy tâm trương mạn", "category": "Tim mạch"},
    {"code": "I62.00", "name_en": "Nontraumatic intracerebral hemorrhage, unspecified", "name_vi": "Xuất huyết não không chấn thương", "category": "Tim mạch"},
    {"code": "I63.9", "name_en": "Cerebral infarction, unspecified", "name_vi": "Nhồi máu não không xác định", "category": "Tim mạch"},
    {"code": "I67.8", "name_en": "Other specified cerebrovascular diseases", "name_vi": "Bệnh mạch máu não khác", "category": "Tim mạch"},
    {"code": "I73.9", "name_en": "Peripheral vascular disease, unspecified", "name_vi": "Bệnh mạch máu ngoại vi không xác định", "category": "Tim mạch"},
    # J00-J99: Diseases of the respiratory system
    {"code": "J00", "name_en": "Acute nasopharyngitis [common cold]", "name_vi": "Viêm mũi họng cấp (cảm lạnh)", "category": "Hô hấp"},
    {"code": "J01.90", "name_en": "Acute sinusitis, unspecified", "name_vi": "Viêm xoang cấp không xác định", "category": "Hô hấp"},
    {"code": "J02.9", "name_en": "Acute pharyngitis, unspecified", "name_vi": "Viêm họng cấp không xác định", "category": "Hô hấp"},
    {"code": "J03.90", "name_en": "Acute tonsillitis, unspecified", "name_vi": "Viêm amidan cấp không xác định", "category": "Hô hấp"},
    {"code": "J04.10", "name_en": "Acute tracheitis without obstruction", "name_vi": "Viêm khí quản cấp không bít tắc", "category": "Hô hấp"},
    {"code": "J06.9", "name_en": "Acute upper respiratory infection, unspecified", "name_vi": "Nhiễm trùng hô hấp trên cấp không xác định", "category": "Hô hấp"},
    {"code": "J11.0", "name_en": "Influenza due to unidentified influenza virus with pneumonia", "name_vi": "Cúm do virus cúm không xác định với viêm phổi", "category": "Hô hấp"},
    {"code": "J12.9", "name_en": "Viral pneumonia, unspecified", "name_vi": "Viêm phổi do virus không xác định", "category": "Hô hấp"},
    {"code": "J18.9", "name_en": "Pneumonia, unspecified organism", "name_vi": "Viêm phổi không xác định tác nhân", "category": "Hô hấp"},
    {"code": "J20.9", "name_en": "Acute bronchitis, unspecified", "name_vi": "Viêm phế quản cấp không xác định", "category": "Hô hấp"},
    {"code": "J40", "name_en": "Bronchitis, not specified as acute or chronic", "name_vi": "Viêm phế quản không xác định cấp hay mạn", "category": "Hô hấp"},
    {"code": "J41.0", "name_en": "Simple chronic bronchitis", "name_vi": "Viêm phế quản mạn đơn giản", "category": "Hô hấp"},
    {"code": "J41.1", "name_en": "Mucopurulent chronic bronchitis", "name_vi": "Viêm phế quản mạn nhầy mủ", "category": "Hô hấp"},
    {"code": "J42", "name_en": "Unspecified chronic bronchitis", "name_vi": "Viêm phế quản mạn không xác định", "category": "Hô hấp"},
    {"code": "J43.9", "name_en": "Emphysema, unspecified", "name_vi": "Khí thũng không xác định", "category": "Hô hấp"},
    {"code": "J44.1", "name_en": "Chronic obstructive pulmonary disease with acute exacerbation", "name_vi": "Bệnh phổi tắc nghẽn mạn với đợt cấp", "category": "Hô hấp"},
    {"code": "J44.9", "name_en": "Chronic obstructive pulmonary disease, unspecified", "name_vi": "Bệnh phổi tắc nghẽn mạn không xác định", "category": "Hô hấp"},
    {"code": "J45.20", "name_en": "Mild intermittent asthma, uncomplicated", "name_vi": "Hen nhẹ từng hồi không biến chứng", "category": "Hô hấp"},
    {"code": "J45.21", "name_en": "Mild intermittent asthma with (acute) exacerbation", "name_vi": "Hen nhẹ từng hồi với đợt cấp", "category": "Hô hấp"},
    {"code": "J45.30", "name_en": "Mild persistent asthma, uncomplicated", "name_vi": "Hen nhẹ dai dẳng không biến chứng", "category": "Hô hấp"},
    {"code": "J45.40", "name_en": "Moderate persistent asthma, uncomplicated", "name_vi": "Hen trung bình dai dẳng không biến chứng", "category": "Hô hấp"},
    {"code": "J45.50", "name_en": "Severe persistent asthma, uncomplicated", "name_vi": "Hen nặng dai dẳng không biến chứng", "category": "Hô hấp"},
    {"code": "J45.909", "name_en": "Unspecified asthma, uncomplicated", "name_vi": "Hen không xác định không biến chứng", "category": "Hô hấp"},
    {"code": "J60", "name_en": "Coalworker's pneumoconiosis", "name_vi": "Bệnh phổi nghề nghiệp", "category": "Hô hấp"},
    {"code": "J80", "name_en": "Acute respiratory distress syndrome", "name_vi": "Hội chứng suy hô hấp cấp", "category": "Hô hấp"},
    {"code": "J96.00", "name_en": "Acute respiratory failure, unspecified whether with hypoxia or hypercapnia", "name_vi": "Suy hô hấp cấp không xác định", "category": "Hô hấp"},
    {"code": "J96.90", "name_en": "Respiratory failure, unspecified", "name_vi": "Suy hô hấp không xác định", "category": "Hô hấp"},
    # K00-K93: Diseases of the digestive system
    {"code": "K21.0", "name_en": "Gastro-esophageal reflux disease with esophagitis", "name_vi": "Bệnh trào ngược dạ dày thực quản với viêm thực quản", "category": "Tiêu hóa"},
    {"code": "K21.9", "name_en": "Gastro-esophageal reflux disease without esophagitis", "name_vi": "Bệnh trào ngược dạ dày thực quản không viêm thực quản", "category": "Tiêu hóa"},
    {"code": "K25.9", "name_en": "Gastric ulcer, unspecified as acute or chronic, without hemorrhage or perforation", "name_vi": "Loét dạ dày không xác định cấp hay mạn", "category": "Tiêu hóa"},
    {"code": "K27.9", "name_en": "Peptic ulcer, unspecified site, without hemorrhage or perforation", "name_vi": "Loét tiêu hóa không xác định vị trí", "category": "Tiêu hóa"},
    {"code": "K29.0", "name_en": "Acute hemorrhagic gastritis", "name_vi": "Viêm dạ dày xuất huyết cấp", "category": "Tiêu hóa"},
    {"code": "K29.50", "name_en": "Chronic gastritis, unspecified", "name_vi": "Viêm dạ dày mạn không xác định", "category": "Tiêu hóa"},
    {"code": "K29.70", "name_en": "Gastritis, unspecified", "name_vi": "Viêm dạ dày không xác định", "category": "Tiêu hóa"},
    {"code": "K31.7", "name_en": "Polyp of stomach", "name_vi": "Polyp dạ dày", "category": "Tiêu hóa"},
    {"code": "K35.80", "name_en": "Unspecified acute appendicitis", "name_vi": "Viêm ruột thừa cấp không xác định", "category": "Tiêu hóa"},
    {"code": "K40.90", "name_en": "Inguinal hernia, unilateral, not specified as recurrent, without obstruction or gangrene", "name_vi": "Thoát vị bẹn đơn侧", "category": "Tiêu hóa"},
    {"code": "K50.00", "name_en": "Crohn's disease of small intestine with unspecified complications", "name_vi": "Bệnh Crohn ruột non với biến chứng không xác định", "category": "Tiêu hóa"},
    {"code": "K51.00", "name_en": "Ulcerative (chronic) pancolitis without complications", "name_vi": "Viêm loét đại tràng toàn bộ mạn không biến chứng", "category": "Tiêu hóa"},
    {"code": "K51.50", "name_en": "Left sided ulcerative (chronic) colitis without complications", "name_vi": "Viêm loét đại tràng trái mạn không biến chứng", "category": "Tiêu hóa"},
    {"code": "K58.9", "name_en": "Irritable bowel syndrome without diarrhea", "name_vi": "Hội chứng ruột kích thích không tiêu chảy", "category": "Tiêu hóa"},
    {"code": "K59.00", "name_en": "Constipation, unspecified", "name_vi": "Táo bón không xác định", "category": "Tiêu hóa"},
    {"code": "K59.10", "name_en": "Functional diarrhea", "name_vi": "Tiêu chảy chức năng", "category": "Tiêu hóa"},
    {"code": "K63.5", "name_en": "Polyp of colon", "name_vi": "Polyp đại tràng", "category": "Tiêu hóa"},
    {"code": "K76.0", "name_en": "Fatty (change of) liver, not elsewhere classified", "name_vi": "Gan nhiễm mỡ không phân loại", "category": "Tiêu hóa"},
    {"code": "K76.81", "name_en": "Hepatomegaly", "name_vi": "Phì đại gan", "category": "Tiêu hóa"},
    {"code": "K80.20", "name_en": "Calculus of gallbladder without cholecystitis without obstruction", "name_vi": "Sỏi túi mật không viêm túi mật", "category": "Tiêu hóa"},
    {"code": "K80.50", "name_en": "Calculus of bile duct without cholangitis or cholecystitis without obstruction", "name_vi": "Sỏi ống mật không viêm", "category": "Tiêu hóa"},
    {"code": "K81.0", "name_en": "Acute cholecystitis", "name_vi": "Viêm túi mật cấp", "category": "Tiêu hóa"},
    {"code": "K81.1", "name_en": "Chronic cholecystitis", "name_vi": "Viêm túi mật mạn", "category": "Tiêu hóa"},
    {"code": "K85.9", "name_en": "Acute pancreatitis, unspecified", "name_vi": "Viêm tụy cấp không xác định", "category": "Tiêu hóa"},
    {"code": "K86.1", "name_en": "Other chronic pancreatitis", "name_vi": "Viêm tụy mạn khác", "category": "Tiêu hóa"},
    # L00-L99: Diseases of the skin and subcutaneous tissue
    {"code": "L20.9", "name_en": "Atopic dermatitis, unspecified", "name_vi": "Viêm da cơ địa không xác định", "category": "Da liễu"},
    {"code": "L30.9", "name_en": "Dermatitis, unspecified", "name_vi": "Viêm da không xác định", "category": "Da liễu"},
    {"code": "L40.0", "name_en": "Psoriasis vulgaris", "name_vi": "Vẩy nến thể thông thường", "category": "Da liễu"},
    {"code": "L50.0", "name_en": "Urticaria", "name_vi": "Mề đay", "category": "Da liễu"},
    {"code": "L70.0", "name_en": "Acne vulgaris", "name_vi": "Mụn trứng cá thông thường", "category": "Da liễu"},
    # M00-M99: Diseases of the musculoskeletal system and connective tissue
    {"code": "M05.79", "name_en": "Rheumatoid arthritis with rheumatoid factor, multiple sites", "name_vi": "Viêm đa khớp dạng thấp dương tính factor, nhiều vị trí", "category": "Cơ xương khớp"},
    {"code": "M10.9", "name_en": "Gout, unspecified", "name_vi": "Gout không xác định", "category": "Cơ xương khớp"},
    {"code": "M15.0", "name_en": "Primary generalized osteoarthritis", "name_vi": "Thoái hóa khớp nguyên phát toàn thân", "category": "Cơ xương khớp"},
    {"code": "M17.11", "name_en": "Primary osteoarthritis, right knee", "name_vi": "Thoái hóa khớp gối phải nguyên phát", "category": "Cơ xương khớp"},
    {"code": "M47.817", "name_en": "Spondylosis without myelopathy or radiculopathy, lumbar region", "name_vi": "Thoái hóa cột sống thắt lưng không chèn ép tủy", "category": "Cơ xương khớp"},
    {"code": "M51.16", "name_en": "Intervertebral disc disorders with radiculopathy, lumbar region", "name_vi": "Rối loạn đĩa đệm cột sống thắt lưng với viêm rễ thần kinh", "category": "Cơ xương khớp"},
    {"code": "M54.5", "name_en": "Low back pain", "name_vi": "Đau thắt lưng", "category": "Cơ xương khớp"},
    {"code": "M54.2", "name_en": "Cervicalgia", "name_vi": "Đau cổ", "category": "Cơ xương khớp"},
    {"code": "M75.01", "name_en": "Adhesive capsulitis, right shoulder", "name_vi": "Viêm bao khớp vai phải dính", "category": "Cơ xương khớp"},
    {"code": "M79.3", "name_en": "Panniculitis, unspecified", "name_vi": "Viêm dưới da không xác định", "category": "Cơ xương khớp"},
    # N00-N99: Diseases of the genitourinary system
    {"code": "N10", "name_en": "Acute pyelonephritis", "name_vi": "Viêm thận bể thận cấp", "category": "Tiết niệu"},
    {"code": "N11.9", "name_en": "Chronic pyelonephritis, unspecified", "name_vi": "Viêm thận bể thận mạn không xác định", "category": "Tiết niệu"},
    {"code": "N18.1", "name_en": "Chronic kidney disease, stage 1", "name_vi": "Bệnh thận mạn giai đoạn 1", "category": "Tiết niệu"},
    {"code": "N18.2", "name_en": "Chronic kidney disease, stage 2", "name_vi": "Bệnh thận mạn giai đoạn 2", "category": "Tiết niệu"},
    {"code": "N18.30", "name_en": "Chronic kidney disease, stage 3 unspecified", "name_vi": "Bệnh thận mạn giai đoạn 3", "category": "Tiết niệu"},
    {"code": "N18.4", "name_en": "Chronic kidney disease, stage 4", "name_vi": "Bệnh thận mạn giai đoạn 4", "category": "Tiết niệu"},
    {"code": "N18.5", "name_en": "Chronic kidney disease, stage 5", "name_vi": "Bệnh thận mạn giai đoạn 5", "category": "Tiết niệu"},
    {"code": "N18.6", "name_en": "End stage renal disease", "name_vi": "Bệnh thận giai đoạn cuối", "category": "Tiết niệu"},
    {"code": "N20.0", "name_en": "Calculus of kidney", "name_vi": "Sỏi thận", "category": "Tiết niệu"},
    {"code": "N20.1", "name_en": "Calculus of ureter", "name_vi": "Sỏi niệu quản", "category": "Tiết niệu"},
    {"code": "N30.00", "name_en": "Acute cystitis without hematuria", "name_vi": "Viêm bàng quang cấp không tiểu máu", "category": "Tiết niệu"},
    {"code": "N39.0", "name_en": "Urinary tract infection, site not specified", "name_vi": "Nhiễm trùng đường tiết niệu không xác định vị trí", "category": "Tiết niệu"},
    {"code": "N40.0", "name_en": "Benign prostatic hyperplasia, unspecified", "name_vi": "Phì đại lành tính tuyến tiền liệt", "category": "Tiết niệu"},
    # O00-O9A: Pregnancy, childbirth and the puerperium
    {"code": "O13.9", "name_en": "Gestational hypertension without significant proteinuria", "name_vi": "Tăng huyết áp thai kỳ không protein niệu", "category": "Sản khoa"},
    {"code": "O24.41", "name_en": "Gestational diabetes mellitus in pregnancy", "name_vi": "Đái tháo đường thai kỳ", "category": "Sản khoa"},
    {"code": "O80.0", "name_en": "Encounter for full-term uncomplicated delivery", "name_vi": "Thai kỳ đủ tháng không biến chứng", "category": "Sản khoa"},
    # P00-P96: Certain conditions originating in the perinatal period
    # Q00-Q99: Congenital malformations, deformations and chromosomal abnormalities
    # R00-R99: Symptoms, signs and abnormal clinical and laboratory findings
    {"code": "R05.9", "name_en": "Cough, unspecified", "name_vi": "Ho không xác định", "category": "Triệu chứng"},
    {"code": "R06.00", "name_en": "Dyspnea, unspecified", "name_vi": "Khó thở không xác định", "category": "Triệu chứng"},
    {"code": "R06.02", "name_en": "Shortness of breath", "name_vi": "Thở ngắn", "category": "Triệu chứng"},
    {"code": "R06.82", "name_en": "Tachypnea, unspecified", "name_vi": "Thở nhanh không xác định", "category": "Triệu chứng"},
    {"code": "R07.9", "name_en": "Chest pain, unspecified", "name_vi": "Đau ngực không xác định", "category": "Triệu chứng"},
    {"code": "R10.0", "name_en": "Acute abdomen", "name_vi": "Cấp tính bụng", "category": "Triệu chứng"},
    {"code": "R10.10", "name_en": "Pain localized to upper abdomen", "name_vi": "Đau khu trú bụng trên", "category": "Triệu chứng"},
    {"code": "R10.30", "name_en": "Pain localized to lower abdomen", "name_vi": "Đau khu trú bụng dưới", "category": "Triệu chứng"},
    {"code": "R10.9", "name_en": "Unspecified abdominal pain", "name_vi": "Đau bụng không xác định", "category": "Triệu chứng"},
    {"code": "R11.0", "name_en": "Nausea", "name_vi": "Buồn nôn", "category": "Triệu chứng"},
    {"code": "R11.10", "name_en": "Vomiting, unspecified", "name_vi": "Nôn không xác định", "category": "Triệu chứng"},
    {"code": "R11.2", "name_en": "Nausea with vomiting, unspecified", "name_vi": "Buồn nôn với nôn", "category": "Triệu chứng"},
    {"code": "R17", "name_en": "Unspecified jaundice", "name_vi": "Vàng da không xác định", "category": "Triệu chứng"},
    {"code": "R50.9", "name_en": "Fever, unspecified", "name_vi": "Sốt không xác định", "category": "Triệu chứng"},
    {"code": "R51.9", "name_en": "Headache, unspecified", "name_vi": "Đau đầu không xác định", "category": "Triệu chứng"},
    {"code": "R55", "name_en": "Syncope and collapse", "name_vi": "Ngất và sụp đổ", "category": "Triệu chứng"},
    {"code": "R56.0", "name_en": "Convulsions, not elsewhere classified", "name_vi": "Co giật không phân loại", "category": "Triệu chứng"},
    {"code": "R60.0", "name_en": "Localized edema", "name_vi": "Phù tại chỗ", "category": "Triệu chứng"},
    {"code": "R60.1", "name_en": "Generalized edema", "name_vi": "Phù toàn thân", "category": "Triệu chứng"},
    {"code": "R63.0", "name_en": "Anorexia", "name_vi": "Chán ăn", "category": "Triệu chứng"},
    {"code": "R63.4", "name_en": "Abnormal weight loss", "name_vi": "Giảm cân bất thường", "category": "Triệu chứng"},
    {"code": "R68.83", "name_en": "Chills", "name_vi": "Rùng mình", "category": "Triệu chứng"},
    {"code": "R73.03", "name_en": "Prediabetes", "name_vi": "Tiền đái tháo đường", "category": "Triệu chứng"},
    {"code": "R73.09", "name_en": "Other abnormal glucose", "name_vi": "Đường huyết bất thường khác", "category": "Triệu chứng"},
    {"code": "R74.0", "name_en": "Nonspecific elevation of levels of transaminase and lactic acid dehydrogenase [LDH]", "name_vi": "Tăng transaminase và LDH không đặc hiệu", "category": "Triệu chứng"},
    {"code": "R76.8", "name_en": "Other specified abnormalities of immunological status", "name_vi": "Bất thường tình trạng miễn dịch khác", "category": "Triệu chứng"},
    {"code": "R77.0", "name_en": "Abnormality of albumin", "name_vi": "Bất thường albumin", "category": "Triệu chứng"},
    {"code": "R77.1", "name_en": "Abnormality of globulin", "name_vi": "Bất thường globulin", "category": "Triệu chứng"},
    {"code": "R79.0", "name_en": "Abnormal serum enzyme level", "name_vi": "Menzymenzymenzym", "category": "Triệu chứng"},
    {"code": "R94.2", "name_en": "Abnormal results of function studies of brain", "name_vi": "Kết quả bất thường thăm dò chức năng não", "category": "Triệu chứng"},
    # S00-T88: Injury, poisoning and certain other consequences of external causes
    {"code": "S06.0X0A", "name_en": "Concussion without loss of consciousness, initial encounter", "name_vi": "Chấn thương sọ não nhẹ không mất ý thức", "category": "Chấn thương"},
    {"code": "S12.000A", "name_en": "Unspecified fracture of first cervical vertebra, initial encounter", "name_vi": "Gãy đốt sống cổ thứ nhất không xác định", "category": "Chấn thương"},
    {"code": "S22.010A", "name_en": "Fracture of manubrium, initial encounter", "name_vi": "Gãy xương ức", "category": "Chấn thương"},
    {"code": "S42.201A", "name_en": "Unspecified fracture of upper end of right humerus, initial encounter", "name_vi": "Gãy đầu trên xương cánh tay phải", "category": "Chấn thương"},
    {"code": "S72.001A", "name_en": "Unspecified fracture of right femoral neck, initial encounter", "name_vi": "Gãy cổ xương đùi phải", "category": "Chấn thương"},
    # Z00-Z99: Factors influencing health status and contact with health services
    {"code": "Z00.00", "name_en": "Encounter for general adult medical examination without abnormal findings", "name_vi": "Khám tổng quát người lớn không bất thường", "category": "Kiểm tra"},
    {"code": "Z23", "name_en": "Encounter for immunization", "name_vi": "Tiêm chủng", "category": "Kiểm tra"},
    {"code": "Z87.39", "name_en": "Personal history of other musculoskeletal disorders", "name_vi": "Tiền sử bệnh cơ xương khớp khác", "category": "Tiền sử"},
    {"code": "Z87.891", "name_en": "Personal history of nicotine dependence", "name_vi": "Tiền sử nghiện nicotine", "category": "Tiền sử"},
    {"code": "Z96.1", "name_en": "Intraocular lens status", "name_vi": "Đã đặt thủy tinh thể nhân tạo", "category": "Tiền sử"},
    {"code": "Z99.2", "name_en": "Dependence on renal dialysis", "name_vi": "Phụ thuộc vào chạy thận nhân tạo", "category": "Tiền sử"},
]

# Vietnamese common diseases added manually
ICD10_VIETNAMESE_ADDITIONS = [
    {"code": "A09", "name_vi": "Tiêu chảy nhiễm khuẩn", "name_en": "Infectious diarrhea", "category": "Nhiễm trùng"},
    {"code": "B34.9", "name_vi": "Nhiễm virus không rõ nguyên nhân", "name_en": "Viral infection NOS", "category": "Nhiễm trùng"},
    {"code": "E11.9", "name_vi": "Đái tháo đường typ 2", "name_en": "DM type 2", "category": "Nội tiết"},
    {"code": "E78.5", "name_vi": "Mỡ máu cao", "name_en": "Hyperlipidemia", "category": "Chuyển hóa"},
    {"code": "I10", "name_vi": "Tăng huyết áp", "name_en": "Hypertension", "category": "Tim mạch"},
    {"code": "I25.10", "name_vi": "Hẹp mạch vành", "name_en": "Coronary artery disease", "category": "Tim mạch"},
    {"code": "I48.91", "name_vi": "Rung nhĩ", "name_en": "Atrial fibrillation", "category": "Tim mạch"},
    {"code": "I50.9", "name_vi": "Suy tim", "name_en": "Heart failure", "category": "Tim mạch"},
    {"code": "I63.9", "name_vi": "Đột quỵ nhồi máu não", "name_en": "Ischemic stroke", "category": "Tim mạch"},
    {"code": "J44.1", "name_vi": "COPD đợt cấp", "name_en": "COPD exacerbation", "category": "Hô hấp"},
    {"code": "J45.909", "name_vi": "Hen phế quản", "name_en": "Asthma", "category": "Hô hấp"},
    {"code": "K21.0", "name_vi": "Trào ngược dạ dày thực quản", "name_en": "GERD", "category": "Tiêu hóa"},
    {"code": "K80.20", "name_vi": "Sỏi mật", "name_en": "Gallstones", "category": "Tiêu hóa"},
    {"code": "K81.0", "name_vi": "Viêm túi mật cấp", "name_en": "Acute cholecystitis", "category": "Tiêu hóa"},
    {"code": "K85.9", "name_vi": "Viêm tụy cấp", "name_en": "Acute pancreatitis", "category": "Tiêu hóa"},
    {"code": "M17.11", "name_vi": "Thoái hóa khớp gối phải", "name_en": "Right knee OA", "category": "Cơ xương khớp"},
    {"code": "M54.5", "name_vi": "Đau thắt lưng", "name_en": "Low back pain", "category": "Cơ xương khớp"},
    {"code": "N17.9", "name_vi": "Suy thận cấp", "name_en": "Acute kidney injury", "category": "Tiết niệu"},
    {"code": "N18.5", "name_vi": "Suy thận mạn giai đoạn 5", "name_en": "CKD stage 5", "category": "Tiết niệu"},
    {"code": "N20.0", "name_vi": "Sỏi thận", "name_en": "Kidney stones", "category": "Tiết niệu"},
    {"code": "R05.9", "name_vi": "Ho", "name_en": "Cough", "category": "Triệu chứng"},
    {"code": "R06.00", "name_vi": "Khó thở", "name_en": "Dyspnea", "category": "Triệu chứng"},
    {"code": "R07.9", "name_vi": "Đau ngực", "name_en": "Chest pain", "category": "Triệu chứng"},
    {"code": "R10.9", "name_vi": "Đau bụng", "name_en": "Abdominal pain", "category": "Triệu chứng"},
    {"code": "R50.9", "name_vi": "Sốt", "name_en": "Fever", "category": "Triệu chứng"},
    {"code": "R51.9", "name_vi": "Đau đầu", "name_en": "Headache", "category": "Triệu chứng"},
]


def build_database():
    """Build ICD-10 database."""
    print("=== Building ICD-10 Database ===")

    all_entries = {}
    for entry in ICD10_CORE:
        code = entry["code"]
        all_entries[code] = {
            "code": code,
            "name_en": entry.get("name_en", ""),
            "name_vi": entry.get("name_vi", ""),
            "category": entry.get("category", ""),
            "search_text": f"{entry.get('name_en', '')} {entry.get('name_vi', '')}".lower().strip()
        }

    for entry in ICD10_VIETNAMESE_ADDITIONS:
        code = entry["code"]
        if code in all_entries:
            existing = all_entries[code]
            if not existing["name_vi"]:
                existing["name_vi"] = entry["name_vi"]
            if entry.get("name_en"):
                existing["name_en"] = entry["name_en"]
            existing["search_text"] = f"{existing['name_en']} {existing['name_vi']}".lower().strip()
        else:
            all_entries[code] = {
                "code": code,
                "name_en": entry.get("name_en", ""),
                "name_vi": entry.get("name_vi", ""),
                "category": entry.get("category", ""),
                "search_text": f"{entry.get('name_en', '')} {entry.get('name_vi', '')}".lower().strip()
            }

    database = {
        "version": "1.0",
        "description": "ICD-10 database for Vietnamese medical NER",
        "total_codes": len(all_entries),
        "categories": list(set(e.get("category", "") for e in all_entries.values())),
        "codes": all_entries
    }

    os.makedirs(DB_DIR, exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(database, f, ensure_ascii=False, indent=2)

    print(f"Saved {len(all_entries)} ICD-10 codes to {OUTPUT_FILE}")
    return database


def try_download_who_icd10():
    """Try to download ICD-10 from WHO API."""
    print("=== Trying WHO ICD-10 API ===")
    try:
        url = "https://icd.who.int/browse/2024-01/mms/en/report.json"
        headers = {"Accept": "application/json"}
        resp = requests.get(url, headers=headers, timeout=30)
        if resp.status_code == 200:
            data = resp.json()
            print(f"WHO API returned data: {list(data.keys())}")
            return data
        else:
            print(f"WHO API returned status {resp.status_code}")
            return None
    except Exception as e:
        print(f"WHO API failed: {e}")
        return None


def download_medicare_icd10():
    """Download CMS Medicare ICD-10-CM descriptions."""
    print("=== Trying Medicare ICD-10 data ===")
    url = "https://www.cms.gov/files/zip/2024-icd-10-cm-tables-and-index.zip"
    try:
        resp = requests.get(url, timeout=60, stream=True)
        if resp.status_code == 200:
            zip_path = os.path.join(DB_DIR, "medicare_icd10.zip")
            with open(zip_path, "wb") as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    f.write(chunk)
            print(f"Downloaded Medicare ICD-10 zip to {zip_path}")
            return True
    except Exception as e:
        print(f"Medicare download failed: {e}")
    return False


if __name__ == "__main__":
    build_database()
    try_download_who_icd10()
