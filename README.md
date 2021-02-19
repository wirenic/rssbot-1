# rssbot

Telegram rss robot written in python.

使用 python 编写的 Telegram rss bot

## Usage

### Install:

```
git clone https://github.com/Kuhahku/rssbot.git
cd rssbot
pip install requirements.txt
```

Edit `config.py`, set your telegram bot `TOKEN` and rss refresh `INTERVAL`

### Run:

```
python main.py
```

### Commands:

```
/rss       Display current subscription list
/sub       Subscribe to an RSS    /sub http://example.com/feed
/unsub     Unsubscribe from an RSS    /unsub http://example.com/feed
```
### Webhook

Edit `config.py`, set your `URL` and `SERVER_IP`

#### Nginx:

```
location /
{
    proxy_pass http://127.0.0.1:5000;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header REMOTE-HOST $remote_addr;
}
```

#### Run:

```
gunicorn -b 127.0.0.1:5000 --access-logfile access.log --error-log error.log webhook:app
```

## License

MIT
