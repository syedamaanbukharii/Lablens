import urllib.request
import json
import urllib.error

# register
req1 = urllib.request.Request("https://lablens-api-oisn.onrender.com/api/auth/register", data=json.dumps({"email":"test13@gmail.com", "password":"password123"}).encode(), headers={"Content-Type":"application/json"})
try:
    res1 = urllib.request.urlopen(req1)
    token = json.loads(res1.read())["access_token"]
except urllib.error.HTTPError as e:
    if e.code == 409:
        req_log = urllib.request.Request("https://lablens-api-oisn.onrender.com/api/auth/login", data="username=test13@gmail.com&password=password123".encode(), headers={"Content-Type":"application/x-www-form-urlencoded"})
        res1 = urllib.request.urlopen(req_log)
        token = json.loads(res1.read())["access_token"]
    else:
        print("Register error:", e.read().decode())
        exit(1)
except Exception as e:
    print(e)
    exit(1)

# post upload
boundary = "----WebKitFormBoundary7MA4YWxkTrZu0gW"
body = f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="test.txt"\r\nContent-Type: text/plain\r\n\r\nGlucose: 90 mg/dL\r\n--{boundary}--\r\n'
req2 = urllib.request.Request("https://lablens-api-oisn.onrender.com/api/reports/upload", data=body.encode(), headers={"Content-Type": f"multipart/form-data; boundary={boundary}", "Authorization": f"Bearer {token}"})
try:
    res2 = urllib.request.urlopen(req2)
    print("Upload success:", res2.read().decode())
except urllib.error.HTTPError as e:
    print("Upload error:", e.read().decode())
except Exception as e:
    print("Other error:", e)
