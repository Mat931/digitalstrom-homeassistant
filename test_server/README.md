This server can be used to test the digitalstrom-homeassistant integration without the need for a real dSS.

## Install dependencies
```bash
python3 -m venv .venv
source .venv/bin/activate
pip3 install -r requirements.txt
```

## Generate certificate and key
```bash
openssl req -x509 -newkey rsa:4096 -keyout key.pem -out cert.pem -sha256 -days 365 -nodes -subj "/C=XX/ST=Test/L=Test/O=Test/OU=Test/CN=Test"
```

## Run test server
```bash
python3 server.py
```
