"""Offline macOS narration -> Manim chapters -> portable, subtitled MP4.

Run in the project's paper_reader environment. See README.md for reproduction.
"""
from __future__ import annotations
import argparse
import hashlib
import html
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys
import wave

HERE = Path(__file__).resolve().parent
PAPER = HERE.parents[1]
WORK = PAPER / 'tmp/video-mac'
LESSON = json.loads((HERE / 'lesson.json').read_text())


def run(args, **kwargs):
    return subprocess.run([str(x) for x in args], check=True, **kwargs)


def duration(path):
    return float(subprocess.check_output(['ffprobe', '-v', 'error', '-show_entries',
                 'format=duration', '-of', 'csv=p=0', str(path)], text=True).strip())


def voice():
    audio = WORK / 'audio'
    audio.mkdir(parents=True, exist_ok=True)
    manifest = []
    for ci, chapter in enumerate(LESSON['chapters']):
        rows = []
        for bi, beat in enumerate(chapter['beats']):
            stem = audio / f'{ci:02}-{bi:02}'
            config = dict(beat, voice=LESSON['voice'])
            fingerprint = hashlib.sha256(json.dumps(config, ensure_ascii=False).encode()).hexdigest()
            if not stem.with_suffix('.wav').exists() or not stem.with_suffix('.sha256').exists() or stem.with_suffix('.sha256').read_text() != fingerprint:
                stem.with_suffix('.txt').write_text(beat['text'])
                run(['say', '-v', LESSON['voice'], '-r', str(beat['rate']), '-f', stem.with_suffix('.txt'), '-o', stem.with_suffix('.aiff')])
                run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', '-i', stem.with_suffix('.aiff'),
                     '-ac', '1', '-ar', '48000', '-c:a', 'pcm_s16le', stem.with_suffix('.wav')])
                stem.with_suffix('.aiff').unlink()
                stem.with_suffix('.sha256').write_text(fingerprint)
            with wave.open(str(stem.with_suffix('.wav'))) as sound:
                seconds = sound.getnframes() / sound.getframerate()
            rows.append(dict(beat, audio=str(stem.with_suffix('.wav')), duration=seconds))
        manifest.append(dict(chapter, beats=rows))
        print(f'Voice {ci+1:02}: {sum(x["duration"] for x in rows):.1f}s', flush=True)
    (WORK / 'voice.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2))
    estimate = sum(b['duration'] + b.get('pause', .55) for c in manifest for b in c['beats']) + len(manifest) * 1.4
    print(f'Estimated duration: {estimate:.1f}s', flush=True)
    if estimate >= 594:
        raise ValueError('Narration exceeds the ten-minute budget; revise the script before rendering.')


def render(quality, selected):
    settings = {'preview': ('854,480', '12'), 'final': ('1920,1080', '24')}
    resolution, fps = settings[quality]
    for ci in selected:
        media = WORK / quality / f'{ci:02}'
        media.mkdir(parents=True, exist_ok=True)
        env = dict(os.environ, ATTENTION_CHAPTER=str(ci), ATTENTION_WORK=str(WORK), ATTENTION_QUALITY=quality)
        env['PATH'] = '/Library/TeX/texbin:' + env.get('PATH', '')
        log = media / 'render.log'
        with log.open('w') as output:
            try:
                run([sys.executable, '-m', 'manim', 'render', HERE / 'scenes.py', 'LessonScene',
                     '-r', resolution, '--fps', fps, '--media_dir', media, '--progress_bar', 'none',
                     '--verbosity', 'WARNING', '--disable_caching', '-o', f'chapter-{ci:02}'],
                    env=env, stdout=output, stderr=subprocess.STDOUT)
            except subprocess.CalledProcessError:
                print(log.read_text()[-6000:], flush=True)
                raise
        print(f'Render {ci+1:02}/{len(LESSON["chapters"])}: {LESSON["chapters"][ci]["title"]}', flush=True)


def stamp(seconds):
    value = round(seconds * 1000)
    h, value = divmod(value, 3600000)
    m, value = divmod(value, 60000)
    s, ms = divmod(value, 1000)
    return f'{h:02}:{m:02}:{s:02},{ms:03}'


def package(quality):
    paths, chapters, subtitles, beats = [], [], [], []
    offset = 0.0
    for ci, chapter in enumerate(LESSON['chapters']):
        files = list((WORK / quality / f'{ci:02}' / 'videos').glob(f'**/chapter-{ci:02}.mp4'))
        if len(files) != 1:
            raise ValueError(f'Expected exactly one rendered chapter {ci}: {files}')
        path = files[0]
        span = duration(path)
        timeline = json.loads((WORK / quality / f'timing-{ci:02}.json').read_text())
        chapters.append({'title': chapter['title'], 'start': offset, 'end': offset + span})
        for beat in timeline:
            start, end = offset + beat['start'], offset + beat['end']
            subtitles += [str(len(beats) + 1), f'{stamp(start)} --> {stamp(end)}', beat['text'], '']
            beats.append(dict(beat, start=start, end=end, chapter=ci))
        paths.append(path)
        offset += span
    if offset >= 600:
        raise ValueError(f'Video duration {offset:.1f}s exceeds 10 minutes')
    concat = WORK / quality / 'concat.txt'
    concat.write_text(''.join("file '" + str(p).replace("'", "'\\''") + "'\n" for p in paths))
    srt = HERE / 'attention-from-scratch.srt' if quality == 'final' else WORK / quality / 'preview.srt'
    srt.write_text('\n'.join(subtitles))
    metadata = [';FFMETADATA1', 'title=' + LESSON['title'], 'comment=Original educational diagrams; illustrative numerical example; offline macOS synthesis.']
    for c in chapters:
        metadata += ['[CHAPTER]', 'TIMEBASE=1/1000', f'START={round(c["start"]*1000)}', f'END={round(c["end"]*1000)}', 'title=' + c['title']]
    meta = WORK / quality / 'chapters.ffmeta'
    meta.write_text('\n'.join(metadata))
    out = HERE / 'attention-from-scratch.mp4' if quality == 'final' else WORK / quality / 'preview.mp4'
    run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', '-f', 'concat', '-safe', '0', '-i', concat,
         '-i', srt, '-i', meta, '-map', '0:v:0', '-map', '0:a:0', '-map', '1:0', '-map_metadata', '2', '-map_chapters', '2',
         '-c:v', 'libx264', '-preset', 'slow', '-crf', '25', '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '80k',
         '-af', 'loudnorm=I=-18:TP=-2:LRA=9', '-c:s', 'mov_text', '-metadata:s:s:0', 'language=zho',
         '-metadata:s:a:0', 'language=zho', '-movflags', '+faststart', out])
    report = {'title': LESSON['title'], 'duration': duration(out), 'bytes': out.stat().st_size, 'chapters': chapters, 'beats': beats}
    (WORK / quality / 'timeline.json').write_text(json.dumps(report, ensure_ascii=False, indent=2))
    if quality == 'final':
        (HERE / 'chapters.json').write_text(json.dumps(chapters, ensure_ascii=False, indent=2))
        poster_beat=next(b for b in beats if b['chapter']==4 and b['beat']==3)
        run(['ffmpeg','-hide_banner','-loglevel','error','-y','-ss',str((poster_beat['start']+poster_beat['end'])/2),
             '-i',out,'-frames:v','1','-vf','scale=1280:-1',HERE/'poster.jpg'])
        player(out, chapters)
    print(json.dumps({'video': str(out), 'seconds': report['duration'], 'MiB': report['bytes']/1024**2}, ensure_ascii=False), flush=True)


