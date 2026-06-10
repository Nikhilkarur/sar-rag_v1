import os
import re

base_dir = r"c:\Users\nkk77\Desktop\gsme\frontend\src"

def replace_in_file(path, pattern, repl, flags=0):
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    content = re.sub(pattern, repl, content, flags=flags)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)

# 1. Verifications.tsx
path = os.path.join(base_dir, "pages", "admin", "Verifications.tsx")
replace_in_file(path, r"description: `Tenant \$\{data\.name\} \(ID: \$\{data\.tenant_id\}\) has been approved and API keys generated\.`,", "description: `Tenant approved successfully. API Key: ${data.api_key}`,")

# 2. SARWorkspace.tsx
path = os.path.join(base_dir, "pages", "portal", "SARWorkspace.tsx")
replace_in_file(path, r"description: `Alert successfully approved at \$\{new Date\(result\.approved_at\)\.toLocaleTimeString\(\)\}\.`,", "description: `Alert successfully approved.`,")

# 3. Credentials.tsx
path = os.path.join(base_dir, "pages", "portal", "settings", "Credentials.tsx")
replace_in_file(path, r"const handleReveal = async \(\): Promise<string> => {[\s\S]*?const res = await revealApiKey\(\); return res\.api_key;[\s\S]*?}", "const handleReveal = async (): Promise<string> => {\n    const res = await revealApiKey();\n    return res.api_key;\n  }")

# 4. Schema.tsx
path = os.path.join(base_dir, "pages", "portal", "settings", "Schema.tsx")
replace_in_file(path, r"data\?\.map\(\(preset: any, i: any\)", "data?.map((preset: any, i: number)")
replace_in_file(path, r"data\?\.find\(\(f: any\) =>", "(data as any[])?.find((f: any) =>")

# 5. Webhook.tsx
path = os.path.join(base_dir, "pages", "portal", "settings", "Webhook.tsx")
replace_in_file(path, r"new_secret", "secret_prefix")
replace_in_file(path, r"setTestResult\(res as any\)", "setTestResult(res as any)")

print("TS fixes applied")
