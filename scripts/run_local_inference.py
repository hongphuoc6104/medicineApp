"""
run_local_inference.py — Test Zero-PIMA GCN inference on local GPU (RTX 3050 4GB)

Usage:
    # Smoke test: chỉ load model, không cần data
    python scripts/run_local_inference.py --smoke

    # Single sample: inference 1 prescription JSON + ảnh pill
    python scripts/run_local_inference.py --single --pill_img PATH --pres_json PATH

    # GCN only: chỉ chạy phần GCN phân loại drugname/other (không cần pill image)
    python scripts/run_local_inference.py --gcn_only --pres_json data/pres/train/pres_001.json
"""

import sys
import os
import argparse
import json
import warnings
warnings.filterwarnings("ignore")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ZP   = os.path.join(ROOT, "Zero-PIMA")
# Insert ZP first; do NOT add ROOT (has conflicting models/ package)
sys.path.insert(0, ZP)
if ROOT in sys.path:
    sys.path.remove(ROOT)
os.chdir(ZP)  # cwd = ZP so config.py and data/ resolve correctly

import torch
import numpy as np

CHECKPOINT = os.path.join(ROOT, "models", "weights", "zero_pima_best.pth")
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")


# ── Load models ────────────────────────────────────────────────────────────────

def load_models(verbose=True):
    """Load Zero-PIMA models từ checkpoint."""
    import config as CFG
    from models.prescription_pill import PrescriptionPill
    from utils.utils import get_model_instance_segmentation
    from utils.option import option

    if verbose:
        print(f"GPU : {torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU'}")
        print(f"VRAM: {torch.cuda.get_device_properties(0).total_memory/1e9:.1f} GB" if torch.cuda.is_available() else "")
        print(f"Loading checkpoint: {CHECKPOINT}")

    # Build args (mock sys.argv để tránh conflict)
    sys.argv = ['run_local_inference.py',
                '--data-path', 'data/',
                '--train-batch-size', '1',
                '--val-batch-size', '1',
                '--epochs', '50',
                '--num-workers', '0']
    args = option()
    args.json_files_test = []

    # Build models
    model_loc   = get_model_instance_segmentation().to(DEVICE)
    model_match = PrescriptionPill(args).to(DEVICE)

    # Load checkpoint
    ckpt = torch.load(CHECKPOINT, map_location=DEVICE, weights_only=False)
    model_loc.load_state_dict(ckpt['model_loc'])
    model_match.load_state_dict(ckpt['model_match'])
    model_loc.eval()
    model_match.eval()

    if verbose:
        print(f"✅ Loaded checkpoint: epoch={ckpt['epoch']}, loss={ckpt['loss']:.4f}")

    return model_loc, model_match, args, ckpt


# ── Smoke test ─────────────────────────────────────────────────────────────────

def run_smoke():
    """Chỉ load model + verify CUDA, không cần data."""
    print("=== Smoke Test ===")
    try:
        model_loc, model_match, args, ckpt = load_models(verbose=True)

        # Count params
        loc_params   = sum(p.numel() for p in model_loc.parameters())
        match_params = sum(p.numel() for p in model_match.parameters())
        print(f"model_loc   params: {loc_params/1e6:.1f}M")
        print(f"model_match params: {match_params/1e6:.1f}M")
        if torch.cuda.is_available():
            used = torch.cuda.memory_allocated(0) / 1e9
            total = torch.cuda.get_device_properties(0).total_memory / 1e9
            print(f"VRAM used: {used:.2f}/{total:.1f} GB")

        print("\n✅ Smoke test PASSED — model loads OK on GPU!")
    except Exception as e:
        print(f"❌ Smoke test FAILED: {e}")
        import traceback; traceback.print_exc()


# ── GCN only: phân loại drugname/other từ prescription JSON ────────────────────

def run_gcn_only(pres_json_path):
    """
    Chạy chỉ phần GCN của Zero-PIMA:
    - Build graph từ prescription JSON
    - Dùng SBERT encode text → SAGEConv → predict drugname/other
    Không cần ảnh pill image.
    """
    print(f"=== GCN Inference: {os.path.basename(pres_json_path)} ===")

    import config as CFG
    from transformers import AutoTokenizer
    import networkx as nx
    from torch_geometric.utils.convert import from_networkx
    import pandas as pd

    model_loc, model_match, args, ckpt = load_models(verbose=True)

    # Load prescription JSON
    with open(pres_json_path) as f:
        prescription = json.load(f)

    print(f"\nTotal text blocks: {len(prescription)}")

    # Build graph (giống data.py nhưng không cần pill image)
    tokenizer = AutoTokenizer.from_pretrained(args.text_model_name)
    pill_info = pd.read_csv(os.path.join(ZP, "data/pill_information.csv"))

    G = _build_graph_from_pres(prescription, pill_info, imgw=1000, imgh=1000)
    data = from_networkx(G)

    # Tokenize text
    text_enc = tokenizer(data.text, max_length=64, padding='max_length',
                         truncation=True, return_tensors='pt')
    data.text_sentences_ids  = text_enc.input_ids.to(DEVICE)
    data.text_sentences_mask = text_enc.attention_mask.to(DEVICE)

    # Forward: chỉ GCN
    with torch.no_grad():
        sentences_feature = model_match.sentences_encoder(
            data.text_sentences_ids, data.text_sentences_mask)
        graph_extract = model_match.forward_graph(data.to(DEVICE), sentences_feature)
        # log_softmax → softmax để lấy prob
        probs = torch.exp(graph_extract)  # shape: [N, 2]
        pred_labels = torch.argmax(probs, dim=1)  # 0=drugname, 1=other

    # In kết quả
    print(f"\n{'Text':50s} {'GT':10s} {'Pred':10s} {'drugname%':10s}")
    print("-" * 85)
    labels_map = {0: 'drugname', 1: 'other'}

    correct = 0
    total = 0
    for i, block in enumerate(prescription):
        gt_label = block.get('label', 'other').lower()
        if gt_label not in ('drugname', 'other'):
            gt_label = 'other'

        pred_idx   = pred_labels[i].item()
        pred_label = labels_map[pred_idx]
        drugname_prob = probs[i][0].item() * 100  # prob of drugname

        is_correct = (gt_label == pred_label)
        correct += is_correct
        total   += 1

        icon = "✅" if is_correct else "❌"
        text = block.get('text', '')[:48]
        print(f"{icon} {text:50s} {gt_label:10s} {pred_label:10s} {drugname_prob:6.1f}%")

    print(f"\nAccuracy: {correct}/{total} = {100*correct/total:.1f}%")

    # Drugnames found
    drugnames = [prescription[i]['text'] for i in range(len(prescription))
                 if pred_labels[i].item() == 0]
    print(f"\nDrug names detected by GCN: {drugnames}")


