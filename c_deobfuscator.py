#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
C言語ソースコードの識別子を変換表に基づいて元に戻すプログラム（改良版）
関数名内の文字列も含めて完全に復元
"""

import re
import sys
from collections import defaultdict


class CDeobfuscator:
    def __init__(self, obfuscated_code, conversion_table_file):
        self.obfuscated_code = obfuscated_code
        self.conversion_map = {}  # new_name -> old_name のマッピング
        self.prefix = "Ut"  # デフォルトプレフィックス
        self.parse_conversion_table(conversion_table_file)
    
    def parse_conversion_table(self, table_file):
        """変換表ファイルを読み込んで逆マッピングを作成"""
        try:
            with open(table_file, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            print(f"エラー: 変換表ファイル '{table_file}' を読み込めません: {e}")
            sys.exit(1)
        
        # プレフィックスを検出
        prefix_match = re.search(r'プレフィックス:\s*(\w+)', content)
        if prefix_match:
            self.prefix = prefix_match.group(1)
            print(f"検出されたプレフィックス: {self.prefix}")
        
        # 変換表から識別子のマッピングを抽出
        # 形式: "  old_name                       -> new_name"
        pattern = r'^\s+(.+?)\s+->\s+(' + re.escape(self.prefix) + r'[A-Za-z0-9_]+)\s*$'
        
        for line in content.split('\n'):
            match = re.match(pattern, line)
            if match:
                old_name = match.group(1).strip()
                new_name = match.group(2)
                # 逆マッピング: 新しい名前 -> 元の名前
                self.conversion_map[new_name] = old_name
        
        if not self.conversion_map:
            print("警告: 変換表から識別子のマッピングが見つかりませんでした")
        else:
            print(f"変換表を読み込みました: {len(self.conversion_map)} 件の識別子")
    
    def deobfuscate(self):
        """逆変換を実行（関数名内の部分文字列も含めて変換）"""
        result_code = self.obfuscated_code
        
        # 長い名前から順に変換（部分一致を避けるため）
        sorted_names = sorted(self.conversion_map.keys(), 
                            key=lambda x: (len(x), x), 
                            reverse=True)
        
        # コメント識別子と通常の識別子を分離
        comment_ids = []
        normal_ids = []
        
        for new_name in sorted_names:
            # Utc1, Utc2, Utc3... はコメント識別子
            if new_name.startswith(f"{self.prefix}c") and len(new_name) > len(self.prefix) + 1:
                if new_name[len(self.prefix)+1:].isdigit():
                    comment_ids.append(new_name)
                else:
                    normal_ids.append(new_name)
            else:
                normal_ids.append(new_name)
        
        # まず通常の識別子を変換（関数名内の部分文字列も含む）
        for new_name in normal_ids:
            old_name = self.conversion_map[new_name]
            
            # 方法1: 単語境界での完全一致（通常の識別子）
            result_code = re.sub(r'\b' + re.escape(new_name) + r'\b', 
                               old_name, result_code)
            
            # 方法2: 関数名やマクロ名内の部分文字列も変換
            # 例: my_Utf1_function のような場合
            # ただし、プレフィックスを含む場合のみ（誤変換を防ぐため）
            if self.prefix in new_name:
                # アンダースコアで囲まれた部分
                result_code = re.sub(r'_' + re.escape(new_name) + r'_', 
                                   f'_{old_name}_', result_code)
                # アンダースコアで始まる部分
                result_code = re.sub(r'_' + re.escape(new_name) + r'\b', 
                                   f'_{old_name}', result_code)
                # アンダースコアで終わる部分
                result_code = re.sub(r'\b' + re.escape(new_name) + r'_', 
                                   f'{old_name}_', result_code)
        
        # 次にコメント識別子を変換（特別処理）
        for new_name in comment_ids:
            old_name = self.conversion_map[new_name]
            
            # 単一行コメント: // Utc1 または // Utc15
            result_code = re.sub(
                r'//\s*' + re.escape(new_name) + r'(?=\s*$|\s*\n)',
                f'// {old_name}',
                result_code,
                flags=re.MULTILINE
            )
            
            # 複数行コメント: /* Utc1 */ または /* Utc35 */
            result_code = re.sub(
                r'/\*\s*' + re.escape(new_name) + r'\s*\*/',
                f'/* {old_name} */',
                result_code
            )
        
        return result_code
    
    def generate_summary(self):
        """変換サマリーを生成"""
        summary = []
        summary.append("=" * 60)
        summary.append(f"逆変換サマリー (プレフィックス: {self.prefix})")
        summary.append("=" * 60)
        
        # カテゴリ別に分類
        categories = {
            'マクロ名': [],
            '列挙型名': [],
            '構造体名': [],
            '共用体名': [],
            '関数名': [],
            '変数名': [],
            'メンバ名': [],
            'コメント': []
        }
        
        for new_name, old_name in sorted(self.conversion_map.items()):
            if new_name.startswith(f"{self.prefix}D"):
                categories['マクロ名'].append((new_name, old_name))
            elif new_name.startswith(f"{self.prefix}e") and new_name[len(self.prefix)+1:].isdigit():
                categories['列挙型名'].append((new_name, old_name))
            elif new_name.startswith(f"{self.prefix}t"):
                categories['構造体名'].append((new_name, old_name))
            elif new_name.startswith(f"{self.prefix}u"):
                categories['共用体名'].append((new_name, old_name))
            elif new_name.startswith(f"{self.prefix}f"):
                categories['関数名'].append((new_name, old_name))
            elif new_name.startswith(f"{self.prefix}v"):
                categories['変数名'].append((new_name, old_name))
            elif new_name.startswith(f"{self.prefix}c") and new_name[len(self.prefix)+1:].isdigit():
                categories['コメント'].append((new_name, old_name))
            elif new_name.startswith(f"{self.prefix}m"):
                categories['メンバ名'].append((new_name, old_name))
        
        for category_name, items in categories.items():
            if items:
                summary.append(f"\n【{category_name}】")
                for new_name, old_name in items:
                    summary.append(f"  {new_name:30s} -> {old_name}")
        
        summary.append(f"\n合計: {len(self.conversion_map)} 件の識別子を復元")
        summary.append("=" * 60)
        
        return "\n".join(summary)


def main():
    """メイン関数"""
    if len(sys.argv) < 2:
        print("使用方法:")
        print("  python c_deobfuscator_improved.py <難読化されたファイル> [変換表ファイル]")
        print("")
        print("例:")
        print("  python c_deobfuscator_improved.py your_code_obfuscated.c")
        print("  python c_deobfuscator_improved.py your_code_obfuscated.c your_code_conversion_table.txt")
        print("")
        print("※ 変換表ファイルを指定しない場合、自動的に推測されます")
        print("※ プレフィックス付きの識別子を完全に復元します（関数名内の部分文字列も含む）")
        sys.exit(1)
    
    obfuscated_file = sys.argv[1]
    
    # 変換表ファイルの決定
    if len(sys.argv) >= 3:
        table_file = sys.argv[2]
    else:
        # 自動推測: ファイル名から _obfuscated.c を削除して _conversion_table.txt を追加
        if obfuscated_file.endswith('_obfuscated.c'):
            base_name = obfuscated_file.replace('_obfuscated.c', '')
            table_file = base_name + '_conversion_table.txt'
        else:
            # 拡張子を .txt に変更
            base_name = obfuscated_file.rsplit('.', 1)[0]
            table_file = base_name + '_conversion_table.txt'
        
        print(f"変換表ファイルを自動推測: {table_file}")
    
    # ファイルを読み込み
    try:
        with open(obfuscated_file, 'r', encoding='utf-8') as f:
            obfuscated_code = f.read()
        print(f"入力ファイル: {obfuscated_file}")
    except Exception as e:
        print(f"エラー: ファイル '{obfuscated_file}' を読み込めません: {e}")
        sys.exit(1)
    
    # 逆変換を実行
    deobfuscator = CDeobfuscator(obfuscated_code, table_file)
    restored_code = deobfuscator.deobfuscate()
    summary = deobfuscator.generate_summary()
    
    # 結果を出力
    print("\n" + summary)
    print("\n" + "=" * 60)
    print("復元されたコード（プレビュー）")
    print("=" * 60)
    # 最初の30行だけ表示
    lines = restored_code.split('\n')
    for i, line in enumerate(lines[:30]):
        print(line)
    if len(lines) > 30:
        print(f"... (残り {len(lines) - 30} 行)")
    
    # ファイルに保存
    if obfuscated_file.endswith('_obfuscated.c'):
        output_filename = obfuscated_file.replace('_obfuscated.c', '_restored.c')
    else:
        output_filename = obfuscated_file.rsplit('.', 1)[0] + '_restored.c'
    
    with open(output_filename, 'w', encoding='utf-8') as f:
        f.write(restored_code)
    
    print(f"\n復元されたコードを '{output_filename}' に保存しました")


if __name__ == "__main__":
    main()
