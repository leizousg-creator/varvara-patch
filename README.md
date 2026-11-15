# varvara-patch

对 [warpgen/varvara](https://github.com/warpgen/varvara)（Android Cloudflare WARP 客户端）的重打包补丁集。

这个仓库**只包含补丁代码与构建脚本**，不包含、也不再分发原版 APK。构建时请自行从上游 Release 下载原版 APK。

## 它做了什么

原版是一个闭源发布的 APK，其中包含若干会向作者自建服务上报数据、以及强制信任作者私有 CA 的逻辑。本补丁集在 dex 与二进制清单层面做最小修改：

| # | 修改 | 原因 |
|---|---|---|
| 1 | 移除 `X-Varvara-Id` 请求头 | 原版把 `ANDROID_ID` 发给作者服务器 |
| 2 | 禁用 `/v1/advice` 上报 | 原版向第三方服务器 POST 运营商代码 / ASN / 国家 |
| 3 | 移除内嵌私有 CA | 原版让所有 HTTPS 只信任作者自签 CA，导致连接任何公共站点都失败 |
| 4 | 强制使用 Cloudflare 端点 | 原版默认服务器指向作者自建域名 |
| 5 | 修正封锁对照探测数组 | 原版探测目标含特定新闻站点，且数组长度参与判定 |
| 6 | 禁用自动更新检查 | 避免被上游推送覆盖掉我们的签名版本 |
| 7 | 加入控制中心磁贴 | 原版没有 QS Tile，只能进 App 开关 |

修改点在 dex 与 `AndroidManifest.xml`（AXML 二进制）上，不触碰资源表，因此不需要 `aapt2`。

## 构建

### 依赖

```sh
# Debian / Ubuntu
apt install python3 openjdk-17-jre-headless zipalign apksigner
# smali / baksmali 3.x
```

`baksmali`、`smali`、`aapt2` 之外的 Android 工具由 `apksigner` / `zipalign` 提供。

### 步骤

```sh
# 1. 下载原版 APK（从上游 Release 页）
#    https://github.com/warpgen/varvara/releases

# 2. 构建
./build.sh Varvara-0.1.152.apk

# 输出: Varvara-patched.apk
```

首次构建会在仓库根目录生成 `signing.keystore`（口令默认 `varvara-local`，可用环境变量 `KS_PASS` 覆盖）。**这个文件必须本地保管，不要提交**——`.gitignore` 已排除。

### 安装

签名与原版不同，因此：

- 常规做法：`pm uninstall com.varvara.vpn` 后再装（会丢配置）
- 有核心逆向（CorePatch 类模块）：可直接 `pm install -r` 覆盖，数据保留

安装后控制中心磁贴需要手动添加：**下拉控制中心 → 编辑 → 找到「瓦尔瓦拉」→ 拖到上方**。

## 目录结构

```
build.sh                    一键构建
patches/
  apply_smali.py            dex 层补丁（7 项，含断言）
  apply_manifest.py         二进制清单注入（不依赖 aapt2）
tools/
  axml.py                   AXML 解析器
src/smali/com/varvara/vpn/
  VarvaraTileService.smali  控制中心磁贴
  VarvaraTileService$b.smali 状态轮询
docs/
  PATCHES.md                每处补丁的定位方法与验证方式
```

## 上游更新时

补丁依赖具体的类名与方法结构（例如 `ch1.h()`、`d51.i()`）。上游若重构代码，`apply_smali.py` 会在对应位置报错并退出，**不会静默产出错误的包**。

适配流程：

1. 跑一次 `build.sh`，看它停在哪一项
2. 对照 `docs/PATCHES.md` 里的定位方法，在新版本里找对应位置
3. 更新 `apply_smali.py` 中的匹配条件

## 风险与边界

- 补丁只影响「数据外发」与「证书信任」，**不改变 WARP 本身的网络性能**。从中国大陆接入通常固定落到 LAX，延迟与速度不会有改善。
- 原版是闭源软件，本仓库的修改基于对 0.1.152 的静态分析。上游可以在任何版本引入补丁未覆盖的新行为。
- 构建产物与原版行为存在差异，自行承担使用风险。

## 许可

本仓库中的补丁代码与脚本为原创。原版 APK 的版权归其作者所有，本仓库不包含其任何二进制内容。
