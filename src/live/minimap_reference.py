"""Bounded native images anchored only by independent terrain registrations."""
from collections import deque
from dataclasses import replace
import math


class RegisteredMinimapFrames:
    def __init__(self):
        self.frames=deque(maxlen=3)

    def clear(self):
        self.frames.clear()

    def remember(self,frame,observation):
        uncertainty=max(observation.error_px,observation.position_uncertainty_px)
        if (frame is None or observation.surface!='minimap' or observation.circle is None
                or not observation.map_id or not observation.layer_id
                or observation.confidence<.8 or not math.isfinite(uncertainty) or uncertainty>1.5
                or not observation.fresh(observation.captured_at)):
            return False
        if self.frames:
            old_frame,old=self.frames[-1]
            if (old_frame.shape!=frame.shape or (old.map_id,old.layer_id)!=(observation.map_id,observation.layer_id)):
                self.clear()
            elif observation.captured_at<=old.captured_at:return False
        # Keep the original independently registered image and transform. Local
        # rechecks never replace this image or become their own reference.
        self.frames.append((frame,replace(observation,position_uncertainty_px=uncertainty)))
        return True

    def locate(self,image,stamp,match):
        for reference,observation in reversed(self.frames):
            if image.shape!=reference.shape or stamp<observation.captured_at:continue
            updated=match(reference,image,observation,stamp)
            if updated is not None:return updated
        return None
