import urllib.request
import json

webhook_url = "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=df144a52-a6b3-4028-8c4b-d180700bf349"

payload = {
    "msgtype": "news",
    "news": {
       "articles" : [
           {
               "title" : "全體加薪通知",
               "description" : "今年全體加薪安排如下...",
               "url" : "https://txcai.txcaix.com/",
               "picurl" : "https://i-meeting.txcaix.com/imageserver/TXCLogo.jpg"
           }
        ]
    }
}

data = json.dumps(payload).encode('utf-8')
req = urllib.request.Request(webhook_url, data=data, headers={'Content-Type': 'application/json'})

try:
    response = urllib.request.urlopen(req)
    print("Response Status Code:", response.getcode())
    print("Response Body:", response.read().decode('utf-8'))
except Exception as e:
    print("Error:", e)
