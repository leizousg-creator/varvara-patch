.class final Lcom/varvara/vpn/VarvaraTileService$b;
.super Ljava/lang/Object;
.implements Ljava/lang/Runnable;

.source "VarvaraTileService.java"


# instance fields
.field final a:Lcom/varvara/vpn/VarvaraTileService;

.field b:I


# direct methods
.method constructor <init>(Lcom/varvara/vpn/VarvaraTileService;)V
    .locals 1

    iput-object p1, p0, Lcom/varvara/vpn/VarvaraTileService$b;->a:Lcom/varvara/vpn/VarvaraTileService;

    const/4 v0, 0x0

    iput v0, p0, Lcom/varvara/vpn/VarvaraTileService$b;->b:I

    invoke-direct {p0}, Ljava/lang/Object;-><init>()V

    return-void
.end method


# virtual methods
.method public run()V
    .locals 6

    iget-object v0, p0, Lcom/varvara/vpn/VarvaraTileService$b;->a:Lcom/varvara/vpn/VarvaraTileService;

    invoke-virtual {v0}, Lcom/varvara/vpn/VarvaraTileService;->d()V

    iget v1, p0, Lcom/varvara/vpn/VarvaraTileService$b;->b:I

    add-int/lit8 v1, v1, 0x1

    iput v1, p0, Lcom/varvara/vpn/VarvaraTileService$b;->b:I

    const/4 v0, 0x4

    if-ge v1, v0, :cond_0

    invoke-static {}, Landroid/os/Looper;->getMainLooper()Landroid/os/Looper;

    move-result-object v0

    new-instance v2, Landroid/os/Handler;

    invoke-direct {v2, v0}, Landroid/os/Handler;-><init>(Landroid/os/Looper;)V

    const-wide/16 v3, 0x7d0

    invoke-virtual {v2, p0, v3, v4}, Landroid/os/Handler;->postDelayed(Ljava/lang/Runnable;J)Z

    :cond_0
    return-void
.end method
