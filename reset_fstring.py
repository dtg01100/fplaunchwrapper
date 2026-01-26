#!/usr/bin/env python3
import re


def fix_fstring_syntax():
    """Fix f-string syntax issues in the generate.py file."""
    with open("lib/generate.py", "r") as f:
        content = f.read()

    # Fix all the f-string issues in the create_wrapper_script method
    old_method = content[
        content.find("    def create_wrapper_script") : content.rfind(
            '"""', 0, content.find("    def generate_all_wrappers")
        )
        + 3
    ]

    # Extract the bash script content and fix all ${} patterns
    bash_script = old_method.split('return f"""', 1)[1].rsplit('"""', 1)[0]

    # Fix all occurrences of \${{ or \$ to be plain ${}
    bash_script = re.sub(r"\\\${{", r"${", bash_script)
    bash_script = re.sub(r"\\\$", r"$", bash_script)

    # Find all the ${variable} patterns that need to be kept
    variables = re.findall(r"\${([^}]+)}", bash_script)

    # For each variable, determine if it's a Python variable or bash variable
    python_vars = ["wrapper_name", "app_id", "self.config_dir", "self.bin_dir"]

    # Escape all bash variables with double $$
    for var in variables:
        if var not in python_vars:
            bash_script = bash_script.replace(f"${{{var}}}", "${{var}}")

    # Rebuild the method
    new_method = f'''    def create_wrapper_script(self, wrapper_name: str, app_id: str) -> str:
        """Create the content of a wrapper script."""
        return f"""
{bash_script}
"""'''

    # Replace the old method with new one
    content = content.replace(old_method, new_method)

    with open("lib/generate.py", "w") as f:
        f.write(content)

    print("Successfully fixed f-string syntax")


if __name__ == "__main__":
    fix_fstring_syntax()
