#!/usr/bin/env python3
"""
evaluate.py — Evaluate Zero-PIMA model on test set.

Usage:
    # Evaluate GCN classification (drugname/other detection)
    python scripts/evaluate.py --checkpoint models/weights/zero_pima_best.pth

    # Evaluate on BVĐK test set specifically
    python scripts/evaluate.py --checkpoint models/weights/zero_pima_best.pth \
        --test-dir data/synthetic_train/pres/test

    # Quick eval (first N samples only)
    python scripts/evaluate.py --checkpoint models/weights/zero_pima_best.pth --max-samples 10
"""
import json
import os
import sys
import argparse
import torch
import warnings
import numpy as np
from collections import defaultdict

warnings.filterwarnings("ignore")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ZP = os.path.join(ROOT, "Zero-PIMA")
sys.path.insert(0, ZP)
os.chdir(ZP)

DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")


def load_models(checkpoint_path, verbose=True):
    """Load Zero-PIMA models from checkpoint."""
    import config as CFG
    from models.prescription_pill import PrescriptionPill
    from utils.utils import get_model_instance_segmentation
    from utils.option import option

    if verbose:
        gpu = torch.cuda.get_device_name(0) if torch.cuda.is_available() else "CPU"
        print(f"  Device : {gpu}")
        print(f"  Checkpoint: {checkpoint_path}")

    sys.argv = ['evaluate.py', '--data-path', 'data/',
                '--train-batch-size', '1', '--val-batch-size', '1',
                '--epochs', '50', '--num-workers', '0']
    args = option()
    args.json_files_test = []

    model_loc = get_model_instance_segmentation().to(DEVICE)
    model_match = PrescriptionPill(args).to(DEVICE)
    graph_crit = torch.nn.NLLLoss(weight=torch.FloatTensor(CFG.labels_weight).to(DEVICE))

    ckpt = torch.load(checkpoint_path, map_location=DEVICE, weights_only=False)
    model_loc.load_state_dict(ckpt['model_loc'])
    model_match.load_state_dict(ckpt['model_match'])

    epoch = ckpt.get('epoch', '?')
    loss = ckpt.get('loss', ckpt.get('best_loss', '?'))
    if verbose:
        print(f"  Loaded: epoch={epoch}, loss={loss}")

    return model_loc, model_match, args, graph_crit


def patch_roi_heads(model_loc):
    """Apply gt_feature patch to roi_heads (safe to call multiple times)."""
    from torchvision.models.detection.roi_heads import RoIHeads
    _orig_fwd = RoIHeads.forward

    def _new_fwd(self, features, proposals, image_shapes, targets=None):
        result, losses = _orig_fwd(self, features, proposals, image_shapes, targets)
        if self.training and targets is not None:
            try:
                dtype = proposals[0].dtype
                gt_boxes = [t['boxes'].to(dtype) for t in targets]
                gt_labels = [t['labels'] for t in targets]
                gt_feat = self.box_roi_pool(features, gt_boxes, image_shapes)
                gt_feat = self.box_head(gt_feat)
                losses['gt_feature'] = gt_feat
                losses['gt_label'] = torch.cat(gt_labels)
            except Exception:
                pass
        return result, losses

    RoIHeads.forward = _new_fwd
    return model_loc


