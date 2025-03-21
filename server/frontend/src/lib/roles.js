export const roles = [
  { value: 100, label: '🥽 Guest' },
  { value: 200, label: '📝 Editor' },
  { value: 300, label: '🔑 Admin' },
  { value: 400, label: '👑 Owner' }
]

export const prettyRoleName = (user) =>
  roles.find(({ label }) => label.toLowerCase().includes(user.role_name))?.label
