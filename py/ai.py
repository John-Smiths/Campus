import requests

def chat_with_robot(question, appid="76e3cc7f38fa40c2ac202e4b4a749b3b", userid=None):
    url = "https://api.sizhi.com/chat"
    params = {
        'appid': appid,
        'spoken': question,
        'userid': userid if userid else 'default_user',  # 如果没有提供userid，则使用默认值
        'stream': False,  # 不使用流方式返回
        'memory': False  # 使用记忆功能
    }
    
    response = requests.post(url, data=params)
    if response.status_code == 200:
        result = response.json()
        if result['status'] == 0:  # 请求成功
            return result['data']['info']['text']
        else:
            return f"Error: {result['message']}"
    else:
        return f"HTTP Error: {response.status_code}"

if __name__ == "__main__":
    appid = "76e3cc7f38fa40c2ac202e4b4a749b3b"
    #answer = chat_with_robot(appid, question)
