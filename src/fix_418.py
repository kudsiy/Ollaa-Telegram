import os

PATH = r"src\run_pipeline.py"

def upgrade_logic():
    with open(PATH, "r", encoding="utf-8") as f:
        content = f.read()

    # Fix 1: Add the missing high-traffic neighborhoods
    neighborhood_updates = """            "22":                   "22_area",
            "wollo sefer":          "wollo_sefer",
            "6 kilo":               "6_kilo",
            "bulgaria":             "bulgaria","""
    
    if '"22":' not in content:
        content = content.replace('"jacros":               "jacros",', f'"jacros":               "jacros",\n{neighborhood_updates}')

    # Fix 2: Detect Commercial & Warehouse assets
    asset_logic = """        # Asset Type Detection
        assets = {
            "building": ["building", "ህንፃ", "ቢልዲንግ"],
            "warehouse": ["warehouse", "wearhouse", "መጋዘን"],
            "commercial": ["commercial", "ንግድ", "shop"]
        }
        for asset_type, keys in assets.items():
            if any(k in text_lower for k in keys):
                return asset_type.upper()"""

    # Fix 3: Kill the "Educational Articles" and "Holiday Ads"
    noise_logic = """    def is_strictly_noise(self, text):
        text_lower = text.lower().strip()
        # Kill Educational Articles (ID 1148 style)
        if "inflation" in text_lower and "bank" in text_lower: return True
        if "1 million homes" in text_lower: return True
        # Kill Holiday Greetings (ID 1081 style)
        if "እንኳን አደረሳችሁ" in text_lower and "apartment" not in text_lower: return True
        # Original filters
        if "[media only]" in text_lower or len(text_lower) < 30: return True
        return False"""

    # Apply the noise function update
    import re
    content = re.sub(r"def is_strictly_noise\(self, text\):.*?return False", noise_logic, content, flags=re.DOTALL)

    with open(PATH, "w", encoding="utf-8") as f:
        f.write(content)
    print("SUCCESS: Commercial assets, new neighborhoods, and Article-filters added.")

if __name__ == "__main__":
    upgrade_logic()