#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
C言語ソースコードの識別子を変換表に基づいて元に戻すプログラム
"""

import re
import sys
from collections import defaultdict


class CDeobfuscator:
    def __init__(self, obfuscated_code, conversion_table_file):
        self.obfuscated_code = obfuscated_code
        self.conversion_map = {}  # new_name -> old_name のマッピング
        self.parse_conversion_table(conversion_table_file)
    
    def parse_conversion_table(self, table_file):
        """変換表ファイルを読み込んで逆マッピングを作成"""
        try:
            with open(table_file, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            print(f"エラー: 変換表ファイル '{table_file}' を読み込めません: {e}")
            sys.exit(1)
        
        # 変換表から識別子のマッピングを抽出
        # 形式: "  old_name                       -> new_name"
        pattern = r'^\s+([A-Za-z_][A-Za-z0-9_]*)\s+->\s+([A-Za-z0-9_]+)\s*$'
        
        for line in content.split('\n'):
            match = re.match(pattern, line)
            if match:
                old_name = match.group(1)
                new_name = match.group(2)
                # 逆マッピング: 新しい名前 -> 元の名前
                self.conversion_map[new_name] = old_name
        
        if not self.conversion_map:
            print("警告: 変換表から識別子のマッピングが見つかりませんでした")
        else:
            print(f"変換表を読み込みました: {len(self.conversion_map)} 件の識別子")
    
    def deobfuscate(self):
        """逆変換を実行"""
        result_code = self.obfuscated_code
        
        # 長い名前から順に変換（部分一致を避けるため）
        # 例: m10 と m1 がある場合、m10 を先に変換する
        sorted_names = sorted(self.conversion_map.keys(), 
                            key=lambda x: (len(x), x), 
                            reverse=True)
        
        for new_name in sorted_names:
            old_name = self.conversion_map[new_name]
            # 単語境界を使用して正確に置換
            result_code = re.sub(r'\b' + re.escape(new_name) + r'\b', 
                               old_name, result_code)
        
        return result_code
    
    def generate_summary(self):
        """変換サマリーを生成"""
        summary = []
        summary.append("=" * 60)
        summary.append("逆変換サマリー")
        summary.append("=" * 60)
        
        # カテゴリ別に分類
        categories = {
            'マクロ名': [],
            '列挙型名': [],
            '構造体名': [],
            '共用体名': [],
            '関数名': [],
            '変数名': [],
            'メンバ名': []
        }
        
        for new_name, old_name in sorted(self.conversion_map.items()):
            if new_name.startswith('D'):
                categories['マクロ名'].append((new_name, old_name))
            elif new_name.startswith('e') and not new_name.startswith('ex'):
                categories['列挙型名'].append((new_name, old_name))
            elif new_name.startswith('t'):
                categories['構造体名'].append((new_name, old_name))
            elif new_name.startswith('u'):
                categories['共用体名'].append((new_name, old_name))
            elif new_name.startswith('f'):
                categories['関数名'].append((new_name, old_name))
            elif new_name.startswith('v'):
                categories['変数名'].append((new_name, old_name))
            elif new_name.startswith('m'):
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
        print("  python c_deobfuscator.py <難読化されたファイル> [変換表ファイル]")
        print("")
        print("例:")
        print("  python c_deobfuscator.py your_code_obfuscated.c")
        print("  python c_deobfuscator.py your_code_obfuscated.c your_code_conversion_table.txt")
        print("")
        print("※ 変換表ファイルを指定しない場合、自動的に推測されます")
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
    print("復元されたコード")
    print("=" * 60)
    print(restored_code)
    
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
