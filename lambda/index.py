# lambda/index.py
import json
import os
# import boto3
import re  # 正規表現モジュールをインポート
# from botocore.exceptions import ClientError
import urllib.request
import urllib.parse
import urllib.error

# Lambda コンテキストからリージョンを抽出する関数
def extract_region_from_arn(arn):
    # ARN 形式: arn:aws:lambda:region:account-id:function:function-name
    match = re.search('arn:aws:lambda:([^:]+):', arn)
    if match:
        return match.group(1)
    return "us-east-1"  # デフォルト値

# グローバル変数としてクライアントを初期化（初期値）
# bedrock_client = None

# モデルID
# MODEL_ID = os.environ.get("MODEL_ID", "us.amazon.nova-lite-v1:0")

FASTAPI_ENDPOINT_URL = os.environ.get("FASTAPI_ENDPOINT_URL" = "https://b084-34-125-172-224.ngrok-free.app")

def lambda_handler(event, context):
    try:
        if not FASTAPI_ENDPOINT_URL:
            raise ValueError("Environment variable FASTAPI_ENDPOINT_URL is not set.")

        # コンテキストから実行リージョンを取得し、クライアントを初期化
        # global bedrock_client
        # if bedrock_client is None:
        #     region = extract_region_from_arn(context.invoked_function_arn)
        #     bedrock_client = boto3.client('bedrock-runtime', region_name=region)
        #     print(f"Initialized Bedrock client in region: {region}")
        
        print("Received event:", json.dumps(event))
        
        # Cognitoで認証されたユーザー情報を取得
        user_info = None
        if 'requestContext' in event and 'authorizer' in event['requestContext']:
            user_info = event['requestContext']['authorizer']['claims']
            print(f"Authenticated user: {user_info.get('email') or user_info.get('cognito:username')}")
        
        # リクエストボディの解析
        body = json.loads(event['body'])
        message = body['message']
        conversation_history = body.get('conversationHistory', [])
        
        print("Processing message:", message)
        # print("Using model:", MODEL_ID)

        # ------------modified------------
        
        # FASTAPI用のリクエストペイロード構築
        request_payload_dict = {
            "message": message,
            "conversationHistory": conversation_history
            
        # JSON文字列に変換、UTF-8でエンコード
        request_payload_bytes = json.dumps(request_payload_dict).encode('utf-8')
        
        # ログメッセージ
        print(f"Calling FastAPI endpoint ({FASTAPI_ENDPOINT_URL}) with payload:", json.dumps(request_payload_dict))
        
        # FASTAPIのエンドポイント呼び出し
        req = urllib.request.Request(
            FASTAPI_ENDPOINT_URL,
            data=request_payload_bytes,
            method='POST',
            headers={'Content-Type': 'application/json'}
        )

        response_body = None
        
        # API呼び出し、エラー処理
        try:
            # タイムアウトを設定 (20秒)
            with urllib.request.urlopen(req, timeout=20) as http_response:
                # ステータスコードチェック
                status_code = http_response.getcode()
                print(f"FastAPI response status code: {status_code}")
                if status_code >= 400:
                    # エラーレスポンスの内容をログに出力試行
                    error_content_bytes = http_response.read()
                    error_content_str = error_content_bytes.decode('utf-8', errors='ignore')
                    print(f"FastAPI error response body: {error_content_str}")
                    raise urllib.error.HTTPError(FASTAPI_ENDPOINT_URL, status_code, f"FastAPI request failed with status {status_code}", http_response.headers, http_response)

                # レスポンスボディを読み込み、デコード
                response_body_bytes = http_response.read()
                response_body_str = response_body_bytes.decode('utf-8')
                # JSONとしてパース
                response_body = json.loads(response_body_str)
        except urllib.error.HTTPError as e:
            # FastAPIサーバーからのエラーレスポンス (4xx, 5xx)
            error_content = e.read().decode('utf-8', errors='ignore') if hasattr(e, 'read') else str(e)
            print(f"HTTP Error calling FastAPI endpoint: {e.code} {e.reason} - {error_content}")
            raise Exception(f"FastAPI API error: {e.code} - {error_content}") from e
        except urllib.error.URLError as e:
            # ネットワークエラー (タイムアウト、名前解決エラーなど)
            print(f"URL Error calling FastAPI endpoint: {e.reason}")
            raise Exception(f"Failed to connect to the FastAPI API: {e.reason}") from e
        except json.JSONDecodeError as e:
            # FastAPIからのレスポンスがJSON形式でない場合
            print(f"Failed to decode JSON response from FastAPI: {e}")
            print(f"Raw response: {response_body_str if 'response_body_str' in locals() else 'N/A'}")
            raise Exception(f"Invalid JSON response received from FastAPI API.") from e
        except Exception as e:
             # その他の予期せぬエラー (タイムアウト含む socket.timeout)
             print(f"Error during FastAPI call: {type(e).__name__} - {e}")
             raise Exception(f"An unexpected error occurred when calling the FastAPI API: {e}") from e
        
        # # 会話履歴を使用
        # messages = conversation_history.copy()
        
        # # ユーザーメッセージを追加
        # messages.append({
        #     "role": "user",
        #     "content": message
        # })
        
        # # Nova Liteモデル用のリクエストペイロードを構築
        # # 会話履歴を含める
        # bedrock_messages = []
        # for msg in messages:
        #     if msg["role"] == "user":
        #         bedrock_messages.append({
        #             "role": "user",
        #             "content": [{"text": msg["content"]}]
        #         })
        #     elif msg["role"] == "assistant":
        #         bedrock_messages.append({
        #             "role": "assistant", 
        #             "content": [{"text": msg["content"]}]
        #         })
        
        # # invoke_model用のリクエストペイロード
        # request_payload = {
        #     "messages": bedrock_messages,
        #     "inferenceConfig": {
        #         "maxTokens": 512,
        #         "stopSequences": [],
        #         "temperature": 0.7,
        #         "topP": 0.9
        #     }
        # }
        # ------------modified------------
        
        # print("Calling Bedrock invoke_model API with payload:", json.dumps(request_payload))
        
        # # invoke_model APIを呼び出し
        # response = bedrock_client.invoke_model(
        #     modelId=MODEL_ID,
        #     body=json.dumps(request_payload),
        #     contentType="application/json"
        # )
        
        # # レスポンスを解析
        # response_body = json.loads(response['body'].read())
        # print("Bedrock response:", json.dumps(response_body, default=str))

        # ログメッセージ
        print("FastAPI response:", json.dumps(response_body))

        # 応答の検証
        # if not response_body.get('output') or not response_body['output'].get('message') or not response_body['output']['message'].get('content'):
        #     raise Exception("No response content from the model")
                if not isinstance(response_body, dict) or 'response' not in response_body:
                    print(f"Invalid or unexpected response format from FastAPI: {response_body}")
                    raise Exception("Invalid response format received from the FastAPI API (expected a JSON object with a 'response' key).")

        # アシスタントの応答を取得
        assistant_response = response_body['response']
        
        # アシスタントの応答を会話履歴に追加
        messages.append({
            "role": "assistant",
            "content": assistant_response
        })
        
        # 成功レスポンスの返却
        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
                "Access-Control-Allow-Methods": "OPTIONS,POST"
            },
            "body": json.dumps({
                "success": True,
                "response": assistant_response,
                "conversationHistory": messages
            })
        }
        
    except Exception as error:
        print("Error:", str(error))
        
        return {
            "statusCode": 500,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
                "Access-Control-Allow-Methods": "OPTIONS,POST"
            },
            "body": json.dumps({
                "success": False,
                "error": str(error)
            })
        }
