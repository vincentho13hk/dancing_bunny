import pygame


class BodyPartAnimation:
    def __init__(self, part_name, start_angle, target_angle, duration, on_complete=None):
        """
        part_name: Name of the body part to animate.
        start_angle: Initial angle.
        target_angle: Desired final angle.
        duration: Time in seconds for the animation.
        """
        self.part_name = part_name
        self.start_angle = start_angle
        self.target_angle = target_angle
        self.duration = duration
        self.elapsed = 0.0
        self.completed = False
        self.on_complete = on_complete

    def update(self, dt):
        self.elapsed += dt
        progress = min(self.elapsed / self.duration, 1.0)
        new_angle = self.start_angle + (self.target_angle - self.start_angle) * progress
        if progress >= 1.0:
            self.completed = True
            if self.on_complete:
                self.on_complete()
        return new_angle

class BodyMovementAnimation:
    def __init__(self, start_pos, target_pos, duration, on_complete=None):
        """
        start_pos: (x, y) initial position.
        target_pos: (x, y) final position.
        duration: Time in seconds for the movement.
        """
        self.start_pos = pygame.math.Vector2(start_pos)
        self.target_pos = pygame.math.Vector2(target_pos)
        self.duration = duration
        self.elapsed = 0.0
        self.completed = False
        self.on_complete = on_complete

    def update(self, dt):
        self.elapsed += dt
        progress = min(self.elapsed / self.duration, 1.0)
        new_pos = self.start_pos.lerp(self.target_pos, progress)
        if progress >= 1.0:
            self.completed = True
            if self.on_complete:
                self.on_complete()
        return new_pos