# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

電子帳簿保存システム (Electronic Bookkeeping System) - A PyQt6-based desktop application for managing electronic transaction documents in compliance with Japan's Electronic Book Preservation Act. The application processes PDF files with OCR, extracts metadata (date, amount, client name), and organizes them into structured directories with searchable indexes.

## Commands

### Development
```bash
# Run the application (command line)
python main.py

# Run the application (double-click)
# Double-click main.py or use 起動.bat for reliable startup

# Install dependencies
pip install -r requirements.txt

# Build executable and installer
python build.py

# Build executable only (skip installer)
python build.py --skip-installer
```

### Building for Release
```bash
# 1. Update version in VERSION.py
# 2. Install build dependencies
pip install -r requirements_build.txt

# 3. Run build script
python build.py

# 4. Output files:
# - dist/DenshiChobohozoSystem/DenshiChobohozoSystem.exe
# - installer/Output/DenshiChobohozoSystem_v2.0.0_setup.exe
```

### Prerequisites
- Tesseract OCR must be installed for text recognition functionality
- Japanese language data (jpn.traineddata) required for OCR
- Default Tesseract path: `C:/Program Files/Tesseract-OCR/tesseract.exe`

## Architecture

### Directory Structure
```
denshi/
├── main.py                 # Application entry point (with path fix)
├── main_window.py         # Main window with tab management
├── VERSION.py             # Version information (Single Source of Truth)
├── config.ini            # Configuration file (auto-generated)
├── 起動.bat               # Batch file for reliable startup
├── build.py              # Build automation script
├── denshi.spec           # PyInstaller configuration
├── BUILD_GUIDE.md        # Build instructions
├── installer/            # Installer resources
│   ├── denshi.iss            # Inno Setup script
│   ├── icon.ico              # Application icon (not in repo)
│   └── README.md             # Resource requirements
├── models/               # Data processing layer
│   ├── metadata_manager.py    # CSV-based document metadata
│   ├── ocr_processor.py       # Tesseract OCR integration
│   └── pdf_processor.py       # PyMuPDF document handling
├── views/                # UI components (PyQt6)
│   ├── file_registration_tab.py  # PDF registration interface
│   ├── file_search_tab.py        # Document search interface
│   ├── settings_dialog.py        # Application settings
│   ├── edit_dialog.py            # Metadata editing
│   └── update_dialog.py          # Update notification dialog
└── utils/                # Helper utilities
    ├── ui_styles.py           # Unified UI styling system
    ├── config_manager.py      # INI file management
    ├── date_converter.py      # Japanese date conversion
    ├── validator.py           # Input validation
    ├── file_hasher.py         # Document integrity
    ├── constants.py           # Application constants and path helpers
    └── update_checker.py      # GitHub API update checker
```

### Core Components

**MainWindow** (`main_window.py`):
- Tab-based interface with registration and search modes
- Manages global state and configuration
- Handles drag & drop PDF files

**MetadataManager** (`models/metadata_manager.py`):
- CSV-based document indexing per year (`{year}年/index.csv`)
- Document metadata: ID, category, type, date, client, amount, memo, file path, hash
- Supports search, update, delete operations

**OcrProcessor** (`models/ocr_processor.py`):
- Tesseract integration for Japanese text recognition
- Supports user-selected regions in PDF preview
- Automatic extraction of amounts, dates, client names

**ConfigManager** (`utils/config_manager.py`):
- INI-based configuration management
- Handles paths, UI settings, document categories
- Auto-saves window dimensions and user preferences

**UIStyles** (`utils/ui_styles.py`):
- Unified styling system for consistent UI appearance
- Meiryo font family with gray color scheme
- Comprehensive styling for all UI components
- Supports both button styles (normal and small variants)

### File Organization Pattern
Documents are organized as:
```
電子帳簿保存/
└── {年}年/
    ├── index.csv           # Metadata index
    ├── 支出情報/           # Expenditure documents
    │   ├── 01.注文書・契約書/
    │   ├── 02.見積書(確定版)/
    │   ├── 03.請求書/
    │   └── 04.領収証/
    └── 収入情報/           # Income documents
        ├── 01.注文書・契約書/
        ├── 02.見積書(確定版)/
        ├── 03.請求書/
        └── 04.領収証/
```

### File Naming Convention
Format: `{通し番号}_{発行日YYYYMMDD}_{金額}_{取引先名}.pdf`
Example: `001_20240901_10800_株式会社サンプル.pdf`

## Key Features

- **PDF Preview**: Zoom, page navigation, OCR region selection
- **Automatic File Naming**: Based on extracted/input metadata
- **Year-based Organization**: Automatic folder creation and management
- **Advanced Search**: Filter by year, document type, client, date, amount, memo with robust error handling
- **Dynamic Date Ranges**: Automatic date range setting based on selected year
- **Optimized UI Layout**: 50% width search conditions, maximized result display area
- **Document Categories**: Configurable expenditure/income categories
- **Japanese Date Conversion**: Wareki (和暦) to Western calendar
- **Metadata Preservation**: CSV index with document integrity checks
- **Unified Styling**: Consistent Meiryo font and gray color scheme throughout
- **Multi-launch Support**: Both double-click and command-line execution
- **Automatic Updates**: GitHub Releases integration with startup update checks
- **Windows Installer**: Inno Setup-based installer with Tesseract OCR bundling

## Configuration

The application uses `config.ini` for settings:
- **Paths**: Root save directory, Tesseract OCR path
- **UI**: Font size, window dimensions, splitter positions
- **Categories**: Expenditure/Income document types
- **Last Inputs**: Remembers user's last selected year and document type

## Development Notes

- Uses PyQt6 for modern GUI framework
- Japanese language support throughout the interface
- Comprehensive error handling and logging with robust null-value protection
- Supports bundling into standalone executable with PyInstaller
- Working directory auto-correction for reliable double-click execution
- OCR engine is pre-loaded at startup for better performance
- Uses pandas for efficient CSV operations with NaN-safe comparisons
- Document integrity maintained with file hashing
- Unified UI styling system with Meiryo font and consistent color scheme
- Optimized search interface layout for improved user experience