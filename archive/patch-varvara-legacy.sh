#!/bin/bash
# Varvara 去上报补丁（dex 级修改，不依赖 aapt2）
# 用法: ./patch-varvara.sh <原始.apk> [输出.apk]
# 依赖: baksmali smali zipalign apksigner keytool
set -euo pipefail

IN="${1:?用法: $0 <原始.apk> [输出.apk]}"
OUT="${2:-Varvara-patched.apk}"
KS="/workspace/varvara-patch.keystore"
KSPASS="varvara123"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

[ -f "$KS" ] || keytool -genkeypair -keystore "$KS" -storepass "$KSPASS" -keypass "$KSPASS" \
  -alias varvara -keyalg RSA -keysize 2048 -validity 10000 -dname "CN=Varvara Patched, O=LocalLab, C=CN"

echo "[1/6] 解出 classes.dex"
cd "$WORK" && unzip -q "$(realpath "$IN")" classes.dex

echo "[2/6] baksmali"
baksmali d classes.dex -o smali

echo "[3/6] 打补丁"
python3 - <<'PY'
import re, glob

p='smali/ch1.smali'
lines=open(p,encoding='utf-8').read().split('\n')
hit=False
for i,l in enumerate(lines):
    if '"X-Varvara-Id"' in l:
        for j in range(i+1,min(i+12,len(lines))):
            if 'setRequestProperty' in lines[j]:
                lines[j]='    # [patch] X-Varvara-Id header removed'
                hit=True; break
        break
assert hit, 'X-Varvara-Id 发送点未找到（上游结构可能已变）'
s='\n'.join(lines)

m=re.search(r'\.method public static h\(Landroid/content/Context;Ld51;\)V\n.*?\n\.end method\n', s, re.S)
assert m, 'h() 未找到'
s=s[:m.start()]+'.method public static h(Landroid/content/Context;Ld51;)V\n    .registers 2\n\n    return-void\n.end method\n'+s[m.end():]
open(p,'w',encoding='utf-8').write(s)

p='smali/d51.smali'
s=open(p,encoding='utf-8').read()
s=s.replace('const-string p0, "vvcc.26cm.monster"','const-string p0, "engage.cloudflareclient.com"')
open(p,'w',encoding='utf-8').write(s)

p='smali/hv0.smali'
s=open(p,encoding='utf-8').read()
s=s.replace('"https://meduza.io"','"https://example.org"')
open(p,'w',encoding='utf-8').write(s)

for f in glob.glob('smali*/**/*.smali', recursive=True):
    s=open(f,encoding='utf-8').read()
    if '26cm.monster' in s:
        s=s.replace('https://vvcc.26cm.monster/v1/info','https://127.0.0.1:1/v1/info')
        s=s.replace('https://vvcc.26cm.monster','https://127.0.0.1:1')
        s=s.replace('vvcc.26cm.monster','engage.cloudflareclient.com')
        open(f,'w',encoding='utf-8').write(s)
print('patch applied')
PY

echo "[4/6] smali 汇编"
smali a smali -o classes_patched.dex

echo "[5/6] 替换 dex 并删旧签名"
python3 - "$(realpath "$IN")" "$WORK/classes_patched.dex" <<'PY'
import sys, zipfile
src, newdex = sys.argv[1], open(sys.argv[2],'rb').read()
old={'META-INF/CERT.SF','META-INF/CERT.RSA','META-INF/MANIFEST.MF'}
with zipfile.ZipFile(src) as z, zipfile.ZipFile('unsigned.apk','w',zipfile.ZIP_DEFLATED) as o:
    for it in z.infolist():
        if it.filename in old: continue
        o.writestr(it, newdex if it.filename=='classes.dex' else z.read(it.filename))
PY

echo "[6/6] 对齐 + 签名"
zipalign -p -f 4 unsigned.apk aligned.apk
apksigner sign --ks "$KS" --ks-pass "pass:$KSPASS" --ks-key-alias varvara --out "$OUT" aligned.apk
apksigner verify "$OUT"
echo "完成: $OUT"
echo "注意: 签名已变，安装前必须卸载原版: pm uninstall com.varvara.vpn"
