# -*- coding: utf-8 -*-
"""
監査ログ - 電子帳簿保存法 真実性確保（訂正・削除の記録）対応

audit_log.csv はルートパス直下に追記専用で保存される。
アプリからの削除・上書きは行わない。
"""

import json
import logging
import os
import uuid
from datetime import datetime

import pandas as pd
from filelock import FileLock

logger = logging.getLogger(__name__)

AUDIT_COLUMNS = [
    'log_id',       # ログ一意ID
    'logged_at',    # 操作日時（ISO8601）
    'operation',    # CREATE / UPDATE / DELETE
    'year_nendo',   # 対象年度
    'record_id',    # 対象レコードID
    'client_name',  # 取引先名（検索用）
    'issue_date',   # 発行日（検索用）
    'amount',       # 金額（検索用）
    'doc_type',     # 書類種別（検索用）
    'changes_json', # 変更内容（JSON）
]

_TRACKED_FIELDS = [
    'issue_date', 'amount', 'client_name', 'memo',
    'category', 'doc_type', 'file_path', 'doc_id',
]


class AuditLogger:
    def __init__(self, root_path: str):
        self.root_path = root_path

    def _log_path(self) -> str:
        return os.path.join(self.root_path, 'audit_log.csv')

    def _append(self, row: dict) -> None:
        try:
            log_path = self._log_path()
            lock_path = log_path + '.lock'
            with FileLock(lock_path, timeout=10):
                df_new = pd.DataFrame([{c: row.get(c, '') for c in AUDIT_COLUMNS}])
                if os.path.exists(log_path):
                    df_new.to_csv(log_path, mode='a', header=False,
                                  index=False, encoding='utf-8-sig')
                else:
                    df_new.to_csv(log_path, mode='w', header=True,
                                  index=False, encoding='utf-8-sig')
        except Exception as e:
            logger.warning(f"監査ログの書き込みに失敗しました: {e}")

    def log_create(self, year_nendo: str, record_id: str, data: dict) -> None:
        self._append({
            'log_id': str(uuid.uuid4()),
            'logged_at': datetime.now().isoformat(),
            'operation': 'CREATE',
            'year_nendo': year_nendo,
            'record_id': str(record_id),
            'client_name': data.get('client_name', ''),
            'issue_date': data.get('issue_date', ''),
            'amount': data.get('amount', ''),
            'doc_type': data.get('doc_type', ''),
            'changes_json': json.dumps({'new': {k: str(v) for k, v in data.items()}},
                                       ensure_ascii=False),
        })

    def log_update(self, year_nendo: str, record_id: str,
                   old_data: dict, new_data: dict) -> None:
        changes = {}
        for field in _TRACKED_FIELDS:
            old_val = str(old_data.get(field, ''))
            new_val = str(new_data.get(field, ''))
            if old_val != new_val:
                changes[field] = {'old': old_val, 'new': new_val}

        self._append({
            'log_id': str(uuid.uuid4()),
            'logged_at': datetime.now().isoformat(),
            'operation': 'UPDATE',
            'year_nendo': year_nendo,
            'record_id': str(record_id),
            'client_name': old_data.get('client_name', ''),
            'issue_date': old_data.get('issue_date', ''),
            'amount': old_data.get('amount', ''),
            'doc_type': old_data.get('doc_type', ''),
            'changes_json': json.dumps(changes, ensure_ascii=False),
        })

    def log_delete(self, year_nendo: str, record_id: str, data: dict) -> None:
        self._append({
            'log_id': str(uuid.uuid4()),
            'logged_at': datetime.now().isoformat(),
            'operation': 'DELETE',
            'year_nendo': year_nendo,
            'record_id': str(record_id),
            'client_name': data.get('client_name', ''),
            'issue_date': data.get('issue_date', ''),
            'amount': data.get('amount', ''),
            'doc_type': data.get('doc_type', ''),
            'changes_json': json.dumps(
                {'deleted': {k: str(v) for k, v in data.items()}},
                ensure_ascii=False
            ),
        })
