// Client-side mirror of the backend password policy
// (UserManager.validate_password). Kept in sync so users get instant feedback;
// the backend remains the source of truth and re-validates on submit.

export const MIN_PASSWORD_LENGTH = 12

// Identifiers shorter than this are not checked for containment, matching the
// backend, to avoid false positives on short email/username fragments.
const MIN_IDENTIFIER_LENGTH = 4

/**
 * Validate a candidate password against the policy.
 *
 * @param {string} password - The candidate password.
 * @param {object} [identifiers] - Optional account identifiers to check against.
 * @param {string} [identifiers.email] - The account email.
 * @param {string} [identifiers.username] - The account username.
 * @returns {string|null} A human-readable error message, or null if valid.
 */
export function passwordPolicyError(password, { email = null, username = null } = {}) {
  if (!password || password.length < MIN_PASSWORD_LENGTH) {
    return `Password must be at least ${MIN_PASSWORD_LENGTH} characters.`
  }

  const lowered = password.toLowerCase()

  const emailLocal = email ? email.split('@')[0].toLowerCase() : ''
  if (emailLocal.length >= MIN_IDENTIFIER_LENGTH && lowered.includes(emailLocal)) {
    return 'Password must not contain your email address.'
  }

  if (
    username &&
    username.length >= MIN_IDENTIFIER_LENGTH &&
    lowered.includes(username.toLowerCase())
  ) {
    return 'Password must not contain your username.'
  }

  return null
}
