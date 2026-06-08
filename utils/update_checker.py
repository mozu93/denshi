# -*- coding: utf-8 -*-
"""
アップデートチェッカー
GitHub Releases APIを使用して、アプリケーションの最新バージョンをチェックします。
"""

import logging
import os
import re
import sys
from typing import Optional, Dict, Any
from dataclasses import dataclass
from packaging import version
import requests

from VERSION import __version__, GITHUB_REPO_OWNER, GITHUB_REPO_NAME

logger = logging.getLogger(__name__)

# GitHub API設定
GITHUB_API_URL = f"https://api.github.com/repos/{GITHUB_REPO_OWNER}/{GITHUB_REPO_NAME}/releases/latest"
API_TIMEOUT = 10  # タイムアウト時間（秒）


@dataclass
class UpdateInfo:
    """アップデート情報"""
    current_version: str
    latest_version: str
    release_url: str
    release_notes: str
    download_url: str
    is_newer: bool


def check_for_updates() -> Optional[UpdateInfo]:
    """
    GitHub Releases APIで最新バージョンをチェックします。

    Returns:
        UpdateInfo: 新しいバージョンが存在する場合、アップデート情報を返します
        None: 最新バージョンを使用中、またはチェックに失敗した場合

    Raises:
        なし（すべての例外は内部でキャッチされ、ログに記録されます）
    """
    try:
        logger.info(f"アップデートチェックを開始します（現在のバージョン: {__version__}）")

        # GitHub API リクエスト
        headers = {
            'Accept': 'application/vnd.github.v3+json',
            'User-Agent': f'DenshiChobohozoSystem/{__version__}'
        }

        response = requests.get(
            GITHUB_API_URL,
            headers=headers,
            timeout=API_TIMEOUT
        )

        # HTTPステータスコードのチェック
        if response.status_code == 404:
            logger.warning("リリース情報が見つかりません（リポジトリが存在しないか、リリースが公開されていません）")
            return None
        elif response.status_code == 403:
            logger.warning("GitHub API レート制限に達しました。しばらく待ってから再試行してください。")
            return None
        elif response.status_code != 200:
            logger.warning(f"GitHub APIからの応答が不正です（ステータスコード: {response.status_code}）")
            return None

        # レスポンスのパース
        release_data = response.json()
        latest_version = release_data.get('tag_name', '').lstrip('v')

        if not latest_version:
            logger.warning("最新バージョン情報の取得に失敗しました")
            return None

        # バージョン比較
        current_ver = version.parse(__version__.lstrip('v'))
        latest_ver = version.parse(latest_version)

        is_newer = latest_ver > current_ver

        if is_newer:
            logger.info(f"新しいバージョンが見つかりました: {latest_version}")
        else:
            logger.info(f"最新バージョンを使用中です（最新: {latest_version}）")

        # アップデート情報を構築
        raw_notes = release_data.get('body', '更新情報はありません。')
        update_info = UpdateInfo(
            current_version=__version__,
            latest_version=f"v{latest_version}",
            release_url=release_data.get('html_url', ''),
            release_notes=_clean_release_notes(raw_notes),
            download_url=_extract_download_url(release_data),
            is_newer=is_newer
        )

        return update_info if is_newer else None

    except requests.exceptions.Timeout:
        logger.warning(f"アップデートチェックがタイムアウトしました（{API_TIMEOUT}秒）")
        return None

    except requests.exceptions.ConnectionError:
        logger.warning("アップデートチェックに失敗しました（ネットワーク接続を確認してください）")
        return None

    except requests.exceptions.RequestException as e:
        logger.warning(f"アップデートチェック中にエラーが発生しました: {e}")
        return None

    except Exception as e:
        logger.error(f"予期しないエラーが発生しました: {e}", exc_info=True)
        return None


