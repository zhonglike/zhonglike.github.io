# zhonglike.tech 安全加固清单

威胁模型判断：本站是**纯静态多页站点**（7 个页面 + 404），无后端、无数据库、无表单、无第三方脚本。
因此 SQL 注入 / 命令注入 / XSS 服务端链路**不适用**，真正的高危面排在下面。

---

## 第一层：页面自身（已完成 ✅）

| 项目 | 状态 | 说明 |
| --- | --- | --- |
| CSP 元标签 | ✅ | `default-src 'none'`，只放行内联样式脚本与 data: 图片，其余全禁。后续若引入第三方脚本会被直接阻断 |
| Referrer-Policy | ✅ | `no-referrer`，外链不泄露来源 |
| 外部请求极少 | ✅ | 无 CDN / 无字体 / 无统计脚本；仅同源 `data/*.json` 与少量平台头像（GitHub / B站）走 https |
| `rel="noopener noreferrer"` | ✅ | 全部外链已加，防 `window.opener` 反向控制 |
| noscript 兜底 | ✅ | 禁用 JS 时内容照常显示（原先会整页空白） |
| 声明唯一官方域名 | ✅ | 页脚标注，反钓鱼仿冒 |

> 注意：GitHub Pages **不允许自定义响应头**，所以 HSTS、`X-Content-Type-Options`、
> `X-Frame-Options` 这类**响应头级**防护只能通过 Cloudflare 或 Cloudflare Pages 实现。

---

## 证书台账（2026-10-01 登记）

已申请到 `zhonglike.tech` 的 DV 证书（DigiCert 颁发），但**当前架构用不上**，原因见下。

| 项 | 值 |
| --- | --- |
| 颁发对象 | `CN=zhonglike.tech` |
| SAN | `zhonglike.tech`、`www.zhonglike.tech` |
| 颁发机构 | DigiCert `Encryption Everywhere DV TLS CA - G2` |
| 有效期 | 2026-10-01 → **2027-04-01**（6 个月，免费证书） |
| 私钥 | RSA 2048 位，与证书配对已验证一致 |
| 格式 | PEM（证书链 2 段）+ KEY；另有 JKS（Tomcat 用，密码见下载包内 txt） |

### ⚠️ 为什么现在用不上

**GitHub Pages 不支持上传自定义证书。** 自定义域名的 HTTPS 只能由 GitHub 通过
Let's Encrypt 自动签发，控制台没有上传入口 —— 这份 DigiCert 证书在当前托管架构下无处可用。

同理，Cloudflare Free 也不支持上传自定义证书（需 Business 以上的 Advanced Certificate
Manager），Vercel / Netlify 同样是平台自动签发。

### 三条可选路径

| 方案 | 这份证书 | 代价 |
| --- | --- | --- |
| 继续 GitHub Pages，等自动签发 | ❌ 闲置 | 零成本，但要等 GitHub 完成签发 |
| 迁 Cloudflare | ❌ 用 CF 自己的证书 | NS 改到 CF，HTTPS 立刻可用；国内访问可能变慢 |
| 自建服务器 / VPS | ✅ 可以用 | 需公网服务器；境内服务器还需 ICP 备案 |

**当前建议**：维持 GitHub Pages 等待自动签发。DNS 已完全正确、无 CAA 限制，通常 24h 内完成；
签好后跑一次 `scripts/../enforce_https.py` 即可开启强制 HTTPS 跳转。

### 🔴 私钥保管红线

- `zhonglike.tech.key` **绝不能**提交进任何 Git 仓库，也不要放进 `zhonglike-portal/` 或 `deploy-zhonglike-tech/`
- 不要截图私钥、不要贴进聊天窗口、不要上传到网盘
- 已核查：工作区内不含任何私钥文件
- 2027-03 起需关注到期；若届时仍在 GitHub Pages 则无需任何操作（平台自动续期）

---

## 第二层：账号与注册商（最高优先级 ⚠️ 尚未完成）

这一层比任何技术方案都重要 —— **域名被劫持的话，前面所有防护都是零**。

### GitHub 账号
- [ ] 开启 **2FA**（推荐硬件密钥 > 认证器 App > 短信）：https://github.com/settings/security
- [ ] 撤销已泄露的 PAT：https://github.com/settings/tokens
- [ ] 检查授权应用与 SSH 密钥：https://github.com/settings/keys
- [ ] 开启私有邮箱Protection + 提交签名（可选）

