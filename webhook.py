#!/usr/bin/env python
# -*- coding: utf-8 -*-
import io
import logging

import requests
from flask import Flask, request
from flask_apscheduler import APScheduler
import feedparser
import telebot

import config
from db import *

# telebot.apihelper.proxy = {'https': 'socks5h://127.0.0.1:7890'}
bot = telebot.TeleBot(config.TOKEN, parse_mode=None)

logging.basicConfig(
    filename='webhook.log',
    filemode='a',
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.WARNING
)

logger = logging.getLogger(__name__)


def get_list(entries, last_link):
    """Get a list of article links for feed updates"""
    link_list = []
    for entry in entries:
        link = entry.link
        if link == last_link:
            return link_list
        link_list.append(link)
    return link_list


def get_refresh():
    """Refresh subscription"""
    rows = db_all()
    for row in rows:
        try:
            rss_content = requests.get(row[0], timeout=5, proxies={"http": None, "https": None})
        except requests.exceptions.ReadTimeout as e:
            logging.warning(row[0] + "\t" + str(e))
        except requests.exceptions.ConnectionError as e:
            logging.warning(row[0] + "\t" + str(e))
        else:
            rss_parse = feedparser.parse(io.BytesIO(rss_content.content))
            link_list = get_list(rss_parse.entries, row[-1])
            if link_list:
                # Get subscribers
                usrlist = db_rssusr(row[0])
                if usrlist:
                    for usr in usrlist:
                        uid = usr[0]
                        for link in link_list:
                            bot.send_message(uid, "<b>%s</b>\n%s" % (row[1], str(link)), parse_mode="HTML")
                try:
                    db_update(row[0], link_list[0])
                except Exception as e:
                    logging.warning(str(e))


# Setting Flask
app = Flask(__name__)


class Config(object):
    JOBS = [
        {
            'id': 'get_refresh',
            'func': 'webhook:get_refresh',
            'trigger': 'interval',
            'minutes': 5
        }
    ]
    SCHEDULER_API_ENABLED = True


app.config.from_object(Config())
scheduler = APScheduler()
scheduler.init_app(app)
scheduler.start()


@app.route('/')
def index():
    return ''


@app.route('/' + config.TOKEN, methods=['POST'])
def get_message():
    bot.process_new_updates([telebot.types.Update.de_json(request.stream.read().decode("utf-8"))])
    return "ok", 200


@app.route('/setwebhook', methods=['GET', 'POST'])
def set_webhook():
    bot.remove_webhook()
    s = bot.set_webhook('{URL}{HOOK}'.format(URL=config.URL, HOOK=config.TOKEN), ip_address=config.SERVER_IP)
    if s:
        return "webhook setup ok"
    else:
        return "webhook setup failed"


@bot.message_handler(commands=['start'])
def cmd_start(message):
    bot.reply_to(message,
                 "这是一个 RSS 订阅 Bot，更新频率为5分钟\n"
                 "可以使用 https://feedburner.com 进行代理，减轻订阅源压力\n"
                 "使用 /help 获取帮助")


@bot.message_handler(commands=['help'])
def cmd_help(message):
    bot.reply_to(message,
                 "命令列表：\n" +
                 "/rss         显示当前订阅列表\n" +
                 "/sub        订阅一个RSS    `/sub http://example.com/feed`\n" +
                 "/unsub   退订一个RSS    `/unsub http://example.com/feed`\n" +
                 "/help       显示帮助信息", parse_mode="MarkdownV2")


@bot.message_handler(commands=['rss'])
def cmd_rss(message):
    """Send to users their subscription list"""
    reword = "订阅列表："
    rss_list = db_chatid(message.chat.id)
    if rss_list:
        for r in rss_list:
            reword = reword + "\n[%s](%s)    `%s`" % (str(r[1]), str(r[2]), str(r[0]))
        bot.reply_to(message, str(reword), parse_mode="MarkdownV2", disable_web_page_preview=True)
    else:
        bot.reply_to(message, "还未添加任何订阅，使用 /help 来获取帮助")


@bot.message_handler(commands=['sub'])
def cmd_sub(message):
    """Add subscription"""
    # Check if the format is correct
    try:
        rss = message.text.split()[1]
    except IndexError:
        bot.reply_to(message, "使用方法: `/sub http://example.com/feed`", parse_mode="MarkdownV2")
    else:
        # Check if RSS is subscribed
        if db_chatid_rss(message.chat.id, rss):
            bot.reply_to(message, "订阅过的 RSS")
        else:
            # Check if this RSS link exists in the rss table
            db_rss_list = db_rss(rss)
            if db_rss_list:
                db_write_usr(message.chat.id, rss)
                bot.reply_to(message, "[%s](%s) 订阅成功" % (db_rss_list[0][1], db_rss_list[0][2]), parse_mode="MarkdownV2",
                             disable_web_page_preview=True)
            else:
                # Check if the RSS link is valid
                try:
                    rss_content = requests.get(rss, timeout=5, proxies={"http": None, "https": None})
                except requests.exceptions.ReadTimeout as e:
                    bot.reply_to(message, "订阅失败：连接超时（%s）" % e)
                except requests.exceptions.ConnectionError as e:
                    bot.reply_to(message, "订阅失败：链接错误（%s）" % e)
                else:
                    rss_parse = feedparser.parse(io.BytesIO(rss_content.content))
                    if len(rss_parse.entries) < 1:
                        bot.reply_to(message, "订阅失败：无效的 RSS 链接")
                    else:
                        db_write_rss(rss, rss_parse.feed.title, rss_parse.feed.link, rss_parse.entries[0].link)
                        db_write_usr(message.chat.id, rss)
                        bot.reply_to(message, "[%s](%s) 订阅成功" % (rss_parse.feed.title, rss_parse.feed.link),
                                     parse_mode="MarkdownV2", disable_web_page_preview=True)


@bot.message_handler(commands=['unsub'])
def cmd_unsub(message):
    """Remove subscription"""
    # Check if the format is correct
    try:
        rss = message.text.split()[1]
    except IndexError:
        bot.reply_to(message, "使用方法: `/unsub http://example.com/feed`", parse_mode="MarkdownV2")
    else:
        # Check if RSS is subscribed
        row = db_chatid_rss(message.chat.id, rss)
        if len(row) > 0:
            result = db_remove(message.chat.id, rss)
            if not result:
                bot.reply_to(message, "[%s](%s) 退订成功" % (row[0][1], row[0][2]), parse_mode="MarkdownV2",
                             disable_web_page_preview=True)
            else:
                bot.reply_to(message, "移除失败：%s" % result)
        else:
            bot.reply_to(message, "未订阅过的 RSS")


@bot.message_handler(commands=['refresh'])
def cmd_refresh(message):
    """Update subscription manually"""
    get_refresh()


# Init database
try:
    db_init()
except sqlite3.OperationalError:
    pass

if __name__ == '__main__':
    app.run()
