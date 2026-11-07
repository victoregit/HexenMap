"""Bounded display prediction. Never changes localization or collection coordinates."""
from dataclasses import replace
import csv
import time
import numpy as np
from src.live.marker_art import LEGACY


def outside_controls(pins, rectangles):
    """Exclude whole symbols and their click targets, using game-client coordinates."""
    def intersects(pin,rect):
        left,top,right,bottom=rect
        a,b,c,d=getattr(pin,'geometry',LEGACY).bounds(pin.x,pin.y)
        return c-1>=left and a<=right and d-1>=top and b<=bottom
    return [pin for pin in pins if not any(intersects(pin,rect) for rect in rectangles)]


class DisplayMotion:
    def __init__(self):
        self.reset()

    def reset(self):
        self.previous = None
        self.velocity = None
        self.last_velocity = None
        self.correction = np.zeros(2)

    def present(self, observation, now):
        if not observation.fresh(now):
            self.reset()
            return observation
        old = self.previous
        if old is None or (old.surface, old.map_id, old.layer_id) != (
                observation.surface, observation.map_id, observation.layer_id):
            self.reset()
        elif observation.captured_at > old.captured_at:
            dt = observation.captured_at-old.captured_at
            delta = observation.world_to_screen[:, 2]-old.world_to_screen[:, 2]
            # Prediction only for stable map translation, never zoom/rotation or minimap.
            stable = (observation.surface == 'map' and .015 <= dt <= .12 and
                      np.allclose(observation.world_to_screen[:, :2],
                                  old.world_to_screen[:, :2], rtol=.0005, atol=.00001))
            velocity = delta/dt if stable else None
            prior = self.last_velocity
            self.velocity = None
            self.correction = np.zeros(2)
            if velocity is not None and prior is not None:
                speed = np.linalg.norm(velocity)
                if (speed > 8 and np.dot(velocity, prior) > 0 and
                        np.linalg.norm(velocity-prior) < max(35, speed*.30)):
                    self.velocity = velocity
                    # Ease only a small prediction error, using the same timestamp.
                    residual = old.world_to_screen[:, 2]+prior*dt-observation.world_to_screen[:, 2]
                    if np.linalg.norm(residual) <= 3:
                        self.correction = residual
            self.last_velocity = velocity
        self.previous = observation
        age = now-observation.captured_at
        if self.velocity is None or age > .12:
            return observation
        offset = self.velocity*min(age, .06)
        length = np.linalg.norm(offset)
        if length > 8:
            offset *= 8/length
        matrix = observation.world_to_screen.copy()
        matrix[:, 2] += offset+self.correction*max(0, 1-age/.06)
        # Original timestamp stays intact; prediction never extends validity.
        return replace(observation, world_to_screen=matrix)


class MarkerCanvas:
    """Retain each symbol's primitives and only move or replace changed symbols."""
    def __init__(self, canvas, draw):
        self.canvas, self.draw = canvas, draw
        self.entries = {}

    def clear(self):
        self.canvas.delete('all')
        self.entries.clear()

    def render(self, pins, collected):
        visible = {p.item.id for p in pins}
        for identifier in self.entries.keys()-visible:
            self.canvas.delete(self.entries.pop(identifier)[0])
        for pin in pins:
            identifier = pin.item.id
            geometry=getattr(pin,'geometry',None)
            x,y=(round(pin.x),round(pin.y)) if geometry is not None and geometry.size else (pin.x,pin.y)
            state = (pin.item.category, collected(identifier),geometry)
            old = self.entries.get(identifier)
            if old and old[3] == state:
                self.canvas.move(old[0], x-old[1], y-old[2])
                self.entries[identifier] = (old[0], x,y, state)
                continue
            if old:
                self.canvas.delete(old[0])
            tag = 'pin:'+identifier
            before = set(self.canvas.find_all())
            options={'collected':state[1]}
            if geometry is not None:options['geometry']=geometry
            self.draw(self.canvas, pin.item.category, x,y, **options)
            for primitive in set(self.canvas.find_all())-before:
                self.canvas.addtag_withtag(tag, primitive)
            self.entries[identifier] = (tag, x,y, state)


class DisplayTelemetry:
    """Capture-to-submission age is measurable; monitor/game presentation is not."""
    def __init__(self, path):
        self.handle=path.open('a',newline='',encoding='utf-8')
        self.writer=csv.writer(self.handle)
        if self.handle.tell()==0:
            self.writer.writerow(['monotonic_s','region','map','layer','surface','pins',
                                  'capture_to_submit_ms','draw_ms','prediction_px'])
        self.flushed=time.monotonic()

    def record(self, region, observation, displayed, pins, started):
        now=time.monotonic()
        prediction=0
        if pins and observation.world_to_screen is not None and displayed.world_to_screen is not None:
            prediction=float(np.linalg.norm(displayed.world_to_screen[:,2]-observation.world_to_screen[:,2]))
        self.writer.writerow([round(now,4),region,observation.map_id,observation.layer_id,
                              observation.surface,len(pins),round((now-observation.captured_at)*1000,2),
                              round((now-started)*1000,2),round(prediction,2)])
        if now-self.flushed>=1:
            self.handle.flush();self.flushed=now

    def close(self):
        self.handle.close()
