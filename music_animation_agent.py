# music_animation_agent.py

import json
import operator
import os
from typing import Annotated, List, Literal, TypedDict, Optional, Dict, Any
from pydantic import BaseModel, Field
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
    
    # Return a formatted string with all phrases
    return "\n".join(phrases)

@tool
def generate_movements(analysis_str: str) -> str:
    """
    Generate movement sequences based on the musical analysis.
    Utilizes LLM to create detailed movement actions aligned with timestamps.
    Returns the movement sequences as a JSON string.
    """
    
    # Initialize the LLM
    chat = ChatOpenAI(model="gpt-4", temperature=0.7)
    
    # Prepare the prompt with detailed instructions
    PROMPT = """
    You are an AI assistant that generates animation movement sequences for a bunny sprite based on music analysis. 
    Below is a list of music phrases with their timestamps, beats, tempo, energy, and descriptions.

    {music_analysis}

    Define the available body parts and their possible actions:
    - **Body:**
        - `move_vertical`: Parameters: `jump_height` (float)
        - `move_horizontal`: Parameters: `delta_x` (float)
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
    - The "body" refers to the central part of the bunny, correspond to vertical and horizontal movement
    - "Body parts" refer to individual limbs (arms and legs) to perform rotation, the angle should not exceed 30 degree, the default is clockwise, negative value would be counterclockwise.

    Each movement is an object with name and sequence, the sequence is a list of actions by different body parts.

    Provide examples Jump and Walk, there are much more other movement that can be combination of different action of different body parts and core body, use your creativity!
    
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
                    "body": {{"action": "move_horizontal", "params": {{"delta_x": -30}}}}
                }},
                "duration": 0.5
            }},
            {{
                "actions": {{
                    "right_leg": {{"action": "lower_right_leg", "params": {{"angle": 0}}}},
                    "body": {{"action": "rest", "params": {{}}}}
                }},
                "duration": 0.5
            }}
        ]
    }}
    
    
    Generate a detailed movement sequence for entire music length. 

    **NOTE**:
    - Movements are synchronized with the beats and tempo.
    - Create your own movement by combining different actions of body parts with creativity, like wave arms, rotate head etc
    - High energy phrases trigger more dynamic movements.
    - Lower energy phrases have more relaxed movements.
    - At the end of each movement, reset the bunny to its default state unless the next phrase continues the movement.
    - Each movement should be quick, <0.5s , speed depends on the music property of that moment
    - Each session of music can be combination of multiple types of movement
    - To repeat a movement, you need to add a movement to list multiple times yourself, using duration 10s would just make the character stay in air for 10s, you cannot rely on others to repeat the movement

    - The duration of all movement SHOULD add up to be length of the music, for a 1 minute music, you should create around 60/0.5 = 120 movements

    Output the movement sequences as a JSON array of movements with the following example structure:
    [
        {{
            "name": "walk from right to left and back to center with the vibe",
            "sequences": [
            ...
            ]
        }},
        {{
            "name": "consecutive jumps with energy",
            "sequences": [
            ...
            ]
        }},
        ...
        ...
        ...
    ]

    Your Output SHOULD contains more than 100 movements, the array should have more than 100 elements, this is a MUST
    Ensure the JSON structure is strictly followed without any additional text.
    """
    prompt = PROMPT.format(music_analysis=analysis_str)
    
    # Get the LLM response
    response = chat.invoke([HumanMessage(content=prompt)])
    
    # Parse the response using PydanticOutputParser
    # output_parser = PydanticOutputParser(pydantic_object=MovementSequence)
    
    # # Validate and parse the LLM response
    # try:
    #     movement_sequence = output_parser.parse(response.content)
    # except Exception as e:
    #     print(f"Error parsing movement sequence: {e}")
    #     # Return an empty movement sequence in case of parsing failure
    #     empty_sequence = MovementSequence(name="AI_generated_sequence", sequences=[])
    #     return json.dumps(empty_sequence.dict())
    print(response.content)
    return response.content

# -------------------------
# AI Agent Definition
# -------------------------

class AgentState(TypedDict):
    messages: Annotated[List[AnyMessage], operator.add]

class MusicAnimationAgent:
    def __init__(self):
        self.llm_model = "gpt-4o-mini"
        self.chat = ChatOpenAI(model=self.llm_model, temperature=0.7)
        self.system = self.AGENT_PROMPT
        tools = [analyze_music, generate_movements]
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

    AGENT_PROMPT = """You are an AI assistant that creates detailed animation movement sequences for a bunny sprite based on the provided music file. 
    Follow these steps:
    1. Use the 'analyze_music' tool to analyze the given music file, the music file is provided to the tool already.
    2. Use the 'generate_movements' tool to create a movement sequence based on the analysis.
    3. Return only the JSON object text generated by the 'generate_movements' tool in the final message. Do not modify the JSON structure or add any additional wrappers or any other string.
    Use these tools as needed to complete your tasks. You should run these tools in sequence as required. Always verify the success of each operation before moving to the next step.
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
        state = {'messages': [initial_message]}
        
        # Run the state graph
        result = self.graph.invoke(state)
        
        if not result or 'messages' not in result:
            print("Failed to generate animation sequence.")
            return None
        
        final_message = result['messages'][-1]
        if isinstance(final_message, SystemMessage):
            print("No movement sequence generated.")
            return None
        
        # Save the raw JSON content to a file
        try:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            output_filepath = os.path.join(current_dir, "output", "animation_sequence.json")
            os.makedirs(os.path.dirname(output_filepath), exist_ok=True)
            with open(output_filepath, "w", encoding="utf-8") as output_file:
                output_file.write(final_message.content)
            print(f"Animation sequence successfully saved to {output_filepath}.")
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