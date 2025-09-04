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
        df.to_csv(csv_path, index=False, encoding='utf-8-sig') # BOM付きUTF-8

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
        all_metadata = []
        for year_nendo_dir in os.listdir(self.root_path):
            # Skip non-directory entries or entries not matching the "YYYY年度" pattern
            if not os.path.isdir(os.path.join(self.root_path, year_nendo_dir)) or not re.match(r'^\d{4}年度$', year_nendo_dir):
                continue
            
            year_path = os.path.join(self.root_path, year_nendo_dir)

            for category_dir in os.listdir(year_path):
                category_path = os.path.join(year_path, category_dir)
                if not os.path.isdir(category_path):
                    continue

                for doc_type_dir in os.listdir(category_path):
                    doc_type_path = os.path.join(category_path, doc_type_dir)
                    if not os.path.isdir(doc_type_path):
                        continue

                    for filename in os.listdir(doc_type_path):
                        if not filename.endswith('.pdf'):
                            continue

                        file_path = os.path.join(doc_type_path, filename)
                        parts = filename.replace('.pdf', '').split('_')
                        if len(parts) != 4:
                            continue

                        doc_id, issue_date, amount, client_name = parts
                        
                        metadata = {
                            'id': str(uuid.uuid4()),
                            'doc_id': doc_id,
                            'category': category_dir,
                            'doc_type': doc_type_dir,
                            'issue_date': issue_date,
                            'client_name': client_name,
                            'amount': int(amount),
                            'memo': '',
                            'file_path': os.path.relpath(file_path, year_path),
                            'created_at': datetime.now().isoformat(),
                            'updated_at': datetime.now().isoformat()
                        }
                        all_metadata.append(metadata)

        df = pd.DataFrame(all_metadata)
        # Group by year_nendo from file_path for saving
        if not df.empty:
            df['year_nendo'] = df['file_path'].apply(lambda x: os.path.normpath(x).split(os.sep)[0])
            for year_nendo, group in df.groupby('year_nendo'):
                self.save_df(year_nendo, group.drop(columns=['year_nendo']))
        else:
            # If no files found, ensure existing index.csv files are cleared or handled as per requirement
            # For now, we'll just pass, assuming no old index files means no data.
            pass