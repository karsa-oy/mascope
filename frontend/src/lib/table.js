import { customAlphabet } from "nanoid";
import alasql from 'alasql';
import * as xlsx from 'xlsx/xlsx.mjs';

export default {
    // TODO - decouple ID generators from the table modules
    genId(length = 16) {
        let id = generateId(length);
        return id;
    },
    genIds(number, length = 16) {
        return Array(number).fill()
            .map(() => this.genId(length));
    },
    select(rows, filters) {
        let result;
        switch (typeof filters) {
            case 'object':
                if (filters) {
                    result = rows.filter((row) => {
                        let fullMatch = Object.entries(filters)
                            .every(([field, filter]) => (row[field] == filter));
                        return fullMatch;
                    });
                } else {
                    result = [];
                }
                break;
            case 'string':
                switch (filters) {
                    case '*':
                        result = rows;
                        break;
                    default:
                        throw Error("Unknown filter format in select operation");
                }
        }
        return result;
    },
    remove(rows, filters) {
        let result;
        switch (typeof filters) {
            case 'object':
                if (filters) {
                    result = rows.filter((row) => {
                        let partialMatch = Object.entries(filters)
                            .some(([field, filter]) => {
                                let value = row[field]
                                if (filter instanceof Array) {
                                    return filter.includes(value)
                                } else {
                                    return value == filter
                                }
                            });
                        return !partialMatch;
                    })
                } else {
                    result = rows;
                }
                break;
            case 'string':
                switch (filters) {
                    case '*':
                        result = [];
                        break;
                    default:
                        throw Error("Unknown filter format in remove operation");
                }
        }
        return result;
    },
    get(rows, filters) {
        let results = this.select(rows, filters);
        switch (results.length) {
            case 0:
                return null;
            case 1:
                return results[0];
            default:
                throw `There is no unique row`
        }
    },
    update(rows, newRow, partial = true) {
        let oldRow = this.get(rows, { id: newRow.id });
        if (partial) {
            for (let field in newRow) {
                oldRow[field] = newRow[field];
            }
        } else {
            oldRow = newRow;
        }
    },
    query(sql, tables) {
        // sort tables by their order in the query
        let tableNames = Object.keys(tables);
        let tableIndeces = tableNames
            .map((name) => sql.search(name))
            .map((i) => i == -1 ? Infinity : i); // missing tables go last
        let position = (n) => tableIndeces[tableNames.indexOf(n)];
        let sortedTableNames = tableNames
            .sort((a, b) => position(a) - position(b))
        let sortedTables = sortedTableNames
            .map((name) => tables[name]);
        // substitute table names with question marks
        let replace = (s, p) => s.replace(p, '?');
        let parsedSql = sortedTableNames.reduce(replace, sql);
        // execute query with alasql
        try {
            let result = alasql(parsedSql, sortedTables);
            return result;
        } catch (error) {
            console.error(`The following frontend SQL query failed:` +
                `${sql}`, {
                tables,
                error
            })
        }
    },
    fromSpreadsheet(clipboardText, fields) {
        // Split full text to rows
        let clipboardLines = clipboardText.split(String.fromCharCode(10));
        let spreadsheet = []
        for (let clipboardLine of clipboardLines) {
            spreadsheet.push(
                clipboardLine.split(String.fromCharCode(9))
            );
        }
        let parsedRows = [];
        for (let i in spreadsheet) {
            let parsedRow = {};
            for (let j in spreadsheet[i]) {
                let field = fields[j];
                parsedRow[field] = spreadsheet[i][j];
            }
            parsedRows.push(parsedRow);
        }
        return parsedRows;
    },
    toSpreadsheet(filename, sheets) {
        var workbook = xlsx.utils.book_new();
        for (let sheet of sheets) {
            let { rows, cols, name } = sheet;
            // construct header
            let fields = cols.map((col) => col.field);
            let headerLabels = cols.map((col) => col.label);
            let header = Object.fromEntries(
                fields.map((field, index) => ([field, headerLabels[index]]))
            )
            // helper function for selecting only used columns
            let selectFields = (row) => Object.fromEntries(
                Object.entries(row).filter(([field]) => fields.includes(field))
            );
            // add header and filter out unused fields
            let formattedRows = [header].concat(rows.map(selectFields))
            let worksheet = xlsx.utils.json_to_sheet(formattedRows, {
                // the default header uses field names
                // so we omit since we add our own header
                skipHeader: true
            });
            xlsx.utils.book_append_sheet(workbook, worksheet, name);
        }
        try {
            xlsx.writeFile(workbook, filename, { type: 'xlsx' })
        } catch (err) {
            console.error(err);
        }
    }
}

let generateId = (length) => (customAlphabet(
    'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz1234567890',
    length
)());