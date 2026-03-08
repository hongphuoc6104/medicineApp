"""
zero_pima_loader.py — Load + cache Zero-PIMA checkpoint.

Used by Phase B only (FRCNN + GCN match).
Phase A uses PhoBERT NER instead.
Loads models lazily on first use and caches them.
"""

import logging
import os
import sys
import warnings

import torch

warnings.filterwarnings("ignore")

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ZP = os.path.join(ROOT, "Zero-PIMA")

_DEFAULT_WEIGHTS = os.path.join(ROOT, "models", "zero_pima", "zero_pima_best.pth")

logger = logging.getLogger(__name__)


class ZeroPimaLoader:
    """Load and cache Zero-PIMA models (singleton)."""

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

    def ensure_loaded(self, need_loc=False):
        """Lazy load models on first use."""
        if self._model_match is not None and (not need_loc or self._model_loc is not None):
            return

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

            ckpt = torch.load(
                self.weights_path, map_location=self.device, weights_only=False
            )
            self._ckpt_info = {
                "epoch": ckpt.get("epoch", "?"),
                "loss": ckpt.get("loss", ckpt.get("best_loss", "?")),
            }

            # Auto-detect key format
            match_key = None
            loc_key = None
            for k in ["model_match", "model_matching"]:
                if k in ckpt:
                    match_key = k
                    break
            for k in ["model_loc", "model_localization", "loc_state_dict"]:
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
                        "No matching model key found. Keys: %s", list(ckpt.keys())
                    )
                self._model_match.eval()

            # Build localization model (only for Phase B)
            if need_loc and self._model_loc is None:
                self._model_loc = get_model_instance_segmentation().to(self.device)
                if loc_key:
                    self._model_loc.load_state_dict(ckpt[loc_key])
                else:
                    logger.warning(
                        "No localization model key found. Keys: %s", list(ckpt.keys())
                    )
                self._model_loc.eval()

        finally:
            os.chdir(original_cwd)
            sys.path = original_path

    @property
    def checkpoint_info(self):
        """Return checkpoint metadata (epoch, loss)."""
        self.ensure_loaded()
        return self._ckpt_info

    @property
    def model_match(self):
        self.ensure_loaded()
        return self._model_match

    @property
    def model_loc(self):
        self.ensure_loaded(need_loc=True)
        return self._model_loc

    @property
    def args(self):
        self.ensure_loaded()
        return self._args

    @property
    def tokenizer(self):
        if self._tokenizer is None:
            from transformers import AutoTokenizer
            self.ensure_loaded()
            self._tokenizer = AutoTokenizer.from_pretrained(
                self._args.text_model_name
            )
        return self._tokenizer
