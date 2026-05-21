import logging
import os

logger = logging.getLogger(__name__)

class OcrProcessor:
    @staticmethod
    def warm_up(config_manager):
        """Tesseract OCR を事前ロードする（バックグラウンドスレッドから呼ばれる）。"""
        import pytesseract
        try:
            tesseract_path = config_manager.get_tesseract_path()
            if tesseract_path and os.path.exists(tesseract_path):
                pytesseract.pytesseract.tesseract_cmd = tesseract_path
            pytesseract.get_tesseract_version()
        except pytesseract.TesseractNotFoundError:
            pass
        except Exception as e:
            logger.warning(f"OCRウォームアップ中にエラーが発生しました: {e}")

    def __init__(self, image, config_manager):
        self.image = image
        self.config_manager = config_manager

    def get_text_and_boxes(self, min_confidence=0):
        """OCR を実行して認識結果をリストで返す。"""
        import pytesseract
        tesseract_path = self.config_manager.get_tesseract_path()
        if tesseract_path and os.path.exists(tesseract_path):
            pytesseract.pytesseract.tesseract_cmd = tesseract_path

        try:
            config = r'--psm 6 --oem 3'
            data = pytesseract.image_to_data(
                self.image,
                output_type=pytesseract.Output.DICT,
                lang='jpn',
                config=config
            )
            results = []
            for i in range(len(data['text'])):
                conf = int(data['conf'][i])
                text = data['text'][i].strip()
                if conf >= min_confidence and text:
                    results.append({
                        'text': text,
                        'left': data['left'][i],
                        'top': data['top'][i],
                        'width': data['width'][i],
                        'height': data['height'][i],
                        'conf': conf
                    })
            return results
        except pytesseract.TesseractNotFoundError:
            raise RuntimeError(
                "Tesseractが見つかりません。メニューの「ツール」→「設定」からtesseract.exeのパスを指定してください。"
            )
        except Exception as e:
            raise RuntimeError(f"OCR処理中にエラーが発生しました: {e}")
