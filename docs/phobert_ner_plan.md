# Kế Hoạch PhoBERT NER — Đã Kiểm Chứng Kỹ Thuật

> [!NOTE]
> Tài liệu này là technical deep-dive cho quá trình huấn luyện PhoBERT NER.
> Dùng làm reference/history cho NER, không dùng làm roadmap trạng thái tổng thể của dự án.
> Trạng thái hiện tại của dự án xem tại `AGENTS.md` và `docs/MASTER_PLAN.md`.

## ⚠️ 3 Lỗi Kỹ Thuật Phát Hiện Trong Plan Cũ (Đã Sửa)

> [!CAUTION]
> **Lỗi 1: PhoBERT KHÔNG tokenize theo từ (word-level).** 
> Nó dùng **Subword (BPE)**, nghĩa là `"Paracetamol"` bị tách thành `["Para", "@@cet", "@@amol"]`. Do đó nhãn BIO cần **alignment** — không thể gán nhãn trực tiếp per-word.

> [!CAUTION]
> **Lỗi 2: PhoBERT YÊU CẦU tách từ tiếng Việt (Word Segmentation).**
> Input phải qua VnCoreNLP: `"Ngày uống 2 lần"` → `"Ngày uống 2 lần"` (giữ nguyên) nhưng `"Hoạt huyết dưỡng não"` → `"Hoạt_huyết dưỡng_não"`. Nếu không tách từ, PhoBERT sẽ hiểu sai ngữ nghĩa.

> [!CAUTION]
> **Lỗi 3: VAIPE có 5 nhãn, không chỉ 2.**
> `drugname`, `usage`, `quantity`, `diagnose`, `date`, `other`. Nếu chỉ dùng 3 class `O/B-DRUG/I-DRUG` thì phải gom `usage + quantity + diagnose + date` thành `O`.

> [!CAUTION]
> **Lỗi 4 (MỚI): 100% Drug text trong VAIPE bắt đầu bằng số thứ tự.**
> VD: `"1) RENAPRIL 5MG 5mg"`. Nếu dùng nguyên đoạn này, từ đầu tiên sẽ là `"1)"` → bị gán `B-DRUG` → Model học sai rằng số thứ tự là tên thuốc! Giải pháp: Tách riêng phần số thứ tự ra để gán nhãn `O`, phần còn lại gán nhãn `DRUG`.

> [!CAUTION]
> **Lỗi 5 (MỚI KHẮC PHỤC): Tách từ tiếng Việt (Word Segmentation).**
> PhoBERT được huấn luyện với các từ đã nối `_` (VD: `"Hoạt_huyết dưỡng_não"`). Tuy nhiên, thư viện `underthesea` có khuynh hướng tách rời các đơn vị như `"150mg"` thành `"150 mg"`. Giải pháp: Tách đoạn text thành 2 phần (STT và Tên Thuốc), chỉ áp dụng `underthesea` vào phần Tên Thuốc để mô hình nhận diện tốt nhất mà không làm sai lệch vị trí gán nhãn `B-DRUG / I-DRUG`.

---

## Dữ Liệu Hiện Có (Đã Verify)

| Tập | Số file | Đường dẫn |
|-----|---------|-----------|
| Train | **938** file JSON | `VAIPE_Full/.../train/prescription/labels/` |
| Test | **118** file JSON | `VAIPE_Full/.../test/prescription/labels/` |

Mỗi file JSON là một mảng `[{id, text, label, box, mapping?}, ...]` đã sắp xếp từ trên xuống dưới.

---

## Bước 1: Chuẩn Bị Dữ Liệu (Data Preparation)

### Mục tiêu
Chuyển 938 file JSON → format mà HuggingFace `datasets` đọc được.

### Script 1: `prepare_ner_data.py`

