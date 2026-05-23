# -*- coding: utf-8 -*-
"""
OCR処理モジュール - ndlocr-lite 使用
"""

import json
import logging
import os
import shutil
import subprocess
import tempfile

logger = logging.getLogger(__name__)

# ndlocr-lite 実行ファイルを PATH から検索、なければ uv の既定パスを参照
_NDL_EXE = (
    shutil.which("ndlocr-lite")
    or os.path.expanduser(r"~\.local\bin\ndlocr-lite.exe")
)


class OcrProcessor:
    @staticmethod
    def warm_up(config_manager):
        """ndlocr-lite の ONNX モデルを事前ロードする（バックグラウンドスレッドから呼ばれる）。"""
        try:
            from PIL import Image
            img = Image.new("RGB", (200, 100), color="white")
            with tempfile.TemporaryDirectory() as tmpdir:
                img_path = os.path.join(tmpdir, "warmup.png")
                out_dir  = os.path.join(tmpdir, "out")
                os.makedirs(out_dir)
                img.save(img_path)
                subprocess.run(
                    [_NDL_EXE, "--sourceimg", img_path, "--output", out_dir, "--json-only"],
                    capture_output=True, timeout=60,
                )
        except Exception as e:
            logger.warning(f"OCRウォームアップ中にエラーが発生しました: {e}")

    def __init__(self, image, config_manager):
        self.image = image
        self.config_manager = config_manager

    def get_text_and_boxes(self, min_confidence=0):
        """OCR を実行して認識結果をリストで返す。

        Returns:
            list of dict: {text, left, top, width, height, conf}
            Tesseract 版と同じインターフェースを維持する。
        """
        if not _NDL_EXE or not os.path.exists(_NDL_EXE):
            raise RuntimeError(
                "ndlocr-lite が見つかりません。\n"
                "コマンドプロンプトで以下を実行してください:\n"
                "  uv tool install git+https://github.com/ndl-lab/ndlocr-lite"
            )

        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                img_path = os.path.join(tmpdir, "input.png")
                out_dir  = os.path.join(tmpdir, "out")
                os.makedirs(out_dir)
                self.image.save(img_path)

                result = subprocess.run(
                    [_NDL_EXE, "--sourceimg", img_path,
                     "--output", out_dir, "--json-only"],
                    capture_output=True, text=True,
                    encoding="utf-8", timeout=120,
                )

                if result.returncode != 0:
                    raise RuntimeError(f"ndlocr-lite エラー: {result.stderr[:300]}")

                json_path = os.path.join(out_dir, "input.json")
                if not os.path.exists(json_path):
                    return []

                with open(json_path, encoding="utf-8") as f:
                    data = json.load(f)

                return _parse_ndlocr_json(data, min_confidence)

        except subprocess.TimeoutExpired:
            raise RuntimeError("OCR処理がタイムアウトしました（120秒）。")
        except RuntimeError:
            raise
        except Exception as e:
            raise RuntimeError(f"OCR処理中にエラーが発生しました: {e}")


def _parse_ndlocr_json(data: dict, min_confidence: float = 0) -> list:
    """ndlocr-lite の JSON 出力を {text, left, top, width, height, conf} のリストに変換。

    boundingBox 形式: [[left,top], [left,bottom], [right,top], [right,bottom]]
    confidence は 0〜1 → 0〜100 に変換して Tesseract 版と揃える。
    """
    results = []
    contents = data.get("contents", [])
    for block in contents:
        items = block if isinstance(block, list) else [block]
        for item in items:
            if not isinstance(item, dict):
                continue
            text = item.get("text", "").strip()
            if not text:
                continue
            conf = float(item.get("confidence", 1.0)) * 100
            if conf < min_confidence:
                continue
            bb = item.get("boundingBox", [])
            if len(bb) >= 4:
                left   = bb[0][0]
                top    = bb[0][1]
                width  = bb[2][0] - left
                height = bb[1][1] - top
            else:
                left = top = width = height = 0
            results.append({
                "text":   text,
                "left":   left,
                "top":    top,
                "width":  width,
                "height": height,
                "conf":   conf,
            })
    return results
