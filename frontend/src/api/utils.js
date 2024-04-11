export const extractDistinctValues = (objects, property) => {
  const propertyValues = objects.map((object) => object[property])
  const distinctPropertyValues = [...new Set(propertyValues)]
  return distinctPropertyValues.map((value) => ({ [property]: value }))
}

export function generateCopyName(originalName) {
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

export function snakeToCamel(snakeCaseStr) {
  return snakeCaseStr.replace(/(_\w)/g, (match) => {
    return match[1].toUpperCase()
  })
}
