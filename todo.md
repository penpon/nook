# TODO
- [ ] Pydantic v2 ConfigDict への移行
  - 対象: `nook/api/models/errors.py` の `ErrorResponse`（class Config で警告、DeprecatedSince20）
  - 対応案: `model_config = ConfigDict(...)` に置き換え
  - 備考: 現在はテスト実行で警告のみ。将来的に実装側で対応する