### 阿里云账号（域名注册商）
- [ ] 开启 **MFA 二次验证**
- [ ] 开启 **域名锁定 / 禁止转移**（防非法转出，这条最关键）
- [ ] 开启操作告警通知（转出、DNS 变更即时短信）
- [ ] 检查联系人信息没被恶意篡改
- [ ] 账号密码唯一且长，不与其他站复用

### DNS 层
- [ ] Aliyun 云解析加 4 条 `@` A → 185.199.108~111.153
- [ ] `www` CNAME → zhonglike.github.io
- [ ] 添加 **CAA 记录**（只允许指定 CA 签发证书，防伪造证书中间人）
- [ ] 若注册商支持，**开启 DNSSEC**（防 DNS 缓存投毒）

---

## 第三层：邮件防伪（2026-10-04 实测更新）

域名**已在用飞书域名邮箱**，`han@zhonglike.tech` 可正常收发信，因此不再适用"拒绝全部"策略。

### 当前实测状态

| 记录 | 现状 | 判定 |
| --- | --- | --- |
| MX | `mx1/mx2/mx3.feishu.cn`（优先级 1 / 5 / 10） | ✅ 已生效 |
| SPF | `v=spf1 +include:_netblocks.m.feishu.cn -all` | ✅ 已配置，且以 `-all` 严格收尾 |
| DMARC | **无记录**（NXDOMAIN） | ⚠️ 待补 |
| DKIM | 需飞书邮箱后台开启后按提示回填 | ⚠️ 待确认 |

### 待补的记录

| 主机记录 | 类型 | 记录值 |
| --- | --- | --- |
| _dmarc | TXT | `v=DMARC1; p=quarantine; rua=mailto:han@zhonglike.tech; adkim=r; aspf=r` |
| （DKIM） | TXT | 飞书邮箱后台生成后按提示添加 |

DMARC 先设 `p=quarantine` 观察一段时间，确认没有误伤正常邮件，再改成 `p=reject`。

### 公开邮箱的副作用

`han@zhonglike.tech` 已出现在 `/links/` 与 `/about/` 页面上，会被爬虫抓取，垃圾邮件会增多。
建议飞书侧开启垃圾邮件过滤，并避免在其他公开场合重复暴露这个地址。

---

## 第四层：套 Cloudflare（DDoS / WAF / 缓存）

GitHub Pages 本身已在 Fastly 后面，有一定抗 DDoS 能力。再套 Cloudflare 主要增益：
WAF 规则、Bot 攻击模式、速率限制、DNSSEC 一键开、HSTS 响应头、宕机兜底页。

**步骤**
1. Cloudflare 添加站点 `zhonglike.tech`（选 Free）
2. Aliyun 控制台把 NS 改成 Cloudflare 给的两条（如 `xxx.ns.cloudflare.com`）
   - 改 NS 前务必把现有解析记录**先抄到 Cloudflare**，否则会断解析
3. SSL/TLS → 概览选 **Full (Strict)**
4. SSL/TLS → 边缘证书 → 开启 **Always Use HTTPS** + **HSTS**（含 preload）
5. DNS → 开启 **DNSSEC**，然后把 DS 记录回填到阿里云（若阿里云支持）
6. 安全 → 机器人 → 开启 **Bot Fight Mode**
7. WAF → 自定义规则加一条速率限制（例如 1 分钟 > 200 请求即质询）
8. 缓存 → 配置规则：静态资源缓存

**必须知道的取舍 ⚠️**
Cloudflare Free 在**中国大陆访问可能变慢甚至不稳**。如果主要访客在国内，
建议先在国内与境外各测一次；否则维持现状（GitHub Pages + 阿里云 DNS）也够用，
重点把第二层账号安全做扎实。

---

## 日常排查命令

```powershell
nslookup -type=A zhonglike.tech
nslookup -type=NS zhonglike.tech
nslookup -type=CAA zhonglike.tech
nslookup -type=TXT _dmarc.zhonglike.tech
Resolve-DnsName zhonglike.tech -Type A
```

上线后建议用 https://securityheaders.com 与 https://ssllabs.com/ssltest 复检。