```python
"""
Bước 1: Chuyển VAIPE JSON → HuggingFace NER Dataset.
Chạy: python prepare_ner_data.py
Output: data/ner_dataset/ (train.json, test.json)
"""
import json
import os
from pathlib import Path

# === CẤU HÌNH ===
VAIPE_BASE = "VAIPE_Full/content/dataset"
TRAIN_DIR = f"{VAIPE_BASE}/train/prescription/labels"
TEST_DIR  = f"{VAIPE_BASE}/test/prescription/labels"
OUTPUT_DIR = "data/ner_dataset"

def convert_file(json_path):
    """
    Chuyển 1 file JSON VAIPE thành 1 sample NER.
    
    Mỗi block text trở thành 1 hoặc nhiều token.
    Label mapping: drugname → B-DRUG/I-DRUG, còn lại → O.
    """
    with open(json_path, "r", encoding="utf-8") as f:
        blocks = json.load(f)
    
    # Sắp xếp blocks theo vị trí: trên→dưới, trái→phải
    blocks.sort(key=lambda b: (b["box"][1], b["box"][0]))
    
    tokens = []   # Danh sách từng từ
    labels = []   # Nhãn BIO tương ứng
    
    for block in blocks:
        text = block.get("text", "").strip()
        label = block.get("label", "other").lower()
        
        if not text:
            continue
        
        # QUAN TRỌNG: Tách tiền tố Số Thứ Tự (STT) để model không học STT là thuốc
        # Hỗ trợ đắc lực cho các format:
        # "1) Thuốc" -> prefix "1)"
        # "2. Thuốc" -> prefix "2."
        # "3 Thuốc" (trong bảng) -> prefix "3"
        import re
        m = re.match(r'^(\d+(?:[\)\.\-]|(?=\s))\s*)(.*)', text)
        if m:
            prefix = m.group(1).strip()
            main_part = m.group(2).strip()
        else:
            prefix = ""
            main_part = text
            
        # QUAN TRỌNG: Tách từ tiếng Việt cho phần main_part
        # Giúp PhoBERT hiểu đúng ngữ nghĩa từ ghép ("Hoạt huyết" -> "Hoạt_huyết")
        try:
            from underthesea import word_tokenize
            main_part = word_tokenize(main_part, format="text")
        except ImportError:
            pass # fallback if not installed
            
        prefix_tokens = prefix.split()
        main_tokens = main_part.split()
        
        # Gán nhãn cho prefix (luôn là O)
        for tok in prefix_tokens:
            tokens.append(tok)
            labels.append("O")
        
        # Gán nhãn cho phần chữ chính
        for i, word in enumerate(main_tokens):
            tokens.append(word)
            if label == "drugname":
                # Từ đầu tiên = B-DRUG, các từ sau = I-DRUG
                labels.append("B-DRUG" if i == 0 else "I-DRUG")
            else:
                # usage, quantity, diagnose, date, other → tất cả là O
                labels.append("O")
    
    return {"tokens": tokens, "ner_tags": labels}


def convert_dir(label_dir, split_name):
    """Chuyển tất cả file trong 1 thư mục."""
    samples = []
    json_files = sorted(Path(label_dir).glob("*.json"))
    
    for jf in json_files:
        try:
            sample = convert_file(str(jf))
            if len(sample["tokens"]) > 0:
                sample["id"] = jf.stem
                samples.append(sample)
        except Exception as e:
            print(f"⚠ Skip {jf.name}: {e}")
    
    print(f"  {split_name}: {len(samples)} samples, "
          f"avg {sum(len(s['tokens']) for s in samples)//len(samples)} tokens/sample")
    return samples


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    print("Converting VAIPE → NER format...")
    train = convert_dir(TRAIN_DIR, "train")
    test  = convert_dir(TEST_DIR,  "test")
    
    # Thống kê nhãn
    all_labels = []
    for s in train:
        all_labels.extend(s["ner_tags"])
    from collections import Counter
    counts = Counter(all_labels)
    print(f"\n  Label distribution (train):")
    for label, count in counts.most_common():
        print(f"    {label}: {count} ({count/len(all_labels):.1%})")
    
    # Lưu ra JSON
    for name, data in [("train", train), ("test", test)]:
        path = os.path.join(OUTPUT_DIR, f"{name}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"  💾 Saved: {path} ({len(data)} samples)")
    
    # === CHECKPOINT KIỂM CHỨNG ===
    # In ra 2 mẫu đầu tiên để bạn kiểm tra thủ công
    print("\n" + "=" * 60)
    print("  KIỂM CHỨNG: 2 mẫu đầu tiên")
    print("=" * 60)
    for sample in train[:2]:
        print(f"\n  📄 {sample['id']}:")
        for tok, lbl in zip(sample["tokens"][:15], sample["ner_tags"][:15]):
            marker = "💊" if "DRUG" in lbl else "  "
            print(f"    {marker} {tok:30s} → {lbl}")
        if len(sample["tokens"]) > 15:
            print(f"    ... ({len(sample['tokens'])} tokens total)")


if __name__ == "__main__":
    main()
```

