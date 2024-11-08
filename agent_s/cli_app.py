import os 
import io
import pyautogui
import platform 
import time 
import argparse

if platform.system() == 'Darwin':
            current_platform = 'macos'
            from agent_s.aci.MacOSACI import MacOSACI
            from agent_s.aci.MacOSACI import UIElement
else:
    raise ValueError("Unsupported platform")
    
from agent_s.core.AgentS import UIAgent, GraphSearchAgent


platform_os = platform.system() 

def show_permission_dialog(code: str, action_description: str):
    """Show a platform-specific permission dialog and return True if approved."""
    if platform.system() == 'Darwin':
        result = os.system(f'osascript -e \'display dialog "Do you want to execute this action?\n\n{code} which will try to {action_description}" with title "Action Permission" buttons {{"Cancel", "OK"}} default button "OK" cancel button "Cancel"\'')
        return result == 0
    elif platform.system() == 'Linux':
        result = os.system(f'zenity --question --title="Action Permission" --text="Do you want to execute this action?\n\n{code}" --width=400 --height=200')
        return result == 0
    return False


def run_agent(agent: UIAgent,instruction: str):
    obs = {}
    traj = 'Task:\n' + instruction
    subtask_traj = ""
    for _ in range(15):
        obs['accessibility_tree'] = UIElement.systemWideElement()
            
        # Get screen shot using pyautogui.
        # Take a screenshot
        screenshot = pyautogui.screenshot()

        # Save the screenshot to a BytesIO object
        buffered = io.BytesIO()
        screenshot.save(buffered, format="PNG")

        # Get the byte value of the screenshot
        screenshot_bytes = buffered.getvalue()
        # Convert to base64 string.
        obs['screenshot'] = screenshot_bytes 

        # Get next action code from the agent 
        info, code = agent.predict(instruction=instruction, observation=obs)

        if 'done' in code[0].lower() or 'fail' in code[0].lower():
            if platform.system() == 'Darwin':
                os.system(f'osascript -e \'display dialog "Task Completed" with title "OpenACI Agent" buttons "OK" default button "OK"\'')
            elif platform.system() == 'Linux':
                os.system(f'zenity --info --title="OpenACI Agent" --text="Task Completed" --width=200 --height=100')
            
            agent.update_narrative_memory(traj)
            break 
    
        
        if 'next' in code[0].lower():
            continue

        if 'wait' in code[0].lower():
            time.sleep(5)
            continue

        else:
            time.sleep(1.)
            print("EXECUTING CODE:", code[0])
            
            # Ask for permission before executing
            exec(code[0])
            time.sleep(1.)
            
            # Update task and subtask trajectories and optionally the episodic memory
            traj += '\n\nReflection:\n' + str(info['reflection']) + '\n\n----------------------\n\nPlan:\n' + info['executor_plan']
            subtask_traj = agent.update_episodic_memory(info, subtask_traj)

def main():
    parser = argparse.ArgumentParser(description="Run GraphSearchAgent with specified model.")
    parser.add_argument("--model", type=str, default="gpt-4o-mini", help="Specify the model to use (e.g., gpt-4o)")
    args = parser.parse_args()
    
    if platform.system() == 'Darwin':
        grounding_agent = MacOSACI()
    else:
        raise ValueError("Unsupported platform")

    while True:
        query = input("Query: ")
        if 'gpt' in args.model:
            engine_type = 'openai'
        elif 'claude' in args.model:
            engine_type = 'anthropic'
        engine_params = {
            "engine_type": engine_type,
            "model": args.model,
        }
        
        agent = GraphSearchAgent(
            engine_params,
            grounding_agent,
            platform=current_platform,
            action_space="pyautogui",
            observation_type="mixed",
            search_engine="LLM"
        )
        
        agent.reset()
        
        # Run the agent on your own device 
        run_agent(agent, query)
        
        response = input("Would you like to provide another query? (y/n): ")
        if response.lower() != "y":
            break

if __name__ == '__main__':
    main()
