# client.py
from ndn.app import NDNApp
from ndn.encoding import Name
from ndn.types import InterestNack, InterestTimeout
import asyncio
import json
import base64

app = NDNApp()

MY_PREFIX = "/client/A/notify"
SERVER_TARGET = "/server/compute"
PROXY_NAME = "/proxy/notify"

@app.route(MY_PREFIX)
def on_notification(name, param, app_param): #app_paramはapplication parameters
    print(f"\n[Client] PUSH通知を受信！ Name: {Name.to_str(name)}", flush=True)
    if app_param:
        msg = bytes(app_param).decode('utf-8')
        print(f"[Client] エラー内容: {msg}", flush=True)
    # Interestの名前(name)に対してDataを作成してネットワークに流す
    app.put_data(name, content=b'ACK from Client', freshness_period=1000)
    print("[Client] Ack(Data)を返信しました", flush=True)

async def main():
    print("[Client] NFD準備中 (3秒待機)...", flush=True)
    await asyncio.sleep(3)

    print(f"[Client] 計算要求を送信します: {SERVER_TARGET}", flush=True)

    token = base64.urlsafe_b64encode(b"client/A").decode().rstrip('=') #client/Aを隠蔽
    
    params = {
        "proxy": PROXY_NAME, #エラー時に送るプロキシ
        "token": token #その時はこのタグ付けて
    }
    params_bytes = json.dumps(params).encode('utf-8') #パケットに載せれるバイナリデータにする

    try:
        await app.express_interest(
            SERVER_TARGET, 
            app_param=params_bytes,
            must_be_fresh=True, 
            can_be_prefix=True, 
            lifetime=2000
        )
        print("[Client] データ受信（計算成功）", flush=True)

    except InterestTimeout:
        print("[Client] Interestタイムアウト（正常動作：身元は隠したままエラー通知を待ちます）", flush=True)
    except Exception as e:
        print(f"[Client] エラー: {e}", flush=True)

if __name__ == '__main__':
    app.run_forever(after_start=main())