def _clean_release_notes(body: str) -> str:
    """リリースノートからインストール方法セクションを除去し、プレーンテキストに整形する。"""
    # 「### インストール方法」または「## インストール方法」セクションを削除
    body = re.sub(
        r'#{1,3}\s*インストール方法.*?(?=\n#{1,3}\s|\Z)',
        '',
        body,
        flags=re.DOTALL
    )
    # Markdown見出し（## / ###）をプレーンテキストに変換
    body = re.sub(r'^#{1,6}\s*', '', body, flags=re.MULTILINE)
    # 箇条書き（- / * / 数字.）をプレーンテキストに変換
    body = re.sub(r'^[\-\*]\s+', '・', body, flags=re.MULTILINE)
    body = re.sub(r'^\d+\.\s+', '・', body, flags=re.MULTILINE)
    # 強調（**bold**）を除去
    body = re.sub(r'\*{1,2}(.+?)\*{1,2}', r'\1', body)
    # バッククォート除去
    body = re.sub(r'`(.+?)`', r'\1', body)
    # 連続する空行を1行にまとめて整形
    body = re.sub(r'\n{3,}', '\n\n', body)
    return body.strip()[:600]


def _extract_download_url(release_data: Dict[str, Any]) -> str:
    """
    リリースデータからダウンロードURLを抽出します。

    Args:
        release_data: GitHub API レスポンスデータ

    Returns:
        str: ダウンロードURL（見つからない場合はリリースページURL）
    """
    try:
        assets = release_data.get('assets', [])

        # .exeファイルを検索
        for asset in assets:
            asset_name = asset.get('name', '').lower()
            if asset_name.endswith('.exe') and 'setup' in asset_name:
                return asset.get('browser_download_url', '')

        # .exeファイルが見つからない場合は、最初のassetのURL
        if assets:
            return assets[0].get('browser_download_url', '')

        # assetsがない場合はダウンロード不可（ブラウザ誘導に切り替え）
        return ''

    except Exception as e:
        logger.warning(f"ダウンロードURLの抽出に失敗しました: {e}")
        return ''


def format_version_for_display(version_str: str) -> str:
    if not version_str.startswith('v'):
        return f"v{version_str}"
    return version_str


def download_installer(
    url: str,
    progress_callback=None,
) -> Optional[str]:
    """インストーラーを一時フォルダにダウンロードする。失敗時は None を返す"""
    import tempfile
    import urllib.request
    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": f"DenshiChobohozoSystem/{__version__}"},
        )
        with urllib.request.urlopen(req, timeout=120) as resp:
            total = int(resp.headers.get("Content-Length", -1))
            fd, tmp_path = tempfile.mkstemp(
                prefix="DenshiChobohozoSystem_new_", suffix=".exe"
            )
            received = 0
            with os.fdopen(fd, "wb") as f:
                while True:
                    chunk = resp.read(65536)
                    if not chunk:
                        break
                    f.write(chunk)
                    received += len(chunk)
                    if progress_callback:
                        progress_callback(received, total)

        # PE ヘッダー検証（MZ マジックバイト）
        with open(tmp_path, "rb") as f:
            magic = f.read(2)
        if magic != b"MZ":
            os.unlink(tmp_path)
            logger.error(
                f"ダウンロードしたファイルが有効な実行ファイルではありません（先頭バイト: {magic!r}）。"
                "GitHub Release にインストーラーがアップロードされているか確認してください。"
            )
            return None

        return tmp_path
    except Exception as e:
        logger.error(f"インストーラーのダウンロードに失敗しました: {e}")
        return None


def launch_installer(installer_path: str) -> None:
    """バッチファイル経由でインストーラーを起動し、アプリを終了する。
    バッチが3秒待機してアプリ終了後にインストーラーを起動する。"""
    import subprocess
    import tempfile
    fd, bat_path = tempfile.mkstemp(
        prefix="DenshiChobohozoSystem_updater_", suffix=".bat"
    )
    with os.fdopen(fd, "w", encoding="cp932") as f:
        f.write("@echo off\r\n")
        f.write("timeout /t 3 /nobreak > nul\r\n")
        f.write(f'start "" "{installer_path}"\r\n')
        f.write('del "%~f0"\r\n')
    subprocess.Popen(
        ["cmd", "/c", bat_path],
        creationflags=subprocess.CREATE_NO_WINDOW,
    )
    sys.exit(0)
