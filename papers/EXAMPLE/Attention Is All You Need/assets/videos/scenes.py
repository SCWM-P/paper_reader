"""Original geometric lessons, synchronized to individually synthesized speech beats."""
from pathlib import Path
import json
import math
import os
import textwrap
import numpy as np
from manim import *

HERE = Path(__file__).resolve().parent
WORK = Path(os.environ.get('ATTENTION_WORK', HERE.parents[1] / 'tmp/video-mac'))
CI = int(os.environ.get('ATTENTION_CHAPTER', '0'))
QUALITY = os.environ.get('ATTENTION_QUALITY', 'final')
CHAPTER = json.loads((WORK / 'voice.json').read_text())[CI]
FONT = os.environ.get('ATTENTION_FONT', 'PingFang SC')
BG, INK, MUTED, GRID = '#0B0E14', '#EEF1F6', '#97A3B6', '#283342'
QC, KC, VC, OC = '#68D5ED', '#F4C66B', '#72DEB5', '#F28FAF'
config.background_color = BG
config.max_files_cached = 500

KEYS = np.array([[2., 1.], [0., 2.], [-1., 1.]])
VALUES = np.array([[1., 0.], [0., 2.], [2., 1.]])
QUERIES = np.array([[1., 0.], [0., 1.], [1., 1.]])


def weights(query):
    scores = query @ KEYS.T / np.sqrt(2)
    e = np.exp(scores - np.max(scores, axis=-1, keepdims=True))
    return e / e.sum(axis=-1, keepdims=True)


def txt(value, size=27, color=INK):
    return Text(value, font=FONT, font_size=size, color=color)


def tex(value, size=42, color=INK):
    return MathTex(value, font_size=size, color=color)


def at(obj, x, y):
    return obj.move_to([x, y, 0])


def caption_lines(value):
    """Balance short lines and keep punctuation off the start of a line."""
    count=max(1,math.ceil(len(value)/40))
    lines=[]
    while count>1:
        target=round(len(value)/count)
        candidates=[i+1 for i,c in enumerate(value) if c in '，。；：？！' and abs(i+1-target)<=7]
        split=min(candidates,key=lambda i:abs(i-target)) if candidates else target
        while split<len(value) and (value[split] in '，。；：？！、' or (value[split-1].isascii() and value[split].isascii() and value[split-1].isalpha() and value[split].isalpha())):
            split+=1
        lines.append(value[:split].strip());value=value[split:].strip();count-=1
    lines.append(value)
    return lines


def label_box(value, x=0, y=0, color=QC, width=2.5, height=.7, size=24):
    box = RoundedRectangle(width=width, height=height, corner_radius=.1,
                           stroke_width=1.5, stroke_color=color, fill_color=color, fill_opacity=.075)
    label = txt(value, size, color)
    if label.width > width - .25: label.scale_to_fit_width(width - .25)
    return at(VGroup(box, label), x, y)


def arrow(start, end, color=INK, **kwargs):
    return Arrow(start, end, color=color, buff=.15, stroke_width=2.5, max_tip_length_to_length_ratio=.14, **kwargs)


def bars(values, labels, x=0, y=-1.5, width=1.0, spacing=1.65, height=2.5, color=VC, digits=3):
    result = VGroup()
    for i, (v, label) in enumerate(zip(values, labels)):
        xx = x + (i - (len(values)-1)/2) * spacing
        rect = Rectangle(width=width, height=max(.015, float(v)*height), stroke_width=0, fill_color=color, fill_opacity=.8)
        rect.move_to([xx, y + rect.height/2, 0])
        number = txt(f'{v:.{digits}f}', 25, color).next_to(rect, UP, buff=.14)
        name = txt(label, 23, MUTED).move_to([xx, y-.32, 0])
        result.add(VGroup(rect, number, name))
    return result


def grid(values, x=-1.8, y=0, width=.9, color=QC, fmt='.2f'):
    result = VGroup()
    for i, row in enumerate(values):
        for j, value in enumerate(row):
            cell = Square(side_length=width, stroke_color=GRID, stroke_width=1.4,
                          fill_color=color, fill_opacity=min(.85,.07+.5*max(0, float(value))))
            label = txt(format(value, fmt), 22, INK)
            result.add(at(VGroup(cell, label), x+(j-(len(row)-1)/2)*width, y+((len(values)-1)/2-i)*width))
    return result


