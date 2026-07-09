import docker
import os
import requests
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

client_docker = docker.from_env()
client_ai = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def post_comment(message):
    token = os.getenv("GITHUB_TOKEN")
    repo = os.getenv("GITHUB_REPOSITORY")
    number = os.getenv("ISSUE_NUMBER") 
    
    if not all([token, repo, number]):
        print("Missing GitHub env vars, skipping comment.")
        return

    url = f"https://api.github.com/repos/{repo}/issues/{number}/comments"
    headers = {
        "Authorization": f"token {token}", 
        "Accept": "application/vnd.github.v3+json"
    }
    
    response = requests.post(url, json={"body": message}, headers=headers)
    
    if response.status_code == 201:
        print(f"Successfully posted comment to {url}")
    else:
        print(f"Failed to post comment. Status Code: {response.status_code}, Response Body: {response.text}")

def get_ai_fix(code, error):
    prompt = f"Fix this code that causes the following test error:\n\nCODE:\n{code}\n\nERROR:\n{error}\n\nReturn ONLY the corrected code."
    response = client_ai.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content

def run_agent_benchmark():
    container = None
    try:
        # Start container
        container = client_docker.containers.run("mini-benchmark:latest", detach=True, tty=True, 
                                                entrypoint="/bin/sh -c 'sleep infinity'")
        
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
        escaped_code = fixed_code.replace('"', '\\"') # type: ignore
        container.exec_run(f"sh -c 'echo \"{escaped_code}\" > app/app.js'")
        
        # Verify
        final_test = container.exec_run("npx jest")
        if final_test.exit_code == 0:
            print("Result: AI FIXED")
            post_comment(f"""AI has proposed a fix. Tests passed. Please review proposed changes below:
                         
                        ```javascript
                        {fixed_code}
                        """)
        else:
            print("Result: AI FAILED")
            post_comment(f"""AI failed to fix the bug. Tests are still failing after AI's attempt.
                         
                        Jest output:
                        {final_test.output.decode()[-1000:]}
                        """)
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        if container:
            container.stop()
            container.remove()

if __name__ == "__main__":
    run_agent_benchmark()