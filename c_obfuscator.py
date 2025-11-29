#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
C言語ソースコードの識別子を系統的に変換するプログラム（反復処理版）
取りこぼしがなくなるまで変換を繰り返す
#if defined(XXX)のXXXも難読化する対応版
"""

import re
import sys
from collections import defaultdict

# サンプルC言語コード（共用体とビットフィールド、列挙型を含む）
SAMPLE_C_CODE = """
#define MAX_SIZE 100
#define PI 3.14159
#define CALCULATE(x, y) ((x) + (y))
#define DEBUG_MODE

#ifdef DEBUG_MODE
#define DEBUG_PRINT(x) printf(x)
#else
#define DEBUG_PRINT(x)
#endif

#ifndef VERSION_MAJOR
#define VERSION_MAJOR 1
#endif

#if defined(MAX_SIZE) && defined(PI)
#define AREA_CALC(r) (PI * (r) * (r))
#endif

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
    def __init__(self, source_code, prefix="Ut", max_iterations=5):
        self.source_code = source_code
        self.prefix = prefix
        self.max_iterations = max_iterations
        self.identifiers = {
            'macro': {},
            'enum': {},
            'struct': {},
            'union': {},
            'function': {},
            'variable': {},
            'member': {},
            'comment': {},
            'other': {}  # その他の識別子用
        }
        self.counters = {
            'macro': 1,
            'enum': 1,
            'struct': 1,
            'union': 1,
            'function': 1,
            'variable': 1,
            'member': 1,
            'comment': 1,
            'other': 1
        }
        self.used_identifiers = set()
        self.comment_mappings = []
        self.directive_macro_placeholders = {}  # ディレクティブ内のマクロ名プレースホルダー
        
        # 変換パターンの定義
        self.patterns = {
            'macro': f'{prefix}D',
            'enum': f'{prefix}e',
            'struct': f'{prefix}t',
            'union': f'{prefix}u',
            'function': f'{prefix}f',
            'variable': f'{prefix}v',
            'member': f'{prefix}m',
            'comment': f'{prefix}c',
            'other': f'{prefix}x'
        }
        
        # C言語の予約語リスト
        self.c_keywords = {
            'int', 'char', 'short', 'long', 'float', 'double', 'void',
            'signed', 'unsigned', 'uint8_t', 'uint16_t', 'uint32_t', 'uint64_t',
            'int8_t', 'int16_t', 'int32_t', 'int64_t', 'size_t',
            'if', 'else', 'switch', 'case', 'default', 'break', 'continue',
            'for', 'while', 'do', 'goto', 'return',
            'auto', 'register', 'static', 'extern', 'typedef',
            'const', 'volatile', 'restrict',
            'struct', 'union', 'enum', 'sizeof', 'inline', 'true', 'false', 'bool',
            '_Bool', '_Complex', '_Imaginary',
            '_Alignas', '_Alignof', '_Atomic', '_Static_assert',
            '_Noreturn', '_Thread_local', '_Generic',
            'printf', 'scanf', 'malloc', 'free', 'memcpy', 'memset',
            'strlen', 'strcpy', 'strcmp', 'strcat', 'sprintf', 'snprintf',
            'fopen', 'fclose', 'fread', 'fwrite', 'fprintf', 'fscanf',
            'exit', 'NULL', 'main', 'define', 'ifndef', 'endif', 'include', 'HASH',
            'bool','true','false',
            'defined'  # defined()演算子は予約語として扱う
        }
    
    def extract_directive_macros(self, code):
        """プリプロセッサディレクティブ内のマクロ名を抽出"""
        directive_macros = set()
        
        # まず#defineで定義されているマクロ名を収集
        defined_macros = set()
        for match in re.finditer(r'#define\s+([A-Za-z_][A-Za-z0-9_]*)', code):
            macro_name = match.group(1)
            if not self.is_reserved_word(macro_name):
                defined_macros.add(macro_name)
        
        # #ifdef MACRO_NAME
        for match in re.finditer(r'#ifdef\s+([A-Za-z_][A-Za-z0-9_]*)', code):
            macro_name = match.group(1)
            if not self.is_reserved_word(macro_name):
                directive_macros.add(macro_name)
        
        # #ifndef MACRO_NAME
        for match in re.finditer(r'#ifndef\s+([A-Za-z_][A-Za-z0-9_]*)', code):
            macro_name = match.group(1)
            if not self.is_reserved_word(macro_name):
                directive_macros.add(macro_name)
        
        # #if, #elif ディレクティブを1行ずつ処理
        for line_match in re.finditer(r'#(?:if|elif)\b[^\n]*', code):
            line = line_match.group(0)
            
            # defined(MACRO_NAME) または defined MACRO_NAME の形式をすべて抽出
            for macro_match in re.finditer(r'defined\s*\(?\s*([A-Za-z_][A-Za-z0-9_]*)\s*\)?', line):
                macro_name = macro_match.group(1)
                if not self.is_reserved_word(macro_name):
                    directive_macros.add(macro_name)
            
            # 条件式内のすべての識別子を抽出（#defineで定義されているものに限定）
            for identifier_match in re.finditer(r'\b([A-Za-z_][A-Za-z0-9_]*)\b', line):
                identifier = identifier_match.group(1)
                # #defineで定義されたマクロ、または既に抽出済みのマクロの場合
                if identifier in defined_macros and not self.is_reserved_word(identifier):
                    directive_macros.add(identifier)
        
        return directive_macros
        
    def remove_comments_strings_and_directives(self, code):
        """コメント、文字列リテラル、プリプロセッサディレクティブを保護"""
        self.protected = {}
        counter = 0
        directive_placeholder_counter = 0
        
        def replace_with_placeholder(match, transformed_content=None):
            nonlocal counter
            placeholder = f"__PROTECTED_{counter}__"
            self.protected[placeholder] = transformed_content if transformed_content else match.group(0)
            counter += 1
            return placeholder
        
        # まず、ディレクティブ内のマクロ名を抽出（保護する前に）
        directive_macros = self.extract_directive_macros(code)
        
        # 抽出したマクロ名をマクロ辞書に登録
        for macro_name in directive_macros:
            if macro_name not in self.identifiers['macro'] and not self.is_reserved_word(macro_name):
                self.identifiers['macro'][macro_name] = f"{self.patterns['macro']}{self.counters['macro']}"
                self.counters['macro'] += 1
                self.used_identifiers.add(macro_name)
        
        # #defineを特殊マーカーに置き換え（識別子として認識されない形式）
        code = code.replace('#define ', '~HASH~define ')
        code = code.replace('#define\t', '~HASH~define\t')
        
        # #includeを保護
        code = re.sub(r'#include\s+[<"][^>"]+[>"]', lambda m: replace_with_placeholder(m), code)
        
        # プリプロセッサディレクティブを保護（マクロ名をプレースホルダーに置き換えながら）
        def protect_directive_with_macro(match):
            nonlocal directive_placeholder_counter
            directive = match.group(0)
            
            # ディレクティブ内のマクロ名をプレースホルダーに置き換え
            # すべての識別子を検出して、マクロ辞書にあるものを置き換える
            def replace_macro_in_directive(m):
                nonlocal directive_placeholder_counter
                identifier = m.group(0)
                if identifier in self.identifiers['macro']:
                    # マクロ名のプレースホルダーを作成
                    placeholder = f"~MACRO_{directive_placeholder_counter}~"
                    self.directive_macro_placeholders[placeholder] = identifier
                    directive_placeholder_counter += 1
                    return placeholder
                return identifier
            
            # ディレクティブ内の識別子を置き換え
            transformed_directive = re.sub(
                r'\b([A-Za-z_][A-Za-z0-9_]*)\b',
                replace_macro_in_directive,
                directive
            )
            
            return replace_with_placeholder(match, transformed_directive)
        
        # #if, #ifdef, #ifndef, #elif, #else, #endif, #pragma, #error, #warningを保護
        code = re.sub(
            r'#(?:if|ifdef|ifndef|elif|else|endif|pragma|error|warning)\b[^\n]*',
            protect_directive_with_macro,
            code
        )
        
        # 文字列リテラルを保護
        code = re.sub(r'"(?:[^"\\]|\\.)*"', lambda m: replace_with_placeholder(m), code)
        code = re.sub(r"'(?:[^'\\]|\\.)*'", lambda m: replace_with_placeholder(m), code)
        
        # コメントを変換して保護
        def replace_comment(match):
            original_comment = match.group(0)
            
            if original_comment.startswith('//'):
                comment_content = original_comment[2:].strip()
            else:
                comment_content = original_comment[2:-2].strip()
            
            if comment_content:
                comment_id = f"{self.patterns['comment']}{self.counters['comment']}"
                self.comment_mappings.append((comment_id, comment_content))
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
        # まず、ディレクティブ内のマクロ名プレースホルダーを難読化後の名前に置き換え
        for placeholder, original_macro_name in self.directive_macro_placeholders.items():
            if original_macro_name in self.identifiers['macro']:
                obfuscated_name = self.identifiers['macro'][original_macro_name]
                # protectedの中身を置き換え
                for prot_key in self.protected:
                    self.protected[prot_key] = self.protected[prot_key].replace(
                        placeholder,
                        obfuscated_name
                    )
        
        # 通常の保護された部分を復元
        for placeholder, original in self.protected.items():
            code = code.replace(placeholder, original)
        
        # 最後に~HASH~を#に戻す
        code = code.replace('~HASH~', '#')
        
        return code
    
    def is_reserved_word(self, name):
        """予約語かどうかをチェック"""
        return name in self.c_keywords
    
    def extract_identifiers(self, code):
        """識別子を抽出して分類（1回目のパス）"""
        
        # 1. マクロ定義（~HASH~defineの後に続く識別子）
        for match in re.finditer(r'~HASH~define\s+([A-Za-z_][A-Za-z0-9_]*)', code):
            name = match.group(1)
            if name not in self.identifiers['macro'] and not self.is_reserved_word(name):
                self.identifiers['macro'][name] = f"{self.patterns['macro']}{self.counters['macro']}"
                self.counters['macro'] += 1
                self.used_identifiers.add(name)
        
        # 2. 列挙型定義
        for match in re.finditer(r'enum\s+([A-Za-z_][A-Za-z0-9_]*)\s*(?:\{|;)', code):
            name = match.group(1)
            if name not in self.identifiers['enum'] and not self.is_reserved_word(name):
                self.identifiers['enum'][name] = f"{self.patterns['enum']}{self.counters['enum']}"
                self.counters['enum'] += 1
                self.used_identifiers.add(name)
        
        # 3. 構造体定義
        for match in re.finditer(r'struct\s+([A-Za-z_][A-Za-z0-9_]*)\s*(?:\{|;|\*|[^\w])', code):
            name = match.group(1)
            if name not in self.identifiers['struct'] and not self.is_reserved_word(name):
                self.identifiers['struct'][name] = f"{self.patterns['struct']}{self.counters['struct']}"
                self.counters['struct'] += 1
                self.used_identifiers.add(name)
        
        # 4. 共用体定義
        for match in re.finditer(r'union\s+([A-Za-z_][A-Za-z0-9_]*)\s*(?:\{|;|\*|[^\w])', code):
            name = match.group(1)
            if name not in self.identifiers['union'] and not self.is_reserved_word(name):
                self.identifiers['union'][name] = f"{self.patterns['union']}{self.counters['union']}"
                self.counters['union'] += 1
                self.used_identifiers.add(name)
        
        # 5. 関数定義・宣言
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
        
        # 6. メンバアクセス（-> と .）
        for match in re.finditer(r'(?:->|\.)\s*([A-Za-z_][A-Za-z0-9_]*)', code):
            name = match.group(1)
            if name not in self.identifiers['member'] and not self.is_reserved_word(name):
                self.identifiers['member'][name] = f"{self.patterns['member']}{self.counters['member']}"
                self.counters['member'] += 1
                self.used_identifiers.add(name)
        
        # 7. 列挙型のメンバ
        enum_blocks = re.finditer(r'enum\s+(?:[A-Za-z_][A-Za-z0-9_]*)?\s*\{([^}]+)\}', code, re.DOTALL)
        for block_match in enum_blocks:
            block = block_match.group(1)
            for match in re.finditer(r'([A-Za-z_][A-Za-z0-9_]*)\s*(?:=\s*[^,}]+)?(?:,|})', block):
                name = match.group(1)
                if name not in self.identifiers['member'] and not self.is_reserved_word(name):
                    self.identifiers['member'][name] = f"{self.patterns['member']}{self.counters['member']}"
                    self.counters['member'] += 1
                    self.used_identifiers.add(name)
        
        # 8. 構造体・共用体内のメンバ定義
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
        
        # 9. 変数定義
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
        for match in re.finditer(r'for\s*\(\s*(?:int|uint\d+_t|size_t)\s+([A-Za-z_][A-Za-z0-9_]*)', code):
            name = match.group(1)
            if (name not in self.identifiers['variable'] and
                name not in self.identifiers['member'] and
                not self.is_reserved_word(name)):
                self.identifiers['variable'][name] = f"{self.patterns['variable']}{self.counters['variable']}"
                self.counters['variable'] += 1
                self.used_identifiers.add(name)
    
    def find_unconverted_identifiers(self, code):
        """未変換の識別子を検出（2回目以降のパス）"""
        # すべての識別子を抽出
        all_identifiers = set(re.findall(r'\b([A-Za-z_][A-Za-z0-9_]*)\b', code))
        
        # 未変換の識別子を検出
        unconverted = []
        for identifier in all_identifiers:
            # 予約語でない、プレフィックス付きでない、既に変換マップにない
            if (not self.is_reserved_word(identifier) and
                not identifier.startswith(self.prefix) and
                not identifier.startswith('__PROTECTED_') and
                not identifier.startswith('~MACRO_') and
                identifier not in self.used_identifiers):
                unconverted.append(identifier)
        
        return unconverted
    
    def add_identifier(self, name, category='other'):
        """識別子を追加"""
        if category not in self.identifiers:
            category = 'other'
        
        if name not in self.identifiers[category]:
            new_id = f"{self.patterns[category]}{self.counters[category]}"
            self.identifiers[category][name] = new_id
            self.counters[category] += 1
            self.used_identifiers.add(name)
            return new_id
        return self.identifiers[category][name]
    
    def apply_transformations(self, code):
        """変換を適用"""
        # すべての識別子を長さ順にソート
        all_items = []
        for category in ['macro', 'enum', 'struct', 'union', 'function', 'member', 'variable', 'other']:
            for old_name, new_name in self.identifiers[category].items():
                all_items.append((old_name, new_name, len(old_name)))
        
        all_items.sort(key=lambda x: x[2], reverse=True)
        
        for old_name, new_name, _ in all_items:
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
            ('その他', 'other'),
        ]
        
        total_count = 0
        for category_name, category_key in categories:
            if self.identifiers[category_key]:
                table.append(f"\n【{category_name}】")
                for old_name, new_name in sorted(self.identifiers[category_key].items()):
                    table.append(f"  {old_name:30s} -> {new_name}")
                    total_count += 1
        
        if self.comment_mappings:
            table.append(f"\n【コメント】")
            seen_pairs = set()
            for comment_id, comment_content in self.comment_mappings:
                pair = (comment_content, comment_id)
                if pair not in seen_pairs:
                    table.append(f"  {comment_content:30s} -> {comment_id}")
                    seen_pairs.add(pair)
                    total_count += 1
        
        table.append(f"\n合計: {total_count} 件の識別子")
        table.append("=" * 60)
        return "\n".join(table)
    
    def obfuscate(self):
        """難読化を実行（反復処理）"""
        print("\n" + "=" * 60)
        print("難読化処理開始（反復モード + ディレクティブ対応）")
        print("=" * 60)
        
        # コメント、文字列、ディレクティブを保護
        protected_code = self.remove_comments_strings_and_directives(self.source_code)
        
        # 1回目のパス: 通常の識別子抽出
        print("\n[パス 1] 通常の識別子抽出...")
        self.extract_identifiers(protected_code)
        initial_count = len(self.used_identifiers)
        print(f"  → {initial_count} 個の識別子を検出")
        
        # 変換を適用
        transformed_code = self.apply_transformations(protected_code)
        
        # 2回目以降のパス: 未変換の識別子を検出して変換
        iteration = 2
        while iteration <= self.max_iterations:
            print(f"\n[パス {iteration}] 未変換識別子の検出...")
            
            # 未変換の識別子を検出
            unconverted = self.find_unconverted_identifiers(transformed_code)
            
            if not unconverted:
                print("  → 未変換の識別子はありません")
                break
            
            print(f"  → {len(unconverted)} 個の未変換識別子を検出")
            print(f"     例: {', '.join(list(unconverted)[:5])}")
            
            # 未変換の識別子を「その他」カテゴリとして追加
            for identifier in unconverted:
                self.add_identifier(identifier, 'other')
            
            # 再度変換を適用
            transformed_code = self.apply_transformations(protected_code)
            iteration += 1
        
        if iteration > self.max_iterations:
            print(f"\n[警告] 最大反復回数({self.max_iterations})に達しました")
            remaining = self.find_unconverted_identifiers(transformed_code)
            if remaining:
                print(f"  残りの未変換識別子: {len(remaining)} 個")
                print(f"  例: {', '.join(list(remaining)[:10])}")
        
        # 保護された部分を復元
        result_code = self.restore_protected(transformed_code)
        
        # 変換表を生成
        conversion_table = self.generate_conversion_table()
        
        print(f"\n最終結果: {len(self.used_identifiers)} 個の識別子を変換")
        print("=" * 60)
        
        return result_code, conversion_table


def main():
    """メイン関数"""
    prefix = "Ut"
    max_iterations = 5
    file_arg_index = 1
    
    # コマンドライン引数の解析
    i = 1
    while i < len(sys.argv):
        if sys.argv[i].startswith("--prefix="):
            prefix = sys.argv[i].split("=")[1]
            print(f"プレフィックス: {prefix}")
            file_arg_index += 1
            i += 1
        elif sys.argv[i].startswith("--max-iterations="):
            max_iterations = int(sys.argv[i].split("=")[1])
            print(f"最大反復回数: {max_iterations}")
            file_arg_index += 1
            i += 1
        else:
            break
    
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
    obfuscator = CObfuscator(source_code, prefix, max_iterations)
    transformed_code, conversion_table = obfuscator.obfuscate()
    
    # 結果を出力
    print("\n" + conversion_table)
    print("\n" + "=" * 60)
    print("変換後のコード（プレビュー - 最初の50行）")
    print("=" * 60)
    lines = transformed_code.split('\n')
    for i, line in enumerate(lines[:50]):
        print(line)
    if len(lines) > 50:
        print(f"... (残り {len(lines) - 50} 行)")
    
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
