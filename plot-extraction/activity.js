import * as XLSX from 'xlsx/xlsx.mjs';
import fs from 'fs';
import path from 'path';
import { v4 as uuid } from 'uuid'



const appendRow = (arr, file) =>{
    fs.appendFileSync(path.join('./output/', file), '\n' + arr.join(",") , 'utf8');
}


try {
    
    const filePath = path.join("./", "Flattened_Activity_Structured_Expanded.xlsx");

    const fileData = fs.readFileSync(filePath);

    const workbook = XLSX.read(fileData, { type: 'buffer' });
    const sheetName = workbook.SheetNames[0];
    const sheetData = XLSX.utils.sheet_to_json(workbook.Sheets[sheetName], { header: 1 });

    const columns = {};
    sheetData[0].forEach((colName, index) => {
        columns[colName] = sheetData.slice(1).map(row => row[index]);
    });

    let packageId = uuid()
    let pkg = ""
    
    for(let i = 0; i< columns["Package"].length; i++){

        let subpackageId = uuid()
        let activityId = uuid()
        let subActivityId = uuid()

        if(`"${columns["Package"][i]}"` != pkg){
            packageId = uuid()
            pkg = `"${columns["Package"][i]}"`
            appendRow([packageId, pkg], "Package.csv");
        }

        appendRow(
          [
            subpackageId,
            packageId,
            `"${columns["Subpackage"][i]}"`,
            `"${columns["Subpackage"][i]}"`,
          ],
          "Subpackage.csv"
        );

        appendRow(
          [
            activityId,
            subpackageId,
            `"${columns["Activity"][i]}"`,
            `"${columns["Activity"][i]}"`,
            "",
          ],
          "Activity.csv"
        );

        appendRow(
          [
            subActivityId,
            activityId,
            `"${columns["Subactivity"][i]}"`,
            `"${columns["Subactivity"][i]}"`,
          ],
          "Subactivity.csv"
        );
        
        appendRow(
            [
                uuid(),
                `"${columns["Inspection_Code"][i]}"`,
                subActivityId,
                `"${columns["Unit_of_RFI"][i]}"`,
                "uom-id",
                "''",
                "type",
                `"${columns["Is_Optional"][i]}"`,
                `"${columns["Inspection_Name"][i]}"`,
                `"${columns["Inspection_Description"][i]}"`,
            ],
            'inspection-points.csv'
            );

    }

} catch (e) {
    console.log("something went wrong");
    console.log(e);
}



