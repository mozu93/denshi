@echo off
chcp 65001 >nul
echo ========================================
echo インストール確認スクリプト
echo ========================================
echo.

echo [1] アプリケーションの確認
if exist "C:\Program Files\DenshiChobohozoSystem\DenshiChobohozoSystem.exe" (
    echo [OK] アプリケーションがインストールされています
) else (
    echo [NG] アプリケーションが見つかりません
)
echo.

echo [2] Tesseract OCRの確認
if exist "C:\Program Files\Tesseract-OCR\tesseract.exe" (
    echo [OK] Tesseract OCRがインストールされています
    "C:\Program Files\Tesseract-OCR\tesseract.exe" --version
) else (
    echo [NG] Tesseract OCRが見つかりません
)
echo.

echo [3] 設定ファイルの確認
if exist "%APPDATA%\DenshiChobohozoSystem\config.ini" (
    echo [OK] 設定ファイルが作成されています
) else (
    echo [INFO] 設定ファイルはまだ作成されていません（初回起動後に作成されます）
)
echo.

echo [4] デスクトップアイコンの確認
if exist "%USERPROFILE%\Desktop\電子帳簿保存システム.lnk" (
    echo [OK] デスクトップアイコンが作成されています
) else (
    echo [INFO] デスクトップアイコンは作成されていません
)
echo.

echo ========================================
echo 確認完了
echo ========================================
pause
