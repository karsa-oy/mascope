const { Parser } = require("json2csv")
import { customAlphabet } from "nanoid";
import alasql from 'alasql';

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
                            .some(([field, filter]) => (row[field] == filter));
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
    max(rows, measureField, groupingFields) {
        let groups = this.unique(
            rows.map(       // get group values
                row => Object.assign({}, ...groupingFields
                    .map(groupingField => ({
                        [groupingField]: row[groupingField]
                    }))
                )
            )
        );
        let maxima = groups.map(
            group => ({     // create groups
                ...group,                           // save grouping field
                [measureField]: Math.max(           // find max measure
                    ...this.select(rows, group)
                        .map(row => row[measureField])
                ),
            })
        );
        return maxima;
    },
    unique(rows) {
        return Array.from(new Set(rows.map(JSON.stringify))).map(JSON.parse);
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
        let result = alasql(parsedSql, sortedTables);
        return result;
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
    toSpreadsheet(filename, cols, rows) {
        const fields = cols.map((col) => ({
            label: col.label,
            value: col.field,
        }));
        try {
            // Parse CSV
            const parser = new Parser({ fields });
            const csv = parser.parse(rows);
            // Make blob
            const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
            // Create a temporary download link for the blob and "click" it
            var link = document.createElement("a");
            var url = URL.createObjectURL(blob);
            link.setAttribute("href", url);
            link.setAttribute("download", filename);
            link.style.visibility = "hidden";
            document.body.appendChild(link);
            link.click();
            // Remove the link
            document.body.removeChild(link);
        } catch (err) {
            console.error(err);
        }
    }
}

let generateId = (length) => (customAlphabet(
    'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz1234567890',
    length
)());