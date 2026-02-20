# -*- coding: utf-8 -*-
"""
アップデートチェッカー
GitHub Releases APIを使用して、アプリケーションの最新バージョンをチェックします。
"""

import logging
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
        update_info = UpdateInfo(
            current_version=__version__,
            latest_version=f"v{latest_version}",
            release_url=release_data.get('html_url', ''),
            release_notes=release_data.get('body', '更新情報はありません。')[:500],  # 先頭500文字
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

        # assetsがない場合はリリースページURL
        return release_data.get('html_url', '')

    except Exception as e:
        logger.warning(f"ダウンロードURLの抽出に失敗しました: {e}")
        return release_data.get('html_url', '')


def format_version_for_display(version_str: str) -> str:
    """
    バージョン文字列を表示用にフォーマットします。

    Args:
        version_str: バージョン文字列（例: "v2.0.0" or "2.0.0"）

    Returns:
        str: フォーマットされたバージョン文字列（例: "v2.0.0"）
    """
    if not version_str.startswith('v'):
        return f"v{version_str}"
    return version_str
