import sys
import os

# Ensure we can import from services
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from services.memory.store import MemoryStore

def test_memory():
    print("Initializing Memory Store (Embedded Mode)...")
    # Use a temp path for testing or the workspace path
    memory = MemoryStore(use_local=True, local_path="/tmp/test_qdrant_db")
    
    print("Adding memories...")
    memory.add_memory("The project code name is Project Apollo.", {"project": "Apollo"})
    memory.add_memory("The server IP address is 192.168.1.50.", {"type": "config"})
    memory.add_memory("Meeting at 3 PM heavily discussed the new UI design.", {"topic": "UI"})
    
    print("Searching for 'what is the project name?'...")
    results = memory.search_memory("what is the project name?")
    
    for r in results:
        print(f"Found: {r['text']} (Score: {r['score']:.4f})")
        if "Apollo" in r['text']:
            print("SUCCESS: Retrieved correct memory!")
            return

    print("FAILURE: Did not find Apollo memory.")

if __name__ == "__main__":
    test_memory()
