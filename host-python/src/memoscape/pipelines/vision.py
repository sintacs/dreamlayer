def extract_object_memory(scene):
    obj = scene["object"]
    return {"object": obj["name"], "place": scene["place"]["name"],
            "detail": obj.get("near",""), "last_seen": scene.get("last_seen",""),
            "confidence": scene.get("confidence", 0.85)}
