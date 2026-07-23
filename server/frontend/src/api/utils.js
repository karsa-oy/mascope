export const extractDistinctValues = (objects, property) => {
  const propertyValues = objects.map((object) => object[property])
  const distinctPropertyValues = [...new Set(propertyValues)]
  return distinctPropertyValues.map((value) => ({ [property]: value }))
}

export function generateCopyName(originalName) {
  if (!originalName) return null
  const cleanedName = originalName.replace(/\s+/g, ' ').trim()

  const namePattern = cleanedName.match(/(.*\sCopy)(?:\((\d+)\))?$/)
  if (namePattern) {
    const baseName = namePattern[1]
    const copyNum = namePattern[2]
    if (copyNum) {
      return `${baseName}(${parseInt(copyNum) + 1})`
    } else {
      return `${baseName}(1)`
    }
  } else {
    return `${cleanedName} Copy`
  }
}

/**
 * Extract a human-readable message from a failed API call.
 *
 * The backend's error responses carry the message in `response.data.error`;
 * network-level failures (no response) only have `error.message`.
 *
 * @param {*} error the caught error (usually an axios error)
 * @param {string} fallback message to use when neither source is available
 * @returns {string} the message to show the user
 */
export function getApiErrorMessage(error, fallback = 'An error occurred') {
  return error?.response?.data?.error || error?.message || fallback
}

export function snakeToCamel(snakeCaseStr) {
  return snakeCaseStr.replace(/(_\w)/g, (match) => {
    return match[1].toUpperCase()
  })
}
