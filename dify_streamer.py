import requests
import json

class DifyStreamer:
    def __init__(self, api_key, base_url="http://paytonai/v1"):
        self.api_key = api_key
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        })

    def generate_stream(self, prompt, model_params=None):
        url = f"{self.base_url}/chat-messages"
        data = {
            "inputs": {},
            "query": prompt,
            "response_mode": "streaming",  # 关键参数：启用流式输出
            "user": "user-identifier"
        }
        
        if model_params:
            data.update(model_params)

        try:
            with self.session.post(url, json=data, stream=True) as response:
                response.raise_for_status()
                for line in response.iter_lines():
                    if line:
                        decoded_line = line.decode('utf-8')
                        if decoded_line.startswith("data:"):
                            try:
                                content = json.loads(decoded_line[5:])
                                yield content.get('answer', '') if isinstance(content, dict) else decoded_line
                            except json.JSONDecodeError:
                                yield decoded_line
        except requests.exceptions.RequestException as e:
            print(f"请求失败: {str(e)}")

# 使用示例
if __name__ == "__main__":
    API_KEY = "app-sxEYZam8yt0pSlFDswfzn4aS"
    streamer = DifyStreamer(API_KEY)
    
    prompt = "你是谁"
    model_params = {
        "temperature": 0.7,
        "max_tokens": 5000
    }
    
    print("AI正在思考：")
    for chunk in streamer.generate_stream(prompt, model_params):
        print(chunk, end="", flush=True)
    print("\n回答完成")


