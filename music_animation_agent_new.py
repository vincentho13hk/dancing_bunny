# music_animation_agent.py

import json
import operator
import os
from typing import Annotated, List, Literal, TypedDict, Optional, Dict, Any
from pydantic import BaseModel, Field, ValidationError
import librosa
import numpy as np
import langchain
from langchain_core.messages import SystemMessage, HumanMessage, AnyMessage
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from langgraph.graph import END, StateGraph, MessagesState
from langgraph.prebuilt import ToolNode
from langchain.output_parsers import PydanticOutputParser

# -------------------------
# Pydantic Models
# -------------------------
langchain.debug=True

class MusicPhrase(BaseModel):
    start_time: float
    end_time: float
    beats: int
    tempo: float
    energy: float
    description: str

class MusicAnalysis(BaseModel):
    phrases: List[MusicPhrase]

class MovementAction(BaseModel):
    action: str
    params: Dict[str, float]

class MovementSequenceBlock(BaseModel):
    description: str
    actions: Optional[Dict[str, MovementAction]]  # None for "rest"
    duration: float  # Duration in seconds

class MovementSequence(BaseModel):
    name: str
    sequences: List[MovementSequenceBlock]

class MovementSeries(BaseModel):
    series: List[MovementSequence]

# -------------------------
# Tools Definitions
# -------------------------

@tool
def analyze_music(filepath: str) -> str:
    """
    Analyze the given music file and extract simplified features.
    Returns a JSON string with timestamped descriptions.
    """
    
    current_dir = os.path.dirname(os.path.abspath(__file__))
    filepath = os.path.join(current_dir, "assets", "Dancing_D.wav")
    try:
        y, sr = librosa.load(filepath, sr=None)
    except Exception as e:
        return json.dumps({"error": f"Failed to load music file: {e}"})
    
    # Tempo and Beat Tracking
    tempo, beats = librosa.beat.beat_track(y=y, sr=sr)
    
    if len(beats) == 0:
        return json.dumps({"error": "No beats detected in the music file."})
    
    beat_times = librosa.frames_to_time(beats, sr=sr)
    
    # Energy Calculation
    energy = librosa.feature.rms(y=y)[0]
    
    # Segment the music into phrases based on beat intervals
    phrases = []
    phrase_length = 16  # Number of beats per phrase
    num_phrases = len(beats) // phrase_length
    
    for i in range(num_phrases):
        start_beat = i * phrase_length
        end_beat = start_beat + phrase_length
        if end_beat >= len(beats):
            break
        
        # Explicitly convert NumPy arrays to floats
        start_time = float(beat_times[start_beat])
        end_time = float(beat_times[end_beat])
        phrase_tempo = float(tempo)
        phrase_energy = float(np.mean(energy[start_beat:end_beat]))
        phrase_beats = end_beat - start_beat  # Total beats in the phrase
        
        description = (
            f"Phrase {i+1}: "
            f"Starts at {start_time:.2f}s, "
            f"lasts for {end_time - start_time:.2f}s, "
            f"beats: {phrase_beats}, "
            f"tempo: {phrase_tempo:.2f} BPM, "
            f"average energy: {phrase_energy:.4f}."
        )
        
        phrases.append(description)
    

    output_dir = os.path.join(current_dir, "output")
    output_file_path = os.path.join(output_dir, "music_analysis_debug.txt")
    # Write debug information to file
    with open(output_file_path, "w", encoding="utf-8") as debug_file:
        debug_file.write("\n".join(phrases))

    # Return a formatted string with all phrases
    return "\n".join(phrases)

