import fitz  # PyMuPDF

class PdfProcessor:
    def __init__(self, pdf_path):
        self.pdf_path = pdf_path
        self.doc = None

    def open(self):
        try:
            self.doc = fitz.open(self.pdf_path)
            return True
        except Exception as e:
            print(f"Error opening PDF: {e}")
            return False

    def get_page_as_pixmap(self, page_num, scale_factor=1):
        if not self.doc or page_num >= self.doc.page_count:
            return None
        page = self.doc.load_page(page_num)
        # Apply scale factor to the matrix for higher resolution image
        mat = fitz.Matrix(scale_factor, scale_factor)
        pix = page.get_pixmap(matrix=mat)
        return pix

    def close(self):
        if self.doc:
            self.doc.close()