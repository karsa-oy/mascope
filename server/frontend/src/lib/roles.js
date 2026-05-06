// Canonical role definitions shared by global and workspace roles
const roleDefinitions = [
  { name: 'guest', level: 100, label: '🥽 Guest' },
  { name: 'editor', level: 200, label: '📝 Editor' },
  { name: 'admin', level: 300, label: '🔑 Admin' },
  { name: 'owner', level: 400, label: '👑 Owner' }
]

// Global roles (value is numeric role_id)
export const roles = roleDefinitions.map(({ level, label }) => ({ value: level, label }))

export const prettyRoleName = (user) =>
  roleDefinitions.find(({ name }) => name === user.role_name)?.label

// Workspace roles (value is string role name)
export const workspaceRoles = roleDefinitions.map(({ name, level, label }) => ({
  value: name,
  level,
  label
}))

export const prettyWorkspaceRoleName = (role) =>
  roleDefinitions.find(({ name }) => name === role)?.label

export const roleLevel = (roleName) =>
  roleDefinitions.find(({ name }) => name === roleName)?.level ?? 0
