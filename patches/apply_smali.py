#!/usr/bin/env python3
"""
Varvara smali 补丁集。

对 baksmali 反编译输出应用全部修改。每处补丁都带断言：
上游结构一旦变化，脚本会明确指出是哪一处失效，而不是静默产出一个错误的包。

用法: apply_smali.py <smali_root>
"""

import glob
import os
import re
import sys

PATCHES = []


def fail(where, msg):
    print(f"\n[失败] {where}: {msg}", file=sys.stderr)
    print("上游结构可能已改变，请检查该处后再更新本脚本。", file=sys.stderr)
    sys.exit(1)


def read(root, name):
    p = os.path.join(root, name)
    if not os.path.exists(p):
        fail(name, "文件不存在")
    return p, open(p, encoding="utf-8").read()


def write(p, s):
    open(p, "w", encoding="utf-8").write(s)


# ---------------------------------------------------------------- 1
def patch_remove_device_id(root):
    """移除 X-Varvara-Id 请求头（原本把 ANDROID_ID 发给作者服务器）"""
    p, s = read(root, "ch1.smali")
    lines = s.split("\n")
    hit = False
    for i, line in enumerate(lines):
        if '"X-Varvara-Id"' in line:
            for j in range(i + 1, min(i + 12, len(lines))):
                if "setRequestProperty" in lines[j]:
                    lines[j] = "    # [patch] X-Varvara-Id header removed"
                    hit = True
                    break
            break
    if not hit:
        fail("ch1.smali / X-Varvara-Id", "未找到发送点")
    write(p, "\n".join(lines))
    PATCHES.append("移除 ANDROID_ID 上报头 (X-Varvara-Id)")


# ---------------------------------------------------------------- 2
def patch_disable_advice(root):
    """禁用 /v1/advice 遥测上报"""
    p, s = read(root, "ch1.smali")
    m = re.search(
        r"\.method public static h\(Landroid/content/Context;Ld51;\)V\n.*?\n\.end method\n",
        s, re.S)
    if not m:
        fail("ch1.smali / h()", "未找到 advice 上报方法")
    s = s[:m.start()] + (
        ".method public static h(Landroid/content/Context;Ld51;)V\n"
        "    .registers 2\n\n"
        "    # [patch] /v1/advice telemetry disabled\n"
        "    return-void\n"
        ".end method\n") + s[m.end():]
    write(p, s)
    PATCHES.append("禁用 /v1/advice 上报")


# ---------------------------------------------------------------- 3
def patch_drop_private_ca(root):
    """移除内嵌私有 CA 的无条件安装（原本所有 HTTPS 只信任作者 CA）"""
    p, s = read(root, "ch1.smali")
    lines = s.split("\n")
    hit = False
    for i, line in enumerate(lines):
        if "Lch1;->q(Landroid/content/Context;Ljavax/net/ssl/HttpsURLConnection;)V" in line:
            lines[i] = "    # [patch] 私有 CA 已移除，改用系统证书链"
            hit = True
            break
    if not hit:
        fail("ch1.smali / ch1.q()", "未找到私有 CA 安装调用")
    write(p, "\n".join(lines))
    PATCHES.append("移除内嵌私有 CA（改用系统证书链）")


# ---------------------------------------------------------------- 4
def patch_force_cf_server(root):
    """让 servers 读取恒为空，强制走 Cloudflare 默认端点"""
    p, s = read(root, "d51.smali")
    if 'const-string v0, "servers"' not in s:
        fail("d51.smali / servers", "未找到 servers 读取键")
    s = s.replace('const-string v0, "servers"', 'const-string v0, "servers_patched_off"', 1)
    write(p, s)
    PATCHES.append("禁用本地 servers 配置，强制 Cloudflare 端点")


# ---------------------------------------------------------------- 5
def patch_drop_probe_target(root):
    """从封锁对照组的探测数组中移除被替换项，恢复 3 元素"""
    p, s = read(root, "hv0.smali")
    old = "filled-new-array {v2, v3, v0, v1}, [Ljava/lang/String;"
    new = "filled-new-array {v2, v3, v0}, [Ljava/lang/String;"
    if s.count(old) != 1:
        fail("hv0.smali / 探测数组", f"期望 1 处，实际 {s.count(old)} 处")
    s = s.replace(old, new)
    write(p, s)
    PATCHES.append("修正封锁对照组探测数组（移除多余项）")


# ---------------------------------------------------------------- 6
def patch_disable_update_check(root):
    """更新检查指向不可达地址，永不提示新版本"""
    p, s = read(root, "yq1.smali")
    a = '"https://api.github.com/repos/warpgen/varvara/releases?per_page=10"'
    b = '"https://api.github.com/repos/warpgen/varvara/releases/latest"'
    if a not in s and b not in s:
        fail("yq1.smali / 更新检查", "未找到 releases API 地址")
    s = s.replace(a, '"https://127.0.0.1:1/releases"')
    s = s.replace(b, '"https://127.0.0.1:1/latest"')
    write(p, s)
    PATCHES.append("禁用自动更新检查")


# ---------------------------------------------------------------- 7
def patch_purge_vendor_domain(root):
    """清除所有指向作者私有服务域名的常量（死代码一并处理）"""
    n = 0
    for f in glob.glob(os.path.join(root, "**", "*.smali"), recursive=True):
        s = open(f, encoding="utf-8").read()
        if "26cm.monster" in s:
            s = s.replace("https://vvcc.26cm.monster/v1/info", "https://127.0.0.1:1/v1/info")
            s = s.replace("https://vvcc.26cm.monster", "https://127.0.0.1:1")
            s = s.replace("vvcc.26cm.monster", "engage.cloudflareclient.com")
            write(f, s)
            n += 1
    if n == 0:
        PATCHES.append("作者私有域名：已无残留")
    else:
        PATCHES.append(f"清除作者私有域名常量（{n} 个文件）")


# ---------------------------------------------------------------- 8
def install_tile_service(root):
    """放入自建的 TileService（控制中心磁贴）"""
    dst_dir = os.path.join(root, "com", "varvara", "vpn")
    os.makedirs(dst_dir, exist_ok=True)
    here = os.path.dirname(os.path.abspath(__file__))
    src_dir = os.path.join(here, "..", "src", "smali", "com", "varvara", "vpn")
    n = 0
    for name in ("VarvaraTileService.smali", "VarvaraTileService$b.smali"):
        src = os.path.join(src_dir, name)
        if not os.path.exists(src):
            fail("src/smali", f"缺少 {name}")
        open(os.path.join(dst_dir, name), "w", encoding="utf-8").write(
            open(src, encoding="utf-8").read())
        n += 1
    PATCHES.append(f"加入控制中心磁贴类（{n} 个）")


def main():
    if len(sys.argv) != 2:
        print("用法: apply_smali.py <smali_root>", file=sys.stderr)
        sys.exit(2)
    root = sys.argv[1]
    if not os.path.isdir(root):
        print(f"目录不存在: {root}", file=sys.stderr)
        sys.exit(2)

    patch_remove_device_id(root)
    patch_disable_advice(root)
    patch_drop_private_ca(root)
    patch_force_cf_server(root)
    patch_drop_probe_target(root)
    patch_disable_update_check(root)
    patch_purge_vendor_domain(root)
    install_tile_service(root)

    print(f"\n共应用 {len(PATCHES)} 项:")
    for i, p in enumerate(PATCHES, 1):
        print(f"  {i}. {p}")


if __name__ == "__main__":
    main()
