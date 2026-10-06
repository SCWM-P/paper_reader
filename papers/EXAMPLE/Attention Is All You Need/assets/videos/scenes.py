"""A narrated vector-animation explanation of the 2017 Transformer.

Render with Manim Community 0.21 in an isolated environment. Set ATTENTION_AUDIO
to a directory containing 00.wav..08.wav (any narration producer is supported).
"""
from pathlib import Path
import json
import os
import wave
import numpy as np
from manim import *

HERE = Path(__file__).resolve().parent
PAPER = HERE.parents[1]
PARTS = json.loads((HERE / "narration.json").read_text(encoding="utf-8"))
AUDIO = Path(os.environ.get("ATTENTION_AUDIO", PAPER / "tmp/video/audio"))
config.background_color = "#0B1020"
BLUE_Q, GOLD_K, GREEN_V = "#68B6FF", "#FFD477", "#65DFB0"
FONT = os.environ.get("ATTENTION_FONT") or next((f for f in ("Microsoft YaHei", "PingFang SC", "Noto Sans CJK SC", "WenQuanYi Zen Hei") if f in __import__("manimpango").list_fonts()), "sans-serif")


def cn(value, size=25, color=WHITE):
    return Text(value, font=FONT, font_size=size, color=color)


def box(label, center, color=BLUE_Q, width=2.5, height=.8):
    r = RoundedRectangle(width=width, height=height, corner_radius=.13,
                         stroke_color=color, fill_color=color, fill_opacity=.12).move_to(center)
    t = cn(label, 22, color).move_to(r)
    if t.width > width - .2:
        t.scale_to_fit_width(width - .2)
    return VGroup(r, t)


def formula(tex, size=40, color=WHITE):
    return MathTex(tex, font_size=size, color=color)


