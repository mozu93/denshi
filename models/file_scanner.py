import os
import re
import uuid
import logging
import pandas as pd
from datetime import datetime

logger = logging.getLogger(__name__)


class FileScanner:
    def __init__(self, root_path: str, csv_repo):
        self.root_path = root_path
        self._repo = csv_repo

    def _get_csv_path(self, year_nendo: str) -> str:
        return os.path.join(self.root_path, year_nendo, 'index.csv')

    def get_next_doc_id(self, year_nendo: str, transaction_type: str, doc_type: str) -> str:
        if not all([year_nendo, transaction_type, doc_type]):
            return "001"

        target_dir = os.path.join(self.root_path, year_nendo, transaction_type, doc_type)

        try:
            if not os.path.exists(target_dir):
                return "001"

            max_id = 0
            for filename in os.listdir(target_dir):
                match = re.match(r'(\d+)_.*\.pdf$', filename)
                if match:
                    file_id = int(match.group(1))
                    max_id = max(max_id, file_id)

            return f"{max_id + 1:03d}"

        except OSError as e:
            logger.error(f"ディレクトリの読み取りに失敗しました: {target_dir}, エラー: {e}")
            return "001"

    def recalculate_all_doc_ids(self):
        """起動時に全ドキュメントの通し番号を再計算する。"""
        logger.info("全ドキュメントの通し番号再計算を開始します。")

        try:
            if not os.path.exists(self.root_path):
                logger.warning(f"ルートパスが存在しません: {self.root_path}")
                return

            for year_nendo_dir in os.listdir(self.root_path):
                year_path = os.path.join(self.root_path, year_nendo_dir)
                if not os.path.isdir(year_path) or not re.match(r'^\d{4}年$', year_nendo_dir):
                    continue

                logger.debug(f"年度 {year_nendo_dir} の処理を開始。")

                for category_dir in os.listdir(year_path):
                    category_path = os.path.join(year_path, category_dir)
                    if not os.path.isdir(category_path):
                        continue

                    for doc_type_dir in os.listdir(category_path):
                        doc_type_path = os.path.join(category_path, doc_type_dir)
                        if not os.path.isdir(doc_type_path):
                            continue

                        files = [
                            f for f in os.listdir(doc_type_path)
                            if f.lower().endswith('.pdf')
                        ]
                        files.sort(
                            key=lambda x: int(re.match(r'(\d+)_', x).group(1))
                            if re.match(r'(\d+)_', x) else 0
                        )

                        for new_id, old_filename in enumerate(files, 1):
                            old_path = os.path.join(doc_type_path, old_filename)
                            parts = old_filename.replace('.pdf', '').split('_')

                            if len(parts) >= 3:
                                new_id_str = f"{new_id:03d}"
                                new_filename = f"{new_id_str}_{'_'.join(parts[1:])}.pdf"
                                new_path = os.path.join(doc_type_path, new_filename)

                                if old_path != new_path:
                                    try:
                                        os.rename(old_path, new_path)
                                        logger.debug(f"リネーム: {old_filename} → {new_filename}")
                                    except OSError as e:
                                        logger.error(
                                            f"ファイルのリネームに失敗しました: "
                                            f"{old_path} → {new_path}, エラー: {e}"
                                        )

            logger.info("全ドキュメントの通し番号再計算が完了しました。")
        except Exception as e:
            logger.error(f"通し番号再計算処理でエラーが発生しました: {e}")

    def rebuild_index(self):
        """Scans all managed directories, parses filenames, and overwrites the index.csv for each year.
        Preserves memo data from existing index.csv if available."""
        for year_nendo_dir in os.listdir(self.root_path):
            year_path = os.path.join(self.root_path, year_nendo_dir)
            if not os.path.isdir(year_path) or not re.match(r'^\d{4}年$', year_nendo_dir):
                continue

            # 既存のインデックスからメモデータを読み込む
            old_memo_map = {}
            try:
                csv_path = self._get_csv_path(year_nendo_dir)
                old_df = self._repo.load(csv_path)
                if not old_df.empty and 'memo' in old_df.columns:
                    for _, row in old_df.iterrows():
                        memo_val = row.get('memo', '')
                        if pd.isna(memo_val) or not str(memo_val).strip():
                            continue
                        memo = str(memo_val).strip()

                        # ① ファイルパスキー（正規化）
                        fp = row.get('file_path', '')
                        if not pd.isna(fp) and str(fp).strip():
                            old_memo_map[os.path.normpath(str(fp).strip())] = memo

                        # ② 内容キー（ファイル名変更時のフォールバック）
                        category = '' if pd.isna(row.get('category', ''))    else str(row.get('category', '')).strip()
                        doc_type = '' if pd.isna(row.get('doc_type', ''))    else str(row.get('doc_type', '')).strip()
                        idt      = '' if pd.isna(row.get('issue_date', ''))  else str(row.get('issue_date', '')).strip()
                        amt      = '' if pd.isna(row.get('amount', ''))      else str(row.get('amount', '')).strip()
                        cname    = '' if pd.isna(row.get('client_name', '')) else str(row.get('client_name', '')).strip()
                        if all([category, doc_type, idt, amt, cname]):
                            old_memo_map[(category, doc_type, idt, amt, cname)] = memo

                logger.debug(f"Loaded {len(old_memo_map)} memos from existing index for {year_nendo_dir}")
            except Exception as e:
                logger.warning(f"Could not load existing memos: {e}")

            current_year_metadata = []
            for category_dir in os.listdir(year_path):
                category_path = os.path.join(year_path, category_dir)
                if not os.path.isdir(category_path):
                    continue

                for doc_type_dir in os.listdir(category_path):
                    doc_type_path = os.path.join(category_path, doc_type_dir)
                    if not os.path.isdir(doc_type_path):
                        continue

                    for filename in os.listdir(doc_type_path):
                        if not filename.lower().endswith('.pdf'):
                            continue

                        file_path = os.path.join(doc_type_path, filename)
                        # 取引先名にアンダースコアが含まれる場合も考慮して最大4分割
                        parts = filename.replace('.pdf', '').split('_', 3)
                        if len(parts) < 4:
                            continue

                        doc_id, issue_date, amount, client_name = parts

                        try:
                            relative_path = os.path.relpath(file_path, year_path)

                            # ① ファイルパスキーで検索
                            memo = old_memo_map.get(os.path.normpath(relative_path), '')
                            # ② パス不一致時は内容キーでフォールバック
                            if not memo:
                                content_key = (category_dir, doc_type_dir, str(issue_date), str(amount), client_name)
                                memo = old_memo_map.get(content_key, '')

                            metadata = {
                                'id': str(uuid.uuid4()),
                                'doc_id': doc_id,
                                'category': category_dir,
                                'doc_type': doc_type_dir,
                                'issue_date': issue_date,
                                'client_name': client_name,
                                'amount': int(amount),
                                'memo': memo,
                                'file_path': relative_path,
                                'created_at': datetime.now().isoformat(),
                                'updated_at': datetime.now().isoformat()
                            }
                            current_year_metadata.append(metadata)
                        except (ValueError, TypeError):
                            logger.warning(f"Skipping file with invalid amount: {filename}")
                            continue

            csv_path = self._get_csv_path(year_nendo_dir)
            df = pd.DataFrame(current_year_metadata)
            self._repo.save(csv_path, df)
            memo_count = len([m for m in current_year_metadata if m['memo']])
            logger.info(
                f"Rebuilt index for {year_nendo_dir} with {len(current_year_metadata)} records, "
                f"preserved {memo_count} memos"
            )

    def has_files_for_doc_type(self, transaction_type: str, doc_type: str) -> bool:
        for year_nendo_dir in os.listdir(self.root_path):
            full_year_path = os.path.join(self.root_path, year_nendo_dir)
            if os.path.isdir(full_year_path) and re.match(r'^\d{4}年$', year_nendo_dir):
                target_dir = os.path.join(full_year_path, transaction_type, doc_type)
                if os.path.exists(target_dir) and len(os.listdir(target_dir)) > 0:
                    return True
        return False

    def has_any_entries(self) -> bool:
        for year_nendo_dir in os.listdir(self.root_path):
            full_path = os.path.join(self.root_path, year_nendo_dir)
            if os.path.isdir(full_path) and re.match(r'^\d{4}年$', year_nendo_dir):
                csv_path = self._get_csv_path(year_nendo_dir)
                if os.path.exists(csv_path):
                    df = self._repo.load(csv_path)  # Bug fix: bypasses load_df
                    if not df.empty:
                        return True
        return False