@tool
def generate_movesets(energy: float, tempo: float) -> str:
    """
    Create creative movesets for the bunny sprite using energy and tempo.
    The LLM will generate different sets of actions.
    """
    prompt = f"""
    Based on the energy ({energy}) and tempo ({tempo}), generate creative movements for the bunny sprite. These movements should correspond to body parts and actions, considering the tempo for the rhythm and energy for the intensity of movements. 

    The available actions are:
    - **Body:**
        - `move_vertical`: Parameters: `jump_height` (float)
        - `move_horizontal`: Parameters: `delta_x` (float)
    - **Head:**
        - `rotate_head`: Parameters: `angle` (float)
    - **Left Arm:**
        - `raise_left_arm`: Parameters: `angle` (float)
        - `lower_left_arm`: Parameters: `angle` (float)
    - **Right Arm:**
        - `raise_right_arm`: Parameters: `angle` (float)
        - `lower_right_arm`: Parameters: `angle` (float)
    - **Left Leg:**
        - `raise_left_leg`: Parameters: `angle` (float)
        - `lower_left_leg`: Parameters: `angle` (float)
    - **Right Leg:**
        - `raise_right_leg`: Parameters: `angle` (float)
        - `lower_right_leg`: Parameters: `angle` (float)

    **Note:** 
    - The "body" refers to the central part of the bunny, correspond to vertical and horizontal movement. 
    - To ensure the bunny stays within the screen and does not move off-screen, any horizontal movement in one direction (e.g., to the left) must follow by a corresponding movement later in the opposite direction (e.g., to the right) to cancel the displacement.
    - "body" movement should be at least 100 for each action but not exceed 200
    - "Body parts" refer to individual limbs (arms and legs) to perform rotation, the angle default is clockwise, negative value would be counterclockwise.
    - Body part head should be included in most actions to enhance the overall visual appeal

    Each movement is an object with name and sequence, the sequence is a list of actions by different body parts.

    Provide examples Jump and Walk, there are much more other movement that can be combination of different action of different body parts and core body, use your creativity! example:
    
    Example 1: Jump
    {{
        "name": "jump",
        "sequences": [
            {{
                "description": "Jump up",
                "actions": {{
                    "body": {{"action": "move_vertical", "params": {{"jump_height": 50}}}},
                    "left_arm": {{"action": "raise_left_arm", "params": {{"angle": -45}}}},
                    "right_arm": {{"action": "raise_right_arm", "params": {{"angle": 45}}}}
                }},
                "duration": 0.5
            }},
            {{
                "description": "Jump down",
                "actions": {{
                    "body": {{"action": "move_vertical", "params": {{"jump_height": -50}}}},
                    "left_arm": {{"action": "lower_left_arm", "params": {{"angle": 0}}}},
                    "right_arm": {{"action": "lower_right_arm", "params": {{"angle": 0}}}}
                }},
                "duration": 0.5
            }}
        ]
    }}

    Example 2: Walk
    {{
        "name": "walk_to_left",
        "sequences": [
            {{
                "actions": {{
                    "left_leg": {{"action": "raise_left_leg", "params": {{"angle": 30}}}},
                    "right_leg": {{"action": "lower_right_leg", "params": {{"angle": 0}}}},
                    "body": {{"action": "move_horizontal", "params": {{"delta_x": -30}}}}
                }},
                "duration": 0.5
            }},
            {{
                "actions": {{
                    "left_leg": {{"action": "lower_left_leg", "params": {{"angle": 0}}}},
                    "right_leg": {{"action": "raise_right_leg", "params": {{"angle": 30}}}},
                    "body": {{
                        "action": "move_horizontal", 
                        "params": {{"delta_x": -30}}
                    }}
                }},
                "duration": 0.5
            }},
            {{
                "actions": {{
                    "right_leg": {{"action": "lower_right_leg", "params": {{"angle": 0}}}},
                    "body": {{
                        "action": "rest", "params": {{}}
                    }}
                }},
                "duration": 0.5
            }}
        ]
    }}

    **NOTE**:
    - Movements are synchronized with the beats and tempo.
    - Create your own movement by combining different actions of body parts with creativity, like wave arms, rotate head etc
    - High energy phrases trigger more dynamic movements.
    - Lower energy phrases have more relaxed movements.
    - At the end of each movement, reset the bunny to its default state unless the next phrase continues the movement. (angle of body parts should get back to 0, displacement of bunny should get to beginning position)
    - beware of the closing brace for actions, before duration
    - only sequences will use [ and ] , do not use bracket otherwise
    - Each movement should be quick, <0.5s , speed depends on the music property of that moment
    - USE CREATIVITY!!! Examples:
    Jump with Arm Swing
    Hop with Head Tilt
    Side Step with Arm Stretch
    Twist and Hop
    Gentle Wave
    Knee Lift with Head Nod
    ...

    Append the movement sequences as a JSON array of movements with the following example 1 structure:
    
    {{
        "name": "moveset 1: walk from right to left and back to center with the vibe",
        "sequences": [
        ...
        ]
    }},
    {{
        "name": "moveset 2: consecutive jumps with energy",
        "sequences": [
        ...
        ]
    }},
    ...
    ...
    ...

    
    """

    chat = ChatOpenAI(model="gpt-4", temperature=0.7)
    response = chat.invoke([HumanMessage(content=prompt)])
    
    # Directly return the response
    return response.content

