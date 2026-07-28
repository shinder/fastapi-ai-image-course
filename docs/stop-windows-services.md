# Windows：停用／恢復原生服務（PostgreSQL、MongoDB、Redis）

本專案的資料庫一律用 Docker 容器跑（`cmd-start-postgres.bat`、`cmd-start-mongodb.bat`、`cmd-start-redis.bat`）。
如果你的 Windows 上**另外**用安裝程式裝過 PostgreSQL、MongoDB 之類的服務，它們預設是「開機自動啟動」，
會先佔走 5432 / 27017 / 6379 這些埠號，導致容器起不來或連錯資料庫。

處理方式有兩條路，先決定要走哪一條：

| 情境 | 做法 |
| --- | --- |
| 平常不會用到原生安裝的那套 | **停掉服務 + 關掉開機自動啟動**（本文主軸） |
| 原生那套還要留著用 | 改容器的對外埠號，例如 `-p 5433:5432`，並同步改 `.env` 的 `DATABASE_URL` |

停用服務只是「不讓它跑」，不會刪掉任何資料；隨時可以照最後一節改回來。

---

## 0. 先開一個系統管理員的終端機

停止服務、改啟動類型都需要系統管理員權限，**查詢**則不用。

- Win + X → 「終端機（系統管理員）」或「Windows PowerShell（系統管理員）」
- 舊版 Windows：開始功能表搜尋 `powershell` → 右鍵 →「以系統管理員身分執行」

沒有管理員權限時，指令會報 `拒絕存取` / `Access is denied`（見疑難排解）。

---

## 1. 確認是誰佔用了埠號

先確定問題真的出在原生服務，而不是先前忘了關的容器。

**PowerShell**

```powershell
# 5432 換成你要查的埠號（MongoDB 27017、Redis 6379）
Get-Process -Id (Get-NetTCPConnection -LocalPort 5432 -State Listen).OwningProcess
```

**cmd**

```cmd
rem 最後一欄是 PID，再拿 PID 去查行程名稱
netstat -ano | findstr :5432
tasklist /fi "pid eq 1234"
```

看行程名稱判斷：

- `postgres.exe`、`mongod.exe`、`memurai.exe` → 是原生安裝的服務，繼續往下做。
- `com.docker.backend.exe`、`wslrelay.exe`、`vpnkit.exe` → 是 Docker 在轉發，代表已經有容器
  佔著這個埠號，用 `docker ps` 看是哪一個，或直接 `cmd-stop-containers.bat`。

---

## 2. 找出服務名稱

服務有 **`Name`（服務名稱）** 和 **`DisplayName`（顯示名稱）** 兩種，指令請一律用 `Name`——
`DisplayName` 含空白和連字號，容易打錯。

```powershell
Get-Service | Where-Object { $_.Name -like "*postgres*" }
```

輸出大致像這樣（`Status` 是目前狀態，`Name` 才是要拿去用的）：

```
Status   Name               DisplayName
------   ----               -----------
Running  postgresql-x64-17  postgresql-x64-17 - PostgreSQL Server 17
```

常見的預設 `Name`：

| 軟體 | 服務名稱 | 埠號 |
| --- | --- | --- |
| PostgreSQL 17 | `postgresql-x64-17` | 5432 |
| MongoDB Community | `MongoDB` | 27017 |
| Memurai（Windows 上的 Redis 相容品） | `Memurai` | 6379 |
| MySQL 8 | `MySQL80` | 3306 |

版本號會跟著安裝版本走（PostgreSQL 16 就是 `postgresql-x64-16`），安裝時若改過名稱也可能不同，
所以請以上面 `Get-Service` 查到的為準。

---

## 3. 停止服務（只停這一次）

**PowerShell**

```powershell
Stop-Service postgresql-x64-17
```

**cmd**

```cmd
net stop postgresql-x64-17
```

停完確認一下狀態，順便看埠號有沒有真的放開：

```powershell
Get-Service postgresql-x64-17
Get-NetTCPConnection -LocalPort 5432 -State Listen -ErrorAction SilentlyContinue
```

第二行沒有輸出就代表埠號空了，可以去跑 `cmd-start-postgres.bat`。

要再啟動就把 `Stop-Service` 換成 `Start-Service`（cmd 是 `net start`），
`Restart-Service` 則是停了再起。

> 注意：這只停「這一次」。重開機後服務會照原本的啟動類型自己起來，所以才有下一節。

---

## 4. 開機自動啟動：關掉與恢復

服務的「啟動類型（StartupType）」決定它開機時的行為，共四種：

| 啟動類型 | 意義 |
| --- | --- |
| `Automatic` | 開機時自動啟動（安裝完的預設值） |
| `Automatic (Delayed Start)` | 開機自動啟動，但延後到登入後才跑，減輕開機負擔 |
| `Manual` | 開機不啟動，但你隨時可以手動 `Start-Service`，其他服務也能依賴它把它拉起來 |
| `Disabled` | 完全停用，連手動啟動都會被拒絕，必須先改回 `Manual` 或 `Automatic` |

