import logging
import jaconv

class ClientManager:
    """取引先管理クラス

    機能:
    - 取引先名とフリガナの管理
    - 50音順ソート
    - 設定ファイルとの連携
    """

    def __init__(self, config_manager):
        self.config_manager = config_manager
        self.logger = logging.getLogger(__name__)

    def add_client(self, name, furigana):
        """取引先を追加"""
        try:
            # フリガナをカタカナに変換
            furigana_katakana = jaconv.hira2kata(furigana)

            # 重複チェック
            if self.is_duplicate(name, furigana_katakana):
                self.logger.warning(f"重複する取引先: {name} ({furigana_katakana})")
                return False

            # 新しいクライアントIDを生成
            client_id = self._generate_client_id()

            # 名前|フリガナ形式で保存
            client_data = f"{name}|{furigana_katakana}"
            self.config_manager.set('ClientNames', client_id, client_data)

            self.logger.info(f"取引先を追加: {name} ({furigana_katakana})")
            return True

        except Exception as e:
            self.logger.error(f"取引先の追加に失敗: {e}")
            return False

    def get_all_clients(self):
        """全ての取引先を50音順で取得"""
        try:
            clients_section = self.config_manager.get_section('ClientNames')
            clients = []

            for client_id, client_data in clients_section.items():
                try:
                    name, furigana = client_data.split('|', 1)
                    clients.append({
                        'id': client_id,
                        'name': name,
                        'furigana': furigana
                    })
                except ValueError:
                    # 旧形式データの場合はそのまま名前として扱う
                    clients.append({
                        'id': client_id,
                        'name': client_data,
                        'furigana': client_data
                    })

            # 50音順でソート
            clients.sort(key=lambda x: x['furigana'])
            return clients

        except Exception as e:
            self.logger.error(f"取引先一覧の取得に失敗: {e}")
            return []

    def get_client_names_list(self):
        """取引先名のリストを50音順で取得"""
        clients = self.get_all_clients()
        return [client['name'] for client in clients]

    def delete_client(self, client_id):
        """取引先を削除"""
        try:
            clients_section = self.config_manager.get_section('ClientNames')
            if client_id in clients_section:
                # 設定ファイルから削除するため、セクション全体を再構築
                new_clients = {k: v for k, v in clients_section.items() if k != client_id}
                self.config_manager.set_section('ClientNames', new_clients)
                self.logger.info(f"取引先を削除: {client_id}")
                return True
            return False

        except Exception as e:
            self.logger.error(f"取引先の削除に失敗: {e}")
            return False

    def update_client(self, client_id, name, furigana):
        """取引先を更新"""
        try:
            # フリガナをカタカナに変換
            furigana_katakana = jaconv.hira2kata(furigana)

            # 重複チェック（自分以外との重複をチェック）
            if self.is_duplicate(name, furigana_katakana, exclude_id=client_id):
                self.logger.warning(f"重複する取引先: {name} ({furigana_katakana})")
                return False

            # 名前|フリガナ形式で更新
            client_data = f"{name}|{furigana_katakana}"
            self.config_manager.set('ClientNames', client_id, client_data)

            self.logger.info(f"取引先を更新: {name} ({furigana_katakana})")
            return True

        except Exception as e:
            self.logger.error(f"取引先の更新に失敗: {e}")
            return False

    def _generate_client_id(self):
        """新しいクライアントIDを生成"""
        try:
            clients_section = self.config_manager.get_section('ClientNames')

            # 既存のIDから最大値を取得
            max_id = 0
            for client_id in clients_section.keys():
                if client_id.startswith('client_'):
                    try:
                        id_num = int(client_id.split('_')[1])
                        max_id = max(max_id, id_num)
                    except (IndexError, ValueError):
                        continue

            # 新しいIDを生成
            return f"client_{max_id + 1:03d}"

        except Exception:
            return "client_001"

    def search_clients(self, query):
        """取引先を検索（名前またはフリガナで部分一致）"""
        try:
            all_clients = self.get_all_clients()
            query_lower = query.lower()

            results = []
            for client in all_clients:
                if (query_lower in client['name'].lower() or
                    query_lower in client['furigana'].lower()):
                    results.append(client)

            return results

        except Exception as e:
            self.logger.error(f"取引先の検索に失敗: {e}")
            return []

    def is_duplicate(self, name, furigana, exclude_id=None):
        """取引先名またはフリガナの重複チェック"""
        try:
            all_clients = self.get_all_clients()

            for client in all_clients:
                # 除外IDが指定されている場合はスキップ
                if exclude_id and client['id'] == exclude_id:
                    continue

                # 名前またはフリガナが重複している場合
                if (client['name'].lower() == name.lower() or
                    client['furigana'].lower() == furigana.lower()):
                    return True

            return False

        except Exception as e:
            self.logger.error(f"重複チェックでエラー: {e}")
            return True  # エラーの場合は安全側に倒して重複として扱う

    def check_duplicate_details(self, name, furigana, exclude_id=None):
        """重複チェックの詳細情報を返す"""
        try:
            import jaconv
            all_clients = self.get_all_clients()

            duplicate_name = False
            duplicate_furigana = False

            for client in all_clients:
                # 除外IDが指定されている場合はスキップ
                if exclude_id and client['id'] == exclude_id:
                    continue

                # 名前の重複をチェック
                if client['name'].lower() == name.lower():
                    duplicate_name = True

                # フリガナの重複をチェック（空でない場合のみ）
                if furigana.strip():
                    furigana_katakana = jaconv.hira2kata(furigana)
                    if client['furigana'].lower() == furigana_katakana.lower():
                        duplicate_furigana = True

            return duplicate_name, duplicate_furigana

        except Exception as e:
            self.logger.error(f"重複詳細チェックでエラー: {e}")
            return True, True  # エラーの場合は安全側に倒す