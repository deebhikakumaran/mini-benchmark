import docker

def run_benchmark():
    client = docker.from_env()
    print("--- Initiating Sandbox Evaluation ---")
    
    try:
        container_output = client.containers.run(
            image="mini-benchmark:latest",
            remove=True
        )
        print("Result: PASSED")
        
    except docker.errors.ContainerError as e: # type: ignore
        print("Result: FAILED")
        print(e.stderr.decode('utf-8'))
        
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    run_benchmark()