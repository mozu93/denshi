import jaconv
import re
from datetime import datetime
import os

import jaconv
import re
from datetime import datetime
import os

LOG_FILE = r"C:\Users\taka\Documents\Gemini\denshi\log\catlog.txt"

def log_debug(message):
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"{datetime.now().isoformat()} - {message}\n")

class DateConverter:
    def to_seireki(self, wareki_text):
        log_debug(f"Input to to_seireki: {wareki_text}")
        original_text = wareki_text
        wareki_text = wareki_text.replace(' ', '') # Remove spaces
        wareki_text = jaconv.z2h(wareki_text, kana=False, ascii=True, digit=True)
        log_debug(f"After cleaning and z2h: {wareki_text}")

        era_map = {
            '明治': 1868,
            '大正': 1912,
            '昭和': 1926,
            '平成': 1989,
            '令和': 2019,
        }

        # Try Japanese era conversion first
        for era, start_year in era_map.items():
            if era in wareki_text:
                try:
                    wareki_text_parts = wareki_text.replace(era, '')
                    parts = re.split('[年月日]', wareki_text_parts)
                    year = int(parts[0])
                    month = int(parts[1])
                    day = int(parts[2])

                    seireki_year = start_year + year - 1
                    log_debug(f"Converted from wareki: {seireki_year:04d}{month:02d}{day:02d}")
                    return f'{seireki_year:04d}{month:02d}{day:02d}'
                except (ValueError, IndexError):
                    log_debug(f"Wareki conversion failed for {wareki_text} with era {era}")
                    continue
        
        # If no era found, try Western calendar with Japanese characters
        numbers = re.findall(r'\d+', wareki_text)
        if len(numbers) >= 3:
            try:
                year = int(numbers[0])
                month = int(numbers[1])
                day = int(numbers[2])
                log_debug(f"Converted from Western calendar: {year:04d}{month:02d}{day:02d}")
                return f'{year:04d}{month:02d}{day:02d}'
            except (ValueError, IndexError):
                log_debug(f"Western calendar conversion failed for {wareki_text}")
                pass

        log_debug(f"No conversion applied, returning original: {original_text}")
        return original_text # Return original text if conversion fails


def log_debug(message):
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"{datetime.now().isoformat()} - {message}\n")

class DateConverter:
    def to_seireki(self, wareki_text):
        original_text = wareki_text
        wareki_text = wareki_text.replace(' ', '') # Remove spaces
        wareki_text = jaconv.z2h(wareki_text, kana=False, ascii=True, digit=True)

        era_map = {
            '明治': 1868,
            '大正': 1912,
            '昭和': 1926,
            '平成': 1989,
            '令和': 2019,
        }

        # Try Japanese era conversion first
        for era, start_year in era_map.items():
            if era in wareki_text:
                try:
                    wareki_text_parts = wareki_text.replace(era, '')
                    parts = re.split('[年月日]', wareki_text_parts)
                    year = int(parts[0])
                    month = int(parts[1])
                    day = int(parts[2])

                    seireki_year = start_year + year - 1
                    return f'{seireki_year:04d}{month:02d}{day:02d}'
                except (ValueError, IndexError):
                    continue
        
        # If no era found, try Western calendar with Japanese characters
        numbers = re.findall(r'\d+', wareki_text)
        if len(numbers) >= 3:
            try:
                year = int(numbers[0])
                month = int(numbers[1])
                day = int(numbers[2])
                return f'{year:04d}{month:02d}{day:02d}'
            except (ValueError, IndexError):
                pass

        return original_text # Return original text if conversion fails
