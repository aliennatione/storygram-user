from manim import *


class DemoScene(Scene):
    """Scena demo generata da demo-authoring. Sostituisci il contenuto."""

    def construct(self):
        title = Text("Demo Storygram", font_size=48)
        self.play(Write(title))
        self.wait(1)
        circle = Circle(color=BLUE)
        self.play(Create(circle))
        self.play(circle.animate.shift(RIGHT * 2))
        self.play(FadeOut(circle), FadeOut(title))