

import pygame
from misc import zero_pad, lerp, pretty_time


class RestingBPM:
    def __init__(self, session):
        self.calibration = []
        self.calibration_start_time = session.now()


    def __call__(self, gui, session, event):
        if event and event.bpm > 1 and not event.error:
            self.calibration.append(event.bpm)
            if len(self.calibration) > 100:
                self.calibration = self.calibration[-101:]

        gui.clear((64, 0, 128))

        if event and len(self.calibration) > 1:
            resting_bpm_average = sum(self.calibration) // len(self.calibration)

            resting_bpm_deviation = 0
            for sample in self.calibration:
                resting_bpm_deviation += abs(resting_bpm_average - sample)
            resting_bpm_deviation /= len(self.calibration)

            session.set_resting_bpm(resting_bpm_average)

            elapsed_seconds = int(session.now() - self.calibration_start_time)
            elapsed_minutes = zero_pad(elapsed_seconds // 60)
            elapsed_seconds = zero_pad(elapsed_seconds % 60)
            elapsed_time = f"{elapsed_minutes}:{elapsed_seconds}"

            graph_min = event.bpm
            graph_max = event.bpm

            for sample in self.calibration:
                graph_min = min(graph_min, sample)
                graph_max = max(graph_max, sample)

            graph_span = max(graph_max - graph_min, 1)
            graph_scale = (gui.h * .25)
            graph_points = []
            histogram = []

            x_anchor = gui.w - (len(self.calibration) - 1) * gui.w_over_100
            y_anchor = gui.h - graph_scale - 20

            def plot(index, sample):
                graph_a = (sample - graph_min) / graph_span
                graph_x = x_anchor + index * gui.w_over_100
                graph_y = y_anchor + graph_scale * (1.0 - graph_a)
                return (graph_x, graph_y)

            for index, sample in enumerate(self.calibration):
                graph_points.append(plot(index, sample))

            x_anchor = 0

            for index, sample in enumerate(sorted(self.calibration)[::-1]):
                histogram.append(plot(index, sample))

            pygame.draw.lines(gui.screen, "black", False, histogram, 8)

            pygame.draw.lines(gui.screen, "blue", False, [plot(0, resting_bpm_average), plot(101, resting_bpm_average)], 8)
            pygame.draw.lines(gui.screen, "white", False, graph_points, 8)

            gui.draw_stat("Current BPM:", round(event.bpm), 0, 0)
            gui.draw_stat("Elapsed Time:", elapsed_time, 1, 0)

            pygame.draw.lines(gui.screen, "blue", False, [(200, 900), (700, 900)], 16)
            gui.draw_stat("Average:", round(resting_bpm_average), 0, 1)

            gui.draw_stat("Deviation:", f"{resting_bpm_deviation:.2f}", 1, 1)

            gui.draw_text("Press space to stop calibration", 650, 1200)
