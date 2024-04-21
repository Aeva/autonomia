
import copy
import pygame
from session import Phase, Event
from misc import zero_pad, lerp, pretty_time


class ResultsGraph:
    def __init__(self, session, gui, bpm_stats, global_bpm):
        self.session = session

        self.min_time = session.log[0].time
        self.max_time = session.log[-1].time
        self.time_span = self.max_time - self.min_time

        self.bpm_line = []
        self.weighted_bpm_line = []
        self.phase_lines = []

        self.last_phase = 0

        self.margin_x1 = 100
        self.margin_x2 = gui.w - 50
        self.margin_y1 = 50
        self.margin_y2 = gui.h - 100

        self.outline_line = [
            (self.margin_x1, self.margin_y1),
            (self.margin_x2, self.margin_y1),
            (self.margin_x2, self.margin_y2),
            (self.margin_x1, self.margin_y2)]

        phase_start = session.log[0]
        self.phases = [(0, phase_start.phase)]

        for event in session.log:
            if event.phase != phase_start.phase:
                self.phases.append((event.time - self.min_time, event.phase))
                phase_start = event

        self.bpm_min, self.bpm_max, self.bpm_range = bpm_stats

        self.x_range = abs(self.margin_x2 - self.margin_x1)
        self.y_range = abs(self.margin_y2 - self.margin_y1)

        self.bpm_x_scale = 1 / self.time_span * self.x_range
        self.bpm_y_scale = 1 / self.bpm_range * self.y_range

        self.target_bpm_low = session.resting_bpm + session.config.target_bpm_low
        self.target_bpm_high = session.resting_bpm + session.config.target_bpm_high

        self.bpm_lines = []
        for i in range(-100, 100, 5):
            if global_bpm:
                bpm = math.floor(self.bpm_min + self.bpm_range * .5) + i
            else:
                bpm = session.resting_bpm + i
            if bpm >= self.bpm_min + 2 and bpm <= self.bpm_max - 2:
                y_plot = self.margin_y2 - (bpm - self.bpm_min) * self.bpm_y_scale
                self.bpm_lines.append((bpm, [(self.margin_x1, y_plot), (self.margin_x2, y_plot)]))

        self.dedupe = [copy.copy(session.log[0])]
        last = self.dedupe[-1]
        for event in session.log[1:]:
            if event.bpm != last.bpm:
                self.dedupe[-1].time = (self.dedupe[-1].time + last.time) * .5
                self.dedupe.append(copy.copy(event))
            last = copy.copy(event)
        if self.dedupe[-1] is not last:
            self.dedupe.append(last)

        self.peaks = [self.dedupe[0]]
        for i in range(1, len(self.dedupe) - 1):
            a = self.dedupe[i - 1]
            b = self.dedupe[i]
            c = self.dedupe[i + 1]
            if (a.bpm < b.bpm and c.bpm < b.bpm) or (a.bpm > b.bpm and c.bpm > b.bpm):
                self.peaks.append(b)
        if self.peaks[-1] is not self.dedupe[-1]:
            self.peaks.append(self.dedupe[-1])

        self.peak_lines = []
        for event in self.peaks:
            x_plot = self.margin_x1 + (event.time - self.min_time) * self.bpm_x_scale
            y_plot = self.margin_y2 - (event.bpm - self.bpm_min) * self.bpm_y_scale
            self.peak_lines.append((x_plot, y_plot))

        def pare(events, span=1):
            min_list = []
            max_list = []
            for i in range(len(events)):
                low = max(0, i - span)
                high = max(0, i + span + 1)
                neighbors = list([e.bpm for e in events[low:high]])
                if events[i].bpm == min(neighbors):
                    min_list.append(events[i])
                if events[i].bpm == max(neighbors):
                    max_list.append(events[i])
            return min_list, max_list

        self.peak_mins, self.peak_maxs = pare(self.peaks)
        for i in range(1):
            self.peak_mins = pare(self.peak_mins)[0]
            self.peak_maxs = pare(self.peak_maxs)[1]

        self.peak_min_lines = []
        for event in self.peak_mins:
            x_plot = self.margin_x1 + (event.time - self.min_time) * self.bpm_x_scale
            y_plot = self.margin_y2 - (event.bpm - self.bpm_min) * self.bpm_y_scale
            self.peak_min_lines.append((x_plot, y_plot))

        self.peak_max_lines = []
        for event in self.peak_maxs:
            x_plot = self.margin_x1 + (event.time - self.min_time) * self.bpm_x_scale
            y_plot = self.margin_y2 - (event.bpm - self.bpm_min) * self.bpm_y_scale
            self.peak_max_lines.append((x_plot, y_plot))

        def soften(events):
            reduced = [copy.copy(events[0])]
            for i in range(1, len(events) - 1):
                a = events[i - 1]
                b = events[i]
                c = events[i + 1]

                bpm = lerp(lerp(a.bpm, b.bpm, .5), lerp(b.bpm, c.bpm, .5), .5)
                b = copy.copy(b)
                b.bpm = bpm

                reduced.append(b)
            reduced.append(copy.copy(events[-1]))
            return reduced

        self.octaves = []
        softened = self.peaks
        for i in range(5):
            softened = soften(softened)
            octave = []
            for event in softened:
                x_plot = self.margin_x1 + (event.time - self.min_time) * self.bpm_x_scale
                y_plot = self.margin_y2 - (event.bpm - self.bpm_min) * self.bpm_y_scale
                octave.append((x_plot, y_plot))
            self.octaves.append(octave)

        for event in session.log:
            x_plot = self.margin_x1 + (event.time - self.min_time) * self.bpm_x_scale
            y_plot = self.margin_y2 - (event.bpm - self.bpm_min) * self.bpm_y_scale
            self.bpm_line.append((x_plot, y_plot))

            y_plot = self.margin_y2 - (event.bpm_rolling_average - self.bpm_min) * self.bpm_y_scale
            self.weighted_bpm_line.append((x_plot, y_plot))

            if event.phase != self.last_phase:
                self.last_phase = event.phase
                phase_color = (64, 64, 64)
                if event.phase == Phase.CALIBRATION:
                    phase_color = "blue"
                if event.phase == Phase.STEADY:
                    phase_color = "green"
                if event.phase == Phase.COOLDOWN:
                    phase_color = "red"
                if event.phase == Phase.FULLSTOP:
                    phase_color = "dark red"
                self.phase_lines.append(
                    (phase_color, [(x_plot, self.margin_y1), (x_plot, self.margin_y2)]))


    def __call__(self, gui, current_mode = 0):
        session = self.session
        gui.clear((90, 90, 90))

        resting_bpm_y = self.margin_y2 - (session.resting_bpm - self.bpm_min) * self.bpm_y_scale
        target_low_y = self.margin_y2 - (self.target_bpm_low - self.bpm_min) * self.bpm_y_scale
        target_high_y = self.margin_y2 - (self.target_bpm_high - self.bpm_min) * self.bpm_y_scale

        mouse_x, mouse_y = pygame.mouse.get_pos()
        hover_x = mouse_x >= self.margin_x1 and mouse_x <= self.margin_x2
        hover_y = mouse_y >= self.margin_y1 and mouse_y <= self.margin_y2

        pygame.draw.polygon(
            gui.screen, (96, 96, 96),
            [(self.margin_x1, self.margin_y1),
             (self.margin_x1, self.margin_y2),
             (self.margin_x2, self.margin_y2),
             (self.margin_x2, self.margin_y1)])

        pygame.draw.polygon(
            gui.screen, (80, 80, 80),
            [(self.margin_x1, target_low_y),
             (self.margin_x1, target_high_y),
             (self.margin_x2, target_high_y),
             (self.margin_x2, target_low_y)])

        if current_mode == 4 or current_mode == 5:
            pygame.draw.polygon(
                gui.screen, (100, 100, 100),
                self.peak_min_lines + [i for i in reversed(self.peak_max_lines)])

        for phase_color, phase_line in self.phase_lines:
            pygame.draw.lines(gui.screen, phase_color, False, phase_line, 2)

        for bpm, line in self.bpm_lines:
            label_color = "gray"
            if bpm == self.session.resting_bpm:
                label_color = "blue"
            if bpm == self.target_bpm_low or bpm == self.target_bpm_high:
                label_color = "white"
            pygame.draw.lines(gui.screen, "gray", False, line, 1)
            gui.draw_y_label(bpm, line[0][0] - 5, line[0][1], label_color)

        pygame.draw.lines(
            gui.screen, "blue", False,
            [(self.margin_x1, resting_bpm_y),
             (self.margin_x2, resting_bpm_y)], 2)

        pygame.draw.lines(
            gui.screen, "black", False,
            [(self.margin_x1, target_low_y),
             (self.margin_x2, target_low_y)], 2)

        pygame.draw.lines(
            gui.screen, "black", False,
            [(self.margin_x1, target_high_y),
             (self.margin_x2, target_high_y)], 2)

        if hover_x:
            pygame.draw.lines(
                gui.screen, "magenta", False,
                [(mouse_x, self.margin_y1),
                 (mouse_x, self.margin_y2)], 1)
            x_span_px = self.margin_x2 - self.margin_x1
            a = (mouse_x - self.margin_x1) / x_span_px
            hover_t = lerp(0, self.max_time - self.min_time, a)
            anchor = (gui.h - self.margin_y2) * .5 + self.margin_y2

            gui.draw_x_label(pretty_time(hover_t), mouse_x, anchor, "magenta", y_align=1)

            selected_phase = None
            for time, phase in self.phases:
                if hover_t >= time:
                    selected_phase = str(phase._name_).lower()
                else:
                    break
            if selected_phase is not None:
                gui.draw_x_label(selected_phase, mouse_x, anchor, "gray", y_align=0)

        if hover_y:
            pygame.draw.lines(
                gui.screen, "magenta", False,
                [(self.margin_x1, mouse_y),
                 (self.margin_x2, mouse_y)], 1)
            y_span_px = self.margin_y2 - self.margin_y1
            a = (mouse_y - self.margin_y1) / y_span_px
            hover_bpm = round(lerp(self.bpm_max, self.bpm_min, a))
            gui.draw_y_label(hover_bpm, self.margin_x1 - 5, mouse_y, "magenta")

        if current_mode == 0:
            gui.draw_text(
                "unfiltered bpm & rolling average",
                self.margin_x2, self.margin_y1, font="smol", x_align=1, y_align=1)
            pygame.draw.lines(gui.screen, "dark red", False, self.bpm_line, 1)
            pygame.draw.lines(gui.screen, "white", False, self.weighted_bpm_line, 1)

        elif current_mode == 1:
            gui.draw_text(
                "unfiltered bpm", self.margin_x2, self.margin_y1, font="smol", x_align=1, y_align=1)
            pygame.draw.lines(gui.screen, "white", False, self.bpm_line, 1)

        elif current_mode == 2:
            gui.draw_text(
                "bpm rolling average", self.margin_x2, self.margin_y1, font="smol", x_align=1, y_align=1)
            pygame.draw.lines(gui.screen, "white", False, self.weighted_bpm_line, 1)

        elif current_mode == 3:
            gui.draw_text(
                "bpm peaks", self.margin_x2, self.margin_y1, font="smol", x_align=1, y_align=1)
            pygame.draw.lines(gui.screen, "white", False, self.peak_lines, 1)

        elif current_mode == 4:
            gui.draw_text(
                "bpm envelope", self.margin_x2, self.margin_y1, font="smol", x_align=1, y_align=1)
            outline_color = (50, 50, 50)
            pygame.draw.lines(gui.screen, outline_color, False, self.peak_min_lines, 4)
            pygame.draw.lines(gui.screen, outline_color, False, self.peak_max_lines, 4)
            pygame.draw.lines(gui.screen, "white", False, self.peak_lines, 1)

        elif current_mode == 5:
            gui.draw_text(
                "bpm envelope & bezier", self.margin_x2, self.margin_y1, font="smol", x_align=1, y_align=1)
            pygame.draw.lines(gui.screen, "black", False, self.peak_min_lines, 4)
            pygame.draw.lines(gui.screen, "black", False, self.peak_max_lines, 4)
            pygame.draw.lines(gui.screen, "white", False, self.peak_lines, 1)
            for i, octave in enumerate(self.octaves):
                a = (i + 1) / max(len(self.octaves), 1)
                c = lerp(64, 0, a)
                color = (c, c, c)
                thickness = round(lerp(2, 6, a))
                pygame.draw.lines(gui.screen, color, False, octave, thickness)

        target_bpm = (
            session.resting_bpm + session.config.target_bpm_low,
            session.resting_bpm + session.config.target_bpm_high)

        pygame.draw.lines(gui.screen, "black", True, self.outline_line, 2)
