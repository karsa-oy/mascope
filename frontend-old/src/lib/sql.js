function stringArray(object) {
  if (!(object instanceof Object)) {
    throw Error('Object or Array expected')
  }
  if (object instanceof Array) {
    return "'" + array.join("', '") + "'"
  } else {
    return [stringArray(Object.keys(object)), stringArray(Object.values(object))]
  }
}