@tool
def add_movement_to_json(movement_str: str, repeat: int = 1):
    """
    Append a validated movement sequence to a predefined JSON file, repeating it as specified.
    
    Parameters:
    - movement_str: A string representation of the movement in JSON format.
    - repeat: Number of times to repeat the movement in the sequence.

    Returns:
    A message indicating success or an error message.
    """

    current_dir = os.path.dirname(os.path.abspath(__file__))
    output_dir = os.path.join(current_dir, "output")
    os.makedirs(output_dir, exist_ok=True)  # Create the folder if it doesn't exist
    MOVEMENT_FILEPATH = os.path.join(output_dir, "movements.json")

    try:
        # Append the raw movement string to the file as is
        with open(MOVEMENT_FILEPATH, "a", encoding="utf-8") as file:
            for i in range(repeat):
                # Append the movement with a trailing comma for proper formatting
                file.write(movement_str.rstrip() + ",\n")

        return f"Successfully appended movement repeated {repeat} times to '{MOVEMENT_FILEPATH}'."
    except Exception as e:
        return f"Error appending movement to JSON: {e}"

@tool
def add_list_of_movements_to_json(movements_list_str: str, repeat: int = 1):
    """
    Append a list of movements to a predefined JSON file, repeating the list as a sequence.
    
    Parameters:
    - movements_list_str: A string representation of a list of movements in JSON format.
    - repeat: Number of times to repeat the entire list of movements.

    Returns:
    A message indicating success or an error message.
    """
    import os

    # Define file path
    current_dir = os.path.dirname(os.path.abspath(__file__))
    output_dir = os.path.join(current_dir, "output")
    os.makedirs(output_dir, exist_ok=True)  # Ensure the output directory exists
    MOVEMENT_FILEPATH = os.path.join(output_dir, "movements.json")

    try:
        # Open the file to append movements
        with open(MOVEMENT_FILEPATH, "a", encoding="utf-8") as file:
            for _ in range(repeat):
                file.write(movements_list_str.rstrip() + ",\n")

        return f"Successfully appended movement list repeated {repeat} times to '{MOVEMENT_FILEPATH}'."
    except Exception as e:
        return f"Error appending movements list to JSON: {e}"



@tool
def initialize_json_file():
    """
    Initializes the movements.json file by adding an opening square bracket '['.
    This ensures the file is ready to accept JSON array elements.
    """
    # Define the filepath
    current_dir = os.path.dirname(os.path.abspath(__file__))
    output_dir = os.path.join(current_dir, "output")
    os.makedirs(output_dir, exist_ok=True)  # Create the folder if it doesn't exist
    MOVEMENT_FILEPATH = os.path.join(output_dir, "movements.json")

    try:
        # Initialize the file with a single '['
        with open(MOVEMENT_FILEPATH, "w", encoding="utf-8") as file:
            file.write("[\n")
        return f"Successfully initialized the movements JSON file: '{MOVEMENT_FILEPATH}'."
    except Exception as e:
        return f"Error initializing the JSON file: {e}"


