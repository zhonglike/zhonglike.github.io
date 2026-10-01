#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""刷新 zhonglike.tech 的三份数据快照
    data/stats.json     总览数字（GitHub / B站 / 抖音 / Steam）
    data/projects.json  原创仓库档案 + README 原文
    data/activity.json  动态流（GitHub 事件 + B站投稿）

原则：任一数据源失败就沿用上一次的值，绝不写 null / 0 覆盖真实数据。
"""

import base64
import json
import os
import re
import sys
import time
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
TZ = timezone(timedelta(hours=8))
NOW = datetime.now(TZ).isoformat(timespec="seconds")

GH = "https://api.github.com"
TOKEN = os.environ.get("GH_TOKEN", "")
UA = "zhonglike-portal-refresh/1.0"

SELF_REPOS = {"zhonglike.github.io"}
BLOCKED_REPOS = {"DeltaForce-Locker", "DeltaForce-OBS-Locker"}

DOUYIN = [
    ("douyin_a", "MS4wLjABAAAAocDV9OG3ChdHJefUldaCZGRAWjlqFJUej-JnA3fbJHbdzcdHvUbc75k6V21p66HT"),
    ("douyin_b", "MS4wLjABAAAA5J8q0yjNvN2gPwe9WgMGsHBjkQOs_iPEKVBcFobpgQyBSyikwbABUDuaGJC1pIXg"),
]
BILI_MID = "3493271126935853"

log = []


def get_json(url, timeout=25, headers=None):
    h = {"User-Agent": UA, "Accept": "application/vnd.github+json"}
    if TOKEN:
        h["Authorization"] = "Bearer " + TOKEN
    if headers:
        h.update(headers)
    req = urllib.request.Request(url, headers=h)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8", "replace"))


def load(name, default):
    try:
        return json.loads((DATA / name).read_text(encoding="utf-8"))
    except Exception:
        return default


def save(name, obj):
    (DATA / name).write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def ok(m):
    log.append("OK   " + m)


def warn(m):
    log.append("WARN " + m)


def clean_readme(md):
    md = re.sub(r"<!--.*?-->", "", md, flags=re.S)
    md = re.sub(r"(?m)^\s*\[!\[.*?\]\(.*?\)\]\(.*?\)\s*$", "", md)
    md = re.sub(r"(?m)^\s*!\[.*?\]\(.*?\)\s*$", "", md)
    md = re.sub(r"\n{3,}", "\n\n", md).strip()
    return md[:12000]


def fetch_github():
    stats = load("stats.json", {})
    gh = stats.get("github", {})

    try:
        u = get_json(GH + "/users/zhonglike")
        gh.update({
            "login": u.get("login"),
            "name": u.get("name") or u.get("login"),
            "bio": u.get("bio") or "",
            "followers": u.get("followers", gh.get("followers")),
            "following": u.get("following", gh.get("following")),
            "created_at": u.get("created_at", gh.get("created_at")),
            "avatar": u.get("avatar_url", gh.get("avatar")),
        })
        ok("github user")
    except Exception as e:
        warn("github user: %s" % e)

    repos = []
    try:
        repos = get_json(GH + "/users/zhonglike/repos?per_page=100&sort=updated")
        ok("github repos: %d" % len(repos))
    except Exception as e:
        warn("github repos: %s" % e)

    if repos:
        gh["repos"] = len(repos)
        gh["forks"] = sum(1 for r in repos if r.get("fork"))
        gh["stars"] = sum(r.get("stargazers_count", 0) for r in repos if not r.get("fork"))

    langs = {}
    items = []
    for r in repos:
        name = r.get("name")
        if r.get("fork") or name in SELF_REPOS or name in BLOCKED_REPOS:
            continue
        lang = r.get("language") or "Other"
        desc = r.get("description") or ""
        langs[lang] = langs.get(lang, 0) + 1
        # 分类：游戏 / 应用 / 工具
        if "game" in name.lower() or "游戏" in desc:
            cat = "game"
        elif lang == "Dart" or name == "OCOS":
            cat = "app"
        else:
            cat = "tool"
        items.append({
            "name": name,
            "cat": cat,
            "desc": desc,
            "lang": lang,
            "stars": r.get("stargazers_count", 0),
            "forks": r.get("forks_count", 0),
            "license": ((r.get("license") or {}).get("spdx_id") or "none"),
            "topics": r.get("topics") or [],
            "created": (r.get("created_at") or "")[:10],
            "updated": (r.get("updated_at") or "")[:10],
            "url": r.get("html_url"),
            "homepage": r.get("homepage") or "",
            "archived": bool(r.get("archived")),
        })

    # 已上线站点：仓库若开了 GitHub Pages 并有自定义域名，自动带上站点入口
    for it in items:
        try:
            pg = get_json(GH + "/repos/zhonglike/%s/pages" % it["name"])
            cname = pg.get("cname")
            if cname:
                it["site"] = "https://" + cname
                it["site_status"] = pg.get("status")
                it["site_https"] = ((pg.get("https_certificate") or {}).get("state") or "pending")
                ok("site %s -> %s (%s)" % (it["name"], cname, it["site_https"]))
        except Exception:
            pass  # 没开 Pages 是常态，不算错误
        time.sleep(0.2)
    if items:
        gh["orig_repos"] = len(items)
        gh["languages"] = dict(sorted(langs.items(), key=lambda kv: -kv[1]))

        prev = {i["name"]: i for i in load("projects.json", {}).get("items", [])}
        # 语言占比按代码字节统计，比仓库计数更贴近真实投入
        by_bytes = {}
        for it in items:
            try:
                lb = get_json(GH + "/repos/zhonglike/%s/languages" % it["name"])
                for k, v in lb.items():
                    by_bytes[k] = by_bytes.get(k, 0) + v
            except Exception:
                pass
            time.sleep(0.2)
        if by_bytes:
            gh["lang_bytes"] = dict(sorted(by_bytes.items(), key=lambda kv: -kv[1])[:8])
            ok("lang bytes: %s" % ", ".join("%s=%d" % kv for kv in list(gh["lang_bytes"].items())[:4]))

        for it in items:
            try:
                rd = get_json(GH + "/repos/zhonglike/%s/readme" % it["name"])
                it["readme"] = clean_readme(
                    base64.b64decode(rd.get("content", "")).decode("utf-8", "replace"))
                ok("readme %s (%d)" % (it["name"], len(it["readme"])))
            except Exception as e:
                old = prev.get(it["name"], {}).get("readme")
                if old:
                    it["readme"] = old
                warn("readme %s: %s" % (it["name"], e))
            time.sleep(0.3)
        save("projects.json", {"updated_at": NOW, "items": items})

    events = []
    try:
        for e in get_json(GH + "/users/zhonglike/events?per_page=60"):
            kind = e.get("type")
            repo = (e.get("repo") or {}).get("name", "")
            short = repo.split("/")[-1]
            # 门户站自身的提交属于站点维护噪音，不算作品动态
            if short in SELF_REPOS:
                continue
            p = e.get("payload") or {}
            url = "https://github.com/" + repo
            title, extra = "", ""
            if kind == "PushEvent":
                cs = p.get("commits") or []
                # events API 常把 commits 置空，此时退回「推送更新」而不是显示 0 个提交
                if cs:
                    title = "推送 %d 个提交到 %s" % (len(cs), short)
                    extra = cs[0].get("message", "").split("\n")[0][:90]
                else:
                    title = "推送更新到 %s" % short
                if p.get("head"):
                    url = "https://github.com/%s/commits/%s" % (repo, str(p["head"])[:7])
            elif kind == "CreateEvent":
                title = "创建 %s：%s" % (p.get("ref_type", "资源"), short)
            elif kind == "WatchEvent":
                title = "Star 了 %s" % repo
            elif kind == "ForkEvent":
                title = "Fork 了 %s" % repo
            elif kind == "IssuesEvent":
                title = "%s issue @ %s" % (p.get("action", "操作"), short)
            elif kind == "PullRequestEvent":
                title = "%s PR @ %s" % (p.get("action", "操作"), short)
            elif kind == "PublicEvent":
                title = "开源了 %s" % short
            elif kind == "ReleaseEvent":
                title = "发布版本 @ %s" % short
            else:
                continue
            events.append({"src": "github", "kind": kind.replace("Event", "").lower(),
                           "title": title, "extra": extra, "url": url, "at": e.get("created_at")})
        ok("github events: %d" % len(events))
    except Exception as e:
        warn("github events: %s" % e)

    # 站点矩阵：门户主站 + 所有已上线 Pages 子站
    stats["sites"] = [{"name": "门户主站", "host": "zhonglike.tech",
                       "url": "https://zhonglike.tech", "desc": "身份聚合与项目索引", "kind": "hub"}] + [
        {"name": it["name"], "host": it["site"].replace("https://", ""),
         "url": it["site"], "desc": it["desc"][:80], "kind": it.get("cat", "tool")}
        for it in items if it.get("site")
    ]

    stats["github"] = gh
    return stats, events


def fetch_bilibili():
    b = load("stats.json", {}).get("bilibili", {})
    hdr = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/131.0.0.0 Safari/537.36",
           "Referer": "https://space.bilibili.com/"}
    try:
        d = get_json("https://api.bilibili.com/x/space/acc/info?mid=" + BILI_MID, headers=hdr).get("data") or {}
        b.update({"uid": BILI_MID, "name": d.get("name", b.get("name")),
                  "level": d.get("level", b.get("level")),
                  "sign": d.get("sign", b.get("sign", "")),
                  "face": d.get("face", b.get("face", ""))})
        ok("bilibili info")
    except Exception as e:
        warn("bilibili info: %s" % e)
    try:
        d = get_json("https://api.bilibili.com/x/relation/stat?vmid=" + BILI_MID, headers=hdr).get("data") or {}
        b["fans"] = d.get("follower", b.get("fans"))
        ok("bilibili fans %s" % b.get("fans"))
    except Exception as e:
        warn("bilibili fans: %s" % e)
    try:
        d = get_json("https://api.bilibili.com/x/space/upstat?mid=" + BILI_MID, headers=hdr).get("data") or {}
        b["videos"] = (d.get("archive") or {}).get("view", b.get("videos"))
        b["likes"] = d.get("likes", b.get("likes"))
        ok("bilibili videos %s" % b.get("videos"))
    except Exception as e:
        warn("bilibili upstat: %s" % e)

    vids = []
    try:
        r = get_json("https://api.bilibili.com/x/space/arc/search?mid=%s&pn=1&ps=8&order=pubdate" % BILI_MID, headers=hdr)
        for v in ((r.get("data") or {}).get("list") or {}).get("vlist") or []:
            vids.append({"src": "bilibili", "kind": "video",
                         "title": v.get("title", ""),
                         "extra": (v.get("description") or "")[:80],
                         "url": "https://www.bilibili.com/video/" + (v.get("bvid") or ""),
                         "at": datetime.fromtimestamp(v.get("created", 0), TZ).isoformat(timespec="seconds") if v.get("created") else "",
                         "plays": v.get("play", 0)})
        ok("bilibili video list: %d" % len(vids))
    except Exception as e:
        warn("bilibili video list: %s" % e)
    return b, vids


def fetch_douyin(stats):
    hdr = {"User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 Mobile/15E148",
           "Referer": "https://www.douyin.com/"}
    for key, sec in DOUYIN:
        cur = stats.get(key, {})
        try:
            r = get_json("https://www.iesdouyin.com/web/api/v2/user/info/?sec_uid=" + sec, headers=hdr)
            u = r.get("user_info") or {}
            if not u:
                warn("%s: 接口返回空" % key)
                continue
            cur.update({
                "sec_uid": sec,
                "nickname": u.get("nickname", cur.get("nickname")),
                "unique_id": u.get("unique_id", cur.get("unique_id")),
                "works": u.get("aweme_count", cur.get("works")),
                "likes": u.get("total_favorited", cur.get("likes")),
                "fans": u.get("mplatform_followers_count", cur.get("fans")),
                "following": u.get("following_count", cur.get("following")),
                "sign": u.get("signature", cur.get("sign", "")),
            })
            ok("%s %s 作品=%s 赞=%s 粉=%s" % (key, cur.get("nickname"), cur.get("works"), cur.get("likes"), cur.get("fans")))
        except Exception as e:
            warn("%s: %s" % (key, e))
        stats[key] = cur
    return stats


def main():
    DATA.mkdir(parents=True, exist_ok=True)
    stats, events = fetch_github()
    b, vids = fetch_bilibili()
    stats["bilibili"] = b
    stats = fetch_douyin(stats)

    ev = sorted([e for e in events + vids if e.get("at")], key=lambda x: x["at"], reverse=True)
    save("activity.json", {"updated_at": NOW, "items": ev[:40]})

    stats["updated_at"] = NOW
    stats.setdefault("note", "由 GitHub Actions 定时刷新；取不到时页面回退到静态兜底值。")
    save("stats.json", stats)

    print("=== refresh %s ===" % NOW)
    print("\n".join(log))
    print("projects=%d events=%d" % (len(load("projects.json", {}).get("items", [])), len(ev[:40])))


if __name__ == "__main__":
    sys.exit(main())
