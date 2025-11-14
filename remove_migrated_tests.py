#!/usr/bin/env python3
"""
test_zenn_explorer.pyから移行済みの15テストを削除
"""

import re

# 移行済みのテスト名
MIGRATED_TESTS = [
    "test_collect_success_with_valid_feed",
    "test_collect_with_multiple_articles",
    "test_collect_with_target_dates_none",
    "test_collect_network_error",
    "test_collect_invalid_feed_xml",
    "test_collect_http_client_timeout",
    "test_collect_gpt_api_error",
    "test_collect_with_limit_zero",
    "test_collect_with_limit_one",
    "test_full_workflow_collect_and_save",
    "test_collect_with_multiple_categories",
    "test_collect_feedparser_attribute_error",
    "test_collect_with_duplicate_article",
    "test_collect_with_empty_feed_entries",
    "test_collect_continues_on_individual_feed_error",
]


def remove_tests(file_path):
    """テストファイルから移行済みテストを削除"""
    with open(file_path, 'r') as f:
        lines = f.readlines()

    result_lines = []
    i = 0
    removed_count = 0

    while i < len(lines):
        line = lines[i]

        # テスト関数の開始を検出
        match = re.match(r'^async def (test_\w+)\(', line)
        if match:
            test_name = match.group(1)

            if test_name in MIGRATED_TESTS:
                # このテストを削除: デコレータから次のテストまたはセクション区切りまで

                # デコレータの開始位置を探す（最大3行前まで）
                decorator_start = i
                for j in range(i - 1, max(i - 4, -1), -1):
                    if lines[j].strip().startswith('@pytest.mark.'):
                        decorator_start = j
                    else:
                        break

                # テスト本体の終了位置を探す
                # 次の関数定義、クラス定義、またはセクション区切りまで
                test_end = i + 1
                for j in range(i + 1, len(lines)):
                    stripped = lines[j].strip()

                    # 次のテスト、クラス、またはセクション区切りを検出
                    if (stripped.startswith('def ') or
                        stripped.startswith('class ') or
                        stripped.startswith('# ====') or
                        (stripped.startswith('@') and 'pytest.mark' in stripped)):
                        test_end = j
                        break

                    # ファイル末尾まで到達
                    if j == len(lines) - 1:
                        test_end = len(lines)
                        break

                # 削除範囲をスキップ
                i = test_end
                removed_count += 1
                print(f"  ✓ {test_name} 削除 (L{decorator_start+1}-L{test_end})")
                continue

        # このラインを保持
        result_lines.append(line)
        i += 1

    # ファイルに書き戻し
    with open(file_path, 'w') as f:
        f.writelines(result_lines)

    original_lines = len(lines)
    new_lines = len(result_lines)
    deleted_lines = original_lines - new_lines

    print(f"\n✓ 完了")
    print(f"  - 削除テスト数: {removed_count}")
    print(f"  - 削除行数: {deleted_lines}行")
    print(f"  - 元: {original_lines}行 → 新: {new_lines}行")


if __name__ == "__main__":
    file_path = "tests/services/test_zenn_explorer.py"
    print(f"移行済みテストを削除中: {file_path}\n")
    remove_tests(file_path)
