"""
Prepare Synthetic & Real Multi-label BIO NER Dataset for PhoBERT.

Generates 1,200+ single-line prescription samples labeled with:
- B-DRUG / I-DRUG
- B-DOSAGE / I-DOSAGE
- B-QTY / I-QTY
- B-USAGE / I-USAGE
- O
"""
import json
import random
from pathlib import Path

ROOT = Path(__file__).parent.parent
DRUG_DB_PATH = ROOT / "data" / "drug_db_vn_full.json"
OUTPUT_DIR = ROOT / "data" / "ner_dataset"

# Fixed seed for reproducibility
random.seed(42)

# Common dosage forms & strengths
DOSAGES = [
    "500mg", "200mg", "100mg", "10mg", "5mg", "1g", "500mcg", "250mg",
    "100IU", "10IU", "2ml", "5ml", "10ml", "0.5mg", "20mg", "40mg"
]

# Common unit quantities
UNITS = ["viên", "vỉ", "hộp", "chai", "lọ", "ống", "gói", "v", "tab", "caps"]

# Common usage instructions
USAGES = [
    "uống 1 viên sau ăn sáng",
    "ngày uống 2 lần, mỗi lần 1 viên sau ăn",
    "sáng 1v - tối 1v (sau ăn)",
    "thoa ngoài da ngày 2-3 lần",
    "nhỏ mắt 1-2 giọt mỗi ngày",
    "hòa nước uống trước bữa ăn 30 phút",
    "uống khi đau, tối đa 3 viên/ngày",
    "uống 1 viên trước khi đi ngủ",
    "ngày 3 lần, mỗi lần 1 gói",
    "uống sau ăn 15 phút"
]

NOISE_PREFIXES = [
    "1.", "2.", "3.", "4.", "5.", "1)", "2)", "3)", "01.", "02.", "STT 1:", "STT 2:"
]

NOISE_HEADERS = [
    "BS. Nguyễn Văn A", "Chẩn đoán: Viêm họng cấp", "Tái khám sau 7 ngày",
    "Đơn thuốc điều trị", "Bệnh viện Đa Khoa", "Mẫu số 01/BYT"
]

def load_drugs():
    """Load drug names from drug_db_vn_full.json or fallback list."""
    drugs = []
    if DRUG_DB_PATH.exists():
        with open(DRUG_DB_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            drug_items = data.get("drugs", []) if isinstance(data, dict) else data
            for item in drug_items:
                if not isinstance(item, dict):
                    continue
                name = item.get("tenThuoc", "").strip()
                if name and len(name) > 2 and len(name) < 40:
                    drugs.append(name)
                # also grab generic hoatChat if available
                hoat_chat = item.get("hoatChat")
                if isinstance(hoat_chat, list):
                    for hc in hoat_chat:
                        if isinstance(hc, dict):
                            hc_name = hc.get("tenHoatChat", "").strip()
                            if hc_name and len(hc_name) > 2 and len(hc_name) < 35:
                                drugs.append(hc_name)
    if not drugs:
        drugs = [
            "Paracetamol", "Celecoxib", "Eperisone", "Mecobalamin", "Loratadine",
            "Augmentin", "Hapacol", "Efferalgan", "Amoxicillin", "Cefuroxime"
        ]
    return list(set(drugs))

def generate_sample(drug_list):
    """Generate a single prescription line with BIO tags."""
    drug = random.choice(drug_list)
    dosage = random.choice(DOSAGES)
    qty_val = random.randint(1, 60)
    qty_unit = random.choice(UNITS)
    qty_str = f"{qty_val} {qty_unit}"
    usage = random.choice(USAGES)
    
    prefix = random.choice(NOISE_PREFIXES) if random.random() < 0.8 else ""
    
    # Sentence construction pattern variants
    pattern = random.choice([1, 2, 3, 4])
    
    tokens = []
    labels = []
    
    if prefix:
        for p in prefix.split():
            tokens.append(p)
            labels.append("O")
            
    # DRUG tokens
    drug_words = drug.split()
    for i, w in enumerate(drug_words):
        tokens.append(w)
        labels.append("B-DRUG" if i == 0 else "I-DRUG")
        
    # DOSAGE tokens
    dosage_words = dosage.split()
    for i, w in enumerate(dosage_words):
        tokens.append(w)
        labels.append("B-DOSAGE" if i == 0 else "I-DOSAGE")
        
    if pattern in [1, 2]:
        # QTY first, then USAGE
        tokens.append("-")
        labels.append("O")
        for i, w in enumerate(qty_str.split()):
            tokens.append(w)
            labels.append("B-QTY" if i == 0 else "I-QTY")
            
        tokens.append("-")
        labels.append("O")
        for i, w in enumerate(usage.split()):
            tokens.append(w)
            labels.append("B-USAGE" if i == 0 else "I-USAGE")
    else:
        # USAGE first, then QTY
        tokens.append("-")
        labels.append("O")
        for i, w in enumerate(usage.split()):
            tokens.append(w)
            labels.append("B-USAGE" if i == 0 else "I-USAGE")
            
        tokens.append("-")
        labels.append("O")
        for i, w in enumerate(qty_str.split()):
            tokens.append(w)
            labels.append("B-QTY" if i == 0 else "I-QTY")
            
    return {"tokens": tokens, "ner_tags": labels}

def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    drugs = load_drugs()
    print(f"Loaded {len(drugs)} unique drug names.")
    
    samples = []
    for _ in range(1200):
        samples.append(generate_sample(drugs))
        
    # Add noise-only samples (headers, doctor notes)
    for h in NOISE_HEADERS:
        tokens = h.split()
        labels = ["O"] * len(tokens)
        samples.append({"tokens": tokens, "ner_tags": labels})
        
    random.shuffle(samples)
    
    split_idx = int(len(samples) * 0.85)
    train_samples = samples[:split_idx]
    val_samples = samples[split_idx:]
    
    with open(OUTPUT_DIR / "train.json", "w", encoding="utf-8") as f:
        json.dump(train_samples, f, ensure_ascii=False, indent=2)
        
    with open(OUTPUT_DIR / "val.json", "w", encoding="utf-8") as f:
        json.dump(val_samples, f, ensure_ascii=False, indent=2)
        
    print(f"✅ Created {len(train_samples)} train samples & {len(val_samples)} val samples in {OUTPUT_DIR}")

if __name__ == "__main__":
    main()
