import asyncio
import websockets
import json
from websockets.exceptions import ConnectionClosedError, WebSocketException
import platform

if platform.system() == "Windows":
    import ctypes
    from ctypes import wintypes

    user32 = ctypes.WinDLL("user32", use_last_error=True)
    KEYEVENTF_EXTENDEDKEY = 0x1
    KEYEVENTF_KEYUP = 0x2
    VK_CAPITAL = 0x14
    CAPSLOCK_SCANCODE = 0x45

    user32.GetKeyState.restype = wintypes.SHORT
    user32.GetKeyState.argtypes = [wintypes.INT]

    user32.keybd_event.argtypes = [
        wintypes.BYTE,
        wintypes.BYTE,
        wintypes.DWORD,
        wintypes.ULONG,
    ]
    user32.keybd_event.restype = None

    def get_capslock_state():
        return bool(user32.GetKeyState(VK_CAPITAL) & 1)

    def toggle_capslock():
        user32.keybd_event(VK_CAPITAL, CAPSLOCK_SCANCODE, KEYEVENTF_EXTENDEDKEY, 0)
        user32.keybd_event(
            VK_CAPITAL, CAPSLOCK_SCANCODE, KEYEVENTF_EXTENDEDKEY | KEYEVENTF_KEYUP, 0
        )

    def set_capslock_state(enabled):
        current = get_capslock_state()
        if current != enabled:
            toggle_capslock()

else:
    raise NotImplementedError(f"Unsupported platform: {platform.system()}")


async def get_latest_message(websocket):
    count = 0
    max_count = 50
    last = None
    while True:
        if count >= max_count:
            return last
        try:
            last = await asyncio.wait_for(websocket.recv(), timeout=0.005)
        except asyncio.TimeoutError:
            return last
        count += 1


async def run_client():
    uri = "wss://notso-global-capslock-production.up.railway.app/ws"

    async with websockets.connect(uri) as websocket:
        print("connected")
        last_state = False
        while True:
            current_state = get_capslock_state()

            if current_state != last_state:
                message = "1" if current_state else "0"
                print(f"CHANGED {last_state} => {current_state}")
                await websocket.send(message)
                last_state = current_state
            else:
                try:
                    data = await get_latest_message(websocket)
                    if data == "1" and current_state == False:
                        set_capslock_state(True)
                        current_state = True
                        last_state = True
                    elif data == "0" and current_state == True:
                        set_capslock_state(False)
                        current_state = False
                        last_state = False
                    elif data == "0" or data == "1":
                        # consistent
                        pass
                    elif data is None:
                        # no update
                        pass
                    else:
                        print(f"ignoring invalid data...")
                except asyncio.TimeoutError as e:
                    pass

            try:
                await asyncio.sleep(0.05)
            except Exception as e:
                print(e)
                return


async def run_client_loop():
    while True:
        try:
            await run_client()
        except (KeyboardInterrupt, asyncio.CancelledError):
            print("\nExiting.")
            return
        except (
            OSError,
            ConnectionClosedError,
            WebSocketException,
            ConnectionResetError,
        ) as e:
            print(f"Error talking to server: {e}. Sleeping and trying again...")
            await asyncio.sleep(2)


if __name__ == "__main__":
    asyncio.run(run_client_loop())