class AttentionExplained(Scene):
    def construct(self):
        self.timeline = []
        for i, method in enumerate([self.intro, self.predecessors, self.projections,
                                   self.scores, self.normalize, self.values,
                                   self.heads, self.architecture, self.outro]):
            if self.mobjects:
                self.play(*[FadeOut(m) for m in list(self.mobjects)], run_time=.6)
            start = self.time
            wav = AUDIO / f"{i:02d}.wav"
            with wave.open(str(wav), "rb") as stream:
                duration = stream.getnframes() / stream.getframerate()
            self.add_sound(str(wav))
            header = cn(PARTS[i]["title"], 32).to_edge(UP, buff=.35)
            chapter = cn(f"{i+1:02d} / 09  ·  Attention Is All You Need (2017)", 15, GREY_B).to_corner(UL, buff=.2)
            subtitle = cn(PARTS[i]["subtitle"], 21, GREY_A)
            if subtitle.width > 12.5:
                subtitle.scale_to_fit_width(12.5)
            subtitle.to_edge(DOWN, buff=.35)
            self.play(FadeIn(header), FadeIn(chapter), FadeIn(subtitle), run_time=.8)
            method()
            self.wait(max(.5, duration + 1 - (self.time - start)))
            self.timeline.append({"start": start, "end": self.time, **PARTS[i]})
        timeline = PAPER / "tmp/video/chapters.json"
        timeline.parent.mkdir(parents=True, exist_ok=True)
        timeline.write_text(json.dumps(self.timeline, ensure_ascii=False, indent=2), encoding="utf-8")

    def intro(self):
        words = [box(t, [x, -.8, 0], c, 2.1) for t, x, c in zip(["我", "读", "论文"], [-4, 0, 4], [BLUE_Q, GOLD_K, GREEN_V])]
        self.play(LaggedStart(*[FadeIn(w, shift=UP*.4) for w in words], lag_ratio=.3), run_time=2)
        question = cn("当前词需要哪些上下文？", 28, BLUE_Q).move_to([0, 1.3, 0])
        self.play(Write(question), run_time=2)
        edges = VGroup(*[CurvedArrow(words[1].get_top(), w.get_top(), angle=a, color=c)
                         for w, a, c in [(words[0], .7, BLUE_Q), (words[2], -.7, GREEN_V)]])
        self.play(Create(edges), run_time=2)
        for k in range(3):
            self.play(*[Indicate(w, color=GREEN_V) for w in words], run_time=1)
            self.wait(.8)
        f = formula(r"\mathrm{Attention}(Q,K,V)=\mathrm{softmax}\!\left(\frac{QK^T}{\sqrt{d_k}}\right)V", 39)
        f.move_to([0, -2.2, 0])
        self.play(Write(f), run_time=3)

    def predecessors(self):
        labels = ["RNN：顺序更新", "CNN：局部窗口", "Self-attention：全局匹配"]
        ys = [1.7, 0, -1.7]
        rows = []
        for label, y in zip(labels, ys):
            self.add(cn(label, 21).move_to([-4.1, y+.55, 0]))
            nodes = VGroup(*[Dot([x, y, 0], radius=.14, color=BLUE_Q) for x in np.linspace(-3.3, 4.6, 6)])
            rows.append(nodes)
            self.play(FadeIn(nodes), run_time=.6)
        recurrent = VGroup(*[Arrow(rows[0][j].get_center(), rows[0][j+1].get_center(), buff=.2, color=GOLD_K) for j in range(5)])
        self.play(LaggedStart(*[GrowArrow(a) for a in recurrent], lag_ratio=.8), run_time=5)
        conv = VGroup(*[Line(rows[1][j].get_center(), rows[1][j+1].get_center(), color=GREEN_V) for j in range(5)])
        self.play(Create(conv), run_time=2)
        window = SurroundingRectangle(VGroup(*rows[1][:3]), color=GREEN_V, buff=.25)
        self.play(Create(window), run_time=1)
        self.play(window.animate.shift(RIGHT*4.74), run_time=2)
        connections = VGroup(*[CurvedArrow(rows[2][2].get_center(), n.get_center(), angle=.6 if j<2 else -.6, color=BLUE_Q, stroke_width=2)
                               for j, n in enumerate(rows[2]) if j != 2])
        self.play(Create(connections), run_time=2)
        self.play(Indicate(rows[2][2]), run_time=1)
        self.wait(2)

    def projections(self):
        x = formula(r"X\in\mathbb{R}^{n\times d_{model}}", 42).move_to([-4, 0, 0])
        self.play(Write(x), run_time=2)
        targets = []
        for y, tex, color in [(1.5, r"Q=XW^Q", BLUE_Q), (0, r"K=XW^K", GOLD_K), (-1.5, r"V=XW^V", GREEN_V)]:
            t = formula(tex, 45, color).move_to([2, y, 0])
            a = Arrow(x.get_right(), t.get_left(), color=color, buff=.35)
            targets.append(t)
            self.play(GrowArrow(a), Write(t), run_time=2)
        roles = [cn("查询：我在寻找什么", 22, BLUE_Q), cn("键：我提供什么线索", 22, GOLD_K), cn("值：我提供什么内容", 22, GREEN_V)]
        for t, role in zip(targets, roles):
            role.next_to(t, RIGHT, buff=.5)
            if role.get_right()[0] > 6.5:
                role.scale(.8).next_to(t, RIGHT, buff=.25)
            self.play(FadeIn(role), run_time=1)
        self.wait(3)
        hint = cn("同一输入 · 三组可学习的投影", 23, GREY_A).move_to([0,-2.5,0])
        self.play(FadeIn(hint), run_time=1)

    def scores(self):
        plane = NumberPlane(x_range=[-.5,2,.5], y_range=[-.5,1.5,.5], x_length=5, y_length=3.5,
                            background_line_style={"stroke_opacity":.25}).move_to([-3,0,0])
        self.play(Create(plane), run_time=2)
        q = Arrow(plane.c2p(0,0), plane.c2p(1,0), buff=0, color=BLUE_Q, stroke_width=8)
        k = Arrow(plane.c2p(0,0), plane.c2p(1,1), buff=0, color=GOLD_K, stroke_width=5)
        self.play(GrowArrow(q), GrowArrow(k), run_time=2)
        qlab = formula(r"q=[1,0]", 30, BLUE_Q).next_to(plane, DOWN, buff=.25)
        self.play(Write(qlab), run_time=1)
        equations = VGroup(*[formula(t, 34, GOLD_K) for t in [r"q\cdot k_1=1\cdot1+0\cdot0=1", r"q\cdot k_2=1\cdot0+0\cdot1=0", r"q\cdot k_3=1\cdot1+0\cdot1=1"]]).arrange(DOWN,buff=.65).move_to([3.3,0,0])
        if equations.width > 6:
            equations.scale_to_fit_width(6)
        for e in equations:
            self.play(Write(e), run_time=2)
        self.play(Transform(k, Arrow(plane.c2p(0,0), plane.c2p(0,1), buff=0,color=GOLD_K,stroke_width=5)),run_time=2)
        self.play(Indicate(equations[1]),run_time=1)
        self.wait(2)

    def normalize(self):
        f = formula(r"[1,0,1]/\sqrt{2}\ \longrightarrow\ [0.707,0,0.707]", 42).move_to([0,1.7,0])
        self.play(Write(f),run_time=3)
        soft = formula(r"\alpha_j=\frac{e^{s_j}}{\sum_\ell e^{s_\ell}}", 42).move_to([-4,-.1,0])
        self.play(Write(soft),run_time=2)
        weights=np.exp(np.array([1,0,1])/np.sqrt(2)); weights/=weights.sum()
        bars=VGroup()
        for j,w in enumerate(weights):
            b=Rectangle(width=1.25,height=float(w)*4,fill_color=[BLUE_Q,GOLD_K,GREEN_V][j],fill_opacity=.7,stroke_width=0).align_to([0,-1.6,0],DOWN).set_x(j*1.8+.5)
            lab=cn(f"{w:.3f}",24).next_to(b,UP,buff=.15)
            token=cn(f"位置 {j+1}",18,GREY_A).next_to(b,DOWN,buff=.15)
            bars.add(VGroup(b,lab,token))
        self.play(LaggedStart(*[FadeIn(b,shift=UP*.2) for b in bars],lag_ratio=.3),run_time=3)
        total=formula(r"\sum_j\alpha_j=1",35).move_to([1.9,-2.5,0])
        self.play(Write(total),run_time=2)
        self.play(*[Indicate(b[0]) for b in bars],run_time=2)
        self.wait(2)

    def values(self):
        terms=[r"0.401[1,0]",r"0.198[0,2]",r"0.401[2,1]"]
        items=VGroup(*[formula(t,39,c) for t,c in zip(terms,[BLUE_Q,GOLD_K,GREEN_V])]).arrange(RIGHT,buff=.8).move_to([0,1.6,0])
        self.play(LaggedStart(*[Write(t) for t in items],lag_ratio=.4),run_time=4)
        converted=VGroup(*[formula(t,39,c) for t,c in zip([r"[0.401,0]",r"[0,0.396]",r"[0.802,0.401]"],[BLUE_Q,GOLD_K,GREEN_V])]).arrange(RIGHT,buff=.8).move_to([0,0,0])
        for a,b in zip(items,converted):
            self.play(TransformFromCopy(a,b),run_time=1.5)
        result=formula(r"z=\sum_j\alpha_jv_j\approx[1.203,0.797]",44,GREEN_V).move_to([0,-1.7,0])
        self.play(Write(result),run_time=3)
        self.play(Indicate(result),run_time=1)
        self.wait(2)

    def heads(self):
        source=box("输入 X",[-5,0,0],WHITE,1.6)
        heads=[box("Head 1",[-1.8,1.3,0],BLUE_Q,2.1),box("Head 2",[-1.8,-1.3,0],GOLD_K,2.1)]
        self.play(FadeIn(source),run_time=1)
        for h in heads:
            self.play(GrowArrow(Arrow(source.get_right(),h.get_left(),color=h[0].get_stroke_color())),FadeIn(h),run_time=1.5)
        zs=[formula(r"z_1=[1.203,0.797]",29,BLUE_Q).next_to(heads[0],RIGHT,buff=.3),formula(r"z_2=[0.860,0.716]",29,GOLD_K).next_to(heads[1],RIGHT,buff=.3)]
        self.play(*[Write(z) for z in zs],run_time=3)
        concat=formula(r"[z_1\Vert z_2]W^O",42,GREEN_V).move_to([1.7,-2.5,0])
        # Route the first head around the second head's numeric label.
        route=VGroup(Line(zs[0].get_right()+RIGHT*.1,[5.5,zs[0].get_y(),0],color=GREEN_V),
                     Line([5.5,zs[0].get_y(),0],[5.5,concat.get_y(),0],color=GREEN_V),
                     Arrow([5.5,concat.get_y(),0],concat.get_right(),color=GREEN_V,buff=.12))
        second=Arrow(zs[1].get_bottom(),concat.get_top(),color=GREEN_V,buff=.15)
        self.play(Create(route),GrowArrow(second),Write(concat),run_time=3)
        hint=VGroup(cn("每个头使用各自的",20,GREY_A),formula(r"W^Q,W^K,W^V",27,GREY_A),cn("投影决定匹配空间",20,GREY_A)).arrange(RIGHT,buff=.18).move_to([0,2.45,0])
        self.play(FadeIn(hint),run_time=1)
        detail=cn("教学参数 · 每头二维",18,GREY_A).move_to([0,2.0,0])
        self.play(FadeIn(detail),run_time=1)
        self.wait(2)

    def architecture(self):
        # The upper triangle is masked before row normalization.
        mask=VGroup()
        for i in range(3):
            for j in range(3):
                c=GREEN_V if j<=i else "#444E66"
                cell=Square(side_length=.6,stroke_width=1,stroke_color=GREY_B,fill_color=c,fill_opacity=.5).move_to([-4.5+j*.65,1.0-i*.65,0])
                text=cn("✓" if j<=i else "×",20).move_to(cell)
                mask.add(VGroup(cell,text))
        self.play(LaggedStart(*[FadeIn(c) for c in mask],lag_ratio=.1),run_time=2)
        masktext=cn("行：查询 / 列：读取位置",17,GREY_A).move_to([-3.9,-1.1,0])
        self.play(FadeIn(masktext),run_time=1)
        encoder=[box("输入 + 位置",[-.3,-2,0],WHITE,2.2,.6),box("Self-attention",[-.3,-.8,0],BLUE_Q,2.2,.65),box("FFN + Add & Norm",[-.3,.4,0],GREEN_V,2.2,.65)]
        decoder=[box("右移目标 + 位置",[3.4,-2,0],WHITE,2.5,.6),box("Masked attention",[3.4,-.8,0],GOLD_K,2.5,.65),box("Cross-attention",[3.4,.4,0],BLUE_Q,2.5,.65),box("FFN → 词分布",[3.4,1.6,0],GREEN_V,2.5,.65)]
        self.play(LaggedStart(*[FadeIn(b) for b in encoder+decoder],lag_ratio=.2),run_time=3)
        arrows=VGroup(*[Arrow(a.get_top(),b.get_bottom(),buff=.1,stroke_width=2) for col in [encoder,decoder] for a,b in zip(col,col[1:])])
        self.play(Create(arrows),run_time=2)
        cross=Arrow(encoder[-1].get_right(),decoder[2].get_left(),buff=.1,color=GREEN_V)
        label=cn("K、V",18,GREEN_V).next_to(cross,UP,buff=.1)
        self.play(GrowArrow(cross),FadeIn(label),run_time=2)
        self.play(Indicate(decoder[1]),run_time=1)
        self.wait(3)

    def outro(self):
        f=formula(r"\mathrm{softmax}\!\left(\frac{QK^T}{\sqrt{d_k}}+M\right)V",54)
        f.move_to([0,1.1,0])
        self.play(Write(f),run_time=3)
        self.play(Indicate(f,color=GREEN_V),run_time=2)
        complexity=formula(r"n\times n\ \mathrm{weights}\quad\Rightarrow\quad O(n^2d)",37,GOLD_K).move_to([0,-.7,0])
        self.play(Write(complexity),run_time=3)
        ref=cn("阅读入口：§3.2 · Figure 2 · §4 / Table 1",24,GREY_A).move_to([0,-2,0])
        self.play(FadeIn(ref),run_time=2)
        credit=cn("依据 Vaswani et al. · NIPS 2017 会议版",18,GREY_B).move_to([0,-2.65,0])
        self.play(FadeIn(credit),run_time=1)
        self.wait(3)
