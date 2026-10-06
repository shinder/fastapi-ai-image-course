"""H03：用 WebSocket 把攝影機影格串到後端做即時偵測（教材 附錄 D）

端點：WS /api/v1/hands/ws
對應頁面：app/static/demos/H03-hands-ws.html；流程與設計取捨見 docs/H03-hands-ws.md

跟 H02（POST 單張圖，routes/hands.py）的差別在於「連線是持續的」，所以多了三件事要處理：
連線數上限、每條連線的資源生命週期、以及塞車時要怎麼辦。

塞車（backpressure，回壓）主要在前端解決——前端同時只讓一格在路上飛，
收到上一格的結果才送下一格。詳見 H03-hands-ws.html 裡的說明。
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from fastapi.concurrency import run_in_threadpool
from PIL import Image as PILImage

from app.config import settings
from app.services.hand_stream import HandStreamSession

router = APIRouter(prefix="/api/v1/hands", tags=["hands-ws"])

# 目前連著幾條。這個計數器不必上鎖：asyncio 是單執行緒的，
# 下面「檢查 → 加一」中間沒有任何 await，不會被其他協程插隊。
# （run_in_threadpool 那種真的會跑到別的執行緒的呼叫才需要小心）
_active_connections = 0


@router.websocket("/ws")
async def hands_ws(websocket: WebSocket):
    """用戶端送 binary 的 JPEG 影格，伺服器每收一格回一則 JSON 結果。

    為什麼送 binary 而不是 base64 的字串：
    base64 會讓體積多 33%，兩邊還要各多一次編解碼。
    WebSocket 本來就支援二進位訊框，沒有理由再包一層。
    """
    global _active_connections

    # 先 accept 再判斷連線數，是為了能送一則看得懂的訊息給前端。
    # 若在 accept 前就 close，瀏覽器只會拿到一個沒有原因的握手失敗
    await websocket.accept()

    if _active_connections >= settings.HAND_WS_MAX_CONN:
        await websocket.send_json(
            {
                "type": "error",
                "message": f"連線數已達上限（{settings.HAND_WS_MAX_CONN}），請稍後再試",
            }
        )
        # 1008 = policy violation，語意上就是「你沒違反協定，但我不接受」
        await websocket.close(code=1008)
        return

    _active_connections += 1
    session: HandStreamSession | None = None

    try:
        # 建 detector 是阻塞的（行程內第一次要初始化 GL，約 170 ms），
        # 不丟 threadpool 的話這段時間整個伺服器的其他請求都會被卡住
        try:
            session = await run_in_threadpool(HandStreamSession)
        except ImportError:
            # 優雅降級：mediapipe 是可選依賴，沒裝時只有這條連線被拒絕，app 照常運作
            # （對照 routes/hands.py 的 503；WebSocket 沒有狀態碼，改用訊息 + 關閉碼）
            await websocket.send_json(
                {
                    "type": "error",
                    "message": "尚未安裝 mediapipe，請先執行：uv sync --extra mediapipe 再重啟服務",
                }
            )
            await websocket.close(code=1011)  # 1011 = 伺服器端出了狀況
            return
        except FileNotFoundError:
            await websocket.send_json(
                {
                    "type": "error",
                    "message": "找不到手部模型檔，請先執行：uv run python scripts/download_models.py",
                }
            )
            await websocket.close(code=1011)
            return

        # 告訴前端可以開始送影格了。前端要等這則訊息，
        # 不然第一格會在 detector 還沒建好時就送到，白白排隊
        await websocket.send_json(
            {
                "type": "ready",
                "max_connections": settings.HAND_WS_MAX_CONN,
                "active_connections": _active_connections,
            }
        )

        while True:
            # 用 receive() 而不是 receive_bytes()：
            # receive_bytes() 遇到文字訊框會丟 KeyError、遇到斷線也要另外處理，
            # 直接看原始訊息比較清楚，也順便示範 ASGI 的訊息長什麼樣子
            message = await websocket.receive()

            if message["type"] == "websocket.disconnect":
                break

            frame = message.get("bytes")
            if frame is None:
                # 不是二進位訊框就不是影格（例如前端送了 ping 之類的文字），略過
                continue

            try:
                result = await run_in_threadpool(session.detect, frame)
            except (OSError, PILImage.DecompressionBombError) as exc:
                # 單一格解碼失敗不必斷線，回報一下繼續等下一格
                await websocket.send_json({"type": "error", "message": f"無法解析影格：{exc}"})
                continue

            await websocket.send_json({"type": "result", **result})

    except WebSocketDisconnect:
        # 使用者關掉分頁、按了停止，都會走到這裡，不是錯誤
        pass
    finally:
        # 不論怎麼結束，detector 一定要關掉、名額一定要還回去。
        # 少了這段，斷線幾次之後就再也連不進來了
        _active_connections -= 1
        if session is not None:
            await run_in_threadpool(session.close)
