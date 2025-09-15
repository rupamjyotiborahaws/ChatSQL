def upload_dataset(file, table_name, db_path, if_not_exists):
    import pandas as pd
    import io
    from sqlalchemy import create_engine

    try:
        # read file into pandas
        # handle large files by streaming into pandas (pandas handles file-like objects)
        bytes_io = file.read()
        # detect encoding / try to read robustly
        try:
            df = pd.read_csv(io.BytesIO(bytes_io))
        except Exception as e_csv:
            df = pd.read_csv(io.BytesIO(bytes_io), encoding="latin1")

        conn_str = f"sqlite:///{db_path}"
        engine = create_engine(conn_str, connect_args={"check_same_thread": False})

        df.to_sql(
            name=table_name,
            con=engine,
            if_exists=if_not_exists,
            method="multi",
            chunksize=1000
        )

    except Exception as e:
        return f"Error processing file: {e}"
    
    return "Dataset uploaded and saved successfully."