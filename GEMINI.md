# GEMINI.md

## Project Overview

This is a Python-based desktop application developed using PyQt6. Its primary purpose is to manage electronic transaction documents (PDFs) in compliance with Japan's Electronic Book Preservation Act.

The application allows users to register PDF files with associated metadata such as date, amount, and client name. It then automatically renames the files based on this metadata and saves them into a structured directory format: `{year}/{transaction_type}/{doc_type}`.

A key feature is its OCR capability, which extracts information directly from the PDF documents to streamline the data entry process. The application also provides functionality to search and manage the registered documents.

## Building and Running

### Dependencies

The project's dependencies are listed in `requirements.txt`. To install them, run:

```bash
pip install -r requirements.txt
```

### OCR Engine

This application uses Tesseract OCR. You need to install it and ensure it's in your system's PATH or configure the path in the application's settings.

### Running the Application

To run the application, execute the following command:

```bash
python main.py
```

## Development Conventions

- **GUI Framework:** The application is built with PyQt6.
- **Modularity:** The code is organized into `models`, `views`, and `utils` directories, separating data logic, UI components, and helper functions.
- **Configuration:** Application settings are managed through a `config.ini` file, which is accessed via the `ConfigManager` class in `utils/config_manager.py`.
- **Data Management:** Metadata for the documents is stored in a CSV file (`index.csv`) within each year's directory. The `MetadataManager` class in `models/metadata_manager.py` handles all interactions with this data.
- **PDF and OCR:** PDF processing is handled by the `PdfProcessor` class (`models/pdf_processor.py`) using PyMuPDF. OCR functionality is encapsulated in the `OcrProcessor` class (`models/ocr_processor.py`) using pytesseract.
