# 部署到 EdgeOne Makers（腾讯云，免翻墙）

GitHub Pages（github.io）在中国大陆被墙，本文件记录 EdgeOne Makers 的部署方式。
EdgeOne Makers 免费版：5GB 总存储 / 40 个项目 / 500 次构建每月，默认域名 `*.edgeone.app` 免备案、大陆直连。

## 已配置内容

仓库根目录的 `edgeone.json` 已将输出目录固定为 `web/dist`（仓库里已提交的静态产物，无需构建）：

```json
{
  "outputDirectory": "web/dist"
}
```

## 控制台操作（一次性）

1. 登录 EdgeOne Makers 控制台：https://console.tencentcloud.com/edgeone/makers ，点「立即开通」。
2. 绑定 GitHub：控制台 → 单击 **Github** → 授权 EdgeOne 访问仓库（可只授权 market_news）。
3. 选择仓库 `market_news`，进入构建配置：
   - 框架预设：无（纯静态，仓库没有 package.json，不需要自动识别框架）
   - 根目录：留空（默认 `./`）
   - 输出目录：`web/dist`（edgeone.json 已固化，控制台不填也会生效）
   - 构建命令：留空
4. 加速区域：选「全球/海外」——默认域名免备案；以后加自定义域名也免备案。
5. 点「开始部署」，等待构建完成，打开生成的 `https://<project>.edgeone.app` 验证。

## 验证

- 首页 `index.html` 会刷新跳转到 `reports/2026-08-16-0800.html`（最新一期报告）。
- 打开报告页，确认 assets（CSS/JS）加载正常。
- 大陆用户直接访问该域名即可，无需翻墙。

## 自动部署

生产环境绑定 `main` 分支：之后每次 push 到 main，EdgeOne 自动重新构建部署。
预览环境绑定其他分支，用于测试。

## 常见问题

- **构建失败**：若报找不到构建命令/产物为空，在「项目设置 - 构建部署配置」把构建命令填 `true`（空操作）后重新部署。
- **自定义域名**：EdgeOne 控制台添加域名后按提示配置 DNS CNAME；「全球/海外」加速区域无需备案。
- **GitHub Pages 保留**：现有 pages.yml 工作流不用动，GitHub Pages 继续作为国际访问入口，两条线并存。

## 参考资料

- 导入 Git 仓库：https://pages.edgeone.ai/zh/document/importing-a-git-repository
- 构建流程与设置指南：https://pages.edgeone.ai/zh/document/build-guide
- edgeone.json 配置：https://pages.edgeone.ai/zh/document/edgeone-json
- 免费额度：https://pages.edgeone.ai/zh/document/limits-and-quotas
