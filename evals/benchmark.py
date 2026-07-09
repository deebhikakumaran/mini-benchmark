import docker
import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

client_docker = docker.from_env()
client_ai = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def get_ai_fix(code, error):
    prompt = f"Fix this code that causes the following test error:\n\nCODE:\n{code}\n\nERROR:\n{error}\n\nReturn ONLY the corrected code."
    response = client_ai.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content

def run_agent_benchmark():
    # Start container
    container = client_docker.containers.run("mini-benchmark:latest", detach=True, tty=True)
    
    # Get the current buggy code
    code = container.exec_run("cat app/app.js").output.decode()
    
    # Run tests and capture failure
    test_result = container.exec_run("npx jest")
    if test_result.exit_code == 0:
        print("Already fixed.")
        return

    # Agent thinks and gets a fix
    print("Agent is fixing the bug.")
    fixed_code = get_ai_fix(code, test_result.output.decode())
    
    # Agent write file back to container
    container.exec_run(f"sh -c 'echo \"{fixed_code}\" > app/app.js'")
    
    # Verify
    final_test = container.exec_run("npx jest")
    if final_test.exit_code == 0:
        print("Result: AI FIXED")
    else:
        print("Result: AI FAILED")
    
    container.stop()
    container.remove()

if __name__ == "__main__":
    run_agent_benchmark()