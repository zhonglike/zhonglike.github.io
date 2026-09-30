# zhonglike.tech 安全加固清单

威胁模型判断：本站是**纯静态单文件**，无后端、无数据库、无表单、无第三方脚本。
因此 SQL 注入 / 命令注入 / XSS 服务端链路**不适用**，真正的高危面排在下面。

---

## 第一层：页面自身（已完成 ✅）

| 项目 | 状态 | 说明 |
| --- | --- | --- |
| CSP 元标签 | ✅ | `default-src 'none'`，只放行内联样式脚本与 data: 图片，其余全禁。后续若引入第三方脚本会被直接阻断 |
| Referrer-Policy | ✅ | `no-referrer`，外链不泄露来源 |
| 外部请求归零 | ✅ | 头像是 base64 内联，无 CDN、无字体、无统计脚本 |
| `rel="noopener noreferrer"` | ✅ | 全部外链已加，防 `window.opener` 反向控制 |
| noscript 兜底 | ✅ | 禁用 JS 时内容照常显示（原先会整页空白） |
| 声明唯一官方域名 | ✅ | 页脚标注，反钓鱼仿冒 |

> 注意：GitHub Pages **不允许自定义响应头**，所以 HSTS、`X-Content-Type-Options`、
> `X-Frame-Options` 这类**响应头级**防护只能通过 Cloudflare 或 Cloudflare Pages 实现。

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

## 第三层：邮件防伪（防被冒名发信）

若该域名**不发信**，直接发布"拒绝全部"策略，等于堵死被冒名钓鱼的口子：

| 主机记录 | 类型 | 记录值 |
| --- | --- | --- |
| @ | TXT | `v=spf1 -all` |
| _dmarc | TXT | `v=DMARC1; p=reject; adkim=s; aspf=s` |
| *._domainkey | TXT | `v=DKIM1; p=` |

若将来要用域名邮箱（如 Google Workspace），再按需替换 SPF/DKIM。

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