def evaluate_gcn(model_loc, model_match, test_loader, graph_crit, max_samples=None, verbose=True):
    """
    Evaluate GCN classification accuracy (drugname vs other).

    Returns metrics dict.
    """
    from utils.utils import calculate_matching_cross_loss

    model_loc.eval()
    model_match.eval()

    stats = {
        'total_samples': 0,
        'gcn_correct': 0,
        'gcn_total': 0,
        'gcn_drugname_tp': 0,
        'gcn_drugname_fp': 0,
        'gcn_drugname_fn': 0,
        'gcn_other_tp': 0,
        'losses': [],
        'skipped': 0,
    }
    per_sample = []

    with torch.no_grad():
        for i, data in enumerate(test_loader):
            if max_samples and i >= max_samples:
                break

            try:
                data = data.to(DEVICE)
                imgs = [img.to(DEVICE) for img in data.pill_image]
                lbls = [{k: v.to(DEVICE) for k, v in t[0].items()}
                        for t in data.pill_label_generate]

                if any(len(l['boxes']) == 0 for l in lbls):
                    stats['skipped'] += 1
                    continue

                # Run localization (need training mode for gt_feature)
                model_loc.train()
                out = model_loc(imgs, lbls)
                model_loc.eval()

                if 'gt_feature' not in out:
                    stats['skipped'] += 1
                    continue

                # Run matching
                # forward returns: images_proj, sent_proj, sent_info_proj,
                #                  sent_all_proj, sent_info_all_proj, graph_extract
                img_proj, sent_proj, sent_info_proj, \
                    sent_all_proj, sent_info_all_proj, g = \
                    model_match(data, out['gt_feature'])

                # GCN classification: 0=drugname, 1=other
                g_loss = graph_crit(g, data.prescription_label)
                pred_labels = torch.argmax(g, dim=1)
                gt_labels = data.prescription_label

                correct = (pred_labels == gt_labels).sum().item()
                total = len(gt_labels)
                stats['gcn_correct'] += correct
                stats['gcn_total'] += total

                for pred, gt in zip(pred_labels, gt_labels):
                    p_val, g_val = pred.item(), gt.item()
                    if g_val == 0:
                        if p_val == 0:
                            stats['gcn_drugname_tp'] += 1
                        else:
                            stats['gcn_drugname_fn'] += 1
                    else:
                        if p_val == 0:
                            stats['gcn_drugname_fp'] += 1
                        else:
                            stats['gcn_other_tp'] += 1

                # Matching loss
                m_loss = calculate_matching_cross_loss(
                    img_proj, sent_proj, sent_info_proj,
                    sent_all_proj, sent_info_all_proj,
                    data.pills_label_in_prescription,
                    data.pill_image_label)

                loss_loc = (out['loss_classifier'] + out['loss_box_reg'] +
                            out['loss_objectness'] + out['loss_rpn_box_reg'])
                total_loss = loss_loc + m_loss + g_loss
                stats['losses'].append(total_loss.item())

                stats['total_samples'] += 1

                per_sample.append({
                    'idx': i,
                    'loss': total_loss.item(),
                    'gcn_acc': correct / total if total > 0 else 0,
                    'n_drugname': (gt_labels == 0).sum().item(),
                    'n_other': (gt_labels == 1).sum().item(),
                    'n_pred_drugname': (pred_labels == 0).sum().item(),
                })

                if verbose and (i + 1) % 20 == 0:
                    acc = stats['gcn_correct'] / stats['gcn_total'] * 100
                    avg_loss = np.mean(stats['losses'])
                    print(f"  [{i+1:4d}] GCN Acc: {acc:.1f}% | "
                          f"Loss: {avg_loss:.4f} | Skip: {stats['skipped']}")

            except (RuntimeError, KeyError) as e:
                stats['skipped'] += 1
                if 'out of memory' in str(e).lower():
                    torch.cuda.empty_cache()
                continue

    # Compute final metrics
    metrics = {}
    if stats['gcn_total'] > 0:
        metrics['gcn_accuracy'] = stats['gcn_correct'] / stats['gcn_total']

        tp = stats['gcn_drugname_tp']
        fp = stats['gcn_drugname_fp']
        fn = stats['gcn_drugname_fn']
        metrics['drugname_precision'] = tp / (tp + fp) if (tp + fp) > 0 else 0
        metrics['drugname_recall'] = tp / (tp + fn) if (tp + fn) > 0 else 0
        p, r = metrics['drugname_precision'], metrics['drugname_recall']
        metrics['drugname_f1'] = 2 * p * r / (p + r) if (p + r) > 0 else 0

    if stats['losses']:
        metrics['avg_loss'] = np.mean(stats['losses'])

    metrics['total_samples'] = stats['total_samples']
    metrics['skipped'] = stats['skipped']
    metrics['per_sample'] = per_sample

    return metrics


