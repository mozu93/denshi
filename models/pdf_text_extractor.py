"""テキストPDF（デジタル発行）から pdfplumber + 正規表現で帳票情報を抽出するモジュール"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Optional

import jaconv
import pdfplumber

logger = logging.getLogger(__name__)


@dataclass
class ExtractionResult:
    issue_date: Optional[str] = None       # YYYYMMDD形式
    client_name: Optional[str] = None      # 発行元・取引先名
    amount: Optional[int] = None           # 税込金額（整数）
    doc_type_hint: Optional[str] = None    # 書類種別キーワード（例: "請求書"）
    is_text_pdf: bool = False              # テキスト抽出可能なPDFかどうか
    confidence: float = 0.0              # 総合信頼度 0.0-1.0
    field_confidences: dict = field(default_factory=dict)  # フィールド別信頼度


class PdfTextExtractor:
    """テキストPDFからpdfplumber+正規表現で帳票情報を抽出する"""

    CONFIDENCE_THRESHOLD = 0.5  # この値以上のフィールドを自動入力する
    MIN_TEXT_LENGTH = 30        # テキストPDFと判断する最小文字数

    # 書類種別マッピング（正規表現 → 検索キーワード）
    DOC_TYPE_KEYWORDS = [
        (r'請求書', '請求書'),
        (r'領収[証書]', '領収証'),
        (r'見積書', '見積書'),
        (r'注文書|発注書', '注文書'),
        (r'契約書', '契約書'),
        (r'振込[明細書]*', '振込明細'),
        (r'引落[通知書]*', '引落通知'),
    ]

    _ERA_MAP = {
        '令和': 2019, '平成': 1989, '昭和': 1926, '大正': 1912, '明治': 1868,
    }

    _CORP_SUFFIX = (
        r'(?:株式会社|有限会社|合同会社|合資会社|合名会社'
        r'|一般社団法人|公益社団法人|社会福祉法人|医療法人'
        r'|学校法人|協同組合|農業協同組合|信用組合|信用金庫)'
    )

    def extract(self, pdf_path: str) -> ExtractionResult:
        """PDFを解析して帳票情報を返す。テキスト抽出できない場合は is_text_pdf=False を返す。"""
        result = ExtractionResult()
        try:
            with pdfplumber.open(pdf_path) as pdf:
                pages_text = [page.extract_text() or "" for page in pdf.pages[:3]]
            text = "\n".join(pages_text)
        except Exception as e:
            logger.warning(f"pdfplumber テキスト抽出エラー ({pdf_path}): {e}")
            return result

        clean = text.strip()
        if len(clean) < self.MIN_TEXT_LENGTH:
            return result  # スキャンPDFまたはテキストなし

        result.is_text_pdf = True
        # 全角→半角正規化（数字・記号のみ、かなは保持）
        normalized = jaconv.z2h(clean, kana=False, ascii=True, digit=True)

        date, date_conf = self._extract_date(normalized, clean)
        amount, amount_conf = self._extract_amount(normalized)
        client, client_conf = self._extract_client_name(clean)
        doc_type, doc_conf = self._extract_doc_type(clean)

        result.issue_date = date
        result.amount = amount
        result.client_name = client
        result.doc_type_hint = doc_type
        result.field_confidences = {
            'issue_date': date_conf,
            'amount': amount_conf,
            'client_name': client_conf,
            'doc_type': doc_conf,
        }
        scored = [c for c in (date_conf, amount_conf, client_conf) if c > 0]
        result.confidence = sum(scored) / len(scored) if scored else 0.0

        return result

    # -------------------------------------------------------------------------
    # 発行日抽出
    # -------------------------------------------------------------------------

    def _extract_date(self, normalized: str, original: str) -> tuple[Optional[str], float]:
        """発行日を抽出して (YYYYMMDD, 信頼度) を返す"""
        # 1. ラベル付き和暦（最高信頼度）
        m = re.search(
            r'(?:発行日|請求日|作成日|日付)[:\s：　]*'
            r'([令平昭大明][和正治]?\d+年\d{1,2}月\d{1,2}日)',
            original
        )
        if m:
            converted = self._parse_wareki(m.group(1))
            if converted:
                return converted, 0.9

        # 2. ラベル付き西暦
        m = re.search(
            r'(?:発行日|請求日|作成日|日付)[:\s：　]*'
            r'(20\d{2}[/\-\.年]\d{1,2}[/\-\.月]\d{1,2}日?)',
            normalized
        )
        if m:
            converted = self._parse_seireki(m.group(1))
            if converted:
                return converted, 0.85

        # 3. ラベルなし和暦
        for era, base in self._ERA_MAP.items():
            m = re.search(fr'{era}(\d+)年(\d{{1,2}})月(\d{{1,2}})日', original)
            if m:
                year = base + int(m.group(1)) - 1
                month, day = int(m.group(2)), int(m.group(3))
                if 1 <= month <= 12 and 1 <= day <= 31:
                    return f'{year:04d}{month:02d}{day:02d}', 0.75

        # 4. ラベルなし西暦（YYYY/MM/DD 等）
        m = re.search(r'(20\d{2})[/\-\.年](\d{1,2})[/\-\.月](\d{1,2})日?', normalized)
        if m:
            year, month, day = int(m.group(1)), int(m.group(2)), int(m.group(3))
            if 1 <= month <= 12 and 1 <= day <= 31:
                return f'{year:04d}{month:02d}{day:02d}', 0.65

        return None, 0.0

    def _parse_wareki(self, s: str) -> Optional[str]:
        for era, base in self._ERA_MAP.items():
            m = re.match(fr'{era}(\d+)年(\d{{1,2}})月(\d{{1,2}})日?', s)
            if m:
                year = base + int(m.group(1)) - 1
                month, day = int(m.group(2)), int(m.group(3))
                if 1 <= month <= 12 and 1 <= day <= 31:
                    return f'{year:04d}{month:02d}{day:02d}'
        return None

    def _parse_seireki(self, s: str) -> Optional[str]:
        m = re.match(r'(20\d{2})[/\-\.年](\d{1,2})[/\-\.月](\d{1,2})日?', s)
        if m:
            year, month, day = int(m.group(1)), int(m.group(2)), int(m.group(3))
            if 1 <= month <= 12 and 1 <= day <= 31:
                return f'{year:04d}{month:02d}{day:02d}'
        return None

    # -------------------------------------------------------------------------
    # 金額抽出
    # -------------------------------------------------------------------------

    def _extract_amount(self, normalized: str) -> tuple[Optional[int], float]:
        """税込金額を抽出して (整数金額, 信頼度) を返す"""
        # 高信頼度: 合計/請求/税込ラベル付き
        high_patterns = [
            r'(?:ご?請求金額|合計金額|税込[合計]?|お支払[合計金額]*|合計)[:\s：　¥￥\\]*([0-9,，]{2,})',
            r'(?:TOTAL|Total)[:\s]*[¥￥\\]?([0-9,，]{2,})',
        ]
        for pat in high_patterns:
            m = re.search(pat, normalized)
            if m:
                amount = self._parse_amount_str(m.group(1))
                if amount and amount > 0:
                    return amount, 0.85

        # 中信頼度: ¥マーク付き（最大値を取引金額とみなす）
        amounts = [
            self._parse_amount_str(m.group(1))
            for m in re.finditer(r'[¥￥\\]([0-9,，]+)', normalized)
        ]
        amounts = [a for a in amounts if a and a > 0]
        if amounts:
            return max(amounts), 0.6

        return None, 0.0

    def _parse_amount_str(self, s: str) -> Optional[int]:
        cleaned = re.sub(r'[,，\s]', '', s)
        try:
            return int(cleaned)
        except ValueError:
            return None

    # -------------------------------------------------------------------------
    # 取引先名（発行元）抽出
    # -------------------------------------------------------------------------

    def _extract_client_name(self, text: str) -> tuple[Optional[str], float]:
        """発行元企業名を抽出して (企業名, 信頼度) を返す"""
        # 1. 発行者ラベル付き（最高優先度）
        m = re.search(
            r'(?:発行者|発行元|販売者|請求者|差出人)[:\s：　]*(.{2,30}?)(?:\n|$)',
            text
        )
        if m:
            name = m.group(1).strip()
            if name:
                return name, 0.9

        # 2. 企業名パターン：御中・様の直前は宛先なので除外
        recipient_names: set[str] = set()
        for m in re.finditer(r'(.{2,30}?)(?:御中|様)(?:\s|$)', text):
            if re.search(self._CORP_SUFFIX, m.group(1)):
                recipient_names.add(m.group(1).strip())

        # 接頭パターン（株式会社XXX）と接尾パターン（XXX株式会社）
        issuer_names: list[str] = []
        for m in re.finditer(fr'({self._CORP_SUFFIX}.{{1,20}})', text):
            name = m.group(1).strip()
            if name not in recipient_names:
                issuer_names.append(name)
        for m in re.finditer(fr'(.{{1,20}}{self._CORP_SUFFIX})', text):
            name = m.group(1).strip()
            if name not in recipient_names and name not in issuer_names:
                issuer_names.append(name)

        if issuer_names:
            return issuer_names[0], 0.7

        # 3. 発行者候補が見つからない場合は宛先名を低信頼度で返す
        if recipient_names:
            return next(iter(recipient_names)), 0.4

        return None, 0.0

    # -------------------------------------------------------------------------
    # 書類種別抽出
    # -------------------------------------------------------------------------

    def _extract_doc_type(self, text: str) -> tuple[Optional[str], float]:
        """書類種別キーワードを抽出して (キーワード, 信頼度) を返す"""
        for pattern, keyword in self.DOC_TYPE_KEYWORDS:
            if re.search(pattern, text):
                return keyword, 0.9
        return None, 0.0
