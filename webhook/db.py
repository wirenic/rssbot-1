#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sqlite3


def db_init():
    """Init the database, create the rss & usr table"""
    conn = sqlite3.connect('rss.db', check_same_thread=False)
    c = conn.cursor()
    c.execute("CREATE TABLE rss (rss text, title text, link text, last text)")
    c.execute("CREATE TABLE usr (chatid int, rss text)")
    conn.commit()
    conn.close()


def db_all():
    """Load the rss table and return all content"""
    conn = sqlite3.connect('rss.db', check_same_thread=False)
    c = conn.cursor()
    c.execute("SELECT * FROM rss")
    rows = c.fetchall()
    conn.close()
    return rows


def db_update(rss, last):
    """Update rss table"""
    conn = sqlite3.connect('rss.db', check_same_thread=False)
    c = conn.cursor()
    q = [last, rss]
    c.execute("UPDATE rss SET last = ? WHERE rss = ?", q)
    conn.commit()
    conn.close()


def db_chatid(chatid):
    """Get subscription list"""
    conn = sqlite3.connect('rss.db', check_same_thread=False)
    c = conn.cursor()
    c.execute("SELECT * FROM rss INNER JOIN usr u on rss.rss = u.rss WHERE u.chatid=?", (chatid,))
    rows = c.fetchall()
    return rows


def db_rss(rss):
    """Check if this link exists in the rss table"""
    conn = sqlite3.connect('rss.db', check_same_thread=False)
    c = conn.cursor()
    c.execute("SELECT * FROM rss WHERE rss=?", (rss,))
    rows = c.fetchall()
    return rows


def db_rssusr(rss):
    """Get rss subscribers"""
    conn = sqlite3.connect('rss.db', check_same_thread=False)
    c = conn.cursor()
    c.execute("SELECT * FROM usr WHERE rss=?", (rss,))
    rows = c.fetchall()
    return rows


def db_chatid_rss(chatid, rss):
    """Check if this subscription exists"""
    conn = sqlite3.connect('rss.db', check_same_thread=False)
    c = conn.cursor()
    c.execute("SELECT * FROM rss INNER JOIN usr u on rss.rss = u.rss WHERE u.chatid=? AND u.rss=?", (chatid, rss))
    rows = c.fetchall()
    conn.close()
    return rows


def db_write_rss(rss, title, link, last):
    """Write to rss table"""
    conn = sqlite3.connect('rss.db', check_same_thread=False)
    c = conn.cursor()
    q = [rss, title, link, last]
    c.execute("INSERT INTO rss ('rss', 'title', 'link', 'last') VALUES (?,?,?,?)", q)
    conn.commit()
    conn.close()


def db_write_usr(chatid, rss):
    """Write to usr table"""
    conn = sqlite3.connect('rss.db', check_same_thread=False)
    c = conn.cursor()
    q = [chatid, rss]
    c.execute("INSERT INTO usr ('chatid', 'rss') VALUES (?,?)", q)
    conn.commit()
    conn.close()


def db_remove(chatid, rss):
    """Delete subscription"""
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