def print_results(metrics, checkpoint_name):
    """Print formatted evaluation results."""
    print(f"\n{'='*60}")
    print(f"  EVALUATION RESULTS: {checkpoint_name}")
    print(f"{'='*60}")
    print(f"  Samples evaluated : {metrics['total_samples']}")
    print(f"  Samples skipped   : {metrics['skipped']}")
    print(f"  Average loss      : {metrics.get('avg_loss', 0):.4f}")
    print()
    print(f"  GCN Classification:")
    print(f"    Overall accuracy : {metrics.get('gcn_accuracy', 0)*100:.1f}%")
    print(f"    Drugname precision: {metrics.get('drugname_precision', 0)*100:.1f}%")
    print(f"    Drugname recall   : {metrics.get('drugname_recall', 0)*100:.1f}%")
    print(f"    Drugname F1       : {metrics.get('drugname_f1', 0)*100:.1f}%")
    print(f"{'='*60}\n")


def main():
    parser = argparse.ArgumentParser(description='Evaluate Zero-PIMA model')
    parser.add_argument('--checkpoint', required=True, help='Path to checkpoint .pth')
    parser.add_argument('--test-dir', default=None,
                        help='Path to test prescription labels (default: data/pres/test/)')
    parser.add_argument('--max-samples', type=int, default=None,
                        help='Max samples to evaluate (for quick test)')
    parser.add_argument('--quiet', action='store_true')
    args = parser.parse_args()

    checkpoint = os.path.join(ROOT, args.checkpoint) if not os.path.isabs(args.checkpoint) else args.checkpoint
    if not os.path.exists(checkpoint):
        print(f"❌ Checkpoint not found: {checkpoint}")
        sys.exit(1)

    print(f"\n{'='*60}")
    print(f"  Zero-PIMA Evaluation")
    print(f"{'='*60}")

    # Load models
    model_loc, model_match, opt_args, graph_crit = load_models(checkpoint, verbose=not args.quiet)

    # Patch roi_heads
    patch_roi_heads(model_loc)

    # Setup test data
    from utils.utils import build_loaders

    if args.test_dir:
        test_dir = os.path.join(ROOT, args.test_dir) if not os.path.isabs(args.test_dir) else args.test_dir
        # Symlink to data/pres/test if needed
        pres_test = os.path.join(ZP, 'data', 'pres', 'test')
        if os.path.islink(pres_test):
            os.unlink(pres_test)
        elif os.path.exists(pres_test):
            import shutil
            shutil.rmtree(pres_test)
        os.makedirs(os.path.dirname(pres_test), exist_ok=True)
        os.symlink(test_dir, pres_test)
        print(f"  Test data: {test_dir} ({len(os.listdir(test_dir))} files)")
    else:
        pres_test = os.path.join(ZP, 'data', 'pres', 'test')
        if os.path.exists(pres_test):
            print(f"  Test data: {pres_test} ({len(os.listdir(pres_test))} files)")
        else:
            print(f"❌ No test data at {pres_test}")
            sys.exit(1)

    test_files = sorted(os.listdir(pres_test))
    test_loader = build_loaders(test_files, mode='test', batch_size=1,
                                num_workers=0, args=opt_args)

    print(f"  Test loader: {len(test_loader.dataset)} samples")
    print()

    # Evaluate
    metrics = evaluate_gcn(model_loc, model_match, test_loader, graph_crit,
                           max_samples=args.max_samples, verbose=not args.quiet)

    # Print results
    ckpt_name = os.path.basename(checkpoint)
    print_results(metrics, ckpt_name)

    # Save results
    results_path = os.path.join(ROOT, 'output', 'eval_results.json')
    os.makedirs(os.path.dirname(results_path), exist_ok=True)
    save_metrics = {k: v for k, v in metrics.items() if k != 'per_sample'}
    save_metrics['checkpoint'] = checkpoint
    with open(results_path, 'w') as f:
        json.dump(save_metrics, f, indent=2)
    print(f"Results saved to {results_path}")


if __name__ == '__main__':
    main()
