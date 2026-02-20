# -*- coding: utf-8 -*-
"""
アップデートチェック機能のテストスクリプト
"""

import sys
import os

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils.update_checker import check_for_updates
from VERSION import __version__, GITHUB_REPO_OWNER, GITHUB_REPO_NAME

print("=" * 60)
print("アップデートチェック テスト")
print("=" * 60)
print(f"現在のバージョン: {__version__}")
print(f"GitHubリポジトリ: {GITHUB_REPO_OWNER}/{GITHUB_REPO_NAME}")
print()

print("GitHub APIにアクセスしています...")
try:
    update_info = check_for_updates()

    if update_info is None:
        print("[結果] 新しいバージョンはありません、またはチェックに失敗しました")
    else:
        print("[結果] 新しいバージョンが見つかりました！")
        print()
        print(f"  現在のバージョン: {update_info.current_version}")
        print(f"  最新バージョン: {update_info.latest_version}")
        print(f"  新しいバージョン: {update_info.is_newer}")
        print(f"  リリースURL: {update_info.release_url}")
        print(f"  ダウンロードURL: {update_info.download_url}")
        print()
        print("リリースノート:")
        print(update_info.release_notes)

except Exception as e:
    print(f"[エラー] {e}")
    import traceback
    traceback.print_exc()

print()
print("=" * 60)
