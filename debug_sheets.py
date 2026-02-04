from app.sheets import get_sheets_client, GOOGLE_SHEET_ID, GOOGLE_SHEET_NAME

def debug_sheets():
    try:
        client = get_sheets_client()
        sheet = client.open_by_key(GOOGLE_SHEET_ID).worksheet(GOOGLE_SHEET_NAME)
        
        filas = sheet.get_all_values()
        print(f"Total filas: {len(filas)}")
        if len(filas) > 1:
            print("Header:", filas[0])
            print("Fila 1 (Data):", filas[1])
            print("Fila 2 (Data):", filas[2])
            print(f"Tipo dato fecha: {type(filas[1][1])} - Valor: '{filas[1][1]}'")
            print(f"Tipo dato monto: {type(filas[1][2])} - Valor: '{filas[1][2]}'")
            
    except Exception as e:
        print(e)

if __name__ == "__main__":
    debug_sheets()
