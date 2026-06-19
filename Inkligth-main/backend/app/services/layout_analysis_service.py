import ast
import logging
import os
import threading
from pathlib import Path
from typing import Optional

import cv2
import numpy as np

from app.core.config import settings
from app.schemas.layout_analysis import LayoutBox, LayoutRegion, PageLayoutResult

logger = logging.getLogger(__name__)

_LAYOUT_MODEL_LOCK = threading.Lock()

_DEFAULT_MODEL_REPO = "wybxc/DocLayout-YOLO-DocStructBench-onnx"
_DEFAULT_MODEL_FILENAME = "doclayout_yolo_docstructbench_imgsz1024.onnx"

_BACKEND_PROVIDERS: dict[str, list[str]] = {
    "cpu": ["CPUExecutionProvider"],
    "cuda": ["CUDAExecutionProvider", "CPUExecutionProvider"],
    "dml": ["DmlExecutionProvider", "CPUExecutionProvider"],
}

_LAYOUT_CLASS_NAMES: dict[int, str] = {
    0: "title",
    1: "plain text",
    2: "abandon",
    3: "figure",
    4: "figure_caption",
    5: "table",
    6: "table_caption",
    7: "table_footnote",
    8: "isolate_formula",
    9: "formula_caption",
}

_VOID_REGION_CLASSES: set[str] = {
    "abandon", "figure", "figure_caption", "table", "table_caption",
    "table_footnote", "isolate_formula", "formula_caption"
}


