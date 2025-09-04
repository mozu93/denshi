import jaconv
import re

class DateConverter:
    def to_seireki(self, wareki_text):
        original_text = wareki_text
        wareki_text = wareki_text.replace(' ', '').replace('　', '')
        wareki_text = jaconv.z2h(wareki_text, kana=False, ascii=True, digit=True)

        era_map = {
            '明治': 1868, '大正': 1912, '昭和': 1926, '平成': 1989, '令和': 2019,
            'M': 1868, 'T': 1912, 'S': 1926, 'H': 1989, 'R': 2019,
        }

        for era_kanji, start_year in era_map.items():
            match = re.match(f"^{era_kanji}(\d+)[.\-年](\d+)[.\-月](\d+)日?", wareki_text, re.IGNORECASE)
            if match:
                try:
                    year = int(match.group(1))
                    month = int(match.group(2))
                    day = int(match.group(3))
                    seireki_year = start_year + year - 1
                    return f'{seireki_year:04d}{month:02d}{day:02d}'
                except (ValueError, IndexError):
                    continue
        
        numbers = re.findall(r'\d+', wareki_text)
        if len(numbers) >= 3:
            try:
                if len(numbers[0]) == 4:
                    year, month, day = int(numbers[0]), int(numbers[1]), int(numbers[2])
                    return f'{year:04d}{month:02d}{day:02d}'
            except (ValueError, IndexError):
                pass

        return original_text
