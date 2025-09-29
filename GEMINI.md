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

**Note:** The `filelock` library has been added to support the multi-user feature.

### OCR Engine

This application uses Tesseract OCR. You need to install it and ensure it's in your system's PATH or configure the path in the application's settings.

### Running the Application

To run the application, execute the following command:

```bash
python main.py
```

## Multi-User Setup (Shared Configuration)

The application can be configured for multi-user access, allowing several users to share the same data and settings (such as the client list and save directory). This is achieved by placing the `config.ini` file in a shared network location.

### How It Works

- **`config.ini`**: This is the main configuration file containing all settings. For sharing, this file is moved to a network drive or a shared folder.
- **`shared_config.path`**: A new, small text file that is created in the application's root directory. It contains only the path to the shared `config.ini` file. The application checks for this file on startup to determine whether to use a local or shared configuration.
- **`config.ini.lock`**: A lock file automatically generated next to the `config.ini` file when a user is modifying the settings. This prevents data corruption from simultaneous edits by multiple users. You do not need to manually create or delete this file.

### Setup Instructions

1.  **Administrator/First User:**
    1.  Copy the local `config.ini` file from the application directory to a shared network location that all users can access (e.g., `\\server\shared_folder\config.ini`).
    2.  Launch the application and go to the "Settings" menu.
    3.  In the "Shared Configuration" section, click the "Browse" button and select the `config.ini` file you just placed in the shared location.
    4.  Click "Save and Close". The application will prompt for a restart.
    5.  After saving, a `shared_config.path` file will be created in the application's directory.

2.  **Other Users:**
    1.  Get a copy of the application files.
    2.  Get a copy of the `shared_config.path` file from the first user and place it in their application directory.
    3.  Now, when they launch the application, it will automatically use the shared configuration.

### Switching Back to Local Mode

To stop using the shared configuration, simply go to "Settings", click "Clear Shared Configuration", and save. This will delete the `shared_config.path` file, and the application will revert to using its local `config.ini` file upon the next restart.

## Development Conventions

- **GUI Framework:** The application is built with PyQt6.
- **Modularity:** The code is organized into `models`, `views`, and `utils` directories, separating data logic, UI components, and helper functions.
- **Configuration:** Application settings are managed through a `config.ini` file, which is accessed via the `ConfigManager` class in `utils/config_manager.py`.
- **Data Management:** Metadata for the documents is stored in a CSV file (`index.csv`) within each year's directory. The `MetadataManager` class in `models/metadata_manager.py` handles all interactions with this data.
- **PDF and OCR:** PDF processing is handled by the `PdfProcessor` class (`models/pdf_processor.py`) using PyMuPDF. OCR functionality is encapsulated in the `OcrProcessor` class (`models/ocr_processor.py`) using pytesseract.