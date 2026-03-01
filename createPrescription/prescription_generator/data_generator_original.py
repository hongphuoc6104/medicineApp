import json
import random
import os
from datetime import datetime, timedelta

# ==============================================================================
# 1. MEDICAL KNOWLEDGE BASE (Cơ sở tri thức y khoa)
# ==============================================================================
class MedicalKnowledgeBase:
    def __init__(self):
        # Database về Bệnh (ICD-10 -> Tên -> Nhóm thuốc phù hợp)
        self.conditions = {
            # --- HÔ HẤP (Respiratory) ---
            "J00": { "code": "J00", "name": "Viêm mũi họng cấp", "types": ["Acute", "Pediatric", "Adult"], "drugs": ["Paracetamol", "Ibuprofen", "Chlorpheniramine", "Vitamin C", "Nước muối sinh lý"] },
            "J20.9": { "code": "J20.9", "name": "Viêm phế quản cấp", "types": ["Acute", "Adult", "Pediatric"], "drugs": ["Amoxicillin_Clavulanate", "Cefuroxime", "Acetylcysteine", "Salbutamol", "Paracetamol"] },
            "J44.9": { "code": "J44.9", "name": "Bệnh phổi tắc nghẽn mạn tính (COPD)", "types": ["Chronic", "Elderly"], "drugs": ["Salbutamol_Inhaler", "Tiotropium", "Budesonide", "Prednisolone", "Azithromycin"] },
            
            # --- TIM MẠCH (Cardiovascular) - COMPLEX ---
            "I10": { "code": "I10", "name": "Tăng huyết áp vô căn", "types": ["Chronic", "Adult", "Elderly"], "drugs": ["Amlodipine", "Losartan", "Telmisartan", "Perindopril", "Hydrochlorothiazide"] },
            "I25.1": { "code": "I25.1", "name": "Bệnh tim thiếu máu cục bộ mạn", "types": ["Chronic", "Elderly"], "drugs": ["Aspirin", "Clopidogrel", "Atorvastatin", "Rosuvastatin", "Bisoprolol", "Nitroglycerin"] },
            "I63.9": { "code": "I63.9", "name": "Di chứng nhồi máu não", "types": ["Chronic", "Elderly", "Neuro"], "drugs": ["Aspirin", "Clopidogrel", "Atorvastatin", "Citicoline", "Piracetam"] },
            
            # --- NỘI TIẾT (Endocrine) ---
            "E11": { "code": "E11", "name": "Đái tháo đường type 2", "types": ["Chronic", "Adult", "Elderly"], "drugs": ["Metformin", "Gliclazide", "Sitagliptin", "Empagliflozin", "Insulin_Glargine"] },
            "E78.0": { "code": "E78.0", "name": "Tăng cholesterol máu thuần", "types": ["Chronic", "Adult", "Elderly"], "drugs": ["Atorvastatin", "Rosuvastatin", "Fenofibrate", "Ezetimibe"] },

            # --- TIÊU HÓA (Gastrointestinal) - NEW ---
            "K21.9": { "code": "K21.9", "name": "Bệnh trào ngược dạ dày-thực quản (GERD)", "types": ["Chronic", "Acute", "Adult"], "drugs": ["Omeprazole", "Esomeprazole", "Pantoprazole", "Domperidone", "Gaviscon"] },
            "K58.0": { "code": "K58.0", "name": "Hội chứng ruột kích thích (IBS)", "types": ["Chronic", "Adult"], "drugs": ["Trimebutine", "Mebeverine", "Probiotics", "Amitriptyline_LowDose"] },
            "K73.9": { "code": "K73.9", "name": "Viêm gan mạn tính", "types": ["Chronic", "Adult"], "drugs": ["Silymarin", "L-Ornithine", "Vitamin B_Group"] },

             # --- CƠ XƯƠNG KHỚP (Musculoskeletal) ---
            "M17": { "code": "M17", "name": "Thoái hóa khớp gối", "types": ["Chronic", "Elderly"], "drugs": ["Celecoxib", "Glucosamine", "Paracetamol", "Diclofenac_Gel"] },
            "M54.5": { "code": "M54.5", "name": "Đau thắt lưng", "types": ["Acute", "Chronic", "Adult"], "drugs": ["Meloxicam", "Eperisone", "Vitamin B_Group", "Paracetamol"] },
            
            # --- THẦN KINH (Neurology) - NEW ---
            "G40.9": { "code": "G40.9", "name": "Bệnh động kinh", "types": ["Chronic", "Adult", "Pediatric"], "drugs": ["Valproic_Acid", "Levetiracetam", "Carbamazepine"] },
            "G43.9": { "code": "G43.9", "name": "Migraine", "types": ["Chronic", "Adult"], "drugs": ["Flunarizine", "Paracetamol", "Naproxen"] },
            "G47.0": { "code": "G47.0", "name": "Rối loạn giấc ngủ", "types": ["Acute", "Adult", "Elderly"], "drugs": ["Rotunda", "Melatonin", "Magnesium_B6"] },
            
            # --- DA LIỄU (Dermatology) - NEW ---
            "L20.9": { "code": "L20.9", "name": "Viêm da cơ địa", "types": ["Chronic", "Pediatric", "Adult"], "drugs": ["Cetirizine", "Fexofenadine", "Hydrocortisone_Cream", "Vitamin C"] },
            "L70.0": { "code": "L70.0", "name": "Mụn trứng cá thông thường", "types": ["Chronic", "Adult"], "drugs": ["Doxycycline", "Isotretinoin", "Adapalene_Gel"] },
            "B35.1": { "code": "B35.1", "name": "Nấm móng", "types": ["Chronic", "Adult"], "drugs": ["Itraconazole", "Terbinafine_Cream"] },
            
            # --- MẮT (Ophthalmology) - NEW ---
            "H10.1": { "code": "H10.1", "name": "Viêm kết mạc cấp", "types": ["Acute", "Pediatric", "Adult"], "drugs": ["Tobramycin_Drop", "Nước muối sinh lý", "Vitamin C"] },
            "H04.1": { "code": "H04.1", "name": "Hội chứng khô mắt", "types": ["Chronic", "Adult", "Elderly"], "drugs": ["Artificial_Tears", "Vitamin A", "Omega-3"] },
        }

        # Database về Thuốc
        self.drugs = {
            # --- Kháng sinh ---
            "Amoxicillin_Clavulanate": [ {"brand": "Augmentin", "dosage": "1g", "unit": "Viên", "instr": "Ngày uống 2 viên (sáng, chiều) sau ăn"}, {"brand": "Klamentin", "dosage": "875/125mg", "unit": "Viên", "instr": "Ngày uống 2 viên sau ăn"} ],
            "Cefuroxime": [ {"brand": "Zinnat", "dosage": "500mg", "unit": "Viên", "instr": "Ngày uống 2 viên sau ăn (sáng, tối)"} ],
            "Azithromycin": [ {"brand": "Zithromax", "dosage": "500mg", "unit": "Viên", "instr": "Ngày uống 1 viên (uống 3 ngày)"} ],
            "Doxycycline": [ {"brand": "Doxycycline", "dosage": "100mg", "unit": "Viên", "instr": "Ngày uống 1 viên sau ăn"} ],
            "Tobramycin_Drop": [ {"brand": "Tobrex", "dosage": "0.3%", "unit": "Lọ", "instr": "Nhỏ mắt ngày 3 lần"} ],
            
            # --- Da Liễu / Nấm ---
            "Itraconazole": [ {"brand": "Sporal", "dosage": "100mg", "unit": "Viên", "instr": "Ngày uống 2 viên sau ăn"} ],
            "Isotretinoin": [ {"brand": "Acnotin", "dosage": "10mg", "unit": "Viên", "instr": "Ngày uống 1 viên sau ăn tối"} ],
            "Adapalene_Gel": [ {"brand": "Differin", "dosage": "0.1%", "unit": "Tuýp", "instr": "Bôi vùng mụn 1 lần buổi tối"} ],
            "Terbinafine_Cream": [ {"brand": "Lamisil", "dosage": "1%", "unit": "Tuýp", "instr": "Bôi vùng nấm 2 lần/ngày"} ],
            "Hydrocortisone_Cream": [ {"brand": "Eumovate", "dosage": "15g", "unit": "Tuýp", "instr": "Bôi vùng da viêm 2 lần/ngày"} ],

            # --- Thần kinh / Tâm thần ---
            "Valproic_Acid": [ {"brand": "Depakin", "dosage": "200mg", "unit": "Viên", "instr": "Ngày uống 2 viên sau ăn"} ],
            "Levetiracetam": [ {"brand": "Keppra", "dosage": "500mg", "unit": "Viên", "instr": "Ngày uống 2 viên (sáng, tối)"} ],
            "Carbamazepine": [ {"brand": "Tegretol", "dosage": "200mg", "unit": "Viên", "instr": "Ngày uống 2 viên"} ],
            "Flunarizine": [ {"brand": "Sibelium", "dosage": "5mg", "unit": "Viên", "instr": "Ngày uống 1 viên buổi tối"} ],
            "Citicoline": [ {"brand": "Somazina", "dosage": "500mg", "unit": "Viên", "instr": "Ngày uống 2 viên (sáng, tối)"} ],
            "Piracetam": [ {"brand": "Nootropil", "dosage": "800mg", "unit": "Viên", "instr": "Ngày uống 3 viên sau ăn"} ],
            "Rotunda": [ {"brand": "Rotunda", "dosage": "30mg", "unit": "Viên", "instr": "Ngày uống 1-2 viên trước khi ngủ"} ],
            
            # --- Tiêu hóa ---
            "Trimebutine": [ {"brand": "Debridat", "dosage": "100mg", "unit": "Viên", "instr": "Ngày uống 2 viên trước ăn"} ],
            "Mebeverine": [ {"brand": "Duspatalin", "dosage": "200mg", "unit": "Viên", "instr": "Ngày uống 2 viên trước ăn"} ],
            "Silymarin": [ {"brand": "Silygamma", "dosage": "140mg", "unit": "Viên", "instr": "Ngày uống 2 viên sau ăn"} ],
            "L-Ornithine": [ {"brand": "Barcavir", "dosage": "500mg", "unit": "Viên", "instr": "Ngày uống 2 viên sau ăn"} ],
            "Probiotics": [ {"brand": "Enterogermina", "dosage": "5ml", "unit": "Ống", "instr": "Uống 2 ống/ngày"} ],
            "Omeprazole": [ {"brand": "Losec", "dosage": "20mg", "unit": "Viên", "instr": "Uống 1 viên trước ăn sáng 30 phút"} ],
            "Esomeprazole": [ {"brand": "Nexium", "dosage": "40mg", "unit": "Viên", "instr": "Uống 1 viên trước ăn sáng 30 phút"} ],
            "Pantoprazole": [ {"brand": "Pantoloc", "dosage": "40mg", "unit": "Viên", "instr": "Ngày uống 1 viên trước ăn sáng"} ],
            "Domperidone": [ {"brand": "Motilium", "dosage": "10mg", "unit": "Viên", "instr": "Ngày uống 3 viên trước ăn"} ],
            "Gaviscon": [ {"brand": "Gaviscon", "dosage": "10ml", "unit": "Gói", "instr": "Uống 1 gói sau ăn khi đau"} ],

            # --- Giảm đau / Xương khớp ---
            "Paracetamol": [ {"brand": "Panadol", "dosage": "500mg", "unit": "Viên", "instr": "Uống 1 viên khi đau/sốt, cách mỗi 4-6h"}, {"brand": "Efferalgan", "dosage": "500mg", "unit": "Viên sủi", "instr": "Hòa 1 viên vào nước, uống khi đau/sốt"} ],
            "Ibuprofen": [ {"brand": "Brufen", "dosage": "400mg", "unit": "Viên", "instr": "Uống 1 viên sau ăn khi đau"} ],
            "Celecoxib": [ {"brand": "Celebrex", "dosage": "200mg", "unit": "Viên", "instr": "Ngày uống 1 viên sau ăn no"} ],
            "Meloxicam": [ {"brand": "Mobic", "dosage": "7.5mg", "unit": "Viên", "instr": "Ngày uống 1 viên sau ăn"} ],
            "Eperisone": [ {"brand": "Myonal", "dosage": "50mg", "unit": "Viên", "instr": "Ngày uống 3 viên sau ăn"} ],
            "Glucosamine": [ {"brand": "Viartril-S", "dosage": "1500mg", "unit": "Gói", "instr": "Uống 1 gói trước ăn sáng"} ],
            "Diclofenac_Gel": [ {"brand": "Voltaren Emulgel", "dosage": "20g", "unit": "Tuýp", "instr": "Bôi vùng đau 2 lần/ngày"} ],

            # --- Tim mạch (Foundation) ---
            "Amlodipine": [{"brand": "Amlor", "dosage": "5mg", "unit": "Viên", "instr": "Ngày uống 1 viên buổi sáng"}],
            "Losartan": [{"brand": "Cozaar", "dosage": "50mg", "unit": "Viên", "instr": "Ngày uống 1 viên buổi sáng"}],
            "Telmisartan": [{"brand": "Micardis", "dosage": "40mg", "unit": "Viên", "instr": "Ngày uống 1 viên buổi sáng"}],
            "Perindopril": [{"brand": "Coversyl", "dosage": "5mg", "unit": "Viên", "instr": "Ngày uống 1 viên buổi sáng trước ăn"}],
            "Bisoprolol": [{"brand": "Concor", "dosage": "2.5mg", "unit": "Viên", "instr": "Ngày uống 1 viên buổi sáng"}],
            
            # --- Tiểu đường / Mỡ máu (Foundation) ---
            "Metformin": [{"brand": "Glucophage XR", "dosage": "750mg", "unit": "Viên", "instr": "Ngày uống 1-2 viên sau ăn tối"}],
            "Gliclazide": [{"brand": "Diamicron MR", "dosage": "30mg", "unit": "Viên", "instr": "Ngày uống 1 viên trước ăn sáng"}],
            "Sitagliptin": [{"brand": "Januvia", "dosage": "100mg", "unit": "Viên", "instr": "Ngày uống 1 viên buổi sáng"}],
            "Empagliflozin": [{"brand": "Jardiance", "dosage": "10mg", "unit": "Viên", "instr": "Ngày uống 1 viên buổi sáng"}],
            "Insulin_Glargine": [{"brand": "Lantus", "dosage": "100U/ml", "unit": "Bút tiêm", "instr": "Tiêm dưới da 10 đơn vị buổi tối"}],
            "Atorvastatin": [{"brand": "Lipitor", "dosage": "10mg", "unit": "Viên", "instr": "Ngày uống 1 viên buổi tối"}],
            "Rosuvastatin": [{"brand": "Crestor", "dosage": "10mg", "unit": "Viên", "instr": "Ngày uống 1 viên tối"}],
            "Fenofibrate": [{"brand": "Lipanthyl", "dosage": "200mg", "unit": "Viên", "instr": "Ngày uống 1 viên sau ăn trưa"}],
            "Ezetimibe": [{"brand": "Ezetrol", "dosage": "10mg", "unit": "Viên", "instr": "Ngày uống 1 viên tối"}],
            "Aspirin": [{"brand": "Aspirin Cardio", "dosage": "81mg", "unit": "Viên", "instr": "Ngày uống 1 viên sau ăn trưa"}],
            "Clopidogrel": [{"brand": "Plavix", "dosage": "75mg", "unit": "Viên", "instr": "Ngày uống 1 viên sáng"}],
            "Hydrochlorothiazide": [{"brand": "Hypothiazid", "dosage": "25mg", "unit": "Viên", "instr": "Ngày uống 1 viên sáng"}],
            "Nitroglycerin": [{"brand": "Nitromint", "dosage": "2.6mg", "unit": "Viên", "instr": "Ngày uống 2 viên (sáng, tối)"}],

            # --- Hô hấp / Dị ứng (Foundation) ---
            "Salbutamol": [ {"brand": "Ventolin", "dosage": "2mg", "unit": "Viên", "instr": "Uống 1 viên khi khó thở"} ],
            "Salbutamol_Inhaler": [ {"brand": "Ventolin Inhaler", "dosage": "100mcg", "unit": "Lọ", "instr": "Xịt 2 nhát khi lên cơn khó thở"} ],
            "Tiotropium": [ {"brand": "Spiriva", "dosage": "18mcg", "unit": "Viên", "instr": "Hít 1 viên mỗi sáng"} ],
            "Budesonide": [ {"brand": "Pulmicort", "dosage": "0.5mg", "unit": "Ống", "instr": "Khí dung 1 ống x 2 lần/ngày"} ],
            "Prednisolone": [ {"brand": "Prednisolone", "dosage": "5mg", "unit": "Viên", "instr": "Ngày uống 4 viên buổi sáng sau ăn"} ],
            "Acetylcysteine": [ {"brand": "Exomuc", "dosage": "200mg", "unit": "Gói", "instr": "Hòa tan uống, ngày 2 gói"} ],
            "Chlorpheniramine": [ {"brand": "Chlorpheniramine", "dosage": "4mg", "unit": "Viên", "instr": "Ngày uống 1 viên tối"} ],
            "Vitamin C": [ {"brand": "Upsa C", "dosage": "1000mg", "unit": "Viên sủi", "instr": "Uống 1 viên buổi sáng"} ],
            "Nước muối sinh lý": [ {"brand": "Nacl 0.9%", "dosage": "10ml", "unit": "Lọ", "instr": "Nhỏ mắt mũi ngày 3 lần"} ],
            "Cetirizine": [ {"brand": "Zyrtec", "dosage": "10mg", "unit": "Viên", "instr": "Ngày uống 1 viên tối"} ],
            "Fexofenadine": [ {"brand": "Telfast", "dosage": "180mg", "unit": "Viên", "instr": "Ngày uống 1 viên sáng"} ],
            "Amitriptyline_LowDose": [ {"brand": "Amitriptyline", "dosage": "25mg", "unit": "Viên", "instr": "Ngày uống 1/2 viên tối"} ],
            "Vitamin B_Group": [ {"brand": "Neurobion", "dosage": "Tab", "unit": "Viên", "instr": "Ngày uống 1 viên sau ăn"} ],
            "Artificial_Tears": [ {"brand": "Systane Ultra", "dosage": "10ml", "unit": "Lọ", "instr": "Nhỏ mắt khi khô, 3-4 lần/ngày"} ],
            "Vitamin A": [ {"brand": "Vitamin A", "dosage": "5000IU", "unit": "Viên", "instr": "Ngày uống 1 viên"} ],
            "Omega-3": [ {"brand": "Omega-3", "dosage": "1000mg", "unit": "Viên", "instr": "Ngày uống 1 viên sau ăn"} ],
            "Magnesium_B6": [ {"brand": "Magne-B6", "dosage": "Tab", "unit": "Viên", "instr": "Ngày uống 2 viên (sáng, tối)"} ],
             "Melatonin": [ {"brand": "Melatonin", "dosage": "5mg", "unit": "Viên", "instr": "Uống 1 viên trước ngủ 30 phút"} ],
        }

        self.doctors = [
             {"name": "Nguyễn Văn A", "title": "BS.CKI"}, {"name": "Trần Thị B", "title": "ThS.BS"},
             {"name": "Lê Vũ C", "title": "BS.CKII"}, {"name": "Phạm Minh D", "title": "TS.BS"},
             {"name": "Hoàng Thị E", "title": "BS.CKI"}, {"name": "Vũ Văn F", "title": "BS"}
        ]
        
        self.hospitals = [
            {"ministry": "BỘ Y TẾ", "name": "BVĐK TW CẦN THƠ", "phone": "0292.382.0071"},
             {"ministry": "BỘ Y TẾ", "name": "BỆNH VIỆN CHỢ RẪY", "phone": "028.3855.4137"},
             {"ministry": "SỞ Y TẾ TP.HCM", "name": "BỆNH VIỆN NHÂN DÂN 115", "phone": "028.3865.2368"},
             {"ministry": "BỘ Y TẾ", "name": "BỆNH VIỆN BẠCH MAI", "phone": "024.3869.3731"},
             {"ministry": "SỞ Y TẾ HÀ NỘI", "name": "BỆNH VIỆN XANH PÔN", "phone": "024.3823.3075"}
        ]

    def get_random_condition(self, age_group):
        candidates = [c for c in self.conditions.values() if age_group in c["types"]]
        if not candidates: return random.choice(list(self.conditions.values()))
        return random.choice(candidates)
    
    def get_drug_details(self, generic_name):
        if generic_name not in self.drugs:
            return None
        return random.choice(self.drugs[generic_name])

