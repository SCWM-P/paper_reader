"""Check this lesson's calculations and packaged local artifact; no network or API calls."""
import hashlib
import json
from pathlib import Path
import re
import subprocess
import numpy as np

HERE=Path(__file__).resolve().parent
PAPER=HERE.parents[1]
EXPECTED_OLD='7cf814d42b2841a4286fe266162674edb75229d2394b095a36ab42cd5ff74de0'


def main():
    q=np.array([1.,0.]);k=np.array([[2.,1.],[0.,2.],[-1.,1.]]);v=np.array([[1.,0.],[0.,2.],[2.,1.]])
    s=q@k.T/np.sqrt(2);w=np.exp(s-s.max());w/=w.sum();z=w@v
    assert np.allclose(w,[.73368111,.17837015,.08794874])
    assert np.allclose(z,[.90957858,.44468905]) and np.isclose(w.sum(),1)
    # The query rotation used in the geometric chapter preserves a convex combination.
    for angle in np.linspace(-np.pi/3,np.pi/2,41):
        scores=np.array([np.cos(angle),np.sin(angle)])@k.T/np.sqrt(2)
        a=np.exp(scores-scores.max());a/=a.sum()
        assert np.all(a>=0) and np.isclose(a.sum(),1)
    lesson=json.loads((HERE/'lesson.json').read_text())
    assert len(lesson['chapters'])==12
    speech=[b['text'] for c in lesson['chapters'] for b in c['beats']]
    assert not any(re.search('论文|Vaswani|第三节|图二|参考文献',t) for t in speech)
    assert hashlib.sha256((HERE/'attention-explained.mp4').read_bytes()).hexdigest()==EXPECTED_OLD
    path=HERE/'attention-from-scratch.mp4'
    probe=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_format','-show_streams','-show_chapters','-of','json',str(path)],text=True))
    streams={s['codec_type']:s for s in probe['streams']}
    assert streams['video']['codec_name']=='h264'
    assert (streams['video']['width'],streams['video']['height'])==(1920,1080)
    assert streams['video']['r_frame_rate']=='24/1'
    assert streams['audio']['codec_name']=='aac'
    assert streams['subtitle']['codec_name']=='mov_text'
    seconds=float(probe['format']['duration'])
    assert 0<seconds<600
    assert len(probe['chapters'])==12
    previous=0
    for chapter in probe['chapters']:
        start,end=float(chapter['start_time']),float(chapter['end_time'])
        assert start>=previous-.003 and start<end<=seconds+.1
        previous=end
    subtitles=(HERE/'attention-from-scratch.srt').read_text()
    assert subtitles.count(' --> ')==len(speech)
    result=subprocess.run(['ffmpeg','-hide_banner','-i',str(path),'-af','volumedetect','-vn','-sn','-f','null','-'],text=True,capture_output=True,check=True)
    volume=re.findall(r'(?:mean_volume|max_volume):\s*([^\n]+)',result.stderr)
    assert len(volume)==2 and float(volume[1].split()[0])<0
    sizes={str(p.relative_to(PAPER)):p.stat().st_size for p in PAPER.rglob('*') if p.is_file() and 'tmp' not in p.relative_to(PAPER).parts}
    report={'video_seconds':seconds,'video_MiB':path.stat().st_size/1024**2,'chapters':len(probe['chapters']),
            'speech_beats':len(speech),'resolution':'1920x1080/24fps','audio_volume':volume,
            'weights':w.tolist(),'output':z.tolist(),'old_video_unchanged':True,'instance_without_tmp_MiB':sum(sizes.values())/1024**2}
    print(json.dumps(report,ensure_ascii=False,indent=2))


if __name__=='__main__':main()
