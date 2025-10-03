import pandas as pd
import os
import uuid
import re
import logging
from datetime import datetime

class MetadataManager:
    def __init__(self, root_path):
        # バリデーション: root_pathがNoneや空文字列でないことを確認
        if not root_path or not isinstance(root_path, str):
            # root_pathが不正な場合、処理を続行できないため例外を送出
            raise ValueError("ルートパスが有効ではありません。")
        self.root_path = root_path
        self.columns = [
            'id', 'doc_id', 'category', 'doc_type', 'issue_date', 
            'client_name', 'amount', 'memo', 'file_path', 'file_hash',
            'created_at', 'updated_at'
        ]

    def update_root_directory(self, new_root_path):
        """Updates the root directory path."""
        self.root_path = new_root_path

    def _get_csv_path(self, year_nendo):
        return os.path.join(self.root_path, year_nendo, 'index.csv')

    def load_df(self, year_nendo):
        csv_path = self._get_csv_path(year_nendo)
        logging.debug(f"load_df - csv_path: {csv_path}")
        if not csv_path or not os.path.exists(csv_path):
            logging.debug(f"load_df - CSVファイルが存在しません: {csv_path}")
            return pd.DataFrame(columns=self.columns)

        try:
            # CSVファイルの読み込み
            # - ファイル破損によるパースエラー(ParserError)が発生する可能性がある
            # - メモリ不足エラーなど、予期せぬ例外が発生する可能性もある
            df = pd.read_csv(csv_path)
            logging.debug(f"load_df - CSVを読み込み成功: {len(df)} 行")
            # カラムの検証: 必須カラムが存在するか確認
            required_columns = ['id', 'doc_id', 'category', 'doc_type', 'issue_date', 'client_name', 'amount', 'memo', 'file_path']
            missing_required = [col for col in required_columns if col not in df.columns]
            if missing_required:
                logging.warning(f"CSVファイル '{csv_path}' に必須カラム {missing_required} が不足しています。空のデータフレームを返します。")
                return pd.DataFrame(columns=self.columns)

            # file_hashカラムが存在しない場合は空文字で追加
            if 'file_hash' not in df.columns:
                df['file_hash'] = ''
                logging.debug("file_hashカラムが存在しないため、空文字で追加しました。")

            # 不足しているカラムがあれば追加
            for col in self.columns:
                if col not in df.columns:
                    df[col] = ''
            return df
        except (pd.errors.ParserError, Exception) as e:
            logging.error(f"CSVファイル '{csv_path}' の読み込みに失敗しました: {e}")
            # 読み込み失敗時は空のデータフレームを返し、処理の続行を試みる
            return pd.DataFrame(columns=self.columns)

    def save_df(self, year_nendo, df):
        csv_path = self._get_csv_path(year_nendo)
        if not csv_path:
            raise ValueError(f"無効な年です: {year_nendo}")

        try:
            # ディレクトリの作成とCSVファイルの保存
            # - 書き込み権限がない場合にPermissionError/OSErrorが発生する可能性がある
            os.makedirs(os.path.dirname(csv_path), exist_ok=True)
            df.to_csv(csv_path, index=False, encoding='utf-8-sig')
        except (IOError, OSError) as e:
            logging.error(f"CSVファイル '{csv_path}' の保存に失敗しました: {e}")
            # 保存失敗はデータ損失に繋がるため、例外を再送出して呼び出し元に通知
            raise RuntimeError(f"インデックスファイルの保存に失敗しました。権限などを確認してください。: {e}")

    def add_entry(self, year_nendo, data):
        # 入力データ(data)の基本的な検証
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
        # 期待されるカラムのみをdataから取得し、予期せぬキーが追加されるのを防ぐ
        for col in self.columns:
            if col in data:
                entry[col] = data[col]

        new_df = pd.concat([df, pd.DataFrame([entry])], ignore_index=True)
        self.save_df(year_nendo, new_df)
        return new_id

    def get_next_doc_id(self, year_nendo, transaction_type, doc_type):
        # 入力値の検証
        if not all([year_nendo, transaction_type, doc_type]):
            return "001"

        target_dir = os.path.join(self.root_path, year_nendo, transaction_type, doc_type)
        
        try:
            if not os.path.exists(target_dir):
                return "001"

            max_id = 0
            # ディレクトリが読み取れない場合、OSErrorが発生する可能性がある
            for filename in os.listdir(target_dir):
                match = re.match(r'(\d+)_.*\.pdf$', filename)
                if match:
                    file_id = int(match.group(1))
                    max_id = max(max_id, file_id)

            return f"{max_id + 1:03d}"

        except OSError as e:
            logging.error(f"ディレクトリの読み取りに失敗しました: {target_dir}, エラー: {e}")
            return "001"

    def rebuild_index(self):
        """Scans all managed directories, parses filenames, and overwrites the index.csv for each year."""
        for year_nendo_dir in os.listdir(self.root_path):
            year_path = os.path.join(self.root_path, year_nendo_dir)
            if not os.path.isdir(year_path) or not re.match(r'^\d{4}年$', year_nendo_dir):
                continue

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
                        parts = filename.replace('.pdf', '').split('_')
                        if len(parts) != 4:
                            continue

                        doc_id, issue_date, amount, client_name = parts
                        
                        try:
                            metadata = {
                                'id': str(uuid.uuid4()),
                                'doc_id': doc_id,
                                'category': category_dir,
                                'doc_type': doc_type_dir,
                                'issue_date': issue_date,
                                'client_name': client_name,
                                'amount': int(amount),
                                'memo': '', # Memos are lost on rebuild as per spec
                                'file_path': os.path.relpath(file_path, year_path),
                                'created_at': datetime.now().isoformat(),
                                'updated_at': datetime.now().isoformat()
                            }
                            current_year_metadata.append(metadata)
                        except (ValueError, TypeError):
                            print(f"Skipping file with invalid amount: {filename}")
                            continue
            
            df = pd.DataFrame(current_year_metadata)
            self.save_df(year_nendo_dir, df)

    def has_files_for_doc_type(self, transaction_type, doc_type):
        for year_nendo_dir in os.listdir(self.root_path):
            full_year_path = os.path.join(self.root_path, year_nendo_dir)
            if os.path.isdir(full_year_path) and re.match(r'^\d{4}年$', year_nendo_dir):
                target_dir = os.path.join(full_year_path, transaction_type, doc_type)
                if os.path.exists(target_dir) and len(os.listdir(target_dir)) > 0:
                    return True
        return False

    def has_any_entries(self):
        for year_nendo_dir in os.listdir(self.root_path):
            full_path = os.path.join(self.root_path, year_nendo_dir)
            if os.path.isdir(full_path) and re.match(r'^\d{4}年$', year_nendo_dir):
                csv_path = self._get_csv_path(year_nendo_dir)
                if os.path.exists(csv_path):
                    df = pd.read_csv(csv_path)
                    if not df.empty:
                        return True
        return False

    def get_available_years(self):
        years = []
        if not os.path.exists(self.root_path):
            return years
        for entry in os.listdir(self.root_path):
            full_path = os.path.join(self.root_path, entry)
            if os.path.isdir(full_path) and re.match(r'^\d{4}年$', entry):
                years.append(entry)
        years.sort(reverse=True) # Newest year first
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
                    # Return True, the record, and the year it was found in
                    return True, result.iloc[0].to_dict(), year
        return False, None, None

    def search_entries(self, year_nendo, transaction_category=None, doc_type=None, other_org_subfolder=None, client_name=None, date_from=None, date_to=None, amount_from=None, amount_to=None, memo=None):
        logging.debug(f"search_entries - 開始 year_nendo={year_nendo}")
        df = self.load_df(year_nendo)
        if df.empty:
            logging.debug("search_entries - DataFrameが空です")
            return df

        df['issue_date'] = pd.to_numeric(df['issue_date'].astype(str), errors='coerce')
        df['amount'] = pd.to_numeric(df['amount'], errors='coerce')

        # 取引区分でフィルタ
        if transaction_category:
            df = df[df['category'] == transaction_category]

        # その他団体の場合、サブフォルダでフィルタ
        if other_org_subfolder:
            # file_pathから該当するサブフォルダを含む行のみ抽出
            df = df[df['file_path'].str.contains(other_org_subfolder, na=False)]

        # 書類種別でフィルタ（その他団体以外の場合）
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

        file_path = record_to_delete.iloc[0]['file_path']
        df = df[df['id'] != record_id]
        self.save_df(year_nendo, df)
        return file_path

    def update_entry(self, year_nendo, record_id, new_data):
        df = self.load_df(year_nendo)
        if df.empty:
            return False

        df['id'] = df['id'].astype(str)
        record_id = str(record_id)

        record_index = df.index[df['id'] == record_id].tolist()
        if not record_index:
            return False
        
        index = record_index[0]

        for key, value in new_data.items():
            if key in df.columns:
                df.loc[index, key] = value
        
        df.loc[index, 'updated_at'] = datetime.now().isoformat()

        self.save_df(year_nendo, df)
        return True