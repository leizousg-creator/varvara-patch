#!/bin/sh
# Varvara 补丁构建脚本
# 从官方原版 APK 生成去上报 + 控制中心磁贴版本
#
# 用法: ./build.sh <原始.apk> [输出.apk]

set -e

REPO=$(cd "$(dirname "$0")" && pwd)
KS="$REPO/signing.keystore"
KS_PASS="${KS_PASS:-varvara-local}"

usage() {
    echo "用法: $0 <原始.apk> [输出.apk]"
    echo ""
    echo "示例: ./build.sh Varvara-0.1.152.apk"
    exit 2
}

[ $# -ge 1 ] || usage

IN="$1"
OUT="${2:-Varvara-patched.apk}"
case "$OUT" in
    /*) OUTPATH="$OUT" ;;
    *)  OUTPATH="$REPO/$OUT" ;;
esac

if [ ! -f "$IN" ]; then
    echo "找不到输入文件: $IN"
    exit 1
fi

echo "=== 检查依赖 ==="
for t in baksmali smali zipalign apksigner keytool python3 unzip; do
    if ! command -v "$t" >/dev/null 2>&1; then
        echo "缺少工具: $t"
        exit 1
    fi
done
echo "OK"

WORK=$(mktemp -d)
trap 'rm -rf "$WORK"' EXIT

echo ""
echo "=== [1/6] 解包 ==="
cd "$WORK"
unzip -q "$(cd "$(dirname "$IN")" && pwd)/$(basename "$IN")" classes.dex AndroidManifest.xml
echo "classes.dex 与 AndroidManifest.xml 已提取"

echo ""
echo "=== [2/6] 反编译 smali ==="
baksmali d classes.dex -o smali

echo ""
echo "=== [3/6] 应用补丁 ==="
python3 "$REPO/patches/apply_smali.py" smali

echo ""
echo "=== [4/6] 汇编 dex ==="
smali a smali -o classes_new.dex

echo ""
echo "=== [5/6] 注入清单 ==="
python3 "$REPO/patches/apply_manifest.py" AndroidManifest.xml Manifest.new.xml

echo ""
echo "=== [6/6] 打包签名 ==="
python3 - "$IN" "$WORK" <<'PY'
import sys, zipfile
src = sys.argv[1]
work = sys.argv[2]
old = {'META-INF/CERT.SF', 'META-INF/CERT.RSA', 'META-INF/MANIFEST.MF'}
dex = open(work + '/classes_new.dex', 'rb').read()
man = open(work + '/Manifest.new.xml', 'rb').read()
with zipfile.ZipFile(src) as z, zipfile.ZipFile(work + '/unsigned.apk', 'w', zipfile.ZIP_DEFLATED) as o:
    for it in z.infolist():
        if it.filename in old:
            continue
        if it.filename == 'classes.dex':
            o.writestr(it, dex)
        elif it.filename == 'AndroidManifest.xml':
            o.writestr(it, man)
        else:
            o.writestr(it, z.read(it.filename))
PY

if [ ! -f "$KS" ]; then
    echo "首次构建，生成本地签名密钥（仅存本机，勿提交）"
    keytool -genkeypair -keystore "$KS" -storepass "$KS_PASS" -keypass "$KS_PASS" \
        -alias varvara -keyalg RSA -keysize 2048 -validity 10000 \
        -dname "CN=Varvara Patched, O=Local, C=CN" >/dev/null 2>&1
fi

zipalign -p -f 4 unsigned.apk aligned.apk
apksigner sign --ks "$KS" --ks-pass "pass:$KS_PASS" --ks-key-alias varvara \
    --out "$OUTPATH" aligned.apk
apksigner verify "$OUTPATH"

echo ""
echo "=== 完成 ==="
echo "输出: $OUTPATH"
ls -l "$OUTPATH" | awk '{print "大小: " $5 " 字节"}'
sha256sum "$OUTPATH"

echo ""
echo "安装前注意:"
echo "  1. 签名与原版不同，需卸载原版，或用核心逆向覆盖"
echo "  2. 控制中心磁贴需在下拉面板的编辑界面手动添加"
