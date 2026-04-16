import httpx
import os
import sys

API_URL = "http://localhost:8000/analyze"
TEST_DIR = "testing-pdfs"

def test_api(file_path):
    print(f"\n[{file_path}]")
    print(f"Reading file from {file_path}...")
    with open(file_path, "rb") as f:
        file_bytes = f.read()
    filename = os.path.basename(file_path)

    import mimetypes
    mime_type, _ = mimetypes.guess_type(file_path)
    if not mime_type:
        mime_type = "application/octet-stream"

    print("--- STEP 1: Sending to Momotopsy Analysis... ---")
    try:
        response = httpx.post(
            "http://localhost:8000/analyze",
            files={"file": (filename, file_bytes, mime_type)},
            timeout=None
        )
        
        if response.status_code == 200:
            print("[SUCCESS] Analysis complete!")
            data = response.json()
            print(f"Document Risk Score: {data.get('document_risk_score')}")
            
            # --- SHOW LIFECYCLE EVENTS ---
            events = data.get('lifecycle_events', [])
            if events:
                print("\nEXTRACTED LIFECYCLE EVENTS:")
                for e in events:
                    print(f"  - [{e['event_type']}] {e['deadline_date']}: {e['description']}")
            
            print("\nFLAGED CLAUSES & NEGOTIATION TEST:")
            predatory_nodes = [n for n in data.get('graph', {}).get('nodes', []) if n.get('label') == 'Predatory']
            
            if not predatory_nodes:
                print("  (No predatory clauses detected in this document)")
            
            for node in predatory_nodes:
                print("-" * 50)
                print(f"Text: {node.get('text')[:100]}...")
                print(f"Risk: {node.get('risk_score')} | Reason: {node.get('reason_flagged')}")
                
                # --- TEST NEGOTIATION KIT ---
                print("Testing Counter-Strike Generation...")
                neg_payload = {
                    "node_id": node.get("id", "test"),
                    "original_text": node.get("text"),
                    "improved_text": node.get("improved_clause"),
                    "document_type": "Uncategorized Contract"
                }
                neg_resp = httpx.post("http://localhost:8000/api/negotiate", json=neg_payload, timeout=30.0)
                if neg_resp.status_code == 200:
                    print(f"Negotiation Generated: {neg_resp.json().get('email_subject')}")
                else:
                    print(f"Negotiation Failed: {neg_resp.status_code}")

            # --- CHECK SCAM RADAR ---
            print("\n--- STEP 2: Checking Scam Radar Leaderboard... ---")
            radar_resp = httpx.get("http://localhost:8000/api/trending-risks")
            if radar_resp.status_code == 200:
                print("Current Trending Risks:")
                for item in radar_resp.json().get("trending", []):
                    print(f"  - {item['issue']}: {item['count']} hits")
            
        else:
            print(f"API Error: {response.status_code}")
            print(response.text)
            
    except httpx.ConnectError:
        print("Could not connect to FastAPI server. Make sure 'python main.py' is running!")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        test_api(sys.argv[1])
    else:
        if not os.path.exists(TEST_DIR):
            print(f"Directory '{TEST_DIR}' does not exist. Creating it...")
            os.makedirs(TEST_DIR)
            print(f"Please place some sample PDFs in '{TEST_DIR}' and run again.")
            sys.exit(0)
            
        supported_exts = {".pdf", ".docx", ".png", ".jpg", ".jpeg"}
        test_files = [f for f in os.listdir(TEST_DIR) if os.path.splitext(f)[1].lower() in supported_exts]
        
        if not test_files:
            print(f"No supported files found in '{TEST_DIR}'. Please download sample PDFs or DOCXs into this folder.")
            sys.exit(0)
            
        print(f"Found {len(test_files)} file(s) in '{TEST_DIR}'. Starting batch tests...")
        for f in test_files:
            test_api(os.path.join(TEST_DIR, f))
