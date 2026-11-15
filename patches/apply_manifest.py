#!/usr/bin/env python3
"""
向二进制 AndroidManifest.xml 注入控制中心磁贴的 <service> 声明。

不依赖 aapt2 —— 直接操作 AXML 二进制结构：
字符串池追加（UTF-16）、元素节点插入、4 字节对齐。

用法: apply_manifest.py <原 AndroidManifest.xml> <输出路径>
"""

import os
import struct
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tools"))
import axml  # noqa: E402

SERVICE_CLASS = "com.varvara.vpn.VarvaraTileService"
PERM_TILE = "android.permission.BIND_QUICK_SETTINGS_TILE"
ACTION_QS = "android.service.quicksettings.action.QS_TILE"
ICON_ID = 0x7F060014  # drawable/varvara_off


def fail(msg):
    print(f"\n[失败] {msg}", file=sys.stderr)
    sys.exit(1)


def enc16(s):
    """UTF-16 字符串池条目：长度 + UTF-16LE + 终止符"""
    return struct.pack("<H", len(s)) + s.encode("utf-16-le") + b"\x00\x00"


def attr(ns, name, raw, dtype, data):
    return struct.pack("<IIIHBBI", ns, name, raw, 8, 0, dtype, data)


def start_elem(name, attrs, line=0):
    body = struct.pack("<IIHHHHHH", 0xFFFFFFFF, name, 20, 20, len(attrs), 0, 0, 0)
    a = b"".join(attrs)
    size = 16 + 20 + len(a)
    return (struct.pack("<HHI", 0x0102, 16, size)
            + struct.pack("<II", line, 0xFFFFFFFF) + body + a)


def end_elem(name, line=0):
    return (struct.pack("<HHI", 0x0103, 16, 24)
            + struct.pack("<II", line, 0xFFFFFFFF)
            + struct.pack("<II", 0xFFFFFFFF, name))


def main():
    if len(sys.argv) != 3:
        print("用法: apply_manifest.py <in.xml> <out.xml>", file=sys.stderr)
        sys.exit(2)
    src, dst = sys.argv[1], sys.argv[2]

    b = open(src, "rb").read()
    nodes, pool = axml.walk(b)
    if pool is None:
        fail("未能解析字符串池")

    need = ["name", "permission", "exported", "icon", "service", "intent-filter", "action"]
    idx = {}
    for k in need:
        if k not in pool.strs:
            fail(f"字符串池缺少 '{k}'，上游清单结构已变化")
        idx[k] = pool.strs.index(k)

    uri = "http://schemas.android.com/apk/res/android"
    if uri not in pool.strs:
        fail("缺少 android 命名空间 URI")
    uri_i = pool.strs.index(uri)

    base = pool.count
    cls_i, perm_i, qs_i = base, base + 1, base + 2

    attrs = [
        attr(uri_i, idx["name"], cls_i, 0x03, cls_i),
        attr(uri_i, idx["permission"], perm_i, 0x03, perm_i),
        attr(uri_i, idx["exported"], 0xFFFFFFFF, 0x12, 1),
        attr(uri_i, idx["icon"], 0xFFFFFFFF, 0x01, ICON_ID),
    ]

    block = start_elem(idx["service"], attrs)
    block += start_elem(idx["intent-filter"], [])
    block += start_elem(idx["action"], [attr(uri_i, idx["name"], qs_i, 0x03, qs_i)])
    block += end_elem(idx["action"])
    block += end_elem(idx["intent-filter"])
    block += end_elem(idx["service"])

    # 重建字符串池（追加新字符串 + 4 字节对齐）
    data_start = pool.off + pool.strstart
    data_end = pool.off + pool.size
    old_data = b[data_start:data_end]
    appended = b"".join(enc16(s) for s in (SERVICE_CLASS, PERM_TILE, ACTION_QS))

    new_offsets = list(pool.offsets)
    off = len(old_data)
    for s in (SERVICE_CLASS, PERM_TILE, ACTION_QS):
        new_offsets.append(off)
        off += len(enc16(s))

    new_data = old_data + appended
    new_count = base + 3
    raw_size = 28 + new_count * 4 + len(new_data)
    new_size = (raw_size + 3) & ~3
    new_data += b"\x00" * (new_size - raw_size)
    new_strstart = 28 + new_count * 4

    pool_bytes = struct.pack("<HHI", 0x0001, 28, new_size)
    pool_bytes += struct.pack("<IIIII", new_count, pool.styc, pool.flags, new_strstart, 0)
    pool_bytes += b"".join(struct.pack("<I", o) for o in new_offsets)
    pool_bytes += new_data

    insert_at = None
    for n in nodes:
        if n[0] == "END" and n[3] == "application":
            insert_at = n[1]
    if insert_at is None:
        fail("未找到 <application> 结束节点")

    out = b[:8] + pool_bytes + b[8 + pool.size:insert_at] + block + b[insert_at:]
    out = struct.pack("<HHI", 0x0003, 8, len(out)) + out[8:]

    # 自检
    vnodes, vpool = axml.walk(out)
    found = [n for n in vnodes if n[0] == "START" and n[3] == "service"]
    if not found:
        fail("自检失败：注入后找不到 service 节点")

    open(dst, "wb").write(out)
    print(f"清单注入完成: {len(b)} -> {len(out)} 字节, 字符串 {pool.count} -> {new_count}")


if __name__ == "__main__":
    main()
