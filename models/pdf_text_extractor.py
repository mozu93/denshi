"""テキストPDF（デジタル発行）から pdfplumber + 正規表現で帳票情報を抽出するモジュール"""
from __future__ import annotations

import logging
import re
import unicodedata
from dataclasses import dataclass, field
from typing import Optional

import jaconv

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
    reg_number: Optional[str] = None       # 適格請求書発行事業者登録番号（T+13桁）


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
        r'|一般社団法人|公益社団法人|一般財団法人|公益財団法人'
        r'|社会福祉法人|医療法人|学校法人|特定非営利活動法人'
        r'|協同組合|農業協同組合|信用組合|信用金庫)'
    )

    # 取引先名として無効なパターン（役職・担当者・銀行口座記号を含む場合は除外）
    _INVALID_CLIENT_RE = re.compile(
        r'代表取締役|担当|[/／]|[（(][普当]{1}[）)]|\d{6,}'
        r'|\s+(?:株式会社|有限会社|合同会社|合資会社|合名会社'
        r'|一般社団法人|公益社団法人|一般財団法人|公益財団法人'
        r'|社会福祉法人|医療法人|学校法人|特定非営利活動法人'
        r'|協同組合|農業協同組合|信用組合|信用金庫)$'
    )

    # 登録番号プレフィックス（適格請求書発行事業者番号 T + 13桁）
    _REG_NUM_PREFIX = re.compile(r'^[TＴ][0-9０-９]{10,13}\s+')

    # 法人格の後ろの余分なスペースを除去するパターン
    _CORP_SPACE_RE = re.compile(
        r'(株式会社|有限会社|合同会社|合資会社|合名会社'
        r'|一般社団法人|公益社団法人|一般財団法人|公益財団法人'
        r'|社会福祉法人|医療法人|学校法人|特定非営利活動法人'
        r'|協同組合|農業協同組合|信用組合|信用金庫)\s+'
    )

    # 銀行口座の支店情報が続く場合に金融機関名と判断するパターン
    _BANK_BRANCH_RE = re.compile(r'\s*(?:本店|支店|営業部|出張所|ATM)')

    def extract(self, pdf_path: str) -> ExtractionResult:
        """PDFを解析して帳票情報を返す。テキスト抽出できない場合は is_text_pdf=False を返す。"""
        import pdfplumber  # 初回PDF処理時にのみインポート（起動時間短縮）
        result = ExtractionResult()
        try:
            with pdfplumber.open(pdf_path) as pdf:
                pages_text = [page.extract_text() or "" for page in pdf.pages[:3]]
            text = "\n".join(pages_text)
        except Exception as e:
            logger.warning(f"pdfplumber テキスト抽出エラー ({pdf_path}): {e}")
            return result

        # (cid:X) だらけのフォント未埋め込みPDFを検出してスキャン扱いにする
        cid_count = text.count('(cid:')
        if cid_count > 5 and len(text) > 0 and cid_count * 6 > len(text) * 0.25:
            return result

        # NFKC正規化: CJK互換文字（⽇→日, ⽉→月）や丸数字（①→1）を標準形に統一
        clean = unicodedata.normalize('NFKC', text.strip())
        if len(clean) < self.MIN_TEXT_LENGTH:
            return result  # スキャンPDFまたはテキストなし

        # スペース区切り年号 "2 0 2 5 年" → "2025年" を前処理で修正
        clean = re.sub(r'(\d)\s(\d)\s(\d)\s(\d)\s*年', r'\1\2\3\4年', clean)
        clean = re.sub(r'(\d)\s(\d)\s*月', r'\1\2月', clean)
        clean = re.sub(r'(\d)\s(\d)\s*日', r'\1\2日', clean)
        # ドット区切り年号 "2..0..2.6..年" → "2026年" を前処理で修正（Google等）
        clean = re.sub(r'(\d)\.+(\d)\.+(\d)\.+(\d)\.+年', r'\1\2\3\4年', clean)
        clean = re.sub(r'(\d)\.+(\d)\.+月', r'\1\2月', clean)
        clean = re.sub(r'(\d)\.+(\d)\.+日', r'\1\2日', clean)
        clean = re.sub(r'(\d)\.+月', r'\1月', clean)
        clean = re.sub(r'(\d)\.+日', r'\1日', clean)

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
        result.reg_number = self._extract_reg_number(normalized)
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
        _DATE_LABELS = r'(?:発行年月日|発行日|請求日|作成日|日付|DATE\s*OF\s*ISSUE)'

        # 1. ラベル付き和暦（最高信頼度）
        m = re.search(
            _DATE_LABELS + r'[:\s：　]*'
            r'([令平昭大明][和正治]?\d+年\s*\d{1,2}\s*月\s*\d{1,2}\s*日)',
            original
        )
        if m:
            converted = self._parse_wareki(re.sub(r'\s', '', m.group(1)))
            if converted:
                return converted, 0.9

        # 2. ラベル付き西暦（スペース混じりも対応）
        m = re.search(
            _DATE_LABELS + r'[:\s：　]*'
            r'(20\d{2})\s*[/\-\.年]\s*(\d{1,2})\s*[/\-\.月]\s*(\d{1,2})\s*日?',
            normalized
        )
        if m:
            year, month, day = int(m.group(1)), int(m.group(2)), int(m.group(3))
            if 1 <= month <= 12 and 1 <= day <= 31:
                return f'{year:04d}{month:02d}{day:02d}', 0.85

        # 3. ラベルなし和暦
        for era, base in self._ERA_MAP.items():
            m = re.search(fr'{era}(\d+)年\s*(\d{{1,2}})\s*月\s*(\d{{1,2}})\s*日', original)
            if m:
                year = base + int(m.group(1)) - 1
                month, day = int(m.group(2)), int(m.group(3))
                if 1 <= month <= 12 and 1 <= day <= 31:
                    return f'{year:04d}{month:02d}{day:02d}', 0.75

        # 4. ラベルなし西暦（YYYY/MM/DD 等、スペース混じりも対応）
        # 期間表示の開始日（"X年X月X日 - Y年Y月Y日"）はスキップして正確な発行日を取得
        for m in re.finditer(r'(20\d{2})\s*[/\-\.年]\s*(\d{1,2})\s*[/\-\.月]\s*(\d{1,2})\s*日?', normalized):
            year, month, day = int(m.group(1)), int(m.group(2)), int(m.group(3))
            if not (1 <= month <= 12 and 1 <= day <= 31):
                continue
            ctx_after = normalized[m.end():m.end() + 20]
            if re.match(r'\s*[-〜]\s*\d{4}', ctx_after):
                continue  # 期間範囲の開始日はスキップ
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

        # ── 最高優先度: 「今回ご/御請求額」（JTB・ベイス等の差引精算型請求書） ──
        # 同行に ¥ 付き（JTB形式）
        m = re.search(r'今回[ご御]?請求(?:金額|合計|額)?[^\n]*?[¥\\]\s*([0-9,，]{2,})', normalized)
        if m:
            amount = self._parse_amount_str(m.group(1))
            if amount and amount > 0:
                return amount, 0.88
        # 次行に金額（ベイス/東洋電機形式: ラベル行に数値なし、次行に複数数値があれば最大値を採用）
        m = re.search(r'今回[ご御]?請求(?:金額|合計|額)?[^\n]*\n([^\n]+)', normalized)
        if m:
            line = m.group(1)
            nums = [self._parse_amount_str(n) for n in re.findall(r'([0-9,，]{3,})', line)]
            nums = [n for n in nums if n and n > 0]
            if nums:
                return max(nums), 0.88

        # ── 高信頼度（次行パターン）: 「ご請求金額」ラベルが同行内にあり次行末に「N円」（帝国データバンク等） ──
        m = re.search(r'ご?請求金額[^\n]*\n[^\n]*?([0-9,，]{3,})円', normalized)
        if m:
            amount = self._parse_amount_str(m.group(1))
            if amount and amount > 0:
                return amount, 0.82

        # ── 送金額（通知書等で支払うべき手数料が「送金額」として明示される場合） ──
        m = re.search(r'送金額[^\n]*?([0-9,，]{3,})\s*円', normalized)
        if m:
            amount = self._parse_amount_str(m.group(1))
            if amount and amount > 0:
                return amount, 0.88

        # ── 高信頼度: ラベル付き（改行をまたがないよう [^0-9\n]* で区切り） ──
        # NOTE: [:\s：　¥￥\\]* は改行(\n)を許すため 10% の誤抽出が発生する。
        #       [^0-9\n]* に変更して同一行内でのみマッチするよう修正。
        # NOTE: お支払[合計金額]* は文字クラスで 0回以上のため「お支払い期日」にも誤マッチする。
        #       必須グループ化に変更してお支払合計/金額/額のみマッチするよう修正。
        high_patterns = [
            # ご請求金額等: 括弧内年号・登録番号が直後に来る場合は誤検出なので除外
            r'(?:ご?請求金額|合計金額|お支払(?:合計|金額|額))(?!\s*[（(]\d{4})(?!\s*登録番号)[^0-9\n]*([0-9,，]{2,})',
            r'税込[合計]?[^0-9\n]*([0-9,，]{2,})',                    # 税込〇〇
            r'(?:総額|TOTAL|Total)[^\n]*?(?:JPY|[¥￥\\])\s*([0-9,，]{2,})',   # Zoom等・外貨（合計より優先）
            r'合\s*計(?!料金)(?!\s*JPY)[^0-9\n]*([0-9,，]{2,})',     # 合 計（料金/JPY接続を除外）
            r'[（(](?:合計|ご?請求金額|税込合計)[）)][^0-9\n]*([0-9,，]{2,})',  # (合計)
            r'JPY\s*([0-9,，]{2,})',                                   # JPY prefix
        ]
        for pat in high_patterns:
            m = re.search(pat, normalized)
            if m:
                amount = self._parse_amount_str(m.group(1))
                if amount and amount > 0:
                    return amount, 0.85

        # ── 高信頼度（表形式）: ラベル行の次行に数値が並ぶ場合、最後の値を取得 ──
        # 例1: 「税抜計 消費税 ご請求金額」→ 次行「13,597 1,359 14,956」
        m = re.search(r'ご?請求金額\s*\n\s*(?:[0-9,，]+\s+)+([0-9,，]+)', normalized)
        if m:
            amount = self._parse_amount_str(m.group(1))
            if amount and amount > 0:
                return amount, 0.80
        # 例2: 「税抜計 消費税(10%) 合計金額」→ 次行「18,000 1,800 19,800」
        m = re.search(r'合計金額\s*\n\s*(?:[0-9,，]+\s+)*([0-9,，]{3,})', normalized)
        if m:
            amount = self._parse_amount_str(m.group(1))
            if amount and amount > 0:
                return amount, 0.80

        # ── 中信頼度: [アカウント]ご利用分 AMOUNT 形式（UQ等、¥/円なし） ──
        m = re.search(r'\Sご利用分[ \t]+([0-9,，]{3,})', normalized, re.MULTILINE)
        if m:
            amount = self._parse_amount_str(m.group(1))
            if amount and amount > 0:
                return amount, 0.70

        # ── 中信頼度: ¥マーク付き（最大値を取引金額とみなす） ──
        amounts = [
            self._parse_amount_str(m.group(1))
            for m in re.finditer(r'[¥￥\\]([0-9,，]+)', normalized)
        ]
        amounts = [a for a in amounts if a and a > 0]
        if amounts:
            return max(amounts), 0.6

        # ── 低信頼度: 円マーク付き（最大値） ──
        # 課税対象額の直後に来る円表記は税抜き金額なので除外
        amounts_yen = []
        for m_y in re.finditer(r'([0-9,，]{3,})円', normalized):
            ctx_before = normalized[max(0, m_y.start() - 15):m_y.start()]
            if re.search(r'課税対象額', ctx_before):
                continue
            a = self._parse_amount_str(m_y.group(1))
            if a and a >= 100:
                amounts_yen.append(a)
        if amounts_yen:
            return max(amounts_yen), 0.5

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

    def _clean_client_name(self, name: str) -> Optional[str]:
        """企業名を正規化・検証して無効な場合は None を返す"""
        # 末尾の「御中」「様」を除去
        name = re.sub(r'[\s　]*(?:御中|様)\s*$', '', name).strip()
        # 先頭の記号（■◆★●▲▼【】□◇☆○）を除去
        name = re.sub(r'^[■◆★●▲▼【】□◇☆○]+\s*', '', name).strip()
        # 先頭の日付パターンを除去: 「2026年04月30日 XX」→「XX」
        name = re.sub(r'^\d{4}[年/-]\d{1,2}[月/-]\d{1,2}日?\s+', '', name).strip()
        # 先頭の括弧プレフィックスを除去: 「(適格請求書) XX」→「XX」
        name = re.sub(r'^[（(][^）)]{1,15}[）)]\s*', '', name).strip()
        # 「名義:」「口座名義:」「振込先名:」等の固定プレフィックスを除去
        name = re.sub(r'^(?:口座名義|振込先名|名義|口座名|名称|担当者?)[:：]\s*', '', name).strip()
        # 先頭の「XX:」プレフィックスを除去（「名:NTTファイナンス」→「NTTファイナンス」）
        # ただし法人格を含む場合は除去しない
        if not re.search(self._CORP_SUFFIX, name.split(':')[0] if ':' in name else ''):
            name = re.sub(r'^[^\w（(法一公社有合農信特]{0,8}[:：]\s*', '', name).strip()
        # 登録番号プレフィックスを除去（T + 13桁）
        name = self._REG_NUM_PREFIX.sub('', name).strip()
        # 「登録番号:」で始まる場合は無効
        if re.match(r'登録番号', name):
            return None
        # 無効パターン（役職・担当者・末尾スペース法人格）を含む場合は除外
        if self._INVALID_CLIENT_RE.search(name):
            return None
        # 法人格の直後にある余分なスペースを除去（「株式会社 ベイス」→「株式会社ベイス」）
        name = self._CORP_SPACE_RE.sub(r'\1', name).strip()
        # 全角ASCII→半角（NTTスマートコネクト等の ＮＴＴ→NTT）
        name = jaconv.z2h(name, kana=False, ascii=True, digit=False)
        # 短すぎる名前は除外
        if len(name) < 2:
            return None
        # 法人格のみで固有名詞がない名前は除外（「株式会社」単独等）
        if re.fullmatch(self._CORP_SUFFIX, name):
            return None
        return name

    def _strip_reg_num(self, s: str) -> str:
        """先頭の適格請求書発行事業者番号（T + 13桁）を除去する"""
        return self._REG_NUM_PREFIX.sub('', s).strip()

    def _is_bank_account_name(self, name: str, text: str) -> bool:
        """name の直後（同一行内）に支店・口座種別キーワードがある場合は振込先と判断して True を返す"""
        try:
            for line in text.split('\n'):
                if name in line:
                    idx = line.find(name)
                    after = line[idx + len(name):]
                    if re.search(r'(?:本店|支店|営業部|出張所|ATM|普通|当座)', after):
                        return True
            return False
        except Exception:
            return False

    def _extract_client_name(self, text: str) -> tuple[Optional[str], float]:
        """発行元企業名を抽出して (企業名, 信頼度) を返す"""
        # 1. 発行者ラベル付き（最高優先度）
        # 「適格請求書発行事業者」は「登録番号」が続く場合と区別する
        m = re.search(
            r'(?:発行者|発行元|販売者|請求者|差出人|代理交付者'
            r'|適格請求書発行事業者名?(?!登録))[:\s：　]*\n?(.{2,50}?)(?:\n|$)',
            text
        )
        if m:
            name = self._clean_client_name(m.group(1).strip())
            if name and len(name) >= 2:
                return name, 0.9

        # 2. 企業名パターン：御中・様の直前は宛先なので除外
        recipient_names: set[str] = set()
        for m in re.finditer(r'(.{2,30}?)(?:御中|様)(?:\s|$)', text):
            candidate = m.group(1).strip()
            if re.search(self._CORP_SUFFIX, candidate):
                # 正規化して追加（比較に使うため）
                normalized_r = self._CORP_SPACE_RE.sub(r'\1', candidate).strip()
                recipient_names.add(normalized_r)

        issuer_names: list[str] = []

        # 接尾パターン（XXX株式会社）を先に検索（固有の名前を取りやすい）
        for m in re.finditer(fr'(.{{1,20}}{self._CORP_SUFFIX})', text):
            name = self._clean_client_name(m.group(1).strip())
            if (name
                    and name not in recipient_names
                    and name not in issuer_names
                    and not self._is_bank_account_name(name, text)):
                issuer_names.append(name)

        # 接頭パターン（株式会社XXX）
        for m in re.finditer(fr'({self._CORP_SUFFIX}.{{1,20}})', text):
            name = self._clean_client_name(m.group(1).strip())
            if (name
                    and name not in recipient_names
                    and name not in issuer_names
                    and not self._is_bank_account_name(name, text)):
                issuer_names.append(name)

        if issuer_names:
            return issuer_names[0], 0.7

        # 3. 発行者候補が見つからない場合は宛先名を返す
        # 法人格あり → 信頼度 0.6（閾値以上）、なし → 0.4
        if recipient_names:
            name = next(iter(recipient_names))
            return name, 0.6

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

    # -------------------------------------------------------------------------
    # 登録番号抽出
    # -------------------------------------------------------------------------

    def _extract_reg_number(self, text: str) -> Optional[str]:
        """発行者の適格請求書登録番号（T+13桁）を抽出して正規化する。
        「貴社の登録番号」等、受取側のT番号が記載されている行はスキップする。"""
        for line in text.split('\n'):
            if '登録番号' not in line:
                continue
            if re.search(r'貴社|貴団体|お客様', line):
                continue  # 受取側のT番号はスキップ
            m = re.search(r'([TＴ][0-9０-９\-]{13,17})', line)
            if not m:
                continue
            raw = jaconv.z2h(m.group(1), ascii=True, digit=True)
            digits = re.sub(r'[^0-9]', '', raw[1:])
            if len(digits) == 13:
                return f'T{digits}'
        return None