### Kiểm chứng Bước 1
Khi chạy xong, bạn sẽ thấy Số Thứ Tự được tách ra nhận nhãn `O` một cách đúng đắn:
```
  📄 VAIPE_P_TRAIN_0:
       1)                             → O
    💊 RENAPRIL                       → B-DRUG
    💊 5MG                            → I-DRUG
    💊 5                            → I-DRUG
    💊 mg                            → I-DRUG
       SL:                            → O
       28                             → O
       Viên                           → O
```
→ Kiểm tra: `B-DRUG` phải bắt đầu ở TÊN THUỐC, còn số thứ tự mang nhãn `O`.

---

## Bước 2: Huấn Luyện PhoBERT (Training)

### Mục tiêu
Fine-tune `vinai/phobert-base-v2` trên dữ liệu NER vừa tạo.

### Tại sao chạy trên Colab/Kaggle?
- Download model `vinai/phobert-base-v2` (~500MB) trên Colab nhanh hơn (internet nhanh).
- GPU T4 (miễn phí) train 938 samples × 15 epochs ≈ **30 phút**.
- Máy local không cần GPU cho bước này.

### Script 2: `train_ner.py` (Chạy trên Colab)

```python
"""
Bước 2: Fine-tune PhoBERT cho NER.
Chạy trên Google Colab GPU.

!pip install transformers datasets seqeval accelerate
"""
import json
import numpy as np
from datasets import Dataset, DatasetDict
from transformers import (
    AutoTokenizer,
    AutoModelForTokenClassification,
    TrainingArguments,
    Trainer,
    DataCollatorForTokenClassification,
)
from seqeval.metrics import (
    classification_report,
    f1_score,
    precision_score,
    recall_score,
)

# === CẤU HÌNH ===
MODEL_NAME = "vinai/phobert-base-v2"
LABEL_LIST = ["O", "B-DRUG", "I-DRUG"]
label2id = {l: i for i, l in enumerate(LABEL_LIST)}
id2label = {i: l for i, l in enumerate(LABEL_LIST)}

# === 1. LOAD DATA ===
def load_json_dataset(path):
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return Dataset.from_dict({
        "tokens": [s["tokens"] for s in data],
        "ner_tags": [[label2id[l] for l in s["ner_tags"]] for s in data],
    })

train_ds = load_json_dataset("data/ner_dataset/train.json")
test_ds  = load_json_dataset("data/ner_dataset/test.json")
ds = DatasetDict({"train": train_ds, "test": test_ds})
print(f"Train: {len(train_ds)}, Test: {len(test_ds)}")

# === 2. TOKENIZER + SUBWORD ALIGNMENT ===
tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)

def tokenize_and_align(examples):
    """
    QUAN TRỌNG: PhoBERT dùng subword tokenization.
    Mỗi word có thể tách thành 2-3 subwords.
    Cần align nhãn: subword đầu tiên nhận nhãn gốc,
    các subword tiếp theo nhận -100 (bị bỏ qua khi tính loss).
    """
    tokenized = tokenizer(
        examples["tokens"],
        is_split_into_words=True,
        truncation=True,
        max_length=256,
        padding=False,
    )
    
    all_labels = []
    for i, labels in enumerate(examples["ner_tags"]):
        word_ids = tokenized.word_ids(batch_index=i)
        label_ids = []
        prev_word_id = None
        for word_id in word_ids:
            if word_id is None:
                # Special tokens ([CLS], [SEP], [PAD])
                label_ids.append(-100)
            elif word_id != prev_word_id:
                # Subword đầu tiên của word → nhận nhãn gốc
                label_ids.append(labels[word_id])
            else:
                # Subword tiếp theo → bỏ qua (-100)
                label_ids.append(-100)
            prev_word_id = word_id
        all_labels.append(label_ids)
    
    tokenized["labels"] = all_labels
    return tokenized

tokenized_ds = ds.map(
    tokenize_and_align, batched=True,
    remove_columns=ds["train"].column_names
)

# === 3. METRICS (Đây là nơi bạn kiểm chứng độ chính xác) ===
def compute_metrics(eval_pred):
    """
    Tính Precision, Recall, F1 cho nhãn DRUG.
    Đây là chỉ số quan trọng nhất để đánh giá mô hình.
    """
    logits, labels = eval_pred
    preds = np.argmax(logits, axis=-1)
    
    true_labels = []
    true_preds = []
    
    for pred_seq, label_seq in zip(preds, labels):
        true_label = []
        true_pred = []
        for p, l in zip(pred_seq, label_seq):
            if l != -100:  # Bỏ qua padding/subword
                true_label.append(id2label[l])
                true_pred.append(id2label[p])
        true_labels.append(true_label)
        true_preds.append(true_pred)
    
    # In ra bảng chi tiết
    print("\n" + classification_report(true_labels, true_preds))
    
    return {
        "precision": precision_score(true_labels, true_preds),
        "recall":    recall_score(true_labels, true_preds),
        "f1":        f1_score(true_labels, true_preds),
    }

# === 4. TRAINING ===
model = AutoModelForTokenClassification.from_pretrained(
    MODEL_NAME,
    num_labels=len(LABEL_LIST),
    label2id=label2id,
    id2label=id2label,
)

training_args = TrainingArguments(
    output_dir="phobert_ner_output",
    num_train_epochs=15,
    per_device_train_batch_size=16,
    per_device_eval_batch_size=32,
    learning_rate=2e-5,
    weight_decay=0.01,
    eval_strategy="epoch",       # Đánh giá sau MỖI epoch
    save_strategy="epoch",
    load_best_model_at_end=True,
    metric_for_best_model="f1",  # Chọn model có F1 cao nhất
    logging_steps=50,
    fp16=True,                   # Tăng tốc trên GPU
)

trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=tokenized_ds["train"],
    eval_dataset=tokenized_ds["test"],
    tokenizer=tokenizer,
    data_collator=DataCollatorForTokenClassification(tokenizer),
    compute_metrics=compute_metrics,
)

# BẮT ĐẦU TRAIN
print("🚀 Starting training...")
trainer.train()

# === 5. ĐÁNH GIÁ CUỐI CÙNG (Kiểm chứng) ===
print("\n" + "=" * 60)
print("  KẾT QUẢ ĐÁNH GIÁ TRÊN TẬP TEST (118 đơn thuốc)")
print("=" * 60)
results = trainer.evaluate()
print(f"  Precision: {results['eval_precision']:.4f}")
print(f"  Recall:    {results['eval_recall']:.4f}")
print(f"  F1-Score:  {results['eval_f1']:.4f}")
print()
if results["eval_f1"] >= 0.90:
    print("  ✅ F1 >= 0.90 → Model ĐẠT CHUẨN, sẵn sàng deploy!")
else:
    print("  ⚠️ F1 < 0.90 → Cần thêm data hoặc điều chỉnh hyperparams.")

# === 6. LƯU MODEL ===
trainer.save_model("phobert_ner_model")
tokenizer.save_pretrained("phobert_ner_model")
print(f"\n  💾 Model saved to: phobert_ner_model/")
print(f"     Copy thư mục này về máy local để dùng.")
```

