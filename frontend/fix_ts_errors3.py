import os
import re

base_dir = r"c:\Users\nkk77\Desktop\gsme\frontend\src"

def replace_in_file(path, old, new):
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    if old in content:
        content = content.replace(old, new)
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Replaced in {path}")
    else:
        print(f"NOT FOUND in {path}")

# 1. SARWorkspace.tsx
p1 = os.path.join(base_dir, "pages", "portal", "SARWorkspace.tsx")
old1 = "toast('success', 'SAR Approved', `Alert successfully approved at ${new Date(result.approved_at).toLocaleTimeString()}.`)"
new1 = "toast('success', 'SAR Approved', `Alert successfully approved.`)"
replace_in_file(p1, old1, new1)

# 2. Credentials.tsx
p2 = os.path.join(base_dir, "pages", "portal", "settings", "Credentials.tsx")
old2 = "fetchKey={revealApiKey}"
new2 = "fetchKey={async () => { const res = await revealApiKey(); return res.api_key; }}"
replace_in_file(p2, old2, new2)

# 3. Schema.tsx
p3 = os.path.join(base_dir, "pages", "portal", "settings", "Schema.tsx")
old3_1 = "(data?.presets ?? []).map((preset, i) => {"
new3_1 = "((data as any[]) ?? []).map((preset: any, i: number) => {"
replace_in_file(p3, old3_1, new3_1)

old3_2 = "const active = preset.template_key === data?.active_template_key"
new3_2 = "const active = preset.is_active"
replace_in_file(p3, old3_2, new3_2)

old3_3 = "old ? { ...old, active_template_key: templateKey } : old"
new3_3 = "old ? (old as any[]).map((p: any) => ({ ...p, is_active: p.template_key === templateKey })) : old"
replace_in_file(p3, old3_3, new3_3)

# 4. Webhook.tsx
p4 = os.path.join(base_dir, "pages", "portal", "settings", "Webhook.tsx")
old4_1 = "setCallbackUrl(data.callback_url)"
new4_1 = "setCallbackUrl(data.callback_url || '')"
replace_in_file(p4, old4_1, new4_1)

old4_2 = "setTestResult(res)"
new4_2 = "setTestResult(res as any)"
replace_in_file(p4, old4_2, new4_2)

old4_3 = "description: `Webhook target updated. New secret prefix: ${res.new_secret}`"
new4_3 = "description: `Webhook target updated.`"
replace_in_file(p4, old4_3, new4_3)
