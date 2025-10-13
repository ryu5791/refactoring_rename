# C言語識別子変換プログラム（改善版）

C言語のソースコードを系統的に難読化・逆変換するPythonツールです。

## 機能

- **変数名**: v1, v2, v3...
- **関数名**: f1, f2, f3...
- **マクロ名**: D1, D2, D3...
- **構造体名**: t1, t2, t3...
- **共用体名**: u1, u2, u3...
- **メンバ名**: m1, m2, m3...
- **コメント**: c1, c2, c3...
- **未使用識別子**: mx1, mx2, mx3...

## 特徴

✅ **コンパイル可能** - C言語の予約語や標準ライブラリ関数は変換しない
✅ **完全可逆** - 変換表を使って元のコードに復元可能
✅ **ビットフィールド対応** - 共用体内のビットフィールドも正確に変換
✅ **プリプロセッサ保護** - #includeなどのディレクティブは保護される
✅ **メンバアクセス対応** - 構造体や共用体のメンバアクセス（->、.）を正しく処理

## 使い方

### 1. 難読化（識別子の変換）

```bash
# サンプルコードで実行
python c_obfuscator.py

# 自分のファイルを変換
python c_obfuscator.py your_code.c
```

**出力ファイル:**
- `your_code_obfuscated.c` - 変換後のソースコード
- `your_code_conversion_table.txt` - 変換表（復元に必要）

### 2. 逆変換（元に戻す）

```bash
# 自動で変換表を検出
python c_deobfuscator.py your_code_obfuscated.c

# 変換表を明示的に指定
python c_deobfuscator.py your_code_obfuscated.c your_code_conversion_table.txt
```

**出力ファイル:**
- `your_code_restored.c` - 復元されたソースコード

## 変換例

### 変換前
```c
#define MAX_SIZE 100

// 列挙型定義
enum Color {
    RED,
    GREEN,
    BLUE
};

// 構造体定義
struct Point {
    int x_coord;
    int y_coord;
};

// グローバル変数
int global_counter = 0;

// 関数定義
int calculate_distance(struct Point p1, struct Point p2) {
    // 差分を計算
    int dx = p1.x_coord - p2.x_coord;
    int dy = p1.y_coord - p2.y_coord;
    return dx * dx + dy * dy;
}
```

### 変換後
```c
#define D1 100

// c1
enum e1 {
    m1,
    m2,
    m3
};

// c2
struct t1 {
    int m4;
    int m5;
};

// c3
int v1 = 0;

// c4
int f1(struct t1 v2, struct t1 v3) {
    // c5
    int v4 = v2.m4 - v3.m4;
    int v5 = v2.m5 - v3.m5;
    return v4 * v4 + v5 * v5;
}
```

### 変換表
```
============================================================
識別子変換表
============================================================

【マクロ名】
  MAX_SIZE                       -> D1

【列挙型名】
  Color                          -> e1

【構造体名】
  Point                          -> t1

【関数名】
  calculate_distance             -> f1

【変数名】
  dx                             -> v4
  dy                             -> v5
  global_counter                 -> v1
  p1                             -> v2
  p2                             -> v3

【メンバ名】
  BLUE                           -> m3
  GREEN                          -> m2
  RED                            -> m1
  x_coord                        -> m4
  y_coord                        -> m5

【コメント】
  列挙型定義                        -> c1
  構造体定義                        -> c2
  グローバル変数                     -> c3
  関数定義                          -> c4
  差分を計算                        -> c5
============================================================
```

## 動作確認

```bash
# 1. オリジナルのコンパイル
gcc -o original your_code.c
./original

# 2. 難読化
python c_obfuscator.py your_code.c

# 3. 難読化版のコンパイル（正常にコンパイルできることを確認）
gcc -o obfuscated your_code_obfuscated.c
./obfuscated

# 4. 復元
python c_deobfuscator.py your_code_obfuscated.c

# 5. 復元版のコンパイル
gcc -o restored your_code_restored.c
./restored
```

## 注意事項

### ⚠️ 制限事項

1. **ヘッダーファイル**: `#include`で読み込まれる外部ファイルは変換されません
2. **変換表の保管**: `*_conversion_table.txt`は必ず保管してください（復元に必須）

### 💡 ベストプラクティス

1. **バックアップ**: 変換前に必ずオリジナルファイルのバックアップを取ってください
2. **テスト**: 変換後のコードが正しくコンパイル・動作することを確認してください

## ファイル構成

```
c-obfuscator/
├── c_obfuscator.py          # 難読化プログラム
└── c_deobfuscator.py        # 逆変換プログラム
```

## 改善点（最新版）

- ✅ メンバアクセス（`->`, `.`）で使用される識別子を正しくメンバ名として検出
- ✅ 関数引数を変数名として正しく分類
- ✅ プリプロセッサディレクティブ（`#include`など）を保護
- ✅ コメントの変換と復元を改善
- ✅ 処理順序を最適化（メンバアクセス → 変数定義の順で処理）

## ライセンス

MIT License

## 最終更新

2025年10月
