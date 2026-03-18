import requests
import time
import hashlib
import base64
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat, PrivateFormat, NoEncryption

BASE = "https://wrcenmardnbprfpqhrqe.supabase.co/functions/v1/peanut-mining"
AGENT_ID = "jeremy_agent_001"  # Change this to something unique

# Generate keys
private_key = Ed25519PrivateKey.generate()
pub_bytes = private_key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
PUBLIC_KEY_B64 = base64.b64encode(pub_bytes).decode()

def sign(data: str) -> str:
    signature = private_key.sign(data.encode())
    return base64.b64encode(signature).decode()

def solve_hash_challenge(payload_b64: str, difficulty: int) -> str:
    payload = base64.b64decode(payload_b64)
    nonce = 0
    prefix = b'\x00' * difficulty
    while True:
        candidate = payload + nonce.to_bytes(8, 'big')
        digest = hashlib.sha256(candidate).digest()
        if digest[:difficulty] == prefix:
            return digest.hex()
        nonce += 1

def register():
    print(f"Registering agent: {AGENT_ID}")
    r = requests.post(f"{BASE}/register", json={
        "agent_id": AGENT_ID,
        "public_key": PUBLIC_KEY_B64,
        "compute_capability": "CPU",
        "max_vcus": 500
    })
    print("Register response:", r.json())

def mine_loop():
    while True:
        try:
            task_resp = requests.get(f"{BASE}/tasks/current")
            task = task_resp.json()
            print(f"\nTask: {task.get('task_id')} | Type: {task.get('type')} | Difficulty: {task.get('difficulty')}")

            task_id = task["task_id"]
            task_type = task.get("type", "hash_challenge")
            payload = task.get("payload", "")
            difficulty = task.get("difficulty", 3)

            start = time.time()

            if task_type == "hash_challenge":
                solution = solve_hash_challenge(payload, difficulty)
            else:
                solution = hashlib.sha256(payload.encode()).hexdigest()

            elapsed_ms = int((time.time() - start) * 1000)

            sig_input = f"{AGENT_ID}:{task_id}:{solution}"
            signature = sign(sig_input)

            result = requests.post(f"{BASE}/submit", json={
                "agent_id": AGENT_ID,
                "task_id": task_id,
                "solution": solution,
                "signature": signature,
                "compute_time_ms": elapsed_ms
            }).json()

            vcus = result.get("vcus_credited", 0)
            peanut = result.get("peanut_earned", 0)
            status = result.get("status", "unknown")
            print(f"Status: {status} | VCUs: {vcus} | $PEANUT: {peanut:,} | Time: {elapsed_ms}ms")

        except Exception as e:
            print(f"Error: {e}")

        time.sleep(3)

if __name__ == "__main__":
    register()
    mine_loop()
