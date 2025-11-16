class NookException(Exception):
    """Nookアプリケーションの基底例外クラス"""

    pass


class ServiceException(NookException):
    """サービス関連の例外"""

    pass


class APIException(ServiceException):
    """外部API関連の例外"""

    def __init__(self, message: str, status_code: int = None, response_body: str = None):
        super().__init__(message)
        self.status_code = status_code
        self.response_body = response_body


class ConfigurationException(NookException):
    """設定関連の例外"""

    pass


class DataException(NookException):
    """データ処理関連の例外"""

    pass


class RetryException(ServiceException):
    """リトライ失敗の例外"""

    pass
