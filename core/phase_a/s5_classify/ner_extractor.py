"""
NER Extractor: PhoBERT-based Named Entity Recognition for drug names.
Uses a fine-tuned PhoBERT NER model to classify text blocks as drugname/other.

Strategy: Process each OCR block independently to avoid truncation.
"""
import re
import torch
from transformers import AutoTokenizer, AutoModelForTokenClassification

try:
    from underthesea import word_tokenize
    HAS_UNDERTHESEA = True
except ImportError:
    HAS_UNDERTHESEA = False

# Regex for STT prefix: "1)", "2.", "3 ", "10-"
STT_REGEX = re.compile(r'^(\d+(?:[\)\.\-]|(?=\s))\s*)(.*)')


class NerExtractor:
    """Extract drug names from OCR text blocks using PhoBERT NER."""

    def __init__(self, model_path="models/phobert_ner_model"):
        self.tokenizer = AutoTokenizer.from_pretrained(model_path)
        self.model = AutoModelForTokenClassification.from_pretrained(
            model_path
        )
        self.model.eval()
        self.id2label = self.model.config.id2label

    def _get_label(self, pred_id):
        """Get label string from prediction id (handles int/str keys)."""
        return self.id2label.get(
            pred_id, self.id2label.get(str(pred_id), "O")
        )

    def _classify_single_block(self, text):
        """
        Classify a single OCR text block.
        Returns (is_drug: bool, confidence: float).
        """
        text = text.strip()
        if not text:
            return False, 0.0

        # Strip STT prefix (same as training data prep)
        m = STT_REGEX.match(text)
        if m:
            main_part = m.group(2).strip()
        else:
            main_part = text

        # Word segment Vietnamese (same as training)
        if HAS_UNDERTHESEA and main_part:
            main_part = word_tokenize(main_part, format="text")

        words = main_part.split()
        if not words:
            return False, 0.0

        # Tokenize each word manually (no word_ids needed)
        word_subwords = []
        for word in words:
            encoded = self.tokenizer.encode(
                word, add_special_tokens=False
            )
            if not encoded:
                encoded = [self.tokenizer.unk_token_id]
            word_subwords.append(encoded)

        # Build input: [CLS] + subwords + [SEP]
        input_ids = [self.tokenizer.cls_token_id]
        word_map = [-1]  # CLS → no word

        for word_idx, subs in enumerate(word_subwords):
            if len(input_ids) + len(subs) + 1 > 256:
                break
            for j, sw in enumerate(subs):
                input_ids.append(sw)
                word_map.append(word_idx if j == 0 else -1)

        input_ids.append(self.tokenizer.sep_token_id)
        word_map.append(-1)

        # Run model
        ids_tensor = torch.tensor([input_ids])
        attn_mask = torch.ones(1, len(input_ids), dtype=torch.long)

        with torch.no_grad():
            logits = self.model(
                input_ids=ids_tensor,
                attention_mask=attn_mask,
            ).logits

        probs = torch.softmax(logits, dim=-1)
        preds = torch.argmax(logits, dim=-1)[0]
        confs = probs.max(dim=-1).values[0]

        # Count DRUG words
        drug_words = 0
        total_words = 0
        max_conf = 0.0

        for idx, wid in enumerate(word_map):
            if wid >= 0:
                total_words += 1
                label = self._get_label(preds[idx].item())
                if label in ("B-DRUG", "I-DRUG"):
                    drug_words += 1
                    max_conf = max(max_conf, confs[idx].item())

        if total_words == 0:
            return False, 0.0

        # If >= 30% of words are DRUG → classify as drugname
        is_drug = drug_words > 0 and drug_words / total_words >= 0.3
        return is_drug, max_conf

    def classify(self, ocr_blocks, **kwargs):
        """
        Classify OCR text blocks as drugname or other.

        Input:  list of dicts [{text, label, box}, ...]
        Output: list of dicts [{text, label, confidence, box}, ...]
                with label = "drugname" or "other"
        """
        results = []
        for block in ocr_blocks:
            text = block.get("text", "")
            is_drug, conf = self._classify_single_block(text)
            # VĐ4: trả "bbox" thay vì "box" để thống nhất với pipeline
            bbox = block.get("bbox") or block.get("box", [0, 0, 0, 0])
            results.append({
                "text": text,
                "label": "drugname" if is_drug else "other",
                "confidence": round(conf, 4),
                "bbox": bbox,
            })
        return results
