import pygame
import math
from animation import BodyMovementAnimation, BodyPartAnimation
from animation_manager import AnimationManager
from config import BODY, PARTS
from helpers import blit_rotate

class BodyPart:
    def __init__(self, image, pivot, name):
        """
        image: A loaded pygame.Surface with correct final size.
        pivot: (x, y) pivot coordinates inside the image's coordinate system.
        name: String name of the body part.
        """
        self.image = image
        self.pivot = pivot  # pivot point within the image
        self.name = name
        self.angle = 0.0
        self.parent = None
        self.parent_pivot_name = None
        self.world_pivot = None  # The pivot point in world coordinates, computed each frame.

    def update_pivot_position(self, parent_world_pos, parent_pivots):
        """
        Update this part's world pivot position based on the parent's movement.
        
        parent_world_pos: The top-left position of the parent (e.g., the body) in world coordinates.
        parent_pivots: A dict {pivot_name: (x,y)} of the parent's pivot points scaled and in world coords.
        """
        if self.parent and self.parent_pivot_name:
            parent_pivot = parent_pivots[self.parent_pivot_name]
            # The world pivot of this part is the parent's world pos + parent's pivot offset
            self.world_pivot = (
                parent_world_pos[0] + parent_pivot[0],
                parent_world_pos[1] + parent_pivot[1]
            )

    def draw(self, surface, debug=False):
        """
        Draw the part rotated around its pivot.
        
        Uses blitRotate from helpers.py to ensure the pivot remains stationary after rotation.
        """
        if self.world_pivot is None:
            return
        
        # Draw the rotated image around self.world_pivot as pivot, with self.pivot as originPos in the image
        blit_rotate(surface, self.image, self.world_pivot, self.pivot, self.angle)

        if debug:
            # Draw the pivot point on the surface
            pygame.draw.circle(surface, (0, 0, 255), (int(self.world_pivot[0]), int(self.world_pivot[1])), 3)


