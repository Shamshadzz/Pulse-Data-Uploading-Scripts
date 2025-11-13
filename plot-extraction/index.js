import * as XLSX from 'xlsx/xlsx.mjs';
import fs from 'fs';
import path from 'path';
import { v4 as uuid } from 'uuid'

const folderPath = 'C:/Users/Tejas Aghade/Desktop/ground/plot-extraction/files';
const PROJECT_ID = "eea7fdda-f78b-46ee-99b7-9e5c9773717b"

function appendRowToCSV(filePath, rowData) {
  const rowString = rowData.join(',');
  fs.appendFileSync(filePath, '\n' + rowString , 'utf8');
}

const csvFile = path.join('./', 'output.csv');


try {
    
    const files = fs.readdirSync(folderPath);
    const excelFiles = files.filter(file => path.extname(file).toLowerCase() === '.xlsx');

    let plotName = ""

    let plotId = uuid()
    
    for (const file of excelFiles) {
        
        const tempPlotName = file.split(" ")[3].split("-")[0];

        if(!plotName  || tempPlotName !== plotName){
            plotName = file.split(" ")[3].split("-")[0]    
            appendRowToCSV(csvFile, [plotId, PROJECT_ID, plotName, "plot",  ]);
        }

        let blockId = uuid();
        const blockName = file.split(" ")[3].split("-")[1]
        appendRowToCSV(csvFile, [blockId, PROJECT_ID, blockName, "block", plotId]);
        
        const filePath = path.join(folderPath, file);

        const fileData = fs.readFileSync(filePath);

        const workbook = XLSX.read(fileData, { type: 'buffer' });
        const sheetName = workbook.SheetNames[0];
        const sheetData = XLSX.utils.sheet_to_json(workbook.Sheets[sheetName], { header: 1 });

        const columns = {};
        sheetData[0].forEach((colName, index) => {
            columns[colName] = sheetData.slice(1).map(row => row[index]);
        });

        for (const [colName, colValues] of Object.entries(columns)) {
            for(let value of colValues ){
                if(value){
                    appendRowToCSV(csvFile, [uuid(), PROJECT_ID, value, colName==="Inverter Names"? "Inverter" : "Table", blockId]);
                }
            }
        }

    }

} catch (e) {
    console.log("something went wrong");
    console.log(e);
}



