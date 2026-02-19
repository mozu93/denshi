import pandas as pd
import os
import logging

logger = logging.getLogger(__name__)


class CsvRepository:
    COLUMNS = [
        'id', 'doc_id', 'category', 'doc_type', 'issue_date',
        'client_name', 'amount', 'memo', 'file_path', 'file_hash',
        'created_at', 'updated_at'
    ]

    def load(self, csv_path: str) -> pd.DataFrame:
        logger.debug(f"load - csv_path: {csv_path}")
        if not csv_path or not os.path.exists(csv_path):
            logger.debug(f"load - CSVファイルが存在しません: {csv_path}")
            return pd.DataFrame(columns=self.COLUMNS)

        try:
            dtype_map = {col: str for col in self.COLUMNS}
            df = pd.read_csv(csv_path, dtype=dtype_map)
            logger.debug(f"load - CSVを読み込み成功: {len(df)} 行")

            required_columns = [
                'id', 'doc_id', 'category', 'doc_type', 'issue_date',
                'client_name', 'amount', 'memo', 'file_path'
            ]
            missing_required = [col for col in required_columns if col not in df.columns]
            if missing_required:
                logger.warning(
                    f"CSVファイル '{csv_path}' に必須カラム {missing_required} が不足しています。"
                    "空のデータフレームを返します。"
                )
                return pd.DataFrame(columns=self.COLUMNS)

            if 'file_hash' not in df.columns:
                df['file_hash'] = ''
                logger.debug("file_hashカラムが存在しないため、空文字で追加しました。")

            for col in self.COLUMNS:
                if col not in df.columns:
                    df[col] = ''
            return df

        except (pd.errors.ParserError, Exception) as e:
            logger.error(f"CSVファイル '{csv_path}' の読み込みに失敗しました: {e}")
            return pd.DataFrame(columns=self.COLUMNS)

    def save(self, csv_path: str, df: pd.DataFrame):
        if not csv_path:
            raise ValueError(f"無効なCSVパスです: {csv_path}")

        try:
            os.makedirs(os.path.dirname(csv_path), exist_ok=True)
            df.to_csv(csv_path, index=False, encoding='utf-8-sig')
        except (IOError, OSError) as e:
            logger.error(f"CSVファイル '{csv_path}' の保存に失敗しました: {e}")
            raise RuntimeError(
                f"インデックスファイルの保存に失敗しました。権限などを確認してください。: {e}"
            )
