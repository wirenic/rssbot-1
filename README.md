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
## License

MIT
