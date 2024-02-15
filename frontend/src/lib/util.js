import { customAlphabet } from "nanoid";

export function beautifySnakeCase(str) {
  // Replace underscores with white space and capitalize first letter
  return capitalizeFirstLetter(str.replaceAll("_", " "));
}

export function camelToSnakeCase(str) {
  return str.replace(/[A-Z]/g, (letter) => `_${letter.toLowerCase()}`);
}

export function capitalizeFirstLetter(str) {
  return str[0].toUpperCase() + str.slice(1);
}

export function genId(len, case_sensitive = true) {
  if (case_sensitive) {
    var alphabet =
      "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz";
  } else {
    var alphabet = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ";
  }
  const nanoid = customAlphabet(alphabet, len);
  return nanoid();
}

export function parseAutosamplerCsv(rows) {
  function explodeSequenceStep(step) {
    let result = [];
    const cycles = step["Cycle(s)"];
    delete step["Cycle(s)"];
    for (let i = 0; i < cycles; ++i) {
      result.push(step);
    }
    return result;
  }
  let result = [];
  var sequenceStep = {};
  for (let row of rows) {
    for (let cellKey in row) {
      const [key, value] = row[cellKey].split(":");
      if (
        key == "Sequence step" ||
        Object.keys(sequenceStep).includes("Sequence step")
      ) {
        // New sequence step or append existing step
        if (key && key.length) {
          sequenceStep[key.trim()] = value.trim();
        }
      }
    }
    if (Object.keys(sequenceStep).includes("Presence")) {
      // Sequence step complete
      result.push(...explodeSequenceStep(sequenceStep));
      sequenceStep = {};
    }
  }
  return result;
}
