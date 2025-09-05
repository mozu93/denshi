import pytesseract
import os

class OcrProcessor:
    def __init__(self, image, config_manager):
        self.image = image
        self.config_manager = config_manager

    def get_text_and_boxes(self, min_confidence=0):
        """
        Performs OCR on the image and returns a list of recognized words 
        with their bounding boxes and confidence levels.
        """
        tesseract_path = self.config_manager.get_tesseract_path()
        if tesseract_path and os.path.exists(tesseract_path):
            pytesseract.pytesseract.tesseract_cmd = tesseract_path
        # If not set or path is invalid, it will fall back to searching the system's PATH

        try:
            config = r'--psm 6 --oem 3' 
            data = pytesseract.image_to_data(self.image, output_type=pytesseract.Output.DICT, lang='jpn', config=config)
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
            # Re-raise a new RuntimeError with a user-friendly message
            raise RuntimeError(
                "Tesseractが見つかりません。メニューの「ツール」→「設定」からtesseract.exeのパスを指定してください。"
            )
        except Exception as e:
            # Catch other potential errors from pytesseract
            raise RuntimeError(f"OCR処理中にエラーが発生しました: {e}")
