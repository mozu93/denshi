import re
import jaconv

class Validator:
    def is_valid_date(self, date_str):
        # Checks if the date is in YYYYMMDD format
        return re.fullmatch(r'\d{8}', date_str) is not None

    def _normalize_amount_string(self, amount_str):
        # Convert full-width digits to half-width
        amount_str = jaconv.z2h(amount_str, kana=False, ascii=True, digit=True)
        # Remove all non-digit characters except for a leading hyphen
        cleaned_amount = ""
        for char in amount_str:
            if char.isdigit():
                cleaned_amount += char
            elif char == '-' and not cleaned_amount: # Only allow '-' at the very beginning
                cleaned_amount += char
        # 先頭ゼロを除去する（例: OCRが "6090" を "0690" と誤認識した場合など）
        # "0" 単体（金額ゼロ）は保持、"0xxx" 形式のみ strip する
        if cleaned_amount and cleaned_amount[0] == '0' and len(cleaned_amount) > 1:
            cleaned_amount = cleaned_amount.lstrip('0') or '0'
        return cleaned_amount

    def is_valid_amount(self, amount_str):
        normalized_amount = self._normalize_amount_string(amount_str)
        
        # Regex to match various numerical formats, including negative numbers and decimals
        # This regex is simplified from the search result to focus on extraction after normalization
        match = re.match(r'^(-?\d+(?:\.\d+)?)(兆|億|万)?', normalized_amount)
        
        if match:
            num_part = match.group(1)
            unit_part = match.group(2)
            
            try:
                value = float(num_part)
                if unit_part == '万':
                    value *= 10000
                elif unit_part == '億':
                    value *= 100000000
                elif unit_part == '兆':
                    value *= 1000000000000
                return True, int(value) # Return True and the integer value
            except ValueError:
                return False, None
        return False, None
