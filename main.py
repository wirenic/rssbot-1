#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import urllib

import feedparser
import telebot
from apscheduler.schedulers.background import BackgroundScheduler

import config
from db import *

logger = telebot.logger
telebot.logger.setLevel(logging.WARNING)
# telebot.apihelper.proxy = {'https': 'socks5h://127.0.0.1:7890'}
bot = telebot.TeleBot(config.TOKEN, parse_mode=None)

logging.basicConfig(
    filename='log.txt',
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.WARNING)


def get_list(rss_d, last):
    """Get a list of article links for feed updates"""
    link_list = []
    for r in range(len(rss_d['links'])):
        link = rss_d['links'][r].link
        if link == last:
            return link_list
        link_list.append(link)
    return link_list


def get_refresh():
    """Refresh subscription"""
    rows = db_all()
    for row in rows:
        try:
            rss_parse = feedparser.parse(row[0])
        except urllib.error.URLError:
            pass
        else:
            rss_d = {'title': rss_parse.feed.title, 'link': rss_parse.feed.link, 'links': rss_parse.entries}
            link_list = get_list(rss_d, row[-1])
            if len(link_list) > 0:
                for link in link_list:
                    # Get subscribers
                    usrlist = db_rssusr(row[0])
                    if usrlist:
                        for u in usrlist:
                            bot.send_message(u[0], "<b>%s</b>\n%s" % (row[1], str(link)), parse_mode="HTML")
                    else:
                        pass
                try:
                    db_update(row[0], link_list[0])
                except Exception as err:
                    logging.warning(str(err))
            else:
                pass


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
                    rss_parse = feedparser.parse(rss)
                except urllib.error.URLError:
                    bot.reply_to(message, "订阅失败：链接错误")
                else:
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


if __name__ == '__main__':
    scheduler = BackgroundScheduler(timezone="Asia/Shanghai")
    scheduler.add_job(get_refresh, 'interval', minutes=config.INTERVAL)
    scheduler.start()
    # Init database
    try:
        db_init()
    except sqlite3.OperationalError:
        pass
    bot.polling()
