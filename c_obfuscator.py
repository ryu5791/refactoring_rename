#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
C言語ソースコードの識別子を系統的に変換するプログラム
"""

import re
import sys
from collections import defaultdict

# サンプルC言語コード（共用体とビットフィールド、列挙型を含む）
SAMPLE_C_CODE = """
#define MAX_SIZE 100
#define PI 3.14159
#define CALCULATE(x, y) ((x) + (y))

// 列挙型定義
enum Color {
    RED,
    GREEN,
    BLUE,
    YELLOW
};

enum Status {
    STATUS_IDLE = 0,
    STATUS_RUNNING = 1,
    STATUS_PAUSED = 2,
    STATUS_STOPPED = 3
};

// 構造体定義
struct Point {
    int x_coord;
    int y_coord;
    char label[20];
    enum Color point_color;
};

// 共用体定義（ビットフィールド付き）
/* ステータスレジスタ共用体 */
union StatusRegister {
    unsigned int raw_value;
    struct {
        unsigned int enabled : 1;  // 有効フラグ
        unsigned int ready : 1;    // 準備完了フラグ
        unsigned int error : 1;    // エラーフラグ
        unsigned int mode : 3;     // モード設定
        unsigned int priority : 2; // 優先度
        unsigned int reserved : 24;
    } bits;
};

// グローバル変数
int global_counter = 0;
struct Point origin = {0, 0, "Origin", RED};
enum Status current_status = STATUS_IDLE;

// 関数宣言
int calculate_distance(struct Point p1, struct Point p2);
void initialize_status(union StatusRegister *reg);
void process_command(int command);

// 関数定義
int calculate_distance(struct Point p1, struct Point p2) {
    // X座標の差分を計算
    int dx = p1.x_coord - p2.x_coord;
    // Y座標の差分を計算
    int dy = p1.y_coord - p2.y_coord;
    /* 距離の二乗を返す */
    return dx * dx + dy * dy;
}

void initialize_status(union StatusRegister *reg) {
    reg->raw_value = 0;
    reg->bits.enabled = 1;
    reg->bits.ready = 0;
    reg->bits.mode = 2;
}

void process_command(int command) {
    // コマンドを処理する
    switch (command) {
        case 0:
            printf("Idle\n");  // アイドル状態
            break;
        case 1:
            printf("Active\n");  // アクティブ状態
            break;
        default:
            printf("Unknown\n");  // 未知のコマンド
            break;
    }
}

