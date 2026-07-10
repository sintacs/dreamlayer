"""On-device object classifiers — CLIP / YOLO(ultralytics) / moondream / CoreML.

ADD-alongside: new siblings. Each is a `classify_fn(frame) -> (label, conf)`
callable for `ObjectRecognizer(classify_fn=...)` (recognizer.py untouched). All
lazy-import their dep (extras group `vision`); when absent, `__call__` returns
None so ObjectRecognizer transparently uses its built-in `_mock`.

    from dreamlayer.object_lens.recognizer import ObjectRecognizer
    from dreamlayer.object_lens.classify_backends import ClipClassifier
    rec = ObjectRecognizer(classify_fn=ClipClassifier(["snake plant","bike lock"]))
"""
from __future__ import annotations
import logging
from typing import Optional, Tuple

log = logging.getLogger("dreamlayer.classify_backends")


def _has(name: str) -> bool:
    try:
        __import__(name)
        return True
    except Exception:
        return False


class ClipClassifier:
    """Zero-shot open-vocabulary labels via CLIP (open_clip): the label whose
    text embedding is closest to the image embedding, with the softmax score as
    confidence. Real inference — lazy-loads the model on first call."""
    dep = "open_clip"
    available = _has("open_clip")

    def __init__(self, labels: Optional[list[str]] = None,
                 model_name: str = "ViT-B-32", pretrained: str = "openai"):
        self.labels = labels or []
        self.model_name = model_name
        self.pretrained = pretrained
        self._model = None
        self._preprocess = None
        self._tokenizer = None
        self._text_features = None

    def _ensure(self):
        if self._model is not None or not self.available:
            return
        try:
            import open_clip  # type: ignore
            import torch  # type: ignore  # noqa: F401
            self._model, _, self._preprocess = \
                open_clip.create_model_and_transforms(
                    self.model_name, pretrained=self.pretrained)
            self._model.eval()
            self._tokenizer = open_clip.get_tokenizer(self.model_name)
        except Exception as exc:
            log.warning("[clip] load failed: %s; mock fallback", exc)
            self._model = None

    def _embed_labels(self):
        import torch  # type: ignore
        if self._text_features is not None:
            return self._text_features
        tokens = self._tokenizer(self.labels)
        with torch.no_grad():
            feats = self._model.encode_text(tokens)
            feats = feats / feats.norm(dim=-1, keepdim=True)
        self._text_features = feats
        return feats

    def __call__(self, frame) -> Optional[Tuple[str, float]]:
        if not self.available or not self.labels:
            return None
        self._ensure()
        if self._model is None:
            return None
        try:
            import torch  # type: ignore
            from PIL import Image  # type: ignore
            import numpy as np
            img = frame
            if not isinstance(img, Image.Image):
                arr = np.asarray(img)
                if arr.dtype != np.uint8:
                    arr = (np.clip(arr, 0, 1) * 255).astype("uint8") \
                        if arr.max() <= 1.0 else arr.astype("uint8")
                img = Image.fromarray(arr).convert("RGB")
            tensor = self._preprocess(img).unsqueeze(0)
            with torch.no_grad():
                feat = self._model.encode_image(tensor)
                feat = feat / feat.norm(dim=-1, keepdim=True)
                sims = (100.0 * feat @ self._embed_labels().T).softmax(dim=-1)[0]
                idx = int(sims.argmax())
            return (self.labels[idx], float(sims[idx]))
        except Exception as exc:
            log.warning("[clip] infer failed: %s; mock fallback", exc)
            return None


class YoloClassifier:
    """YOLOv8 bounding-box detector (ultralytics), CoreML-exportable."""
    dep = "ultralytics"
    available = _has("ultralytics")

    def __init__(self, weights: str = "yolov8n.pt"):
        self._model = None
        if self.available:
            try:
                from ultralytics import YOLO  # type: ignore
                self._model = YOLO(weights)
            except Exception as exc:
                log.warning("[yolo] load failed: %s; mock fallback", exc)

    def __call__(self, frame) -> Optional[Tuple[str, float]]:
        if self._model is None:
            return None
        try:
            res = self._model(frame, verbose=False)[0]
            if not len(res.boxes):
                return None
            b = res.boxes[0]
            name = res.names[int(b.cls[0])]
            return (str(name), float(b.conf[0]))
        except Exception as exc:
            log.warning("[yolo] infer failed: %s", exc)
            return None


class MoondreamClassifier:
    """Compact VLM (moondream): ask "What is the main object?" and take the
    short answer as the label. Real inference — lazy-loads on first call.
    Confidence is a fixed prior (VLMs don't emit calibrated scores); the
    recognizer's min_confidence gate still applies."""
    dep = "moondream"
    available = _has("moondream")

    def __init__(self, prompt: str = "What is the main object? Answer in 1-3 words.",
                 confidence: float = 0.6):
        self.prompt = prompt
        self.confidence = confidence
        self._model = None

    def _ensure(self):
        if self._model is not None or not self.available:
            return
        try:
            import moondream as md  # type: ignore
            self._model = md.vl()          # loads the packaged/default weights
        except Exception as exc:
            log.warning("[moondream] load failed: %s; mock fallback", exc)
            self._model = None

    def __call__(self, frame) -> Optional[Tuple[str, float]]:
        if not self.available:
            return None
        self._ensure()
        if self._model is None:
            return None
        try:
            from PIL import Image  # type: ignore
            import numpy as np
            img = frame
            if not isinstance(img, Image.Image):
                arr = np.asarray(img)
                if arr.max() <= 1.0:
                    arr = (np.clip(arr, 0, 1) * 255).astype("uint8")
                img = Image.fromarray(arr.astype("uint8")).convert("RGB")
            answer = self._model.query(img, self.prompt).get("answer", "")
            label = str(answer).strip().strip(".").lower()
            if not label:
                return None
            return (label, self.confidence)
        except Exception as exc:
            log.warning("[moondream] infer failed: %s; mock fallback", exc)
            return None


class CoreMLClassifier:
    """CoreML on-device inference (coremltools) — Apple Silicon path. Kept a
    thin seam: a real Vela/CoreML model plugs in here when the .mlmodel exists."""
    dep = "coremltools"
    available = _has("coremltools")

    def __init__(self, model_path: Optional[str] = None):
        self.model_path = model_path

    def __call__(self, frame) -> Optional[Tuple[str, float]]:
        return None if not (self.available and self.model_path) else None


def default_classifier(labels: Optional[list[str]] = None):
    """The vision ladder: the best *installed* real backend, else None (so the
    recognizer's deterministic mock stays authoritative — the whole suite runs
    unchanged with no vision deps). YOLO (fast, boxed) → moondream (VLM) →
    CLIP (zero-shot, needs a label set). Returns a classify_fn or None."""
    if YoloClassifier.available:
        y = YoloClassifier()
        if y._model is not None:
            return y
    if MoondreamClassifier.available:
        return MoondreamClassifier()
    if ClipClassifier.available and labels:
        return ClipClassifier(labels)
    return None
