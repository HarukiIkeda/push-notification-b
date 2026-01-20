from ndn.app import NDNApp
from ndn.encoding import Name
import asyncio
import json

app = NDNApp()

LISTEN_PREFIX = "/server/compute"

@app.route(LISTEN_PREFIX)
def on_interest(name, param, app_param): #nameはinterestの名前
    print(f"[Server] リクエスト受信: {Name.to_str(name)}", flush=True) #Name.to_str(nameで人間が読める形に変換)

    if not app_param:
        print("[Server] パラメータがないので無視します", flush=True) #空っぽのinterest来たら無視
        return

    try:
        # 中身を取り出す
        params_json = bytes(app_param).decode('utf-8') #app_paramはプロキシとかトークンとか
        params = json.loads(params_json)
        
        target_proxy = params.get("proxy") #paramsのproxy成分だけを取り出す
        token = params.get("token")
        
        print(f"[Server] 指示解読: Proxy='{target_proxy}', Token='{token}'", flush=True)
        print("[Server] 計算エラー発生！ 指示通りに通知します", flush=True)

        asyncio.create_task(send_notification(target_proxy, token)) #asyncioで非同期に通知を送る

    except Exception as e:
        print(f"[Server] パラメータ解析失敗: {e}", flush=True)

async def send_notification(proxy_name, token):
    # 通知先を作成: /proxy/notify / <token>
    target = f"{proxy_name}/{token}"
    
    print(f"[Server] プロキシへ通知送信: {target}", flush=True)
    
    try:
        # 戻り値を受け取る (data_name, meta_info, content)
        _, _, content = await app.express_interest(
            target,
            app_param=b'Error: Zero Division Detected',
            must_be_fresh=True,
            can_be_prefix=False,
            lifetime=1000
        )
        # ここに来る＝ProxyからAckが返ってきた
        ack_msg = bytes(content).decode('utf-8')
        print(f"[Server] 通知成功！ ProxyからAck受信: {ack_msg}", flush=True)
    except Exception as e:
        print(f"[Server] 送信失敗エラー: {e}", flush=True)

if __name__ == '__main__':
    print(f"[Server] 起動中... 待ち受け: {LISTEN_PREFIX}", flush=True)
    app.run_forever()