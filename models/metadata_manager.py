import pandas as pd
import os
import uuid
import re
from datetime import datetime

class MetadataManager:
    def __init__(self, root_path):
        self.root_path = root_path

    def _get_csv_path(self, year_nendo):
        return os.path.join(self.root_path, year_nendo, 'index.csv')

    def load_df(self, year_nendo):
        csv_path = self._get_csv_path(year_nendo)
        if os.path.exists(csv_path):
            return pd.read_csv(csv_path)
        else:
            return pd.DataFrame(columns=[
                'id', 'doc_id', 'category', 'doc_type', 'issue_date', 
                'client_name', 'amount', 'memo', 'file_path', 
                'created_at', 'updated_at'
            ])

    def save_df(self, year_nendo, df):
        csv_path = self._get_csv_path(year_nendo)
        os.makedirs(os.path.dirname(csv_path), exist_ok=True)
        df.to_csv(csv_path, index=False, encoding='utf-8-sig')

    def add_entry(self, year_nendo, data):
        df = self.load_df(year_nendo)
        new_id = str(uuid.uuid4())
        now = datetime.now().isoformat()
        entry = {
            'id': new_id,
            'created_at': now,
            'updated_at': now,
            **data
        }
        new_df = pd.concat([df, pd.DataFrame([entry])], ignore_index=True)
        self.save_df(year_nendo, new_df)
        return new_id

    def get_next_doc_id(self, year_nendo, transaction_type, doc_type):
        target_dir = os.path.join(self.root_path, year_nendo, transaction_type, doc_type)
        if not os.path.exists(target_dir):
            return "001"

        max_id = 0
        for filename in os.listdir(target_dir):
            match = re.match(r'(\d+)_.*\.pdf', filename)
            if match:
                doc_id = int(match.group(1))
                if doc_id > max_id:
                    max_id = doc_id
        
        return f"{max_id + 1:03d}"

    def rebuild_index(self):
        """Scans all managed directories, parses filenames, and overwrites the index.csv for each year."""
        for year_nendo_dir in os.listdir(self.root_path):
            year_path = os.path.join(self.root_path, year_nendo_dir)
            if not os.path.isdir(year_path) or not re.match(r'^\d{4}年度$', year_nendo_dir):
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
            if os.path.isdir(full_year_path) and re.match(r'^\d{4}年度$', year_nendo_dir):
                target_dir = os.path.join(full_year_path, transaction_type, doc_type)
                if os.path.exists(target_dir) and len(os.listdir(target_dir)) > 0:
                    return True
        return False

    def has_any_entries(self):
        for year_nendo_dir in os.listdir(self.root_path):
            full_path = os.path.join(self.root_path, year_nendo_dir)
            if os.path.isdir(full_path) and re.match(r'^\d{4}年度$', year_nendo_dir):
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
            if os.path.isdir(full_path) and re.match(r'^\d{4}年度$', entry):
                years.append(entry)
        years.sort(reverse=True) # Newest year first
        return years

    def search_entries(self, year_nendo, doc_type=None, client_name=None, date_from=None, date_to=None, amount_from=None, amount_to=None, memo=None):
        df = self.load_df(year_nendo)
        if df.empty:
            return df

        df['issue_date'] = pd.to_numeric(df['issue_date'].astype(str), errors='coerce')
        df['amount'] = pd.to_numeric(df['amount'], errors='coerce')

        if doc_type and doc_type != "すべて":
            df = df[df['doc_type'] == doc_type]
        
        if client_name:
            df = df[df['client_name'].str.contains(client_name, na=False)]
            
        if memo:
            df = df[df['memo'].str.contains(memo, na=False)]

        if date_from:
            date_from_int = int(date_from.toString("yyyyMMdd"))
            df = df[df['issue_date'] >= date_from_int]

        if date_to:
            date_to_int = int(date_to.toString("yyyyMMdd"))
            df = df[df['issue_date'] <= date_to_int]

        if amount_from:
            try:
                df = df[df['amount'] >= int(amount_from)]
            except (ValueError, TypeError):
                pass

        if amount_to:
            try:
                df = df[df['amount'] >= int(amount_to)]
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