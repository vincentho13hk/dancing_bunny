import pygame
import cv2
import numpy as np
from sprite import BunnySprite
from config import *
import json
import os
import time
import ffmpeg

def load_movement_sequence(file_path):
    with open(file_path, 'r') as f:
        return json.load(f)

def main():
    pygame.init()
    screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    clock = pygame.time.Clock()
    
    pygame.mixer.init()
    music_file = 'assets/Dancing_D.wav'
    pygame.mixer.music.load(music_file)

    bunny = BunnySprite(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 + 100)
    animation_manager = bunny.animation_manager
    movement_sequence = load_movement_sequence('output/movements.json')

    output_dir = "output"
    os.makedirs(output_dir, exist_ok=True)
    temp_video_path = os.path.join(output_dir, "temp.mp4")
    final_video_path = os.path.join(output_dir, "output.webm")
    
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = None
    recording = False
    recording_start_time = 0

    def stop_recording():
        nonlocal recording, out
        if recording:
            pygame.mixer.music.stop()
            animation_manager.stop()
            out.release()
            
            recording_duration = time.time() - recording_start_time
            
            input_video = ffmpeg.input(temp_video_path)
            input_audio = ffmpeg.input(music_file, t=recording_duration)
            ffmpeg.output(input_video, input_audio, final_video_path,
                         vcodec='libvpx', acodec='libvorbis').overwrite_output().run()
            os.remove(temp_video_path)
            recording = False

    running = True
    while running:
        dt = clock.tick(FPS) / 1000.0

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE:
                if not recording:
                    out = cv2.VideoWriter(temp_video_path, fourcc, FPS, (WINDOW_WIDTH, WINDOW_HEIGHT))
                    pygame.mixer.music.play()
                    animation_manager.load_sequences(movement_sequence)
                    recording = True
                    recording_start_time = time.time()
                else:
                    stop_recording()

        screen.fill(BACKGROUND_COLOR)
        bunny.update(dt)
        bunny.draw(screen, debug=True)
        pygame.display.flip()

        if recording:
            string_image = pygame.image.tostring(screen, 'RGB')
            temp_surf = np.frombuffer(string_image, dtype=np.uint8)
            temp_surf = temp_surf.reshape((WINDOW_HEIGHT, WINDOW_WIDTH, 3))
            temp_surf = cv2.cvtColor(temp_surf, cv2.COLOR_RGB2BGR)
            out.write(temp_surf)
            
            if not pygame.mixer.music.get_busy():
                stop_recording()

    pygame.quit()

if __name__ == "__main__":
    main()