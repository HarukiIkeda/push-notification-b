from ndn.app import NDNApp
from ndn.encoding import Name, Component
import asyncio
import json

app = NDNApp()

LISTEN_PREFIX_COMPUTE = "/server/compute"
LISTEN_PREFIX_FETCH = "/server/fetch"

# 計算結果を保存しておく場所, IDをキーにして計算結果を保存する: {"d538cbb9": "Result...42"}
results_store = {}

@app.route(LISTEN_PREFIX_COMPUTE)
def on_compute_request(name, param, app_param):
    print(f"[Server] 計算リクエスト受信: {Name.to_str(name)}", flush=True)

    if not app_param:
        return
    
    # ★非同期処理（計算＋通知）をここから別タスクとして起動する
    asyncio.create_task(process_compute(name, app_param))

async def process_compute(name, app_param):
    try:
        params_json = bytes(app_param).decode('utf-8') #app_paramはプロキシとかトークンとか
        params = json.loads(params_json)
        
        target_proxy = params.get("proxy") #paramsのproxy成分だけを取り出す
        token = params.get("token")
        tx_id = params.get("id")
        
        print(f"[Server] 受付: ID='{tx_id}', Proxy='{target_proxy}'", flush=True)

        print(f"[Server] 計算処理を開始", flush=True)
        await asyncio.sleep(4)

        # 計算完了をシミュレートして保存
        calculation_result = f"Result_of_{tx_id}_is_XXX"
        results_store[tx_id] = calculation_result
        print(f"[Server] 計算完了。結果を保存しました: {calculation_result}", flush=True)
        #「終わった」という通知を裏で送る
        # 計算と通信を同時に行うため、非同期タスクとして実行
        asyncio.create_task(send_notification(target_proxy, token, tx_id))

    except Exception as e:
        print(f"[Server] パラメータ解析失敗: {e}", flush=True)

#Clientから「ID:〇〇の結果をください」と言われたときに動く関数
@app.route(LISTEN_PREFIX_FETCH)
def on_fetch_request(name, param, app_param): #nameにinterestのフルネームが入ってる（id含む）
    # name構造: /server/fetch / <tx_id>
    print(f"[Server] 結果取得リクエスト受信: {Name.to_str(name)}", flush=True)
    
    #idが入ってる成分探す
    tx_id_comp = name[-1]
    #もし一番後ろが「自動付与されるハッシュ値」だったら、その1つ前がID
    if Component.get_type(tx_id_comp) == Component.TYPE_PARAMETERS_SHA256:
         tx_id_comp = name[-2]
         
    #コンポーネントの「中身(Value)」だけを正確に取り出す
    # bytes(comp) だとヘッダ(Type/Length)が含まれてしまうので get_value を使う
    tx_id = bytes(Component.get_value(tx_id_comp)).decode('utf-8')
    
    # 保存された結果を探す
    result_data = results_store.get(tx_id)
    
    if result_data:
        print(f"[Server] 結果を返信します: {result_data}", flush=True)
        app.put_data(name, content=result_data.encode('utf-8'), freshness_period=1000) #結果の入ったDataパケット返す
    else:
        # デバッグ用に repr() を使って見えない文字も表示する
        print(f"[Server] エラー: 指定されたIDの結果が見つかりません ID={repr(tx_id)}", flush=True)
        print(f"[Server] 現在の保存リスト: {list(results_store.keys())}", flush=True)

async def send_notification(proxy_name, token, tx_id):
    target = f"{proxy_name}/{token}"
    print(f"[Server] プロキシへ完了通知送信: {target}", flush=True)
    
    fetch_url = f"{LISTEN_PREFIX_FETCH}/{tx_id}"

    notify_payload = {
        "status": "Complete",
        "id": tx_id,
        "fetch_name": fetch_url,
        "message": "Data is ready. Please fetch."
    }
    notify_bytes = json.dumps(notify_payload).encode('utf-8')

    try:
        _, _, content = await app.express_interest(
            target,
            app_param=notify_bytes,
            must_be_fresh=True,
            can_be_prefix=False,
            lifetime=1000
        )
        ack_msg = bytes(content).decode('utf-8')
        print(f"[Server] Proxy経由でAck受信: {ack_msg}", flush=True)
        
    except Exception as e:
        print(f"[Server] 通知送信失敗: {e}", flush=True)

if __name__ == '__main__':
    print(f"[Server] 起動中... (Compute & Fetch)", flush=True)
    app.run_forever()