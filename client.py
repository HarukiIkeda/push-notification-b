# client.py
from ndn.app import NDNApp
from ndn.encoding import Name
from ndn.types import InterestNack, InterestTimeout
import asyncio
import json
import base64
import uuid # ID生成用

app = NDNApp()

MY_PREFIX = "/client/A/notify"
SERVER_TARGET_COMPUTE = "/server/compute" # 計算依頼用
PROXY_NAME = "/proxy/notify"

@app.route(MY_PREFIX)
def on_notification(name, param, app_param):
    print(f"\n[Client] 完了通知を受信 Name: {Name.to_str(name)}", flush=True)
    
    tx_id = "Unknown" #IDを初期化
    if app_param:
        #通知の中身(JSON)からIDを確認
        try:
            msg_bytes = bytes(app_param) # 1. 中身をバイト列として取り出す
            msg_str = msg_bytes.decode('utf-8') # 2. 文字列に変換
            msg_json = json.loads(msg_str) # 3. JSON(辞書)に変換
            tx_id = msg_json.get("id") # 4. "id" タグの中身(例: d538cbb9)を取り出す
            status = msg_json.get("status") # 5. "status" タグの中身(例: Complete)を取り出す
            #print(f"[Client] 通知内容: ID={tx_id}, Status={status}", flush=True)

            fetch_target = msg_json.get("fetch_name") #通知から「受取場所」を取り出す
            print(f"[Client] 通知内容: ID={tx_id}, Status={status}, 場所={fetch_target}", flush=True)

            # 完了通知なら、指定された場所へ取りに行く
            if status == "Complete" and fetch_target:
                asyncio.create_task(fetch_result(fetch_target))
        except:
            print(f"[Client] 解析エラー: {msg_str}", flush=True)

    #IDを含めたAckを返す
    ack_content = f'ACK from Client (ID: {tx_id})'.encode('utf-8')
    app.put_data(name, content=ack_content, freshness_period=1000)
    print(f"[Client] Ackを返信しました: ID={tx_id}", flush=True)

#サーバーへ結果を取りに行く関数
async def fetch_result(target_name):
    print(f"[Client] 結果取得interest送信: ID={target_name}", flush=True)
    # 名前の中にIDを埋め込む: /server/fetch/<tx_id>
    
    try:
        data_name, meta_info, content = await app.express_interest(
            target_name,
            must_be_fresh=True,
            can_be_prefix=False,
            lifetime=2000
        )
        result = bytes(content).decode('utf-8')
        print(f"[Client] 計算結果受信: {result}", flush=True)
    except InterestTimeout:
        print("[Client] 結果取得タイムアウト", flush=True)

async def main():
    #print("[Client] NFD準備中 (3秒待機)...", flush=True)
    await asyncio.sleep(3)

    #Transaction ID (tx_id) を生成
    tx_id = str(uuid.uuid4())[:8] # 長いので先頭8文字だけ使う
    print(f"[Client] 計算要求interestを送信 (ID: {tx_id})", flush=True)

    #client/Aを隠蔽。base64はバイト列返すのでdecodeで文字列に変換し、末尾の=を削る
    token = base64.urlsafe_b64encode(b"client/A").decode().rstrip('=')
    
    params = {
        "proxy": PROXY_NAME,
        "token": token,
        "id": tx_id  # ★リクエストにIDを含める
    }
    params_bytes = json.dumps(params).encode('utf-8') #パケットに載せれるバイナリデータにする

    try:
        await app.express_interest(
            SERVER_TARGET_COMPUTE, 
            app_param=params_bytes,
            must_be_fresh=True, 
            can_be_prefix=True, 
            lifetime=2000
        )
        print("[Client] 計算リクエスト送信完了（通知待ち）", flush=True)

    except InterestTimeout:
        # Dataが返ってこないのは仕様（Serverは通知で返すから）
        print("[Client] PITタイムアウト（正常：通知を待ちます）", flush=True)
    except Exception as e:
        print(f"[Client] エラー: {e}", flush=True)

if __name__ == '__main__':
    app.run_forever(after_start=main())