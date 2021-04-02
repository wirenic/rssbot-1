#!/usr/bin/env python
# -*- coding: utf-8 -*-
import asyncio
import logging
import time

import aiohttp
import feedparser
from aiogram import Bot, types
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from aiogram.dispatcher import Dispatcher
from aiogram.utils.executor import start_webhook
from apscheduler.schedulers.asyncio import AsyncIOScheduler

import config
from db import *

API_TOKEN = config.TOKEN

rep = {"\\": r"\\", "`": "\\`", "*": "\\*", "_": "\\_", "#": "\\#", "+": "\\+", "-": "\\-", ".": "\\.", "!": "\\!"}

# webhook settings
WEBHOOK_HOST = config.WEBHOOK_HOST
WEBHOOK_PATH = config.WEBHOOK_PATH
WEBHOOK_URL = f"{WEBHOOK_HOST}{WEBHOOK_PATH}"

# webserver settings
WEBAPP_HOST = config.WEBAPP_HOST
WEBAPP_PORT = config.WEBAPP_PORT

# Configure logging
logging.basicConfig(
    filename='webhook.log',
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.WARNING)

headers = {
    'user-agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.71 '
                  'Safari/537.36',
}

# Initialize bot and dispatcher
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)
dp.middleware.setup(LoggingMiddleware())


async def get_list(entries, last_link):
    """Get a list of article links for feed updates"""
    link_list = []
    for entry in entries:
        link = entry.link
        if link == last_link:
            return link_list
        link_list.append(link)
    return link_list


async def get_refresh():
    """Update subscription"""
    rows = db_all()
    async with aiohttp.ClientSession(
            connector=aiohttp.TCPConnector(ssl=False), headers=headers) as session:
        tasks = [
            asyncio.create_task(refresh(session, row))
            for row in rows]
        await asyncio.wait(tasks)


async def refresh(session, row):
    """Refresh subscription"""
    try:
        async with session.get(row[0]) as response:
            rss_content = await response.text()
            status_code = response.status
    except aiohttp.client_exceptions.ClientConnectorError:
        logging.warning(f"{row[1]}[{row[0]}]\t更新失败：链接错误")
    except asyncio.exceptions.TimeoutError:
        logging.warning(f"{row[1]}[{row[0]}]\t更新失败：连接超时")
    else:
        rss_parse = feedparser.parse(rss_content)
        if len(rss_parse.entries) < 1:
            logging.warning(f"{row[1]}[{row[0]}]\t更新失败：链接失效(status:{status_code})")
        else:
            # Sort by publish time
            sort_list = [ent for ent in rss_parse.entries]
            sort_list.sort(key=lambda ent: time.mktime(ent.published_parsed), reverse=True)

            link_list = await get_list(sort_list, row[-1])
            if link_list:
                # Get subscribers
                usrlist = db_rssusr(row[0])
                if usrlist:
                    for usr in usrlist:
                        uid = usr[0]
                        for link in link_list:
                            await bot.send_message(uid, f"<b>{row[1]}</b>\n{link}", parse_mode="HTML")
                try:
                    db_update(row[0], link_list[0])
                except Exception as e:
                    logging.warning(str(e))


@dp.message_handler(commands=['start'])
async def cmd_start(message: types.Message):
    await message.reply(f"这是一个 RSS 订阅 Bot，更新频率为{config.INTERVAL}分钟\n"
                        f"使用 /help 获取帮助")


@dp.message_handler(commands=['help'])
async def cmd_help(message: types.Message):
    await message.reply(
        "命令列表：\n" +
        "/rss         显示当前订阅列表\n" +
        "/sub        订阅一个RSS    `/sub http://example.com/feed`\n" +
        "/unsub   退订一个RSS    `/unsub http://example.com/feed`\n" +
        "/help       显示帮助信息", parse_mode="MarkdownV2")


@dp.message_handler(commands=['rss'])
async def cmd_rss(message: types.Message):
    """Send to users their subscription list"""
    reword = "订阅列表："
    rss_list = db_chatid(message.chat.id)
    if rss_list:
        for r in rss_list:
            title = str(r[1])
            for k in rep:
                title = title.replace(k, rep[k])
            reword += f"\n[{title}]({r[2]})    `{r[0]}`"
        await message.reply(reword, parse_mode="MarkdownV2", disable_web_page_preview=True)
    else:
        await message.reply("还未添加任何订阅，使用 /help 来获取帮助")


