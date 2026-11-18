.class public Lcom/varvara/vpn/VarvaraTileService;
.super Landroid/service/quicksettings/TileService;
.source "VarvaraTileService.java"


# direct methods
.method public constructor <init>()V
    .locals 0

    invoke-direct {p0}, Landroid/service/quicksettings/TileService;-><init>()V

    return-void
.end method


# 生成磁贴图标：圆环 + V
.method private e()Landroid/graphics/drawable/Icon;
    .locals 1

    # 使用资源图标：varvara_off 的 alpha 剪影
    const v0, 0x7f060014

    invoke-static {p0, v0}, Landroid/graphics/drawable/Icon;->createWithResource(Landroid/content/Context;I)Landroid/graphics/drawable/Icon;

    move-result-object v0

    return-object v0
.end method


# 判断 tun0 是否已建立
.method private b()Z
    .locals 3

    :try_start_0
    const-string v0, "tun0"

    invoke-static {v0}, Ljava/net/NetworkInterface;->getByName(Ljava/lang/String;)Ljava/net/NetworkInterface;

    move-result-object v0

    if-eqz v0, :cond_0

    invoke-virtual {v0}, Ljava/net/NetworkInterface;->isUp()Z

    move-result v1

    return v1

    :cond_0
    :try_end_0
    .catch Ljava/lang/Exception; {:try_start_0 .. :try_end_0} :catch_0

    goto :goto_0

    :catch_0
    move-exception v0

    :goto_0
    const/4 v1, 0x0

    return v1
.end method


.method public d()V
    .locals 4

    invoke-virtual {p0}, Landroid/service/quicksettings/TileService;->getQsTile()Landroid/service/quicksettings/Tile;

    move-result-object v0

    if-nez v0, :cond_0

    return-void

    :cond_0
    invoke-direct {p0}, Lcom/varvara/vpn/VarvaraTileService;->b()Z

    move-result v1

    if-eqz v1, :cond_1

    const/4 v2, 0x2

    goto :goto_0

    :cond_1
    const/4 v2, 0x1

    :goto_0
    invoke-virtual {v0, v2}, Landroid/service/quicksettings/Tile;->setState(I)V

    invoke-direct {p0}, Lcom/varvara/vpn/VarvaraTileService;->e()Landroid/graphics/drawable/Icon;

    move-result-object v3

    invoke-virtual {v0, v3}, Landroid/service/quicksettings/Tile;->setIcon(Landroid/graphics/drawable/Icon;)V

    invoke-virtual {v0}, Landroid/service/quicksettings/Tile;->updateTile()V

    return-void
.end method


.method public onClick()V
    .locals 7

    invoke-direct {p0}, Lcom/varvara/vpn/VarvaraTileService;->b()Z

    move-result v0

    invoke-virtual {p0}, Landroid/service/quicksettings/TileService;->getQsTile()Landroid/service/quicksettings/Tile;

    move-result-object v1

    if-eqz v1, :cond_0

    if-eqz v0, :cond_1

    const/4 v2, 0x1

    goto :goto_0

    :cond_1
    const/4 v2, 0x2

    :goto_0
    invoke-virtual {v1, v2}, Landroid/service/quicksettings/Tile;->setState(I)V

    invoke-direct {p0}, Lcom/varvara/vpn/VarvaraTileService;->e()Landroid/graphics/drawable/Icon;

    move-result-object v3

    invoke-virtual {v1, v3}, Landroid/service/quicksettings/Tile;->setIcon(Landroid/graphics/drawable/Icon;)V

    invoke-virtual {v1}, Landroid/service/quicksettings/Tile;->updateTile()V

    :cond_0
    new-instance v1, Landroid/content/Intent;

    const-class v2, Lcom/varvara/vpn/VarvaraVpnService;

    invoke-direct {v1, p0, v2}, Landroid/content/Intent;-><init>(Landroid/content/Context;Ljava/lang/Class;)V

    if-eqz v0, :cond_2

    const-string v2, "stop"

    goto :goto_1

    :cond_2
    const-string v2, "start"

    :goto_1
    invoke-virtual {v1, v2}, Landroid/content/Intent;->setAction(Ljava/lang/String;)Landroid/content/Intent;

    invoke-virtual {p0, v1}, Landroid/content/Context;->startForegroundService(Landroid/content/Intent;)Landroid/content/ComponentName;

    new-instance v1, Lcom/varvara/vpn/VarvaraTileService$b;

    invoke-direct {v1, p0}, Lcom/varvara/vpn/VarvaraTileService$b;-><init>(Lcom/varvara/vpn/VarvaraTileService;)V

    invoke-static {}, Landroid/os/Looper;->getMainLooper()Landroid/os/Looper;

    move-result-object v2

    new-instance v3, Landroid/os/Handler;

    invoke-direct {v3, v2}, Landroid/os/Handler;-><init>(Landroid/os/Looper;)V

    const-wide/16 v4, 0x7d0

    invoke-virtual {v3, v1, v4, v5}, Landroid/os/Handler;->postDelayed(Ljava/lang/Runnable;J)Z

    return-void
.end method


.method public onStartListening()V
    .locals 0

    invoke-virtual {p0}, Lcom/varvara/vpn/VarvaraTileService;->d()V

    return-void
.end method