def _build_graph_from_pres(prescription, pill_info, imgw, imgh):
    """Build networkx graph từ prescription JSON (giống data.py)."""
    import config as CFG
    G = _create_graph(prescription, imgw, imgh, pill_info, CFG)
    return G


def _create_graph(bboxes, imgw, imgh, pill_info, CFG):
    """Replica của PrescriptionPillData.create_graph() từ data.py."""
    import networkx as nx
    G = nx.Graph()
    bboxes_copy = [dict(b) for b in bboxes]  # deep copy để không mutate original

    for src_idx, src_row in enumerate(bboxes_copy):
        src_row['label'] = src_row.get('label', 'other').lower()
        if src_row['label'] not in ('drugname', 'other'):
            src_row['label'] = 'other'

        text_information = ' '
        if src_row['label'] == 'drugname' and src_row.get('mapping'):
            rows = pill_info[pill_info['Pill'] == src_row['mapping']]
            if len(rows) > 0:
                color = rows['Color'].values[0]
                shape = rows['Shape'].values[0]
                text_information = f"{color} {shape}"

        src_row['y'] = torch.tensor(CFG.LABELS.index(src_row['label']), dtype=torch.long)
        box = src_row.get('box', [0, 0, 10, 10])
        src_row['x_min'], src_row['y_min'], src_row['x_max'], src_row['y_max'] = box
        src_row['bbox'] = [
            src_row['x_min'] / imgw, src_row['y_min'] / imgh,
            src_row['x_max'] / imgw, src_row['y_max'] / imgh
        ]

        G.add_node(
            src_idx,
            text=src_row.get('text', ''),
            text_information=text_information,
            bbox=src_row['bbox'],
            prescription_label=src_row['y'],
            pills_label_in_prescription=torch.tensor(-1, dtype=torch.long)
        )

        src_range_x = (src_row['x_min'], src_row['x_max'])
        src_range_y = (src_row['y_min'], src_row['y_max'])

        neighbor_hozi_right = []
        neighbor_vert_bot   = []

        for dest_idx, dest_row in enumerate(bboxes_copy):
            if dest_idx == src_idx:
                continue
            db = dest_row.get('box', [0, 0, 10, 10])
            dxmin, dymin, dxmax, dymax = db
            dest_range_x = (dxmin, dxmax)
            dest_range_y = (dymin, dymax)

            if max(src_range_x[0], dest_range_x[0]) < min(src_range_x[1], dest_range_x[1]):
                if dest_range_y[0] >= src_range_y[1]:
                    neighbor_vert_bot.append(dest_idx)

            if max(src_range_y[0], dest_range_y[0]) < min(src_range_y[1], dest_range_y[1]):
                if dest_range_x[0] >= src_range_x[1]:
                    neighbor_hozi_right.append(dest_idx)

        if neighbor_hozi_right:
            nei = min(neighbor_hozi_right, key=lambda x: bboxes_copy[x].get('box', [0])[0])
            G.add_edge(src_idx, nei)
        if neighbor_vert_bot:
            nei = min(neighbor_vert_bot, key=lambda x: bboxes_copy[x].get('box', [0, 0])[1])
            G.add_edge(src_idx, nei)

    return G


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Zero-PIMA local inference")
    parser.add_argument('--smoke',     action='store_true', help='Smoke test: chỉ load model')
    parser.add_argument('--gcn_only',  action='store_true', help='GCN inference trên prescription JSON')
    parser.add_argument('--single',    action='store_true', help='Full inference: pill image + prescription')
    parser.add_argument('--pres_json', type=str, default='data/pres/train/pres_001.json')
    parser.add_argument('--pill_img',  type=str, default=None)
    args = parser.parse_args()

    if args.smoke:
        run_smoke()
    elif args.gcn_only:
        run_gcn_only(args.pres_json)
    elif args.single:
        print("Single full inference (FRCNN + GCN) — cần pill image + VAIPE data")
        print("Chạy --gcn_only trước để test GCN không cần pill image")
    else:
        # Default: smoke + gcn_only
        run_smoke()
        print()
        run_gcn_only(args.pres_json)


if __name__ == '__main__':
    main()
