# animation_manager.py

class AnimationManager:
    def __init__(self, sprite):
        """
        sprite: Instance of BunnySprite.
        """
        self.sprite = sprite
        self.queue = []  # Queue of sequences
        self.current_animation = None
        self.is_animating = False
        self.sequence = []
        self.sequence_index = 0
        self.elapsed_time = 0.0

    def load_sequence(self, config):
        """
        Load a single movement sequence.
        """
        if self.is_animating:
            print(f"Movement '{self.current_animation.get('name', 'Unnamed')}' is already playing.")
            return self.current_animation.get("name", "Unnamed")
        
        self.queue.append(config)
        self._start_next_sequence()
        return config.get("name", "Unnamed")

    def load_sequences(self, configs):
        """
        Load multiple movement sequences.
        """
        if self.is_animating:
            print(f"Current movement '{self.current_animation.get('name', 'Unnamed')}' is playing. Queuing new movements.")
        self.queue.extend(configs)
        self._start_next_sequence()

    def _start_next_sequence(self):
        if not self.is_animating and self.queue:
            self.current_animation = self.queue.pop(0)
            self.sequence = self.current_animation.get("sequences", [])
            self.sequence_index = 0
            self.elapsed_time = 0.0
            self.is_animating = True
            self.execute_current_sequence()

    def execute_current_sequence(self):
        if self.sequence_index >= len(self.sequence):
            self.is_animating = False
            self.current_animation = None
            self._start_next_sequence()
            return
        
        action_block = self.sequence[self.sequence_index]
        actions = action_block.get("actions")
        duration = action_block.get("duration", 1.0)
        
        if actions != "rest":
            for part, params in actions.items():
                action = params.get("action")
                method = getattr(self.sprite, action, None)
                if callable(method):
                    method(duration=duration, **params.get("params", {}))
                else:
                    print(f"Action '{action}' not found in BunnySprite.")
        
        self.current_duration = duration
        self.sequence_start_time = self.elapsed_time
        self.sequence_index += 1

    def update(self, dt):
        if not self.is_animating:
            return
        
        self.elapsed_time += dt
        current_block = self.sequence[self.sequence_index - 1]
        duration = current_block.get("duration", 1.0)
        
        if self.elapsed_time - self.sequence_start_time >= duration:
            self.execute_current_sequence()
    
    def stop(self):
        """
        Stop the current animation and clear the queue.
        """
        print("Stopping all animations.")
        self.queue.clear()
        self.current_animation = None
        self.is_animating = False
        self.sequence = []
        self.sequence_index = 0
        self.elapsed_time = 0.0