### 查目前的啟動類型

```powershell
Get-Service postgresql-x64-17 | Select-Object Name, Status, StartType
```

或用 `sc.exe`（`START_TYPE` 那行：`2` 是自動、`3` 是手動、`4` 是停用）：

```powershell
sc.exe qc postgresql-x64-17
```

### 關掉開機自動啟動

建議改成 `Manual` 而不是 `Disabled`——偶爾想用原生那套時，`Manual` 直接 `Start-Service` 就好。

```powershell
# 一次做完：改成手動啟動，並停掉目前正在跑的
Set-Service postgresql-x64-17 -StartupType Manual
Stop-Service postgresql-x64-17
```

要完全封死（確定不會再用，或要防止其他程式把它拉起來）：

```powershell
Set-Service postgresql-x64-17 -StartupType Disabled -Status Stopped
```

cmd 沒有 `Set-Service`，改用 `sc.exe`。**`start=` 後面一定要有一個空白、等號前面不能有空白**，
這是 `sc.exe` 的怪規矩，寫錯只會得到一段用法說明：

```cmd
sc config postgresql-x64-17 start= demand
net stop postgresql-x64-17
```

`start=` 可填 `auto`（自動）、`delayed-auto`（延遲自動）、`demand`（手動）、`disabled`（停用）。

> 在 **PowerShell** 裡請寫 `sc.exe`，不要只寫 `sc`——`sc` 是 `Set-Content` 的別名，
> 會變成在建檔案。在 cmd 裡則寫 `sc` 即可。

### 恢復成開機自動啟動

```powershell
Set-Service postgresql-x64-17 -StartupType Automatic
Start-Service postgresql-x64-17
```

想恢復成「延遲自動」的話，Windows 內建的 PowerShell 5.1 其 `Set-Service` 不支援這個選項
（PowerShell 7 才有 `AutomaticDelayedStart`），用 `sc.exe` 最保險：

```powershell
sc.exe config postgresql-x64-17 start= delayed-auto
```

恢復前記得先把 Docker 容器停掉（`cmd-stop-containers.bat`），否則兩邊搶同一個埠號，
後起來的那個會失敗。

---

## 5. GUI 方式（services.msc）

不想記指令的話：

1. Win + R → 輸入 `services.msc` → Enter。
2. 找到「postgresql-x64-17 - PostgreSQL Server 17」。
3. 右鍵 →「停止」可停這一次。
4. 右鍵 →「內容」→「啟動類型」下拉選「手動」或「已停用」→「套用」，這才是關掉開機自動啟動。

「內容」視窗裡的「服務名稱」就是前面說的 `Name`，「相依性」分頁可以看哪些服務依賴它。

---

## 6. 疑難排解

**`拒絕存取` / `Access is denied` / `服務無法啟動`**

終端機沒有管理員權限，回第 0 節重開一個。

**`找不到指定的服務` / `Cannot find any service with service name`**

服務名稱打錯，或這台機器根本沒裝。回第 2 節用 `Get-Service` 查清楚。

**停止時卡住、逾時**

多半是還有連線沒斷（pgAdmin、DBeaver、你自己的程式）。先關掉那些工具再停一次。
真的停不掉，可以用 PostgreSQL 自帶的 `pg_ctl` 強制一點（路徑依實際安裝版本調整）：

```cmd
"C:\Program Files\PostgreSQL\17\bin\pg_ctl.exe" -D "C:\Program Files\PostgreSQL\17\data" -m fast stop
```

`-m fast` 會中斷現有連線並回復未完成的交易；`-m immediate` 更粗暴，下次啟動要跑 crash
recovery，一般不建議。這是最後手段——正常情況請用 `Stop-Service`，讓服務管理員知道它被停了，
不然服務狀態會跟實際情況對不起來。

**有相依服務擋著**

```powershell
Stop-Service postgresql-x64-17 -Force
```

`-Force` 會連同依賴它的服務一起停掉。

**改成 `Disabled` 後啟動失敗**

這是預期行為，`Disabled` 連手動啟動都不允許。先 `Set-Service ... -StartupType Manual` 再啟動。

---

## 7. 快速對照

以 PostgreSQL 17 為例，其他服務把名稱換掉即可：

```powershell
# 讓 Docker 容器接手：關掉自動啟動並停止服務
Set-Service postgresql-x64-17 -StartupType Manual
Stop-Service postgresql-x64-17

# 改回原生服務：先停容器，再恢復自動啟動
# （在專案目錄執行 cmd-stop-containers.bat）
Set-Service postgresql-x64-17 -StartupType Automatic
Start-Service postgresql-x64-17

# 隨時查狀態
Get-Service postgresql-x64-17 | Select-Object Name, Status, StartType
```