# ==============================================================================
# 2. GENERATOR LOGIC
# ==============================================================================
class PrescriptionGenerator:
    def __init__(self):
        self.kb = MedicalKnowledgeBase()
        self.current_id = 0

    def generate_patient(self):
        last_names = ["Nguyễn", "Trần", "Lê", "Phạm", "Hoàng", "Huỳnh", "Phan", "Vũ", "Võ", "Đặng", "Bùi", "Đỗ", "Hồ", "Ngô", "Dương", "Lý"]
        middle_names = ["Văn", "Thị", "Hữu", "Đức", "Minh", "Thu", "Ngọc", "Thanh", "Quang", "Mạnh", "Kim", "Xuân"]
        first_names = ["An", "Bình", "Cường", "Dung", "Em", "Giang", "Hải", "Lan", "Mai", "Oanh", "Khoa", "Phúc", "Tâm", "Thảo", "Hùng", "Sơn", "Tùng", "Trang"]
        
        gender = random.choice(["Nam", "Nữ"])
        name = f"{random.choice(last_names)} {random.choice(middle_names)} {random.choice(first_names)}"
        if gender == "Nam" and "Thị" in name: name = name.replace("Thị", "Văn")
        elif gender == "Nữ" and "Văn" in name: name = name.replace("Văn", "Thị")

        age_group_roll = random.random()
        if age_group_roll < 0.15: # 15% Pediatric
            age = random.randint(1, 16)
            group = "Pediatric"
        elif age_group_roll < 0.55: # 40% Adult
            age = random.randint(17, 60)
            group = "Adult"
        else: # 45% Elderly (High chance of Polypharmacy)
            age = random.randint(61, 95)
            group = "Elderly"

        address = f"{random.randint(1,999)} Đường {random.choice(['Nguyễn Huệ', 'Lê Lợi', 'Trần Hưng Đạo', '3/2', 'CMT8', 'Võ Văn Kiệt'])}, {random.choice(['Hà Nội', 'TP.HCM', 'Đà Nẵng', 'Cần Thơ', 'Hải Phòng'])}"
        insurance_code = f"DN{random.randint(4000000000, 9999999999)}"

        return {
            "name": name.upper(),
            "age": age,
            "gender": gender,
            "address": address,
            "insurance_code": insurance_code,
            "group": group
        }

    def generate_prescription(self):
        self.current_id += 1
        patient = self.generate_patient()
        doctor = random.choice(self.kb.doctors)
        # REMOVED HOSPITAL GENERATION

        # MEDICAL LOGIC: Assign Diseases
        patient_conditions = []
        
        # ROLL FOR COMPLEXITY
        # 15% Simple (1-3 meds, 1 condition)
        # 85% Complex (Multiple conditions, comorbidities)
        is_simple_case = random.random() < 0.15

        if is_simple_case:
            num_conditions = 1
        else:
            # COMPLEX LOGIC
            if patient["group"] == "Elderly":
                num_conditions = random.randint(3, 6) # High comorbidity
            elif patient["group"] == "Adult":
                num_conditions = random.randint(2, 4)
            else: # Pediatric
                num_conditions = random.choices([1, 2], weights=[0.7, 0.3])[0]
        
        chosen_codes = set()
        
        # Helper to force diversity (not just HTN all the time)
        # We define "seed" specialties to start with
        seed_specialties = ["Cardio", "Endo", "Neuro", "Resp", "GI", "Derma", "Eye"]
        weights = [0.3, 0.2, 0.15, 0.1, 0.1, 0.05, 0.1]
        
        # 1. Pick primary conditions
        for _ in range(num_conditions):
            cond = None
            
            # Smart Comorbidity Logic: If we already have Diabetes (E11), high chance to add Hypertension (I10) or Lipid (E78.0)
            if "E11" in chosen_codes and "I10" not in chosen_codes and random.random() < 0.7:
                 cond = self.kb.conditions["I10"]
            elif "E11" in chosen_codes and "E78.0" not in chosen_codes and random.random() < 0.7:
                 cond = self.kb.conditions["E78.0"]
            elif "I63.9" in chosen_codes and "I25.1" not in chosen_codes and random.random() < 0.6:
                 cond = self.kb.conditions["I25.1"]
            
            if not cond:
                # Pick random
                cond = self.kb.get_random_condition(patient["group"])
                
            if cond["code"] not in chosen_codes:
                patient_conditions.append(cond)
                chosen_codes.add(cond["code"])

        diag_str = "; ".join([f"{c['code']}: {c['name']}" for c in patient_conditions])
        
        selected_meds_list = []
        
        for cond in patient_conditions:
            possible_drugs = cond["drugs"]
            
            # Logic: Number of drugs to take from this condition
            if is_simple_case:
                 take_count = random.randint(1, min(2, len(possible_drugs)))
            else:
                 # Complex: Take more drugs (Polypharmacy)
                 # 70% chance to take 2-3 drugs if available, else 1
                 take_count = random.randint(1, len(possible_drugs))
                 # Bias towards taking more
                 if len(possible_drugs) >= 2 and random.random() < 0.7:
                     take_count = random.randint(2, len(possible_drugs))
            
            picked_generics = random.sample(possible_drugs, min(take_count, len(possible_drugs)))
            
            for generic in picked_generics:
                if any(m["generic_name"] == generic for m in selected_meds_list): continue
                
                details = self.kb.get_drug_details(generic)
                if details:
                    duration = 28 if "Chronic" in cond["types"] else 7
                    daily_dose = 1
                    if "2 viên" in details["instr"] or "2 lần" in details["instr"]: daily_dose = 2
                    if "3 viên" in details["instr"] or "3 lần" in details["instr"]: daily_dose = 3
                    
                    total_qty = duration * daily_dose
                    
                    # Randomize unit/qty slightly for realism
                    if details["unit"] == "Lọ" or details["unit"] == "Tuýp":
                        total_qty = random.randint(1, 2)

                    med_entry = {
                        "generic_name": generic,
                        "brand_name": details["brand"],
                        "dosage": details["dosage"],
                        "unit": details["unit"],
                        "quantity": total_qty,
                        "instructions": details["instr"]
                    }
                    selected_meds_list.append(med_entry)
        
        # Final check for "Simple Case": Max 3 drugs
        if is_simple_case and len(selected_meds_list) > 3:
            selected_meds_list = selected_meds_list[:3]

        # Randomize Date: Dec 2025 to Dec 2026
        start_date = datetime(2025, 12, 1)
        end_date = datetime(2026, 12, 31)
        delta_days = (end_date - start_date).days
        random_days = random.randint(0, delta_days)
        today = start_date + timedelta(days=random_days)
        
        follow_up_days = 28 if any("Chronic" in c["types"] for c in patient_conditions) else 7
        follow_up_date = (today + timedelta(days=follow_up_days)).strftime("%d/%m/%Y")
        
        return {
            "id": self.current_id,
            # "hospital": hospital, # REMOVED
            "patient": {k: v for k, v in patient.items() if k != "group"},
            "prescription_code": f"25{random.randint(100000,999999)}",
            "diagnosis": diag_str,
            "doctor": doctor,
            "medications": selected_meds_list,
            "follow_up_date": follow_up_date,
            "prescription_date": today.strftime("ngày %d tháng %m năm %Y"),
            "notes": "Tái khám nhớ mang theo đơn thuốc này." if len(selected_meds_list) > 5 else "",
            "lab_tests": "CT-Scanner, MRI, Huyết đồ" if "I63.9" in chosen_codes else "",
            "barcode_bottom": f"0000{self.current_id:08d}",
            "duration_days": follow_up_days
        }

def generate_dataset(num_records=50, output_file="generated_data.json"):
    gen = PrescriptionGenerator()
    data = {"prescriptions": [gen.generate_prescription() for _ in range(num_records)]}
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"Generated {num_records} prescriptions to {output_file}")

if __name__ == "__main__":
    # Generate 100 sample records
    generate_dataset(num_records=100, output_file="generated_sample_data.json")
