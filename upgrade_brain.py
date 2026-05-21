import os

PATH = r"src\run_pipeline.py"

def fix_it():
    if not os.path.exists(PATH):
        print("Error: File not found.")
        return

    with open(PATH, "r", encoding="utf-8") as f:
        lines = f.readlines()

    # Find where the broken function starts
    start = -1
    for i, line in enumerate(lines):
        if "def is_strictly_noise" in line:
            start = i
            break
    
    if start == -1:
        print("Could not find the function. The file might be too messy.")
        return

    # This is the perfectly spaced version of the function
    new_function = [
        "    def is_strictly_noise(self, text):\n",
        "        text_lower = text.lower().strip()\n",
        "        # Filter out the 'Investment Talk' junk you saw in the 33 rows\n",
        "        marketing = ['roi', 'investment', '1 million homes', 'future of africa', 'growth', 'ባለሀብት']\n",
        "        if any(k in text_lower for k in marketing) and 'price' not in text_lower:\n",
        "            return True\n",
        "        # Filter out short link-only garbage\n",
        "        if '[media only]' in text_lower or 'https://' in text_lower or len(text_lower) < 25:\n",
        "            return True\n",
        "        return False\n"
    ]

    # Find where the old function ends (the next 'def')
    end = start + 1
    while end < len(lines):
        if "    def " in lines[end]:
            break
        end += 1

    # Stitch the file back together with the fix
    final_lines = lines[:start] + new_function + lines[end:]

    with open(PATH, "w", encoding="utf-8") as f:
        f.writelines(final_lines)
    print("SUCCESS: Spacing fixed. Your 'brain' is now correctly upgraded.")

if __name__ == "__main__":
    fix_it()