# -*- coding: utf-8 -*-
"""抓取各平台公开数据，合并进 data/stats.json。

设计原则：
- 任一数据源失败时保留上一次的值，绝不写入 null / 0 覆盖真实数据。
- 只依赖公开接口，不需要任何密钥。
- 由 .github/workflows/refresh-stats.yml 定时调用。
"""
import datetime, json, pathlib, urllib.error, urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "stats.json"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")
TZ = datetime.timezone(datetime.timedelta(hours=8))

GH_USER = "zhonglike"
BILI_MID = "3493271126935853"
DOUYIN_A = "MS4wLjABAAAAocDV9OG3ChdHJefUldaCZGRAWjlqFJUej-JnA3fbJHbdzcdHvUbc75k6V21p66HT"
DOUYIN_B = "MS4wLjABAAAA5J8q0yjNvN2gPwe9WgMGsHBjkQOs_iPEKVBcFobpgQyBSyikwbABUDuaGJC1pIXg"


def get_json(url, headers=None, timeout=25):
    h = {"User-Agent": UA, "Accept": "application/json, text/plain, */*"}
    if headers:
        h.update(headers)
    req = urllib.request.Request(url, headers=h)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8", "replace"))


def safe(fn, label, out):
    """执行抓取，失败只记录不抛出。返回 dict 或 None。"""
    try:
        return fn()
    except Exception as e:
        out.append("[warn] %s 抓取失败，沿用旧值：%s" % (label, repr(e)[:110]))
        return None


def load():
    if DATA.exists():
        return json.loads(DATA.read_text(encoding="utf-8"))
    return {}


def deep_set(d, path, value):
    node = d
    for key in path[:-1]:
        node = node.setdefault(key, {})
    node[path[-1]] = value


def main():
    log = []
    st = load()

    # ---- GitHub（官方 REST，稳定）----
    def gh():
        u = get_json("https://api.github.com/users/" + GH_USER,
                     {"Accept": "application/vnd.github+json"})
        repos = get_json("https://api.github.com/users/%s/repos?per_page=100&sort=updated" % GH_USER,
                         {"Accept": "application/vnd.github+json"})
        orig = [r for r in repos if not r.get("fork")]
        return {
            "repos": len(repos),
            "orig_repos": len(orig),
            "forks": len(repos) - len(orig),
            "stars": sum(r.get("stargazers_count", 0) for r in orig),
            "followers": u.get("followers"),
            "following": u.get("following"),
        }
    g = safe(gh, "GitHub", log)
    if g:
        st.setdefault("github", {}).update(g)
        log.append("[ok] GitHub: %s 仓库 / %s 原创 / %s star" %
                   (g["repos"], g["orig_repos"], g["stars"]))

    # ---- 哔哩哔哩 ----
    def bili():
        rel = get_json("https://api.bilibili.com/x/relation/stat?vmid=" + BILI_MID,
                       {"Referer": "https://space.bilibili.com/"})
        d = rel.get("data") or {}
        out = {}
        if d.get("follower") is not None:
            out["fans"] = d["follower"]
        if d.get("following") is not None:
            out["following"] = d["following"]
        try:
            import urllib.parse
            kw = urllib.parse.quote("可爱的硬币1145")
            s = get_json("https://api.bilibili.com/x/web-interface/search/type"
                         "?search_type=bili_user&keyword=" + kw,
                         {"Referer": "https://www.bilibili.com/"})
            hit = None
            for item in (s.get("data") or {}).get("result") or []:
                if str(item.get("mid")) == BILI_MID:
                    hit = item
                    break
            if hit:
                out["videos"] = hit.get("videos")
                out["level"] = hit.get("level")
        except Exception:
            pass
        return out or None
    b = safe(bili, "哔哩哔哩", log)
    if b:
        st.setdefault("bilibili", {}).update({k: v for k, v in b.items() if v is not None})
        log.append("[ok] 哔哩哔哩: %s" % json.dumps(b, ensure_ascii=False))

    # ---- 抖音（老接口，随时可能失效；失败即保留旧值）----
    def dy(sec):
        d = get_json("https://www.iesdouyin.com/web/api/v2/user/info/?sec_uid=" + sec)
        ui = d.get("user_info") or {}
        if not ui.get("nickname"):
            return None
        return {
            "works": ui.get("aweme_count"),
            "likes": int(ui["total_favorited"]) if ui.get("total_favorited") else None,
            "fans": ui.get("mplatform_followers_count"),
            "following": ui.get("following_count"),
            "unique_id": ui.get("unique_id"),
        }
    for key, sec, label in [("douyin_a", DOUYIN_A, "抖音 zhonglike"),
                            ("douyin_b", DOUYIN_B, "抖音 可爱的硬币1145")]:
        r = safe(lambda s=sec: dy(s), label, log)
        if r:
            clean = {k: v for k, v in r.items() if v is not None}
            st.setdefault(key, {}).update(clean)
            log.append("[ok] %s: %s" % (label, json.dumps(clean, ensure_ascii=False)))

    st["updated_at"] = datetime.datetime.now(TZ).replace(microsecond=0).isoformat()
    DATA.parent.mkdir(parents=True, exist_ok=True)
    DATA.write_text(json.dumps(st, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    log.append("[done] " + str(DATA.relative_to(ROOT)))
    print("\n".join(log))


if __name__ == "__main__":
    main()
