#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
C言語ソースコードの識別子を系統的に変換するプログラム（改良版）
プレフィックス「Ut」を追加して誤変換を防ぐ
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
            printf("Idle\\n");  // アイドル状態
            break;
        case 1:
            printf("Active\\n");  // アクティブ状態
            break;
        default:
            printf("Unknown\\n");  // 未知のコマンド
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
    def __init__(self, source_code, prefix="Ut"):
        self.source_code = source_code
        self.prefix = prefix  # 誤変換防止用のプレフィックス
        self.identifiers = {
            'macro': {},      # UtD1, UtD2, ...
            'enum': {},       # Ute1, Ute2, ...
            'struct': {},     # Utt1, Utt2, ...
            'union': {},      # Utu1, Utu2, ...
            'function': {},   # Utf1, Utf2, ...
            'variable': {},   # Utv1, Utv2, ...
            'member': {},     # Utm1, Utm2, ...
            'comment': {}     # Utc1, Utc2, ...
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
        
        # 変換パターンの定義（プレフィックス付き）
        self.patterns = {
            'macro': f'{prefix}D',
            'enum': f'{prefix}e',
            'struct': f'{prefix}t',
            'union': f'{prefix}u',
            'function': f'{prefix}f',
            'variable': f'{prefix}v',
            'member': f'{prefix}m',
            'comment': f'{prefix}c'
        }
        
        # C言語の予約語リスト
        self.c_keywords = {
            # 型
            'int', 'char', 'short', 'long', 'float', 'double', 'void',
            'signed', 'unsigned', 'uint8_t', 'uint16_t', 'uint32_t', 'uint64_t',
            'int8_t', 'int16_t', 'int32_t', 'int64_t', 'size_t',
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
            'exit', 'NULL',
            # 特殊な関数
            'main'  # main関数は変換しない
        }
        
    def remove_comments_strings_and_directives(self, code):
        """コメント、文字列リテラル、プリプロセッサディレクティブを保護"""
        self.protected = {}
        counter = 0
        
        def replace_with_placeholder(match, transformed_content=None):
            nonlocal counter
            placeholder = f"__PROTECTED_{counter}__"
            self.protected[placeholder] = transformed_content if transformed_content else match.group(0)
            counter += 1
            return placeholder
        
        # 1. プリプロセッサディレクティブを保護（#includeなど、#defineは除く）
        def protect_include(match):
            return replace_with_placeholder(match)
        
        code = re.sub(r'#include\s+[<"][^>"]+[>"]', protect_include, code)
        code = re.sub(r'#(?:if|ifdef|ifndef|elif|else|endif|pragma|error|warning)\b[^\n]*', protect_include, code)
        
        # 2. 文字列リテラルを保護
        code = re.sub(r'"(?:[^"\\]|\\.)*"', lambda m: replace_with_placeholder(m), code)
        code = re.sub(r"'(?:[^'\\]|\\.)*'", lambda m: replace_with_placeholder(m), code)
        
        # 3. コメントを変換して保護
        def replace_comment(match):
            original_comment = match.group(0)
            
            if original_comment.startswith('//'):
                comment_content = original_comment[2:].strip()
            else:
                comment_content = original_comment[2:-2].strip()
            
            if comment_content:
                comment_id = f"{self.patterns['comment']}{self.counters['comment']}"
                self.identifiers['comment'][comment_content] = comment_id
                self.counters['comment'] += 1
                
                if original_comment.startswith('//'):
                    transformed_comment = f"// {comment_id}"
                else:
                    transformed_comment = f"/* {comment_id} */"
            else:
                transformed_comment = original_comment
            
            return replace_with_placeholder(match, transformed_comment)
        
        code = re.sub(r'//[^\n]*', replace_comment, code)
        code = re.sub(r'/\*.*?\*/', replace_comment, code, flags=re.DOTALL)
        
        return code
    
    def restore_protected(self, code):
        """保護された部分を復元"""
        for placeholder, original in self.protected.items():
            code = code.replace(placeholder, original)
        return code
    
    def is_reserved_word(self, name):
        """予約語かどうかをチェック"""
        return name in self.c_keywords
    
    def extract_identifiers(self, code):
        """識別子を抽出して分類"""
        
        # 1. マクロ定義を抽出
        for match in re.finditer(r'#define\s+([A-Za-z_][A-Za-z0-9_]*)', code):
            name = match.group(1)
            if name not in self.identifiers['macro'] and not self.is_reserved_word(name):
                self.identifiers['macro'][name] = f"{self.patterns['macro']}{self.counters['macro']}"
                self.counters['macro'] += 1
                self.used_identifiers.add(name)
        
        # 2. 列挙型定義を抽出
        for match in re.finditer(r'enum\s+([A-Za-z_][A-Za-z0-9_]*)\s*(?:\{|;)', code):
            name = match.group(1)
            if name not in self.identifiers['enum'] and not self.is_reserved_word(name):
                self.identifiers['enum'][name] = f"{self.patterns['enum']}{self.counters['enum']}"
                self.counters['enum'] += 1
                self.used_identifiers.add(name)
        
        # 3. 構造体定義を抽出
        for match in re.finditer(r'struct\s+([A-Za-z_][A-Za-z0-9_]*)\s*(?:\{|;|\*|[^\w])', code):
            name = match.group(1)
            if name not in self.identifiers['struct'] and not self.is_reserved_word(name):
                self.identifiers['struct'][name] = f"{self.patterns['struct']}{self.counters['struct']}"
                self.counters['struct'] += 1
                self.used_identifiers.add(name)
        
        # 4. 共用体定義を抽出
        for match in re.finditer(r'union\s+([A-Za-z_][A-Za-z0-9_]*)\s*(?:\{|;|\*|[^\w])', code):
            name = match.group(1)
            if name not in self.identifiers['union'] and not self.is_reserved_word(name):
                self.identifiers['union'][name] = f"{self.patterns['union']}{self.counters['union']}"
                self.counters['union'] += 1
                self.used_identifiers.add(name)
        
        # 5. 関数定義・宣言を抽出
        for match in re.finditer(
            r'(?:^|[\n;])\s*(?:static\s+|inline\s+|extern\s+)*'
            r'(?:const\s+|volatile\s+)*'
            r'(?:void|int|char|short|long|float|double|unsigned|signed|'
            r'uint\d+_t|int\d+_t|size_t|'
            r'struct\s+\w+|union\s+\w+|enum\s+\w+)\s+'
            r'(?:\*\s*)*([A-Za-z_][A-Za-z0-9_]*)\s*\([^)]*\)\s*(?:[;{])',
            code, re.MULTILINE
        ):
            name = match.group(1)
            if name not in self.identifiers['function'] and not self.is_reserved_word(name):
                self.identifiers['function'][name] = f"{self.patterns['function']}{self.counters['function']}"
                self.counters['function'] += 1
                self.used_identifiers.add(name)
        
        # 6. メンバアクセス（-> と .）で使用されている識別子を最優先で抽出
        for match in re.finditer(r'(?:->|\.)\s*([A-Za-z_][A-Za-z0-9_]*)', code):
            name = match.group(1)
            if name not in self.identifiers['member'] and not self.is_reserved_word(name):
                self.identifiers['member'][name] = f"{self.patterns['member']}{self.counters['member']}"
                self.counters['member'] += 1
                self.used_identifiers.add(name)
        
        # 7. 列挙型のメンバ（列挙子）を抽出
        enum_blocks = re.finditer(
            r'enum\s+(?:[A-Za-z_][A-Za-z0-9_]*)?\s*\{([^}]+)\}',
            code, re.DOTALL
        )
        for block_match in enum_blocks:
            block = block_match.group(1)
            for match in re.finditer(r'([A-Za-z_][A-Za-z0-9_]*)\s*(?:=\s*[^,}]+)?(?:,|})', block):
                name = match.group(1)
                if name not in self.identifiers['member'] and not self.is_reserved_word(name):
                    self.identifiers['member'][name] = f"{self.patterns['member']}{self.counters['member']}"
                    self.counters['member'] += 1
                    self.used_identifiers.add(name)
        
        # 8. 構造体・共用体内のメンバ定義を抽出
        struct_union_blocks = re.finditer(
            r'(?:struct|union)\s+(?:[A-Za-z_][A-Za-z0-9_]*)?\s*\{([^}]+)\}',
            code, re.DOTALL
        )
        for block_match in struct_union_blocks:
            block = block_match.group(1)
            for match in re.finditer(
                r'(?:unsigned\s+|const\s+|volatile\s+|static\s+)*'
                r'(?:int|char|short|long|float|double|void|uint\d+_t|int\d+_t|size_t|struct\s+\w+|union\s+\w+|enum\s+\w+)\s+'
                r'(?:\*\s*)*([A-Za-z_][A-Za-z0-9_]*)\s*(?::\s*\d+|;|\[)',
                block
            ):
                name = match.group(1)
                if name not in self.identifiers['member'] and not self.is_reserved_word(name):
                    self.identifiers['member'][name] = f"{self.patterns['member']}{self.counters['member']}"
                    self.counters['member'] += 1
                    self.used_identifiers.add(name)
        
        # 9. 変数定義を抽出
        variable_patterns = [
            # 関数引数
            r'\(\s*(?:const\s+|volatile\s+)*'
            r'(?:unsigned\s+|signed\s+)*'
            r'(?:int|char|short|long|float|double|void|'
            r'uint\d+_t|int\d+_t|size_t|'
            r'struct\s+\w+|union\s+\w+|enum\s+\w+)\s+'
            r'(?:\*\s*)*([A-Za-z_][A-Za-z0-9_]*)\s*[,)]',
            
            # グローバル・ローカル変数
            r'(?:^|[\n;{])\s*(?:static\s+|extern\s+|const\s+|volatile\s+)*'
            r'(?:unsigned\s+|signed\s+)*'
            r'(?:int|char|short|long|float|double|void|'
            r'uint\d+_t|int\d+_t|size_t|'
            r'struct\s+\w+|union\s+\w+|enum\s+\w+)\s+'
            r'(?:\*\s*)*([A-Za-z_][A-Za-z0-9_]*)\s*(?:[=;\[,])',
        ]
        
        for pattern in variable_patterns:
            for match in re.finditer(pattern, code, re.MULTILINE):
                name = match.group(1)
                if (name not in self.identifiers['function'] and
                    name not in self.identifiers['struct'] and
                    name not in self.identifiers['union'] and
                    name not in self.identifiers['enum'] and
                    name not in self.identifiers['variable'] and
                    name not in self.identifiers['macro'] and
                    name not in self.identifiers['member'] and
                    not self.is_reserved_word(name)):
                    self.identifiers['variable'][name] = f"{self.patterns['variable']}{self.counters['variable']}"
                    self.counters['variable'] += 1
                    self.used_identifiers.add(name)
        
        # 10. forループ内の変数
        for match in re.finditer(
            r'for\s*\(\s*(?:int|uint\d+_t|size_t)\s+([A-Za-z_][A-Za-z0-9_]*)',
            code
        ):
            name = match.group(1)
            if (name not in self.identifiers['variable'] and
                name not in self.identifiers['member'] and
                not self.is_reserved_word(name)):
                self.identifiers['variable'][name] = f"{self.patterns['variable']}{self.counters['variable']}"
                self.counters['variable'] += 1
                self.used_identifiers.add(name)
    
    def apply_transformations(self, code):
        """変換を適用（単語境界を使用せず、すべての出現箇所を変換）"""
        # 長い名前から順に変換（部分一致を避けるため）
        all_items = []
        for category in ['macro', 'enum', 'struct', 'union', 'function', 'member', 'variable']:
            for old_name, new_name in self.identifiers[category].items():
                all_items.append((old_name, new_name, len(old_name)))
        
        # 長さの降順でソート
        all_items.sort(key=lambda x: x[2], reverse=True)
        
        for old_name, new_name, _ in all_items:
            # 単語境界を使用した置換（独立した識別子）
            code = re.sub(r'\b' + re.escape(old_name) + r'\b', new_name, code)
        
        return code
    
    def generate_conversion_table(self):
        """変換表を生成"""
        table = []
        table.append("=" * 60)
        table.append(f"識別子変換表 (プレフィックス: {self.prefix})")
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
        
        total_count = 0
        for category_name, category_key in categories:
            if self.identifiers[category_key]:
                table.append(f"\n【{category_name}】")
                for old_name, new_name in sorted(self.identifiers[category_key].items()):
                    table.append(f"  {old_name:30s} -> {new_name}")
                    total_count += 1
        
        table.append(f"\n合計: {total_count} 件の識別子")
        table.append("=" * 60)
        return "\n".join(table)
    
    def obfuscate(self):
        """難読化を実行"""
        # コメント、文字列、ディレクティブを保護
        protected_code = self.remove_comments_strings_and_directives(self.source_code)
        
        # 識別子を抽出
        self.extract_identifiers(protected_code)
        
        # 変換を適用
        transformed_code = self.apply_transformations(protected_code)
        
        # 保護された部分を復元
        result_code = self.restore_protected(transformed_code)
        
        # 変換表を生成
        conversion_table = self.generate_conversion_table()
        
        return result_code, conversion_table


def main():
    """メイン関数"""
    # コマンドライン引数からプレフィックスを取得（オプション）
    prefix = "Ut"  # デフォルトプレフィックス
    file_arg_index = 1
    
    if len(sys.argv) > 1 and sys.argv[1].startswith("--prefix="):
        prefix = sys.argv[1].split("=")[1]
        file_arg_index = 2
        print(f"プレフィックス: {prefix}")
    
    if len(sys.argv) > file_arg_index:
        filename = sys.argv[file_arg_index]
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                source_code = f.read()
            print(f"入力ファイル: {filename}")
        except Exception as e:
            print(f"エラー: ファイル '{filename}' を読み込めません: {e}")
            sys.exit(1)
    else:
        source_code = SAMPLE_C_CODE
        print("入力ファイル: サンプルコード")
    
    # 難読化を実行
    obfuscator = CObfuscator(source_code, prefix)
    transformed_code, conversion_table = obfuscator.obfuscate()
    
    # 結果を出力
    print("\n" + conversion_table)
    print("\n" + "=" * 60)
    print("変換後のコード")
    print("=" * 60)
    print(transformed_code)
    
    # ファイルに保存
    if len(sys.argv) > file_arg_index:
        output_filename = sys.argv[file_arg_index].rsplit('.', 1)[0] + '_obfuscated.c'
        table_filename = sys.argv[file_arg_index].rsplit('.', 1)[0] + '_conversion_table.txt'
        
        with open(output_filename, 'w', encoding='utf-8') as f:
            f.write(transformed_code)
        
        with open(table_filename, 'w', encoding='utf-8') as f:
            f.write(conversion_table)
        
        print(f"\n変換後のコードを '{output_filename}' に保存しました")
        print(f"変換表を '{table_filename}' に保存しました")


if __name__ == "__main__":
    main()