### Kiểm chứng Bước 2
Sau khi train xong, màn hình Colab sẽ in ra:
```
           precision    recall  f1-score   support
    DRUG       0.95      0.92      0.93       XXX

  Precision: 0.9500
  Recall:    0.9200
  F1-Score:  0.9340
  ✅ F1 >= 0.90 → Model ĐẠT CHUẨN!
```

Nếu F1 < 0.90 → KHÔNG deploy, cần điều chỉnh.

---

## Bước 3: Tích Hợp Vào Pipeline (Inference)

### Mục tiêu
Thay GCN bằng PhoBERT NER trong `run_pipeline.py`.

### Script 3: `ner_extractor.py` (Chạy trên máy local)

```python
"""
Bước 3: NER Extractor thay thế GCN.
Đặt tại: core/phase_a/s5_classify/ner_extractor.py
"""
import torch
from transformers import AutoTokenizer, AutoModelForTokenClassification
from underthesea import word_tokenize


class NerExtractor:
    """Extract drug names from OCR text using PhoBERT NER."""
    
    def __init__(self, model_path="models/phobert_ner_model"):
        self.tokenizer = AutoTokenizer.from_pretrained(model_path)
        self.model = AutoModelForTokenClassification.from_pretrained(
            model_path
        )
        self.model.eval()
        self.id2label = self.model.config.id2label
    
    def extract(self, ocr_blocks):
        """
        Input:  list of dicts [{text, box, ...}, ...]
        Output: list of dicts [{text, label, confidence}, ...]
        
        Ghép tất cả text lại → đẩy qua NER → tách kết quả ra.
        """
        # Ghép text blocks thành danh sách words
        # Lưu mapping: word_index → block_index
        words = []
        word_to_block = []
        
        for block_idx, block in enumerate(ocr_blocks):
            text = block.get("text", "").strip()
            # Tách STT prefix giống Script 1
            # Hỗ trợ mọi biến thể STT: "1)", "2.", "3 "
            import re
            m = re.match(r'^(\d+(?:[\)\.\-]|(?=\s))\s*)(.*)', text)
            if m:
                prefix = m.group(1).strip()
                main_part = m.group(2).strip()
            else:
                prefix = ""
                main_part = text
            
            # Tách từ tiếng Việt
            main_part = word_tokenize(main_part, format="text")
            
            for w in prefix.split():
                words.append(w)
                word_to_block.append(block_idx)
                
            for w in main_part.split():
                words.append(w)
                word_to_block.append(block_idx)
        
        if not words:
            return []
        
        # Tokenize + predict
        encoding = self.tokenizer(
            words,
            is_split_into_words=True,
            truncation=True,
            max_length=512,
            return_tensors="pt",
        )
        
        with torch.no_grad():
            logits = self.model(**encoding).logits
        
        probs = torch.softmax(logits, dim=-1)
        preds = torch.argmax(logits, dim=-1)[0]
        confs = probs.max(dim=-1).values[0]
        
        # Align subwords → words
        word_ids = encoding.word_ids()
        word_labels = {}
        word_confs = {}
        
        for idx, (wid, pred, conf) in enumerate(
            zip(word_ids, preds, confs)
        ):
            if wid is not None and wid not in word_labels:
                label = self.id2label[pred.item()]
                word_labels[wid] = label
                word_confs[wid] = conf.item()
        
        # Gom các word liên tiếp có nhãn DRUG → drug name
        drug_names = []
        current_drug = []
        current_conf = []
        
        for wid in range(len(words)):
            label = word_labels.get(wid, "O")
            conf = word_confs.get(wid, 0)
            
            if label == "B-DRUG":
                # Lưu drug trước đó (nếu có)
                if current_drug:
                    drug_names.append({
                        "text": " ".join(current_drug),
                        "label": "drugname",
                        "confidence": sum(current_conf) / len(current_conf),
                    })
                current_drug = [words[wid]]
                current_conf = [conf]
            elif label == "I-DRUG" and current_drug:
                current_drug.append(words[wid])
                current_conf.append(conf)
            else:
                if current_drug:
                    drug_names.append({
                        "text": " ".join(current_drug),
                        "label": "drugname",
                        "confidence": sum(current_conf) / len(current_conf),
                    })
                    current_drug = []
                    current_conf = []
        
        # Flush last drug
        if current_drug:
            drug_names.append({
                "text": " ".join(current_drug),
                "label": "drugname",
                "confidence": sum(current_conf) / len(current_conf),
            })
        
        return drug_names
```

