#!/usr/bin/env python3
import re
import sys
from pathlib import Path


def rebuild_wrapper_script():
    """Rebuild the wrapper script method to replace f-strings with normal strings."""
    # Read the content of the generate.py file
    generate_file = Path("lib/generate.py")
    if not generate_file.exists():
        print(f"Error: {generate_file} does not exist")
        return False

    content = generate_file.read_text()

    # Find the create_wrapper_script method
    match = re.search(
        r'def create_wrapper_script\(self, wrapper_name: str, app_id: str\) -> str:.*?return f""".*?fi\n"""',
        content,
        re.DOTALL,
    )
    if match:
        old_full_method = match.group()

        # Extract the shell script part without f prefix
        shell_script_part = old_full_method.split('return f"""', 1)[1].rsplit('"""', 1)[
            0
        ]

        # Create a template with placeholders
        shell_script_template = shell_script_part.replace(
            "{wrapper_name}", "{wrapper_name}"
        )
        shell_script_template = shell_script_template.replace("{app_id}", "{app_id}")
        shell_script_template = shell_script_template.replace(
            "{self.config_dir}", "{config_dir}"
        )
        shell_script_template = shell_script_template.replace(
            "{self.bin_dir}", "{bin_dir}"
        )

        # Build the new method that uses .format() instead of f-strings
        new_full_method = f'''    def create_wrapper_script(self, wrapper_name: str, app_id: str) -> str:
        """Create the content of a wrapper script."""
        shell_script = """{shell_script_template}"""
        # Replace placeholders with actual values
        script = shell_script.format(
            wrapper_name=wrapper_name,
            app_id=app_id,
            config_dir=str(self.config_dir),
            bin_dir=str(self.bin_dir)
        )
        return script'''

        # Replace old method with new one
        content = content.replace(old_full_method, new_full_method)

        # Write the updated content back to the file
        generate_file.write_text(content)

        print("Successfully rebuilt wrapper script method")
        return True
    else:
        print("Error: Could not find create_wrapper_script method")
        return False


if __name__ == "__main__":
    success = rebuild_wrapper_script()
    sys.exit(0 if success else 1)
