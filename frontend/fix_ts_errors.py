import os

base_dir = r"c:\Users\nkk77\Desktop\gsme\frontend\src"

def replace_in_file(path, old, new):
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    content = content.replace(old, new)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)

# 1. api/auth.ts
path = os.path.join(base_dir, "api", "auth.ts")
replace_in_file(path, "import type { LoginPayload, SignupPayload, User } from '../types'", "import type { User } from '../types'")
replace_in_file(path, "login(payload: LoginPayload)", "login(payload: any)")
replace_in_file(path, "signup(payload: SignupPayload)", "signup(payload: any)")

# 2. Login.tsx
path = os.path.join(base_dir, "pages", "auth", "Login.tsx")
replace_in_file(path, "login(email, password)", "login({ email, password })")

# 3. Verifications.tsx
path = os.path.join(base_dir, "pages", "admin", "Verifications.tsx")
replace_in_file(path, "description: `Tenant ${data.name} (ID: ${data.tenant_id}) has been approved and API keys generated.`,", "description: `Tenant approved successfully. ${data.message}`,")

# 4. SARWorkspace.tsx
# error TS2339: Property 'approved_at' does not exist on type 'void'.
path = os.path.join(base_dir, "pages", "portal", "SARWorkspace.tsx")
replace_in_file(path, "toast({ title: 'SAR Approved', description: `Alert successfully approved at ${new Date(result.approved_at).toLocaleTimeString()}.`, variant: 'success' })", "toast({ title: 'SAR Approved', description: `Alert successfully approved.`, variant: 'success' })")

# 5. Credentials.tsx
# error TS2322: Type '() => Promise<{ api_key: string; }>' is not assignable to type '() => Promise<string>'.
path = os.path.join(base_dir, "pages", "portal", "settings", "Credentials.tsx")
replace_in_file(path, "const handleReveal = async (): Promise<string> => {", "const handleReveal = async (): Promise<string> => {")
replace_in_file(path, "return await revealApiKey()", "const res = await revealApiKey(); return res.api_key;")

# 6. Schema.tsx
# error TS2339: Property 'presets' does not exist on type 'NoInfer<any[]>'.
path = os.path.join(base_dir, "pages", "portal", "settings", "Schema.tsx")
replace_in_file(path, "data?.presets.map((preset: any, i: any)", "data?.map((preset: any, i: any)")
replace_in_file(path, "isActive = preset.template_key === data?.active_template_key", "isActive = preset.is_active")
replace_in_file(path, "data?.presets.find((f: any) => f.template_key === activeTemplate)", "data?.find((f: any) => f.template_key === activeTemplate)")

# 7. Webhook.tsx
# error TS2322: Type 'null' is not assignable to type 'string | undefined'.
path = os.path.join(base_dir, "pages", "portal", "settings", "Webhook.tsx")
replace_in_file(path, "setCallbackUrl(data.callback_url)", "setCallbackUrl(data.callback_url || '')")
replace_in_file(path, "description: `Webhook target updated. New secret prefix: ${res.new_secret}`", "description: `Webhook target updated.`")
replace_in_file(path, "setTestResult(res)", "setTestResult(res as any)")

print("TS fixes applied")
