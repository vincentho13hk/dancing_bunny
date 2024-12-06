WINDOW_WIDTH = 1200
WINDOW_HEIGHT = 800
FPS = 60
BACKGROUND_COLOR = (255, 255, 255)

# Image dimensions for reference
DIMENSIONS = {
    "body": (161, 196),
    "head": (296, 368),
    "arm": (71, 188),
    "leg": (84, 111)
}

BODY_WIDTH = 161
BODY_MIDDLE_X = BODY_WIDTH // 2  # 80

FPS = 60
BACKGROUND_COLOR = (255, 255, 255)

BODY = {
    "width": 161,
    "height": 196,
    "center": (80, 98),
    "pivots": {
        "neck": (80, 12),
        "shoulder_left": (6, 42),
        "shoulder_right": (152, 42),
        "hip_left": (36, 190),
        "hip_right": (121, 190)
    }
}

PARTS = {
    "head": {
        "pivot": (148, 368),
        "connect_to_pivot": "neck",
        "rotation_range": (-10, 10)
    },
    "left_arm": {
        "pivot": (66, 21),
        "connect_to_pivot": "shoulder_left",
        "rotation_range": (-45, 45)
    },
    "right_arm": {
        "pivot": (4, 21),
        "connect_to_pivot": "shoulder_right",
        "rotation_range": (-45, 45)
    },
    "left_leg": {
        "pivot": (42, 15),
        "connect_to_pivot": "hip_left",
        "rotation_range": (-30, 30)
    },
    "right_leg": {
        "pivot": (42, 15),
        "connect_to_pivot": "hip_right",
        "rotation_range": (-30, 30)
    }
}


# Animation settings
DANCE_SPEED = 0.05
OUTPUT_FILE = "bunny_dance.mp4"
VIDEO_DURATION = 30  # seconds

