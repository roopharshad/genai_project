"""Print the restoration Space's API (endpoints, parameters, choices).

Usage: .venv\\Scripts\\python.exe scripts\\inspect_restoration_api.py
"""
import truststore

truststore.inject_into_ssl()

from gradio_client import Client  # noqa: E402

client = Client("randomtable/Image-Restoration-GFPGAN", verbose=False)
client.view_api(all_endpoints=True)
print("Gradio version:", client.config.get("version"))
for comp in client.config["components"]:
    props = comp.get("props", {})
    if comp.get("type") in ("radio", "number", "image", "file"):
        print(f"- {props.get('label')}: {comp['type']} choices={props.get('choices')} default={props.get('value')}")
