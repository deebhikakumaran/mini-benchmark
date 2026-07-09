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

def get_issue_info():
    token = os.getenv("GITHUB_TOKEN")
    repo = os.getenv("GITHUB_REPOSITORY")
    number = os.getenv("ISSUE_NUMBER")

    if not all([token, repo, number]):
        print("No issue info available.")
        return
    
    url = f"https://api.github.com/repos/{repo}/issues/{number}"
    headers = {"Authorization": f"token {token}"}
    response = requests.get(url, headers=headers).json()

    title = response.get('title', '')
    description = response.get('body', '')
    return f"TITLE: {title}\nDESCRIPTION: {description}"

def get_ai_fix(app_code, test_code, error, issue_info):
    # Diagnosis Phase
    diagnosis_prompt = f"""
    Analyze this bug and write a 3-sentence summary of the root cause.
    ISSUE: {issue_info}
    TEST ERROR: {error}
    """

    response = client_ai.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "You are a code patching machine. Output ONLY structured file blocks. No conversational text."},
            {"role": "user", "content": diagnosis_prompt},
        ]
    )
    
    diagnosis = response.choices[0].message.content
    
    # Solution Phase
    solution_prompt = f"""
    DIAGNOSIS: {diagnosis}
    
    APP CODE: {app_code}
    TEST CODE: {test_code}
    
    CRITICAL FORMATTING RULES (FAILURE TO FOLLOW WILL BREAK THE SYSTEM):
    1. Output ONLY the file blocks in the format below.
    2. Do NOT include ANY introductory text, greetings, or explanations.
    3. Use this exact format for EACH file:
    FILE: <file_path>
    CODE:
    <full_file_content_here>
    END_FILE
    """
    
    response = client_ai.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "You are a code patching machine. Output ONLY structured file blocks. No conversational text."},
            {"role": "user", "content": diagnosis_prompt},
            {"role": "assistant", "content": diagnosis},
            {"role": "user", "content": solution_prompt}
        ]
    )
    
    content = response.choices[0].message.content
    return content.replace("```javascript", "").replace("```", "").strip() # type: ignore

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
        
        # Get issue information
        issue_info = get_issue_info()

        # Agent thinks and gets a fix
        print("Agent is fixing the bug.")
        fixed_output = get_ai_fix(app_code, test_code, test_result.output.decode(), issue_info)
        print(f"DEBUG: Searching for patterns in output: {fixed_output[:100]}...")

        if "FILE:" in fixed_output:
            fixed_output = fixed_output[fixed_output.find("FILE:"):]

        # Parse all file blocks
        pattern = r"FILE:\s*(?P<path>[\w\/\.]+)(?:\s*CODE:)?\s*(?P<code>[\s\S]*?)(?:END_FILE|$)"
        matches = list(re.finditer(pattern, fixed_output, re.IGNORECASE))

        if len(matches) == 0:
            print("Regex failed to match. AI did not follow format.")
        else:
            print(f"DEBUG: Found {len(matches)} matches.")

        ai_final_code = []

        for match in matches:
            file_path = match.group('path')
            code_content = match.group('code').replace("```javascript", "").replace("```", "").strip()
            
            # Escape and write each file
            escaped_code = code_content.replace('"', '\\"')
            container.exec_run(f"sh -c 'echo \"{escaped_code}\" > {file_path}'")

            ai_final_code.append({"file": file_path, "code": code_content})
            print(f"Updated {file_path}")

        report = "### AI proposed the following changes:\n"
        for entry in ai_final_code:
            report += f"\n#### File: `{entry['file']}`\n```javascript\n{entry['code']}\n```\n"
                
        # Verify
        final_test = container.exec_run("npx jest")
        if final_test.exit_code == 0:
            print("Result: AI FIXED")
            post_comment(f"""AI has proposed a fix. Tests passed. 
                            {report}
                          """)
        else:
            print("Result: AI FAILED")
            log = final_test.output.decode()[-1000:] 
            post_comment(f"""AI failed to fix the bug. 
                            Tests are still failing after AI's attempt.

                            Jest output:
                            ```
                            {log}
                            ```

                            {report}
                            """)
            
    except Exception as e:
        post_comment(f"Benchmark Error: {str(e)}")
    finally:
        if container:
            container.stop()
            container.remove()

if __name__ == "__main__":
    run_agent_benchmark()