#!/usr/bin/env python3
with open('lib/generate.py', 'r') as f:
    content = f.read()

# Find and replace the problematic create_wrapper_script method
# with a version that uses normal string interpolation instead of f-strings

old_method = '''    def create_wrapper_script(self, wrapper_name: str, app_id: str) -> str:
        """Create the content of a wrapper script."""
        return f"""#!/usr/bin/env bash
'''

new_method = '''    def create_wrapper_script(self, wrapper_name: str, app_id: str) -> str:
        """Create the content of a wrapper script."""
        script = ''' + '''"""#!/usr/bin/env bash
'''

# Find the end of the create_wrapper_script method
end_pattern = 'fi\n"'

# Split the content to extract the shell script template
import re
match = re.search(r'def create_wrapper_script.*?fi\n"""', content, re.DOTALL)
if match:
    old_full_method = match.group()
    
    # Extract the shell script part without f prefix
    shell_script = old_full_method.split('return f"""', 1)[1].rsplit('"""', 1)[0]
    
    # Replace Python variables using normal string interpolation
    shell_script = shell_script.replace('{wrapper_name}', wrapper_name)
    shell_script = shell_script.replace('{app_id}', app_id)
    shell_script = shell_script.replace('{self.config_dir}', str(self.config_dir))
    shell_script = shell_script.replace('{self.bin_dir}', str(self.bin_dir))
    
    # Rebuild the method
    new_full_method = f'''    def create_wrapper_script(self, wrapper_name: str, app_id: str) -> str:
        """Create the content of a wrapper script."""
        script = ''' + repr(shell_script) + '''
        return script
'''
    
    # Replace old method with new one
    content = content.replace(old_full_method, new_full_method)

    with open('lib/generate.py', 'w') as f:
        f.write(content)
    
    print('Successfully rebuilt wrapper script method')
else:
    print('Error: Could not find create_wrapper_script method')
