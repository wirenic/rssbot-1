# rssbot

Asynchronous Telegram RSS Bot written in python.

使用 python 编写的异步 Telegram RSS Bot

## Usage

### Install:

```
git clone https://github.com/Kuhahku/rssbot.git
cd rssbot
pip install -r requirements.txt
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

Edit `config.py`, complete the setting

#### Nginx:

```
location /
{
    proxy_pass http://127.0.0.1:5001;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header REMOTE-HOST $remote_addr;
}
```

#### Run:

```
python webhook.py
```

## License

MIT
