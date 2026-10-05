#!/usr/bin/env python3
"""Render the Manim scene and package MP4, subtitles and chapter metadata.

Select an isolated environment containing requirements.txt; TeX must be on PATH.
The audio directory can contain WAV narration created on any operating system.
Windows can generate it with voice.ps1. FFmpeg is used for final packaging.
"""
import argparse
import html
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PAPER = HERE.parents[1]


def stamp(seconds):
    milliseconds=round(seconds*1000)
    h,rest=divmod(milliseconds,3600000);m,rest=divmod(rest,60000);s,ms=divmod(rest,1000)
    return f'{h:02}:{m:02}:{s:02},{ms:03}'


def package(video, out, ffmpeg):
    out=Path(out).resolve();out.parent.mkdir(parents=True,exist_ok=True)
    chapters=json.loads((PAPER/'tmp/video/chapters.json').read_text(encoding='utf-8'))
    metadata=[';FFMETADATA1','title=Attention Is All You Need — 注意力与多头注意力',
              'comment=Vaswani et al., NIPS 2017; illustrative Q/K/V example; Manim Community.']
    subtitles=[]
    number=1
    for chapter in chapters:
        metadata += ['[CHAPTER]','TIMEBASE=1/1000',f'START={round(chapter["start"]*1000)}',
                     f'END={round(chapter["end"]*1000)}','title='+chapter['title']]
        # Sentence boundaries are proportionally timed to the recorded chapter WAV.
        # The scene also burns a concise chapter subtitle directly into its frames.
        sentences=[s.strip() for s in re.findall(r'[^。！？]+[。！？]?',chapter['text']) if s.strip()]
        duration=chapter['end']-chapter['start']-1
        total=sum(len(s) for s in sentences)
        elapsed=chapter['start']
        for sentence in sentences:
            end=elapsed+duration*len(sentence)/total
            subtitles += [str(number),f'{stamp(elapsed)} --> {stamp(end)}',sentence,'']
            elapsed=end;number+=1
    srt=out.with_suffix('.srt');srt.write_text('\n'.join(subtitles),encoding='utf-8')
    (out.parent/'chapters.json').write_text(json.dumps(chapters,ensure_ascii=False,indent=2),encoding='utf-8')
    meta=PAPER/'tmp/video/chapters.ffmeta';meta.write_text('\n'.join(metadata),encoding='utf-8')
    subprocess.run([ffmpeg,'-hide_banner','-loglevel','error','-y','-i',str(video),'-i',str(srt),
                    '-i',str(meta),'-map','0:v:0','-map','0:a:0','-map','1:0','-map_metadata','2',
                    '-map_chapters','2','-c:v','copy','-c:a','copy','-c:s','mov_text',
                    '-metadata:s:s:0','language=zho','-movflags','+faststart',str(out)],check=True)
    # A local companion player exposes chapter seeking and optional subtitles.
    vtt='WEBVTT\n\n'+re.sub(r'(\d{2}:\d{2}:\d{2}),(\d{3})',r'\1.\2','\n'.join(subtitles))
    data=json.dumps(vtt,ensure_ascii=False).replace('<','\\u003c')
    buttons=''.join(f'<button data-time="{c["start"]:.3f}"><span>{i+1:02d}</span>{html.escape(c["title"])}</button>' for i,c in enumerate(chapters))
    player='''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Attention Is All You Need · 数学动画</title><style>
    *{box-sizing:border-box}body{margin:0;background:#0b1020;color:#e3e9f5;font:16px/1.8 system-ui,'Microsoft YaHei',sans-serif}main{max-width:1200px;margin:auto;padding:36px 24px}h1{font-size:30px;margin:8px 0 12px}p{color:#acbbd2}a{color:#68b6ff}video{width:100%;border:1px solid #2e405b;border-radius:14px;background:#080c16}.chapters{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin:24px 0}button{font:inherit;text-align:left;color:inherit;background:#152239;border:1px solid #2e405b;padding:12px;border-radius:8px;cursor:pointer}button:hover{border-color:#68b6ff}button span{color:#68b6ff;margin-right:14px}.meta{font-size:13px}details{border-top:1px solid #2e405b;padding-top:16px}summary{cursor:pointer}li{margin:8px 0}@media(max-width:700px){.chapters{grid-template-columns:1fr 1fr}h1{font-size:24px}main{padding:24px 16px}}
    </style></head><body><main><p class="meta">PAPER EXPLAINER · Vaswani et al. · NIPS 2017</p><h1>从一次点积，到多头注意力</h1><p>中文旁白 · 1080p 数学动画 · 9 章 · 约 5 分钟</p><video id="movie" controls preload="metadata" src="VIDEO_FILE"></video><div class="chapters">CHAPTER_BUTTONS</div><p><a href="../../note.html#visual-lab">打开交互阅读笔记</a> · <a href="attention-explained.mp4" download>下载 MP4</a> · <a href="attention-explained.srt" download>下载字幕</a></p><details><summary>计算示例与制作说明</summary><ul><li>教学输入 X=[[1,0,1,0],[0,1,0,2],[1,1,2,1]]。Head 1 的 Q/K 取前两维，V 取后两维；Head 2 的 Q/K 取后两维，V 取前两维。</li><li>单头示例权重约 [0.401,0.198,0.401]，输出 [1.203,0.797]；另一个头的输出 [0.860,0.716]。HTML 演示可逐项核对完整矩阵。</li><li>采用 Manim Community 绘制矢量动画，Windows 系统中文语音生成旁白；画面保留章节摘要字幕。全文字幕按句长估计时间，可在播放器字幕菜单开启。</li><li>完整论文架构与原图见阅读笔记。此视频的架构图突出数据流；残差、LayerNorm 和位置编码由旁白说明。</li></ul><p>依据：<a href="https://papers.nips.cc/paper_files/paper/2017/file/3f5ee243547dee91fbd053c1c4a845aa-Paper.pdf">官方会议 PDF</a>。制作代码与旁白位于本视频目录。</p></details></main><script>
    const movie=document.getElementById('movie');document.querySelectorAll('[data-time]').forEach(b=>b.addEventListener('click',()=>{movie.currentTime=Number(b.dataset.time);movie.play().catch(error=>{if(error.name!=='AbortError') console.warn('Playback:',error.message);});}));
    const track=document.createElement('track');track.kind='subtitles';track.label='中文全文';track.srclang='zh';track.src=URL.createObjectURL(new Blob([SUBTITLE_DATA],{type:'text/vtt'}));movie.append(track);
    </script></body></html>'''
    player=player.replace('VIDEO_FILE',html.escape(out.name,quote=True)).replace('CHAPTER_BUTTONS',buttons).replace('SUBTITLE_DATA',data)
    (out.parent/'video.html').write_text(player,encoding='utf-8')
    print(json.dumps({'video':str(out),'subtitles':str(srt),'chapters':len(chapters)},ensure_ascii=False))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--audio',default=str(PAPER/'tmp/video/audio'))
    p.add_argument('--out',default=str(HERE/'attention-explained.mp4'))
    p.add_argument('--ffmpeg',default=shutil.which('ffmpeg'))
    p.add_argument('--existing-video',help='package an already rendered video')
    a=p.parse_args()
    if not a.ffmpeg:
        p.error('FFmpeg must be on PATH or provided with --ffmpeg')
    video=Path(a.existing_video) if a.existing_video else PAPER/'tmp/video/manim/videos/scenes/1080p30/AttentionExplained.mp4'
    if not a.existing_video:
        env=dict(os.environ,ATTENTION_AUDIO=str(Path(a.audio).resolve()))
        subprocess.run([sys.executable,'-m','manim','render',str(HERE/'scenes.py'),'AttentionExplained',
                        '-qh','--fps','30','--media_dir',str(PAPER/'tmp/video/manim'),
                        '--progress_bar','none','--verbosity','WARNING'],cwd=PAPER,env=env,check=True)
    package(video,a.out,a.ffmpeg)
