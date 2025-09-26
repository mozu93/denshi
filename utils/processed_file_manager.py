import os
import shutil
import datetime
import glob
import logging
from pathlib import Path

class ProcessedFileManager:
    """処理済ファイル管理クラス

    機能:
    - 処理済フォルダの自動作成
    - 処理済ファイルの移動
    - 30日経過後のファイル自動削除
    """

    PROCESSED_FOLDER_NAME = "処理済"
    RETENTION_DAYS = 30

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def get_processed_folder_path(self, source_folder):
        """処理済フォルダのパスを取得"""
        return os.path.join(source_folder, self.PROCESSED_FOLDER_NAME)

    def create_processed_folder(self, source_folder):
        """処理済フォルダを作成"""
        processed_folder = self.get_processed_folder_path(source_folder)
        try:
            os.makedirs(processed_folder, exist_ok=True)
            self.logger.info(f"処理済フォルダを作成: {processed_folder}")
            return processed_folder
        except OSError as e:
            self.logger.error(f"処理済フォルダの作成に失敗: {e}")
            raise RuntimeError(f"処理済フォルダの作成に失敗しました: {e}")

    def move_to_processed_folder(self, file_path):
        """ファイルを処理済フォルダに移動"""
        try:
            # ファイルの存在確認
            if not os.path.exists(file_path):
                raise RuntimeError(f"ソースファイルが存在しません: {file_path}")

            source_dir = os.path.dirname(file_path)
            file_name = os.path.basename(file_path)

            self.logger.info(f"ファイル移動開始: {file_path}")
            self.logger.info(f"ソースディレクトリ: {source_dir}")

            # 処理済フォルダを作成
            processed_folder = self.create_processed_folder(source_dir)
            self.logger.info(f"処理済フォルダ: {processed_folder}")

            # 移動先パス
            dest_path = os.path.join(processed_folder, file_name)

            # 同名ファイルがある場合はタイムスタンプを付加
            if os.path.exists(dest_path):
                name, ext = os.path.splitext(file_name)
                timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                dest_path = os.path.join(processed_folder, f"{name}_{timestamp}{ext}")
                self.logger.info(f"同名ファイル存在のため名前変更: {dest_path}")

            # ファイル移動
            self.logger.info(f"ファイル移動実行: {file_path} → {dest_path}")
            shutil.move(file_path, dest_path)
            self.logger.info(f"ファイル移動完了: {dest_path}")
            return dest_path

        except (OSError, IOError) as e:
            error_msg = f"ファイル移動に失敗: {e} (ソース: {file_path})"
            self.logger.error(error_msg)
            raise RuntimeError(error_msg)

    def cleanup_old_files(self, source_folder):
        """30日以上経過したファイルを削除"""
        processed_folder = self.get_processed_folder_path(source_folder)

        if not os.path.exists(processed_folder):
            return

        cutoff_date = datetime.datetime.now() - datetime.timedelta(days=self.RETENTION_DAYS)
        deleted_count = 0

        try:
            # 処理済フォルダ内の全ファイルをチェック
            for file_path in glob.glob(os.path.join(processed_folder, "*")):
                if os.path.isfile(file_path):
                    # ファイルの更新日時を取得
                    file_mtime = datetime.datetime.fromtimestamp(os.path.getmtime(file_path))

                    # 30日以上経過していれば削除
                    if file_mtime < cutoff_date:
                        try:
                            os.remove(file_path)
                            deleted_count += 1
                            self.logger.info(f"古いファイルを削除: {file_path}")
                        except OSError as e:
                            self.logger.warning(f"ファイル削除に失敗: {file_path}, エラー: {e}")

            if deleted_count > 0:
                self.logger.info(f"古いファイル {deleted_count}件を削除しました")

            return deleted_count

        except Exception as e:
            self.logger.error(f"古いファイルの削除処理でエラー: {e}")
            return 0

    def get_processed_files_info(self, source_folder):
        """処理済フォルダ内のファイル情報を取得"""
        processed_folder = self.get_processed_folder_path(source_folder)

        if not os.path.exists(processed_folder):
            return []

        files_info = []
        try:
            for file_path in glob.glob(os.path.join(processed_folder, "*")):
                if os.path.isfile(file_path):
                    stat = os.stat(file_path)
                    files_info.append({
                        'name': os.path.basename(file_path),
                        'path': file_path,
                        'size': stat.st_size,
                        'modified': datetime.datetime.fromtimestamp(stat.st_mtime),
                        'days_until_deletion': self.RETENTION_DAYS - (datetime.datetime.now() - datetime.datetime.fromtimestamp(stat.st_mtime)).days
                    })

            # 更新日時でソート
            files_info.sort(key=lambda x: x['modified'], reverse=True)
            return files_info

        except Exception as e:
            self.logger.error(f"処理済ファイル情報の取得でエラー: {e}")
            return []

    def cleanup_all_folders(self, root_path):
        """指定パス配下の全ての処理済フォルダをクリーンアップ"""
        total_deleted = 0

        try:
            # root_path配下の全ディレクトリを検索
            for root, dirs, files in os.walk(root_path):
                if self.PROCESSED_FOLDER_NAME in dirs:
                    folder_path = root
                    deleted = self.cleanup_old_files(folder_path)
                    total_deleted += deleted

            if total_deleted > 0:
                self.logger.info(f"全体で {total_deleted}件の古いファイルを削除しました")

            return total_deleted

        except Exception as e:
            self.logger.error(f"全体クリーンアップでエラー: {e}")
            return 0