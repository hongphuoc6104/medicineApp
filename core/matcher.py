"""
core/matcher.py — Zero-PIMA wrapper for MedicineApp.

Two modes:
  Phase A: classify_prescription(ocr_blocks) → GCN classify drugname/other
  Phase B: verify_pills(pill_image, prescription_blocks) → full FRCNN+GCN matching

Usage:
    from core.matcher import ZeroPimaMatcher
    matcher = ZeroPimaMatcher()

    # Phase A: classify text blocks
    results = matcher.classify_prescription(ocr_blocks, img_w=1000, img_h=1000)
    # → [{"text": "Amoxicillin 500mg", "label": "drugname", "confidence": 0.95}, ...]

    # Phase B: verify pills
    matches = matcher.verify_pills(pill_image, prescription_blocks)
"""

import logging
import os
import sys
import warnings

import torch
import numpy as np

warnings.filterwarnings("ignore")

# Paths
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ZP = os.path.join(ROOT, "Zero-PIMA")

# Default checkpoint
_DEFAULT_WEIGHTS = os.path.join(ROOT, "models", "weights", "zero_pima_best.pth")


logger = logging.getLogger(__name__)


class ZeroPimaMatcher:
    """Wrap Zero-PIMA models for prescription classification and pill matching."""

    def __init__(self, weights_path=None, device=None):
        self.weights_path = weights_path or _DEFAULT_WEIGHTS
        self.device = device or torch.device(
            "cuda" if torch.cuda.is_available() else "cpu"
        )
        self._model_loc = None
        self._model_match = None
        self._args = None
        self._ckpt_info = None
        self._tokenizer = None

    # ── Lazy loading ──────────────────────────────────────────────────────

    def _ensure_loaded(self, need_loc=False):
        """Lazy load models on first use."""
        if self._model_match is not None and (not need_loc or self._model_loc is not None):
            return

        # Setup Zero-PIMA imports
        original_path = sys.path.copy()
        original_cwd = os.getcwd()
        sys.path.insert(0, ZP)
        if ROOT in sys.path:
            sys.path.remove(ROOT)
        os.chdir(ZP)

        try:
            import config as CFG  # noqa: F811
            from models.prescription_pill import PrescriptionPill
            from utils.utils import get_model_instance_segmentation
            from utils.option import option

            # Build args
            sys.argv = [
                "matcher.py",
                "--data-path", "data/",
                "--train-batch-size", "1",
                "--val-batch-size", "1",
                "--epochs", "50",
                "--num-workers", "0",
            ]
            self._args = option()
            self._args.json_files_test = []

            # Load checkpoint
            ckpt = torch.load(
                self.weights_path, map_location=self.device, weights_only=False
            )
            self._ckpt_info = {
                "epoch": ckpt.get("epoch", "?"),
                "loss": ckpt.get("loss", ckpt.get("best_loss", "?")),
            }

            # Auto-detect key format
            # Format A: model_match / model_loc
            # Format B: model_matching / model_localization
            # Format C: loc_state_dict (Colab notebook)
            match_key = None
            loc_key = None
            for k in ["model_match", "model_matching"]:
                if k in ckpt:
                    match_key = k
                    break
            for k in ["model_loc", "model_localization",
                       "loc_state_dict"]:
                if k in ckpt:
                    loc_key = k
                    break

            # Build matching model (always needed)
            if self._model_match is None:
                self._model_match = PrescriptionPill(self._args).to(self.device)
                if match_key:
                    self._model_match.load_state_dict(ckpt[match_key])
                else:
                    logger.warning(
                        "No matching model key found in checkpoint. "
                        "Keys: %s", list(ckpt.keys())
                    )
                self._model_match.eval()

            # Build localization model (only for Phase B)
            if need_loc and self._model_loc is None:
                self._model_loc = get_model_instance_segmentation().to(self.device)
                if loc_key:
                    self._model_loc.load_state_dict(ckpt[loc_key])
                else:
                    logger.warning(
                        "No localization model key found in checkpoint. "
                        "Keys: %s", list(ckpt.keys())
                    )
                self._model_loc.eval()

        finally:
            os.chdir(original_cwd)
            sys.path = original_path

    @property
    def checkpoint_info(self):
        """Return checkpoint metadata (epoch, loss)."""
        self._ensure_loaded()
        return self._ckpt_info

    # ── Phase A: GCN text classification ──────────────────────────────────

    def classify_prescription(self, ocr_blocks, img_w=1000, img_h=1000):
        """
        Classify OCR text blocks as drugname/other using GCN.

        Args:
            ocr_blocks: list of dicts, each with "text" and "bbox" [xmin,ymin,xmax,ymax]
            img_w, img_h: image dimensions for normalizing bbox

        Returns:
            list of dicts: {text, label, confidence, bbox}
        """
        self._ensure_loaded(need_loc=False)

        import networkx as nx
        from torch_geometric.utils.convert import from_networkx
        from transformers import AutoTokenizer

        if self._tokenizer is None:
            self._tokenizer = AutoTokenizer.from_pretrained(
                self._args.text_model_name
            )

        # Setup ZP imports for config
        sys.path.insert(0, ZP)
        import config as CFG

        # Build graph
        G = self._build_graph(ocr_blocks, img_w, img_h, CFG)
        if len(G.nodes) == 0:
            return []

        data = from_networkx(G)

        # Tokenize
        text_enc = self._tokenizer(
            data.text,
            max_length=64,
            padding="max_length",
            truncation=True,
            return_tensors="pt",
        )
        data.text_sentences_ids = text_enc.input_ids.to(self.device)
        data.text_sentences_mask = text_enc.attention_mask.to(self.device)

        # Forward GCN only
        with torch.no_grad():
            sentences_feature = self._model_match.sentences_encoder(
                data.text_sentences_ids, data.text_sentences_mask
            )
            graph_extract = self._model_match.forward_graph(
                data.to(self.device), sentences_feature
            )
            probs = torch.exp(graph_extract)  # log_softmax → softmax
            pred_labels = torch.argmax(probs, dim=1)  # 0=drugname, 1=other

        # Build results
        labels_map = {0: "drugname", 1: "other"}
        results = []
        for i, block in enumerate(ocr_blocks):
            pred_idx = pred_labels[i].item()
            drugname_prob = probs[i][0].item()
            results.append({
                "text": block.get("text", ""),
                "label": labels_map[pred_idx],
                "confidence": round(drugname_prob, 4),
                "bbox": block.get("bbox", []),
            })

        return results

    # ── Phase B: Full pill verification ───────────────────────────────────

    def verify_pills(self, pill_image, prescription_blocks, img_w=1000, img_h=1000):
        """
        Full Zero-PIMA: detect pills + match to prescription drugs.

        Args:
            pill_image: numpy array (BGR) or PIL Image
            prescription_blocks: list of dicts (same format as classify_prescription)
            img_w, img_h: prescription image dimensions

        Returns:
            list of dicts: {pill_idx, matched_drug, confidence, bbox}
        """
        self._ensure_loaded(need_loc=True)

        import networkx as nx
        from torch_geometric.utils.convert import from_networkx
        from transformers import AutoTokenizer
        from PIL import Image
        import torchvision.transforms.functional as TF

        if self._tokenizer is None:
            self._tokenizer = AutoTokenizer.from_pretrained(
                self._args.text_model_name
            )

        sys.path.insert(0, ZP)
        import config as CFG

        # ── FRCNN: detect pills ──
        if isinstance(pill_image, np.ndarray):
            import cv2
            rgb = cv2.cvtColor(pill_image, cv2.COLOR_BGR2RGB)
            pil_img = Image.fromarray(rgb)
        else:
            pil_img = pill_image

        tensor = TF.to_tensor(pil_img).unsqueeze(0).to(self.device)

        with torch.no_grad():
            frcnn_out = self._model_loc(tensor)

        pred = frcnn_out[0]
        if len(pred["boxes"]) == 0:
            return {"detections": [], "matches": []}

        # Get features from detected pills
        pill_features = pred.get("features", None)
        pill_boxes = pred["boxes"].cpu().tolist()
        pill_scores = pred["scores"].cpu().tolist()

        detections = []
        for i, (box, score) in enumerate(zip(pill_boxes, pill_scores)):
            if score >= 0.5:
                detections.append({
                    "pill_idx": i,
                    "bbox": [round(c, 1) for c in box],
                    "score": round(score, 3),
                })

        # ── GCN: classify prescription text ──
        G = self._build_graph(prescription_blocks, img_w, img_h, CFG)
        data = from_networkx(G)

        text_enc = self._tokenizer(
            data.text, max_length=64, padding="max_length",
            truncation=True, return_tensors="pt",
        )
        data.text_sentences_ids = text_enc.input_ids.to(self.device)
        data.text_sentences_mask = text_enc.attention_mask.to(self.device)

        # ── Matching ──
        # Note: full matching requires gt_feature from FRCNN
        # This is a simplified version; full contrastive matching
        # requires the patched roi_heads.py that returns gt_feature
        with torch.no_grad():
            sentences_feature = self._model_match.sentences_encoder(
                data.text_sentences_ids, data.text_sentences_mask
            )
            graph_extract = self._model_match.forward_graph(
                data.to(self.device), sentences_feature
            )
            graph_predict = torch.nn.functional.softmax(graph_extract, dim=-1)
            graph_predict = graph_predict[:, 0].unsqueeze(1)

            # Project text
            text_proj = self._model_match.sentences_projection(sentences_feature)
            text_proj = graph_predict * text_proj  # GCN attention gate

        # Build drug names from drugname-classified blocks
        drug_blocks = []
        for i, block in enumerate(prescription_blocks):
            pred_idx = torch.argmax(graph_extract[i]).item()
            if pred_idx == 0:  # drugname
                drug_blocks.append({
                    "idx": i,
                    "text": block.get("text", ""),
                    "embedding_idx": i,
                })

        return {
            "detections": detections,
            "drug_blocks": drug_blocks,
            "note": "Full contrastive matching requires patched roi_heads.py with gt_feature output",
        }

    # ── Helpers ────────────────────────────────────────────────────────────

    @staticmethod
    def _normalize_bbox(bbox):
        """
        Convert bbox to [xmin, ymin, xmax, ymax].

        Handles:
          - 4-point polygon: [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]
          - Simple rect: [xmin, ymin, xmax, ymax]
        """
        if not bbox:
            return [0, 0, 10, 10]

        # 4-point polygon format
        if isinstance(bbox[0], (list, tuple)):
            xs = [p[0] for p in bbox]
            ys = [p[1] for p in bbox]
            return [min(xs), min(ys), max(xs), max(ys)]

        # Already [xmin, ymin, xmax, ymax]
        if len(bbox) == 4:
            return list(bbox)

        return [0, 0, 10, 10]

    def _build_graph(self, blocks, img_w, img_h, CFG):
        """Build networkx graph from text blocks (same logic as data.py)."""
        import networkx as nx

        G = nx.Graph()
        bboxes = [dict(b) for b in blocks]

        # Pre-normalize all bboxes
        for b in bboxes:
            b["bbox"] = self._normalize_bbox(b.get("bbox"))

        for src_idx, src_row in enumerate(bboxes):
            label = src_row.get("label", "other").lower()
            if label not in ("drugname", "other"):
                label = "other"

            y_label = torch.tensor(
                CFG.LABELS.index(label), dtype=torch.long
            )
            xmin, ymin, xmax, ymax = src_row["bbox"]

            G.add_node(
                src_idx,
                text=src_row.get("text", ""),
                text_information=" ",
                bbox=[
                    xmin / img_w, ymin / img_h,
                    xmax / img_w, ymax / img_h,
                ],
                prescription_label=y_label,
                pills_label_in_prescription=torch.tensor(
                    -1, dtype=torch.long
                ),
            )

            src_range_x = (xmin, xmax)
            src_range_y = (ymin, ymax)
            neighbor_hozi_right = []
            neighbor_vert_bot = []

            for dest_idx, dest_row in enumerate(bboxes):
                if dest_idx == src_idx:
                    continue
                dxmin, dymin, dxmax, dymax = dest_row["bbox"]
                dest_range_x = (dxmin, dxmax)
                dest_range_y = (dymin, dymax)

                if (max(src_range_x[0], dest_range_x[0])
                        < min(src_range_x[1], dest_range_x[1])):
                    if dest_range_y[0] >= src_range_y[1]:
                        neighbor_vert_bot.append(dest_idx)

                if (max(src_range_y[0], dest_range_y[0])
                        < min(src_range_y[1], dest_range_y[1])):
                    if dest_range_x[0] >= src_range_x[1]:
                        neighbor_hozi_right.append(dest_idx)

            if neighbor_hozi_right:
                nei = min(
                    neighbor_hozi_right,
                    key=lambda x: bboxes[x]["bbox"][0],
                )
                G.add_edge(src_idx, nei)
            if neighbor_vert_bot:
                nei = min(
                    neighbor_vert_bot,
                    key=lambda x: bboxes[x]["bbox"][1],
                )
                G.add_edge(src_idx, nei)

        return G

