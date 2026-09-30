# zhonglike.tech

个人门户站，静态单文件站点，托管于 GitHub Pages。

- 首页：`index.html`（自包含，无外部依赖）
- 自定义域名：`CNAME` = zhonglike.tech
- `.nojekyll`：跳过 Jekyll 构建，避免资源被过滤

## 部署

1. 在 GitHub 新建仓库 `zhonglike.github.io`（公开）
2. 设置里 Pages → Branch: `main` / `root` → Custom domain: `zhonglike.tech`
3. 阿里云云解析 DNS 里添加记录（见下方）

## DNS 记录（阿里云 → 云解析 DNS）

| 主机记录 | 记录类型 | 记录值 |
| --- | --- | --- |
| @   | A | 185.199.108.153 |
| @   | A | 185.199.109.153 |
| @   | A | 185.199.110.153 |
| @   | A | 185.199.111.153 |
| www | CNAME | zhonglike.github.io |

IPv6 可选：@ 添加 4 条 AAAA → 2606:50c0:8000::153 / 8001 / 8002 / 8003::153
