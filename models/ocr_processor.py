# -*- coding: utf-8 -*-
"""
OCR処理モジュール - ndlocr-lite 常駐サーバー方式

アプリ起動時に ndlocr-lite のモデルを1回だけロードし、
以降の OCR リクエストは推論のみ実行することで高速化。
"""

import json
import logging
import os
import shutil
import subprocess
import sys
import tempfile
import threading
from pathlib import Path

logger = logging.getLogger(__name__)

def _find_ndl_python() -> str:
    """ndlocr-lite の Python 実行ファイルパスを動的に解決する。"""
    # 1) uv tool dir で tools ディレクトリを取得
    uv_exe = shutil.which("uv") or os.path.expanduser(r"~\.local\bin\uv.exe")
    if os.path.exists(uv_exe):
        try:
            result = subprocess.run(
                [uv_exe, "tool", "dir"],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0:
                tools_dir = result.stdout.strip()
                candidate = os.path.join(tools_dir, "ndlocr-lite", "Scripts", "python.exe")
                if os.path.exists(candidate):
                    return candidate
        except Exception:
            pass

    # 2) フォールバック: Roaming\uv\tools の既定パス
    fallback = os.path.expanduser(r"~\AppData\Roaming\uv\tools\ndlocr-lite\Scripts\python.exe")
    return fallback


_NDL_PYTHON = _find_ndl_python()

# 常駐サーバースクリプトのパスを解決
# PyInstallerバンドル時は sys._MEIPASS 以下に配置される
if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
    _SERVER_SCRIPT = str(Path(sys._MEIPASS) / "models" / "ndlocr_server.py")
else:
    _SERVER_SCRIPT = str(Path(__file__).parent / "ndlocr_server.py")


class _OcrServer:
    """
    ndlocr-lite モデルを常駐させる シングルトンサーバー。
    モデルは最初のリクエスト（または warm_up）時に1回だけロードされる。
    """
    _lock = threading.Lock()
    _instance = None

    @classmethod
    def get(cls) -> "_OcrServer":
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    def __init__(self):
        self._proc: subprocess.Popen | None = None
        self._proc_lock = threading.Lock()

    def _start(self):
        """サーバープロセスを起動してモデルロードを待つ。"""
        if not os.path.exists(_NDL_PYTHON):
            raise RuntimeError(
                "ndlocr-lite の Python 環境が見つかりません。\n"
                "インストールされているか確認してください。"
            )
        if not os.path.exists(_SERVER_SCRIPT):
            raise RuntimeError(f"サーバースクリプトが見つかりません: {_SERVER_SCRIPT}")

        logger.info("ndlocr-lite サーバーを起動中...")
        # Windows でコンソールウィンドウが表示されないよう CREATE_NO_WINDOW を指定
        _cflags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
        proc = subprocess.Popen(
            [_NDL_PYTHON, _SERVER_SCRIPT],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            bufsize=1,   # 行バッファ
            creationflags=_cflags,
        )

        # "READY" を待つ（最大120秒）
        import select as _select
        import time
        deadline = time.time() + 120
        while time.time() < deadline:
            line = proc.stdout.readline().strip()
            if line == "READY":
                logger.info("ndlocr-lite サーバー準備完了")
                self._proc = proc
                return
            if line.startswith("{"):
                # エラー JSON が返ってきた場合
                err = json.loads(line).get("error", line)
                raise RuntimeError(f"ndlocr-lite サーバー起動エラー: {err}")
            if proc.poll() is not None:
                stderr = proc.stderr.read()
                raise RuntimeError(f"ndlocr-lite サーバーが終了しました:\n{stderr[:500]}")

        proc.terminate()
        raise RuntimeError("ndlocr-lite サーバーの起動がタイムアウトしました（120秒）。")

    def run_ocr(self, img_path: str) -> dict:
        """画像パスを送信して OCR 結果の辞書を返す。"""
        with self._proc_lock:
            # プロセスが死んでいたら再起動
            if self._proc is None or self._proc.poll() is not None:
                self._proc = None
                self._start()

            proc = self._proc
            proc.stdin.write(img_path + "\n")
            proc.stdin.flush()

            line = proc.stdout.readline()
            if not line:
                raise RuntimeError("ndlocr-lite サーバーから応答がありませんでした。")

            result = json.loads(line)
            if "error" in result:
                raise RuntimeError(f"OCR エラー: {result['error']}")
            return result

    def shutdown(self):
        with self._proc_lock:
            if self._proc and self._proc.poll() is None:
                try:
                    self._proc.stdin.close()
                    self._proc.wait(timeout=5)
                except Exception:
                    self._proc.terminate()
                self._proc = None


class OcrProcessor:
    @staticmethod
    def warm_up(config_manager):
        """アプリ起動時にバックグラウンドでモデルをロードしておく。"""
        try:
            from PIL import Image
            server = _OcrServer.get()
            with server._proc_lock:
                if server._proc is None or server._proc.poll() is not None:
                    server._proc = None
                    server._start()
            logger.info("ndlocr-lite ウォームアップ完了")
        except Exception as e:
            logger.warning(f"OCRウォームアップ中にエラーが発生しました: {e}")

    @staticmethod
    def shutdown():
        """アプリ終了時にサーバーを停止する。"""
        _OcrServer.get().shutdown()

    def __init__(self, image, config_manager):
        self.image = image
        self.config_manager = config_manager

    def get_text_and_boxes(self, min_confidence=0):
        """OCR を実行して認識結果をリストで返す。

        Returns:
            list of dict: {text, left, top, width, height, conf}
        """
        if not os.path.exists(_NDL_PYTHON):
            raise RuntimeError(
                "ndlocr-lite が見つかりません。\n"
                "インストーラーで OCRエンジンをインストールしてください。"
            )

        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                img_path = os.path.join(tmpdir, "input.png")
                self.image.save(img_path)

                server = _OcrServer.get()
                data = server.run_ocr(img_path)

            return _parse_ndlocr_json(data, min_confidence)

        except RuntimeError:
            raise
        except Exception as e:
            raise RuntimeError(f"OCR処理中にエラーが発生しました: {e}")


def _parse_ndlocr_json(data: dict, min_confidence: float = 0) -> list:
    """ndlocr-lite の JSON 出力を {text, left, top, width, height, conf} のリストに変換。"""
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
