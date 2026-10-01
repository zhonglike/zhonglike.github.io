/* zhonglike.tech — 共享脚本
   1) 进场动画  2) 导航高亮（按路径）  3) 实时数据注入  4) 条形图动画
   所有取数失败都静默回退到 HTML 内的静态兜底值，页面永不空白。 */

(function () {
  'use strict';

  /* ---------- 1) 进场动画 ---------- */
  var items = document.querySelectorAll('.rv');
  if (items.length) {
    if ('IntersectionObserver' in window) {
      var io = new IntersectionObserver(function (es) {
        es.forEach(function (e) {
          if (e.isIntersecting) { e.target.classList.add('in'); io.unobserve(e.target); }
        });
      }, { rootMargin: '0px 0px -8% 0px', threshold: 0.05 });
      Array.prototype.forEach.call(items, function (el) { io.observe(el); });
    } else {
      Array.prototype.forEach.call(items, function (el) { el.classList.add('in'); });
    }
  }

  /* ---------- 2) 导航高亮 ---------- */
  // 路由式：取当前路径首段，匹配 <a data-route>，都没命中则高亮首页
  var seg = location.pathname.replace(/^\/+/, '').split('/')[0] || '';
  var links = Array.prototype.slice.call(document.querySelectorAll('[data-route]'));
  var hit = false;
  links.forEach(function (a) {
    var on = a.getAttribute('data-route') === seg;
    if (on) hit = true;
    a.classList.toggle('on', on);
  });
  if (!hit) links.forEach(function (a) {
    a.classList.toggle('on', a.getAttribute('data-route') === '');
  });

  // 首页锚点模式：无子路径时按滚动位置同步
  var anchors = Array.prototype.slice.call(document.querySelectorAll('[data-nav]'));
  if (anchors.length && !seg) {
    var secs = anchors.map(function (a) { return document.getElementById(a.getAttribute('data-nav')); });
    function sync() {
      var mid = window.scrollY + 90, cur = null;
      secs.forEach(function (s) { if (s && s.offsetTop <= mid) cur = s.id; });
      anchors.forEach(function (a) {
        a.classList.toggle('on', a.getAttribute('data-nav') === cur);
      });
    }
    window.addEventListener('scroll', sync, { passive: true });
    sync();
  }

  /* ---------- 3) 实时数据 ---------- */
  function stamp(text) {
    var el = document.getElementById('stamp-time');
    if (el) el.textContent = text;
  }
  function pick(d, path) {
    if (!d) return undefined;
    return String(path).split('.').reduce(function (o, k) {
      return (o === undefined || o === null) ? undefined : o[k];
    }, d);
  }

  function applyStats(d) {
    Array.prototype.forEach.call(document.querySelectorAll('[data-stat]'), function (el) {
      var v = pick(d, el.getAttribute('data-stat'));
      if (v !== undefined && v !== null) el.textContent = v;
    });
    // 账号年龄：由 created_at 现场推算，避免写死后过期
    Array.prototype.forEach.call(document.querySelectorAll('[data-months]'), function (el) {
      var v = pick(d, el.getAttribute('data-months'));
      var t = v ? new Date(v).valueOf() : NaN;
      if (!isNaN(t)) {
        var m = Math.floor((Date.now() - t) / 2592000000);
        if (m >= 0) el.textContent = (m >= 12 ? Math.floor(m / 12) + ' 年 ' + (m % 12) + ' 月' : m + ' 月');
      }
    });
    // 迷你语言条：任何 [data-langbars="n"] 容器都按字节占比渲染前 n 名
    Array.prototype.forEach.call(document.querySelectorAll('[data-langbars]'), function (box) {
      var lb = pick(d, 'github.lang_bytes');
      if (!lb) return;
      var ks = Object.keys(lb);
      var n = parseInt(box.getAttribute('data-langbars'), 10) || 4;
      ks = ks.slice(0, n);
      var total = ks.reduce(function (s, k) { return s + lb[k]; }, 0);
      box.innerHTML = '';
      ks.forEach(function (k) {
        var pct = total ? (lb[k] / total * 100) : 0;
        var w = window.ZL.el('div', 'bar');
        var t = window.ZL.el('div', 'bar__t');
        t.appendChild(window.ZL.el('b', null, k));
        t.appendChild(window.ZL.el('span', null, pct.toFixed(1) + '%'));
        w.appendChild(t);
        var tr = window.ZL.el('div', 'bar__track');
        var fl = window.ZL.el('div', 'bar__fill');
        fl.setAttribute('data-pct', pct.toFixed(1));
        tr.appendChild(fl);
        w.appendChild(tr);
        box.appendChild(w);
      });
      window.ZL.bars(box);
    });

    if (d && d.updated_at) {
      var dt = new Date(d.updated_at);
      stamp(isNaN(dt.valueOf()) ? d.updated_at
        : (dt.getMonth() + 1) + '月' + dt.getDate() + '日 '
        + ('0' + dt.getHours()).slice(-2) + ':' + ('0' + dt.getMinutes()).slice(-2));
    }
  }

  window.ZL = {
    /* 读一个 JSON，失败返回 null 并且不抛错 */
    json: function (url) {
      return fetch(url, { cache: 'no-store' })
        .then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); });
    },
    stats: function () {
      return window.ZL.json('/data/stats.json').then(applyStats).catch(function () { stamp('静态快照'); });
    },
    /* 条形图动画：[data-pct="62"] → width 62% */
    bars: function (root) {
      var bs = (root || document).querySelectorAll('[data-pct]');
      Array.prototype.forEach.call(bs, function (b) {
        var v = parseFloat(b.getAttribute('data-pct'));
        if (!isNaN(v)) requestAnimationFrame(function () { b.style.width = Math.max(0, Math.min(100, v)) + '%'; });
      });
    },
    el: function (tag, cls, text) {
      var e = document.createElement(tag);
      if (cls) e.className = cls;
      if (text !== undefined && text !== null) e.textContent = text;
      return e;
    },

    /* 极简 Markdown → HTML。先整体转义再解析，杜绝 README 里的 HTML 注入。 */
    md: function (src) {
      if (!src) return '';
      var esc = function (s) {
        return s.replace(/&/g, '&amp;').replace(/</g, '&lt;')
          .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
      };
      var inline = function (s) {
        s = esc(s);
        s = s.replace(/`([^`]+)`/g, '<code>$1</code>');
        s = s.replace(/!\[([^\]]*)\]\((https?:[^)\s]+)\)/g,
          function (m, a, u) { return '<img alt="' + a + '" src="' + u + '" loading="lazy">'; });
        s = s.replace(/\[([^\]]+)\]\((https?:[^)\s]+|#[^)\s]*)\)/g,
          '<a href="$2" target="_blank" rel="noopener noreferrer">$1</a>');
        s = s.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
        s = s.replace(/(^|[^*])\*([^*]+)\*/g, '$1<em>$2</em>');
        return s;
      };

      var lines = String(src).replace(/\r\n?/g, '\n').split('\n');
      var out = [], inCode = false, code = [], inList = null, para = [];

      function flushPara() {
        if (para.length) { out.push('<p>' + inline(para.join(' ')) + '</p>'); para = []; }
      }
      function flushList() {
        if (inList) { out.push('</' + inList + '>'); inList = null; }
      }
      function flush() { flushPara(); flushList(); }

      for (var i = 0; i < lines.length; i++) {
        var ln = lines[i];
        if (/^```/.test(ln)) {
          if (inCode) { out.push('<pre><code>' + esc(code.join('\n')) + '</code></pre>'); code = []; inCode = false; }
          else { flush(); inCode = true; }
          continue;
        }
        if (inCode) { code.push(ln); continue; }

        if (/^\s*$/.test(ln)) { flush(); continue; }

        var h = ln.match(/^(#{1,4})\s+(.*)$/);
        if (h) { flush(); var lv = Math.min(h[1].length, 3); out.push('<h' + lv + '>' + inline(h[2]) + '</h' + lv + '>'); continue; }

        if (/^(---|\*\*\*|___)\s*$/.test(ln)) { flush(); out.push('<hr>'); continue; }

        var li = ln.match(/^\s*[-*+]\s+(.*)$/) || ln.match(/^\s*\d+[.)]\s+(.*)$/);
        if (li) {
          flushPara();
          var tag = /^\s*\d/.test(ln) ? 'ol' : 'ul';
          if (inList !== tag) { flushList(); out.push('<' + tag + '>'); inList = tag; }
          out.push('<li>' + inline(li[1]) + '</li>');
          continue;
        }

        if (/^>\s?/.test(ln)) { flush(); out.push('<blockquote>' + inline(ln.replace(/^>\s?/, '')) + '</blockquote>'); continue; }
        if (/^\|.*\|$/.test(ln)) { flush(); continue; }  // 表格暂不渲染

        flushList();
        para.push(ln);
      }
      if (inCode) out.push('<pre><code>' + esc(code.join('\n')) + '</code></pre>');
      flush();
      return out.join('\n');
    },
    /* 相对时间：2026-09-30T20:34:21+08:00 → "3 天前" */
    ago: function (iso) {
      var t = new Date(iso).valueOf();
      if (isNaN(t)) return '';
      var s = (Date.now() - t) / 1000;
      if (s < 60) return '刚刚';
      if (s < 3600) return Math.floor(s / 60) + ' 分钟前';
      if (s < 86400) return Math.floor(s / 3600) + ' 小时前';
      if (s < 2592000) return Math.floor(s / 86400) + ' 天前';
      if (s < 31536000) return Math.floor(s / 2592000) + ' 个月前';
      return Math.floor(s / 31536000) + ' 年前';
    },
    ymd: function (iso) {
      var d = new Date(iso);
      if (isNaN(d.valueOf())) return '';
      return d.getFullYear() + '-' + ('0' + (d.getMonth() + 1)).slice(-2) + '-' + ('0' + d.getDate()).slice(-2);
    }
  };

  window.ZL.stats();
})();