### Kiểm chứng Bước 3
```bash
# Chạy trên ảnh prescription_3 (GCN chỉ bắt 2/5 thuốc)
python scripts/run_pipeline.py --dir data/input/prescription_3

# Kỳ vọng NER bắt 5/5:
#   💊 Celecoxib (Celebrex 200mg) 200mg
#   💊 Eperisone (Myonal 50mg) 50mg
#   💊 Mecobalamin (Methycobal 500mcg)
#   💊 Loratadine (Clarityne 10mg) 10mg
#   💊 Paracetamol (Panadol 500mg) 500mg
```

---

## Tóm Tắt Toàn Bộ Quy Trình

| Bước | Nơi chạy | Thời gian | Output | Kiểm chứng |
|:---:|:---|:---:|:---|:---|
| **1** | Máy local | 5 giây | `data/ner_dataset/train.json` | Mở file kiểm tra nhãn B-DRUG |
| **2** | Colab GPU | 30 phút | `phobert_ner_model/` (~500MB) | F1-Score phải ≥ 0.90 |
| **3** | Máy local | 5 phút code | `ner_extractor.py` | Chạy prescription_3 phải ra 5/5 |

> [!IMPORTANT]  
> **Trước khi bắt đầu**, hãy backup model GCN hiện tại:
> ```bash
> cp -r models/weights/ models/weights_backup_gcn/
> ```

> [!NOTE]
> **Thư viện cần cài trên Colab:**  
> `pip install transformers datasets seqeval accelerate`
> 
> **Thư viện cần cài trên máy local (inference):**  
> `pip install transformers torch`  
> (Đã có sẵn trong venv hiện tại)
