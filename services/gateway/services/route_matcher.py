"""
ルートマッチングサービス

routing.ymlを読み込み、リクエストパス/メソッドからターゲットコンテナを特定します。

Note:
    FastAPIの APIRouter とは異なる機能を提供します。
    このモジュールは設定ファイルベースのルーティングマッチングロジックです。
"""

import re
from typing import Optional, Tuple, Dict, Any, List
import yaml
import logging

from ..config import config

logger = logging.getLogger(__name__)


class RouteMatcher:
    def __init__(self, function_registry: Any):
        """
        Args:
            function_registry: FunctionRegistry instance
        """
        self.function_registry = function_registry
        self.config_path = config.ROUTING_CONFIG_PATH
        self._routing_config: List[Dict[str, Any]] = []

    def load_routing_config(self) -> List[Dict[str, Any]]:
        """
        routing.ymlを読み込んでキャッシュ
        """
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                cfg = yaml.safe_load(f)
                self._routing_config = cfg.get("routes", [])
                logger.info(f"Loaded {len(self._routing_config)} routes from {self.config_path}")
        except FileNotFoundError:
            logger.warning(f"Warning: Routing config not found at {self.config_path}")
            self._routing_config = []
        except yaml.YAMLError as e:
            logger.error(f"Error parsing routing config: {e}")
            self._routing_config = []

        return self._routing_config

    def _path_to_regex(self, path_pattern: str) -> str:
        """
        パスパターンを正規表現に変換

        例: "/users/{user_id}/posts/{post_id}"
            → "^/users/(?P<user_id>[^/]+)/posts/(?P<post_id>[^/]+)$"
        """
        # {param} を名前付きキャプチャグループに置換
        regex_pattern = re.sub(r"\{(\w+)\}", r"(?P<\1>[^/]+)", path_pattern)
        return f"^{regex_pattern}$"

    def match_route(
        self, request_path: str, request_method: str
    ) -> Tuple[Optional[str], Dict[str, str], Optional[str], Dict[str, Any]]:
        """
        リクエストパスとメソッドからターゲットコンテナを特定

        Args:
            request_path: リクエストパス (例: "/api/users/123")
            request_method: HTTPメソッド (例: "POST")

        Returns:
            Tuple of:
                - target_container: コンテナ名 (見つからない場合はNone)
                - path_params: パスパラメータの辞書
                - route_path: マッチしたルートのパスパターン (resource用)
                - function_config: function設定（image, environment等）
        """
        if not self._routing_config:
            self.load_routing_config()

        for route in self._routing_config:
            route_path = route.get("path", "")
            route_method = route.get("method", "").upper()

            # メソッドが一致するか確認
            if request_method.upper() != route_method:
                continue

            # パスパターンを正規表現に変換してマッチング
            regex_pattern = self._path_to_regex(route_path)
            match = re.match(regex_pattern, request_path)

            if match:
                # パスパラメータを抽出
                path_params = match.groupdict()

                # function 設定を取得（新形式: 文字列、旧形式: 辞書）
                function_ref = route.get("function", {})

                if isinstance(function_ref, str):
                    # 新形式: function_registry から設定を取得
                    target_container = function_ref
                    function_config = self.function_registry.get_function_config(function_ref) or {}
                else:
                    # 旧形式（後方互換）: 辞書から直接取得
                    target_container = function_ref.get("container", "")
                    function_config = function_ref

                return target_container, path_params, route_path, function_config

        # マッチするルートが見つからない
        return None, {}, None, {}
