import docker

# 1. Connect to the local Docker daemon
client = docker.from_env()

print("🐳 Checking Docker connection...")
try:
    version = client.version()
    print(f"✅ Connected to Docker Engine v{version['Version']}!")
    
    # 2. Run a lightweight container test
    print("\n🚀 Spinning up a transient Python container to run 'python --version'...")
    output = client.containers.run(
        image="python:3.10-slim",
        command="python --version",
        remove=True  # Automatically delete the container when finished
    )
    print(f"📦 Container Output: {output.decode('utf-8').strip()}")
    print("\n🎉 Docker Python SDK is fully operational!")

except Exception as e:
    print(f"❌ Error connecting to Docker: {e}")