

class FullStop:
    def __init__(self):
        pass

    def __call__(self, gui, session, event):
        gui.clear((64, 64, 64))

        calming_color = (96, 96, 96)
        slightly_less_calming_color = (196, 196, 196)

        gui.draw_stat(
            "Current BPM:", event.bpm, 0, 0,
            label_color=calming_color, value_color=calming_color, wiggle = event.bpm > session.resting_bpm)

        gui.draw_stat(
            "Resting BPM:", session.resting_bpm, 1, 0,
            label_color=calming_color, value_color=calming_color)

        gui.draw_text(
            "press space", None, gui.h * .5 + 20, y_align=1,
            color=slightly_less_calming_color, font="big")

        gui.draw_text(
            "to save and quit", None, gui.h * .5 + 20,
            color=slightly_less_calming_color, font="big")

        gui.draw_text("quiesce.", 100, 1200, color=calming_color, font="bigger")
