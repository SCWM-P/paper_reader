# 前端来源与许可

界面布局和视觉取材于 [nashsu/llm_wiki](https://github.com/nashsu/llm_wiki)，本地参考提交为 `48fd970e206a02a6d2028d1dbfc41b7a0345bf0b`。直接改编的主题变量位于 `src/theme.css`；其余组件按 Python API 重写。

Copyright 2024–2026 Yong Su。上游 GPL-3.0 全文保留在 `LICENSE`，构建时从 `public/UPSTREAM_LICENSE.txt` 一并分发。前端改编代码遵循该许可，不能仅保留视觉而删除来源和许可。

React、Geist、Lucide、React Markdown、KaTeX、Mermaid、Graphology、Sigma 和相关运行依赖的版权及许可汇总于 `public/THIRD_PARTY_NOTICES.txt`。该文件包含 npm 生产依赖树中的许可正文；构建工具本身不进入浏览器包。

复现构建：`npm ci && npm run build`。构建产物写入 Python 核心包的 `static/`；构建清空旧产物，公共许可文件随后随资源复制。运行时不依赖 Node、Rust、参考仓库或 CDN。
