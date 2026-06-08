import os
import uuid
import re
import math
import logging
import shutil
from datetime import datetime

from models.csv_repository import CsvRepository
from models.file_scanner import FileScanner
from models.audit_logger import AuditLogger

logger = logging.getLogger(__name__)


class MetadataManager:
    def __init__(self, root_path):
        if not root_path or not isinstance(root_path, str):
            raise ValueError("ルートパスが有効ではありません。")
        self.root_path = root_path
        self._repo = CsvRepository()
        self._scanner = FileScanner(root_path, self._repo)
        self._audit = AuditLogger(root_path)
        self.columns = CsvRepository.COLUMNS

    def update_root_directory(self, new_root_path):
        """Updates the root directory path."""
        self.root_path = new_root_path
        self._scanner.root_path = new_root_path
        self._audit.root_path = new_root_path

    def _get_csv_path(self, year_nendo):
        return os.path.join(self.root_path, year_nendo, 'index.csv')

    # --- CSV I/O delegated to CsvRepository ---

    def load_df(self, year_nendo):
        return self._repo.load(self._get_csv_path(year_nendo))

    def save_df(self, year_nendo, df):
        self._repo.save(self._get_csv_path(year_nendo), df)

    # --- File system operations delegated to FileScanner ---

    def get_next_doc_id(self, year_nendo, transaction_type, doc_type):
        return self._scanner.get_next_doc_id(year_nendo, transaction_type, doc_type)

    def recalculate_all_doc_ids(self):
        self._scanner.recalculate_all_doc_ids()

    def rebuild_index(self):
        self._scanner.rebuild_index()

    def has_files_for_doc_type(self, transaction_type, doc_type):
        return self._scanner.has_files_for_doc_type(transaction_type, doc_type)

    def has_any_entries(self):
        return self._scanner.has_any_entries()

    # --- CRUD / Search operations ---

    def add_entry(self, year_nendo, data):
        import pandas as pd
        if not isinstance(data, dict) or 'doc_id' not in data:
            raise ValueError("追加するデータが無効です。")

        df = self.load_df(year_nendo)
        new_id = str(uuid.uuid4())
        now = datetime.now().isoformat()

        entry = {
            'id': new_id,
            'created_at': now,
            'updated_at': now
        }
        for col in self.columns:
            if col in data:
                entry[col] = data[col]

        new_df = pd.concat([df, pd.DataFrame([entry])], ignore_index=True)
        self.save_df(year_nendo, new_df)
        self._audit.log_create(year_nendo, new_id, entry)
        return new_id

    def get_available_years(self):
        years = []
        if not os.path.exists(self.root_path):
            return years
        for entry in os.listdir(self.root_path):
            full_path = os.path.join(self.root_path, entry)
            if os.path.isdir(full_path) and re.match(r'^\d{4}年$', entry):
                years.append(entry)
        years.sort(reverse=True)  # Newest year first
        return years

    def is_hash_registered(self, file_hash):
        """Checks if a given file hash is already registered in any index."""
        if not file_hash:
            return False, None, None

        available_years = self.get_available_years()
        for year in available_years:
            df = self.load_df(year)
            if 'file_hash' in df.columns:
                result = df[df['file_hash'] == file_hash]
                if not result.empty:
                    return True, result.iloc[0].to_dict(), year
        return False, None, None

    def search_entries(self, year_nendo, transaction_category=None, doc_type=None,
                       other_org_subfolder=None, client_name=None, date_from=None,
                       date_to=None, amount_from=None, amount_to=None, memo=None):
        import pandas as pd
        logger.debug(f"search_entries - 開始 year_nendo={year_nendo}")
        df = self.load_df(year_nendo)
        if df.empty:
            logger.debug("search_entries - DataFrameが空です")
            return df

        df['issue_date'] = pd.to_numeric(df['issue_date'].astype(str), errors='coerce')
        df['amount'] = pd.to_numeric(df['amount'], errors='coerce')

        if transaction_category:
            df = df[df['category'] == transaction_category]

        if other_org_subfolder:
            df = df[df['file_path'].str.contains(other_org_subfolder, na=False)]

        if doc_type and doc_type != "すべて":
            df = df[df['doc_type'] == doc_type]

        if client_name:
            df = df[df['client_name'].str.contains(client_name, na=False)]

        if memo:
            df = df[df['memo'].str.contains(memo, na=False)]

        if date_from:
            date_from_int = int(date_from.toString("yyyyMMdd"))
            df = df[df['issue_date'].notna() & (df['issue_date'] >= date_from_int)]

        if date_to:
            date_to_int = int(date_to.toString("yyyyMMdd"))
            df = df[df['issue_date'].notna() & (df['issue_date'] <= date_to_int)]

        if amount_from:
            try:
                amount_from_int = int(amount_from)
                df = df[df['amount'].notna() & (df['amount'] >= amount_from_int)]
            except (ValueError, TypeError):
                pass

        if amount_to:
            try:
                amount_to_int = int(amount_to)
                df = df[df['amount'].notna() & (df['amount'] <= amount_to_int)]
            except (ValueError, TypeError):
                pass

        return df

    def get_entry_by_id(self, year_nendo, record_id):
        df = self.load_df(year_nendo)
        if df.empty:
            return None

        df['id'] = df['id'].astype(str)
        record_id = str(record_id)

        result = df[df['id'] == record_id]
        if not result.empty:
            return result.iloc[0].to_dict()
        return None

    def delete_entry(self, year_nendo, record_id):
        df = self.load_df(year_nendo)
        if df.empty:
            return None

        df['id'] = df['id'].astype(str)
        record_id = str(record_id)

        record_to_delete = df[df['id'] == record_id]
        if record_to_delete.empty:
            return None

        deleted_record = record_to_delete.iloc[0].to_dict()
        file_path = deleted_record['file_path']
        df = df[df['id'] != record_id]
        self.save_df(year_nendo, df)
        self._audit.log_delete(year_nendo, record_id, deleted_record)
        return file_path

    def update_entry(self, original_year, record_id, new_data):
        import pandas as pd
        # 1. Load original data
        df_original = self.load_df(original_year)
        if df_original.empty:
            raise RuntimeError(f"{original_year} のインデックスが空です。データが見つかりません。")

        df_original['id'] = df_original['id'].astype(str)
        record_id = str(record_id)

        original_record_list = df_original.index[df_original['id'] == record_id].tolist()
        if not original_record_list:
            raise RuntimeError(f"レコード ID {record_id} が {original_year} のインデックスに見つかりません。")
        original_index = original_record_list[0]
        original_record = df_original.loc[original_index].to_dict()

        # 2. Extract destination info and determine changes
        dest_year = new_data.get('destination_year')
        dest_category = new_data.get('destination_category')
        dest_doc_type = new_data.get('destination_doc_type')

        is_year_changed = dest_year != original_year
        is_category_changed = dest_category != original_record.get('category')
        is_doc_type_changed = dest_doc_type != original_record.get('doc_type')
        is_location_changed = is_year_changed or is_category_changed or is_doc_type_changed

        def _safe_str_cmp(val):
            """NaN/None を空文字列として正規化し文字列比較に使用する。"""
            if val is None or (isinstance(val, float) and math.isnan(val)):
                return ''
            return str(val)

        def _normalize_amount_for_compare(val):
            """金額を int 経由で正規化して比較（"10800", 10800, 10800.0 を同一視）。"""
            try:
                f = float(str(val))
                if math.isnan(f):
                    return ''
                return str(int(f))
            except (ValueError, TypeError):
                return str(val) if val is not None else ''

        is_rename_needed = (
            _safe_str_cmp(new_data.get('issue_date')) != _safe_str_cmp(original_record.get('issue_date')) or
            _normalize_amount_for_compare(new_data.get('amount')) != _normalize_amount_for_compare(original_record.get('amount')) or
            _safe_str_cmp(new_data.get('client_name')) != _safe_str_cmp(original_record.get('client_name'))
        )

        requires_file_operation = is_location_changed or is_rename_needed

        # --- Phase 1: File System Operation ---
        # file_path が NaN や None の場合は更新不可
        raw_file_path = original_record.get('file_path')
        if raw_file_path is None or (isinstance(raw_file_path, float) and math.isnan(raw_file_path)):
            logger.error(f"Record {record_id} has invalid file_path ({raw_file_path!r}). Aborting update.")
            raise RuntimeError(
                f"レコード ID {record_id} のファイルパスが無効です（{raw_file_path!r}）。\n"
                "インデックスを再構築してから再試行してください。"
            )
        old_full_path = os.path.normpath(
            os.path.join(self.root_path, original_year, str(raw_file_path))
        )
        new_full_path = None
        file_op_results = {}

        if requires_file_operation:
            try:
                doc_id = original_record.get('doc_id')
                if is_location_changed:
                    doc_id = self.get_next_doc_id(dest_year, dest_category, dest_doc_type)

                # client_name を Windows ファイル名として無効な文字からサニタイズ
                sanitized_client_name = re.sub(r'[\\/:*?"<>|]', '', str(new_data.get('client_name', '')))
                new_filename = (
                    f"{doc_id}_{new_data['issue_date']}_"
                    f"{new_data['amount']}_{sanitized_client_name}.pdf"
                )
                new_relative_path = os.path.join(dest_category, dest_doc_type, new_filename)
                new_full_path = os.path.join(self.root_path, dest_year, new_relative_path)

                if os.path.exists(old_full_path):
                    dest_dir = os.path.dirname(new_full_path)
                    os.makedirs(dest_dir, exist_ok=True)
                    shutil.move(old_full_path, new_full_path)
                    file_op_results['file_path'] = new_relative_path
                    file_op_results['doc_id'] = doc_id
                else:
                    # ファイルが期待するパスに存在しない（別名でリネーム済みの可能性）
                    # ファイル移動はスキップしてメタデータのみ更新。file_path は元のまま維持。
                    logger.warning(
                        f"Record {record_id}: file not found at '{old_full_path}'. "
                        "Updating metadata without file rename."
                    )
                    file_op_results['file_path'] = str(raw_file_path)
                    file_op_results['doc_id'] = original_record.get('doc_id')

            except Exception as e:
                logger.error(
                    f"File operation failed for record {record_id}: {e}"
                )
                raise RuntimeError(
                    f"ファイルの移動/名前変更に失敗しました。\n"
                    f"エラー: {e}\n\n"
                    f"PDFを別のアプリケーションで開いている場合は閉じてから再試行してください。\n"
                    f"パス: {old_full_path}"
                ) from e

        # --- Phase 2: Index (CSV) Operation ---
        try:
            final_record_data = original_record.copy()
            final_record_data['issue_date'] = new_data['issue_date']
            final_record_data['amount'] = new_data['amount']
            final_record_data['client_name'] = new_data['client_name']
            final_record_data['memo'] = new_data['memo']
            final_record_data['updated_at'] = datetime.now().isoformat()

            if requires_file_operation:
                final_record_data['category'] = dest_category
                final_record_data['doc_type'] = dest_doc_type
                final_record_data['file_path'] = file_op_results['file_path']
                final_record_data['doc_id'] = file_op_results['doc_id']

            if is_year_changed:
                # Cross-year move: delete from old, add to new
                df_original = df_original.drop(original_index)
                self.save_df(original_year, df_original)

                df_new = self.load_df(dest_year)
                entry_to_add = {k: v for k, v in final_record_data.items() if k in self.columns}
                new_entry_df = pd.DataFrame([entry_to_add])
                df_updated = pd.concat([df_new, new_entry_df], ignore_index=True)
                self.save_df(dest_year, df_updated)
            else:
                # Same-year move or metadata-only update
                for key, value in final_record_data.items():
                    if key in df_original.columns:
                        df_original.loc[original_index, key] = value
                self.save_df(original_year, df_original)

            self._audit.log_update(original_year, record_id, original_record, final_record_data)
            return True

        except Exception as e:
            logger.critical(
                f"CRITICAL INCONSISTENCY: Index update failed for record {record_id} "
                f"AFTER file was moved. Error: {e}"
            )
            rollback_msg = ""
            if new_full_path and os.path.exists(new_full_path):
                try:
                    shutil.move(new_full_path, old_full_path)
                    logger.info(f"Rollback successful. File moved back to {old_full_path}")
                    rollback_msg = "\nファイルは元の場所に戻しました。"
                except Exception as move_back_e:
                    logger.critical(
                        f"CRITICAL: ROLLBACK FAILED. File is at {new_full_path}, "
                        f"index is NOT updated. Error: {move_back_e}"
                    )
                    rollback_msg = f"\n警告: ファイルのロールバックに失敗しました。手動で確認してください。\n{new_full_path}"
            raise RuntimeError(
                f"インデックス（CSVファイル）の更新に失敗しました。\nエラー: {e}{rollback_msg}"
            ) from e