class BunnySprite:
    def __init__(self, center_x, center_y):
        self.time = 0.0
        self.body_movements = []        # List of BodyMovementAnimation
        self.body_part_animations = []  # List of BodyPartAnimation
        self.action_queue = []          # List of tuples (execute_time, action, params)
        # Load images
        self.images = {
            "body": pygame.image.load("assets/body.png").convert_alpha(),
            "head": pygame.image.load("assets/head.png").convert_alpha(),
            "left_arm": pygame.image.load("assets/left_arm.png").convert_alpha(),
            "right_arm": pygame.image.load("assets/right_arm.png").convert_alpha(),
            "left_leg": pygame.image.load("assets/left_leg.png").convert_alpha(),
            "right_leg": pygame.image.load("assets/right_leg.png").convert_alpha(),
        }

        # Initial body position
        self.position = pygame.math.Vector2(
            center_x - BODY["center"][0],
            center_y - BODY["center"][1]
        )

        # Create body part hierarchy
        self.body = BodyPart(self.images["body"], BODY["center"], "body")
        self.parts = {}
        for part_name, part_data in PARTS.items():
            part = BodyPart(
                self.images[part_name],
                part_data["pivot"],
                part_name
            )
            part.parent = self.body
            part.parent_pivot_name = part_data["connect_to_pivot"]
            self.parts[part_name] = part

        self.animation_manager = AnimationManager(self)
        self.update_part_positions()

    def update_part_positions(self):
        body_pos = self.position
        parent_pivots = BODY["pivots"]
        for part in self.parts.values():
            part.update_pivot_position(body_pos, parent_pivots)

    def draw(self, surface, debug=False):
        self.update_part_positions()
        surface.blit(self.body.image, self.position)
        if debug:
            rect = self.body.image.get_rect(topleft=self.position)
            pygame.draw.rect(surface, (0, 255, 0), rect, 2)
        for part in self.parts.values():
            part.draw(surface, debug)

    def rotate_part_to(self, part_name, angle):
        if part_name in self.parts:
            min_angle, max_angle = PARTS[part_name]["rotation_range"]
            clamped_angle = max(min(angle, max_angle), min_angle)
            self.parts[part_name].angle = clamped_angle

    def add_body_part_animation(self, part_name, target_angle, duration, on_complete=None):
        if part_name not in self.parts:
            print(f"Part '{part_name}' does not exist.")
            return
        current_angle = self.parts[part_name].angle
        animation = BodyPartAnimation(part_name, current_angle, target_angle, duration, on_complete)
        self.body_part_animations.append(animation)

    def add_body_movement_animation(self, target_pos, duration, on_complete=None):
        animation = BodyMovementAnimation(self.position, target_pos, duration, on_complete)
        self.body_movements.append(animation)

    # Basic Actions
    def raise_left_arm(self, duration=1.0, angle=-45, on_complete=None):
        self.add_body_part_animation("left_arm", angle, duration, on_complete)

    def raise_right_arm(self, duration=1.0, angle=45, on_complete=None):
        self.add_body_part_animation("right_arm", angle, duration, on_complete)

    def lower_left_arm(self, duration=1.0, angle=0, on_complete=None):
        self.add_body_part_animation("left_arm", angle, duration, on_complete)

    def lower_right_arm(self, duration=1.0, angle=0, on_complete=None):
        self.add_body_part_animation("right_arm", angle, duration, on_complete)

    def raise_left_leg(self, duration=1.0, angle=30):
        self.add_body_part_animation("left_leg", angle, duration)

    def raise_right_leg(self, duration=1.0, angle=-30):
        self.add_body_part_animation("right_leg", angle, duration)

    def lower_left_leg(self, duration=1.0, angle=0):
        self.add_body_part_animation("left_leg", angle, duration)

    def lower_right_leg(self, duration=1.0, angle=0):
        self.add_body_part_animation("right_leg", angle, duration)
    
    def rotate_head(self, duration=0.2, angle=0):
        self.add_body_part_animation("head", angle, duration)

    # Movement Actions
    def move_vertical(self, jump_height, duration):
        target_y = self.position.y - jump_height
        move = BodyMovementAnimation(
            start_pos=(self.position.x, self.position.y),
            target_pos=(self.position.x, target_y),
            duration=duration
        )
        self.body_movements.append(move)

    def move_horizontal(self, delta_x, duration):
        target_x = self.position.x + delta_x
        move = BodyMovementAnimation(
            start_pos=(self.position.x, self.position.y),
            target_pos=(target_x, self.position.y),
            duration=duration
        )
        self.body_movements.append(move)


    # Complex Actions
    def raise_both_arms(self, duration=1.0, angle=45, on_complete=None):
        self.raise_left_arm(duration, -angle, on_complete)
        self.raise_right_arm(duration, angle)

    def lower_both_arms(self, duration=1.0, on_complete=None):
        self.lower_left_arm(duration, 0)
        self.lower_right_arm(duration, 0, on_complete)
    
    # Raise Hands Animation
    def raise_hands(self, raise_duration=0.5, lower_duration=0.5):
        def lower_arms():
            self.lower_both_arms(duration=lower_duration)
        
        # Raise both arms with the callback
        self.raise_both_arms(duration=raise_duration, on_complete=lower_arms)

    # Jump Animation
    def jump(self, jump_height=50, duration_up=0.3, duration_down=0.3):
        start_pos = self.position.y
        peak_pos = start_pos - jump_height

        # Move Up
        move_up = BodyMovementAnimation(
            start_pos=(self.position.x, start_pos),
            target_pos=(self.position.x, peak_pos),
            duration=duration_up
        )
        self.body_movements.append(move_up)

        move_up.on_complete = lambda: self.body_movements.append(
            BodyMovementAnimation(
                start_pos=(self.position.x, peak_pos),
                target_pos=(self.position.x, start_pos),
                duration=duration_down
            )
        )
    
    # Raise Hands Animation
    def raise_hands(self, raise_duration=0.5, lower_duration=0.5):
        def lower_arms():
            self.lower_both_arms(duration=lower_duration)
        
        # Raise both arms with the callback
        self.raise_both_arms(duration=raise_duration, on_complete=lower_arms)

    def jump_and_raise_hands(self, jump_height=100, duration_jump_up=1, duration_jump_down=0.5, raise_duration=0.5, lower_duration=0.5):
        self.jump(jump_height, duration_jump_up, duration_jump_down)
        self.raise_hands(raise_duration, lower_duration)

    def perform_raise_hands_animation(self, raise_duration=0.5, lower_duration=0.5):
        self.raise_both_arms(raise_duration)
        # Schedule lowering after raising completes
        trigger_time = self.time + raise_duration
        self.body_part_animations.append(('lower_both_arms', trigger_time, lower_duration))

    def update(self, dt):
        self.time += dt
        self.animation_manager.update(dt)

        # Update body part animations
        for animation in self.body_part_animations[:]:
            if isinstance(animation, BodyPartAnimation):
                new_angle = animation.update(dt)
                self.rotate_part_to(animation.part_name, new_angle)
                if animation.completed:
                    self.body_part_animations.remove(animation)
            elif isinstance(animation, tuple):
                # Unpack the scheduled action tuple
                if len(animation) == 3:
                    action, trigger_time, duration = animation
                elif len(animation) == 2:
                    action, trigger_time = animation
                    duration = 1.0  # Default duration if not specified
                else:
                    print(f"Invalid animation tuple: {animation}")
                    self.body_part_animations.remove(animation)
                    continue
                
                if self.time >= trigger_time:
                    if action == 'lower_both_arms':
                        self.lower_both_arms(duration=duration)
                    # Remove the processed action
                    self.body_part_animations.remove(animation)

        # Update body movements
        for movement in self.body_movements[:]:
            new_pos = movement.update(dt)
            self.position = pygame.math.Vector2(new_pos)
            if movement.completed:
                self.body_movements.remove(movement)