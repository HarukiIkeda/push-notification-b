# proxy.py
from ndn.app import NDNApp
from ndn.encoding import Name, Component
import asyncio
import base64

app = NDNApp()

LISTEN_PREFIX = "/proxy/notify"

@app.route(LISTEN_PREFIX) 
def on_notification(name, param, app_param): #nameはinterestの名前だが、NDNの仕様で末尾にparams-sha...が付く
    print(f"[Proxy] 通知受信: {Name.to_str(name)}", flush=True)
    asyncio.create_task(forward_to_client(name, app_param)) #非同期にクライアントへ転送

async def forward_to_client(incoming_name, payload):
    prefix_len = len(Name.from_str(LISTEN_PREFIX)) #自分のプレフィックス(/proxy/notify)が何個の成分か数える
    
    end_index = len(incoming_name)
    if end_index > 0 and Component.get_type(incoming_name[-1]) == Component.TYPE_PARAMETERS_SHA256:
        end_index -= 1
    
    if end_index <= prefix_len:
        print("[Proxy] エラー: トークンが見つかりません", flush=True)
        return

    token_component = incoming_name[prefix_len] #prefix_len番目がtoken
    token_str = bytes(token_component).decode('utf-8') #バイナリを文字列に変換

    try:
        padding = len(token_str) % 4 #クライアント側で=を削ったため、len%4を計算して足りない分だけ=を補完。Base64は文字数が4の倍数である必要がある
        if padding > 0:
            token_str += '=' * (4 - padding)
            
        decoded_name = base64.urlsafe_b64decode(token_str).decode('utf-8') #デコードして元のクライアント名を取得
        print(f"[Proxy] 暗号化されたクライアント名を解読しました クライアント名: {decoded_name}", flush=True)
        
        target = f"/{decoded_name}/notify"
        print(f"[Proxy] 完了通知を転送します 転送先: {target}", flush=True)

        # Interestの結果(Data)を受け取る変数を用意
        data_name, meta_info, content = await app.express_interest(
            target,
            app_param=payload,
            must_be_fresh=True,
            can_be_prefix=False,
            lifetime=1000
        )
        
        ack_msg = bytes(content).decode('utf-8')
        print(f"[Proxy] クライアントからAck受信: {ack_msg}", flush=True)

        #クライアントからのAck内容をそのままサーバーへ転送
        # "ACK from Client (ID: ...)" という内容がそのままサーバーに届く
        app.put_data(incoming_name, content=content, freshness_period=1000)
        print("[Proxy] サーバへAckを転送しました", flush=True)

    except Exception as e:
        print(f"[Proxy] 転送失敗(解読不可): {e}", flush=True)

if __name__ == '__main__':
    print(f"[Proxy] 起動中... 待ち受け: {LISTEN_PREFIX}", flush=True)
    app.run_forever()