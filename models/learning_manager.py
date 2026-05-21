"""
OCR領域と書類種別の学習を管理するモジュール。

取引先名をキーとして以下を学習・記憶する:
- 書類種別 / 取引区分（保存時に記録）
- 手動OCRで特定したフィールドの位置（ページ比率で記録）
"""
from __future__ import annotations

import json
import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)

# 学習データの構造
# {
#   "issuers": {
#     "株式会社ABC": {
#       "doc_type": "03.請求書",
#       "transaction_type": "支出情報",
#       "save_count": 3,
#       "ocr_regions": {
#         "issue_date": [x_pct, y_pct, w_pct, h_pct],
#         "amount":     [x_pct, y_pct, w_pct, h_pct]
#       }
#     }
#   }
# }

_SCHEMA_VERSION = 1


class LearningManager:
    """取引先ごとの書類種別・OCR領域を学習・提供するクラス"""

    def __init__(self, data_path: str):
        self.data_path = data_path
        self._data: dict = self._load()

    # ------------------------------------------------------------------
    # 学習API
    # ------------------------------------------------------------------

    def learn_from_save(
        self,
        issuer: str,
        doc_type: str,
        transaction_type: str,
        ocr_regions: dict[str, tuple[float, float, float, float]],
    ) -> None:
        """保存時に書類種別とOCR領域を学習する。"""
        if not issuer:
            return
        record = self._get_or_create(issuer)
        record["doc_type"] = doc_type
        record["transaction_type"] = transaction_type
        record["save_count"] = record.get("save_count", 0) + 1

        # OCR領域を追加・更新（今回使用した領域のみ上書き）
        if "ocr_regions" not in record:
            record["ocr_regions"] = {}
        for field_name, region in ocr_regions.items():
            record["ocr_regions"][field_name] = list(region)

        self._save()
        logger.info(f"学習データを保存: {issuer} → {doc_type} ({transaction_type}), OCR領域={list(ocr_regions.keys())}")

    def learn_ocr_region(
        self,
        issuer: str,
        field_name: str,
        region_pct: tuple[float, float, float, float],
    ) -> None:
        """手動OCR実行時に領域を即座に学習する（保存前でも記録する）。"""
        if not issuer or not field_name:
            return
        record = self._get_or_create(issuer)
        if "ocr_regions" not in record:
            record["ocr_regions"] = {}
        record["ocr_regions"][field_name] = list(region_pct)
        self._save()
        logger.info(f"OCR領域を学習: {issuer}.{field_name} = {region_pct}")

    # ------------------------------------------------------------------
    # 参照API
    # ------------------------------------------------------------------

    def get_suggestion(self, issuer: str) -> Optional[dict]:
        """
        取引先名から学習データを返す。

        Returns:
            {doc_type, transaction_type, ocr_regions} または None
        """
        if not issuer:
            return None
        record = self._data.get("issuers", {}).get(issuer)
        if not record:
            return None
        return {
            "doc_type": record.get("doc_type"),
            "transaction_type": record.get("transaction_type"),
            "ocr_regions": record.get("ocr_regions", {}),
            "save_count": record.get("save_count", 0),
        }

    def known_issuers(self) -> list[str]:
        """学習済みの取引先名一覧を返す。"""
        return list(self._data.get("issuers", {}).keys())

    # ------------------------------------------------------------------
    # 内部処理
    # ------------------------------------------------------------------

    def _get_or_create(self, issuer: str) -> dict:
        issuers = self._data.setdefault("issuers", {})
        if issuer not in issuers:
            issuers[issuer] = {}
        return issuers[issuer]

    def _load(self) -> dict:
        if not os.path.exists(self.data_path):
            return {"version": _SCHEMA_VERSION, "issuers": {}}
        try:
            with open(self.data_path, encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data.get("issuers"), dict):
                raise ValueError("issuers が辞書ではありません")
            return data
        except Exception as e:
            logger.warning(f"学習データの読み込みに失敗しました（初期化します）: {e}")
            return {"version": _SCHEMA_VERSION, "issuers": {}}

    def _save(self) -> None:
        try:
            with open(self.data_path, "w", encoding="utf-8") as f:
                json.dump(self._data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"学習データの保存に失敗しました: {e}")
