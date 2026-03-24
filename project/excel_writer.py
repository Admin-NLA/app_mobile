import pandas as pd
import io
from xlsxwriter.worksheet import Worksheet

def create_records_excel_file(data:list, edition:str):
    df = pd.DataFrame(data)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, header=False, index=False, sheet_name='Contactos', startrow=3)
        workbook = writer.book
        worksheet:Worksheet = writer.sheets['Contactos']
        max_row, max_col = df.shape

        title_format = workbook.add_format({
            'bold': True,
            'font_size': 20,
            'align': 'center',
            'valign': 'vcenter',
            'bg_color': '#daeef3'
        })

        subtitle_format = workbook.add_format({
            'bold': True,
            'italic': True,
            'font_size': 14,
            'align': 'center',
            'valign': 'vcenter',
        })

        worksheet.merge_range("A1:E1", "Congreso de Mantenimiento y Confiabilidad", title_format)
        worksheet.set_row(0,25)
        worksheet.write("C2", edition, subtitle_format)

        column_settings = []
        for header in df.columns:
            column_settings.append({'header': header})

        worksheet.add_table(3,0,max_row+2, max_col-1, {'columns': column_settings, 'style': 'Table Style Dark 9'})
        wrap_format = workbook.add_format({'text_wrap':True, 'valign': 'vcenter'})

        for i, col in enumerate(df.columns):
            if col == 'NOTAS':
                worksheet.set_column(i,i,50, wrap_format)
            else:
                col_width = max(len(str(col)), df[col].astype(str).map(len).max())
                worksheet.set_column(i, i, col_width + 2, workbook.add_format({'valign': 'vcenter'}))

    output.seek(0)
    return output