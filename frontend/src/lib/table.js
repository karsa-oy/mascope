import alasql from 'alasql'
import * as xlsx from 'xlsx/xlsx.mjs'

export default {
  select(rows, filters) {
    let result
    switch (typeof filters) {
      case 'object':
        if (filters) {
          result = rows.filter((row) => {
            let fullMatch = Object.entries(filters).every(([field, filter]) => row[field] == filter)
            return fullMatch
          })
        } else {
          result = []
        }
        break
      case 'string':
        switch (filters) {
          case '*':
            result = rows
            break
          default:
            throw Error('Unknown filter format in select operation')
        }
    }
    return result
  },
  get(rows, filters) {
    let results = this.select(rows, filters)
    switch (results.length) {
      case 0:
        return null
      case 1:
        return results[0]
      default:
        console.log(rows.map((row) => row.id))
        console.log(rows, filters)
        throw `There is no unique row`
    }
  },
  query(sql, tables) {
    // sort tables by their order in the query
    let tableNames = Object.keys(tables)
    let tableIndeces = tableNames
      .map((name) => sql.search(name))
      .map((i) => (i == -1 ? Infinity : i)) // missing tables go last
    let position = (n) => tableIndeces[tableNames.indexOf(n)]
    let sortedTableNames = tableNames.sort((a, b) => position(a) - position(b))
    let sortedTables = sortedTableNames.map((name) => tables[name])
    // substitute table names with question marks
    let replace = (s, p) => s.replace(p, '?')
    let parsedSql = sortedTableNames.reduce(replace, sql)
    // execute query with alasql
    try {
      let result = alasql(parsedSql, sortedTables)
      return result
    } catch (error) {
      console.error(`The following frontend SQL query failed:` + `${sql}`, {
        tables,
        error
      })
    }
  },
  fitSpreadsheetColumnWidths(worksheet) {
    const data = xlsx.utils.sheet_to_json(worksheet)
    if (data.length == 0) return
    const colLengths = Object.keys(data[0]).map((k) => (k ? k.toString().length : 0))
    for (const d of data) {
      Object.values(d).forEach((element, index) => {
        const length = element ? element.toString().length : 0
        if (colLengths[index] < length) {
          colLengths[index] = length
        }
      })
    }
    worksheet['!cols'] = colLengths.map((l) => {
      return {
        wch: l
      }
    })
    return worksheet
  },
  fromSpreadsheet(clipboardText, fields, skipHeader = false) {
    // Split full text to rows
    let clipboardLines = clipboardText.split(String.fromCharCode(10))
    // Skip header row
    if (skipHeader) clipboardLines.splice(0, 1)
    // Remove last line if empty
    if (!clipboardLines[clipboardLines.length - 1].length) clipboardLines.pop()
    let spreadsheet = []
    for (let clipboardLine of clipboardLines) {
      spreadsheet.push(clipboardLine.split(String.fromCharCode(9)))
    }
    let parsedRows = []
    for (let row of spreadsheet) {
      let parsedRow = {}
      for (let i in row) {
        let field = fields[i]
        parsedRow[field] = row[i].trim()
      }
      parsedRows.push(parsedRow)
    }
    return parsedRows
  },
  readHeader(clipboardText) {
    let fields = clipboardText.split(String.fromCharCode(10))[0].split(String.fromCharCode(9))
    return fields
  },
  toSpreadsheet(filename, sheets) {
    let workbook = xlsx.utils.book_new()
    for (let sheet of sheets) {
      let { rows, cols, name } = sheet
      // construct header
      let fields = cols.map((col) => col.field)
      let headerLabels = cols.map((col) => col.label)
      let header = Object.fromEntries(fields.map((field, index) => [field, headerLabels[index]]))
      // helper function for selecting only used columns
      let selectFields = (row) =>
        Object.fromEntries(Object.entries(row).filter(([field]) => fields.includes(field)))
      // add header and filter out unused fields
      let formattedRows = [header].concat(rows.map(selectFields))
      let worksheet = xlsx.utils.json_to_sheet(formattedRows, {
        // the default header uses field names
        // so we omit since we add our own header
        skipHeader: true
      })
      worksheet = this.fitSpreadsheetColumnWidths(worksheet)
      xlsx.utils.book_append_sheet(workbook, worksheet, name)
    }
    try {
      xlsx.writeFile(workbook, filename, { type: 'xlsx' })
    } catch (err) {
      console.error(err)
    }
  }
}
