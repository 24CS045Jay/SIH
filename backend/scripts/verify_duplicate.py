from pathlib import Path
import json
from urllib.request import Request, urlopen

BASE = "http://127.0.0.1:8024/api/v1"

def post_json(path, payload):
    request = Request(BASE + path, data=json.dumps(payload).encode(), headers={"Content-Type": "application/json"}, method="POST")
    with urlopen(request) as response:
        return json.loads(response.read())

def upload(token):
    path = Path("/tmp/kmrl_phase4_demo2.pdf")
    boundary = "----duplicatecheck"
    body = b"--" + boundary.encode() + b"\r\nContent-Disposition: form-data; name=\"file\"; filename=\"phase4-demo.pdf\"\r\nContent-Type: application/pdf\r\n\r\n" + path.read_bytes() + b"\r\n--" + boundary.encode() + b"--\r\n"
    request = Request(BASE + "/documents/upload", data=body, headers={"Authorization": f"Bearer {token}", "Content-Type": f"multipart/form-data; boundary={boundary}"}, method="POST")
    try:
        urlopen(request)
    except Exception as exc:
        return getattr(exc, "code", 500), exc.read().decode()
    return 200, "unexpectedly accepted duplicate"

login = post_json("/auth/login", {"email": "engineering.demo@kmrl.example", "password": "demo-password"})
code, body = upload(login["access_token"])
assert code == 409, (code, body)
print("duplicate upload rejected with HTTP 409")
