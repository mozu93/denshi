try:
    from PIL import Image
except ImportError:
    import Image
import pytesseract

class OcrProcessor:
    def __init__(self, image):
        self.image = image

    def get_text_and_boxes(self, min_confidence=0): # Changed default min_confidence to 0
        """
        Performs OCR on the image and returns a list of recognized words 
        with their bounding boxes and confidence levels.

        Args:
            min_confidence (int): The minimum confidence level (0-100) to include a word.

        Returns:
            list: A list of dictionaries, where each dictionary represents a word
                  and has keys: 'text', 'left', 'top', 'width', 'height', 'conf'.
                  Returns None if Tesseract is not found.
        """
        try:
            # Added config parameter for psm and oem
            config = r'--psm 3 --oem 3' 
            data = pytesseract.image_to_data(self.image, output_type=pytesseract.Output.DICT, lang='jpn', config=config)
            results = []
            for i in range(len(data['text'])):
                conf = int(data['conf'][i])
                text = data['text'][i].strip()
                
                if conf >= min_confidence and text: # Changed > to >= to include 0 confidence
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
            # Re-raise the exception to be caught by the UI layer
            raise pytesseract.TesseractNotFoundError(
                "Tesseract is not installed or not in your PATH. OCR機能を利用するにはインストールが必要です。"
            )