class LessonScene(Scene):
    def construct(self):
        title = txt(CHAPTER['title'], 35).to_edge(LEFT, buff=.65).set_y(3.3)
        counter = txt(f'{CI+1:02} / 12', 19, MUTED).to_edge(RIGHT, buff=.65).set_y(3.3)
        line = Line([-6.45, 2.82, 0], [6.45, 2.82, 0], stroke_color=GRID, stroke_width=1)
        band = Rectangle(width=14.23, height=1.05, fill_color=BG, fill_opacity=.98, stroke_width=0).move_to([0,-3.45,0])
        self.fixed = [title, counter, line, band]
        self.add(*self.fixed)
        self.caption = None
        self.timeline = []
        getattr(self, CHAPTER['id'])()
        self.wait(.7)
        out = WORK / QUALITY / f'timing-{CI:02}.json'
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(self.timeline, ensure_ascii=False, indent=2))

    def beat(self, index, *animations, run_time=2.0, action=None):
        row = CHAPTER['beats'][index]
        if self.caption is not None: self.remove(self.caption)
        lines = caption_lines(row['text'])
        self.caption = Paragraph(*lines, font=FONT, font_size=22, line_spacing=.6, alignment='center', color=INK)
        if self.caption.width > 12.8: self.caption.scale_to_fit_width(12.8)
        self.caption.move_to([0,-3.38,0]).set_z_index(20)
        self.add(self.caption)
        start = self.time
        self.add_sound(row['audio'])
        if animations: self.play(*animations, run_time=run_time)
        if action: action()
        target = row['duration'] + row.get('pause', .55)
        self.wait(max(.15, target-(self.time-start)))
        self.timeline.append({'text':row['text'], 'start':start, 'end':self.time,
                              'speech_end':start+row['duration'], 'beat':index})

    def clear_body(self):
        body = [m for m in self.mobjects if m not in self.fixed and m is not self.caption]
        if body: self.play(*[FadeOut(m) for m in body], run_time=.5)

    def context(self):
        a = at(txt('deposit at the bank', 37), 0, 1.5)
        b = at(txt('sit by the river bank', 37), 0, -.25)
        ta = at(txt('把钱存进银行', 26, KC), 0, .82)
        tb = at(txt('坐在河岸边', 26, VC), 0, -.93)
        self.beat(0, FadeIn(a, shift=UP*.15), FadeIn(b, shift=UP*.15), FadeIn(ta), FadeIn(tb))
        def vectors():
            self.clear_body()
            word = label_box('bank', -4.8, 0, QC, 1.8)
            raw = at(tex(r'\begin{bmatrix}0.2\\-0.4\\0.7\\\vdots\end{bmatrix}', 36, QC), -2.5, 0)
            contexts = VGroup(label_box('存款的上下文', 2.8, 1, KC, 3.2), label_box('河流的上下文', 2.8, -1, VC, 3.2))
            self.play(FadeIn(word), GrowArrow(arrow(word.get_right(), raw.get_left(), QC)), FadeIn(raw), run_time=1.5)
            self.play(FadeIn(contexts), run_time=1)
            self.play(GrowArrow(arrow(raw.get_right(),contexts[0].get_left(),KC)),GrowArrow(arrow(raw.get_right(),contexts[1].get_left(),VC)),run_time=1.4)
        self.beat(1, action=vectors)
        question = at(txt('读谁？    读多少？', 43, QC), 0, -2.05)
        self.beat(2, Write(question), run_time=2)
        def steps():
            self.clear_body()
            boxes = VGroup(*[label_box(v,x,0,c,3.25,1.1,31) for v,x,c in [('比较线索',-4.4,QC),('分配权重',0,KC),('汇总内容',4.4,VC)]])
            self.play(LaggedStart(*[FadeIn(b,shift=UP*.15) for b in boxes],lag_ratio=.25),run_time=2)
            self.play(*[GrowArrow(arrow(boxes[i].get_right(),boxes[i+1].get_left(),MUTED)) for i in range(2)],run_time=1.5)
        self.beat(3, action=steps)

    def roles(self):
        tokens = VGroup(*[label_box(w,x,1.55,QC,2) for w,x in [('我',-4),('读',0),('书',4)]])
        rows = VGroup(*[at(tex(r'x_'+str(i+1)+r'=[\cdots]',34,QC),x,.35) for i,x in enumerate([-4,0,4])])
        self.beat(0, FadeIn(tokens), LaggedStart(*[FadeIn(r,shift=DOWN*.2) for r in rows],lag_ratio=.25))
        def project():
            self.clear_body()
            source=at(tex('x_i',64),-4.7,0)
            self.add(source)
            self.roles=VGroup()
            for y,term,color in [(1.5,r'q_i=x_iW^Q',QC),(0,r'k_i=x_iW^K',KC),(-1.5,r'v_i=x_iW^V',VC)]:
                equation=at(tex(term,43,color),-.3,y)
                self.roles.add(equation)
                self.play(GrowArrow(arrow(source.get_right(),equation.get_left(),color)),Write(equation),run_time=1.1)
        self.beat(1,action=project)
        names=VGroup(*[at(txt(v,27,c),4.0,y) for v,c,y in [('找什么？',QC,1.5),('怎样匹配？',KC,0),('取回什么？',VC,-1.5)]])
        self.beat(2,LaggedStart(*[FadeIn(v) for v in names],lag_ratio=.4),run_time=2.5)
        note=at(txt('W 的参数由训练学习',26,MUTED),0,-2.35)
        self.beat(3,FadeIn(note),*[Indicate(v,color=OC) for v in self.roles],run_time=2.3)

    def dot(self):
        plane=NumberPlane(x_range=[-1.5,2.6,1],y_range=[-.5,2.5,1],x_length=5.6,y_length=4.05,
            background_line_style={'stroke_color':GRID,'stroke_opacity':.6,'stroke_width':1},axis_config={'stroke_color':MUTED,'stroke_width':1.5}).move_to([-3.15,0,0])
        origin=plane.c2p(0,0)
        q=Arrow(origin,plane.c2p(1,0),buff=0,color=QC,stroke_width=7)
        keys=VGroup(*[Arrow(origin,plane.c2p(*k),buff=0,color=KC,stroke_width=3.5) for k in KEYS])
        labs=VGroup(*[tex('k_'+str(i+1),27,KC).next_to(keys[i].get_end(),UP if i!=2 else LEFT,buff=.08) for i in range(3)])
        qlab=at(tex(r'q=(1,0)',35,QC),-3,-2.35)
        self.beat(0,Create(plane),GrowArrow(q),LaggedStart(*[GrowArrow(k) for k in keys],lag_ratio=.25),FadeIn(labs),FadeIn(qlab),run_time=3)
        eqs=VGroup(*[at(tex(t,36,KC),3.2,y) for t,y in [(r'q\cdot k_1=1(2)+0(1)=2',1.3),(r'q\cdot k_2=1(0)+0(2)=0',.05),(r'q\cdot k_3=1(-1)+0(1)=-1',-1.2)]])
        for e in eqs:
            if e.width>5.6:e.scale_to_fit_width(5.6)
        proj=DashedLine(plane.c2p(2,1),plane.c2p(2,0),color=KC,stroke_width=2)
        self.beat(1,Write(eqs[0]),Create(proj),Indicate(keys[0]),run_time=2.7)
        self.beat(2,Write(eqs[1]),Write(eqs[2]),Indicate(keys[1]),Indicate(keys[2]),run_time=3)
        highlighted=Line(origin,plane.c2p(2,0),color=KC,stroke_width=7).set_opacity(.6)
        self.beat(3,Create(highlighted),run_time=2)
        def rotate():
            self.play(FadeOut(proj),FadeOut(highlighted),run_time=.4)
            self.play(Transform(q,Arrow(origin,plane.c2p(0,1),buff=0,color=QC,stroke_width=7)),Transform(qlab,at(tex(r'q=(0,1)',35,QC),-3,-2.35)),run_time=2.5)
            new=VGroup(*[at(tex(t,36,KC),3.2,y) for t,y in [(r'q\cdot k_1=1',1.3),(r'q\cdot k_2=2',.05),(r'q\cdot k_3=1',-1.2)]])
            self.play(*[Transform(a,b) for a,b in zip(eqs,new)],run_time=1.5)
        self.beat(4,action=rotate)

    def softmax(self):
        raw=at(tex(r'[2,\;0,\;-1]',60,KC),0,.7)
        name=at(txt('匹配分数',27,MUTED),0,1.9)
        self.beat(0,Write(raw),FadeIn(name),run_time=2)
        scaled=at(tex(r'\frac{[2,\;0,\;-1]}{\sqrt{2}}\approx[1.414,\;0,\;-0.707]',43,KC),0,.9)
        variance=at(tex(r'\mathrm{Var}\!\left(\sum_{r=1}^{d_k}q_rk_r\right)\approx d_k',34,MUTED),0,-.7)
        assumption=at(txt('示意条件：各乘积近似独立，方差约为 1',24,MUTED),0,-1.65)
        self.beat(1,Transform(raw,scaled),Write(variance),FadeIn(assumption),run_time=3)
        self.beat(2,Circumscribe(raw,color=QC,buff=.18),run_time=2)
        def exponentiate():
            self.clear_body()
            self.formula=at(tex(r'e^{[1.414,\;0,\;-0.707]}\approx[4.113,\;1,\;0.493]',39,KC),0,1.8)
            self.chart=bars([4.113,1,.493],['位置 1','位置 2','位置 3'],height=.55,color=KC)
            self.play(Write(self.formula),LaggedStart(*[GrowFromEdge(b,DOWN) for b in self.chart],lag_ratio=.2),run_time=3)
        self.beat(3,action=exponentiate)
        normalized=at(tex(r'a_j=\frac{e^{s_j}}{\sum_\ell e^{s_\ell}}',43,VC),0,1.8)
        weighted=bars(weights(QUERIES[0]),['位置 1','位置 2','位置 3'],height=2.8,color=VC)
        self.beat(4,Transform(self.formula,normalized),Transform(self.chart,weighted),run_time=3.4)
        total=at(tex(r'a_1+a_2+a_3=1',34,VC),0,-2.35)
        self.beat(5,Write(total),run_time=1.8)

    def values(self):
        plane=NumberPlane(x_range=[-.25,2.5,.5],y_range=[-.25,2.5,.5],x_length=4.7,y_length=4.1,
            background_line_style={'stroke_color':GRID,'stroke_opacity':.5,'stroke_width':1},axis_config={'stroke_color':MUTED,'stroke_width':1}).move_to([-3.25,0,0])
        origin=plane.c2p(0,0)
        vectors=VGroup(*[Arrow(origin,plane.c2p(*v),buff=0,color=VC,stroke_width=4) for v in VALUES])
        labels=VGroup(*[tex('v_'+str(i+1),27,VC).next_to(vectors[i].get_end(),RIGHT,buff=.1) for i in range(3)])
        equations=VGroup(*[at(tex(s,36,VC),3.1,y) for s,y in [(r'v_1=(1,0)',1.5),(r'v_2=(0,2)',0),(r'v_3=(2,1)',-1.5)]])
        self.beat(0,Create(plane),LaggedStart(*[GrowArrow(v) for v in vectors],lag_ratio=.2),FadeIn(labels),FadeIn(equations),run_time=3)
        alpha=weights(QUERIES[0]); parts=alpha[:,None]*VALUES
        scaled=VGroup(*[Arrow(origin,plane.c2p(*p),buff=0,color=VC,stroke_width=4) for p in parts])
        terms=VGroup(*[at(tex(s,35,VC),3.1,y) for s,y in [(r'a_1v_1\approx(0.734,0)',1.5),(r'a_2v_2\approx(0,0.357)',0),(r'a_3v_3\approx(0.176,0.088)',-1.5)]])
        for t in terms:
            if t.width>5.7:t.scale_to_fit_width(5.7)
        self.beat(1,Transform(vectors,scaled),FadeOut(labels),*[Transform(a,b) for a,b in zip(equations,terms)],run_time=3.3)
        output=alpha@VALUES
        cumulative=np.cumsum(parts,axis=0)
        chain=VGroup(*[Arrow(plane.c2p(*(np.zeros(2) if i==0 else cumulative[i-1])),plane.c2p(*cumulative[i]),buff=0,color=VC,stroke_width=4) for i in range(3)])
        result=at(tex(r'z=\sum_j a_jv_j\approx(0.910,0.445)',35,OC),2.5,-2.35)
        if result.width>6.8:result.scale_to_fit_width(6.8)
        dot=Dot(plane.c2p(*output),radius=.075,color=OC)
        self.beat(2,Transform(vectors,chain),FadeIn(dot),Write(result),run_time=3.4)
        triangle=Polygon(*[plane.c2p(*v) for v in VALUES],color=VC,stroke_width=2,fill_color=VC,fill_opacity=.1)
        corners=VGroup(*[Dot(plane.c2p(*v),radius=.045,color=VC) for v in VALUES])
        self.beat(3,FadeOut(vectors),Create(triangle),FadeIn(corners),Indicate(dot,color=OC,scale_factor=1.8),run_time=3)
        def mix():
            self.play(FadeOut(equations),FadeOut(result),run_time=.5)
            tracker=ValueTracker(0)
            dot.add_updater(lambda m:m.move_to(plane.c2p(*(weights(np.array([np.cos(tracker.get_value()),np.sin(tracker.get_value())]))@VALUES))))
            caption=at(txt('查询转动，混合比例随之改变',27,QC),3.1,.7)
            self.play(FadeIn(caption),tracker.animate.set_value(np.pi/2),run_time=4,rate_func=smooth)
            self.play(tracker.animate.set_value(-np.pi/3),run_time=2.5,rate_func=smooth)
            dot.clear_updaters()
        self.beat(4,action=mix)

    def matrix(self):
        q=at(tex(r'Q=\begin{bmatrix}q_1\\q_2\\q_3\end{bmatrix}',49,QC),-3.7,.1)
        rows=at(txt('一行 = 一个查询',29,QC),2.7,.1)
        self.beat(0,Write(q),FadeIn(rows),run_time=2.5)
        def scores():
            self.clear_body()
            self.table=grid(QUERIES@KEYS.T,x=-2.2,width=1,color=KC,fmt='.0f')
            self.col=at(txt('被读取的位置 →',24,MUTED),-2.2,2.0)
            self.row=at(txt('读\n取\n者',23,MUTED),-4.25,0)
            self.f=at(tex(r'S=QK^{\mathsf T}',45,KC),3.0,.65)
            self.dim=at(tex(r'(3\times2)(2\times3)=3\times3',30,MUTED),2.6,-.4)
            self.play(FadeIn(self.table),FadeIn(self.col),FadeIn(self.row),Write(self.f),Write(self.dim),run_time=3)
            self.play(Create(SurroundingRectangle(VGroup(*self.table[:3]),color=QC,buff=.05)),run_time=1)
        self.beat(1,action=scores)
        normalized=grid(weights(QUERIES),x=-2.2,width=1,color=VC)
        formula=at(tex(r'A=\operatorname{softmax}_{\rm row}\!\left(S/\sqrt{d_k}\right)',35,VC),2.5,.8)
        if formula.width>6:formula.scale_to_fit_width(6)
        output=at(tex(r'Z=AV\quad(3\times2)',42,OC),2.6,-.65)
        self.beat(2,Transform(self.table,normalized),Transform(self.f,formula),Transform(self.dim,output),run_time=3.5)
        cost=at(tex(r'n\text{ positions}\quad\Longrightarrow\quad n^2\text{ scores}',35,MUTED),0,-2.25)
        self.beat(3,Write(cost),run_time=2)

    def heads(self):
        source=label_box('输入 X',-5.1,0,INK,1.6)
        head1=label_box('注意力头 1',-.8,0,QC,3)
        edge=arrow(source.get_right(),head1.get_left(),QC)
        self.beat(0,FadeIn(source),GrowArrow(edge),FadeIn(head1),run_time=2)
        head2=label_box('注意力头 2',-.8,-1.2,KC,3)
        def split():
            self.play(FadeOut(edge),head1.animate.set_y(1.2),run_time=.8)
            self.play(FadeIn(head2),GrowArrow(arrow(source.get_right(),head1.get_left(),QC)),GrowArrow(arrow(source.get_right(),head2.get_left(),KC)),run_time=1.5)
            self.play(FadeIn(at(tex(r'W_1^Q,W_1^K,W_1^V',28,QC),-.8,2.1)),FadeIn(at(tex(r'W_2^Q,W_2^K,W_2^V',28,KC),-.8,-2.1)),run_time=1)
        self.beat(1,action=split)
        concat=at(tex(r'[z^{(1)}\mid z^{(2)}]W^O',38,OC),3.7,0)
        if concat.width>4.8:concat.scale_to_fit_width(4.8)
        self.beat(2,GrowArrow(arrow(head1.get_right(),concat.get_left(),QC)),GrowArrow(arrow(head2.get_right(),concat.get_left(),KC)),Write(concat),run_time=3)
        learned=at(txt('并行的视角  ·  学到的分工',28,MUTED),0,-2.55)
        self.beat(3,FadeIn(learned),Indicate(head1),Indicate(head2),run_time=2)

    def position(self):
        row1=VGroup(*[label_box(v,x,1.2,c,1.8) for v,x,c in [('猫',-3.4,QC),('追',0,KC),('狗',3.4,VC)]])
        row2=VGroup(*[label_box(v,x,-1,c,1.8) for v,x,c in [('狗',-3.4,VC),('追',0,KC),('猫',3.4,QC)]])
        self.beat(0,FadeIn(row1),FadeIn(row2),run_time=2)
        edges=VGroup(*[Line(row1[i].get_bottom(),row2[2-i].get_top(),color=[QC,KC,VC][i],stroke_width=2) for i in range(3)])
        equation=at(tex(r'\operatorname{Attn}(PX)=P\operatorname{Attn}(X)',34,MUTED),0,-2.3)
        self.beat(1,Create(edges),Write(equation),FadeIn(at(txt('P 表示交换行的位置',20,MUTED),0,-1.75)),run_time=3)
        def waves():
            self.clear_body()
            axes=Axes(x_range=[0,8,2],y_range=[-1.2,1.2,1],x_length=7.2,y_length=3.1,
                      axis_config={'color':GRID,'include_tip':False}).move_to([-2,0,0])
            curves=VGroup(*[axes.plot(lambda x,w=w:np.sin(x*w),x_range=[0,8,.05],color=c,stroke_width=2.5) for w,c in [(1,QC),(.4,KC),(.15,VC)]])
            self.play(Create(axes),LaggedStart(*[Create(c) for c in curves],lag_ratio=.2),run_time=3)
            marker=DashedLine(axes.c2p(3,-1.1),axes.c2p(3,1.1),color=INK)
            p=at(tex(r'p_3=\begin{bmatrix}\sin(3\omega_1)\\\cos(3\omega_1)\\\vdots\end{bmatrix}',33,KC),4.2,0)
            self.play(Create(marker),Write(p),run_time=2)
            self.add(at(txt('横轴：位置    颜色：不同频率',23,MUTED),-2,-2.3))
        self.beat(2,action=waves)
        def add_positions():
            self.clear_body()
            eq=at(tex(r'\underbrace{x_i}_{\text{content}}+\underbrace{p_i}_{\text{position}}',58),0,.45)
            eq.set_color_by_tex('x_i',QC)
            names=at(txt('是什么                   在哪里',29,KC),0,-1.25)
            self.play(Write(eq),FadeIn(names),run_time=2.5)
        self.beat(3,action=add_positions)

    def mask(self):
        n=4
        initial=np.ones((n,n))*.35
        table=grid(initial,x=-2.2,width=.83,color=QC,fmt='.0f')
        for cell in table:cell[1].set_opacity(0)
        words=at(txt('我    想    喝    水',26),-2.2,2.15)
        rowlabels=VGroup(*[at(txt(v,23,MUTED),-4.35,(1.5-i)*.83) for i,v in enumerate(['我','想','喝','水'])])
        now=at(txt('当前位置：想',29,QC),3,1.2)
        nextword=at(txt('预测下一个词：喝',29,OC),3,0)
        self.beat(0,FadeIn(table),FadeIn(words),FadeIn(rowlabels),FadeIn(now),FadeIn(nextword),run_time=2.3)
        blocked=VGroup()
        for i in range(n):
            for j in range(i+1,n):
                cell=table[i*n+j]
                blocked.add(at(tex(r'-\infty',24,OC),*cell.get_center()[:2]))
        inf=at(tex(r'e^{-\infty}=0',44,OC),3,-1.45)
        self.beat(1,FadeIn(blocked),Write(inf),*[table[i*n+j][0].animate.set_fill(OC,opacity=.16) for i in range(n) for j in range(i+1,n)],run_time=3)
        note=at(tex(r'j\leq i',42,VC),-2.2,-2.35)
        self.beat(2,Write(note),*[Indicate(table[i*n+j][0],color=VC) for i in range(n) for j in range(i+1)],run_time=3)
        def generate():
            self.clear_body()
            top=VGroup(*[label_box(v,x,1.0,QC,1.9) for v,x in zip(['<开始>','我','想','喝'],[-4.5,-1.5,1.5,4.5])])
            bottom=VGroup(*[label_box(v,x,-.5,VC,1.9) for v,x in zip(['我','想','喝','水'],[-4.5,-1.5,1.5,4.5])])
            self.play(FadeIn(top),FadeIn(at(txt('训练：各行并行',25,MUTED),0,2.2)),run_time=.8)
            self.play(*[GrowArrow(arrow(a.get_bottom(),b.get_top(),VC)) for a,b in zip(top,bottom)],FadeIn(bottom),run_time=1.5)
            self.play(FadeIn(at(txt('生成：一个接一个',25,MUTED),0,-1.65)),run_time=.6)
            for b in bottom:self.play(Indicate(b,color=OC),run_time=.7)
        self.beat(3,action=generate)

    def block(self):
        attention=label_box('多头注意力',-1.1,1.65,QC,3.4)
        norm1=label_box('加回输入 + 层归一化',-1.1,.55,MUTED,3.4,.58,21)
        ffn=label_box('逐位置前馈网络',-1.1,-.55,VC,3.4)
        norm2=label_box('加回输入 + 层归一化',-1.1,-1.65,MUTED,3.4,.58,21)
        original_edge=arrow(attention.get_bottom(),ffn.get_top(),MUTED)
        self.beat(0,FadeIn(attention),FadeIn(ffn),GrowArrow(original_edge),run_time=2.5)
        formula=at(tex(r'\operatorname{ReLU}(xW_1+b_1)W_2+b_2',29,VC),3.6,-.5)
        if formula.width>4.2:formula.scale_to_fit_width(4.2)
        self.beat(1,Write(formula),Circumscribe(ffn,color=VC),run_time=2.5)
        def residual():
            self.play(FadeIn(norm1),FadeIn(norm2),FadeOut(formula),FadeOut(original_edge),run_time=1)
            self.play(GrowArrow(arrow(attention.get_bottom(),norm1.get_top(),MUTED)),GrowArrow(arrow(norm1.get_bottom(),ffn.get_top(),MUTED)),run_time=.8)
            for top,bottom in [(2.25,.55),(-.03,-1.65)]:
                bypass=VMobject(color=OC,stroke_width=2).set_points_as_corners([[-1.1,top,0],[-4.4,top,0],[-4.4,bottom,0],[-2.85,bottom,0]])
                self.play(Create(bypass),run_time=1.1)
            self.play(GrowArrow(arrow(ffn.get_bottom(),norm2.get_top(),MUTED)),run_time=.6)
            self.add(at(txt('归一化：先减均值，再按波动大小缩放',21,MUTED),2.2,-2.5))
        self.beat(2,action=residual)
        def stack():
            self.clear_body()
            boxes=VGroup(*[label_box('交换信息  +  逐位置加工',0,y,c,6,.85,28) for y,c in [(1.65,QC),(.05,VC),(-1.55,OC)]])
            self.play(LaggedStart(*[FadeIn(b,shift=UP*.15) for b in boxes],lag_ratio=.3),run_time=2)
            self.play(*[GrowArrow(arrow(boxes[i].get_bottom(),boxes[i+1].get_top(),MUTED)) for i in range(2)],run_time=1.5)
            self.add(*[at(txt(f'第 {i+1} 层',24,MUTED),-4.4,b.get_y()) for i,b in enumerate(boxes)])
        self.beat(3,action=stack)

    def model(self):
        source=label_box('猫在睡觉',-4,-1.6,INK,3)
        encoder=label_box('编码器',-4,.25,QC,3,1.5,34)
        encname=at(txt('读取整句输入',24,QC),-4,1.8)
        self.beat(0,FadeIn(source),GrowArrow(arrow(source.get_top(),encoder.get_bottom(),QC)),FadeIn(encoder),FadeIn(encname),run_time=2.5)
        prefix=label_box('已生成：The',1.8,-2,INK,3.3,.6,23)
        mask=label_box('带遮罩的自注意力',1.8,-.9,KC,3.8,.65,24)
        cross=label_box('交叉注意力',1.8,.4,VC,3.8,.7,27)
        qarrow=arrow(mask.get_top(),cross.get_bottom(),QC)
        kvarrow=arrow(encoder.get_right(),cross.get_left(),VC)
        qname=at(tex('Q',26,QC),2.1,-.24)
        kvname=at(tex('K,V',28,VC),-1.25,.9)
        self.beat(1,FadeIn(prefix),FadeIn(mask),GrowArrow(arrow(prefix.get_top(),mask.get_bottom(),KC)),FadeIn(cross),GrowArrow(qarrow),GrowArrow(kvarrow),FadeIn(qname),FadeIn(kvname),FadeIn(at(txt('解码器',27,VC),1.8,1.8)),run_time=4)
        def distribution():
            self.clear_body()
            self.b=bars([.55,.25,.2],['cat','dog','runs'],height=3.5,spacing=2.4,color=QC)
            self.head=at(txt('The  →  下一个词？',32,INK),0,1.95)
            self.play(FadeIn(self.head),LaggedStart(*[GrowFromEdge(b,DOWN) for b in self.b],lag_ratio=.2),run_time=3)
            self.add(at(txt('词表分布（示意）',23,MUTED),0,-2.35))
        self.beat(2,action=distribution)
        updated=bars([.72,.18,.1],['cat','dog','runs'],height=3.5,spacing=2.4,color=VC)
        self.beat(3,Transform(self.head,at(txt('正确目标：cat  →  调整参数',30,VC),0,1.95)),Transform(self.b,updated),run_time=3)

    def recap(self):
        formula=at(tex(r'\operatorname{softmax}\!\left(\frac{QK^{\mathsf T}}{\sqrt{d_k}}\right)V',64),0,.75)
        labels=VGroup(*[at(txt(t,27,c),x,-.9) for t,x,c in [('比较线索',-4.2,QC),('分配权重',0,KC),('汇总内容',4.2,VC)]])
        self.beat(0,Write(formula),LaggedStart(*[FadeIn(l) for l in labels],lag_ratio=.3),run_time=3.5)
        tags=VGroup(*[label_box(t,x,-2.1,c,2.6,.65,23) for t,x,c in [('多个视角',-4.4,QC),('位置与范围',0,KC),('重复加工',4.4,VC)]])
        self.beat(1,FadeIn(tags),run_time=2)
        def finale():
            self.clear_body()
            nodes=VGroup(*[Dot([x,1.2,0],radius=.12,color=QC) for x in np.linspace(-4.4,4.4,6)])
            query=Dot([0,-.5,0],radius=.15,color=OC)
            links=VGroup(*[Line(query.get_center(),p.get_center(),stroke_width=w,color=VC,stroke_opacity=.25+.09*w) for p,w in zip(nodes,[1,2,7,4,2,1])])
            self.play(FadeIn(nodes),FadeIn(query),Create(links),run_time=3)
            sentence=at(txt('让信息的传递方式，由输入决定。',37,INK),0,-2)
            self.play(Write(sentence),run_time=2.5)
        self.beat(2,action=finale)