@dp.message_handler(commands=['sub'])
async def cmd_sub(message: types.Message):
    """Add subscription"""
    # Check if the format is correct
    try:
        rss = message.text.split()[1]
    except IndexError:
        await message.reply("使用方法: `/sub http://example.com/feed`", parse_mode="MarkdownV2")
    else:
        # Check if RSS is subscribed
        if db_chatid_rss(message.chat.id, rss):
            await message.reply("订阅过的 RSS")
        else:
            # Check if this RSS link exists in the rss table
            db_rss_list = db_rss(rss)
            if db_rss_list:
                db_write_usr(message.chat.id, rss)
                title = db_rss_list[0][1]
                for k in rep:
                    title = title.replace(k, rep[k])
                await message.reply(f"[{title}]({db_rss_list[0][2]}) 订阅成功", parse_mode="MarkdownV2",
                                    disable_web_page_preview=True)
            else:
                # Check if the RSS link is valid
                async with aiohttp.ClientSession(
                        connector=aiohttp.TCPConnector(ssl=False), headers=headers) as session:
                    try:
                        async with session.get(rss) as response:
                            rss_content = await response.text()
                            status_code = response.status
                    except aiohttp.client_exceptions.ClientConnectorError as e:
                        await message.reply(f"订阅失败：链接错误({e})")
                    except asyncio.exceptions.TimeoutError as e:
                        await message.reply(f"订阅失败：连接超时({e})")
                    else:
                        rss_parse = feedparser.parse(rss_content)
                        if len(rss_parse.entries) < 1:
                            await message.reply(f"订阅失败：链接无效(status:{status_code})")
                        else:
                            # Sort by publish time
                            sort_list = [ent for ent in rss_parse.entries]
                            sort_list.sort(key=lambda ent: time.mktime(ent.published_parsed), reverse=True)

                            db_write_rss(rss, rss_parse.feed.title, rss_parse.feed.link, sort_list[0].link)
                            db_write_usr(message.chat.id, rss)
                            title = rss_parse.feed.title
                            for k in rep:
                                title = title.replace(k, rep[k])
                            await message.reply(f"[{title}]({rss_parse.feed.link}) 订阅成功", parse_mode="MarkdownV2",
                                                disable_web_page_preview=True)


@dp.message_handler(commands=['unsub'])
async def cmd_unsub(message: types.Message):
    """Remove subscription"""
    # Check if the format is correct
    try:
        rss = message.text.split()[1]
    except IndexError:
        await message.reply("使用方法: `/unsub http://example.com/feed`", parse_mode="MarkdownV2")
    else:
        # Check if RSS is subscribed
        row = db_chatid_rss(message.chat.id, rss)
        if len(row) > 0:
            # Check for other subscribers
            usr = db_rssusr(rss)
            if len(usr) > 1:
                result = db_remove_usr_rss(message.chat.id, rss)
                if not result:
                    title = row[0][1]
                    for k in rep:
                        title = title.replace(k, rep[k])
                    await message.reply(f"[{title}]({row[0][2]}) 退订成功", parse_mode="MarkdownV2",
                                        disable_web_page_preview=True)
                else:
                    await message.reply(f"移除失败：{result}")
            else:
                result = db_remove_rss(rss) + db_remove_usr_rss(message.chat.id, rss)
                if not result:
                    title = row[0][1]
                    for k in rep:
                        title = title.replace(k, rep[k])
                    await message.reply(f"[{title}]({row[0][2]}) 退订成功", parse_mode="MarkdownV2",
                                        disable_web_page_preview=True)
                else:
                    await message.reply(f"移除失败：{result}")
        else:
            await message.reply("未订阅过的 RSS")


@dp.message_handler(commands=['refresh'])
async def cmd_refresh(message: types.Message):
    """Update subscription manually"""
    await get_refresh()


async def on_startup(dp):
    await bot.set_webhook(WEBHOOK_URL, ip_address=config.SERVER_IP)
    # insert code here to run it after start


async def on_shutdown(dp):
    logging.warning('Shutting down..')

    # insert code here to run it before shutdown

    # Remove webhook (not acceptable in some cases)
    await bot.delete_webhook()

    # Close DB connection (if used)
    # await dp.storage.close()
    # await dp.storage.wait_closed()

    logging.warning('Bye!')


# Timed task
scheduler = AsyncIOScheduler()
scheduler.add_job(get_refresh, 'interval', minutes=config.INTERVAL)
scheduler.start()

if __name__ == '__main__':
    # Init database
    try:
        db_init()
    except sqlite3.OperationalError:
        pass

    # Start bot
    start_webhook(
        dispatcher=dp,
        webhook_path=WEBHOOK_PATH,
        on_startup=on_startup,
        on_shutdown=on_shutdown,
        skip_updates=True,
        host=WEBAPP_HOST,
        port=WEBAPP_PORT,
    )
