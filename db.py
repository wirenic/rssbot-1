#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sqlite3


def db_init():
    """初始化数据库，创建 rss & usr 表"""
    conn = sqlite3.connect('rss.db', check_same_thread=False)
    c = conn.cursor()
    c.execute("CREATE TABLE rss (rss text, title text, link text, last text)")
    c.execute("CREATE TABLE usr (chatid int, rss text)")
    conn.commit()
    conn.close()


def db_all():
    """加载rss数据表，并返回所有内容"""
    conn = sqlite3.connect('rss.db', check_same_thread=False)
    c = conn.cursor()
    c.execute("SELECT * FROM rss")
    rows = c.fetchall()
    conn.close()
    return rows


def db_update(rss, last):
    """更新rss数据表"""
    conn = sqlite3.connect('rss.db', check_same_thread=False)
    c = conn.cursor()
    q = [last, rss]
    c.execute("UPDATE rss SET last = ? WHERE rss = ?", q)
    conn.commit()
    conn.close()


def db_chatid(chatid):
    """获取订阅列表"""
    conn = sqlite3.connect('rss.db', check_same_thread=False)
    c = conn.cursor()
    c.execute("SELECT * FROM rss INNER JOIN usr u on rss.rss = u.rss WHERE u.chatid=?", (chatid,))
    rows = c.fetchall()
    return rows


def db_rss(rss):
    """检查rss表中是否存在此链接"""
    conn = sqlite3.connect('rss.db', check_same_thread=False)
    c = conn.cursor()
    c.execute("SELECT * FROM rss WHERE rss=?", (rss,))
    rows = c.fetchall()
    return rows


def db_rssusr(rss):
    """获取rss订阅用户"""
    conn = sqlite3.connect('rss.db', check_same_thread=False)
    c = conn.cursor()
    c.execute("SELECT * FROM usr WHERE rss=?", (rss,))
    rows = c.fetchall()
    return rows


def db_chatid_rss(chatid, rss):
    """检查是否存在此订阅"""
    conn = sqlite3.connect('rss.db', check_same_thread=False)
    c = conn.cursor()
    c.execute("SELECT * FROM rss INNER JOIN usr u on rss.rss = u.rss WHERE u.chatid=? AND u.rss=?", (chatid, rss))
    rows = c.fetchall()
    conn.close()
    return rows


def db_write_rss(rss, title, link, last):
    """写入rss数据表"""
    conn = sqlite3.connect('rss.db', check_same_thread=False)
    c = conn.cursor()
    q = [rss, title, link, last]
    c.execute("INSERT INTO rss ('rss', 'title', 'link', 'last') VALUES (?,?,?,?)", q)
    conn.commit()
    conn.close()


def db_write_usr(chatid, rss):
    """写入rss数据表"""
    conn = sqlite3.connect('rss.db', check_same_thread=False)
    c = conn.cursor()
    q = [chatid, rss]
    c.execute("INSERT INTO usr ('chatid', 'rss') VALUES (?,?)", q)
    conn.commit()
    conn.close()


def db_remove(chatid, rss):
    """删除订阅"""
    try:
        conn = sqlite3.connect('rss.db', check_same_thread=False)
        c = conn.cursor()
        c.execute("DELETE FROM usr WHERE chatid = ? AND rss = ?", (chatid, rss,))
        conn.commit()
        conn.close()
    except sqlite3.Error as e:
        return str(e)
    else:
        return False