class LayoutAnalysisService:
    _instance: Optional["LayoutAnalysisService"] = None
    _model: Optional[object] = None
    _model_path: Optional[str] = None
    _backend: str = "cpu"

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @property
    def is_ready(self) -> bool:
        return self._model is not None

    @property
    def model_path(self) -> Optional[str]:
        return self._model_path

    @property
    def backend(self) -> str:
        return self._backend

    @property
    def available_providers(self) -> list[str]:
        try:
            import onnxruntime
            return onnxruntime.get_available_providers()
        except Exception:
            return []

    def set_backend(self, name: str) -> None:
        global _BACKEND_PROVIDERS
        if name not in _BACKEND_PROVIDERS:
            raise ValueError(f"Unsupported backend: {name}. Choose from: {list(_BACKEND_PROVIDERS.keys())}")
        if name != self._backend:
            self._backend = name
            self._model = None
            logger.info("Layout analysis backend switched to '%s', model will reload", name)

    def _resolve_model_path(self) -> str:
        config_model_path = getattr(settings, "LAYOUT_MODEL_PATH", None)
        if config_model_path and os.path.exists(config_model_path):
            return config_model_path

        try:
            from huggingface_hub import hf_hub_download
            config_model_id = getattr(settings, "LAYOUT_MODEL_REPO", _DEFAULT_MODEL_REPO)
            config_model_filename = getattr(settings, "LAYOUT_MODEL_FILENAME", _DEFAULT_MODEL_FILENAME)
            cache_dir = os.path.join(os.path.abspath(settings.UPLOAD_DIR), ".cache", "models")
            os.makedirs(cache_dir, exist_ok=True)
            hf_endpoint = getattr(settings, "HF_ENDPOINT", "https://hf-mirror.com")
            logger.info("Downloading layout model from %s/%s (endpoint=%s)...",
                         config_model_id, config_model_filename, hf_endpoint)
            path = hf_hub_download(
                repo_id=config_model_id,
                filename=config_model_filename,
                cache_dir=cache_dir,
                endpoint=hf_endpoint,
            )
            logger.info("Layout model downloaded to: %s", path)
            return path
        except ImportError:
            logger.warning("huggingface_hub not installed, cannot auto-download layout model")
        except Exception as e:
            logger.warning("Failed to download layout model from HuggingFace: %s", e)

        local_fallback = os.path.join(
            os.path.abspath(settings.UPLOAD_DIR), ".cache", "models",
            "models--wybxc--DocLayout-YOLO-DocStructBench-onnx", "snapshots",
        )
        if os.path.isdir(local_fallback):
            for entry in os.listdir(local_fallback):
                candidate = os.path.join(local_fallback, entry, _DEFAULT_MODEL_FILENAME)
                if os.path.exists(candidate):
                    return candidate
            for root, _dirs, files in os.walk(local_fallback):
                for f in files:
                    if f.endswith(".onnx"):
                        return os.path.join(root, f)

        raise FileNotFoundError(
            "Layout analysis ONNX model not found. "
            "Please set LAYOUT_MODEL_PATH in .env or install huggingface_hub for automatic download."
        )

    def load_model(self, force_reload: bool = False) -> None:
        with _LAYOUT_MODEL_LOCK:
            if self._model is not None and not force_reload:
                return

            import onnx
            import onnxruntime

            model_path = self._resolve_model_path()
            logger.info("Loading ONNX layout model from: %s", model_path)

            model = onnx.load(model_path, load_external_data=False)
            metadata = {d.key: d.value for d in model.metadata_props}
            self._stride = ast.literal_eval(metadata["stride"])
            self._names = ast.literal_eval(metadata["names"])
            del model

            sess_options = onnxruntime.SessionOptions()
            sess_options.graph_optimization_level = onnxruntime.GraphOptimizationLevel.ORT_ENABLE_ALL

            backend_name = getattr(settings, "LAYOUT_MODEL_BACKEND", "cpu")
            self._backend = backend_name
            providers = _BACKEND_PROVIDERS.get(backend_name, _BACKEND_PROVIDERS["cpu"])

            compiled_providers = {"CoreMLExecutionProvider", "TensorrtExecutionProvider"}
            can_cache = not compiled_providers.intersection(providers)
            if can_cache:
                optimized_path = model_path + ".optimized"
                if os.path.exists(optimized_path):
                    model_path = optimized_path
                else:
                    sess_options.optimized_model_filepath = optimized_path

            self._model = onnxruntime.InferenceSession(
                model_path, sess_options, providers=providers
            )
            self._model_path = model_path
            logger.info(
                "Layout model loaded successfully. Providers: %s, Stride: %d",
                self._model.get_providers(), self._stride
            )

    def _resize_and_pad(self, image: np.ndarray, new_shape: int | tuple) -> np.ndarray:
        if isinstance(new_shape, int):
            new_shape = (new_shape, new_shape)

        h, w = image.shape[:2]
        new_h, new_w = new_shape

        r = min(new_h / h, new_w / w)
        resized_h, resized_w = int(round(h * r)), int(round(w * r))

        image = cv2.resize(image, (resized_w, resized_h), interpolation=cv2.INTER_LINEAR)

        pad_w = (new_w - resized_w) % self._stride
        pad_h = (new_h - resized_h) % self._stride
        top, bottom = pad_h // 2, pad_h - pad_h // 2
        left, right = pad_w // 2, pad_w - pad_w // 2

        image = cv2.copyMakeBorder(
            image, top, bottom, left, right, cv2.BORDER_CONSTANT, value=(114, 114, 114)
        )
        return image

    def _scale_boxes(self, img1_shape, boxes, img0_shape):
        gain = min(img1_shape[0] / img0_shape[0], img1_shape[1] / img0_shape[1])
        pad_x = round((img1_shape[1] - img0_shape[1] * gain) / 2 - 0.1)
        pad_y = round((img1_shape[0] - img0_shape[0] * gain) / 2 - 0.1)
        boxes[..., :4] = (boxes[..., :4] - [pad_x, pad_y, pad_x, pad_y]) / gain
        return boxes

    def predict(
        self,
        image: np.ndarray,
        imgsz: int = 1024,
        confidence_threshold: float = 0.25,
    ) -> PageLayoutResult:
        if self._model is None:
            self.load_model()

        orig_h, orig_w = image.shape[:2]

        pix = self._resize_and_pad(image, new_shape=imgsz)
        pix = np.transpose(pix, (2, 0, 1))
        pix = np.expand_dims(pix, axis=0)
        pix = pix.astype(np.float32) / 255.0
        new_h, new_w = pix.shape[2:]

        preds = self._model.run(None, {"images": pix})[0]

        preds = preds[preds[..., 4] > confidence_threshold]
        preds[..., :4] = self._scale_boxes((new_h, new_w), preds[..., :4], (orig_h, orig_w))

        regions_by_class: dict[str, list[LayoutBox]] = {}
        for box_data in preds:
            cls_id = int(box_data[-1])
            cls_name = self._names.get(cls_id, _LAYOUT_CLASS_NAMES.get(cls_id, f"class_{cls_id}"))
            regions_by_class.setdefault(cls_name, []).append(LayoutBox(
                x0=float(box_data[0]),
                y0=float(box_data[1]),
                x1=float(box_data[2]),
                y1=float(box_data[3]),
                confidence=float(box_data[4]),
                class_id=cls_id,
                class_name=cls_name,
            ))

        regions = [
            LayoutRegion(class_name=name, boxes=boxes)
            for name, boxes in sorted(regions_by_class.items())
        ]

        return PageLayoutResult(
            page_number=0,
            page_width=float(orig_w),
            page_height=float(orig_h),
            regions=regions,
        )

    def build_layout_mask(
        self,
        page_result: PageLayoutResult,
        target_height: int,
        target_width: int,
    ) -> np.ndarray:
        box = np.ones((target_height, target_width), dtype=np.int32)
        h, w = box.shape

        void_region_boxes = []
        text_region_boxes = []

        for region in page_result.regions:
            for b in region.boxes:
                x0 = np.clip(int(b.x0 - 1), 0, w - 1)
                y0 = np.clip(int(target_height - b.y1 - 1), 0, h - 1)
                x1 = np.clip(int(b.x1 + 1), 0, w - 1)
                y1 = np.clip(int(target_height - b.y0 + 1), 0, h - 1)

                if region.class_name in _VOID_REGION_CLASSES:
                    void_region_boxes.append((x0, y0, x1, y1))
                else:
                    text_region_boxes.append((x0, y0, x1, y1, len(text_region_boxes) + 2))

        for i, (x0, y0, x1, y1, region_id) in enumerate(text_region_boxes):
            box[y0:y1, x0:x1] = region_id

        for x0, y0, x1, y1 in void_region_boxes:
            box[y0:y1, x0:x1] = 0

        return box

    def analyze_page(
        self,
        page_image: np.ndarray,
        page_number: int = 0,
        imgsz: int = 1024,
    ) -> PageLayoutResult:
        result = self.predict(page_image, imgsz=imgsz)
        result.page_number = page_number
        return result

    def analyze_document(
        self,
        doc_path: str,
        pages: Optional[list[int]] = None,
        imgsz: int = 1024,
    ) -> list[PageLayoutResult]:
        import fitz

        doc = fitz.open(doc_path)
        total_pages = doc.page_count
        target_pages = pages if pages else list(range(total_pages))

        results: list[PageLayoutResult] = []
        for pno in target_pages:
            if pno >= total_pages:
                continue
            page = doc[pno]
            pix = page.get_pixmap(dpi=200)
            image = np.frombuffer(pix.samples, np.uint8).reshape(pix.height, pix.width, pix.n)
            if pix.n >= 3:
                image = image[:, :, :3]
            elif pix.n == 1:
                image = cv2.cvtColor(image, cv2.COLOR_GRAY2RGB)
            elif pix.n == 4:
                image = image[:, :, :3]

            result = self.analyze_page(image, page_number=pno, imgsz=imgsz)
            results.append(result)

        doc.close()
        return results


layout_analysis_service = LayoutAnalysisService()