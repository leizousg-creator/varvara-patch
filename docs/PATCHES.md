# 补丁定位与验证

本文件记录每一处修改在原版 0.1.152 中的确切位置，供上游更新后重新定位。
类名是 R8 混淆产物（`ch1`、`d51`、`hv0`、`yq1`、`pn0`、`iv0`），**上游重新编译后这些名字会变**，定位时以行为特征为准，不要依赖类名。

---

## 1. ANDROID_ID 上报头

**行为**：读 `Settings.Secure "android_id"`，塞进请求头 `X-Varvara-Id`，挂在通用 HTTP 发送函数上。

**定位**：
```sh
grep -rn 'X-Varvara-Id' smali/
```
应只有一处 `const-string` 声明，其后若干行内跟一条
`invoke-virtual {v3, v4, v2}, Ljava/net/URLConnection;->setRequestProperty(...)`。

**修改**：删除那条 `setRequestProperty`。

**验证**：`grep -c 'X-Varvara-Id'` 仍为 1（声明保留），但发送调用数为 0。

---

## 2. `/v1/advice` 遥测

**行为**：构造 JSON（`country`/`asn`/`mcc_mnc`/`net`）POST 到第三方服务器。

**定位**：
```sh
grep -rn '"/v1/advice"' smali/
```
所在方法签名形如 `public static h(Landroid/content/Context;Ld51;)V`。

**修改**：整个方法体替换为 `return-void`。

**验证**：方法体只剩 `.registers 2` + `return-void`。

---

## 3. 内嵌私有 CA

**行为**：从 `res/raw` 读一张自签证书，建**空** KeyStore 只装这一张证书，生成 `SSLSocketFactory` 并 `setSSLSocketFactory` 到每个 HTTPS 连接。等于所有 TLS 只信任该私有 CA。

**定位**：
```sh
grep -rn 'setSSLSocketFactory\|Lch1;->q(' smali/
```
无条件调用点形如：
`invoke-static {p0, v3}, Lch1;->q(Landroid/content/Context;Ljavax/net/ssl/HttpsURLConnection;)V`

**修改**：注释掉该调用，改用系统证书链。

**验证**：运行时日志不再出现 `Trust anchor for certification path not found`。

---

## 4. 默认服务器指向作者域名

**行为**：`d51.i()` 读 SharedPreferences 的 `servers` 键，为空时回落作者域名。

**定位**：
```sh
grep -rn '"servers"' smali/ | grep getString
```

**修改**：读取键名改为 `servers_patched_off`，使读取恒为 null，必然走默认 Cloudflare 分支。

**注意**：不要只改默认值——已安装过的用户配置里存着旧域名，改默认值不生效。

**验证**：`grep -rn '26cm.monster' smali/` 无结果。

---

## 5. 封锁对照探测数组

**行为**：三个分组（对照被封站点 / 普通站点 / 特定服务）合并后逐个探测，用于判断「整体受限」还是「部分开放」。

**定位**：
```sh
grep -rn 'filled-new-array' smali/hv0.smali
```
第一组原为 4 元素（含一个新闻站点），组内必须全部不可达才判定为整体封锁。

**修改**：把该组改回 3 元素 `{v2, v3, v0}`（移除被替换项）。

**注意**：曾经尝试把该目标换成 `example.org`，结果它永远可达，导致判定逻辑认为「这组没被封」，进而把个别站点失败误报为「部分开放」。**这一组不能放可达域名**。

**验证**：连接后顶部状态栏不出现「部分开放」提示。

---

## 6. 自动更新检查

**行为**：请求 GitHub releases API 比对版本。

**定位**：
```sh
grep -rn 'api.github.com/repos/warpgen' smali/
```

**修改**：URL 改为 `https://127.0.0.1:1/...`，请求必失败。

**验证**：日志出现 `update: check failed`，UI 无更新提示。

---

## 7. 控制中心磁贴

**新增内容**：
- `com/varvara/vpn/VarvaraTileService.smali` — TileService 实现
- `com/varvara/vpn/VarvaraTileService$b.smali` — 状态轮询 Runnable
- 清单注入 `<service>` 声明

**磁贴逻辑**：
- `onClick`：先翻转磁贴状态并刷新（乐观更新，避免等待隧道建立造成延迟），再向 `VarvaraVpnService` 发 `start` / `stop`
- `d()`：读 `tun0` 是否存在，同步真实状态与图标
- `b()`：每 2 秒回读一次，最多 4 次

**图标**：代码绘制（96×96 Bitmap，圆环 + V）。原版所有图片资源（`varvara_off`/`varvara_on`/`ic_launcher_foreground`）都是同一张 1024×1024 彩色插画，QS 只取 alpha 剪影后会变成纯白圆，因此不用资源改用绘制。

**清单注入方式**：直接改 AXML 二进制（字符串池 UTF-16，追加 3 个字符串，插入 4 个节点），不依赖 aapt2。注意字符串池 size 必须 4 字节对齐，否则 `apktool` 解码报 `Stream advanced past chunk end`。

**smali 限制**：`Canvas.drawLine(FFFF Paint)` 需要 6 个寄存器参数，超过普通 `invoke` 的 5 个上限，必须用 `invoke-virtual/range` 且寄存器连续排列。

**验证**：
```sh
dumpsys package com.varvara.vpn | grep VarvaraTileService
logcat -d | grep -i "addPackageTilesOnBgThread"
```
应能看到 `label = 瓦尔瓦拉`。
