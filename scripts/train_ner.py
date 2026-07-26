"""
Train PhoBERT NER Multi-label Token Classification Model on local GPU (RTX 3050).

Fine-tunes vinai/phobert-base-v2 with 9 BIO entity tags:
- O (0)
- B-DRUG (1), I-DRUG (2)
- B-DOSAGE (3), I-DOSAGE (4)
- B-QTY (5), I-QTY (6)
- B-USAGE (7), I-USAGE (8)

Saves output model weights to models/phobert_ner_model/
"""
import json
import os
import torch
from pathlib import Path
from torch.utils.data import Dataset, DataLoader
from transformers import AutoTokenizer, AutoModelForTokenClassification, get_linear_schedule_with_warmup
from torch.optim import AdamW

ROOT = Path(__file__).parent.parent
DATA_DIR = ROOT / "data" / "ner_dataset"
OUTPUT_MODEL_DIR = ROOT / "models" / "phobert_ner_model"

LABEL_2_ID = {
    "O": 0,
    "B-DRUG": 1,
    "I-DRUG": 2,
    "B-DOSAGE": 3,
    "I-DOSAGE": 4,
    "B-QTY": 5,
    "I-QTY": 6,
    "B-USAGE": 7,
    "I-USAGE": 8
}

ID_2_LABEL = {v: k for k, v in LABEL_2_ID.items()}

class PrescriptionDataset(Dataset):
    def __init__(self, json_path, tokenizer, max_len=256):
        with open(json_path, "r", encoding="utf-8") as f:
            self.data = json.load(f)
        self.tokenizer = tokenizer
        self.max_len = max_len

    def __len__(self):
        return len(self.data)

    def __getitem__(self, idx):
        item = self.data[idx]
        tokens = item["tokens"]
        ner_tags = item["ner_tags"]

        input_ids = [self.tokenizer.cls_token_id]
        label_ids = [-100]  # CLS token label ignored

        for word, tag in zip(tokens, ner_tags):
            subwords = self.tokenizer.encode(word, add_special_tokens=False)
            if not subwords:
                subwords = [self.tokenizer.unk_token_id]
            tag_id = LABEL_2_ID.get(tag, 0)

            for j, sw in enumerate(subwords):
                if len(input_ids) >= self.max_len - 1:
                    break
                input_ids.append(sw)
                # First subword gets tag_id, rest get -100 (ignored in loss computation)
                label_ids.append(tag_id if j == 0 else -100)

        input_ids.append(self.tokenizer.sep_token_id)
        label_ids.append(-100)

        seq_len = len(input_ids)
        attention_mask = [1] * seq_len

        # Pad to max_len
        pad_len = self.max_len - seq_len
        input_ids += [self.tokenizer.pad_token_id] * pad_len
        attention_mask += [0] * pad_len
        label_ids += [-100] * pad_len

        return {
            "input_ids": torch.tensor(input_ids, dtype=torch.long),
            "attention_mask": torch.tensor(attention_mask, dtype=torch.long),
            "labels": torch.tensor(label_ids, dtype=torch.long)
        }

def train():
    os.environ["PYTORCH_CUDA_ALLOC_CONF"] = "expandable_segments:True"
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"🚀 Training PhoBERT NER on Device: {device}")
    if torch.cuda.is_available():
        print(f"   GPU Device Name: {torch.cuda.get_device_name(0)}")
        torch.cuda.empty_cache()

    base_model_name = "vinai/phobert-base-v2"
    tokenizer = AutoTokenizer.from_pretrained(base_model_name)

    train_dataset = PrescriptionDataset(DATA_DIR / "train.json", tokenizer)
    val_dataset = PrescriptionDataset(DATA_DIR / "val.json", tokenizer)

    train_loader = DataLoader(train_dataset, batch_size=16, shuffle=True)
    val_loader = DataLoader(val_dataset, batch_size=16, shuffle=False)

    model = AutoModelForTokenClassification.from_pretrained(
        base_model_name,
        num_labels=len(LABEL_2_ID),
        id2label=ID_2_LABEL,
        label2id=LABEL_2_ID
    )
    model.to(device)

    epochs = 4
    accum_steps = 4
    total_steps = (len(train_loader) // accum_steps) * epochs
    optimizer = AdamW(model.parameters(), lr=3e-5, weight_decay=0.01)
    scheduler = get_linear_schedule_with_warmup(
        optimizer, num_warmup_steps=int(0.1 * total_steps), num_training_steps=total_steps
    )

    best_val_loss = float("inf")

    for epoch in range(epochs):
        model.train()
        total_train_loss = 0.0
        optimizer.zero_grad()

        for step, batch in enumerate(train_loader):
            input_ids = batch["input_ids"].to(device)
            attention_mask = batch["attention_mask"].to(device)
            labels = batch["labels"].to(device)

            outputs = model(input_ids=input_ids, attention_mask=attention_mask, labels=labels)
            loss = outputs.loss / accum_steps
            loss.backward()

            if (step + 1) % accum_steps == 0 or (step + 1) == len(train_loader):
                torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
                optimizer.step()
                scheduler.step()
                optimizer.zero_grad()

            total_train_loss += loss.item() * accum_steps

        avg_train_loss = total_train_loss / len(train_loader)

        # Validation
        model.eval()
        total_val_loss = 0.0
        correct_tokens = 0
        total_tokens = 0

        with torch.no_grad():
            for batch in val_loader:
                input_ids = batch["input_ids"].to(device)
                attention_mask = batch["attention_mask"].to(device)
                labels = batch["labels"].to(device)

                outputs = model(input_ids=input_ids, attention_mask=attention_mask, labels=labels)
                total_val_loss += outputs.loss.item()

                preds = torch.argmax(outputs.logits, dim=-1)
                mask = labels != -100
                correct_tokens += (preds[mask] == labels[mask]).sum().item()
                total_tokens += mask.sum().item()

        avg_val_loss = total_val_loss / len(val_loader)
        accuracy = (correct_tokens / total_tokens) if total_tokens > 0 else 0.0

        print(f"Epoch {epoch+1}/{epochs} | Train Loss: {avg_train_loss:.4f} | Val Loss: {avg_val_loss:.4f} | Token Accuracy: {accuracy*100:.2f}%")

        if avg_val_loss < best_val_loss:
            best_val_loss = avg_val_loss
            OUTPUT_MODEL_DIR.mkdir(parents=True, exist_ok=True)
            model.save_pretrained(OUTPUT_MODEL_DIR)
            tokenizer.save_pretrained(OUTPUT_MODEL_DIR)
            print(f"   💾 Saved best model to {OUTPUT_MODEL_DIR}")

    print(f"\n✅ Training completed! Fine-tuned PhoBERT multi-label model saved to {OUTPUT_MODEL_DIR}")

if __name__ == "__main__":
    train()