int main(void) {
    // ポイントの初期化
    struct Point point1 = {10, 20, "P1", BLUE};
    struct Point point2 = {30, 40, "P2", GREEN};
    union StatusRegister status;
    enum Status sys_status = STATUS_RUNNING;
    
    // 距離を計算
    int distance = calculate_distance(point1, point2);
    initialize_status(&status);
    
    /* コマンド処理を実行 */
    process_command(1);
    
    // カウンタを更新
    global_counter++;
    current_status = STATUS_RUNNING;
    
    // ステータスチェック
    if (sys_status == STATUS_RUNNING) {
        global_counter += 10;
    }
    
    return 0;  // 正常終了
}
"""


class CObfuscator:
    def __init__(self, source_code):
        self.source_code = source_code
        self.identifiers = {
            'macro': {},      # D1, D2, ...
            'enum': {},       # e1, e2, ...
            'struct': {},     # t1, t2, ...
            'union': {},      # u1, u2, ...
            'function': {},   # f1, f2, ...
            'variable': {},   # v1, v2, ...
            'member': {},     # m1, m2, ...
            'comment': {}     # c1, c2, ...
        }
        self.counters = {
            'macro': 1,
            'enum': 1,
            'struct': 1,
            'union': 1,
            'function': 1,
            'variable': 1,
            'member': 1,
            'comment': 1
        }
        self.used_identifiers = set()
        
        # C言語の予約語リスト
        self.c_keywords = {
            # 型
            'int', 'char', 'short', 'long', 'float', 'double', 'void',
            'signed', 'unsigned',
            # 制御構文
            'if', 'else', 'switch', 'case', 'default', 'break', 'continue',
            'for', 'while', 'do', 'goto', 'return',
            # 記憶クラス
            'auto', 'register', 'static', 'extern', 'typedef',
            # 修飾子
            'const', 'volatile', 'restrict',
            # その他
            'struct', 'union', 'enum', 'sizeof', 'inline',
            # C99以降
            '_Bool', '_Complex', '_Imaginary',
            # C11以降
            '_Alignas', '_Alignof', '_Atomic', '_Static_assert',
            '_Noreturn', '_Thread_local', '_Generic',
            # 標準ライブラリ関数（よく使われるもの）
            'printf', 'scanf', 'malloc', 'free', 'memcpy', 'memset',
            'strlen', 'strcpy', 'strcmp', 'strcat', 'sprintf', 'snprintf',
            'fopen', 'fclose', 'fread', 'fwrite', 'fprintf', 'fscanf',
            'exit', 'NULL'
        }
        
    def remove_comments_and_strings(self, code):
        """コメントと文字列リテラルを一時的に除去し、コメントを変換"""
        # コメントと文字列を保護するための辞書
        self.protected = {}
        counter = 0
        
        def replace_string_with_placeholder(match):
            nonlocal counter
            placeholder = f"__PROTECTED_STR_{counter}__"
            self.protected[placeholder] = match.group(0)
            counter += 1
            return placeholder
        
        def replace_comment_with_placeholder(match):
            nonlocal counter
            original_comment = match.group(0)
            
            # コメントの種類を判定
            if original_comment.startswith('//'):
                # 単一行コメント
                comment_prefix = '//'
                comment_content = original_comment[2:].strip()
            else:
                # 複数行コメント
                comment_prefix = '/*'
                comment_suffix = '*/'
                comment_content = original_comment[2:-2].strip()
            
            # コメント内容を変換マップに追加
            if comment_content:
                comment_id = f"c{self.counters['comment']}"
                self.identifiers['comment'][comment_content] = comment_id
                self.counters['comment'] += 1
                
                # 変換後のコメントを作成
                if original_comment.startswith('//'):
                    transformed_comment = f"// {comment_id}"
                else:
                    transformed_comment = f"/* {comment_id} */"
            else:
                # 空のコメントはそのまま
                transformed_comment = original_comment
            
            placeholder = f"__PROTECTED_COMMENT_{counter}__"
            self.protected[placeholder] = transformed_comment
            counter += 1
            return placeholder
        
        # 文字列リテラルを保護
        code = re.sub(r'"(?:[^"\\]|\\.)*"', replace_string_with_placeholder, code)
        code = re.sub(r"'(?:[^'\\]|\\.)*'", replace_string_with_placeholder, code)
        
        # コメントを変換して保護
        code = re.sub(r'//[^\n]*', replace_comment_with_placeholder, code)
        code = re.sub(r'/\*.*?\*/', replace_comment_with_placeholder, code, flags=re.DOTALL)
        
        return code
    
    def restore_protected(self, code):
        """保護された文字列とコメントを復元"""
        for placeholder, original in self.protected.items():
            code = code.replace(placeholder, original)
        return code
    
    def is_reserved_word(self, name):
        """予約語かどうかをチェック"""
        return name in self.c_keywords
    
    def extract_identifiers(self, code):
        """識別子を抽出して分類"""
        # マクロ定義を抽出
        for match in re.finditer(r'#define\s+([A-Za-z_][A-Za-z0-9_]*)', code):
            name = match.group(1)
            if name not in self.identifiers['macro'] and not self.is_reserved_word(name):
                self.identifiers['macro'][name] = f"D{self.counters['macro']}"
                self.counters['macro'] += 1
                self.used_identifiers.add(name)
        
        # 列挙型定義を抽出
        for match in re.finditer(r'enum\s+([A-Za-z_][A-Za-z0-9_]*)\s*\{', code):
            name = match.group(1)
            if name not in self.identifiers['enum'] and not self.is_reserved_word(name):
                self.identifiers['enum'][name] = f"e{self.counters['enum']}"
                self.counters['enum'] += 1
                self.used_identifiers.add(name)
        
        # 構造体定義を抽出
        for match in re.finditer(r'struct\s+([A-Za-z_][A-Za-z0-9_]*)\s*\{', code):
            name = match.group(1)
            if name not in self.identifiers['struct'] and not self.is_reserved_word(name):
                self.identifiers['struct'][name] = f"t{self.counters['struct']}"
                self.counters['struct'] += 1
                self.used_identifiers.add(name)
        
        # 共用体定義を抽出
        for match in re.finditer(r'union\s+([A-Za-z_][A-Za-z0-9_]*)\s*\{', code):
            name = match.group(1)
            if name not in self.identifiers['union'] and not self.is_reserved_word(name):
                self.identifiers['union'][name] = f"u{self.counters['union']}"
                self.counters['union'] += 1
                self.used_identifiers.add(name)
        
        # メンバ名を抽出（構造体・共用体内）
        struct_union_blocks = re.finditer(
            r'(?:struct|union)\s+[A-Za-z_][A-Za-z0-9_]*\s*\{([^}]+)\}',
            code, re.DOTALL
        )
        for block_match in struct_union_blocks:
            block = block_match.group(1)
            # メンバ変数を抽出（ビットフィールドにも対応）
            for match in re.finditer(
                r'(?:unsigned\s+)?(?:int|char|short|long|float|double|struct\s+\w+|enum\s+\w+)\s+([A-Za-z_][A-Za-z0-9_]*)\s*(?::\s*\d+|;|\[)',
                block
            ):
                name = match.group(1)
                if name not in self.identifiers['member'] and not self.is_reserved_word(name):
                    self.identifiers['member'][name] = f"m{self.counters['member']}"
                    self.counters['member'] += 1
                    self.used_identifiers.add(name)
        
        # 列挙型のメンバ（列挙子）を抽出
        enum_blocks = re.finditer(
            r'enum\s+[A-Za-z_][A-Za-z0-9_]*\s*\{([^}]+)\}',
            code, re.DOTALL
        )
        for block_match in enum_blocks:
            block = block_match.group(1)
            # 列挙子を抽出
            for match in re.finditer(
                r'([A-Za-z_][A-Za-z0-9_]*)\s*(?:=\s*[^,}]+)?[,}]',
                block
            ):
                name = match.group(1)
                if name not in self.identifiers['member'] and not self.is_reserved_word(name):
                    self.identifiers['member'][name] = f"m{self.counters['member']}"
                    self.counters['member'] += 1
                    self.used_identifiers.add(name)
        
        # 関数定義・宣言を抽出
        for match in re.finditer(
            r'(?:^|\n)\s*(?:static\s+)?(?:inline\s+)?(?:extern\s+)?'
            r'(?:void|int|char|short|long|float|double|unsigned|struct\s+\w+|union\s+\w+|enum\s+\w+)\s+'
            r'(?:\*\s*)?([A-Za-z_][A-Za-z0-9_]*)\s*\([^)]*\)\s*(?:\{|;)',
            code, re.MULTILINE
        ):
            name = match.group(1)
            if name not in self.identifiers['function'] and not self.is_reserved_word(name):
                self.identifiers['function'][name] = f"f{self.counters['function']}"
                self.counters['function'] += 1
                self.used_identifiers.add(name)
        
        # 変数定義を抽出（グローバル変数とローカル変数）
        for match in re.finditer(
            r'(?:^|\n|;|\{)\s*(?:static\s+)?(?:extern\s+)?'
            r'(?:unsigned\s+)?(?:int|char|short|long|float|double|struct\s+\w+|union\s+\w+|enum\s+\w+)\s+'
            r'(?:\*\s*)?([A-Za-z_][A-Za-z0-9_]*)\s*(?:=|;|\[)',
            code, re.MULTILINE
        ):
            name = match.group(1)
            # 関数名や構造体名、列挙型名、予約語でないことを確認
            if (name not in self.identifiers['function'] and
                name not in self.identifiers['struct'] and
                name not in self.identifiers['union'] and
                name not in self.identifiers['enum'] and
                name not in self.identifiers['variable'] and
                not self.is_reserved_word(name)):
                self.identifiers['variable'][name] = f"v{self.counters['variable']}"
                self.counters['variable'] += 1
                self.used_identifiers.add(name)
    
    def find_unused_identifiers(self, code):
        """未使用の識別子を検出し、変換マップに追加（オプション）"""
        # すべての識別子候補を抽出
        all_identifiers = set(re.findall(r'\b([A-Za-z_][A-Za-z0-9_]*)\b', code))
        
        # 未使用のメンバ名を検出
        unused_counter = 1
        for identifier in all_identifiers:
            if identifier not in self.used_identifiers and not self.is_reserved_word(identifier):
                self.identifiers['member'][identifier] = f"mx{unused_counter}"
                unused_counter += 1
    
    def apply_transformations(self, code):
        """変換を適用"""
        # 変換の優先順位: マクロ → 列挙型 → 構造体/共用体 → 関数 → メンバ → 変数
        # コメントは既に変換済みなので除外
        for category in ['macro', 'enum', 'struct', 'union', 'function', 'member', 'variable']:
            for old_name, new_name in self.identifiers[category].items():
                # 単語境界を使用して正確に置換
                code = re.sub(r'\b' + re.escape(old_name) + r'\b', new_name, code)
        
        return code
    
    def generate_conversion_table(self):
        """変換表を生成"""
        table = []
        table.append("=" * 60)
        table.append("識別子変換表")
        table.append("=" * 60)
        
        categories = [
            ('マクロ名', 'macro'),
            ('列挙型名', 'enum'),
            ('構造体名', 'struct'),
            ('共用体名', 'union'),
            ('関数名', 'function'),
            ('変数名', 'variable'),
            ('メンバ名', 'member'),
            ('コメント', 'comment')
        ]
        
        for category_name, category_key in categories:
            if self.identifiers[category_key]:
                table.append(f"\n【{category_name}】")
                for old_name, new_name in sorted(self.identifiers[category_key].items()):
                    table.append(f"  {old_name:30s} -> {new_name}")
        
        table.append("\n" + "=" * 60)
        return "\n".join(table)
    
    def obfuscate(self):
        """難読化を実行"""
        # コメントと文字列を保護
        protected_code = self.remove_comments_and_strings(self.source_code)
        
        # 識別子を抽出
        self.extract_identifiers(protected_code)
        
        # 未使用の識別子を検出（オプション - デフォルトでは無効化）
        # self.find_unused_identifiers(protected_code)
        
        # 変換を適用
        transformed_code = self.apply_transformations(protected_code)
        
        # 保護された部分を復元
        result_code = self.restore_protected(transformed_code)
        
        # 変換表を生成
        conversion_table = self.generate_conversion_table()
        
        return result_code, conversion_table


def main():
    """メイン関数"""
    if len(sys.argv) > 1:
        # ファイルから読み込み
        filename = sys.argv[1]
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                source_code = f.read()
            print(f"入力ファイル: {filename}")
        except Exception as e:
            print(f"エラー: ファイル '{filename}' を読み込めません: {e}")
            sys.exit(1)
    else:
        # サンプルコードを使用
        source_code = SAMPLE_C_CODE
        print("入力ファイル: サンプルコード")
    
    # 難読化を実行
    obfuscator = CObfuscator(source_code)
    transformed_code, conversion_table = obfuscator.obfuscate()
    
    # 結果を出力
    print("\n" + conversion_table)
    print("\n" + "=" * 60)
    print("変換後のコード")
    print("=" * 60)
    print(transformed_code)
    
    # ファイルに保存
    if len(sys.argv) > 1:
        output_filename = sys.argv[1].rsplit('.', 1)[0] + '_obfuscated.c'
        table_filename = sys.argv[1].rsplit('.', 1)[0] + '_conversion_table.txt'
        
        with open(output_filename, 'w', encoding='utf-8') as f:
            f.write(transformed_code)
        
        with open(table_filename, 'w', encoding='utf-8') as f:
            f.write(conversion_table)
        
        print(f"\n変換後のコードを '{output_filename}' に保存しました")
        print(f"変換表を '{table_filename}' に保存しました")


if __name__ == "__main__":
    main()