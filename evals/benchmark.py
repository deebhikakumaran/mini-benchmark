import docker
import os
import re
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

    if response.status_code != 201:
        print(f"Failed to post comment: {response.text}")

def get_ai_fix(app_code, test_code, error):
    prompt = f"""
    You are an expert debugger. I am providing you with the application code and the test file.
    
    APP CODE (app/app.js):
    {app_code}
    
    TEST CODE (tests/todo.test.js):
    {test_code}
    
    ERROR:
    {error}
    
    CRITICAL INSTRUCTIONS:
    1. The error 'TypeError: app.address is not a function' happens because Supertest needs a proper server instance or correctly exported app.
    2. Do NOT add 'app.listen()' to app.js.
    3. If app.js is correctly exporting the app, modify the test file to wrap the app using 'http.createServer(app)'.
    4. Provide the fixed file content for the file you modified.
    
    Return the result in this JSON-like format:
    FILE: <filename>
    CODE:
    <corrected code>
    """
    
    response = client_ai.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}]
    )
    content = response.choices[0].message.content
    return content.replace("```javascript", "").replace("```", "").strip()  # type: ignore

def run_agent_benchmark():
    container = None
    try:
        # Start container
        container = client_docker.containers.run("mini-benchmark:latest", detach=True, tty=True, 
                                                entrypoint="/bin/sh -c 'sleep infinity'")
        
        # Get the current buggy code
        app_code = container.exec_run("cat app/app.js").output.decode()
        test_code = container.exec_run("cat tests/todo.test.js").output.decode()
        
        # Run tests and capture failure
        test_result = container.exec_run("npx jest")
        if test_result.exit_code == 0:
            print("Already fixed.")
            return

        # Agent thinks and gets a fix
        print("Agent is fixing the bug.")
        fixed_output = get_ai_fix(app_code, test_code, test_result.output.decode())

        # Parse output for file path and code
        match = re.search(r"FILE: ([\w\/\.]+)\n([\s\S]*)", fixed_output)
        if match:
            file_path = match.group(1)
            code_content = match.group(2).replace("```javascript", "").replace("```", "").strip()
            
            # Escape and agent writes back to container
            escaped_code = code_content.replace('"', '\\"')
            container.exec_run(f"sh -c 'echo \"{escaped_code}\" > {file_path}'")
        
        # Verify
        final_test = container.exec_run("npx jest")
        if final_test.exit_code == 0:
            print("Result: AI FIXED")
            post_comment(f"""AI has proposed a fix. Tests passed. 
                            Please review proposed changes to {file_path} below:
                                                    
                            ```javascript
                            {code_content}
                            ```""")
        else:
            print("Result: AI FAILED")
            log = final_test.output.decode()[-1000:] 
            post_comment(f"""AI failed to fix the bug. 
                            Tests are still failing after AI's attempt.

                            Jest output:
                            ```
                            {log}
                            ```""")
            
    except Exception as e:
        post_comment(f"Benchmark Error: {str(e)}")
    finally:
        if container:
            container.stop()
            container.remove()

if __name__ == "__main__":
    run_agent_benchmark()