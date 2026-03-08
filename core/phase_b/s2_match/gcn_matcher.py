"""
gcn_matcher.py — GCN pill-to-prescription matching for Phase B.

Matches detected pills to prescription drug names using Zero-PIMA GCN.

Usage:
    from core.phase_b.s2_match.gcn_matcher import GcnMatcher
    matcher = GcnMatcher()
    result = matcher.match(pill_image, prescription_blocks)
"""

import logging
import os
import sys

import numpy as np
import torch

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))
ZP = os.path.join(ROOT, "Zero-PIMA")

logger = logging.getLogger(__name__)


def _normalize_bbox(bbox):
    """Convert bbox to [xmin, ymin, xmax, ymax]."""
    if not bbox:
        return [0, 0, 10, 10]
    if isinstance(bbox[0], (list, tuple)):
        xs = [p[0] for p in bbox]
        ys = [p[1] for p in bbox]
        return [min(xs), min(ys), max(xs), max(ys)]
    if len(bbox) == 4:
        return list(bbox)
    return [0, 0, 10, 10]


def _build_graph(blocks, img_w, img_h, CFG):
    """Build networkx graph from text blocks."""
    import networkx as nx

    G = nx.Graph()
    bboxes = [dict(b) for b in blocks]

    for b in bboxes:
        b["bbox"] = _normalize_bbox(b.get("bbox"))

    for src_idx, src_row in enumerate(bboxes):
        label = src_row.get("label", "other").lower()
        if label not in ("drugname", "other"):
            label = "other"

        y_label = torch.tensor(CFG.LABELS.index(label), dtype=torch.long)
        xmin, ymin, xmax, ymax = src_row["bbox"]

        G.add_node(
            src_idx,
            text=src_row.get("text", ""),
            text_information=" ",
            bbox=[xmin / img_w, ymin / img_h, xmax / img_w, ymax / img_h],
            prescription_label=y_label,
            pills_label_in_prescription=torch.tensor(-1, dtype=torch.long),
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
            nei = min(neighbor_hozi_right, key=lambda x: bboxes[x]["bbox"][0])
            G.add_edge(src_idx, nei)
        if neighbor_vert_bot:
            nei = min(neighbor_vert_bot, key=lambda x: bboxes[x]["bbox"][1])
            G.add_edge(src_idx, nei)

    return G


class GcnMatcher:
    """Match pills to prescription drugs using FRCNN + GCN."""

    def __init__(self, loader=None):
        """
        Args:
            loader: ZeroPimaLoader instance. If None, creates one.
        """
        if loader is None:
            from core.shared.zero_pima_loader import ZeroPimaLoader
            loader = ZeroPimaLoader()
        self._loader = loader

    def match(self, pill_image, prescription_blocks, img_w=1000, img_h=1000):
        """
        Full Zero-PIMA: detect pills + match to prescription drugs.

        Args:
            pill_image: numpy array (BGR) or PIL Image
            prescription_blocks: list of dicts with "text" and "bbox"
            img_w, img_h: prescription image dimensions

        Returns:
            dict: {detections, drug_blocks, note}
        """
        self._loader.ensure_loaded(need_loc=True)

        from torch_geometric.utils.convert import from_networkx
        from PIL import Image
        import torchvision.transforms.functional as TF

        sys.path.insert(0, ZP)
        import config as CFG

        # ── FRCNN: detect pills ──
        if isinstance(pill_image, np.ndarray):
            import cv2
            rgb = cv2.cvtColor(pill_image, cv2.COLOR_BGR2RGB)
            pil_img = Image.fromarray(rgb)
        else:
            pil_img = pill_image

        device = self._loader.device
        tensor = TF.to_tensor(pil_img).unsqueeze(0).to(device)

        with torch.no_grad():
            frcnn_out = self._loader.model_loc(tensor)

        pred = frcnn_out[0]
        if len(pred["boxes"]) == 0:
            return {"detections": [], "matches": []}

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
        G = _build_graph(prescription_blocks, img_w, img_h, CFG)
        data = from_networkx(G)

        tokenizer = self._loader.tokenizer
        text_enc = tokenizer(
            data.text, max_length=64, padding="max_length",
            truncation=True, return_tensors="pt",
        )
        data.text_sentences_ids = text_enc.input_ids.to(device)
        data.text_sentences_mask = text_enc.attention_mask.to(device)

        model = self._loader.model_match
        with torch.no_grad():
            sentences_feature = model.sentences_encoder(
                data.text_sentences_ids, data.text_sentences_mask
            )
            graph_extract = model.forward_graph(
                data.to(device), sentences_feature
            )
            graph_predict = torch.nn.functional.softmax(graph_extract, dim=-1)
            graph_predict = graph_predict[:, 0].unsqueeze(1)

            text_proj = model.sentences_projection(sentences_feature)
            text_proj = graph_predict * text_proj

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
            "note": "Full contrastive matching requires patched roi_heads.py",
        }
