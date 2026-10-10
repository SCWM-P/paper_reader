# 让词语交换信息：从注意力到 Transformer

面向具备基本线性代数、概率论与简单机器学习知识的大一本科生。不要求读过论文。
以二维向量为主线，依次解释上下文、Q/K/V、点积、缩放、softmax、加权平均、批量计算、多头、位置、因果遮罩和编码器／解码器。
深色背景、稳定的角色配色、几何构造与逐步推导借鉴数学可视化课程的表现方式；所有画面和讲稿为本次编写。

## 播放

- `video.html`：新版章节导航与旧版对照。
- `attention-from-scratch.mp4`：新版，8 分 34 秒，1080p/24fps，约 11.2 MiB；中文合成旁白、画面字幕、可切换字幕轨与章节信息。
- `attention-from-scratch.srt`：按独立语音段的真实起止时间生成的字幕。
- `attention-explained.mp4`：原 Windows 成片，保留原始文件作为对照。

## 在 Mac 上重做

从项目根目录使用 `pyproject.toml` 中的环境。系统须有 FFmpeg、TeX（`latex`、`dvisvgm`）、中文字体 PingFang SC，以及 `say` 的 Tingting 语音。

```bash
conda activate paper_reader
python -m pip install -e '.[video]'
python 'papers/EXAMPLE/Attention Is All You Need/assets/videos/build.py' all
```

`build.py` 使用本机 `say`，不连接语音服务。每一段旁白单独合成、测量，再与相应动画同步；复杂的计算段使用较低语速并增加停顿。
`lesson.json` 保存文本、分段语速和停顿。`scenes.py` 保存 Manim 0.21.0 动画，`ATTENTION_FONT` 可覆盖字体。
音频、TeX/SVG 缓存、分段视频及日志写入本篇论文的 `tmp/video-mac/`，不进入 Git。

分步重做、预览或修改某一章：

```bash
python 'papers/EXAMPLE/Attention Is All You Need/assets/videos/build.py' voice
python 'papers/EXAMPLE/Attention Is All You Need/assets/videos/build.py' render --quality preview
python 'papers/EXAMPLE/Attention Is All You Need/assets/videos/build.py' package --quality preview
# 从 0 开始编号；例如，只重做点积和加权汇总两章。
python 'papers/EXAMPLE/Attention Is All You Need/assets/videos/build.py' render --chapters 2,4
python 'papers/EXAMPLE/Attention Is All You Need/assets/videos/build.py' package
```

完整正式渲染必须覆盖全部 12 章。修改旁白后先执行 `voice`，然后重做对应画面并重新打包。
预览采用 480p/12fps；正式版采用 1080p/24fps。打包会检查总时长小于 600 秒。
成片采用 H.264/AAC，支持通常的浏览器和系统播放器；字幕已画入画面，播放器可切换字幕轨可按需启用。

## 教学数字与边界

贯穿示例使用 `q=[1,0]`，`K=[[2,1],[0,2],[-1,1]]`，`V=[[1,0],[0,2],[2,1]]`，`d_k=2`。
结果由 NumPy 计算：权重 `[0.73368111,0.17837015,0.08794874]`，输出 `[0.90957858,0.44468905]`。
点积同时受方向与长度影响；softmax 权重是读取份额，不是事实可信度。
二维参数、词语语境、各头分工和训练分布变化均是教学构造，不代表某个已训练模型的真实内部状态。
注意力输出位于值向量凸包内的结论，针对单头、非负归一化权重的加权平均；后续输出投影及残差不受这一限制。
缩放推导使用各坐标乘积近似独立、方差相近的示意条件。
完整模型图聚焦信息流；逐位置网络、残差与层归一化先在独立章节解释。

## 制作检查

运行 `python 'papers/EXAMPLE/Attention Is All You Need/assets/videos/verify.py'` 检查数值、视频流、字幕、章节、音量统计和十分钟限制。
画面审阅应覆盖每一段字幕的中间与结束状态，特别检查公式截断、标签重叠、遮罩方向及旁白是否先于必要画面。
最终语音仍是系统合成语音，不能等同于真人演播；教学节奏与声音偏好可继续按实际观看反馈调整。

工具参考：[Manim 场景 API](https://docs.manim.community/en/stable/reference/manim.scene.scene.Scene.html)、[FFmpeg 文档](https://ffmpeg.org/ffmpeg.html)。
