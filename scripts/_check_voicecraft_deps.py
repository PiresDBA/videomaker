import importlib.util
for m in ["dotenv", "edge_tts", "google", "openai", "requests"]:
    print(m, bool(importlib.util.find_spec(m)))
