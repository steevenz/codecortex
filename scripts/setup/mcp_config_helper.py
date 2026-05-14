import json
import os
import sys
import re

def strip_comments(text):
    # Strip // comments, but avoid stripping http:// or https://
    # We look for // that is NOT preceded by a colon
    text = re.sub(r'(?<!:)//.*', '', text)
    # Strip /* */ comments
    text = re.sub(r'/\*.*?\*/', '', text, flags=re.DOTALL)
    return text

def strip_trailing_commas(text):
    # Remove trailing commas before } or ]
    text = re.sub(r',\s*([}\]])', r'\1', text)
    return text

def update_json(path, key, config):
    try:
        # Use utf-8-sig to handle BOM automatically
        with open(path, 'r', encoding='utf-8-sig') as f:
            content = f.read()
        
        clean_content = strip_comments(content)
        clean_content = strip_trailing_commas(clean_content)
        
        try:
            # Use strict=False to allow some control characters
            data = json.loads(clean_content, strict=False)
        except json.JSONDecodeError as e:
            if not content.strip():
                data = {}
            else:
                print(f"JSON Parse Error in {path}: {e}")
                print("Cleaned content snippet:")
                print(clean_content[:500])
                raise e
                
        if key not in data:
            data[key] = {}
        
        # Determine service name
        service_name = "creative-critical-thinking"
        if "codecortex" in str(config):
             service_name = "codecortex"
             
        data[key][service_name] = config
        
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
        return True
    except Exception as e:
        print(f"Error updating JSON {path}: {e}")
        return False

def update_yaml(path, key, config):
    try:
        import yaml
    except ImportError:
        return False
    try:
        with open(path, 'r', encoding='utf-8-sig') as f:
            data = yaml.safe_load(f) or {}
        if key not in data: data[key] = {}
        
        service_name = "creative-critical-thinking"
        if "codecortex" in str(config):
             service_name = "codecortex"
             
        data[key][service_name] = config
        
        with open(path, 'w', encoding='utf-8') as f:
            yaml.safe_dump(data, f, default_flow_style=False)
        return True
    except Exception as e:
        print(f"Error updating YAML {path}: {e}")
        return False

def update_toml(path, key, config):
    try:
        with open(path, 'r', encoding='utf-8-sig') as f:
            content = f.read()
        section = f"[{key}]"
        if section in content:
            service_name = "creative-critical-thinking"
            if "codecortex" in str(config): service_name = "codecortex"
            
            if f'"{service_name}"' in content: return True
            
            new_entry = f'\n"{service_name}" = {{ command = "npx", args = ["--yes", "--package", "{config["args"][2]}", "{service_name}"], env = {{ CCT_PORT = "8010" }} }}\n'
            content = content.replace(section, section + new_entry)
            with open(path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
    except: pass
    return False

if __name__ == "__main__":
    if len(sys.argv) < 5: sys.exit(1)
    path, key, config_file, fmt = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
    with open(config_file, 'r', encoding='utf-8') as f:
        config = json.load(f)
    success = False
    if fmt == "JSON": success = update_json(path, key, config)
    elif fmt == "YAML": success = update_yaml(path, key, config)
    elif fmt == "TOML": success = update_toml(path, key, config)
    sys.exit(0 if success else 1)
