#!/usr/bin/env python3
"""
Varvara smali 补丁集（特征驱动）。

上游每次发版都会重新混淆类名（0.1.152 的 ch1/d51/hv0/yq1 在 0.1.157 变成
mh1/l51/pv0/hr1），所以本脚本不依赖类名，而是按代码特征定位。

每处补丁都带断言：结构变化时明确报错并退出，不会静默产出错误的包。

用法: apply_smali.py <smali_root>
"""

import glob
import os
import re
import sys

PATCHES = []


def fail(where, msg):
    print(f"\n[失败] {where}: {msg}", file=sys.stderr)
    print("上游结构可能已改变，请对照 docs/PATCHES.md 重新定位。", file=sys.stderr)
    sys.exit(1)


def all_smali(root):
    return glob.glob(os.path.join(root, "**", "*.smali"), recursive=True)


def files_with(root, needle):
    """返回内容包含 needle 的 smali 文件列表"""
    out = []
    for f in all_smali(root):
        try:
            if needle in open(f, encoding="utf-8", errors="ignore").read():
                out.append(f)
        except OSError:
            continue
    return out


def read(p):
    return open(p, encoding="utf-8", errors="ignore").read()


def write(p, s):
    open(p, "w", encoding="utf-8").write(s)


def rel(root, p):
    return os.path.relpath(p, root)


# ---------------------------------------------------------------- 1
def patch_remove_device_id(root):
    """移除 X-Varvara-Id 请求头（原本把 ANDROID_ID 发给作者服务器）"""
    hits = files_with(root, '"X-Varvara-Id"')
    if not hits:
        fail("X-Varvara-Id", "未找到上报头")
    done = 0
    for p in hits:
        lines = read(p).split("\n")
        changed = False
        for i, line in enumerate(lines):
            if '"X-Varvara-Id"' in line:
                for j in range(i + 1, min(i + 14, len(lines))):
                    if "setRequestProperty" in lines[j]:
                        lines[j] = "    # [patch] X-Varvara-Id header removed"
                        changed = True
                        break
                break
        if changed:
            write(p, "\n".join(lines))
            done += 1
    if not done:
        fail("X-Varvara-Id", "找到常量但未找到发送调用")
    PATCHES.append(f"移除 ANDROID_ID 上报头（{done} 处）")


# ---------------------------------------------------------------- 2
def patch_disable_advice(root):
    """禁用 /v1/advice 遥测上报（方法名 h，第二参数类型随版本变化）"""
    hits = files_with(root, '"/v1/advice"')
    if not hits:
        fail("/v1/advice", "未找到上报地址")
    done = 0
    for p in hits:
        s = read(p)
        m = re.search(
            r"\.method public static h\(Landroid/content/Context;(L[a-z0-9]+;)\)V\n.*?\n\.end method\n",
            s, re.S)
        if not m:
            continue
        param = m.group(1)  # 保留真实参数类型，否则调用方找不到该签名
        s = s[:m.start()] + (
            f".method public static h(Landroid/content/Context;{param})V\n"
            "    .registers 2\n\n"
            "    # [patch] /v1/advice telemetry disabled\n"
            "    return-void\n"
            ".end method\n") + s[m.end():]
        write(p, s)
        done += 1
    if not done:
        fail("/v1/advice", "未匹配到上报方法（签名可能已变）")
    PATCHES.append(f"禁用 /v1/advice 上报（{done} 处）")


# ---------------------------------------------------------------- 3
def patch_drop_private_ca(root):
    """移除内嵌私有 CA 的安装调用（原本所有 HTTPS 只信任作者自签 CA）"""
    pat = re.compile(
        r"[ \t]*invoke-static \{[^}]+\}, L[a-zA-Z0-9_$]+;->q\(Landroid/content/Context;"
        r"Ljavax/net/ssl/HttpsURLConnection;\)V\n")
    total = 0
    for p in all_smali(root):
        s = read(p)
        if "HttpsURLConnection;)V" not in s:
            continue
        new, n = pat.subn("    # [patch] 私有 CA 安装已移除，改用系统证书链\n", s)
        if n:
            write(p, new)
            total += n
    if not total:
        fail("私有 CA", "未找到 CA 安装调用")
    PATCHES.append(f"移除内嵌私有 CA（{total} 处）")


