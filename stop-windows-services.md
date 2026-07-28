# Windows 要如何停掉 postgresql 17 的 service ?

最快的方式是用管理員權限的命令列。PostgreSQL 17 的 Windows 服務名稱預設是 `postgresql-x64-17`。

**PowerShell（以管理員身分執行）**

```powershell
Stop-Service postgresql-x64-17
```

**傳統 cmd（以管理員身分執行）**

```cmd
net stop postgresql-x64-17
```

**先確認服務名稱**（如果上面的名稱不對，例如安裝時改過或是 32 位元版）

```powershell
Get-Service | Where-Object { $_.Name -like "*postgres*" }
```

注意 `Name` 和 `DisplayName` 是兩個不同的東西——`net stop` 兩個都吃，但用 `Name`（`postgresql-x64-17`）比較不會出錯。

**GUI 方式**：Win + R 輸入 `services.msc`，找到「postgresql-x64-17 - PostgreSQL Server 17」，右鍵停止。

**幾個補充**

如果想連開機自動啟動一起關掉（只停一次的話下次重開機還是會起來）:

```powershell
Set-Service postgresql-x64-17 -StartupType Manual
```

要之後再啟動就把 `Stop-Service` 換成 `Start-Service`。

如果停止時卡住或報錯，通常是還有連線沒斷。可以用 `pg_ctl` 強制一點：

```cmd
pg_ctl.exe -D "C:\Program Files\PostgreSQL\17\data" -m fast stop
```

`-m fast` 會中斷現有連線並回復未完成的交易，`-m immediate` 更粗暴（下次啟動要跑 crash recovery），一般不建議。