def player(out, chapters):
    buttons = ''.join(f'<button data-time="{c["start"]:.3f}"><span>{i+1:02}</span>{html.escape(c["title"])}</button>' for i,c in enumerate(chapters))
    page = '''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>让词语交换信息 · 数学动画</title><style>
*{box-sizing:border-box}body{margin:0;background:#0c1018;color:#e8eaf0;font:16px/1.8 system-ui,"PingFang SC",sans-serif}main{max-width:1120px;margin:48px auto;padding:0 24px}small{letter-spacing:.18em;color:#68d4e8}h1{font-size:38px;line-height:1.3;margin:16px 0}p{color:#a6afc0}video{width:100%;background:#080b11;border-radius:12px}.chapters{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin:20px 0 40px}button{background:#161e2d;border:1px solid #283347;color:#dfe5f1;padding:12px;text-align:left;cursor:pointer;border-radius:6px;font:inherit;font-size:14px}button:hover{border-color:#68d4e8}button span{color:#68d4e8;margin-right:10px}a{color:#68d4e8}details{margin:36px 0;border-top:1px solid #283347;padding-top:20px}summary{cursor:pointer}details video{margin-top:20px}@media(max-width:650px){main{margin:24px auto;padding:0 16px}h1{font-size:28px}.chapters{grid-template-columns:1fr 1fr}}
</style><main><small>从几何直觉，到可计算的模型</small><h1>让词语交换信息</h1><p>从注意力到 Transformer · 中文旁白与字幕 · 1080p · 不需要预先读过论文</p>
<video id="movie" controls preload="metadata" poster="poster.jpg" src="attention-from-scratch.mp4"></video><div class="chapters">BUTTONS</div>
<p><a href="attention-from-scratch.mp4" download>下载新版 MP4</a> · <a href="attention-from-scratch.srt" download>下载字幕</a> · <a href="../../note.html#teaching-video">返回阅读笔记</a></p>
<details><summary>对照旧版（Windows 制作，约 5 分钟）</summary><video controls preload="none" src="attention-explained.mp4"></video><p>旧版原文件保留，便于比较讲解、节奏与画面。</p></details>
<p>面向具备基础线性代数、概率论与简单机器学习知识的初学者。二维数字和语言线索均为教学构造，不代表训练后模型的真实内部状态。中文旁白由 macOS 本地语音合成。</p></main>
<script>const v=document.querySelector('#movie');document.querySelectorAll('[data-time]').forEach(b=>b.onclick=()=>{v.currentTime=+b.dataset.time;v.play().catch(()=>{});});</script></html>'''
    (HERE / 'video.html').write_text(page.replace('BUTTONS', buttons))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage', choices=['voice', 'render', 'package', 'all'])
    parser.add_argument('--quality', choices=['preview','final'], default='final')
    parser.add_argument('--chapters', help='zero-based comma-separated chapter indices; rendering only')
    args = parser.parse_args()
    WORK.mkdir(parents=True, exist_ok=True)
    (WORK / '.gitignore').write_text('*\n')
    if args.stage in ('voice','all'): voice()
    if args.stage in ('render','all'):
        selected = [int(x) for x in args.chapters.split(',')] if args.chapters else range(len(LESSON['chapters']))
        render(args.quality, selected)
    if args.stage in ('package','all'): package(args.quality)


if __name__ == '__main__':
    main()