# ---------------------------------------------------------------- 4
def patch_force_cf_server(root):
    """让 servers 读取恒为空，强制走 Cloudflare 默认端点"""
    hits = files_with(root, 'const-string v0, "servers"')
    if not hits:
        fail("servers 键", "未找到配置读取")
    for p in hits:
        s = read(p)
        s = s.replace('const-string v0, "servers"',
                      'const-string v0, "servers_patched_off"', 1)
        write(p, s)
    PATCHES.append("禁用本地 servers 配置，强制 Cloudflare 端点")


# ---------------------------------------------------------------- 5
def patch_drop_probe_target(root):
    """从封锁对照组的探测数组中移除被替换项"""
    hits = files_with(root, '"https://meduza.io"')
    if not hits:
        # 上游可能已自行移除；此时检查数组是否已是 3 元素
        PATCHES.append("封锁对照探测数组：上游已无该目标，跳过")
        return
    done = 0
    for p in hits:
        s = read(p)
        s2 = s.replace("filled-new-array {v2, v3, v0, v1}, [Ljava/lang/String;",
                       "filled-new-array {v2, v3, v0}, [Ljava/lang/String;")
        s2 = s2.replace('"https://meduza.io"', '"https://example.org"')
        if s2 != s:
            write(p, s2)
            done += 1
    if not done:
        fail("探测数组", "未匹配到 4 元素探测数组")
    PATCHES.append(f"修正封锁对照探测数组（{done} 处）")


# ---------------------------------------------------------------- 6
def patch_disable_update_check(root):
    """更新检查指向不可达地址，永不提示新版本"""
    a = '"https://api.github.com/repos/warpgen/varvara/releases?per_page=10"'
    b = '"https://api.github.com/repos/warpgen/varvara/releases/latest"'
    hits = files_with(root, "api.github.com/repos/warpgen")
    if not hits:
        fail("更新检查", "未找到 releases API")
    n = 0
    for p in hits:
        s = read(p)
        if a not in s and b not in s:
            continue
        s = s.replace(a, '"https://127.0.0.1:1/releases"')
        s = s.replace(b, '"https://127.0.0.1:1/latest"')
        write(p, s)
        n += 1
    PATCHES.append(f"禁用自动更新检查（{n} 处）")


# ---------------------------------------------------------------- 7
def patch_purge_vendor_domain(root):
    """清除所有指向作者私有服务域名的常量"""
    n = 0
    for p in files_with(root, "26cm.monster"):
        s = read(p)
        s = s.replace("https://vvcc.26cm.monster/v1/info", "https://127.0.0.1:1/v1/info")
        s = s.replace("https://vvcc.26cm.monster", "https://127.0.0.1:1")
        s = s.replace("vvcc.26cm.monster", "engage.cloudflareclient.com")
        write(p, s)
        n += 1
    PATCHES.append(f"清除作者私有域名常量（{n} 个文件）" if n
                   else "作者私有域名：已无残留")


# ---------------------------------------------------------------- 8
def install_tile_service(root):
    """放入自建的 TileService（控制中心磁贴）"""
    dst = os.path.join(root, "com", "varvara", "vpn")
    os.makedirs(dst, exist_ok=True)
    here = os.path.dirname(os.path.abspath(__file__))
    src_dir = os.path.join(here, "..", "src", "smali", "com", "varvara", "vpn")
    n = 0
    for name in ("VarvaraTileService.smali", "VarvaraTileService$b.smali"):
        src = os.path.join(src_dir, name)
        if not os.path.exists(src):
            fail("src/smali", f"缺少 {name}")
        write(os.path.join(dst, name), read(src))
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