@tool
def finalize_movements_json():
    """
    Finalize the movements JSON file by removing trailing commas and properly closing the JSON array.
    """
    # Define the filepath
    current_dir = os.path.dirname(os.path.abspath(__file__))
    output_dir = os.path.join(current_dir, "output")
    MOVEMENT_FILEPATH = os.path.join(output_dir, "movements.json")

    try:
        # Read the file
        with open(MOVEMENT_FILEPATH, "r", encoding="utf-8") as file:
            lines = file.readlines()

        # Remove the trailing comma from the last movement and close the array
        if lines and lines[-1].strip().endswith(","):
            lines[-1] = lines[-1].rstrip(",\n") + "\n"
        lines.append("]\n")  # Close the JSON array

        # Write back the corrected content
        with open(MOVEMENT_FILEPATH, "w", encoding="utf-8") as file:
            file.writelines(lines)

        return f"Successfully finalized the movements JSON file: '{MOVEMENT_FILEPATH}'."
    except Exception as e:
        return f"Error finalizing the JSON file: {e}"


# -------------------------
# AI Agent Definition
# -------------------------

class AgentState(TypedDict):
    messages: Annotated[List[AnyMessage], operator.add]
    total_duration: float  # Tracks the cumulative duration of movements generated

class MusicAnimationAgent:
    def __init__(self):
        self.llm_model = "gpt-4o-mini"
        self.chat = ChatOpenAI(model=self.llm_model, temperature=0.7)
        self.system = self.AGENT_PROMPT
        tools = [analyze_music, generate_movesets, add_movement_to_json,  finalize_movements_json, initialize_json_file]
        tool_node = ToolNode(tools=tools)
        self.model = self.chat.bind_tools(tools)
        
        # Define the state graph
        graph = StateGraph(AgentState)
        graph.add_node("llm", self.call_openai)
        graph.add_node("tools", tool_node)
        graph.add_conditional_edges(
            "llm",
            self.should_continue
        )
        graph.add_edge("tools", "llm")
        graph.set_entry_point("llm")
        self.graph = graph.compile()

    AGENT_PROMPT = """
    0: Initialization
    Use the 'add_movement_to_json' tool to setup the output file

    1. **Analyze the Music:**
    Use the 'analyze_music' tool to analyze the music file and extract key characteristics such as:
    - **Beats:** The beats throughout the music file.
    - **Tempo:** The beats per minute (BPM).
    - **Energy:** Energy levels at different timestamps.
    - **Music Phrases:** Divide the music into phrases based on beats.

    2. **Generate Movesets for Different Vibes:**
    After analyzing the music, use the 'generate_movesets' tool to create a variety of movesets. Each moveset should be based on the music's tempo, energy, and vibe. 
    For example:
    - **High Energy:** Use fast, dynamic movements such as running or fast jumps.
    - **Low Energy:** Use slow, relaxed movements like slow arm raises or walking.
    
    The movesets can include various actions like arm swings, leg lifts, jumps, kicks, and body movements.

    - Use the `add_movement_to_json` tool to directly append single moveset or sequence of movesets to the output JSON file.
    - only sequences will use [ and ] , do not use/add bracket otherwise
    - For longer periods, use the `repeat` parameter of the `add_movement_to_json` tool to efficiently fill the required duration.
        Example:
        ```text
        add_movement_to_json(movement_str=<MOVEMENT_JSON_STRING>, repeat=5)
        ```
    
        example input str:
        ```
        {{
            "name": "moveset 1: walk from right to left and back to center with the vibe",
            "sequences": [
            ...
            ]
        }},
        {{
            "name": "moveset 2: consecutive jumps with energy",
            "sequences": [
            ...
            ]
        }}
        ```

    4. **Focus on JSON Generation**:
    - **Do not generate summaries, explanations, or additional output text.**
    - The `add_movement_to_json` tool handle creating and managing the `movements.json` file. Ensure all movesets are added using these tools.
    - There is no need to output or display the final JSON file — the process is complete when the required movements have been appended.

    5. **Example Move JSON**:
    {{
        "name": "move 1",
        "sequences": [
        ...
        ]
    }}

    6. **Phrases Filling**:
    Divide the music into periods (e.g., phrases) based on the analysis.
    - For each phrase, ensure the `movements.json` file has enough movesets to completely fill the time.
    - A single 2-second jump movement could be repeated 5 times to fill a 10-second period, or a combination of jumps, arm swings, and body movements could be used.
    - Use the `add_list_of_movements_to_json` tool when combining multiple movesets together.
    - ENSURE that the number of movements is sufficient to completely fill each period (for a 10s period, probably have 10+ movements).
    - DIFFERENT movesets SHOULD be used for each phrase to maintain variety and synchronization with the music's energy.


    

    You have access to the following tools:
    - **analyze_music:** Analyzes the music file and returns a breakdown of beats, tempo, energy, and phrases.
    - **generate_movesets:** Generates a variety of movement actions based on the music's tempo, energy, and vibe.
    - **add_movement_to_json:** Add a single movement or movements into the output JSON file with option of repetition.
    - **finalize_movements_json:** Finalize the JSON file at the end.

    Your goal is to combine the music analysis and generate creative, synchronized animation movements for the bunny sprite. 

    You must add enough moveset into the json file that can be played to cover entire music audio length, for a one-minute audio, it probably has 50+ movements
    """

    def call_openai(self, state: AgentState):
        messages = state['messages']
        if self.system:
            messages = [SystemMessage(content=self.system)] + messages
        message = self.model.invoke(messages)
        return {'messages': [message]}

    def should_continue(self, state: MessagesState) -> Literal["tools", END]:
        messages = state['messages']
        last_message = messages[-1]
        if last_message.tool_calls:
            return "tools"
        return END

    def generate_animation_sequence(self, music_filepath: str) -> Optional[MovementSequence]:
        """
        Orchestrate the tools to generate an animation sequence based on the music file.
        """
        # Initialize the agent's state with the music filepath as a human message
        initial_message = HumanMessage(content=f"Create an animation sequence based on the music file")
        state = {"messages": [initial_message], "total_duration": 0.0}

        
        # Run the state graph
        result = self.graph.invoke(state)
        
        if not result or 'messages' not in result:
            print("Failed to generate animation sequence.")
            return None
        
        final_message = result['messages'][-1]
        if isinstance(final_message, SystemMessage):
            print("No movement sequence generated.")
            return None
        
        # Save the output result to a file
        try:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            output_filepath = os.path.join(current_dir, "output", "output.txt")
            os.makedirs(os.path.dirname(output_filepath), exist_ok=True)
            with open(output_filepath, "w", encoding="utf-8") as output_file:
                output_file.write(final_message.content)
            print(f"Animation sequence successfully saved.")
        except Exception as e:
            print(f"Failed to save animation sequence: {e}")
            return None
        # Since we're ignoring parsing, just return the raw JSON string
        return final_message.content
    
if __name__ == "__main__":
    def main():
        # Get the absolute path
        current_dir = os.path.dirname(os.path.abspath(__file__))
        music_filepath = os.path.join(current_dir, "assets", "Dancing_D.wav")
        
        # Instantiate the AI Agent
        agent = MusicAnimationAgent()
        
        # Generate the animation sequence
        agent.generate_animation_sequence(music_filepath)
    
    main()