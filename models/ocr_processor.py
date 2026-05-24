# -*- coding: utf-8 -*-
"""
OCR処理モジュール - Windows OCR (WinRT) 方式

Windows 10/11 標準搭載の OCR エンジンを使用。
追加インストール不要（winsdk パッケージのみ必要）・高速・現代印刷文字に強い。
"""

import asyncio
import io
import logging
import threading
from typing import Optional

from PIL import Image

logger = logging.getLogger(__name__)


class _WinOcrEngine:
    """Windows OCR エンジンのシングルトンラッパー。スレッドセーフ。"""

    _lock = threading.Lock()
    _instance: Optional["_WinOcrEngine"] = None

    @classmethod
    def get(cls) -> "_WinOcrEngine":
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    def __init__(self):
        self._engine = None
        self._engine_lock = threading.Lock()

    def ensure_engine(self):
        """OCR エンジンを初期化する（初回のみ）。"""
        with self._engine_lock:
            if self._engine is not None:
                return
            try:
                from winsdk.windows.media.ocr import OcrEngine
                from winsdk.windows.globalization import Language

                lang = Language("ja")
                if OcrEngine.is_language_supported(lang):
                    self._engine = OcrEngine.try_create_from_language(lang)
                else:
                    self._engine = OcrEngine.try_create_from_user_profile_languages()

                if self._engine is None:
                    raise RuntimeError("Windows OCR エンジンの作成に失敗しました")
                logger.info("Windows OCR エンジン初期化完了")
            except ImportError:
                raise RuntimeError(
                    "winsdk パッケージが見つかりません。\n"
                    "pip install winsdk を実行してください。"
                )

    def run_ocr(self, pil_image: Image.Image) -> list:
        """PIL Image に OCR を実行して結果リストを返す。

        asyncio.run() でコルーチンを実行する。
        QThread 内から呼ばれる想定。
        """
        self.ensure_engine()
        return asyncio.run(self._recognize_async(pil_image))

    async def _recognize_async(self, pil_image: Image.Image) -> list:
        """WinRT OCR を非同期で実行する。"""
        from winsdk.windows.graphics.imaging import BitmapDecoder
        from winsdk.windows.storage.streams import InMemoryRandomAccessStream, DataWriter

        # PIL → BMP バイト列（軽量・無圧縮で高速）
        buf = io.BytesIO()
        pil_image.convert("RGB").save(buf, format="BMP")
        bmp_bytes = buf.getvalue()

        # BMP バイト列 → WinRT InMemoryRandomAccessStream
        stream = InMemoryRandomAccessStream()
        writer = DataWriter(stream.get_output_stream_at(0))
        writer.write_bytes(bytearray(bmp_bytes))
        await writer.store_async()
        stream.seek(0)

        # BitmapDecoder → SoftwareBitmap
        decoder = await BitmapDecoder.create_async(stream)
        bitmap = await decoder.get_software_bitmap_async()

        # OCR 実行
        result = await self._engine.recognize_async(bitmap)

        # LINE 単位でグループ化して返す。
        # Windows OCR は日本語を1文字ずつ word 分割することがあるため、
        # word 単位ではなく line 単位で結合することで正しい文字列順序を保つ。
        lines = []
        for line in result.lines:
            line_text = "".join(w.text for w in line.words).strip()
            if not line_text:
                continue
            # ライン全体のバウンディングボックスを計算
            xs = [int(w.bounding_rect.x) for w in line.words]
            ys = [int(w.bounding_rect.y) for w in line.words]
            x2s = [int(w.bounding_rect.x + w.bounding_rect.width) for w in line.words]
            y2s = [int(w.bounding_rect.y + w.bounding_rect.height) for w in line.words]
            left   = min(xs)
            top    = min(ys)
            width  = max(x2s) - left
            height = max(y2s) - top
            lines.append({
                "text":   line_text,
                "left":   left,
                "top":    top,
                "width":  width,
                "height": height,
                "conf":   1.0,
            })
        return lines


class OcrProcessor:
    """OCR 処理の公開インターフェース。"""

    @staticmethod
    def warm_up(config_manager):
        """アプリ起動時にバックグラウンドでエンジンを初期化しておく。"""
        def _init():
            try:
                _WinOcrEngine.get().ensure_engine()
                logger.info("Windows OCR ウォームアップ完了")
            except Exception as e:
                logger.warning(f"OCR ウォームアップ中にエラーが発生しました: {e}")

        t = threading.Thread(target=_init, daemon=True)
        t.start()

    @staticmethod
    def shutdown():
        """アプリ終了時の後処理（Windows OCR はサーバー不要）。"""
        pass

    def __init__(self, image: Image.Image, config_manager):
        self.image = image
        self.config_manager = config_manager

    def get_text_and_boxes(self, min_confidence: float = 0) -> list:
        """OCR を実行して認識結果をリストで返す。

        Returns:
            list of dict: {text, left, top, width, height, conf}
        """
        try:
            engine = _WinOcrEngine.get()
            results = engine.run_ocr(self.image)
            if min_confidence > 0:
                results = [r for r in results if r.get("conf", 1.0) * 100 >= min_confidence]
            return results
        except RuntimeError:
            raise
        except Exception as e:
            raise RuntimeError(f"OCR処理中にエラーが発生しました: {e}")
